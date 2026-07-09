# Check: execution-context-manifest

Re-runs the seven-row decision matrix from
`plan-marshall:manage-execution-manifest/standards/decision-rules.md` against
every scanned plan and reports plans whose persisted `execution.toon` disagrees
with the rule the inputs would fire today. Also surfaces two step-drift signals:
`name_drift` (by resolving each phase-5 step ID to its matrix `role:` in-code and
intersecting the resolved roles against `{quality-gate, module-tests}`, mirroring
the composer's Role-Field Intersection) and `owner_drift` (#852 D6 — by resolving
each phase-6 finalize step ID to its ownership class, orchestrator-owned inline vs
leaf-dispatchable, and flagging a built-in step the canonical finalize roster no
longer recognizes).

The deterministic re-derivation lives in `scripts/audit.py`. This sub-document
is the interpretation guide the orchestrator applies to the rows that check
emits — it does not re-implement the matrix.

## Inputs the check reads

Per scanned plan, the script reads the structured inputs (never
`solution_outline.md` prose):

- `references.json` — `scope_estimate`, and the lengths of `affected_files[]` /
  `modified_files[]`.
- `status.json::metadata` — `change_type` and the plan-source surrogate
  (`plan_source` / `recipe_key`).
- `execution.toon` — the persisted manifest, including
  `phase_5.verification_steps` and `phase_6.steps` (the finalize step roster the
  `owner_drift` derivation classifies).
- `logs/decision.log` — the
  `(plan-marshall:manage-execution-manifest:compose) Rule … fired` line that
  records which rule the composer actually applied.

The script re-evaluates the seven-row matrix against the collected inputs and
compares the derived rule key to the persisted one.

## Emitted columns

The check emits one summary block plus a rows table. The summary block carries
`genuine_signal_count` — the number of rows that are actionable signals (a
`drift` verdict, a populated `name_drift`, or a populated `owner_drift`), distinct
from `name_drift_count` / `owner_drift_count` and the per-verdict counts:

```
rows[N]{plan_id,verdict,severity,reason,expected_rule,actual_rule,change_type,scope,recipe,affected,modified,name_drift,owner_drift}
```

| Column | Meaning |
|--------|---------|
| `plan_id` | The scanned plan's directory basename. |
| `verdict` | One of `ok` / `drift` / `incomplete` / `unloggable` (see below). |
| `severity` | `genuine` (actionable — a `drift` verdict, a populated `name_drift`, or a populated `owner_drift`) or `informational` (`ok` / `incomplete` / `unloggable`). |
| `reason` | Short explanation of the verdict. |
| `expected_rule` | The rule key the inputs would fire today (re-derived). |
| `actual_rule` | The rule key recorded in `decision.log` (or `-` when absent). |
| `change_type` | `status.json::metadata.change_type`. |
| `scope` | `references.json::scope_estimate`. |
| `recipe` | The plan-source / recipe-key surrogate. |
| `affected` | `len(affected_files)`. |
| `modified` | `len(modified_files)`. |
| `name_drift` | Populated when a phase-5 step ID resolves to no matrix `role:` (unresolvable role) or the resolved roles have zero intersection with `{quality-gate, module-tests}` (see below). Empty otherwise. |
| `owner_drift` | Populated when a phase-6 built-in step ID resolves to no ownership class (orchestrator / leaf / hybrid) — the persisted manifest references a finalize step the canonical roster renamed or removed (#852 D6, see below). Empty otherwise. |

## Verdict columns

The script bins each plan into exactly one of four verdicts:

| Verdict | Meaning |
|---------|---------|
| `ok` | The persisted `Rule … fired` matches the rule the inputs would fire today. |
| `drift` | The persisted rule disagrees with the re-derivation (either a different rule, or no `Rule … fired` line despite compose lines being present). |
| `incomplete` | No `execution.toon` exists — the plan never reached `phase-4-plan` Step 8b. Not a defect of the manifest composer; surfaced so retrospectives can distinguish "manifest wrong" from "manifest never written". Active plans scanned via `--include-active` that have not yet reached Step 8b land here. |
| `unloggable` | `execution.toon` exists but `decision.log` carries no compose entry. Pre-logging-era plans land here. The manifest is reported alongside the derived expected rule for visual cross-check. |

## The name_drift column

The `name_drift` column is computed by role resolution, not literal-name
matching. For each step ID in `phase_5.verification_steps`, the script resolves
the step's matrix `role:` **in-code** — no standards `.md` file is read (the
per-step `phase-5-execute/standards/{name}.md` role-files were deleted in favor
of the single parameterized canonical-verify step). Resolution mirrors the
composer's `_role_of`:

- **Canonical-verify steps** of the shape `default:verify:{canonical}` (or the
  bare `verify:{canonical}` form) derive the role from the trailing
  `{canonical}` segment via the canonical→role table (e.g.
  `default:verify:quality-gate` → `quality-gate`, `default:verify:module-tests`
  / `default:verify:verify` → `module-tests`, `default:verify:coverage` →
  `coverage`). The single source of this mapping is
  `marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/canonical_verify.md`
  § "derived role", copied in-code by both the composer and `scripts/audit.py`.
- **Legacy bare default-step names** (`quality_check` → `quality-gate`,
  `build_verify` → `module-tests`, `coverage_check` → `coverage`) resolve via an
  in-code back-compat table for archived plans whose manifests predate the
  parameterized form.

The resolved roles are intersected against `{quality-gate, module-tests}`,
mirroring the composer's Role-Field Intersection
(`manage-execution-manifest/standards/decision-rules.md` § "Role-Field
Intersection").

Genuine drift is exactly one of:

- **Unresolvable role** — a step ID whose `{canonical}` segment is unknown (not
  in the canonical→role table) or whose bare name is not a recognized legacy
  default-step name. The resolver degrades to "unresolved" rather than crashing.
- **Zero intersection** — a non-empty `phase_5` whose resolved roles do not
  include `quality-gate` or `module-tests`.

The step IDs `default:verify:quality-gate` and `default:verify:module-tests`
(and the legacy `quality_check` / `build_verify`) are CORRECT — they resolve to
roles `quality-gate` and `module-tests` and are NEVER flagged. There is no
"renamed name" to alias back: a well-composed manifest using the canonical step
IDs always intersects, regardless of the surface step-ID spelling, because the
intersection is on roles. A populated `name_drift` therefore points at a real
composition fault (an unknown step ID, or a manifest carrying steps that do not
verify code), not a cosmetic rename.

## The owner_drift column (#852 D6 step-ownership)

`name_drift` covers the phase-5 verify roster (which verification steps a manifest
carries); `owner_drift` extends the same re-derivation idea to the phase-6
finalize roster, covering **step-ownership**. #852's D6 step-ownership
canonicalization split every finalize step into two ownership classes —
ORCHESTRATOR-OWNED (inline) steps that run synchronously in the main context
(pure scripts / trivial orchestration: `push`, `ci-verify`, `record-metrics`,
`archive-plan`, …) and LEAF-DISPATCHABLE steps dispatched under
`Task: execution-context-{level}` because they carry an LLM core (`create-pr`,
`automated-review`, `sonar-roundtrip`, the review / simplify / security-audit
sweeps, …), plus the one hybrid step (`architecture-refresh`: Tier-0 inline +
Tier-1 fan-out).

**Derivation, not a persisted field.** The manifest carries NO per-step `owner`
field — `execution.toon` records only the bare `phase_6.steps` ID list. The check
therefore DERIVES each step's ownership from the canonical finalize roster
(`phase-6-finalize/SKILL.md` § "Dispatched workflows vs inline steps"), the single
source of truth, via `_resolve_step_owner` — exactly as `name_drift` derives
phase-5 roles in-code rather than reading a persisted role. Both maps
(`_ORCHESTRATOR_OWNED_STEPS`, `_LEAF_DISPATCHED_STEPS`, `_HYBRID_OWNED_STEPS`,
`_EXTERNAL_STEP_OWNER`) are keyed by the bare step name.

Genuine `owner_drift` is exactly a **built-in** (`default:`-prefixed or bare)
phase-6 step ID whose ownership cannot be resolved — the persisted manifest
references a finalize step the canonical roster renamed or removed. `project:` /
`bundle:skill` external steps are project-defined and resolve via the known
meta-project map; an unknown external step resolves to "no class" WITHOUT flagging
drift (a project step is not a canonical-roster fault). A well-composed manifest
using the canonical finalize steps always resolves and is NEVER flagged.

## How the orchestrator interprets the rows

- **`ok`** — no action; the manifest matches the re-derivation.
- **`drift`** — the manifest composer produced a manifest that the current rule
  set would not reproduce. Surface the row and treat it as a candidate
  systemic signal: a recurring drift across plans (see
  [`recurring-pattern-detector.md`](recurring-pattern-detector.md)) flows into
  the three-gate lesson-filing path.
- **`incomplete`** — informational; distinguishes "manifest wrong" from
  "manifest never written". No lesson candidate.
- **`unloggable`** — informational; cross-check the reported manifest against
  the derived `expected_rule` visually. No lesson candidate unless the visual
  cross-check reveals a genuine mismatch.
- **populated `name_drift`** (`severity: genuine`) — a real composition fault:
  either a step ID whose `role:` cannot be resolved, or a manifest whose phase-5
  steps resolve to no quality-gate/module-tests role. Adjudicate per-row against
  the `name_drift` reason and treat a recurring shape as a candidate systemic
  signal (see [`recurring-pattern-detector.md`](recurring-pattern-detector.md)).
  It is NOT a config/rename signal — there is nothing to rename back.
- **populated `owner_drift`** (`severity: genuine`) — a phase-6 built-in finalize
  step the canonical roster no longer recognizes (#852 D6). The persisted manifest
  references a renamed or removed finalize step; the derived ownership class is
  therefore unresolvable. Adjudicate against the `owner_drift` reason and read a
  recurring shape as a roster-drift systemic signal. Like `name_drift`, it is NOT a
  rename-back signal — the fault is that the manifest carries a step the current
  finalize roster does not define.

The `severity` column is the precision gate: only `genuine` rows (a `drift`
verdict, a populated `name_drift`, or a populated `owner_drift`) are actionable.
`informational` rows (`ok` / `incomplete` / `unloggable`) and the
`genuine_signal_count` summary let the orchestrator separate real findings from
expected noise.

## Critical rules

- The script is the single source of truth for the re-derived rule key. Do not
  paraphrase or re-implement the matrix in chat.
- `execution.toon` is parsed by a small inline reader inside `scripts/audit.py`
  (the project's `toon_parser` lives behind the executor PYTHONPATH which this
  skill does not load). If the manifest schema changes, update the reader in
  `scripts/audit.py` rather than calling out to the manage-execution-manifest
  script — that would be a dispatch-shaped solution for deterministic work.
- This check is read-only; it never edits `.plan/` files.
