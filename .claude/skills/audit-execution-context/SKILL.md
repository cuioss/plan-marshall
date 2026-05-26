---
name: audit-execution-context
description: Audit archived plans for execution-manifest correctness against manage-execution-manifest decision-rules and surface dispatch-granularity signals
user-invocable: true
allowed-tools: Bash, Read, Grep
---

# Audit Execution-Context Behavior (project-local)

Re-runs the seven-row decision matrix from
`plan-marshall:manage-execution-manifest/standards/decision-rules.md`
against every archived plan and reports plans whose persisted `execution.toon`
disagrees with the rule the inputs would fire today. Also surfaces the
name-drift signal between the standard's canonical phase-5 candidates
(`quality-gate`, `module-tests`, `coverage`) and project-renamed equivalents.

The skill is **project-local** because it operates on
`.plan/local/archived-plans/` — a directory that only exists in this
meta-project. Consumer projects of plan-marshall have no equivalent corpus.

## Why a script, not a dispatch

Per `extension-api/standards/dispatch-granularity.md` Heuristic 1, the
7-row matrix is a boolean predicate over file-derived inputs. It costs nothing
to evaluate and has no LLM judgement core, so it stays inside the script. The
slash command surface is the LLM-friendly invocation of that script — no
subagent is spawned.

## Enforcement

**Execution mode**: Run the audit script and surface its TOON report verbatim;
do not paraphrase rule names or invent verdicts that the script did not emit.

**Prohibited actions**:
- Do NOT mutate any plan artifact — the audit is read-only against
  `.plan/local/archived-plans/` and `.plan/local/plans/`.
- Do NOT re-derive the decision matrix inline in the chat; if the matrix
  changes, edit `audit.py` and re-run.
- Do NOT fall back to interpreting `solution_outline.md` prose when the
  structured inputs (`references.json`, `status.json::metadata`) are present —
  prose interpretation is non-deterministic and was the source of contradictory
  verdicts in earlier ad-hoc audits.

**Constraints**:
- The script is invoked exactly as written in Step 1 — no PYTHONPATH override,
  no inlined Python, no `find`/`grep` substitutes for the script's own
  filesystem walk.
- When `--plan-id` narrows the scan, the same TOON shape is emitted (single
  row) so downstream tooling can consume both forms uniformly.

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--plan-dir PATH` | optional | Override the default `.plan/local/archived-plans` root. Useful when auditing a vendored snapshot. |
| `--plan-id ID` | optional | Restrict the scan to one archived plan (its directory basename). |
| `--include-active` | optional | Additionally scan `.plan/local/plans/` so in-flight plans are reported alongside archived ones. Active plans without a manifest are reported as `incomplete`, not `drift`. |

## Usage Examples

```bash
/audit-execution-context
```

Walks every archived plan and emits a TOON table with one row per plan.

```bash
/audit-execution-context --plan-id 2026-05-26-fix-1-init-phase-boundary-bootstrap-bug
```

Single-plan audit; useful when a retrospective wants a focused read-out.

```bash
/audit-execution-context --include-active
```

Adds in-flight plans to the scan. In-flight plans that have not yet reached
`phase-4-plan` Step 8b show up under the `incomplete` bucket.

## Workflow

### Step 1: Run the audit script

```bash
python3 .claude/skills/audit-execution-context/scripts/audit.py
```

The script:

1. Walks `.plan/local/archived-plans/{plan_id}/` (and optionally
   `.plan/local/plans/`).
2. Reads `status.json::metadata.change_type` and `…plan_source` (recipe_key
   surrogate), `references.json::scope_estimate`, and the lengths of
   `affected_files[]` / `modified_files[]`.
3. Parses the small fixed-shape `execution.toon` directly (no executor
   PYTHONPATH dependency).
4. Scans `logs/decision.log` for the
   `(plan-marshall:manage-execution-manifest:compose) Rule … fired` line.
5. Re-evaluates the seven-row matrix against the collected inputs and
   compares the derived rule key to the persisted one.
6. Emits a TOON document with one summary block and one
   `rows[N]{plan_id,verdict,reason,expected_rule,actual_rule,change_type,scope,recipe,affected,modified,name_drift}` table.

### Step 2: Interpret the verdict columns

The script bins each plan into exactly one of four verdicts:

| Verdict | Meaning |
|---------|---------|
| `ok` | The persisted `Rule … fired` matches the rule the inputs would fire today. |
| `drift` | The persisted rule disagrees with the re-derivation (either a different rule or no `Rule … fired` line despite compose lines being present). |
| `incomplete` | No `execution.toon` exists — the plan never reached `phase-4-plan` Step 8b. Not a defect of the manifest composer; surfaced so retrospectives can distinguish "manifest wrong" from "manifest never written". |
| `unloggable` | `execution.toon` exists but `decision.log` carries no compose entry. Pre-logging-era plans land here. The manifest is reported alongside the derived expected rule for visual cross-check. |

### Step 3: Inspect the `name_drift` column

The `name_drift` column flags plans whose persisted `phase_5.verification_steps`
list contains zero entries from the standard's canonical set
(`quality-gate`, `module-tests`). On projects that renamed their candidates,
Row 2 / Row 3 / Row 5 in the seven-row matrix intersect against names that no
longer match — silently producing empty `phase_5.verification_steps`. The
column is informational; remediation lives in
`manage-execution-manifest/standards/decision-rules.md` (introduce a
canonical-name alias map) or in the project's `marshal.json` (rename
candidates back to canonical names).

## Critical Rules

- The script is the single source of truth for the re-derived rule key. Do
  not paraphrase or re-implement the matrix in chat.
- `execution.toon` is parsed by a small inline reader (the project's
  `toon_parser` lives behind the executor PYTHONPATH which this skill does not
  load). If the manifest schema changes, update the reader in
  `scripts/audit.py` rather than calling out to the manage-execution-manifest
  script — that would be a dispatch-shaped solution for deterministic work.
- The audit is **read-only**; it never edits `.plan/` files.

## Related

- `plan-marshall:manage-execution-manifest` — the composer itself; this skill
  audits the artefacts it produces.
- `plan-marshall:plan-retrospective` — consumes `execution.toon` and the
  compose decision-log lines; an audit failure here predicts a stale
  retrospective signal.
- `extension-api/standards/dispatch-granularity.md` — the heuristic basis for
  keeping this skill script-shaped rather than dispatch-shaped.
