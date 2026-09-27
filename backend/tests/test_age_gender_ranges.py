"""Age/gender-specific reference ranges: selection logic (pure)."""
from server import compute_result_flags

TEST_DOC = {
    "reference_ranges": [
        {"parameter": "Hemoglobin (Hb)", "unit": "g/dL", "normal_range": "12 - 17"},
        {"parameter": "Hemoglobin (Hb)", "unit": "g/dL", "normal_range": "14 - 18",
         "age_min": 18, "age_max": 120, "gender": "M"},
        {"parameter": "Hemoglobin (Hb)", "unit": "g/dL", "normal_range": "12 - 16",
         "age_min": 18, "age_max": 120, "gender": "F"},
        {"parameter": "Hemoglobin (Hb)", "unit": "g/dL", "normal_range": "11 - 15",
         "age_min": 0, "age_max": 17, "gender": None},
    ]
}


def test_adult_male_picks_male_range():
    flags, _ = compute_result_flags(TEST_DOC, {"Hemoglobin (Hb)": 17.5}, 30, "male")
    assert flags["Hemoglobin (Hb)"] == "N"  # 17.5 inside 14-18 (M)


def test_adult_female_picks_female_range():
    flags, _ = compute_result_flags(TEST_DOC, {"Hemoglobin (Hb)": 17.5}, 30, "female")
    assert flags["Hemoglobin (Hb)"] == "H"  # 17.5 above 12-16 (F)
    flags2, _ = compute_result_flags(TEST_DOC, {"Hemoglobin (Hb)": 13.0}, 30, "female")
    assert flags2["Hemoglobin (Hb)"] == "N"


def test_child_picks_child_range():
    flags, _ = compute_result_flags(TEST_DOC, {"Hemoglobin (Hb)": 10.5}, 10, "male")
    assert flags["Hemoglobin (Hb)"] == "L"  # 10.5 below 11-15 (child)
    flags2, _ = compute_result_flags(TEST_DOC, {"Hemoglobin (Hb)": 13.0}, 10, "female")
    assert flags2["Hemoglobin (Hb)"] == "N"  # child range ignores gender


def test_fallback_to_generic_without_demographics():
    # Old two-arg call: no age/gender -> generic 12-17 entry.
    flags, _ = compute_result_flags(TEST_DOC, {"Hemoglobin (Hb)": 17.5})
    assert flags["Hemoglobin (Hb)"] == "H"
    flags2, _ = compute_result_flags(TEST_DOC, {"Hemoglobin (Hb)": 17.5}, None, None)
    assert flags2["Hemoglobin (Hb)"] == "H"


def test_gender_only_range_still_needs_matching_gender():
    doc = {"reference_ranges": [
        {"parameter": "X", "unit": "u", "normal_range": "1 - 2"},
        {"parameter": "X", "unit": "u", "normal_range": "5 - 6", "gender": "F"},
    ]}
    flags, _ = compute_result_flags(doc, {"X": 5.5}, 40, "female")
    assert flags["X"] == "N"
    flags2, _ = compute_result_flags(doc, {"X": 5.5}, 40, "male")
    assert flags2["X"] == "H"  # falls back to generic


def test_most_specific_entry_wins():
    doc = {"reference_ranges": [
        {"parameter": "Y", "unit": "u", "normal_range": "1 - 10"},
        {"parameter": "Y", "unit": "u", "normal_range": "1 - 10", "gender": "M"},
        {"parameter": "Y", "unit": "u", "normal_range": "4 - 5", "age_min": 18, "age_max": 99, "gender": "M"},
    ]}
    flags, _ = compute_result_flags(doc, {"Y": 6}, 30, "male")
    assert flags["Y"] == "H"  # 3-constraint entry (4-5) wins over looser ones
