# Agent Operating Rules — LIMS.Pro

## Objective
Make the smallest correct change, preserve existing behavior, and prove the result with real command output.

## Start every task
1. Read this file and the relevant skill in `.agents/skills/`.
2. Inspect the repository tree and entry points (`backend/server.py`, `frontend/src/`).
3. Reproduce the issue or establish a baseline before editing.
4. Name the files and boundaries likely to change.

## Implementation rules
- Read before editing; do not invent APIs, files, or results.
- Backend entry point must remain `uvicorn server:app` (`backend/server.py` is a compatibility shim over `backend/app/`).
- Follow existing architecture: routers in `backend/app/routers/`, business logic in `backend/app/services/`, shared code in `backend/app/core/`.
- Keep UI responsive and accessible; test at 360px, 390px, 768px and desktop.
- Validate all external input at the boundary (Pydantic models).
- Enforce authorization server-side (`require_role`), never only in the UI.
- Never expose secrets in output, logs, files, or URLs. Never print JWT_SECRET.
- Ask before destructive operations (data deletion, history rewrites).

## Documentation
- Update `docs/ARCHITECTURE.md` when structure or data flow changes.
- Add a dated entry to `docs/DECISIONS.md` for every lasting technical choice.
- Keep README setup commands synchronized with the code.

## Verification
- Backend: run the smallest relevant pytest first, then the full suite (`/tmp/limsvenv/bin/pytest -q` from `backend/`).
- Frontend: `npm run build` must pass after UI changes.
- Completion requires real command/tool evidence — never claim success from inspection alone.

## Final response
State root cause, changed files, checks run with actual results, and any remaining limitations.

## Skill router
| Task | Skills |
|------|--------|
| Understand structure/data flow | repo-map + architecture |
| Lasting technical choice | decisions |
| Rough request → precise task | prompt-enhancer |
| React frontend work | responsive-ui |
| Mobile/layout/touch | responsive-ui |
| Auth/data/uploads | security-review |
| Bug or regression | testing |
| Release/deployment | release-check |
| FastAPI/Python backend | testing + security-review |

Load the narrowest set. Follow repo-specific commands. Verify before claiming completion.
