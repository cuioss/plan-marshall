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

**Mechanism:** a boolean `minimal` marker on a `skills_by_profile.{profile}` block. `"minimal": true`
positively declares an empty profile deliberate; an empty profile block WITHOUT it is the distinct
**undeclared-empty** state.

**Reasoning (recorded per D2):** the marker aligns with the store's existing fail-closed,
positive-marker posture — the graph's zero-edge disambiguation (`resolver_count`) and the `files`
inventory (`truncated` / `elided`), both of which distinguish "answered nothing" from "was not looked
at" *without inferring intent from cardinality* (`architecture-persistence.md` lines 568–573). It is
**not a third parallel vocabulary mechanism** (the out-of-scope drift the plan warns against): it is a
single boolean predicate on the existing profile block, read by the same read-path guard that already
reports `skills_by_profile` health. What makes the *next* unmarked-empty profile detectable: the guard
checks each present profile block for `defaults == [] and optionals == [] and minimal is not True` and
emits the named condition; only a positive `minimal: true` silences it.

**Fail-closed declaration:** `_validate_skills_by_profile_structure` (`_cmd_enrich.py`, the enrich
write path) now flags a non-boolean `minimal` (`"minimal": "true"`, `1`) as malformed. A malformed
declaration leaves the profile in the undeclared-empty state — it cannot silently launder the signal
(`is True` identity check in `_profile_declares_minimal`).

**Schema documented:** `architecture-persistence.md` § "Skills by Profile" now carries the three-state
table (populated / declared-minimal / undeclared-empty) and the read-path condition.

*Done:* the declaration exists in the schema and the undeclared empty is a distinct representable
state. Commit: guard/schema/validator commit below.

### D3 — report the named condition at allocation time (non-fatal)

`detect_stale_skills_by_profile` (`_cmd_client_query.py`) now emits, per present-but-empty **undeclared**
profile, the named condition *"module '{M}': profile '{P}' resolves no skills and is not declared
minimal — set \"minimal\": true …"*. It is surfaced by `_emit_skills_by_profile_staleness_warning` as a
non-blocking `[STALENESS]` WARNING on the `architecture module` read exercised by phase-4-plan's module
pre-fetch — **at allocation time, and it does not abort the run** (the guard returns a list of strings;
its emitter swallows logging exceptions). A `minimal: true` profile emits nothing.

The LLM-side consumer was aligned in lock-step: **phase-4-plan Step 5** now short-circuits a
declared-minimal profile (no warning, no Q-Gate finding) and re-words the undeclared-empty branch as an
*UNRESOLVED* condition that points at both remedies (enrich, or declare `minimal: true`). The scenario
table and "Profile Not in Module" section were updated to match.

*Done:* the condition surfaces in allocation output and is non-fatal.

### D4 — a test that fails today, in both directions

Added to `test/plan-marshall/manage-architecture/test_skills_by_profile_staleness_guard.py`:

- `test_warns_on_unresolved_undeclared_empty_profile` — a populated `implementation` + empty,
  undeclared `module_testing` surfaces the named condition. **Empty-case assertion.**
- `test_no_warning_on_declared_minimal_profile` — the same empty profile with `minimal: true` surfaces
  nothing.
- `test_declared_minimal_and_unmarked_empty_are_distinguishable` — both directions in one assertion
  (the vacuous-guard trap: an empty-only assertion cannot detect the escape hatch swallowing the
  signal).

**Pre-fix failure OBSERVED and recorded** (D4 / Verification requirement). Running the tests against the
un-patched guard:

```
FAILED ... test_warns_on_unresolved_undeclared_empty_profile
  AssertionError: []
  assert False = any(<generator ...>)
FAILED ... test_declared_minimal_and_unmarked_empty_are_distinguishable
  assert (False)
2 failed, 7 passed
```

The empty-case assertion fails with `AssertionError: []` — the pre-fix guard returns `[]` for the
undeclared-empty profile, exactly the invisibility D1 confirmed. Post-fix: **9 passed**.

Two enrich-validator tests were also added (`test_enrich_skills_by_profile_declared_minimal_persists_without_warnings`,
`test_enrich_skills_by_profile_warns_on_non_boolean_minimal`) covering the fail-closed `minimal`
validation.

*Done:* both assertions exist and the empty-case pre-fix failure was observed.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` at gate time: two production scripts
(`_cmd_client_query.py`, `_cmd_enrich.py`) and two test files changed → Python footprint present →
build required. `UV_HTTP_TIMEOUT=600 ./pw verify plan-marshall` (all three sub-steps, scoped to the
bundle where every changed file lives): **SUCCESS** — mypy(production) 278 files, ruff, SPDX,
mypy(test) 588 files, module-tests **16446 passed, 1 skipped** (`0:08:09`). No `uv.lock` churn (3.12
interpreter matched the floor).

## Findings

**Verification sub-agent** (independent, read-only; general-purpose). Verdict: implementation matches
the plan — all four deliverables present, correctly specified, test-covered, no undeclared collateral
change. Findings:

| # | Source | Description | Disposition |
|---|--------|-------------|-------------|
| 1 | sub-agent (beyond-diff sweep) | `_cmd_client_query.py` module-section comment (block above the guard) still enumerated only the two-signal (stale / missing) model, omitting the new unresolved-profile signal. | **Fixed** — comment rewritten to name all three signals. |
| 2 | sub-agent (beyond-diff sweep) | `_emit_skills_by_profile_staleness_warning` docstring said "stale or missing", omitting the unresolved signal. | **Fixed** — docstring now says "stale, missing, or unresolved" and cross-references the guard. |
| 3 | sub-agent (beyond-diff sweep) | `get_module_info` call-site comment said "stale (retired notations) or missing entirely", omitting the unresolved signal. | **Fixed** — comment now names the unresolved-profile case. |
| 4 | sub-agent (minor) | phase-4-plan scenario-table row read "Profile empty/absent, declared minimal" — an *absent* profile has no block to carry `minimal: true`, so that combination is unreachable. | **Fixed** — reworded to "Profile present but empty, declared minimal" / "Profile empty or absent, NOT declared minimal". |
| 5 | sub-agent (minor, out of scope) | `_cmd_client_render.py` renders per-profile skill *counts*, so declared-minimal and undeclared-empty both render as `0 skills` — the render surface does not reflect the distinction. | **Rejected (out of scope)** — a count summary, not a false claim; the plan scoped the distinction to the guard/allocation surface, not the render. Recorded as residue. |
| 6 | sub-agent (minor, out of scope) | A contradictory `{"defaults":[x], "minimal": true}` is treated as populated by the guard but emptied by phase-4-plan Step 5 (which checks `minimal` first). | **Rejected (out of scope)** — nonsensical input; neither the plan nor the closed-vocabulary posture asks to reconcile a `minimal` flag on a populated profile. Recorded as residue. |

Findings 1–3 are three instances of one defect kind (old two-state model restatement), recorded per
instance. After fixes, `./pw quality-gate plan-marshall` re-ran clean (mypy 278 files, ruff, SPDX);
the fixes are comment/docstring/table-wording only — no logic or test behavior changed.

**CI findings:** _pending PR._

**PR review findings:** _pending PR._

## Reviewer participation

Expected reviewer population, derived from configuration — the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc
(cross-named by `.github/workflows/pr-agent.yml`):

| Reviewer (`author_login`) | Verdict (`reviewed` / `rate-limited` / `silent`) | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` (pr-agent) | _pending PR_ | — |
| `coderabbitai` (coderabbit) | _pending PR_ | — |
| `sourcery-ai` (sourcery) | _pending PR_ | — |

Coverage: _pending PR_ (of 3).

## Cost

_pending_

## Contract check (Step 9)

_pending_

## What have we learned (Step 9)

_pending_

## Residue

_pending_
