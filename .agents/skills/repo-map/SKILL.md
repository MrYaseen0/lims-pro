# Skill: repo-map

## Purpose
Build an accurate file map of the repository — entry points, dependencies, routes, data stores, and test commands — before editing anything.

## When to use
Every task that touches code. Especially before refactors, bug fixes, and feature work.

## Instructions
1. Identify runtime entry points:
   - Backend: `backend/server.py` (shim) → `backend/app/main.py` (FastAPI app)
   - Frontend: `frontend/src/index.js` → `frontend/src/App.js`
2. List package scripts and test commands:
   - Backend: `/tmp/limsvenv/bin/pytest -q` (from `backend/`), `/tmp/limsvenv/bin/uvicorn server:app`
   - Frontend: `npm ci`, `npm run build`, `npm start`
3. Map routes: every file in `backend/app/routers/` → its URL prefix and role guards.
4. Map data flow: request → router → service (`backend/app/services/`) → MongoDB collection.
5. Map persistence: MongoDB database name, collections used, where indexes are ensured (`ensure_indexes`).
6. Map auth boundaries: `get_current_user`, `require_role` in `backend/app/core/deps.py`; which routes require which roles.
7. Cite exact file paths for everything.

## Rules
- Do not edit until the map and the likely fault path are clear.
- Do not invent files, routes, or collections — verify each one exists.
- If the map contradicts `docs/ARCHITECTURE.md`, flag the drift.
