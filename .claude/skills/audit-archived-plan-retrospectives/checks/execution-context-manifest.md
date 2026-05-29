# Check: execution-context-manifest

Re-runs the seven-row decision matrix from
`plan-marshall:manage-execution-manifest/standards/decision-rules.md` against
every scanned plan and reports plans whose persisted `execution.toon` disagrees
with the rule the inputs would fire today. Also surfaces the name-drift signal
between the standard's canonical phase-5 candidates (`quality-gate`,
`module-tests`, `coverage`) and project-renamed equivalents.

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
  `phase_5.verification_steps`.
- `logs/decision.log` — the
  `(plan-marshall:manage-execution-manifest:compose) Rule … fired` line that
  records which rule the composer actually applied.

The script re-evaluates the seven-row matrix against the collected inputs and
compares the derived rule key to the persisted one.

## Emitted columns

The check emits one summary block plus a rows table:

```
rows[N]{plan_id,verdict,reason,expected_rule,actual_rule,change_type,scope,recipe,affected,modified,name_drift}
```

| Column | Meaning |
|--------|---------|
| `plan_id` | The scanned plan's directory basename. |
| `verdict` | One of `ok` / `drift` / `incomplete` / `unloggable` (see below). |
| `reason` | Short explanation of the verdict. |
| `expected_rule` | The rule key the inputs would fire today (re-derived). |
| `actual_rule` | The rule key recorded in `decision.log` (or `-` when absent). |
| `change_type` | `status.json::metadata.change_type`. |
| `scope` | `references.json::scope_estimate`. |
| `recipe` | The plan-source / recipe-key surrogate. |
| `affected` | `len(affected_files)`. |
| `modified` | `len(modified_files)`. |
| `name_drift` | `true` when `phase_5.verification_steps` contains zero canonical-set entries (see below). |

## Verdict columns

The script bins each plan into exactly one of four verdicts:

| Verdict | Meaning |
|---------|---------|
| `ok` | The persisted `Rule … fired` matches the rule the inputs would fire today. |
| `drift` | The persisted rule disagrees with the re-derivation (either a different rule, or no `Rule … fired` line despite compose lines being present). |
| `incomplete` | No `execution.toon` exists — the plan never reached `phase-4-plan` Step 8b. Not a defect of the manifest composer; surfaced so retrospectives can distinguish "manifest wrong" from "manifest never written". Active plans scanned via `--include-active` that have not yet reached Step 8b land here. |
| `unloggable` | `execution.toon` exists but `decision.log` carries no compose entry. Pre-logging-era plans land here. The manifest is reported alongside the derived expected rule for visual cross-check. |

## The name_drift column

The `name_drift` column flags plans whose persisted
`phase_5.verification_steps` list contains zero entries from the standard's
canonical set (`quality-gate`, `module-tests`). On projects that renamed their
candidates, Row 2 / Row 3 / Row 5 of the seven-row matrix intersect against
names that no longer match — silently producing an empty
`phase_5.verification_steps`. The column is informational; remediation lives in
`manage-execution-manifest/standards/decision-rules.md` (introduce a
canonical-name alias map) or in the project's `marshal.json` (rename candidates
back to canonical names).

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
- **`name_drift: true`** — surface as a configuration signal; the remediation
  is a config/standard change, not a per-plan fix.

## Critical rules

- The script is the single source of truth for the re-derived rule key. Do not
  paraphrase or re-implement the matrix in chat.
- `execution.toon` is parsed by a small inline reader inside `scripts/audit.py`
  (the project's `toon_parser` lives behind the executor PYTHONPATH which this
  skill does not load). If the manifest schema changes, update the reader in
  `scripts/audit.py` rather than calling out to the manage-execution-manifest
  script — that would be a dispatch-shaped solution for deterministic work.
- This check is read-only; it never edits `.plan/` files.
