# Skill: security-review

## Purpose
Threat-model trust boundaries and privileged actions before shipping.

## When to use
Auth changes, new endpoints, file uploads, new roles, dependency additions, pre-release review.

## Instructions
1. List trust boundaries: anonymous → authenticated → role-gated (technician, pathologist, lab_manager, admin, doctor).
2. Check each new/changed endpoint:
   - Is `get_current_user` enforced? Is `require_role` correct for the action?
   - Is input validated at the boundary (Pydantic model, strict types)?
   - Can a MongoDB operator (`$ne`, `$gt`, `$where`) reach a query? (Pydantic `str` types block this.)
   - Are IDs/object references authorized (no IDOR — user can only touch their scope)?
3. Check secrets: no hardcoded keys, `JWT_SECRET` from env with fail-fast if missing, no secrets in logs/responses.
4. Check destructive actions: delete endpoints require confirmation-worthy roles; audit log written.
5. Check rate limits: login has 10/min/IP (`backend/app/core/deps.py`); consider global limits for new hot endpoints.
6. Check dependencies: no known-CVE packages introduced (review `requirements.txt` diff).

## Rules
- UI hiding is not security — enforce server-side.
- Do not weaken safeguards to make a test pass.
- Never print secrets in output, logs, or reports.
- Report findings as: severity, attack scenario, exact file:line, fix.
