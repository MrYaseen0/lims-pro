# Skill: architecture

## Purpose
Keep `docs/ARCHITECTURE.md` aligned with the actual implementation.

## When to use
After any structural change: new router, new service, new collection, new auth rule, new external integration.

## Instructions
1. Read `docs/ARCHITECTURE.md` first.
2. Verify every statement against current files — components, data flow, trust boundaries, storage, external services, deployment.
3. Update the doc to match reality. Every claim must cite a current file or configuration.
4. Structure:
   - Components (backend package layout, frontend pages)
   - Data flow (request lifecycle with file paths)
   - Trust boundaries (auth, roles, rate limits)
   - Storage (MongoDB collections + indexes)
   - External services (none currently, or list them)
   - Deployment (Docker Compose topology, CI)

## Rules
- Never describe aspirational architecture — only what the code does today.
- If code and doc disagree, fix the doc (or fix the code, then the doc).
