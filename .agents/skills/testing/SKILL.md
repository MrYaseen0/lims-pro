# Skill: testing

## Purpose
Reproduce first, fix narrowly, and prove it with real test output.

## When to use
Bug fixes, regressions, new features, refactors.

## Instructions
1. **Reproduce first.** Write the smallest failing test (or pytest command) that demonstrates the issue before changing code.
2. **Narrow fix.** Change the minimum code needed. Do not refactor surrounding code in the same pass.
3. **Targeted check.** Run the specific test file first:
   ```bash
   cd backend && /tmp/limsvenv/bin/pytest tests/test_<name>.py -q
   ```
4. **Full gate.** Run the whole suite and require it green:
   ```bash
   cd backend && /tmp/limsvenv/bin/pytest -q
   ```
5. **Report.** State the exact commands run and their actual results (pass/fail counts).

## Backend test conventions
- Tests live in `backend/tests/`, fixtures in `backend/tests/conftest.py`.
- Test DB: `lims_test_db` on `mongodb://localhost:27017` (never touch production data).
- `pytest.ini` sets `asyncio_mode = auto`.
- If tests pass alone but fail together, suspect fixture/teardown interference or a stray background pytest process — kill strays with `pkill -f pytest` and re-run before blaming the code.

## Rules
- Never weaken a test or safeguard to make it pass.
- Never claim "tests pass" without running them in this session.
- A task is complete only after the full gate is green.
