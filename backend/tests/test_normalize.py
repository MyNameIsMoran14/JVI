from app.extraction.models import Analyte, ResultFlag, UnitConversion
from app.extraction.normalize import compute_flag, convert_unit, detect_jump, match_analyte, slugify_code


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


def test_convert_unit_missing_unit_is_fine_for_dimensionless_analyte() -> None:
    index = Analyte(
        id=2, code="IRI", name_ru="Индекс", canonical_unit="", aliases=[], group="x", is_key=False
    )
    value, issue = convert_unit(0.36, None, index, [])
    assert value == 0.36
    assert issue is None


def test_convert_unit_normalizes_unicode_superscript() -> None:
    wbc = Analyte(
        id=3, code="WBC", name_ru="Лейкоциты", canonical_unit="10^9/л", aliases=[], group="blood", is_key=True
    )
    value, issue = convert_unit(5.0, "10⁹/л", wbc, [])
    assert value == 5.0
    assert issue is None


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


def test_slugify_code_deterministic() -> None:
    assert slugify_code("Новый неизвестный показатель") == slugify_code("Новый неизвестный показатель")


def test_slugify_code_differs_for_different_names() -> None:
    assert slugify_code("Показатель А") != slugify_code("Показатель Б")


def test_slugify_code_handles_pure_cyrillic() -> None:
    code = slugify_code("Циркулирующие иммунные комплексы")
    assert code.startswith("AUTO_")
    assert code.isascii()
