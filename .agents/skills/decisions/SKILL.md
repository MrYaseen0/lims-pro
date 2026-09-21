# Skill: decisions

## Purpose
Record lasting technical choices in `docs/DECISIONS.md` so future work understands why.

## When to use
Any decision with consequences: framework choices, schema changes, auth model changes, refactor direction, dropped features.

## Instructions
1. Append a dated entry to `docs/DECISIONS.md` using this format:

```
## YYYY-MM-DD — Title
- **Context:** What problem or situation prompted this.
- **Decision:** What was chosen.
- **Alternatives:** What else was considered.
- **Reason:** Why this won.
- **Consequences:** What follows from it (costs, constraints).
- **Revisit trigger:** What future event would reopen this.
```

2. Keep entries short — 6 lines, not essays.

## Rules
- Record the decision when it is made, not later.
- Never rewrite history — supersede with a new dated entry.
