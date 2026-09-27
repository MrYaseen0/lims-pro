"""Reference-range parsing and automatic H/L/N flagging (pure logic)."""
import re
from typing import Dict, Any, Optional


_RANGE_RE = re.compile(r"^\s*([+-]?(?:\d+(?:\.\d+)?|\.\d+))\s*[-–]\s*([+-]?(?:\d+(?:\.\d+)?|\.\d+))\s*$")

def parse_range_bounds(normal_range: str):
    """Parse '12 - 17' -> (12.0, 17.0). Returns None if not parseable."""
    m = _RANGE_RE.match(normal_range or "")
    if not m:
        return None
    try:
        return float(m.group(1)), float(m.group(2))
    except ValueError:
        return None

def to_float(value) -> Optional[float]:
    try:
        return float(str(value).strip())
    except (ValueError, TypeError, AttributeError):
        return None

def _normalize_gender(gender) -> Optional[str]:
    """Normalize a gender value to 'M' | 'F' | 'O' (or None if unknown)."""
    if gender is None:
        return None
    g = str(gender).strip().lower()
    if not g:
        return None
    if g.startswith("m"):
        return "M"
    if g.startswith("f"):
        return "F"
    return "O"


def _range_specificity(entry: dict) -> int:
    """Number of non-null age/gender constraints on a range entry."""
    return sum(1 for key in ("age_min", "age_max", "gender") if entry.get(key) is not None)


def match_range_entry(ranges, parameter: str, age_years=None, gender=None):
    """Pick the best range entry for ``parameter`` given patient demographics.

    Candidates must match the parameter name (case-insensitive) and satisfy
    every constraint they carry: age within [age_min, age_max] when set
    (requires a known age), and gender when set. The most specific entry
    (most non-null constraints; ties broken by list order) wins. Falls back
    to a generic unconstrained entry when no constrained entry matches.
    Returns None when nothing usable exists.
    """
    gender_norm = _normalize_gender(gender)
    try:
        age = float(age_years) if age_years is not None else None
    except (TypeError, ValueError):
        age = None
    wanted = str(parameter).strip().lower()
    constrained, generic = [], []
    for r in ranges or []:
        if str(r.get("parameter", "")).strip().lower() != wanted:
            continue
        if not parse_range_bounds(str(r.get("normal_range", ""))):
            continue
        age_min, age_max = r.get("age_min"), r.get("age_max")
        entry_gender = _normalize_gender(r.get("gender"))
        # A constrained entry only matches when the patient data needed to
        # evaluate its constraints is present and satisfies them.
        if age_min is not None and (age is None or age < float(age_min)):
            continue
        if age_max is not None and (age is None or age > float(age_max)):
            continue
        if entry_gender is not None and (gender_norm is None or gender_norm != entry_gender):
            continue
        if _range_specificity(r) > 0:
            constrained.append(r)
        else:
            generic.append(r)
    if constrained:
        return max(constrained, key=_range_specificity)
    return generic[0] if generic else None


def compute_result_flags(test_doc: Optional[dict], values: Dict[str, Any], age_years=None, gender=None):
    """Compare entered values against the test's reference ranges.

    Returns (flags, auto_abnormal) where flags maps parameter name ->
    'H' | 'L' | 'N'. Handles per-parameter values keyed by parameter name,
    plus the legacy single {"value": ...} shape for single-range tests.

    When age_years/gender are given, age/gender-specific range entries are
    preferred (most specific match wins); otherwise the generic entry is
    used, keeping old positional calls working unchanged.
    """
    flags: Dict[str, str] = {}
    ranges = (test_doc or {}).get("reference_ranges") or []
    if not ranges:
        return flags, False
    norm_values = {str(k).strip().lower(): v for k, v in (values or {}).items()}
    # One range entry per parameter: dedupe by the entry we would match.
    seen = set()
    for r in ranges:
        param = str(r.get("parameter", "")).strip()
        if not param or param.lower() in seen:
            continue
        seen.add(param.lower())
        entry = match_range_entry(ranges, param, age_years, gender)
        if entry is None:
            continue
        bounds = parse_range_bounds(str(entry.get("normal_range", "")))
        if not bounds:
            continue
        low, high = bounds
        raw = norm_values.get(param.lower())
        if raw is None and len(ranges) == 1:
            raw = (values or {}).get("value")
        num = to_float(raw)
        if num is None:
            continue
        if num < low:
            flags[param] = "L"
        elif num > high:
            flags[param] = "H"
        else:
            flags[param] = "N"
    auto_abnormal = any(f in ("H", "L") for f in flags.values())
    return flags, auto_abnormal


def check_delta(previous, current, limit_percent=20):
    """Compare a current value against the previous result for delta checking.

    Returns a dict with previous_value, current_value, abs_change,
    change_percent and warning (True when change_percent > limit_percent).
    Returns None when either value is missing/non-numeric or the previous
    value is zero (percent change undefined) — no warning is raised then.
    """
    prev = to_float(previous)
    cur = to_float(current)
    if prev is None or cur is None or prev == 0:
        return None
    abs_change = abs(cur - prev)
    change_percent = abs_change / abs(prev) * 100.0
    return {
        "previous_value": prev,
        "current_value": cur,
        "abs_change": abs_change,
        "change_percent": change_percent,
        "warning": change_percent > float(limit_percent),
    }


def check_critical_values(test_doc: Optional[dict], values: Dict[str, Any]):
    """Check if any values exceed critical (panic) thresholds.

    Returns a list of dicts with parameter, value, critical_low/high,
    and direction ('critical_low' or 'critical_high') for each violation.
    Each parameter is evaluated exactly once (against its best range entry),
    so age/gender variant entries never produce duplicate alerts.
    """
    criticals = []
    ranges = (test_doc or {}).get("reference_ranges") or []
    if not ranges:
        return criticals
    norm_values = {str(k).strip().lower(): v for k, v in (values or {}).items()}
    seen = set()
    for r in ranges:
        param = str(r.get("parameter", "")).strip()
        if not param or param.lower() in seen:
            continue
        seen.add(param.lower())
        entry = match_range_entry(ranges, param)
        if entry is None:
            continue
        raw = norm_values.get(param.lower())
        if raw is None and len(ranges) == 1:
            raw = (values or {}).get("value")
        num = to_float(raw)
        if num is None:
            continue
        crit_low = to_float(entry.get("critical_low"))
        crit_high = to_float(entry.get("critical_high"))
        if crit_low is not None and num < crit_low:
            criticals.append({
                "parameter": param,
                "value": num,
                "critical_low": crit_low,
                "critical_high": crit_high,
                "direction": "critical_low",
            })
        elif crit_high is not None and num > crit_high:
            criticals.append({
                "parameter": param,
                "value": num,
                "critical_low": crit_low,
                "critical_high": crit_high,
                "direction": "critical_high",
            })
    return criticals

def serialize_datetime(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj
