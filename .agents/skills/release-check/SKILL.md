# Skill: release-check

## Purpose
Make completion depend on executable checks. Nothing ships without a green gate.

## When to use
Before every commit, push, and deployment.

## Instructions
Run the full verification loop in order. Stop at the first failure.

```bash
# 1. Backend tests (from backend/)
cd backend && /tmp/limsvenv/bin/pytest -q

# 2. Backend boot smoke test
cd backend && JWT_SECRET=<test-only> /tmp/limsvenv/bin/uvicorn server:app --port 8001 &
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8001/docs
# kill the server after

# 3. Frontend production build (from frontend/)
cd frontend && npm ci && npm run build

# 4. Docker Compose config validation (from repo root)
docker compose config > /dev/null && echo "compose OK"
```

## Rules
- Use the repository's real commands — do not claim a check passed when its tool isn't available.
- If `npm ci` or Docker isn't available in this environment, mark that gate as SKIPPED (not passed) and say so.
- Report each gate as PASS / FAIL / SKIPPED with the actual command output.
- A release is green only when every applicable gate passes.
