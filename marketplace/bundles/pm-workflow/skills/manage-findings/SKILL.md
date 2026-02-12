---
name: manage-findings
description: Unified finding and Q-Gate storage with JSONL persistence for plan-scoped and phase-scoped findings
user-invocable: false
allowed-tools: Bash
---

# Manage Findings

Unified storage for plan-level findings and phase-scoped Q-Gate findings. Both share the same type taxonomy, resolution model, and severity values.

## Scope Distinction

| Scope | Storage | Lifecycle |
|-------|---------|-----------|
| **Plan findings** | `.plan/plans/{plan_id}/artifacts/findings.jsonl` | Long-lived, promotable |
| **Q-Gate findings** | `.plan/plans/{plan_id}/artifacts/qgate-{phase}.jsonl` | Per-phase, not promotable |

Plan findings are working data during plan execution. Notable findings are promoted to project-level at `7-finalize`. Q-Gate findings track per-phase verification issues.

## Storage Structure

```
.plan/plans/{plan_id}/
└── artifacts/
    ├── assessments.jsonl      # Component assessments
    ├── findings.jsonl         # Unified: lessons + bugs (optionally promotable)
    ├── qgate-2-refine.jsonl   # Per-phase Q-Gate findings
    ├── qgate-3-outline.jsonl
    ├── qgate-4-plan.jsonl
    ├── qgate-6-verify.jsonl
    └── qgate-7-finalize.jsonl
```

## Finding Types

| Type | Origin | Default Promotion Target |
|------|--------|--------------------------|
| `bug` | Implementation errors | manage-lessons |
| `improvement` | Discovered patterns | manage-lessons |
| `anti-pattern` | Bad practices found | manage-lessons |
| `triage` | Triage decisions | manage-lessons |
| `tip` | Helpful hints | architecture (tips) |
| `insight` | Deeper understanding | architecture (insights) |
| `best-practice` | Recommended patterns | architecture (best_practices) |
| `build-error` | Compilation failures | (any, if pattern emerges) |
| `test-failure` | Test failures | (any, if pattern emerges) |
| `lint-issue` | Linter warnings | (any, if pattern emerges) |
| `sonar-issue` | Sonar findings | (any, if pattern emerges) |
| `pr-comment` | PR review comments | (any, if pattern emerges) |

**Resolution values**: `pending`, `fixed`, `suppressed`, `accepted`, `taken_into_account`

**Severity values**: `error`, `warning`, `info`

## CLI Commands

### Plan-Scoped Finding Commands

```bash
# Add finding
python3 .plan/execute-script.py pm-workflow:manage-findings:manage-findings \
  add --plan-id {plan_id} --type {type} --title {title} --detail DETAIL \
  [--file-path PATH] [--line N] [--component C] \
  [--module M] [--rule R] [--severity S]

# Query findings
python3 .plan/execute-script.py pm-workflow:manage-findings:manage-findings \
  query --plan-id {plan_id} [--type T] [--resolution R] \
  [--promoted BOOL] [--file-pattern PATTERN]

# Get single finding
python3 .plan/execute-script.py pm-workflow:manage-findings:manage-findings \
  get --plan-id {plan_id} --hash-id {hash_id}

# Resolve finding
python3 .plan/execute-script.py pm-workflow:manage-findings:manage-findings \
  resolve --plan-id {plan_id} --hash-id {hash_id} --resolution {resolution} [--detail DETAIL]

# Promote finding
python3 .plan/execute-script.py pm-workflow:manage-findings:manage-findings \
  promote --plan-id {plan_id} --hash-id {hash_id} --promoted-to {promoted_to}
```

### Q-Gate Commands

Per-phase Q-Gate findings for the unified findings-iteration model across phases 2-7.

```bash
# Add Q-Gate finding
python3 .plan/execute-script.py pm-workflow:manage-findings:manage-findings \
  qgate add --plan-id {plan_id} --phase {phase} --source {qgate|user_review} \
  --type {type} --title {title} --detail {detail} \
  [--file-path PATH] [--component C] [--severity S] [--iteration N]

# Query Q-Gate findings
python3 .plan/execute-script.py pm-workflow:manage-findings:manage-findings \
  qgate query --plan-id {plan_id} --phase {phase} \
  [--resolution R] [--source S] [--iteration N]

# Resolve Q-Gate finding
python3 .plan/execute-script.py pm-workflow:manage-findings:manage-findings \
  qgate resolve --plan-id {plan_id} --hash-id {hash_id} --resolution {resolution} --phase {phase} \
  [--detail DETAIL]

# Clear Q-Gate findings for phase
python3 .plan/execute-script.py pm-workflow:manage-findings:manage-findings \
  qgate clear --plan-id {plan_id} --phase {phase}
```

**Phases**: `2-refine`, `3-outline`, `4-plan`, `6-verify`, `7-finalize`

**Sources**: `qgate` (automated verification), `user_review` (user feedback)

**Deduplication**: `qgate add` deduplicates by title within each phase:
- If a finding with the same title already exists and is `pending` → returns `status: deduplicated` (no new record)
- If a finding with the same title exists but is resolved → returns `status: reopened` (reactivated to `pending`)
- Otherwise → creates new finding with `status: success`

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
| phase-7-finalize | finding | add, promote |
| Q-Gate agent | qgate finding | add, resolve |
| Phase agents | qgate finding | add |

### Consumers

| Client | Artifact | Operation |
|--------|----------|-----------|
| phase-7-finalize | finding | query, resolve, promote |
| Phase agents (2-7) | qgate finding | query, resolve |

## Promotion Workflow

At `7-finalize`:

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
