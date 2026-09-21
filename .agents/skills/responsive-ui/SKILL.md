# Skill: responsive-ui

## Purpose
Ship frontend changes that work on real phones, not just desktop browsers.

## When to use
Any change to `frontend/src/` — pages, components, styling.

## Instructions
1. Reuse existing components and Tailwind tokens before adding new styles.
2. Test widths: **360px, 390px, 768px, desktop**. Check:
   - No horizontal overflow; tables scroll or stack.
   - Touch targets ≥ 44px; tap every visible control.
   - Sticky headers, drawers, and modals behave at each width.
   - No z-index wars; no content hidden behind fixed bars.
3. Keep interaction feedback fast; animate transform/opacity only.
4. Support `prefers-reduced-motion`.
5. Run `npm run build` — it must pass.

## LIMS.Pro frontend notes
- Pages live in `frontend/src/pages/` (Patients, Orders, TechnicianQueue, PathologistQueue, Reports, etc.).
- API client: `frontend/src/lib/api.js` — use `credentials: 'include'` (cookie auth).
- Pagination component: `frontend/src/components/Pagination.js` — wire it wherever lists grow (Patients done partially, Orders pending).

## Rules
- Never claim "mobile works" without checking the three widths.
- UI hiding is not access control — role gating stays server-side.
