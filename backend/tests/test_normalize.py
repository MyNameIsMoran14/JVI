from app.extraction.models import Analyte, ResultFlag, UnitConversion
from app.extraction.normalize import compute_flag, convert_unit, detect_jump, match_analyte


def _hgb() -> Analyte:
    return Analyte(
        id=1,
        code="HGB",
        name_ru="Гемоглобин",
        canonical_unit="г/л",
        aliases=["HGB", "Hb", "гемоглобин"],
        group="blood",
        is_key=True,
    )


def test_match_analyte_exact_alias() -> None:
    analyte, confidence = match_analyte("HGB", [_hgb()])
    assert analyte is not None
    assert analyte.code == "HGB"
    assert confidence == 1.0


def test_match_analyte_exact_case_insensitive() -> None:
    analyte, confidence = match_analyte("гемоглобин", [_hgb()])
    assert analyte is not None
    assert confidence == 1.0


def test_match_analyte_fuzzy() -> None:
    analyte, confidence = match_analyte("гемоглабин", [_hgb()])  # typo of "гемоглобин"
    assert analyte is not None
    assert analyte.code == "HGB"
    assert 0 < confidence < 1.0


def test_match_analyte_no_match() -> None:
    analyte, confidence = match_analyte("совершенно другой показатель xyz", [_hgb()])
    assert analyte is None
    assert confidence == 0.0


def test_convert_unit_same_unit() -> None:
    value, issue = convert_unit(120.0, "г/л", _hgb(), [])
    assert value == 120.0
    assert issue is None


def test_convert_unit_with_conversion_factor() -> None:
    hgb = _hgb()
    conversions = [UnitConversion(id=1, analyte_id=hgb.id, from_unit="г/дл", factor=10)]
    value, issue = convert_unit(12.0, "г/дл", hgb, conversions)
    assert value == 120.0
    assert issue is None


def test_convert_unit_unknown_unit() -> None:
    value, issue = convert_unit(12.0, "ммоль/л", _hgb(), [])
    assert value is None
    assert issue is not None


def test_convert_unit_missing_unit() -> None:
    value, issue = convert_unit(12.0, None, _hgb(), [])
    assert value is None
    assert issue == "не указана единица измерения"


def test_compute_flag_low() -> None:
    assert compute_flag(90, ref_low=130, ref_high=160) == ResultFlag.low


def test_compute_flag_high() -> None:
    assert compute_flag(200, ref_low=130, ref_high=160) == ResultFlag.high


def test_compute_flag_normal() -> None:
    assert compute_flag(140, ref_low=130, ref_high=160) == ResultFlag.normal


def test_compute_flag_no_reference() -> None:
    assert compute_flag(140, ref_low=None, ref_high=None) is None


def test_compute_flag_no_value() -> None:
    assert compute_flag(None, ref_low=130, ref_high=160) is None


def test_detect_jump_true() -> None:
    assert detect_jump(new_value=30, previous_value=10) is True


def test_detect_jump_false() -> None:
    assert detect_jump(new_value=12, previous_value=10) is False


def test_detect_jump_ignores_non_positive() -> None:
    assert detect_jump(new_value=0, previous_value=10) is False
