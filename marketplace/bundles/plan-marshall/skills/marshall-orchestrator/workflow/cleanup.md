# Cleanup Verb Workflow

Workflow doc for the `cleanup` verb: review and reconcile the epic's **spec corpus**, then sequence the ledger-compaction stage, the archive step, and a restart-readiness verdict, emitting one report. The binding contract — the verb-name settlement, the subject boundary, the apply-policy per finding class, the phase-order invariant, the running-row exclusion, and the verdict-persistence rule — is owned by [`persona-marshall-orchestrator/standards/orchestration-model.md` § Cleanup Contract](../../persona-marshall-orchestrator/standards/orchestration-model.md#cleanup-contract); this doc implements it and xrefs those statements rather than restating them. When this doc and the standard disagree, the standard wins.

**Phase order is an invariant, not a preference**: corpus → ledger → archive → restart-readiness. The rationale — compacting the ledger first relocates settled narrative the corpus pass is about to contradict — is stated once at [§ Cleanup Contract](../../persona-marshall-orchestrator/standards/orchestration-model.md#cleanup-contract) and is not repeated here.

## Inputs

| Parameter | Required | Description |
|-----------|:--------:|-------------|
| `slug` | Yes | Epic slug of an existing epic. |

## Dispatch

Per the [Dispatch Decision Rule](../../persona-marshall-orchestrator/standards/orchestration-model.md#dispatch-decision-rule), this verb names which sub-steps are dispatchable and which are not; it does not restate the three tests, the safety constraints, or the fall-back clause.

- **Dispatchable** — the **verdict half of A1 only**: corroborating each spec's verify-first clauses against the implementing source at HEAD. It reuses [`analyze.md` Step 2](analyze.md)'s corroboration dispatch verbatim — the same `execution-context-{level}` vehicle, the same `orchestrator.analyze` effort surface, and the same `corroborations[N]{claim,verdict,evidence}` return shape — so no second corroboration mechanism is introduced. The leaf returns verdicts and writes nothing, which is what lets it pass the write-freedom test.
- **Inline-only** — every apply (A2 through A5), every ledger write including each `corpus set-verdict` call, **A5 in full**, and Phases B, C and D.

## Workflow

### Step 1: Push the orchestrator terminal title

Per the [Terminal-Title Repaint Contract](../../persona-marshall-orchestrator/standards/orchestration-model.md#terminal-title-repaint-contract), push the `Orchestrator-{SlugName}` title through the platform-runtime seam before the verb's first read:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime session push-title-token \
  --store orchestrator --slug {slug}
```

### Step 2: Enumerate the corpus (Phase A entry)

```bash
python3 .plan/execute-script.py plan-marshall:marshall-orchestrator:orchestrator corpus enumerate \
  --slug {slug}
```

The returned payload is the population every later count in the report is computed over: `rows_total` / `specs_total` are the denominators, `rows_without_spec` and `specs_without_row` are the two reconciliation directions, and `unreadable` names every spec the pass could not read. A row carrying `excluded_reason: running` is enumerated and reported as excluded — never silently omitted, per the running-row exclusion in [§ Cleanup Contract](../../persona-marshall-orchestrator/standards/orchestration-model.md#cleanup-contract).

### Step 3 (A1): Re-ground each staged spec against HEAD

For every enumerated spec whose row is NOT `running`, corroborate its verify-first clauses against the implementing source at the current HEAD. The corroboration is [`analyze.md` Step 2](analyze.md)'s, reused verbatim: the same vehicle, the same effort surface, and the same `corroborations[N]{claim,verdict,evidence}` return with the closed `corroborated` / `contradicted` / `unverifiable` vocabulary. No second verdict vocabulary is introduced anywhere in this verb.

**Persist every returned verdict**, one `corpus set-verdict` call per claim, with the producer recorded as `{slug}/cleanup` — see [`marshall-orchestrator/SKILL.md`](../SKILL.md) § Canonical invocations → `corpus set-verdict` for the argument surface.

The field's grammar is defined once at [§ Re-Grounding Verdict Field](../../persona-marshall-orchestrator/standards/orchestration-model.md#re-grounding-verdict-field) and is restated nowhere here — not its keys, not its value sets, not the parse rule both sides use. **This doc never hand-writes the field**: `corpus set-verdict` is the only sanctioned emitter, so the single-emitter property holds at the producer as well as inside the script.

This split is the Dispatch Decision Rule made operational: the dispatched leaf returns verdicts (write-free, so it passes the write-freedom test) and the inline orchestrator performs the write through the seam.

**Persist every verdict, not only refutations.** A recorded `corroborated` is what lets the next reader distinguish *checked and held* from *never checked*, and that distinction is the whole point of the field.

### Step 4 (A2): Applicability — an already-fixed spec needs a positive account

A spec may be marked already-fixed only on a **positive account of what closed the defect** — the commit, the PR, or the named symbol that now carries the behaviour. An absent symbol is equally explained by a fix, a rename, and a file move, so absence alone never settles applicability. A spec that cannot be given a positive account is left staged and reported, not retired.

### Step 5 (A3): Ambiguity

Over the population `corpus enumerate` published — never over an ad-hoc re-scan — flag each spec missing an Objective, an Expected Surface, or a claim label, and apply the action the apply-policy table assigns to the ambiguity class (see [§ Cleanup Contract](../../persona-marshall-orchestrator/standards/orchestration-model.md#cleanup-contract)).

### Step 6 (A4): Duplication

```bash
python3 .plan/execute-script.py plan-marshall:marshall-orchestrator:orchestrator corpus cross-check \
  --slug {slug}
```

The verb reports candidates over three named populations — sibling epics (active and archived), the live plan set, and this epic's own corpus — and applies nothing. Superseding is this doc's inline, ledger-writing act, per the duplication row of the apply-policy table. ⛔ **No spec file is ever deleted**: the retired spec is the audit record of why it was retired.

### Step 7 (A5): Distribution — component-first, task-second

Regroup the corpus by **component first and task second**, and record each move in `applied[]` with its source and its destination. Two guards apply to every merge:

- **A weak merge is labelled weak in its own header** and is licensed to split back at outline. A merge the orchestrator is not confident in is recorded as such rather than presented as settled.
- **A merged spec re-counts its deliverables.** Overlapping deliverables collapse rather than concatenate, so the merged spec's count is re-derived rather than summed — and the [Scope-Bloat Split Guard](../../persona-marshall-orchestrator/standards/orchestration-model.md#scope-bloat-split-guard) is evaluated against the re-derived count.

A5 is inline-only in full: it is the judgement-heaviest class and the only one that is hard to reverse.

### Step 8 (Phase B): Call the ledger-compaction stage

Call the compaction stage; do **not** re-implement it. When the stage has not landed, report `ledger_compaction: not_available` naming the component that owns the surface, and continue — the corpus phases already ran and their result is not withheld because a later stage is absent. Two implementations of ledger compaction is a worse outcome than no verb at all (see the subject boundary in [§ Cleanup Contract](../../persona-marshall-orchestrator/standards/orchestration-model.md#cleanup-contract)).

### Step 9 (Phase C): Archive — retire consumed messages, relocate settled narrative

Enumerate the inbox and retire each consumed message through the existing drain calls:

```bash
python3 .plan/execute-script.py plan-marshall:marshall-orchestrator:orchestrator inbox list \
  --slug {slug}
```

```bash
python3 .plan/execute-script.py plan-marshall:marshall-orchestrator:orchestrator inbox archive \
  --slug {slug} --message {name}
```

⛔ **This phase is NOT the `archive` verb.** [`archive.md`](archive.md) relocates a *closed epic tree*; this phase retires consumed inbox messages and relocates settled narrative inside a live epic. This phase MUST NOT call the `archive` verb.

**The refusal branch is the permanent documented default.** Three facts, stated plainly rather than as a hypothetical:

1. The emission-quiescence precondition was to be supplied by `PLAN-TRUTH-032`, whose ledger row is **`superseded`** — a superseded spec never lands.
2. **No quiescence signal exists today**, and none will arrive until a successor spec supplies one.
3. The archive phase therefore **refuses to drain the inbox and says so in the report**, every run, until that successor lands.

⛔ Quiescence is **never** derived from a timer, and **never** from a merge landing. Both are recorded hazards and both are prohibited derivations — a later author must not reinvent either as a convenience.

The refusal is a **first-class reported outcome, not a silent skip**: it occupies the named `archive_drain` / `archive_drain_reason` report fields, so an operator reading a clean report can tell "nothing needed draining" from "draining was refused". Draining a stale or unreachable narrative is strictly worse than deferring it, which is why refusing is the correct default rather than a degraded one.

### Step 10 (Phase D): Restart-readiness verdict

```bash
python3 .plan/execute-script.py plan-marshall:marshall-orchestrator:orchestrator cleanup restart-check \
  --slug {slug}
```

Each returned signal carries its own verdict, its own evidence, and the population it was derived from; the overall verdict is the floor over the participating signals. Carry that overall verdict into the report's `restart_verdict` field verbatim — an unobservable signal resolves to `indeterminate` and is never re-read as `not_ready`.

### Step 11: Log and set the resume anchor

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging decision \
  --plan-id {slug} --level INFO --message "{cleanup decision: applied/declined per spec, restart verdict}" --store orchestrator
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status update-field \
  --plan-id {slug} --field resume_anchor --value "{next action}" --store orchestrator
```

## Idempotence

**Each applied change is keyed by `(spec id, finding class)`.** A spec already carrying the applied correction for a given finding class produces no second application, so a second run immediately after the first is a no-op: its `applied[]` is empty while its per-spec verdicts are unchanged. The key is the mechanism, not an aspiration — an apply that cannot be keyed this way is not idempotent and belongs in `declined[]` with its reason.

## Output

```toon
status: success | error
display_detail: "cleanup {slug}: {A} applied, {D} declined, restart {verdict}"
slug: {slug}
rows_total: {N}
specs_total: {N}
specs_scanned: {N}
specs_excluded_running: {N}
regrounded[S]{spec,claims_scanned,corroborated,contradicted,unverifiable}:
  PLAN-01-alpha.md,4,3,1,0
applied[A]{spec,finding_class,source,destination}:
  PLAN-07-beta.md,duplication,PLAN-07-beta.md,PLAN-03-alpha.md
declined[D]{spec,finding_class,reason}:
  PLAN-09-gamma.md,redistribution,"row is running — never re-scoped mid-execution"
ledger_compaction: not_available | compacted
archive_drain: refused
archive_drain_reason: "no quiescence signal exists — PLAN-TRUTH-032 is superseded"
restart_verdict: ready | not_ready | indeterminate
resume_anchor: "{next action}"
```

`display_detail` is ≤80 chars, ASCII, no trailing period.

Every per-spec row in `regrounded[]` carries its own `claims_scanned` population, so a row of zeros states which zero it is. `applied[]` names a source and a destination for every move — a silent application is indistinguishable from a lossy one. `declined[]` is a **required field, never omitted**: a clean report that hides a skip is exactly the failure this epic files against everyone else, so a run that declined nothing emits an empty `declined[]` rather than dropping the key.
