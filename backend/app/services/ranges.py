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

def compute_result_flags(test_doc: Optional[dict], values: Dict[str, Any]):
    """Compare entered values against the test's reference ranges.

    Returns (flags, auto_abnormal) where flags maps parameter name ->
    'H' | 'L' | 'N'. Handles per-parameter values keyed by parameter name,
    plus the legacy single {"value": ...} shape for single-range tests.
    """
    flags: Dict[str, str] = {}
    ranges = (test_doc or {}).get("reference_ranges") or []
    if not ranges:
        return flags, False
    norm_values = {str(k).strip().lower(): v for k, v in (values or {}).items()}
    for r in ranges:
        param = str(r.get("parameter", "")).strip()
        bounds = parse_range_bounds(str(r.get("normal_range", "")))
        if not param or not bounds:
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


def check_critical_values(test_doc: Optional[dict], values: Dict[str, Any]):
    """Check if any values exceed critical (panic) thresholds.

    Returns a list of dicts with parameter, value, critical_low/high,
    and direction ('critical_low' or 'critical_high') for each violation.
    """
    criticals = []
    ranges = (test_doc or {}).get("reference_ranges") or []
    if not ranges:
        return criticals
    norm_values = {str(k).strip().lower(): v for k, v in (values or {}).items()}
    for r in ranges:
        param = str(r.get("parameter", "")).strip()
        if not param:
            continue
        raw = norm_values.get(param.lower())
        if raw is None and len(ranges) == 1:
            raw = (values or {}).get("value")
        num = to_float(raw)
        if num is None:
            continue
        crit_low = to_float(r.get("critical_low"))
        crit_high = to_float(r.get("critical_high"))
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
