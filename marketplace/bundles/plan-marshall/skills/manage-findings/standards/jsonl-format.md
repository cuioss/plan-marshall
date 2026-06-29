# Findings JSONL Format

Storage format specifications for plan-level findings, phase-scoped Q-Gate findings, and assessments.

## Storage Layout

All finding-related JSONL files live under a single subdirectory:

```text
.plan/plans/{plan_id}/artifacts/findings/
├── {type}.jsonl             # one file per finding type (bug, improvement, sonar-issue, …)
├── qgate-{phase}.jsonl      # per-phase Q-Gate findings
├── assessments.jsonl        # component assessments
└── sonar-scan-summary.jsonl # producer-written verified-scan attestation (NOT a finding store)
```

| File | Scope | Purpose |
|------|-------|---------|
| `findings/{type}.jsonl` | Plan | Per-type plan findings — one file per value of the `type` field |
| `findings/qgate-{phase}.jsonl` | Phase | Per-phase verification findings, not promotable |
| `findings/assessments.jsonl` | Plan | Component assessments (certainty/confidence) |
| `findings/sonar-scan-summary.jsonl` | Plan | Producer-written verified-scan attestation rows — NOT managed by the `manage-findings` add/resolve verbs (see [Producer-Written Attestation Files](#producer-written-attestation-files)) |

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
- `findings/arch-constraint.jsonl`
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
| `type` | string | One of: `bug`, `improvement`, `anti-pattern`, `triage`, `tip`, `insight`, `best-practice`, `build-error`, `test-failure`, `lint-issue`, `sonar-issue`, `arch-constraint`, `pr-comment`, `pr-comment-overflow`. Types mapping to lesson categories: `bug`, `improvement`, `anti-pattern` (direct promotion); `arch-constraint` (reinforce-on-recurrence lifecycle, not direct promotion) — see `manage-lessons/standards/file-format.md` |
| `title` | string | Short description of the finding |
| `detail` | string | Full description with context |
| `severity` | string | `error`, `warning`, or `info` (default: `warning`) |
| `resolution` | string | `pending`, `fixed`, `suppressed`, `accepted`, `taken_into_account`, or `rejected` |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `file_path` | string | Relative path to affected file |
| `line` | int | Line number in affected file |
| `component` | string | Component identifier |
| `module` | string | Module name |
| `rule` | string | Rule identifier (e.g., linter rule, Sonar rule) |
| `author` | string | Reviewer/comment-author login (e.g. coderabbitai, gemini-code-assist) — indexed/queryable; primary attribution field for pr-comment findings |
| `kind` | string | pr-comment structure discriminator: inline / review_body / issue_comment — indexed/queryable; drives the actionable-vs-meta classification in the review retrospective |
| `reviewed_commit_sha` | string | PR HEAD SHA at the time the comment was ingested — the commit the reviewer bot saw; indexed/queryable, used to detect when HEAD has advanced past the last reviewed commit and a re-review is owed |
| `bot_kind` | string | Reviewer-bot identity derived from `author`: `coderabbit` or `gemini` — indexed/queryable; distinct from `kind` (which describes comment structure), this identifies WHICH bot reviewed and keys the re-review strategy registry |

For `pr-comment` findings, the queryable `author`, `kind`, `reviewed_commit_sha`, and `bot_kind` fields are the source of truth for reviewer identity, comment structure, and re-review matching; the author/kind lines written into the `detail` blob are retained for human readability only. `bot_kind` (the reviewer's identity) is distinct from `kind` (the comment's structure), and `reviewed_commit_sha` together with `bot_kind` are indexed/queryable so the re-review mechanism can match a reviewer to the commit it last saw.

### Resolution semantics

The `resolution` field carries six values. `pending` is the initial state; the other five represent ways a finding has been *addressed*. Only `pending` contributes to the `pending_findings_blocking_count` invariant that gates phase boundaries (see [`findings-pipeline.md`](../../ref-workflow-architecture/standards/findings-pipeline.md) § Per-phase blocking partition) — every non-`pending` value, including `rejected`, is excluded from the blocking count.

| Resolution | Meaning | Effect on source tree | Recorded detail |
|------------|---------|------------------------|------------------|
| `pending` | The finding has been added but not yet triaged. Blocks the next guarded phase boundary. | None | Auto-populated on `add`. |
| `fixed` | A fix-task was created (or the change was applied inline) and the next verification cycle will re-evaluate the finding. The underlying problem is being removed. | Source change (in this run or a follow-up) | `resolution_detail` names the fix-task id or the inline change. |
| `suppressed` | An inline annotation has been added at the finding's location with a documented rationale. The underlying behaviour stays; the linter/Sonar/reviewer is told to stop flagging it for the stated reason. | Inline annotation (`// NOSONAR …`, `# noqa: …`, language-specific) plus rationale comment | `resolution_detail` carries the rationale text. |
| `accepted` | The finding is acknowledged and the disposition is to leave the code as-is. No annotation; no source change. The rationale lives only in the finding record. | None | `resolution_detail` carries the rationale text. |
| `taken_into_account` | The finding informed a higher-order change rather than producing a direct fix or suppression — typically a Q-Gate finding that drove an outline restructure, a phasing-rationale block, or a scope adjustment. Closest in spirit to "noted and absorbed." | Indirect — the higher-order change is the response | `resolution_detail` names the higher-order change (e.g. the section added to `solution_outline.md`). |
| `rejected` | The validity-verification ([ext-point-verify](../../extension-api/standards/ext-point-verify.md)) stage refuted the finding as invalid / a false positive. No source change; the finding is terminal and non-blocking (does not contribute to `pending_findings_blocking_count`) and never reaches triage. | None | `resolution_detail` carries the refutation rationale. |

The five addressed values are not interchangeable. `fixed` removes the problem; `suppressed` and `accepted` document a decision to keep it; `taken_into_account` records that the feedback shaped something other than a direct fix; `rejected` records that the finding was never a real defect (set by the verify stage, distinct from `accepted`, which keeps a real finding as-is). The triage workflow ([`plan-marshall/workflow/triage.md`](../../plan-marshall/workflow/triage.md)) and the per-domain `ext-triage-{domain}` standards (under each domain bundle) decide which value applies in each case; `rejected` is set earlier, by the verify pre-stage, before triage runs.

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
| `arch-constraint` | Not promotable (recurring violations feed lessons; see below) | N/A |
| `pr-comment` | Not promotable | N/A |
| `pr-comment-overflow` | Not promotable | N/A |

### `pr-comment-overflow`

`pr-comment-overflow` is the bookkeeping type that carries unprocessed `pr-comment` IDs from a budget-exhausted `automated-review` iteration to the next one. It is filed by `automated-review` (see [`phase-6-finalize/workflow/automated-review.md`](../../phase-6-finalize/workflow/automated-review.md) § Overflow handling) when the per-iteration triage budget is nearly exhausted before all `pr-comment` findings have been processed.

| Field | Expected shape |
|-------|----------------|
| `title` | `Triage budget exhausted: {N} pr-comment finding(s) deferred` |
| `severity` | `warning` (overflow does not block the boundary; it defers work to the next iteration) |
| `detail` | Comma-separated list of `pr-comment` `hash_id` values that were enqueued but not resolved this iteration. The list is machine-readable; the next iteration's overflow consumer parses it to know which comments to prioritise. |
| `resolution` | `pending` until every comment named in `detail` has been individually resolved (FIX / SUPPRESS / ACCEPT) in a subsequent `automated-review` iteration; then `fixed`. |

**Resolution semantics**: an overflow finding resolves once the next `automated-review` iteration has processed every comment listed in its `detail` (each individual comment goes through the standard FIX / SUPPRESS / ACCEPT path; the overflow finding itself is the umbrella). If a subsequent iteration cannot finish the deferred queue either, a fresh `pr-comment-overflow` finding is filed for the still-unprocessed remainder — the original overflow finding is `resolved` with `--resolution fixed` once its specific comments are processed; the new overflow is a separate record.

The type is non-promotable: it is operational bookkeeping, not a long-lived knowledge artefact. The blocking partition (see [`findings-pipeline.md`](../../ref-workflow-architecture/standards/findings-pipeline.md) § Per-phase blocking partition) does NOT include `pr-comment-overflow` — the overflow finding deliberately does not block the `6-finalize` boundary because the deferred work is handled by the dispatcher's `loop_back` re-entry rather than by gating the phase boundary.

### `arch-constraint`

`arch-constraint` is the finding type emitted by the `default:verify:arch-gate` verify-step (see [`extension-api/standards/ext-point-build-verify-step.md`](../../extension-api/standards/ext-point-build-verify-step.md) § Domain-Appended Verify Steps). The arch-gate producer runs a domain's native architectural-constraint tool (ArchUnit / import-linter / dependency-cruiser) as a read-only structural-boundary gate and parses each structural-boundary violation into an `arch-constraint` finding, which flows to the domain's `ext-triage-{domain}` skill through the same producer → store → triage pattern as `lint-issue` / `sonar-issue`.

| Field | Expected shape |
|-------|----------------|
| `title` | The violated rule's human-readable summary (e.g. `Layer 'service' must not depend on 'web'`). |
| `severity` | `error` for a hard boundary violation; `warning` for an advisory contract. |
| `file_path` / `line` | The offending source location reported by the native tool, when available. |
| `rule` | The rule identity (the tool's rule name / contract id). This is the dedup key the lessons machinery uses to reinforce one recurring-violation lesson rather than allocate one per instance. |

The type is **not promotable** through the finding-promotion path. Recurring arch-constraint violations feed the `arch-constraint` lesson type (rule-identity dedup, retire-on-quiet / reinforce-on-recurrence lifecycle) via the lessons housekeeping machinery — see `manage-lessons/standards/file-format.md` — which is a separate channel from finding promotion. The per-finding triage disposition (FIX / SUPPRESS / ACCEPT) is decided by the owning `ext-triage-{domain}` skill.

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

## Producer-Written Attestation Files

Some files under `artifacts/findings/` are **producer-written attestation files**, not finding stores. They share the directory (so they survive `manage-status archive` exactly like the per-type finding files) but are append-only artifacts a producer script writes directly — they are NOT created, mutated, or resolved through the `manage-findings` `add` / `resolve` / `promote` verbs, carry no `hash_id` / `resolution` / `promoted` fields, and do not participate in the per-phase blocking partition.

| File | Producer | Write contract |
|------|----------|----------------|
| `findings/sonar-scan-summary.jsonl` | `workflow-integration-sonar:sonar fetch-and-store` (`sonar.py:_write_scan_summary`) | One attestation row appended per `fetch-and-store` run — written **unconditionally**, including when `new_code_issue_count == 0` and on `count_status == undecidable`, so an absent file unambiguously means "not checked" and a `confirmed` zero is a positive on-disk fact. Read at the success gate of [`phase-6-finalize/workflow/sonar-roundtrip.md`](../../phase-6-finalize/workflow/sonar-roundtrip.md). |

### `sonar-scan-summary.jsonl` row schema

Each line is a JSON object written by `sonar.py:_write_scan_summary`. This is a **distinct artifact kind** from `findings/sonar-issue.jsonl` (the latter is a `manage-findings`-managed per-type finding store; this is a producer-written attestation file). The full producer contract — CE-readiness wait, the verified-count + undecidable discriminator, and the consumer success gate — lives in [`workflow-integration-sonar/SKILL.md`](../../workflow-integration-sonar/SKILL.md) § "Scan-Summary Marker (sonar-scan-summary.jsonl)"; do NOT restate it here.

| Field | Type | Always present | Description |
|-------|------|:--------------:|-------------|
| `count_status` | string | yes | `confirmed` (CE settled in budget) or `undecidable` (CE timeout or REST/auth failure) |
| `new_code_issue_count` | int \| null | yes | Verified PR-scoped new-code total on `confirmed`; `null` on `undecidable` |
| `count_status_reason` | string | no | Human-readable reason; emitted **only** on `undecidable` |
| `pr` | string \| null | yes | PR number the fetch was scoped to (`null` for a non-PR / branch fetch) |
| `project` | string | yes | Sonar project key the fetch enumerated |
| `scanned_sha` | string | yes | Worktree HEAD SHA the scan attests to; `""` when the SHA cannot be resolved |
| `ts` | string | yes | ISO-8601 UTC timestamp of the fetch |

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
