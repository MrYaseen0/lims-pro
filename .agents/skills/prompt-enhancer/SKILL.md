# Skill: prompt-enhancer

## Purpose
Convert a rough request into a precise, copy-pasteable implementation prompt without changing intent.

## When to use
Terse bug reports, vague feature asks, any request that needs diagnosis before editing.

## Instructions
Rewrite the request as one implementation prompt containing:
1. **Goal** — one sentence, preserving the user's actual requirement.
2. **Diagnose first** — which files to read, what to reproduce, likely fault path.
3. **Constraints** — architecture rules from AGENTS.md, files not to touch.
4. **Acceptance criteria** — observable behaviors that define done.
5. **Verification** — exact commands to run (pytest file, build, curl).
6. **Final summary required** — root cause, changed paths, check results, limitations.

## Rules
- Preserve the user's requirements — never silently narrow or expand scope.
- Diagnose before editing; never invent completed work.
- Output the enhanced prompt as a copy-pasteable block, not raw chat prose.
