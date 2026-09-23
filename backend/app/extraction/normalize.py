from rapidfuzz import fuzz, process

from app.extraction.models import Analyte, ResultFlag, UnitConversion

FUZZY_MATCH_THRESHOLD = 85
JUMP_RATIO_THRESHOLD = 3.0


def _norm(value: str) -> str:
    return value.strip().lower()


def match_analyte(raw_name: str, analytes: list[Analyte]) -> tuple[Analyte | None, float]:
    """Matches a raw label from a lab form to a known analyte.

    Returns (analyte, confidence) — confidence is 1.0 for an exact alias/name/code match,
    the fuzzy score (0-1) for a fuzzy match above the threshold, or (None, 0.0) if unmatched.
    """
    target = _norm(raw_name)

    corpus: dict[str, Analyte] = {}
    for analyte in analytes:
        for candidate in (analyte.code, analyte.name_ru, *analyte.aliases):
            corpus[_norm(candidate)] = analyte

    if target in corpus:
        return corpus[target], 1.0

    best = process.extractOne(target, corpus.keys(), scorer=fuzz.WRatio)
    if best is None:
        return None, 0.0
    match_name, score, _ = best
    if score < FUZZY_MATCH_THRESHOLD:
        return None, 0.0
    return corpus[match_name], score / 100


def convert_unit(
    value: float, unit: str | None, analyte: Analyte, conversions: list[UnitConversion]
) -> tuple[float | None, str | None]:
    """Converts a value to the analyte's canonical unit. Returns (value_canonical, issue)."""
    if unit is None:
        return None, "не указана единица измерения"

    normalized_unit = _norm(unit)
    canonical = _norm(analyte.canonical_unit or "")
    if not canonical or normalized_unit == canonical:
        return value, None

    for conversion in conversions:
        if conversion.analyte_id == analyte.id and _norm(conversion.from_unit) == normalized_unit:
            return value * float(conversion.factor), None

    return None, f"неизвестная единица «{unit}», нужна ручная проверка"


def compute_flag(
    value: float | None, ref_low: float | None, ref_high: float | None
) -> ResultFlag | None:
    if value is None or (ref_low is None and ref_high is None):
        return None
    if ref_low is not None and value < ref_low:
        return ResultFlag.low
    if ref_high is not None and value > ref_high:
        return ResultFlag.high
    return ResultFlag.normal


def detect_jump(new_value: float, previous_value: float) -> bool:
    """Flags a jump of JUMP_RATIO_THRESHOLD× or more versus the previous confirmed value."""
    if new_value <= 0 or previous_value <= 0:
        return False
    ratio = max(new_value / previous_value, previous_value / new_value)
    return ratio >= JUMP_RATIO_THRESHOLD
