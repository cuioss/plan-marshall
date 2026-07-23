---
name: plan-marshall-manage-findings
description: Unified JSONL storage for plan-scoped findings, phase-scoped Q-Gate findings, and component assessments
compatibility: Adapted from plan-marshall marketplace (Claude Code native)
---

# Manage Findings

Unified storage for plan-level findings, phase-scoped Q-Gate findings, and component assessments. Findings and Q-Gate share the same type taxonomy, resolution model, and severity values. Assessments use a separate certainty/confidence model for component evaluations.

> **Architectural context**: This SKILL.md documents the storage layout and CLI surface. For the end-to-end producer→store→consumer→gate pipeline that connects every quality signal (PR review comments, Sonar issues, build / test / lint failures, Q-Gate findings) to this store and the `pending_findings_blocking_count` invariant, see [`ref-workflow-architecture/standards/findings-pipeline.md`](../ref-workflow-architecture/standards/findings-pipeline.md).

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error response patterns.

**Skill-specific constraints:**
- Only valid resolution values: `pending`, `fixed`, `suppressed`, `accepted`, `taken_into_account`, `rejected`
- Plan findings and Q-Gate findings use different command prefixes (direct vs `qgate`)
- Assessment commands use the `assessment` prefix
- Q-Gate deduplication is automatic; do not add duplicate findings manually
- Assessment confidence values must be numeric (0-100)

## Scope Distinction

| Scope | Storage | Lifecycle |
|-------|---------|-----------|
| **Plan findings** | `.plan/plans/{plan_id}/artifacts/findings/{type}.jsonl` (one per type) | Long-lived, promotable |
| **Q-Gate findings** | `.plan/plans/{plan_id}/artifacts/findings/qgate-{phase}.jsonl` | Per-phase, not promotable |
| **Assessments** | `.plan/plans/{plan_id}/artifacts/findings/assessments.jsonl` | Working data, read-only after outline |

Plan findings are working data during plan execution. Notable findings are promoted to project-level at `6-finalize`. Q-Gate findings track per-phase verification issues. Assessments track component evaluations with certainty/confidence classifications.

## Storage Structure

All finding-related JSONL files live under a single `findings/` subdirectory. Plan findings are split per type — each value of the `type` field gets its own file, and queries merge across files transparently:

```text
.plan/plans/{plan_id}/
└── artifacts/
    └── findings/
        ├── assessments.jsonl       # Component assessments
        ├── bug.jsonl               # Plan finding — type: bug
        ├── improvement.jsonl       # Plan finding — type: improvement
        ├── anti-pattern.jsonl
        ├── triage.jsonl
        ├── tip.jsonl
        ├── insight.jsonl
        ├── best-practice.jsonl
        ├── build-error.jsonl
        ├── test-failure.jsonl
        ├── lint-issue.jsonl
        ├── sonar-issue.jsonl
        ├── pr-comment.jsonl
        ├── qgate-2-refine.jsonl    # Per-phase Q-Gate findings
        ├── qgate-3-outline.jsonl
        ├── qgate-4-plan.jsonl
        ├── qgate-5-execute.jsonl
        └── qgate-6-finalize.jsonl
```

Per-type files are created lazily — only types that have been added produce a file. The `list` command transparently merges across all per-type files (in canonical type order); `get`/`resolve`/`promote` locate the owning file by `hash_id`. The CLI surface is unaffected by the per-type split.

See [standards/jsonl-format.md](standards/jsonl-format.md) for the complete storage layout and per-type file list.

## Finding Types

Types: `bug`, `improvement`, `anti-pattern`, `triage`, `tip`, `insight`, `best-practice`, `build-error`, `test-failure`, `lint-issue`, `sonar-issue`, `pr-comment`

Resolutions: `pending`, `fixed`, `suppressed`, `accepted`, `taken_into_account`, `rejected`

The `rejected` resolution is set by the validity-verification ([ext-point-verify](../extension-api/standards/ext-point-verify.md)) stage when it refutes a finding as a false positive; like `fixed` / `accepted`, it is non-pending and never blocks the findings gate.

Severities: `error`, `warning`, `info` (default: `warning`)

See [standards/jsonl-format.md](standards/jsonl-format.md) for the complete type taxonomy with promotion targets, resolution semantics, severity values, and the type selection guide.

## CLI Commands

**Parser architecture**: This script uses a two-level subparser pattern. Top-level subcommands (`add`, `list`, `get`, `resolve`, `promote`) handle plan-scoped findings directly. The `qgate` subcommand introduces a second parser level with its own subcommands (`qgate add`, `qgate list`, `qgate resolve`, `qgate clear`). The `assessment` subcommand introduces a third command group (`assessment add`, `assessment list`, `assessment get`, `assessment clear`). This mirrors the three storage scopes in the CLI surface.

### Plan-Scoped Finding Commands

```bash
# Add finding
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  add --plan-id {plan_id} --type {type} --title {title} --detail DETAIL \
  [--file-path PATH] [--line N] [--component C] \
  [--module M] [--rule R] [--severity S]

# List findings (per-plan; add --include-qgate to merge pending Q-Gate findings)
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  list --plan-id {plan_id} [--type T] [--resolution R] \
  [--promoted BOOL] [--file-pattern PATTERN] [--include-qgate]

# Get single finding
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  get --plan-id {plan_id} --hash-id {hash_id}

# Resolve finding
# {resolution} ∈ {pending, fixed, suppressed, accepted, taken_into_account, rejected}.
# Use --resolution rejected when the validity-verification (ext-point-verify) stage
# refutes the finding as a false positive (non-pending; never reaches triage).
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  resolve --plan-id {plan_id} --hash-id {hash_id} --resolution {resolution} [--detail DETAIL]

# Promote finding
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  promote --plan-id {plan_id} --hash-id {hash_id} --promoted-to {promoted_to}

# Ingest quarantined raw_input free-text (one batched validate_struct pass)
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  ingest --plan-id {plan_id}
```

#### Batched `raw_input` ingestion (`ingest`)

Producers file untrusted free-text under a quarantined `raw_input.{field}` sub-object; the top-level record fields stay clean-by-construction. The `ingest` verb runs ONE deterministic batched pass over every pending finding (per-plan + per-phase Q-Gate): it validates each finding's `raw_input` mapping through the `validate_struct` `finding` schema (the single containment boundary — additionalProperties:false + per-field `maxLength` clamping + domain allowlist) and, on `status: success`, promotes the clamped values to the top-level fields of the same name (leaving `raw_input.*` in place for audit). A validator rejection resolves the finding as `rejected` (recording the violation in `resolution_detail`) rather than promoting. The invariant: no top-level field is ever populated from an un-validated `raw_input` value, so the top-level surface the triage pass reads is clean-by-construction.

#### Unified read surface (`--include-qgate`)

By default `list` returns only the per-plan findings store (the per-type `{type}.jsonl` files). Passing `--include-qgate` merges the **pending** per-phase Q-Gate findings — across every phase in the Q-Gate phase set — into the same result set, so a caller can retrieve both the per-plan findings and the in-flight Q-Gate findings in a single read. Only Q-Gate records whose `resolution == 'pending'` are merged; resolved Q-Gate findings are never surfaced through this read. The `--type` and `--file-pattern` filters apply to both slices for parity; the `--resolution` and `--promoted` filters apply to the per-plan slice only (the Q-Gate slice is implicitly `pending`).

The merged response is shape-compatible with the default `list` output and adds three provenance markers — `qgate_included: true`, `plan_count`, and `qgate_count` — so consumers can tell how many findings came from each store (see **Output Format** below). The unified query is the read surface `verification-feedback.md` and `triage.md` consume for the per-plan finding sweep. See the `## Canonical invocations` → `list` section below for the authoritative `--include-qgate` argparse surface.

### Q-Gate Commands

Per-phase Q-Gate findings for the unified findings-iteration model across phases 2-7.

```bash
# Add Q-Gate finding
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate add --plan-id {plan_id} --phase {phase} --source {qgate|user_review} \
  --type {type} --title {title} --detail {detail} \
  [--file-path PATH] [--component C] [--severity S] [--iteration N]

# List Q-Gate findings
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate list --plan-id {plan_id} --phase {phase} \
  [--resolution R] [--source S] [--iteration N]

# Resolve Q-Gate finding
# {resolution} accepts rejected too — a refuted Q-Gate finding closes non-pending
# and is excluded from the unified (--include-qgate) gate read.
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate resolve --plan-id {plan_id} --hash-id {hash_id} --resolution {resolution} --phase {phase} \
  [--detail DETAIL]

# Clear Q-Gate findings for phase
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate clear --plan-id {plan_id} --phase {phase}
```

**Phases**: `2-refine`, `3-outline`, `4-plan`, `5-execute`, `6-finalize`

**Sources**: `qgate` (automated verification), `user_review` (user feedback)

**Deduplication**: `qgate add` deduplicates by title within each phase (case-sensitive, exact match):
- If a finding with the same title already exists and is `pending` → returns `status: deduplicated` (no new record)
- If a finding with the same title exists but is resolved → returns `status: reopened` (reactivated to `pending`)
- Otherwise → creates new finding with `status: success`

**Iteration**: The optional `--iteration N` parameter tracks which verification cycle produced the finding (e.g., iteration 1 = first build attempt, iteration 2 = after fixes). Useful for filtering findings from a specific cycle via `qgate list --iteration N`.

**Phase 1-init**: Not included in Q-Gate phases — init creates plan infrastructure and has no verification step that would produce findings.

### Assessment Commands

Component evaluation storage providing structured JSONL persistence for certainty/confidence assessments from analysis agents.

```bash
# Add assessment
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  assessment add --plan-id {plan_id} --file-path {file_path} --certainty {certainty} --confidence {confidence} \
  [--agent AGENT] [--detail DETAIL] [--evidence EVIDENCE]

# List assessments
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  assessment list --plan-id {plan_id} [--certainty C] [--min-confidence N] \
  [--max-confidence N] [--file-pattern PATTERN]

# Get single assessment
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  assessment get --plan-id {plan_id} --hash-id {hash_id}

# Clear assessments (all or by agent)
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  assessment clear --plan-id {plan_id} [--agent AGENT]
```

**Certainty values**: `CERTAIN_INCLUDE`, `CERTAIN_EXCLUDE`, `UNCERTAIN`

| Value | Meaning |
|-------|---------|
| `CERTAIN_INCLUDE` | Component is definitely in scope for the deliverable |
| `CERTAIN_EXCLUDE` | Component is definitely NOT in scope |
| `UNCERTAIN` | Requires further analysis to determine scope |

**Certainty vs confidence**: Certainty is the classification (in/out/unknown). Confidence (0-100) measures how sure the agent is about that classification. An `UNCERTAIN` assessment with confidence 90 means the agent is highly confident the scope is ambiguous; a `CERTAIN_INCLUDE` with confidence 60 means moderate certainty it belongs.

## Output Format

All commands return TOON format.

**Add response**:
```toon
status: success
hash_id: a3f2c1
type: bug
```

**Query response**:
```toon
status: success
plan_id: EXAMPLE-PLAN
total_count: 30
filtered_count: 15

findings[15]{hash_id,type,title,resolution}:
a3f2c1,bug,Null check missing,pending
b4e3d2,sonar-issue,TODO comment,fixed
```

**Unified query response** (`list --include-qgate`): same shape as the default query response, plus three provenance markers — `qgate_included`, `plan_count`, and `qgate_count`. The `findings` array is the per-plan slice followed by the merged pending Q-Gate slice. `total_count` is the full universe of both slices (the entire per-plan store plus every pending Q-Gate record across phases, before `--type`/`--file-pattern` narrowing); `filtered_count` is the post-narrowing union actually returned in `findings`.

```toon
status: success
plan_id: EXAMPLE-PLAN
qgate_included: true
plan_count: 12
qgate_count: 3
total_count: 33
filtered_count: 15

findings[15]{hash_id,type,title,resolution}:
a3f2c1,bug,Null check missing,pending
b4e3d2,sonar-issue,TODO comment,fixed
```

## Integration

### Producers

| Client | Artifact | Operation |
|--------|----------|-----------|
| Sonar integration | finding (sonar-issue) | add, resolve |
| CI integration | finding (pr-comment) | add, resolve |
| phase-6-finalize | finding | add, promote |
| Q-Gate agent | qgate finding | add, resolve |
| Phase agents | qgate finding | add |

### Consumers

| Client | Artifact | Operation |
|--------|----------|-----------|
| phase-6-finalize | finding | list, resolve, promote |
| Phase agents (2-7) | qgate finding | list, resolve |

## Promotion Workflow

At `6-finalize`:

1. List unpromoted findings: `list --plan-id {plan_id} --promoted false`
2. For each finding to promote:
   - **To manage-lessons** (bug, improvement, anti-pattern) — first run the canonical three-gate lesson-creation policy in [`../manage-lessons/standards/lesson-creation-policy.md`](../manage-lessons/standards/lesson-creation-policy.md) (Gate 1 dedup, Gate 2 active-plan check, Gate 3 create); do not restate the gate mechanics. The two-step path-allocate add flow below is Gate 3, reached only when Gates 1 and 2 both clear:
     ```bash
     # Step A: allocate the lesson file (returns an absolute path)
     manage-lessons add --component {component} --category {type} --title {title}
     # Step B: write the finding body directly to the returned path via the Write tool
     # Step C: record the promotion
     promote --plan-id {plan_id} --hash-id {hash_id} --promoted-to {lesson_id}
     ```
     When Gate 1 returns `merge_into` (a similar lesson exists) or Gate 2 finds a covering active plan, do NOT allocate a new lesson — extend the existing lesson / fold into the plan per the policy, then still resolve the finding via `promote --plan-id {plan_id} --hash-id {hash_id} --promoted-to {existing_lesson_id|active-plan}`.
   - **To architecture** (tip, insight, best-practice):
     ```bash
     architecture enrich {type} --module {module} --{type} "{content}" --reasoning "From plan {plan_id}"
     promote --plan-id {plan_id} --hash-id {hash_id} --promoted-to architecture
     ```

**`promoted_to` values**: Either `architecture` (for tips/insights/best-practices routed to manage-architecture), or the lesson ID returned by `manage-lessons add` (the `id` field of the created lesson, still present in the TOON output).

**Error cases**:
- Promoting an already-promoted finding returns `status: error, error: already_promoted`
- If the target skill call fails, the finding is NOT marked as promoted (promote is the last step)

## Canonical invocations

The canonical argparse surface for `manage-findings.py`. The D4 plugin-doctor analyzer
(`_analyze_manage_invocation.py`) reads this section as source-of-truth for markdown
notation occurrences across the marketplace. Consuming skills xref this section by
name (e.g., "see `manage-findings` Canonical invocations → `qgate add`") instead of
restating the command inline.

### add

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings add \
  --plan-id PLAN_ID --type TYPE --title TEXT --detail TEXT \
  [--file-path PATH] [--line N] [--component COMPONENT] [--module MODULE] \
  [--rule RULE] [--severity SEVERITY] [--author AUTHOR] [--kind KIND] \
  [--raw-input FIELD=VALUE] [--raw-input-max-bytes N]
```

### list

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings list \
  --plan-id PLAN_ID \
  [--type TYPE_CSV] [--resolution RESOLUTION] [--promoted {true|false}] \
  [--file-pattern PATTERN] [--include-qgate] [--author AUTHOR] [--kind KIND]
```

### get

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings get \
  --plan-id PLAN_ID --hash-id HASH_ID
```

### resolve

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings resolve \
  --plan-id PLAN_ID --hash-id HASH_ID --resolution RESOLUTION \
  [--detail TEXT]
```

### promote

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings promote \
  --plan-id PLAN_ID --hash-id HASH_ID --promoted-to TARGET
```

### ingest

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings ingest \
  --plan-id PLAN_ID
```

### qgate add

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate add \
  --plan-id PLAN_ID --phase PHASE --source SOURCE --type TYPE \
  --title TEXT --detail TEXT \
  [--file-path PATH] [--component COMPONENT] [--severity SEVERITY] [--iteration N] \
  [--rule RULE] [--raw-input FIELD=VALUE] [--raw-input-max-bytes N]
```

### qgate list

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate list \
  --plan-id PLAN_ID --phase PHASE \
  [--resolution RESOLUTION] [--source SOURCE] [--iteration N]
```

### qgate resolve

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate resolve \
  --plan-id PLAN_ID --hash-id HASH_ID --resolution RESOLUTION --phase PHASE \
  [--detail TEXT]
```

### qgate clear

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate clear \
  --plan-id PLAN_ID --phase PHASE
```

### assessment add

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings assessment add \
  --plan-id PLAN_ID --file-path PATH --certainty CERTAINTY --confidence N \
  [--agent AGENT] [--detail TEXT] [--evidence TEXT]
```

### assessment list

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings assessment list \
  --plan-id PLAN_ID \
  [--certainty CERTAINTY] [--min-confidence N] [--max-confidence N] \
  [--file-pattern PATTERN]
```

### assessment get

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings assessment get \
  --plan-id PLAN_ID --hash-id HASH_ID
```

### assessment clear

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings assessment clear \
  --plan-id PLAN_ID [--agent AGENT]
```

## Error Responses

> See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for the standard error response format.

| Error Code | Cause |
|------------|-------|
| `not_found` | Finding hash_id doesn't exist |
| `already_promoted` | Finding was previously promoted |
| `invalid_type` | Type not in the finding types table |
| `invalid_resolution` | Resolution not in the valid values |
| `invalid_phase` | Phase not in 2-refine through 6-finalize |

## Related

- `manage-lessons` — Promotion target for bug, improvement, anti-pattern, triage findings
- `manage-architecture` — Promotion target for tip, insight, best-practice findings (via `enrich` commands)
- `manage-status` — Plan lifecycle tracking complementing findings resolution
