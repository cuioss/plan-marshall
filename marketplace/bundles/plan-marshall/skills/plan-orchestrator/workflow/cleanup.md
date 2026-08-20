# Cleanup Verb Workflow

Workflow doc for the `cleanup` verb: review and reconcile the epic's **spec corpus**, then sequence the ledger-compaction stage, the archive step, and a restart-readiness verdict, emitting one report. The binding contract — the verb-name settlement, the subject boundary, the apply-policy per finding class, the phase-order invariant, the running-row exclusion, and the verdict-persistence rule — is owned by [`persona-plan-orchestrator/standards/orchestration-model.md` § Cleanup Contract](../../persona-plan-orchestrator/standards/orchestration-model.md#cleanup-contract); this doc implements it and xrefs those statements rather than restating them. When this doc and the standard disagree, the standard wins.

**Phase order is an invariant, not a preference**: corpus → ledger → archive → restart-readiness. The rationale — compacting the ledger first relocates settled narrative the corpus pass is about to contradict — is stated once at [§ Cleanup Contract](../../persona-plan-orchestrator/standards/orchestration-model.md#cleanup-contract) and is not repeated here.

## Inputs

| Parameter | Required | Description |
|-----------|:--------:|-------------|
| `slug` | Yes | Epic slug of an existing epic. |

## Dispatch

Per the [Dispatch Decision Rule](../../persona-plan-orchestrator/standards/orchestration-model.md#dispatch-decision-rule), this verb names which sub-steps are dispatchable and which are not; it does not restate the three tests, the safety constraints, or the fall-back clause.

- **Dispatchable** — the **verdict half of A1 only**: corroborating each spec's verify-first clauses against the implementing source at HEAD. It reuses [`analyze.md` Step 2](analyze.md)'s corroboration dispatch verbatim — the same `execution-context-{level}` vehicle, the same `orchestrator.analyze` effort surface, and the same `corroborations[N]{claim,verdict,evidence}` return shape — so no second corroboration mechanism is introduced. The leaf returns verdicts and writes nothing, which is what lets it pass the write-freedom test.
- **Inline-only** — every apply (A2 through A5), every ledger write including each `corpus set-verdict` call, **A5 in full**, and Phases B, C and D.

## Workflow

### Step 1: Push the orchestrator terminal title

Per the [Terminal-Title Repaint Contract](../../persona-plan-orchestrator/standards/orchestration-model.md#terminal-title-repaint-contract), push the `Orchestrator-{SlugName}` title through the platform-runtime seam before the verb's first read:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime session push-title-token \
  --store orchestrator --slug {slug}
```

### Step 2: Enumerate the corpus (Phase A entry)

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator corpus enumerate \
  --slug {slug}
```

The returned payload is the population every later count in the report is computed over: `rows_total` / `specs_total` are the denominators, `rows_without_spec` and `specs_without_row` are the two reconciliation directions, and `unreadable` names every spec the pass could not read. A row carrying `excluded_reason: running` is enumerated and reported as excluded — never silently omitted, per the running-row exclusion in [§ Cleanup Contract](../../persona-plan-orchestrator/standards/orchestration-model.md#cleanup-contract).

### Step 3 (A1): Re-ground each staged spec against HEAD

For every enumerated spec whose row is NOT `running`, corroborate its verify-first clauses against the implementing source at the current HEAD. The corroboration is [`analyze.md` Step 2](analyze.md)'s, reused verbatim: the same vehicle, the same effort surface, and the same `corroborations[N]{claim,verdict,evidence}` return with the closed `corroborated` / `contradicted` / `unverifiable` vocabulary. No second verdict vocabulary is introduced anywhere in this verb.

**Persist every returned verdict**, one `corpus set-verdict` call per claim, with the producer recorded as `{slug}/cleanup` — see [`plan-orchestrator/SKILL.md`](../SKILL.md) § Canonical invocations → `corpus set-verdict` for the argument surface.

The field's grammar is defined once at [§ Re-Grounding Verdict Field](../../persona-plan-orchestrator/standards/orchestration-model.md#re-grounding-verdict-field) and is restated nowhere here — not its keys, not its value sets, not the parse rule both sides use. **This doc never hand-writes the field**: `corpus set-verdict` is the only sanctioned emitter, so the single-emitter property holds at the producer as well as inside the script.

This split is the Dispatch Decision Rule made operational: the dispatched leaf returns verdicts (write-free, so it passes the write-freedom test) and the inline orchestrator performs the write through the seam.

**Persist every verdict, not only refutations.** A recorded `corroborated` is what lets the next reader distinguish *checked and held* from *never checked*, and that distinction is the whole point of the field.

### Step 4 (A2): Applicability — an already-fixed spec needs a positive account

A spec may be marked already-fixed only on a **positive account of what closed the defect** — the commit, the PR, or the named symbol that now carries the behaviour. An absent symbol is equally explained by a fix, a rename, and a file move, so absence alone never settles applicability. A spec that cannot be given a positive account is left staged and reported, not retired.

### Step 5 (A3): Ambiguity

Over the population `corpus enumerate` published — never over an ad-hoc re-scan — flag each spec missing an Objective, an Expected Surface, or a claim label, and apply the action the apply-policy table assigns to the ambiguity class (see [§ Cleanup Contract](../../persona-plan-orchestrator/standards/orchestration-model.md#cleanup-contract)).

### Step 6 (A4): Duplication

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator corpus cross-check \
  --slug {slug}
```

The verb reports candidates over three named populations — sibling epics (active and archived), the live plan set, and this epic's own corpus — and applies nothing. Superseding is this doc's inline, ledger-writing act, per the duplication row of the apply-policy table. ⛔ **No spec file is ever deleted**: the retired spec is the audit record of why it was retired.

### Step 7 (A5): Distribution — component-first, task-second

Regroup the corpus by **component first and task second**, and record each move in `applied[]` with its source and its destination. Two guards apply to every merge:

- **A weak merge is labelled weak in its own header** and is licensed to split back at outline. A merge the orchestrator is not confident in is recorded as such rather than presented as settled.
- **A merged spec re-counts its deliverables.** Overlapping deliverables collapse rather than concatenate, so the merged spec's count is re-derived rather than summed — and the [Scope-Bloat Split Guard](../../persona-plan-orchestrator/standards/orchestration-model.md#scope-bloat-split-guard) is evaluated against the re-derived count.

A5 is inline-only in full: it is the judgement-heaviest class and the only one that is hard to reverse.

### Step 8 (Phase B): Compact the ledger

The ledger-compaction stage. Its binding contract — the derivable-versus-narrative discriminator, the GENERATED-marker mechanism, the annotation-zone rule, the `## Decisions` authority, the `settled.md` relocation target, idempotence, and the closed-epic refusal — is owned by [§ Ledger-Compaction Stage](../../persona-plan-orchestrator/standards/orchestration-model.md#ledger-compaction-stage); the deterministic surface (arguments, error codes, report shape) is [`plan-orchestrator/SKILL.md`](../SKILL.md) § Canonical invocations → `compact`. The stage has two halves along the derivable-versus-narrative split, and the split IS the dispatch boundary. Three blocks follow, and they map onto those two halves rather than being three halves: **settled-narrative relocation** and the **one-time marker migration** are both the judgement half — inline, orchestrator-performed, never dispatched and never through the script — and **derivable regeneration** is the deterministic half. Within the judgement half do the marker migration **first**: the relocation moves narrative sections wholesale, and doing it after the migration risks relocating an annotation zone the migration has just written into.

**Settled-narrative relocation (judgement — inline).** Identify each `epic.md` section whose subject is **closed** — a shipped plan's residue, a resolved defect — and bulky enough to relocate. A section is settled only when its subject is closed, ⛔ **never merely because it is old**: a retraction, a refutation, and a do-not-re-derive note are the anti-rework record and stay reachable, relocated but never dropped. ⛔ **Do not apply the settled-versus-live call silently on a first run** — present the proposed relocations to the operator for confirmation; when no operator is reachable, relocate nothing this pass and record that the judgement was deferred (a deferred relocation is safe; a wrong one is not). For each confirmed section, move its body **verbatim** into `settled.md` (a live-epic sibling of `history.md`, created under the [direct-file-write carve-out](../../persona-plan-orchestrator/standards/orchestration-model.md#carve-outs)) under a `## {Heading}`, and leave a pointer at the origin naming that heading in double quotes so the reachability check resolves it:

```text
> ↪ Relocated to `settled.md` § "{Heading}" — {one-line reason the subject is settled}
```

This is inline-only: it is the judgement-heaviest and least-reversible act here and it writes the ledger, so it fails the [Dispatch Decision Rule](../../persona-plan-orchestrator/standards/orchestration-model.md#dispatch-decision-rule)'s write-freedom test. No sub-step of this phase is dispatchable.

**One-time marker migration (judgement — inline, and BEFORE the script call).** The script refuses to insert markers into a hand-authored document, so an `epic.md` scaffolded before the `ordered-queue` marker pair shipped never gets its queue regenerated — the block is reported `markers_absent` every pass, and its owning section is reported `markers_absent_not_regenerated` rather than as an abstention. The remedy is a one-time structural edit the orchestrator makes itself, under the [direct-file-write carve-out](../../persona-plan-orchestrator/standards/orchestration-model.md#carve-outs), never through the script.

**Two rules, each with its own condition. Both are inline and both run BEFORE the script call below.** They are **mutually exclusive by construction** — Rule 1 requires the marker pair ABSENT, Rule 2 requires it PRESENT — so exactly one of them, or neither, applies to a given `epic.md`. Rule 2 is not a sub-step of Rule 1.

⛔ **Only Rule 1 is one-time; Rule 2 is checked EVERY pass.** Rule 1's precondition self-destructs — inserting the markers is what makes them present, so it can never fire again on that ledger. Rule 2's does not: a hand-written line can land between the markers at any later time, and the only thing that catches it before the next regeneration overwrites it is checking. Read "one-time migration" as naming Rule 1's character, never as licence to skip Rule 2's check.

If the `### Queue annotations` zone both rules move content into does not exist — likely on the same pre-marker `epic.md` Rule 1 addresses, since the zone and the markers shipped together — **create it**, as a `### Queue annotations` subsection of `## Ordered Queue` positioned immediately after the marker pair's `END`. Moving content into a zone that is not there is not an option, and inventing a different destination would put it back inside the region the generator owns.

**Rule 1 — insert the marker pair.** Applies **only when both hold**: `epic.md` carries a `## Ordered Queue` section, AND that section contains no `<!-- BEGIN GENERATED: ordered-queue -->` marker. When the pair is already present, Rule 1 does not apply at all. Its two steps run **in this order**:

1. **First, move any per-row `Notes` content into the `### Queue annotations` zone.** The generator owns every byte between the markers and re-derives the table from `status.json`, so a note that is inside the block when the markers go in is overwritten on the first pass; the annotation zone sits outside the markers and survives verbatim. This is first, not second: inserting the markers before the move puts the notes inside the generated region, so the move then has to reach into a block the next script call may already have overwritten.
2. **Then insert the marker pair around the existing table** — `<!-- BEGIN GENERATED: ordered-queue -->` immediately above the table's header row and `<!-- END GENERATED: ordered-queue -->` immediately below its last data row, so the next script call finds the block and regenerates it.

**Rule 2 — evacuate hand-written content already inside the markers.** Applies when the marker pair **is** present and a hand-written line sits between `BEGIN` and `END` — the case Rule 1 excludes. Move that line into the adjacent `### Queue annotations` zone, before the script call below, for the same reason: the region is the generator's, so the content is lost on the next pass unless it is moved out first.

⛔ **Do not fabricate queue rows.** Rule 1's markers go around the table that is already there; the script re-derives its contents from `status.json` on the next call. Inserting a marker pair around invented rows would make the migration itself the lossy act it exists to prevent.

**The safety net, not a substitute for the move.** `cmd_compact`'s `compaction_regenerated[]` rows carry `replaced_body` — the pre-write between-marker text — for every block whose outcome is `regenerated`. So a first pass over an already-annotated ledger NAMES the content it overwrote rather than reporting only a line-count delta, and an operator can recover a line Rule 2 missed. Read it whenever a first pass reports `regenerated` on a ledger you did not just migrate.

**Derivable regeneration and invariant verification (deterministic — the script).** Call the compaction script; do **not** re-implement it (two implementations of ledger compaction is a worse outcome than no verb at all). It regenerates the START-HERE resume summary and the Ordered Queue table in place, leaves every byte outside the markers untouched, verifies the invariants, and reports:

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator compact \
  --slug {slug}
```

Report `ledger_compaction: compacted`, and fold the stage's `regenerated[]`, `invariants[]`, and `abstained[]` into this report as `compaction_regenerated[]`, `compaction_invariants[]` and `compaction_abstained[]` — all three **required, never omitted**, emitted empty when the stage produced no rows. Carry each `compaction_abstained[]` row's `treatment` through verbatim: a `markers_absent_not_regenerated` row is a surface the stage COULD NOT REACH, and reporting it as `preserved_verbatim` would claim an abstention nobody chose. Every relocation the judgement half applied is named in `applied[]` with its source and destination, per the apply-policy. A `violated` invariant is acted on here, not swallowed (a `relocated_pointer_reachable: violated` means a pointer names a heading `settled.md` does not carry — fix the pointer or the heading and re-run); an `indeterminate` one is an unobservable check, never a failure. The stage refuses a closed epic (`refused_closed`) — but `cleanup` never reaches Phase B on a closed epic, because compaction is a live-epic operation.

### Step 9 (Phase C): Archive — retire consumed messages

⛔ **Do not drain the inbox. This phase reports the refusal; it retires no message.** The step's only executable act today is emitting `archive_drain: refused` with its reason into the report. (Settled-narrative relocation is **not** here — it is the compaction stage's, run in Phase B above.)

⛔ **This phase is NOT the `archive` verb.** [`archive.md`](archive.md) relocates a *closed epic tree*; this phase would retire consumed inbox messages inside a live epic. This phase MUST NOT call the `archive` verb.

**The refusal branch is the permanent documented default.** Three facts, stated plainly rather than as a hypothetical:

1. The emission-quiescence precondition was to be supplied by `PLAN-TRUTH-032`, whose ledger row is **`superseded`** — a superseded spec never lands.
2. **No EPIC-WIDE emission-quiescence signal exists today.** One PER-SENDER closure signal does exist and must not be mistaken for it: `inbox list` reports `closed_senders` — the senders that have filed a valid `lifecycle: stream-end` marker — alongside `live_count`. That establishes *these named senders will send no more*; it does not establish *no sender will send again*. The gap is not a matter of degree. The epic's sender population is open: a plan the orchestrator has not yet emitted, or one emitted and not yet started, is a sender that has filed nothing at all, so it appears in neither `closed_senders` nor `live_count` and is indistinguishable from a sender that does not exist. `closed_senders` covering every sender seen so far is therefore consistent with a sender about to appear, which is exactly what quiescence has to rule out. Deriving epic-wide quiescence from it would be reading a statement about the observed population as a statement about the whole.
3. The archive phase therefore **refuses to drain the inbox and says so in the report**, every run, until a successor spec supplies an epic-wide signal.

⛔ Quiescence is **never** derived from a timer, and **never** from a merge landing. Both are recorded hazards and both are prohibited derivations — a later author must not reinvent either as a convenience.

The refusal is a **first-class reported outcome, not a silent skip**: it occupies the named `archive_drain` / `archive_drain_reason` report fields, so an operator reading a clean report can tell "nothing needed draining" from "draining was refused". Draining a stale or unreachable narrative is strictly worse than deferring it, which is why refusing is the correct default rather than a degraded one.

**Deferred mechanism — not an instruction.** When a successor spec supplies the epic-wide quiescence signal, the drain needs no new machinery: the existing `inbox list` / `inbox archive` calls already enumerate and retire consumed messages, so that successor gates these two calls on its signal rather than introducing a third inbox surface. `closed_senders` is the material that successor builds ON — the per-sender half is already reported, and what it still needs is the sender-population bound fact 2 names. Both calls are recorded here as the surface that successor will reuse, and neither is run by this step:

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator inbox list \
  --slug {slug}
```

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator inbox archive \
  --slug {slug} --message {name}
```

### Step 10 (Phase D): Restart-readiness verdict

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator cleanup restart-check \
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
ledger_compaction: compacted
compaction_regenerated[R]{surface,outcome,lines_before,lines_after,replaced_body}:
  ordered-queue,regenerated,7,9,"| 1 | PLAN-04 | WS-01 | staged | scripts/a.py |"
compaction_invariants[I]{invariant,verdict,evidence,population}:
  queue_spec_bidirectional,ok,"queue and specs reconcile both ways","4 queue row(s) and 4 spec file(s)"
compaction_abstained[B]{section,treatment}:
  Decisions,preserved_verbatim
archive_drain: refused
archive_drain_reason: "no epic-wide quiescence signal — closed_senders is per-sender only"
restart_verdict: ready | not_ready | indeterminate
resume_anchor: "{next action}"
```

`display_detail` is ≤80 chars, ASCII, no trailing period.

Every per-spec row in `regrounded[]` carries its own `claims_scanned` population, so a row of zeros states which zero it is. `applied[]` names a source and a destination for every move — a silent application is indistinguishable from a lossy one. `declined[]` is a **required field, never omitted**: a clean report that hides a skip is exactly the failure this epic files against everyone else, so a run that declined nothing emits an empty `declined[]` rather than dropping the key.

The three `compaction_*` keys carry the compact stage's own `regenerated[]`, `invariants[]` and `abstained[]` through into this report unchanged — `replaced_body` included, since dropping it at this boundary would put the line-count delta back in place of the content it names — and each is **required and never omitted** for the same reason `declined[]` is — a run that regenerated nothing, hit no invariant, or abstained from nothing emits the empty array rather than dropping the key, because an absent key is indistinguishable from a check that never ran. `compaction_abstained[]`'s `treatment` distinguishes a **choice** (`preserved_verbatim` — the section carries no derivable surface) from a **blind spot** (`markers_absent_not_regenerated` — the section owns a derivable surface whose marker pair is absent, so the stage could not reach it); the stage counts them apart as `abstained_count` and `unreachable_count`, and this report must not collapse them.
