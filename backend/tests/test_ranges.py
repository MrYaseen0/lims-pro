"""Unit tests for reference-range parsing and H/L/N flag evaluation.

These are pure functions — no database needed.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("JWT_SECRET", "test-secret-key-for-pytest-suite")
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "lims_test_db")

from server import parse_range_bounds, compute_result_flags, to_float


def test_parse_simple_range():
    assert parse_range_bounds("12 - 17") == (12.0, 17.0)


def test_parse_no_spaces():
    assert parse_range_bounds("4.5-5.5") == (4.5, 5.5)


def test_parse_en_dash():
    assert parse_range_bounds("80 – 100") == (80.0, 100.0)


def test_parse_large_numbers():
    assert parse_range_bounds("4000 - 11000") == (4000.0, 11000.0)


def test_parse_invalid_returns_none():
    assert parse_range_bounds("not a range") is None
    assert parse_range_bounds("") is None
    assert parse_range_bounds(None) is None
    assert parse_range_bounds("< 5") is None


def test_flags_high_low_normal():
    test_doc = {"reference_ranges": [
        {"parameter": "Hemoglobin (Hb)", "unit": "g/dL", "normal_range": "12 - 17"},
        {"parameter": "TLC (WBC)", "unit": "/uL", "normal_range": "4000 - 11000"},
        {"parameter": "RBC Count", "unit": "million/uL", "normal_range": "4.5 - 5.5"},
    ]}
    flags, auto = compute_result_flags(test_doc, {
        "Hemoglobin (Hb)": 19, "TLC (WBC)": 2000, "RBC Count": 5.0,
    })
    assert flags["Hemoglobin (Hb)"] == "H"
    assert flags["TLC (WBC)"] == "L"
    assert flags["RBC Count"] == "N"
    assert auto is True


def test_flags_all_normal_not_abnormal():
    test_doc = {"reference_ranges": [
        {"parameter": "Hemoglobin (Hb)", "unit": "g/dL", "normal_range": "12 - 17"},
    ]}
    flags, auto = compute_result_flags(test_doc, {"Hemoglobin (Hb)": 14})
    assert flags == {"Hemoglobin (Hb)": "N"}
    assert auto is False


def test_flags_boundary_values_are_normal():
    test_doc = {"reference_ranges": [
        {"parameter": "X", "unit": "u", "normal_range": "10 - 20"},
    ]}
    flags, _ = compute_result_flags(test_doc, {"X": 10})
    assert flags["X"] == "N"
    flags, _ = compute_result_flags(test_doc, {"X": 20})
    assert flags["X"] == "N"


def test_flags_case_insensitive_parameter_match():
    test_doc = {"reference_ranges": [
        {"parameter": "Hemoglobin (Hb)", "unit": "g/dL", "normal_range": "12 - 17"},
    ]}
    flags, _ = compute_result_flags(test_doc, {"hemoglobin (hb)": 19})
    assert flags["Hemoglobin (Hb)"] == "H"


def test_flags_no_ranges():
    flags, auto = compute_result_flags({}, {"X": 5})
    assert flags == {} and auto is False
    flags, auto = compute_result_flags(None, {"X": 5})
    assert flags == {} and auto is False


def test_flags_unparseable_range_skipped():
    test_doc = {"reference_ranges": [
        {"parameter": "X", "unit": "u", "normal_range": "see notes"},
    ]}
    flags, auto = compute_result_flags(test_doc, {"X": 999})
    assert flags == {} and auto is False


def test_flags_non_numeric_value_skipped():
    test_doc = {"reference_ranges": [
        {"parameter": "X", "unit": "u", "normal_range": "10 - 20"},
    ]}
    flags, auto = compute_result_flags(test_doc, {"X": "hemolyzed"})
    assert flags == {} and auto is False


def test_to_float():
    assert to_float(" 12.5 ") == 12.5
    assert to_float(7) == 7.0
    assert to_float(None) is None
    assert to_float("abc") is None
