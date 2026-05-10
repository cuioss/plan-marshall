# Findings JSONL Format

Storage format specifications for plan-level findings, phase-scoped Q-Gate findings, and assessments.

## Storage Layout

All finding-related JSONL files live under a single subdirectory:

```
.plan/plans/{plan_id}/artifacts/findings/
├── {type}.jsonl             # one file per finding type (bug, improvement, sonar-issue, …)
├── qgate-{phase}.jsonl      # per-phase Q-Gate findings
└── assessments.jsonl        # component assessments
```

| File | Scope | Purpose |
|------|-------|---------|
| `findings/{type}.jsonl` | Plan | Per-type plan findings — one file per value of the `type` field |
| `findings/qgate-{phase}.jsonl` | Phase | Per-phase verification findings, not promotable |
| `findings/assessments.jsonl` | Plan | Component assessments (certainty/confidence) |

### Per-Type Splitting

Plan-scoped findings are stored split per type rather than in a single combined file. Each finding type listed in the type taxonomy below has its own JSONL file in the `findings/` subdirectory:

- `findings/bug.jsonl`
- `findings/improvement.jsonl`
- `findings/anti-pattern.jsonl`
- `findings/triage.jsonl`
- `findings/tip.jsonl`
- `findings/insight.jsonl`
- `findings/best-practice.jsonl`
- `findings/build-error.jsonl`
- `findings/test-failure.jsonl`
- `findings/lint-issue.jsonl`
- `findings/sonar-issue.jsonl`
- `findings/pr-comment.jsonl`
- `findings/pr-comment-overflow.jsonl`

Files are created lazily — a per-type file only exists once a finding of that type has been added.

The `query` command merges across all per-type files in canonical type order before applying filters. The `get`, `resolve`, and `promote` commands locate the owning per-type file by scanning the directory for the requested `hash_id`.

## Plan Finding Record

Each line in a `findings/{type}.jsonl` file is a JSON object:

```json
{
  "hash_id": "a3f2c1",
  "timestamp": "2026-03-27T10:00:00Z",
  "type": "bug",
  "title": "Null check missing in validation",
  "detail": "The validate() method does not check for null input",
  "severity": "warning",
  "resolution": "pending",
  "file_path": "src/main/java/Validator.java",
  "line": 42,
  "component": "jwt-validator",
  "module": "cui-jwt",
  "rule": "NP_NULL_ON_SOME_PATH",
  "promoted": false,
  "promoted_to": null
}
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `hash_id` | string | 6-character hex hash (auto-generated, see Hash ID Generation) |
| `timestamp` | string | ISO 8601 UTC (auto-generated on add) |
| `type` | string | One of: `bug`, `improvement`, `anti-pattern`, `triage`, `tip`, `insight`, `best-practice`, `build-error`, `test-failure`, `lint-issue`, `sonar-issue`, `pr-comment`, `pr-comment-overflow`. The first three (`bug`, `improvement`, `anti-pattern`) map to lesson categories — see `manage-lessons/standards/file-format.md` |
| `title` | string | Short description of the finding |
| `detail` | string | Full description with context |
| `severity` | string | `error`, `warning`, or `info` (default: `warning`) |
| `resolution` | string | `pending`, `fixed`, `suppressed`, `accepted`, or `taken_into_account` |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `file_path` | string | Relative path to affected file |
| `line` | int | Line number in affected file |
| `component` | string | Component identifier |
| `module` | string | Module name |
| `rule` | string | Rule identifier (e.g., linter rule, Sonar rule) |

### Promotion Fields

| Field | Type | Description |
|-------|------|-------------|
| `promoted` | bool | Whether this finding has been promoted (default: `false`) |
| `promoted_to` | string/null | Target identifier: `architecture` or lesson hash_id |

### Promotion Mapping

Finding types promote to specific targets:

| Finding Type | Promotion Target | Lesson Category |
|-------------|-----------------|-----------------|
| `bug` | manage-lessons | `bug` |
| `improvement` | manage-lessons | `improvement` |
| `anti-pattern` | manage-lessons | `anti-pattern` |
| `triage` | manage-lessons | `bug` (triaged) |
| `tip` | manage-architecture (enrich) | N/A |
| `insight` | manage-architecture (enrich) | N/A |
| `best-practice` | manage-architecture (enrich) | N/A |
| `build-error` | Not promotable | N/A |
| `test-failure` | Not promotable | N/A |
| `lint-issue` | Not promotable | N/A |
| `sonar-issue` | Not promotable | N/A |
| `pr-comment` | Not promotable | N/A |
| `pr-comment-overflow` | Not promotable | N/A |

### `pr-comment-overflow`

`pr-comment-overflow` is the bookkeeping type that carries unprocessed `pr-comment` IDs from a budget-exhausted `automated-review` iteration to the next one. It is filed by `automated-review` (see [`phase-6-finalize/standards/automated-review.md`](../../phase-6-finalize/standards/automated-review.md) § Overflow handling) when the per-iteration triage budget is nearly exhausted before all `pr-comment` findings have been processed.

| Field | Expected shape |
|-------|----------------|
| `title` | `Triage budget exhausted: {N} pr-comment finding(s) deferred` |
| `severity` | `warning` (overflow does not block the boundary; it defers work to the next iteration) |
| `detail` | Comma-separated list of `pr-comment` `hash_id` values that were enqueued but not resolved this iteration. The list is machine-readable; the next iteration's overflow consumer parses it to know which comments to prioritise. |
| `resolution` | `pending` until every comment named in `detail` has been individually resolved (FIX / SUPPRESS / ACCEPT) in a subsequent `automated-review` iteration; then `fixed`. |

**Resolution semantics**: an overflow finding resolves once the next `automated-review` iteration has processed every comment listed in its `detail` (each individual comment goes through the standard FIX / SUPPRESS / ACCEPT path; the overflow finding itself is the umbrella). If a subsequent iteration cannot finish the deferred queue either, a fresh `pr-comment-overflow` finding is filed for the still-unprocessed remainder — the original overflow finding is `resolved` with `--resolution fixed` once its specific comments are processed; the new overflow is a separate record.

The type is non-promotable: it is operational bookkeeping, not a long-lived knowledge artefact. The blocking partition (see [`findings-pipeline.md`](../../ref-workflow-architecture/standards/findings-pipeline.md) § Per-phase blocking partition) does NOT include `pr-comment-overflow` — the overflow finding deliberately does not block the `6-finalize` boundary because the deferred work is handled by the dispatcher's `loop_back` re-entry rather than by gating the phase boundary.

## Q-Gate Finding Record

Each line in `findings/qgate-{phase}.jsonl` is a JSON object:

```json
{
  "hash_id": "b4e3d2",
  "timestamp": "2026-03-27T10:05:00Z",
  "type": "build-error",
  "title": "Compilation failure in module cui-jwt",
  "detail": "Cannot find symbol: class JwtValidator",
  "severity": "error",
  "resolution": "pending",
  "source": "qgate",
  "iteration": 1,
  "file_path": "src/main/java/JwtService.java",
  "component": "cui-jwt"
}
```

### Additional Q-Gate Fields

| Field | Type | Description |
|-------|------|-------------|
| `source` | string | `qgate` (automated verification) or `user_review` (user feedback) |
| `iteration` | int | Verification cycle number (1 = first build attempt, 2 = after fixes) |

Q-Gate findings do NOT have `promoted`/`promoted_to` fields — they are not promotable.

## Hash ID Generation

Hash IDs are 6-character hex strings generated using `SHA-256(timestamp + random_bytes)[:6]`.

- Algorithm: `hashlib.sha256(f'{utc_iso}{secrets.token_hex(8)}'.encode()).hexdigest()[:6]`
- IDs are unique per record, NOT deterministic from content
- Deduplication in Q-Gate uses title matching (see below), not hash comparison

## Deduplication (Q-Gate Only)

When adding a Q-Gate finding, the system checks for existing findings with the same title in the phase file:

| Existing State | Action | Returned Status |
|----------------|--------|-----------------|
| No match | Create new record | `success` |
| Match with `pending` resolution | No change | `deduplicated` |
| Match with non-pending resolution | Reset to `pending` | `reopened` |

## Valid Phases

> Phase names follow the standard 6-phase model. See [manage-contract.md](../../ref-workflow-architecture/standards/manage-contract.md) § Phase Names for the canonical definition.

Q-Gate files are created per phase: `2-refine`, `3-outline`, `4-plan`, `5-execute`, `6-finalize`. Phase `1-init` is excluded — it creates plan infrastructure and has no verification step.
