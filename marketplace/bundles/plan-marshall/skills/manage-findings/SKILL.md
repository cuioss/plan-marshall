---
name: manage-findings
description: Unified finding, Q-Gate, and assessment storage with JSONL persistence for plan-scoped findings, phase-scoped Q-Gate findings, and component assessments
user-invocable: false
scope: plan
---

# Manage Findings

Unified storage for plan-level findings, phase-scoped Q-Gate findings, and component assessments. Findings and Q-Gate share the same type taxonomy, resolution model, and severity values. Assessments use a separate certainty/confidence model for component evaluations.

## Enforcement

> **Base contract**: See `plan-marshall:ref-manage-contract` for shared enforcement rules, TOON output format, and error response patterns.

**Skill-specific constraints:**
- Only valid resolution values: `pending`, `fixed`, `suppressed`, `accepted`, `taken_into_account`
- Plan findings and Q-Gate findings use different command prefixes (direct vs `qgate`)
- Assessment commands use the `assessment` prefix
- Q-Gate deduplication is automatic; do not add duplicate findings manually
- Assessment confidence values must be numeric (0-100)

## Scope Distinction

| Scope | Storage | Lifecycle |
|-------|---------|-----------|
| **Plan findings** | `.plan/plans/{plan_id}/artifacts/findings.jsonl` | Long-lived, promotable |
| **Q-Gate findings** | `.plan/plans/{plan_id}/artifacts/qgate-{phase}.jsonl` | Per-phase, not promotable |
| **Assessments** | `.plan/plans/{plan_id}/artifacts/assessments.jsonl` | Working data, read-only after outline |

Plan findings are working data during plan execution. Notable findings are promoted to project-level at `6-finalize`. Q-Gate findings track per-phase verification issues. Assessments track component evaluations with certainty/confidence classifications.

## Storage Structure

```
.plan/plans/{plan_id}/
└── artifacts/
    ├── assessments.jsonl      # Component assessments
    ├── findings.jsonl         # Unified: lessons + bugs (optionally promotable)
    ├── qgate-2-refine.jsonl   # Per-phase Q-Gate findings
    ├── qgate-3-outline.jsonl
    ├── qgate-4-plan.jsonl
    ├── qgate-5-execute.jsonl
    └── qgate-6-finalize.jsonl
```

## Finding Types

Types: `bug`, `improvement`, `anti-pattern`, `triage`, `tip`, `insight`, `best-practice`, `build-error`, `test-failure`, `lint-issue`, `sonar-issue`, `pr-comment`

Resolutions: `pending`, `fixed`, `suppressed`, `accepted`, `taken_into_account`

Severities: `error`, `warning`, `info` (default: `warning`)

See [standards/jsonl-format.md](standards/jsonl-format.md) for the complete type taxonomy with promotion targets, resolution semantics, severity values, and the type selection guide.

## CLI Commands

**Parser architecture**: This script uses a two-level subparser pattern. Top-level subcommands (`add`, `query`, `get`, `resolve`, `promote`) handle plan-scoped findings directly. The `qgate` subcommand introduces a second parser level with its own subcommands (`qgate add`, `qgate query`, `qgate resolve`, `qgate clear`). The `assessment` subcommand introduces a third command group (`assessment add`, `assessment query`, `assessment get`, `assessment clear`). This mirrors the three storage scopes in the CLI surface.

### Plan-Scoped Finding Commands

```bash
# Add finding
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  add --plan-id {plan_id} --type {type} --title {title} --detail DETAIL \
  [--file-path PATH] [--line N] [--component C] \
  [--module M] [--rule R] [--severity S]

# Query findings
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  query --plan-id {plan_id} [--type T] [--resolution R] \
  [--promoted BOOL] [--file-pattern PATTERN]

# Get single finding
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  get --plan-id {plan_id} --hash-id {hash_id}

# Resolve finding
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  resolve --plan-id {plan_id} --hash-id {hash_id} --resolution {resolution} [--detail DETAIL]

# Promote finding
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  promote --plan-id {plan_id} --hash-id {hash_id} --promoted-to {promoted_to}
```

### Q-Gate Commands

Per-phase Q-Gate findings for the unified findings-iteration model across phases 2-7.

```bash
# Add Q-Gate finding
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate add --plan-id {plan_id} --phase {phase} --source {qgate|user_review} \
  --type {type} --title {title} --detail {detail} \
  [--file-path PATH] [--component C] [--severity S] [--iteration N]

# Query Q-Gate findings
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  qgate query --plan-id {plan_id} --phase {phase} \
  [--resolution R] [--source S] [--iteration N]

# Resolve Q-Gate finding
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

**Iteration**: The optional `--iteration N` parameter tracks which verification cycle produced the finding (e.g., iteration 1 = first build attempt, iteration 2 = after fixes). Useful for filtering findings from a specific cycle via `qgate query --iteration N`.

**Phase 1-init**: Not included in Q-Gate phases — init creates plan infrastructure and has no verification step that would produce findings.

### Assessment Commands

Component evaluation storage providing structured JSONL persistence for certainty/confidence assessments from analysis agents.

```bash
# Add assessment
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  assessment add --plan-id {plan_id} --file-path {file_path} --certainty {certainty} --confidence {confidence} \
  [--agent AGENT] [--detail DETAIL] [--evidence EVIDENCE]

# Query assessments
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  assessment query --plan-id {plan_id} [--certainty C] [--min-confidence N] \
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
plan_id: my-plan
total_count: 30
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
| phase-6-finalize | finding | query, resolve, promote |
| Phase agents (2-7) | qgate finding | query, resolve |

## Promotion Workflow

At `6-finalize`:

1. Query unpromoted findings: `query --plan-id {plan_id} --promoted false`
2. For each finding to promote:
   - **To manage-lessons** (bug, improvement, anti-pattern, triage):
     ```bash
     manage-lessons add --component {component} --category {type} ...
     promote --plan-id {plan_id} --hash-id {hash_id} --promoted-to {promoted_id}
     ```
   - **To architecture** (tip, insight, best-practice):
     ```bash
     architecture enrich {type} --module {module} --{type} "{content}" --reasoning "From plan {plan_id}"
     promote --plan-id {plan_id} --hash-id {hash_id} --promoted-to architecture
     ```

**`promoted_to` values**: Either `architecture` (for tips/insights/best-practices routed to manage-architecture), or the lesson ID returned by `manage-lessons add` (the hash_id of the created lesson).

**Error cases**:
- Promoting an already-promoted finding returns `status: error, error: already_promoted`
- If the target skill call fails, the finding is NOT marked as promoted (promote is the last step)

## Error Responses

> See `plan-marshall:ref-manage-contract` for the standard error response format.

| Error Code | Cause |
|------------|-------|
| `not_found` | Finding hash_id doesn't exist |
| `already_promoted` | Finding was previously promoted |
| `invalid_type` | Type not in the finding types table |
| `invalid_resolution` | Resolution not in the valid values |
| `invalid_phase` | Phase not in 2-refine through 6-finalize |

## Related Skills

- `manage-lessons` — Promotion target for bug, improvement, anti-pattern, triage findings
- `manage-architecture` — Promotion target for tip, insight, best-practice findings (via `enrich` commands)
- `manage-assessments` — Complementary: assessments track component evaluations, findings track issues discovered
