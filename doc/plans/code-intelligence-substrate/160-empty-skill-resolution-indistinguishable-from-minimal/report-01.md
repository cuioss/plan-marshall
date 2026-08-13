# Run report — 160-empty-skill-resolution-indistinguishable-from-minimal (run 01)

**Date (UTC):** 2026-08-13    **Branch:** claude/empty-skill-resolution-h67nvw    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

- `plan-marshall:ref-code-quality` (always) — read from bundle path.
- `pm-plugin-development:plugin-script-architecture` (always) — read from bundle path.
- `plan-marshall:persona-implementer` — production-code work identity.
- `pm-dev-python:python-core` — Python production code.
- `pm-dev-python:pytest-testing` — Python tests.

Plugin `Skill:` notation was not attempted; skills were read directly by bundle path (the route that
always works in a fresh cloud clone).

## Deliverables

### D1 — GATE: re-ground against the current tree (mutates nothing)

**Resolution site named (with symbol):**
`detect_stale_skills_by_profile(module_name, skills_by_profile, is_live)` in
`marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_query.py`
(lines 448–473), invoked at allocation time via `_emit_skills_by_profile_staleness_warning`
(same file, line 489) on the `architecture module` read path (`get_module_info`, line 533). This read
is exercised during **phase-4-plan Step 5** (`marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md`,
lines 298–323), which pre-fetches `architecture module --module {D.module}` and extracts
`skills_by_profile.{profile}` to populate each task's `skills[]`. The per-module inventory schema is
`skills_by_profile` in `_cmd_enrich.py` (writer `enrich_skills_by_profile`, validator
`_validate_skills_by_profile_structure`, lines 184–213), documented in
`manage-architecture/standards/architecture-persistence.md` § "Skills by Profile".

**Indistinguishability — CONFIRMED against the current tree:**

The read-path guard's only emptiness check is the *whole-map* branch
`if not skills_by_profile: return [... "missing or empty"]` (line 465). A **per-profile** empty
resolution — a module whose map is `{"implementation": {"defaults": [x]}, "module_testing": {"defaults": [], "optionals": []}}`
— produces **zero** signal: the map is non-empty so the missing/empty branch does not fire, and the
empty `module_testing` block contributes no notations so the stale-notation branch does not fire
either. The function returns `[]`. There is furthermore **no field** by which a profile can declare
deliberate minimality, so an empty-because-unresolved profile and a deliberately-minimal one are
byte-identical to this function. The masking effect the plan describes is reproduced exactly: the two
causes converge on one indistinguishable observable (an empty `skills[]` degrading to the persona
floor added by phase-4-plan's Persona-Skill Augmentation, `SKILL.md` line 356).

**Closed-vocabulary posture confirmed** (D2 alignment target): the architecture store already defends
"answered nothing" vs "was not looked at" as a *positive marker, never inferred from cardinality* —
the `architecture graph` zero-edge disambiguation (`resolver_count: N` + `edge_count: 0` = "ran, found
nothing" vs `resolver_count: 0` = "no capability", `architecture-persistence.md` lines 568–573,
explicitly "the same fail-closed reporting discipline the `files` inventory applies via
`truncated`/`elided`") and the closed, validated `type` vocabulary (`CONCEPT_TYPES`). Plan 150
(concept model) names these as "the fail-closed detector posture and the closed-vocabulary posture two
sibling plans exist to defend." D2 aligns with them rather than inventing a third mechanism.

*Verdict:* confirmed — proceed with D2/D3/D4 against the named site.

### D2 — make the two states distinguishable in the inventory

_in progress_

### D3 — report the named condition at allocation time (non-fatal)

_in progress_

### D4 — a test that fails today, in both directions

_in progress_

## Build gate

_pending_

## Findings

_pending_

## Reviewer participation

_pending_

## Cost

_pending_

## Contract check (Step 9)

_pending_

## What have we learned (Step 9)

_pending_

## Residue

_pending_
