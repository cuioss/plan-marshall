---
name: manage-findings
description: Unified JSONL storage for plan-scoped findings, phase-scoped Q-Gate findings, and component assessments
user-invocable: false
mode: script-executor
scope: plan
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

Per-type files are created lazily — only types that have been added produce a file. The `list` command transparently merges across all per-type files (in canonical type order); `get`/`resolve`/`promote` locate the owning file by `hash_id` **within the plan-findings file set only** — the per-type `{type}.jsonl` files, never `qgate-*.jsonl` and never `assessments.jsonl`. A `hash_id` that lives in one of those sibling stores is reported as `finding_in_other_store`, naming the store and the verb that owns it, rather than silently missed by the read or silently written by the resolve/promote pass. The CLI surface is unaffected by the per-type split.

See [standards/jsonl-format.md](standards/jsonl-format.md) for the complete storage layout and per-type file list.

## Store Resolution and the Store States

The findings store is resolved cwd-relatively (ADR-002): `plans/{plan_id}/` MOVES into its worktree at phase-5 and back at finalize. From the main checkout the directory of a running plan is therefore genuinely absent — and a primitive that returns `[]` for a non-existent path cannot tell that apart from a plan that filed nothing.

Every operation surface — read, write, `add` and the batched `ingest` pass alike — resolves the store through one explicit handle and publishes what it found alongside its own payload:

| Field | Meaning |
|-------|---------|
| `store_resolution` | Which anchor resolved the runtime-state root: `cwd_relative` (production), `override` (`PLAN_BASE_DIR` / `set_base_dir()`, tests), or `unresolved` (no root reached at all). |
| `store_path` | The resolved `artifacts/findings/` directory, or `null` when `store_resolution` is `unresolved`. |
| `findings_store_state` | `present` / `missing` / `plan_absent` / `unknown` — see below. |
| `unresolved_store` | `true` exactly when the surface REFUSED because the store was never reached; derived from `findings_store_state`, so the two cannot drift apart. |

The state values:

| `findings_store_state` | Condition | Outcome |
|------------------------|-----------|---------|
| `present` | The plan directory and its `artifacts/findings/` both exist. | `status: success` with today's counts. |
| `missing` | The plan directory exists but has filed nothing yet (no `artifacts/findings/`). | `status: success`, `total_count: 0` — the **benign zero**, unchanged from before this discriminator existed. |
| `plan_absent` | `plans/{plan_id}/` is not under the resolved root. | `status: error`, `error: findings_store_unresolved`; the message names the resolved root and, when the plan can be located, the checkout that actually holds it. |
| `unknown` | No runtime-state root could be resolved at all. | `status: error`, `error: findings_store_unresolved`. |

The state is decided on the **plan directory**, never on `artifacts/findings/`. A plan's first-ever finding legitimately creates that subdirectory, so a guard keyed there would refuse every real plan's first write — and turn the benign zero into the inverse defect.

### `--any-checkout` (read-only)

`--any-checkout` is an explicit opt-in that reads a plan's findings from whichever checkout currently holds the plan directory, resolving through the existing `git-workflow locate-plan-checkout` verb. It is declared on exactly five verbs, and on no other:

- `list`
- `get`
- `qgate list`
- `assessment list`
- `assessment get`

Every one of those is a READ, and that list is the flag's whole presence set: **every verb not named above is without it**, `add` and every other write verb included — so a caller in one checkout can never obtain write authority over a plan whose directory lives in another. The guarantee is stated as the complement of the five rather than as a roster of the writes, because a second list would have to be re-derived from `--help` on every verb added and is exactly what goes stale. A write verb handed the flag is rejected by argparse (exit code 2), not silently ignored. Without the flag, a cross-checkout read returns the `plan_absent` refusal naming the checkout that holds the plan.

This surface **retires the direct-path workaround**: reading `.plan/local/worktrees/*/.plan/local/plans/*/artifacts/findings/*.jsonl` by hand-constructed path is no longer the way to reach a worktree-resident plan's findings. Go through the script funnel with `--any-checkout` instead.

### The `add` verbs refuse an absent plan directory

`add`, `qgate add` and `assessment add` all end at an append whose parent-directory creation would materialize the whole `plans/{plan_id}/artifacts/findings/` chain. Against a `plan_id` with no directory under the resolved root that manufactures a **phantom store** — after which a subsequent `list` reports `findings_store_state: present` for a plan that never existed, defeating the guarantee the read surfaces provide.

All three therefore REFUSE, returning `status: error` / `error: findings_store_unresolved` / `findings_store_state: plan_absent` and creating nothing on disk. Because `qgate add`'s refusal is an `error`, it is already outside the `QGATE_PERSIST_OK` partition (`success` / `deduplicated` / `reopened`), so every caller that tests membership in that set treats a refused add as not-in-store with no change at the call site. A real plan whose directory exists but which has no `artifacts/findings/` yet still succeeds and still creates the file.

### `ingest` refuses on the same guard

`ingest` both READS the pending findings and WRITES to them (promoting validated fields, resolving rejections), so it carries the same guard and returns the same refusal. Against an unreached store its counts would be a three-way zero — `promoted: 0`, `rejected: 0`, `skipped: 0` — over records it never looked at, which is exactly the clean zero this discriminator exists to abolish.

### The refusal shape travels to downstream consumers

The refusal carries **no `findings` key**, because there is no substrate to report findings from. A consumer that subscripts a query payload unconditionally therefore raises `KeyError('findings')` — an error naming a dict key rather than the absent plan directory that caused it. Every cross-skill consumer of the `pr-comment` read recognises the refusal via `_findings_store_state.as_unresolved_store_error` and **re-publishes the same `error` code**, so one unreached store produces one error code across the whole pipeline rather than one vocabulary per consumer. None substitutes an empty finding list: an empty list would render a store nobody read as a confident "nobody reviewed".

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
  [--promoted BOOL] [--file-pattern PATTERN] [--author AUTHOR] [--kind KIND] \
  [--bot-kind BOT_KIND] [--preference-admissible] [--include-qgate] [--any-checkout]

# Get single finding
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  get --plan-id {plan_id} --hash-id {hash_id} [--any-checkout]

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

#### Preference-evidence narrowing (`--preference-admissible`)

`--preference-admissible` narrows the result to the findings that may seed a preference recurrence: a `pr-comment` is kept only when it is positively attributed to a recognized reviewer bot, and every other finding type passes through untouched. The flag APPLIES the authorship-admissibility rule; [`scripts/_preference_admissibility.py`](scripts/_preference_admissibility.py) IMPLEMENTS it, as the single home both preference surfaces reach. For why the gate keys on positive external attribution rather than trying to recognize the pipeline's own comments, see [`../phase-6-finalize/standards/disposition-to-hint-routing.md`](../phase-6-finalize/standards/disposition-to-hint-routing.md) § "(e) Authorship admissibility" — the single source of truth, not restated here.

The recognized reviewer set is re-derived from the live registry, once per query, and that derivation can fail. When it does, the rule **degrades to a presence-only check**: a `pr-comment` is kept on a PRESENT `bot_kind` without validating it against the registry. The degrade is deliberate — rejecting every bot-attributed comment instead would hand preference learning a clean zero over a population it never read — and the pipeline's own comments are excluded on BOTH paths, because they carry an ABSENT `bot_kind` and the presence check runs first. What the degrade admits is a present-but-unrecognized `bot_kind`: a legacy or de-registered reviewer identity.

The degrade is never silent. Whenever the flag is on, the result carries **`preference_admissibility_basis`** — `recognized` when the registry resolved and the full check ran, `presence_only` when it did not and the rule degraded. The field is absent when the flag is off, so it never asserts a basis for a check that did not run. The cross-plan auditor publishes the same field on its `preference-pattern-detector` block, so both preference surfaces state which of the two paths they walked.

The flag is **off by default**, so no existing caller's result changes. It is **keyword-only** on the underlying `query_findings` / `query_findings_unified` functions — both are consumed across skills, and it sits beside `any_checkout`, so positional binding is closed off rather than left to caller discipline. It composes with the other filters by acting on the already-filtered slice — `total_count` still spans the whole store, `filtered_count` reports the post-narrowing result — and it narrows the Q-Gate slice too under `--include-qgate`, so one flag never returns half-excluded output.

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
  [--resolution R] [--source S] [--iteration N] [--any-checkout]

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
  [--max-confidence N] [--file-pattern PATTERN] [--any-checkout]

# Get single assessment
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings \
  assessment get --plan-id {plan_id} --hash-id {hash_id} [--any-checkout]

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

All commands return TOON format. Every payload **computed against the store** additionally carries the four store-state fields documented in **Store Resolution and the Store States** above (`store_resolution`, `store_path`, `findings_store_state`, `unresolved_store`), so a count is never reported without the substrate it was computed from.

The one class of payload that carries none is an **argument-validation rejection**. Those are refused before the store is resolved at all, so they report nothing about the store and publish nothing about it; the request never reached a substrate to describe. Every payload that reports a count, a record, a not-found verdict or a write outcome carries all four.

**Add response**:
```toon
status: success
hash_id: a3f2c1
type: bug
store_resolution: cwd_relative
store_path: /repo/.plan/local/plans/EXAMPLE-PLAN/artifacts/findings
findings_store_state: present
unresolved_store: false
```

**Query response**:
```toon
status: success
plan_id: EXAMPLE-PLAN
total_count: 30
filtered_count: 15
store_resolution: cwd_relative
store_path: /repo/.plan/local/plans/EXAMPLE-PLAN/artifacts/findings
findings_store_state: present
unresolved_store: false

findings[15]{hash_id,type,title,resolution}:
a3f2c1,bug,Null check missing,pending
b4e3d2,sonar-issue,TODO comment,fixed
```

**Unreached-store refusal** (any verb, when `plans/{plan_id}/` is absent under the resolved root):
```toon
status: error
error: findings_store_unresolved
plan_id: EXAMPLE-PLAN
message: "plan directory /repo/.plan/local/plans/EXAMPLE-PLAN is absent under the resolved root /repo/.plan/local, so the findings store for plan 'EXAMPLE-PLAN' was never reached"
store_resolution: cwd_relative
store_path: /repo/.plan/local/plans/EXAMPLE-PLAN/artifacts/findings
findings_store_state: plan_absent
unresolved_store: true
```

⛔ **Read `findings_store_state` before reading any count.** A `total_count: 0` is trustworthy only under `present` or `missing`; it is never emitted under `plan_absent` or `unknown`, where the surface refuses instead. Branching on the count alone re-creates the defect this discriminator removes.

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

**Preference-narrowed query response** (`list --preference-admissible`, with or without `--include-qgate`): the same shape as above, plus `preference_admissibility_basis` naming which authorship check actually ran.

```toon
status: success
plan_id: EXAMPLE-PLAN
total_count: 30
filtered_count: 9
preference_admissibility_basis: recognized
```

⛔ **Read `preference_admissibility_basis` before treating the narrowed set as authorship-validated.** `recognized` means every kept `pr-comment` was checked against the live registry-derived reviewer set. `presence_only` means that registry was unresolvable and the rule degraded: the kept comments carry a `bot_kind`, but nothing validated it, so a legacy or de-registered identity is in the set. The field is emitted only when `--preference-admissible` is on — its absence means the narrowing did not run, never that the strong check did.

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

The canonical argparse surface for `manage-findings.py`. ⛔ **No build-gating rule
checks this section.** `manage-findings` is in `_EXCLUDED_SKILLS`, so
`missing-canonical-block` never sees the file at all — deleting this whole section
emits nothing. `manage-invocation-invalid` does scan the file, but skips every
`manage-findings` notation in it, so the forms below are not validated against the
live argparse surface. The rule that targets this skill,
`manage-findings-invocation-invalid`, is not in the `quality-gate` roster and runs
only on the per-component `analyze` path. Consuming skills xref this section by
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
  [--file-pattern PATTERN] [--include-qgate] [--author AUTHOR] [--kind KIND] \
  [--bot-kind BOT_KIND] [--preference-admissible] [--any-checkout]
```

### get

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings get \
  --plan-id PLAN_ID --hash-id HASH_ID [--any-checkout]
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
  [--resolution RESOLUTION] [--source SOURCE] [--iteration N] [--any-checkout]
```

### qgate resolve

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate resolve \
  --plan-id PLAN_ID --hash-id HASH_ID --resolution RESOLUTION --phase PHASE \
  [--detail TEXT]
```

### qgate resolve-evidenced

Evidence-gated batch resolution for the self-review loop-back (D3). Transitions
every pending Q-Gate finding of `--phase` whose `file_path` is in the supplied
`--changed-path` set to `fixed`; leaves every pending finding whose file was NOT
touched (or that carries no `file_path`) at `pending`. `--changed-path` is the
landed-fix evidence — the caller computes it (e.g. `git diff --name-only
{prior_anchor}..HEAD`). Returns `{status, phase, resolved[], left_pending[]}`.

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings qgate resolve-evidenced \
  --plan-id PLAN_ID --phase PHASE \
  [--changed-path PATH ...] [--evidence-sha SHA]
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
  [--file-pattern PATTERN] [--any-checkout]
```

### assessment get

```bash
python3 .plan/execute-script.py plan-marshall:manage-findings:manage-findings assessment get \
  --plan-id PLAN_ID --hash-id HASH_ID [--any-checkout]
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
| `findings_store_unresolved` | `plans/{plan_id}/` is absent under the resolved root (`findings_store_state: plan_absent`), or no runtime-state root resolved at all (`unknown`). Returned by every surface — read, write and `add` — instead of a clean zero or a manufactured store. |
| `finding_in_other_store` | The `hash_id` is absent from the plan-findings file set but present in a sibling store. The payload names the store (`found_in`) and the verb that owns it (`use_verb`); the sibling record is left byte-identical. |

## Related

- `manage-lessons` — Promotion target for bug, improvement, anti-pattern, triage findings
- `manage-architecture` — Promotion target for tip, insight, best-practice findings (via `enrich` commands)
- `manage-status` — Plan lifecycle tracking complementing findings resolution
