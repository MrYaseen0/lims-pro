"""Seed helpers: yearly patient serials, doctors, test reference ranges."""
import uuid
from datetime import datetime, timezone
from typing import Optional

from pymongo import ReturnDocument

from app.core.database import db


# Yearly patient serial numbers: 0001-09-2026 (counter-month-year).
# The counter restarts at 1 every calendar year.
async def next_patient_serial() -> str:
    now = datetime.now()
    year = now.year
    result = await db.counters.find_one_and_update(
        {"_id": f"patient_serial_{year}"},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return f"{result['seq']:04d}-{now.month:02d}-{year}"

SEED_DOCTORS = ["Dr. Ahmed Khan", "Dr. Sara Malik", "Dr. Bilal Hussain"]

async def ensure_doctors_seeded():
    """Seed the referring-doctors list once (never duplicates)."""
    if await db.doctors.count_documents({}) == 0:
        await db.doctors.insert_many([
            {
                "id": str(uuid.uuid4()),
                "name": name,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            for name in SEED_DOCTORS
        ])

# Reference ranges keyed by test code. Each entry is a list of
# {"parameter", "unit", "normal_range"} dicts.
REFERENCE_RANGES = {
    "CBC": [
        {"parameter": "Hemoglobin (Hb)", "unit": "g/dL", "normal_range": "12 - 17", "critical_low": 7.0, "critical_high": 20.0},
        {"parameter": "TLC (WBC)", "unit": "/uL", "normal_range": "4000 - 11000", "critical_low": 2000, "critical_high": 30000},
        {"parameter": "RBC Count", "unit": "million/uL", "normal_range": "4.5 - 5.5"},
        {"parameter": "Platelet Count", "unit": "/uL", "normal_range": "150000 - 400000", "critical_low": 20000, "critical_high": 1000000},
        {"parameter": "PCV", "unit": "%", "normal_range": "36 - 46"},
        {"parameter": "MCV", "unit": "fL", "normal_range": "80 - 100"},
        {"parameter": "MCH", "unit": "pg", "normal_range": "27 - 32"},
        {"parameter": "MCHC", "unit": "g/dL", "normal_range": "32 - 36"},
        {"parameter": "Neutrophils", "unit": "%", "normal_range": "40 - 75"},
        {"parameter": "Lymphocytes", "unit": "%", "normal_range": "20 - 40"},
        {"parameter": "Monocytes", "unit": "%", "normal_range": "2 - 8"},
        {"parameter": "Eosinophils", "unit": "%", "normal_range": "1 - 6"},
        {"parameter": "Basophils", "unit": "%", "normal_range": "0 - 1"},
        {"parameter": "ESR", "unit": "mm/hr", "normal_range": "0 - 20"},
    ],
    "RFT": [
        {"parameter": "Urea", "unit": "mg/dL", "normal_range": "15 - 40"},
        {"parameter": "Creatinine", "unit": "mg/dL", "normal_range": "0.6 - 1.2", "critical_high": 7.5},
        {"parameter": "Uric Acid", "unit": "mg/dL", "normal_range": "3.0 - 7.0"},
        {"parameter": "Sodium (Na+)", "unit": "mEq/L", "normal_range": "135 - 145", "critical_low": 120, "critical_high": 160},
        {"parameter": "Potassium (K+)", "unit": "mEq/L", "normal_range": "3.5 - 5.5", "critical_low": 2.8, "critical_high": 6.0},
        {"parameter": "Chloride (Cl-)", "unit": "mEq/L", "normal_range": "98 - 107"},
        {"parameter": "Calcium", "unit": "mg/dL", "normal_range": "8.5 - 10.5", "critical_low": 6.5, "critical_high": 13.0},
        {"parameter": "Phosphorus", "unit": "mg/dL", "normal_range": "2.5 - 4.5"},
    ],
    "LFT": [
        {"parameter": "Total Bilirubin", "unit": "mg/dL", "normal_range": "0.3 - 1.2"},
        {"parameter": "Direct Bilirubin", "unit": "mg/dL", "normal_range": "0.0 - 0.3"},
        {"parameter": "Indirect Bilirubin", "unit": "mg/dL", "normal_range": "0.2 - 0.8"},
        {"parameter": "SGPT (ALT)", "unit": "U/L", "normal_range": "7 - 56"},
        {"parameter": "SGOT (AST)", "unit": "U/L", "normal_range": "10 - 40"},
        {"parameter": "Alkaline Phosphatase", "unit": "U/L", "normal_range": "44 - 147"},
        {"parameter": "Total Protein", "unit": "g/dL", "normal_range": "6.0 - 8.3"},
        {"parameter": "Albumin", "unit": "g/dL", "normal_range": "3.5 - 5.5"},
        {"parameter": "Globulin", "unit": "g/dL", "normal_range": "2.0 - 3.5"},
        {"parameter": "A/G Ratio", "unit": "-", "normal_range": "1.0 - 2.5"},
    ],
}

# Age/gender-specific Hemoglobin variants for CBC. They carry optional
# age_min/age_max (years) and gender ("M"/"F"; None = any). The generic
# "12 - 17" entry above stays as the fallback for unknown demographics.
CBC_HEMOGLOBIN_VARIANTS = [
    {"parameter": "Hemoglobin (Hb)", "unit": "g/dL", "normal_range": "14 - 18",
     "critical_low": 7.0, "critical_high": 20.0, "age_min": 18, "age_max": 120, "gender": "M",
     "delta_limit_percent": 20},
    {"parameter": "Hemoglobin (Hb)", "unit": "g/dL", "normal_range": "12 - 16",
     "critical_low": 7.0, "critical_high": 20.0, "age_min": 18, "age_max": 120, "gender": "F",
     "delta_limit_percent": 20},
    {"parameter": "Hemoglobin (Hb)", "unit": "g/dL", "normal_range": "11 - 15",
     "critical_low": 7.0, "critical_high": 20.0, "age_min": 0, "age_max": 17, "gender": None,
     "delta_limit_percent": 20},
]

SEED_TESTS = [
    {"name": "Complete Blood Count", "code": "CBC", "category": "Hematology", "sample_type": "blood", "price": 25.0, "turn_around_time": 4},
    {"name": "Renal Function Test", "code": "RFT", "category": "Biochemistry", "sample_type": "blood", "price": 40.0, "turn_around_time": 6},
    {"name": "Blood Glucose Fasting", "code": "BGF", "category": "Biochemistry", "sample_type": "blood", "price": 15.0, "turn_around_time": 2},
    {"name": "Lipid Profile", "code": "LIPID", "category": "Biochemistry", "sample_type": "blood", "price": 45.0, "turn_around_time": 6},
    {"name": "Liver Function Test", "code": "LFT", "category": "Biochemistry", "sample_type": "blood", "price": 50.0, "turn_around_time": 6},
    {"name": "Kidney Function Test", "code": "KFT", "category": "Biochemistry", "sample_type": "blood", "price": 40.0, "turn_around_time": 6},
    {"name": "Thyroid Profile", "code": "THYROID", "category": "Endocrinology", "sample_type": "blood", "price": 60.0, "turn_around_time": 8},
    {"name": "Urine Routine", "code": "URINE", "category": "Clinical Pathology", "sample_type": "urine", "price": 10.0, "turn_around_time": 2},
    {"name": "HbA1c", "code": "HBA1C", "category": "Biochemistry", "sample_type": "blood", "price": 35.0, "turn_around_time": 4},
    {"name": "Vitamin D", "code": "VITD", "category": "Biochemistry", "sample_type": "blood", "price": 55.0, "turn_around_time": 24},
    {"name": "Vitamin B12", "code": "VITB12", "category": "Biochemistry", "sample_type": "blood", "price": 50.0, "turn_around_time": 24},
]

async def ensure_test_reference_ranges():
    """Backfill reference ranges for CBC/RFT/LFT on databases seeded before this change.
    Also inserts the RFT test itself if it does not exist yet.
    Merges critical_low/critical_high thresholds into existing ranges by parameter
    name, without overwriting values an admin already customized.
    Also backfills the age/gender-specific Hemoglobin variants for CBC (matched
    by parameter+gender+age_min+age_max so re-runs never duplicate)."""
    for t in SEED_TESTS:
        code = t["code"]
        ranges = REFERENCE_RANGES.get(code, [])
        if not ranges:
            continue
        existing = await db.tests.find_one({"code": code})
        if not existing:
            test_doc = {
                "id": str(uuid.uuid4()),
                **t,
                "description": f"Standard {t['name']} test",
                "reference_ranges": ranges,
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            await db.tests.insert_one(test_doc)
        elif not existing.get("reference_ranges"):
            await db.tests.update_one({"code": code}, {"$set": {"reference_ranges": ranges}})
        else:
            seed_by_param = {r["parameter"]: r for r in ranges}
            merged = []
            changed = False
            for r in existing["reference_ranges"]:
                seed = seed_by_param.get(r.get("parameter"))
                if seed:
                    r = dict(r)
                    for key in ("critical_low", "critical_high"):
                        if key in seed and key not in r:
                            r[key] = seed[key]
                            changed = True
                merged.append(r)
            if changed:
                await db.tests.update_one({"code": code}, {"$set": {"reference_ranges": merged}})
    await ensure_hemoglobin_variants()


def _variant_key(entry: dict):
    """Identity of an age/gender range variant (no-duplicate matching)."""
    return (
        entry.get("parameter"),
        entry.get("gender"),
        entry.get("age_min"),
        entry.get("age_max"),
    )


async def ensure_hemoglobin_variants():
    """Add the age/gender-specific Hemoglobin ranges to CBC without duplicating."""
    test = await db.tests.find_one({"code": "CBC"})
    if not test:
        return
    existing_keys = {_variant_key(r) for r in test.get("reference_ranges", [])}
    missing = [v for v in CBC_HEMOGLOBIN_VARIANTS if _variant_key(v) not in existing_keys]
    if missing:
        await db.tests.update_one(
            {"code": "CBC"},
            {"$push": {"reference_ranges": {"$each": missing}}},
        )


# ---------------- Multi-branch ----------------

DEFAULT_BRANCH_CODE = "MAIN"
DEFAULT_BRANCH_NAME = "Main Branch"


async def ensure_default_branch() -> str:
    """Idempotently seed the default branch and backfill branch_id on
    collections that predate multi-branch support. Returns the branch id."""
    branch = await db.branches.find_one({"code": DEFAULT_BRANCH_CODE})
    if not branch:
        branch = {
            "id": str(uuid.uuid4()),
            "name": DEFAULT_BRANCH_NAME,
            "code": DEFAULT_BRANCH_CODE,
            "address": "",
            "phone": "",
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.branches.insert_one(branch)
    branch_id = branch["id"]
    missing = {"branch_id": {"$exists": False}}
    await db.users.update_many(missing, {"$set": {"branch_id": branch_id}})
    await db.patients.update_many(missing, {"$set": {"branch_id": branch_id}})
    await db.orders.update_many(missing, {"$set": {"branch_id": branch_id}})
    await db.inventory_items.update_many(missing, {"$set": {"branch_id": branch_id}})
    return branch_id


async def get_default_branch_id():
    """Return the default branch id, or None if it was never seeded."""
    branch = await db.branches.find_one({"code": DEFAULT_BRANCH_CODE}, {"_id": 0, "id": 1})
    return branch["id"] if branch else None
