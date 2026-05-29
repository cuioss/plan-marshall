---
name: audit-archived-plan-retrospectives
description: Audit archived plans across nine retrospective checks — execution-manifest correctness, quality-verification findings, metrics anomalies, cross-plan recurring patterns, token-efficiency trend, scope-estimate accuracy, PR-merge velocity, and task-count efficiency — file lessons through the three-gate policy, and dormate reviewed plans
user-invocable: true
allowed-tools: Bash, Read, Grep, Write, AskUserQuestion
---

# Audit Archived Plan Retrospectives (project-local)

Multi-check retrospective auditor over the archived-plan corpus. The skill is
the LLM-driven orchestration narrative; `scripts/audit.py` is the deterministic
computation core. The orchestrator selects which checks to run, surfaces each
check's script-computed TOON verbatim, drives lesson filing through the
three-gate `lesson-creation-policy.md` sequence, and runs the interactive
dormation step that relocates reviewed plans to `.plan/temp/dormated-plans/`.

The skill is **project-local** because it operates on
`.plan/local/archived-plans/` — a directory that only exists in this
meta-project. Consumer projects of plan-marshall have no equivalent corpus.

## Hybrid design: script computes, LLM orchestrates

`scripts/audit.py` performs all deterministic per-plan and cross-plan
computation and emits each check's rows as bespoke TOON. `SKILL.md` (this body)
is the LLM half: it chooses the checks, reads the emitted rows, decides whether
a surfaced signal warrants a lesson, and confirms the destructive dormation
move via `AskUserQuestion`. The boundary is strict — the script computes and
emits; the LLM interprets, files lessons, and confirms destructive moves. The
script never mutates a plan artifact except the explicitly-confirmed dormation
move.

Per `extension-api/standards/dispatch-granularity.md` Heuristic 1, every check's
core computation is a deterministic predicate over file-derived inputs, so it
stays inside the script rather than spawning a subagent. The slash command is the
LLM-friendly invocation of that script plus the orchestration this body
describes — no subagent is spawned.

## Enforcement

**Execution mode**: Select the checks to run, invoke the audit script for each
selected check, and surface its TOON report verbatim; do not paraphrase rule
names, anomaly classes, or verdicts that the script did not emit.

**Prohibited actions**:
- Do NOT mutate any plan artifact other than the explicitly-confirmed dormation
  move. Every check is read-only against `.plan/local/archived-plans/` and
  `.plan/local/plans/`.
- Do NOT re-derive any check's computation inline in the chat; if a check's
  logic changes, edit `scripts/audit.py` and re-run.
- Do NOT fall back to interpreting `solution_outline.md` prose when the
  structured inputs (`references.json`, `status.json::metadata`,
  `metrics.toon`, `execution.toon`, `tasks/TASK-*.json`,
  `artifacts/findings/*.jsonl`) are present — prose interpretation is
  non-deterministic and was the source of contradictory verdicts in earlier
  ad-hoc audits.
- Do NOT run the dormation move without an explicit user confirmation obtained
  via `AskUserQuestion`; the script's move function refuses to run unless the
  orchestrator passes the confirmed flag.
- Do NOT file a lesson without first running the three-gate policy
  (`lesson-creation-policy.md`) — dedup, active-plan check, then create.

**Constraints**:
- The script is invoked exactly as written in the workflow steps — no
  PYTHONPATH override, no inlined Python, no `find`/`grep` substitutes for the
  script's own filesystem walk.
- When `--plan-id` narrows the scan, the same TOON shape is emitted (single
  row per check) so downstream tooling can consume both forms uniformly.
- When `--check {name}` narrows to one check, only that check's TOON block is
  emitted.

## Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--plan-dir PATH` | optional | Override the default `.plan/local/archived-plans` root. Useful when auditing a vendored snapshot. |
| `--plan-id ID` | optional | Restrict the scan to one archived plan (its directory basename). |
| `--include-active` | optional | Additionally scan `.plan/local/plans/` so in-flight plans are reported alongside archived ones. Active plans without a manifest are reported as `incomplete`, not `drift`. |
| `--check NAME` | optional | Run a single check instead of all. Valid names: `execution-context-manifest`, `quality-verification-report`, `metrics`, `recurring-pattern-detector`, `token-efficiency-trend`, `scope-estimate-accuracy`, `pr-merge-velocity`, `task-count-efficiency`. Default: run every check. |

## Available checks

Each check is documented in a self-contained sub-document under `checks/`. The
sub-document records what `scripts/audit.py` computes for that check, the inputs
it reads, the emitted columns, and how the orchestrator interprets and acts on
the rows.

| Check | Sub-document | Surfaces |
|-------|--------------|----------|
| Execution-manifest correctness | [`checks/execution-context-manifest.md`](checks/execution-context-manifest.md) | Persisted `execution.toon` vs the re-derived seven-row rule; the `name_drift` signal. |
| Quality-verification report | [`checks/quality-verification-report.md`](checks/quality-verification-report.md) | Findings present, proposed lessons, and whether each was already filed. |
| Metrics anomalies | [`checks/metrics.md`](checks/metrics.md) | Disproportionate token usage, incomplete recordings, impossible values, optimization signals. |
| Recurring-pattern detector | [`checks/recurring-pattern-detector.md`](checks/recurring-pattern-detector.md) | Cross-plan finding signatures appearing in N≥3 plans as systemic signals. |
| Token-efficiency trend | [`checks/token-efficiency-trend.md`](checks/token-efficiency-trend.md) | Chronological tokens-per-phase regression across the corpus. |
| Scope-estimate accuracy | [`checks/scope-estimate-accuracy.md`](checks/scope-estimate-accuracy.md) | Declared `scope_estimate` vs actual affected/modified file count. |
| PR-merge velocity | [`checks/pr-merge-velocity.md`](checks/pr-merge-velocity.md) | PR open-to-merge duration; long-review-cycle flagging. |
| Task-count efficiency | [`checks/task-count-efficiency.md`](checks/task-count-efficiency.md) | Under-decomposed / over-decomposed task-count outliers. |

## Usage Examples

```bash
/audit-archived-plan-retrospectives
```

Runs every check over every archived plan and emits one TOON block per check.

```bash
/audit-archived-plan-retrospectives --plan-id 2026-05-26-fix-1-init-phase-boundary-bootstrap-bug
```

Single-plan audit across all checks; useful when a retrospective wants a focused
read-out.

```bash
/audit-archived-plan-retrospectives --check metrics
```

Runs only the metrics-anomaly check across the corpus.

```bash
/audit-archived-plan-retrospectives --include-active
```

Adds in-flight plans to the scan. In-flight plans that have not yet reached
`phase-4-plan` Step 8b show up under the `incomplete` bucket for checks that
depend on `execution.toon`.

## Workflow

### Step 1: Select the checks to run

Default to all checks. When the user supplies `--check {name}`, run only that
check. The check names are listed in the **Available checks** table above; each
maps to a `checks/{name}.md` sub-document and a `--check {name}` value the script
accepts.

### Step 2: Run the audit script for the selected checks

```bash
python3 .claude/skills/audit-archived-plan-retrospectives/scripts/audit.py [--plan-dir PATH] [--plan-id ID] [--include-active] [--check NAME]
```

The script walks `.plan/local/archived-plans/{plan_id}/` (and optionally
`.plan/local/plans/`), reads the structured inputs each check requires, computes
the per-plan and cross-plan signals, and emits one bespoke-TOON block per check.
Surface each emitted block verbatim and interpret its rows using the
corresponding `checks/{name}.md` sub-document.

### Step 3: Interpret each check's rows

For each emitted check block, open the matching `checks/{name}.md` sub-document
and apply its interpretation guide. The sub-documents are the single source of
truth for what each column means and which row states warrant action; this body
does not restate them.

### Step 4: File lessons through the three-gate policy

Two check classes emit candidate lesson signatures: the quality-verification
report's unfiled proposed lessons and the recurring-pattern detector's systemic
signals at the 3+ threshold. For each candidate signature, run the canonical
three-gate sequence from `plan-marshall:manage-lessons`'s
`lesson-creation-policy.md`:

1. **Gate 1 — dedup**: search the lessons corpus for an existing lesson covering
   the same signature. On `merge_into` / `already_closed`, extend the existing
   lesson instead of filing a new one.
2. **Gate 2 — active-plan check**: if an active plan already covers the fix, fold
   the signal into that plan rather than filing a lesson.
3. **Gate 3 — create**: only when Gates 1 and 2 both clear, allocate a lesson
   file via `manage-lessons add` and write the body to the returned `path`.

The quality-verification check already cross-checks each proposed lesson against
the lessons corpus and the archived-plan corpus, so a candidate it marks as
"already filed" or "covered by archived plan {id}" MUST NOT be re-filed.

### Step 5: Interactive dormation

After the audit has been reviewed, offer to dormate each reviewed plan —
relocating its directory from `.plan/local/archived-plans/{plan_id}/` to
`.plan/temp/dormated-plans/{plan_id}/`. The move is destructive, so confirmation
is mandatory:

1. For each plan the user wants to dormate, raise an `AskUserQuestion`
   confirming the move (the confirmation is owned here, in the LLM body — never
   delegated to the script).
2. Only on explicit confirmation, invoke the script's confirmed dormation move:

   ```bash
   python3 .claude/skills/audit-archived-plan-retrospectives/scripts/audit.py --dormate {plan_id} --confirmed
   ```

   Without `--confirmed`, the script's move function is inert and refuses to
   relocate anything.

## Critical Rules

- The script is the single source of truth for every check's computed rows. Do
  not paraphrase or re-implement any check in chat.
- `execution.toon`, `metrics.toon`, and the other structured inputs are parsed
  by small inline readers inside `scripts/audit.py` (the project's
  `toon_parser` lives behind the executor PYTHONPATH which this skill does not
  load). If a manifest or metrics schema changes, update the reader in
  `scripts/audit.py` rather than calling out to a `manage-*` script — that would
  be a dispatch-shaped solution for deterministic work.
- The audit is **read-only** against all plan artifacts except the
  explicitly-confirmed dormation move.
- Lesson filing always passes through the three-gate policy — never file
  directly from a surfaced signal.

## Related

- `plan-marshall:manage-execution-manifest` — the composer audited by the
  execution-context-manifest check.
- `plan-marshall:manage-lessons` — the lessons corpus and the three-gate
  `lesson-creation-policy.md` that Step 4 follows.
- `plan-marshall:plan-retrospective` — consumes `execution.toon`, `metrics.toon`,
  and the compose decision-log lines; audit failures here predict stale
  retrospective signals.
- `extension-api/standards/dispatch-granularity.md` — the heuristic basis for
  keeping this skill script-shaped rather than dispatch-shaped.
