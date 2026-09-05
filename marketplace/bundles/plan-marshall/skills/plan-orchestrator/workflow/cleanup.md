# Cleanup Verb Workflow

Workflow doc for the `cleanup` verb: review and reconcile the epic's **spec corpus**, then sequence the ledger-compaction stage, the archive step, and a restart-readiness verdict, emitting one report. The binding contract — the verb-name settlement, the subject boundary, the apply-policy per finding class, the phase-order invariant, the running-row exclusion, and the verdict-persistence rule — is owned by [`persona-plan-orchestrator/standards/orchestration-model.md` § Cleanup Contract](../../persona-plan-orchestrator/standards/orchestration-model.md#cleanup-contract); this doc implements it and xrefs those statements rather than restating them. When this doc and the standard disagree, the standard wins.

**Phase order is an invariant, not a preference**: corpus → ledger → archive → restart-readiness. The rationale — compacting the ledger first relocates settled narrative the corpus pass is about to contradict — is stated once at [§ Cleanup Contract](../../persona-plan-orchestrator/standards/orchestration-model.md#cleanup-contract) and is not repeated here.

## Exit-code convention for every script call

The exit-code contract for every `python3 .plan/execute-script.py` call in this document — of EVERY notation, not only `manage-*` — is stated once in [`tools-script-executor/standards/exit-code-convention.md`](../../tools-script-executor/standards/exit-code-convention.md); it is not restated here.

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

**Zero-claim branch.** A claim section the parser cannot read yields no parsed claims, so a `corpus set-verdict --claim-index N` call above is refused with `error: claim_index_out_of_range`. That refusal is this branch's trigger — it is what this step observes, and it carries what to do next: `claims_total: 0`, the observed `claim_section_state`, and a `recovery` field naming the alternative address. When `claim_section_state` is `unreadable`, re-issue the call once with `--section-scope` instead, settling the section as a whole with the same producer. This is an addressing change only: the claim prose is not re-authored, and no spec is asked to convert its section into bullets in order to be settled. A section whose state is `absent` or `empty` needs no call at all — it admits already.

When the corroboration returned no verdict for such a spec at all, no call is issued and no refusal is seen, so the section stays unsettled. That is not a silent pass: the unreadable section contributes a blocking row to `corpus verdicts`, which [`orchestrate.md`](orchestrate.md) Step 4's prep-ready test refuses to emit on.

The field's grammar is defined once at [§ Re-Grounding Verdict Field](../../persona-plan-orchestrator/standards/orchestration-model.md#re-grounding-verdict-field) and is restated nowhere here — not its keys, not its value sets, not the parse rule both sides use. **This doc never hand-writes the field**: `corpus set-verdict` is the only sanctioned emitter, so the single-emitter property holds at the producer as well as inside the script.

This split is the Dispatch Decision Rule made operational: the dispatched leaf returns verdicts (write-free, so it passes the write-freedom test) and the inline orchestrator performs the write through the seam.

**Persist every verdict, not only refutations.** A recorded `corroborated` is what lets the next reader distinguish *checked and held* from *never checked*, and that distinction is the whole point of the field.

#### The declared-surface half of the same pass

Re-grounding has two halves, and until now only the claim half ran. A spec's `## Expected Surface` is written once at staging and never revisited, so scope the plan or a later fold added cannot reach it — and the disjointness gate reads exactly that declaration. This step therefore CONSUMES the single reader alongside the claim parse; it never re-derives a surface of its own:

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator corpus surfaces \
  --slug {slug}
```

Two findings come out of that read, and both route to the **Wrong surface / understated surface — apply — correct the Expected Surface** row of the apply-policy table (see [§ Cleanup Contract](../../persona-plan-orchestrator/standards/orchestration-model.md#cleanup-contract)); neither is a new class:

- **Unresolvable** — the row's `derivation_status` is in the indeterminate set (`derived`, `prose`, `absent`, `unreadable`), so the spec declares nothing the gate can compare and its clean gate reading is SILENCE rather than a checked negative. Correct the section in place so it resolves, or — when the surface genuinely is a function of other plans' — leave the `derived` declaration and record that the spec is deliberately unpickable until those land.
- **Understated** — the spec's own narrative names files its `## Expected Surface` does not. The declaration is corrected to match the narrative, in place.

**The running-row exclusion applies unchanged.** A spec whose ledger row is `running` is enumerated and reported as excluded, never re-scoped — a plan in flight owns its own scope, and re-scoping it underneath would be the ledger overwriting a live plan's declaration.

**Verify by re-reading, not by inspecting the edit.** The apply-policy table's own rationale for this row is *verifiable by re-running the sweep*, so re-run `corpus surfaces` after the corrections and report the before/after over the same `specs_total`. A correction that did not move its own metric did not land, whatever the diff shows.

⛔ **The two finding classes above need DIFFERENT metrics, and reading both against `indeterminate_count` would reject a correct fix.** `indeterminate_count` moves only when a spec crosses between an indeterminate status and `declarative`, so it is the instrument for the **Unresolvable** class alone. An **Understated** spec is already `declarative` — that is what makes its declaration comparable and its omission invisible — so adding the missing paths leaves `indeterminate_count` unchanged, and a rule keyed on that count alone would report a landed correction as unlanded. Verify an understated correction against the **claimed surface** instead, and verify it by MEMBERSHIP, not by cardinality: every path the correction added must appear as its own row in the payload's `claimed[]` list, matched on that row's `plan_id` and `path`. The before/after `claimed_count` is a **secondary cardinality cross-check only** — it rises by one whichever path was added, so a correction that added a *different* path than the fold requires moves the count exactly as a correct one does while the required path stays absent from `claimed[]`, and the gate goes on comparing the wrong surface. That is this step's own defect re-entering through its verification instrument, which is why the count may corroborate a membership check and may never stand in for one. Both readings come out of the same single `corpus surfaces` read; no second sweep is needed.

⛔ **A spec deliberately left `derived` is EXEMPT from the metric-movement rule, and the exemption is named rather than inferred from an unmoved count.** The Unresolvable branch above permits a genuinely derived declaration to stand, and such a spec stays indeterminate by construction — `derived` is in the indeterminate set, so `corpus surfaces` reports `admits_disjointness_check: false` for it and counts it in `indeterminate_count` on every run, before and after. An unmoved `indeterminate_count` therefore has two causes that read identically: a correction that failed to land, and a spec that was deliberately not corrected. Decompose the residual rather than reading it as a failure — name each deliberately-derived spec in the before/after, so the count that did not move is accounted for by name. ⚠ The record that licenses the exemption is the decision line [`analyze.md`](analyze.md) asks for, and it is an **authoring rule with no machine backstop**: `manage-logging decision` stores free-form text and no verb reads or validates it, so at the gate a recorded deliberate fold is indistinguishable from an unrecorded one. Saying so is what this doc owes; a validated decision record is an epic-level mechanism, not this step's.

⛔ **This reconciles the DECLARED side only, and the boundary is a disjointness rather than an overlap to resolve later.** Two surfaces describe one plan and they are reconciled by different owners on different triggers:

| | Declared side — *this step* | Realized side — the plan lifecycle's |
|---|---|---|
| Artifact | the spec's `## Expected Surface` | the plan's `references.affected_files` and the footprint resolver |
| Store | the orchestrator store | the plan store |
| Producer | the orchestrator's own fold and re-grounding acts | the plan, derived from worktree git state |
| Trigger | a drain, or this cleanup pass | plan execution |

They meet at exactly ONE point: the COMPARISON between the two, which is a read of both and is owned by neither. This step therefore never rewrites `references.affected_files`, and the plan lifecycle never rewrites a spec's `## Expected Surface`. Building one mechanism to reconcile both would put a single writer across two stores on two unrelated triggers, which is why the split is stated here rather than left to converge.

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

The ledger-compaction stage. Its binding contract — the derivable-versus-narrative discriminator, the GENERATED-marker mechanism, the annotation-zone rule, the `## Decisions` authority, the `settled.md` relocation target, idempotence, and the closed-epic refusal — is owned by [§ Ledger-Compaction Stage](../../persona-plan-orchestrator/standards/orchestration-model.md#ledger-compaction-stage); the deterministic surface (arguments, error codes, report shape) is [`plan-orchestrator/SKILL.md`](../SKILL.md) § Canonical invocations → `compact`.

⛔ **Read the epic's phase FIRST, before either judgement block.** Both judgement blocks write `epic.md` directly and both run BEFORE the script, so the script's own `refused_closed` does not protect them — by the time it fires, the frozen ledger has already been hand-edited. No other `cleanup` step carries a phase gate either, so a closed-but-not-yet-archived epic reaches this step with an active store tree:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read \
  --plan-id {slug} --store orchestrator
```

When `phase == closed`, **skip Phase B in its entirety** — both judgement blocks and the script call — and report `ledger_compaction: refused_closed`. Compaction is a live-epic operation, and `close` sealed that tree as the audit record.

⛔ **Fail closed on an unreadable phase.** A `manage-status read` that errors, or a payload carrying no `phase`, is *unobserved*, NOT *not-closed* — and the whole point of this gate is that the writes it guards happen before anything else can refuse them. Skip Phase B and report `ledger_compaction: indeterminate` with the read's own error, rather than proceeding on the assumption that a phase you could not read is a live one.

The stage has two halves along the derivable-versus-narrative split, and the split IS the dispatch boundary. **Two judgement blocks** — settled-narrative relocation and the marker migration — are inline, orchestrator-performed, never dispatched and never through the script; **derivable regeneration** is the deterministic half. Run the two judgement blocks in the order they appear below.

**The order is not load-bearing, and the reason is an invariant rather than a convention:** an annotation zone is a LIVE working surface and is therefore never a relocation candidate (see the ⛔ in the relocation block). So relocation cannot carry away the zone the migration writes into, and the migration cannot create a section relocation would then sweep. Either order yields the same ledger; the stated order is for reproducibility of the report, not for safety.

**Settled-narrative relocation (judgement — inline).** Identify each `epic.md` section whose subject is **closed** — a shipped plan's residue, a resolved defect — and bulky enough to relocate. A section is settled only when its subject is closed, ⛔ **never merely because it is old**: a retraction, a refutation, and a do-not-re-derive note are the anti-rework record and stay reachable, relocated but never dropped. ⛔ **An annotation zone is NEVER a relocation candidate** — neither `### Annotations` nor `### Queue annotations`, whatever their contents' subjects. They are live working surfaces the generator's neighbours write into every pass, not narrative about a closed subject; relocating one would carry away the destination the marker migration below needs and leave a pointer where a working zone belongs. ⛔ **Do not apply the settled-versus-live call silently on a first run** — present the proposed relocations to the operator for confirmation; when no operator is reachable, relocate nothing this pass and record that the judgement was deferred (a deferred relocation is safe; a wrong one is not). For each confirmed section, move its body **verbatim** into `settled.md` (a live-epic sibling of `history.md`, created under the [direct-file-write carve-out](../../persona-plan-orchestrator/standards/orchestration-model.md#carve-outs)) under a `## {Heading}`, and leave a pointer at the origin naming that heading in double quotes so the reachability check resolves it:

```text
> ↪ Relocated to `settled.md` § "{Heading}" — {one-line reason the subject is settled}
```

This is inline-only: it is the judgement-heaviest and least-reversible act here and it writes the ledger, so it fails the [Dispatch Decision Rule](../../persona-plan-orchestrator/standards/orchestration-model.md#dispatch-decision-rule)'s write-freedom test. No sub-step of this phase is dispatchable.

**One-time marker migration (judgement — inline, and BEFORE the script call).** The script refuses to insert markers into a hand-authored document, so an `epic.md` scaffolded before a marker pair shipped never gets that block regenerated — it is reported `markers_absent` every pass, and its owning section is reported `markers_absent_not_regenerated` (unless the owning heading is itself absent, in which case there is no abstained row at all and the `markers_absent` outcome in `compaction_regenerated[]` is the only signal). The remedy is a one-time structural edit the orchestrator makes itself, under the [direct-file-write carve-out](../../persona-plan-orchestrator/standards/orchestration-model.md#carve-outs), never through the script.

⛔ **This applies to EVERY generated block, not only the queue.** `GENERATED_BLOCKS` names two, and a pre-marker ledger is usually missing both. Each has its own owning section and its own annotation zone, and the migration is per block:

| Block | Owning section | Annotation zone | What the pair wraps |
|---|---|---|---|
| `resume-summary` | `## START HERE` | `### Annotations` | the section's existing summary body (resume anchor, phase, inbox lines) |
| `ordered-queue` | `## Ordered Queue` | `### Queue annotations` | the existing queue table, header row through last data row |

Migrating only the queue leaves `resume-summary` in exactly the permanent-refusal state this block exists to end.

**Two rules, each with its own condition.** Both are inline and both run BEFORE the script call below. ⛔ **Both conditions are read over the WHOLE `epic.md`, not within the owning section** — that is the same scope `_marker_indices` uses, and it is what makes them genuinely exclusive: Rule 1 requires that block's pair ABSENT from the file, Rule 2 requires it PRESENT. Reading Rule 1's condition section-locally would let a stale pair elsewhere in the file satisfy both rules at once, and the script would then regenerate the stale copy and leave the real one duplicated. **At most one applies per block; neither applying is normal.** They are not complements — a ledger with the pair present and no hand-written line between the markers matches neither. Rule 2 is not a sub-step of Rule 1.

⛔ **Only Rule 1 is one-time; Rule 2 is checked EVERY pass.** Rule 1's precondition self-destructs — inserting the markers is what makes them present, so it can never fire again for that block. Rule 2's does not: a hand-written line can land between the markers at any later time, and the only thing that catches it before the next regeneration overwrites it is checking. Read "one-time migration" as naming Rule 1's character, never as licence to skip Rule 2's check.

**Rule 1 — insert the marker pair.** Applies to a block when **both** hold: `epic.md` carries that block's owning section, AND the file carries no `<!-- BEGIN GENERATED: {block} -->` marker. (No owning section means nothing to wrap: Rule 1 does not apply, and the block's `markers_absent` outcome is reported without an abstained row.) Its **two steps**, in this order:

1. **First, move any non-derivable content out of what the pair will wrap** — per-row `Notes` for the queue, hand-written annotation for the summary — into that block's annotation zone. The generator owns every byte between the markers and re-derives the content from `status.json`, so anything inside the block when the markers go in is overwritten on the first pass; the zone sits outside the markers and survives verbatim.
2. **Then insert the marker pair** — `BEGIN` immediately above the wrapped content's first line and `END` immediately below its last, so the next script call finds the block and regenerates it.

**Rule 2 — evacuate hand-written content already inside the markers.** Applies to a block when the file carries its marker pair AND a hand-written line sits between `BEGIN` and `END`. Move that line into that block's annotation zone, before the script call below, for the same reason: the region is the generator's, so the content is lost on the next pass unless it is moved out first.

**Creating an absent annotation zone.** Both rules move content into a zone that a pre-marker `epic.md` usually lacks, since the zones and the markers shipped together. **Create it only when the rule that applies to that block has something to put in it** — an absent zone with nothing to move into it is not a defect, and an empty zone added speculatively is noise. Where it must be created, position it by the rule that is firing:

- **Under Rule 2** (the pair is present): **immediately after that block's `END` marker**. Placing it after the wrapped content here would put it between the last wrapped line and `END` — inside the generated region, which is the exact loss this instruction exists to prevent.
- **Under Rule 1** (the pair is absent): **immediately after the content the pair will wrap**. There is no `END` to position against at step-1 time; step 2 then inserts `END` immediately below that content — between it and the zone — so the zone ends up outside the pair.

⛔ **Do not fabricate content.** Rule 1's markers go around what is already there; the script re-derives the contents from `status.json` on the next call. Inserting a marker pair around invented rows would make the migration itself the lossy act it exists to prevent.

**The safety net, not a substitute for the move.** `cmd_compact`'s `regenerated[]` rows carry `replaced_body` — the pre-write between-marker text — for every block whose outcome is `regenerated`. So a first pass over an already-annotated ledger NAMES the content it overwrote rather than reporting only a line-count delta, and an operator can recover a line Rule 2 missed. Read it whenever a first pass reports `regenerated` on a ledger you did not just migrate.

**Derivable regeneration and invariant verification (deterministic — the script).** Call the compaction script; do **not** re-implement it (two implementations of ledger compaction is a worse outcome than no verb at all). It regenerates the START-HERE resume summary and the Ordered Queue table in place, leaves every byte outside the markers untouched, verifies the invariants, and reports:

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator compact \
  --slug {slug}
```

Report `ledger_compaction: compacted`, and fold the stage's `regenerated[]`, `invariants[]`, and `abstained[]` into this report as `compaction_regenerated[]`, `compaction_invariants[]` and `compaction_abstained[]` — all three **required, never omitted**, emitted empty when the stage produced no rows. **Record every migration rule that fired in `compaction_migrated[]`** (also required, also emitted empty when none did): the script ran after the migration and cannot see it, so this array is the only place a direct structural write to `epic.md` is named. Carry each `compaction_abstained[]` row's `treatment` through verbatim: a `markers_absent_not_regenerated` row is a surface the stage COULD NOT REACH, and reporting it as `preserved_verbatim` would claim an abstention nobody chose. Every relocation the judgement half applied is named in `applied[]` with its source and destination, per the apply-policy. A `violated` invariant is acted on here, not swallowed (a `relocated_pointer_reachable: violated` means a pointer names a heading `settled.md` does not carry — fix the pointer or the heading and re-run); an `indeterminate` one is an unobservable check, never a failure. The stage independently refuses a closed epic (`refused_closed`) at the script boundary — but that refusal protects only the script's own write, which is why the phase gate at the top of this step runs before the two judgement blocks rather than relying on it.

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
ledger_compaction: compacted | refused_closed | indeterminate
ledger_compaction_reason: "manage-status read returned file_not_found"
compaction_regenerated[R]{surface,outcome,lines_before,lines_after,replaced_body}:
  ordered-queue,regenerated,7,9,"| 1 | PLAN-04 | WS-01 | staged | scripts/a.py |"
compaction_invariants[I]{invariant,verdict,evidence,population}:
  queue_spec_bidirectional,ok,"queue and specs reconcile both ways","4 queue row(s) and 4 spec file(s)"
compaction_abstained[B]{section,treatment}:
  Decisions,preserved_verbatim
compaction_migrated[M]{block,rule,zone_created,moved_lines}:
  ordered-queue,rule-1,true,3
archive_drain: refused
archive_drain_reason: "no epic-wide quiescence signal — closed_senders is per-sender only"
restart_verdict: ready | not_ready | indeterminate
resume_anchor: "{next action}"
```

`display_detail` is ≤80 chars, ASCII, no trailing period.

Every per-spec row in `regrounded[]` carries its own `claims_scanned` population, so a row of zeros states which zero it is. `applied[]` names a source and a destination for every move — a silent application is indistinguishable from a lossy one. `declined[]` is a **required field, never omitted**: a clean report that hides a skip is exactly the failure this epic files against everyone else, so a run that declined nothing emits an empty `declined[]` rather than dropping the key.

`compaction_regenerated[]`, `compaction_invariants[]` and `compaction_abstained[]` carry the compact stage's own `regenerated[]`, `invariants[]` and `abstained[]` through into this report unchanged (`compaction_migrated[]` is the fourth `compaction_*` key and is NOT one of these — it is this step's own, described below) — `replaced_body` included, since dropping it at this boundary would put the line-count delta back in place of the content it names — and each is **required and never omitted** for the same reason `declined[]` is — a run that regenerated nothing, hit no invariant, or abstained from nothing emits the empty array rather than dropping the key, because an absent key is indistinguishable from a check that never ran. `compaction_abstained[]`'s `treatment` distinguishes a **choice** (`preserved_verbatim` — the section carries no derivable surface) from a **blind spot** (`markers_absent_not_regenerated` — the section owns a derivable surface whose marker pair is absent, so the stage could not reach it); the stage counts them apart as `abstained_count` and `unreachable_count`, and this report must not collapse them.

`ledger_compaction_reason` pairs with `ledger_compaction` exactly as `archive_drain_reason` pairs with `archive_drain`, and for the same stated reason: it is what lets an operator reading a clean report tell a compaction that was not needed from one that was REFUSED or could not be attempted. It carries the refusal's own words — the phase for `refused_closed`, the failing read's error code for `indeterminate` — and is empty for `compacted`.

`compaction_migrated[]` is **this step's own** array, not the script's — the script cannot see the migration, because the migration ran before it and left no trace the script reads. It is **required and never omitted**, emitted empty when no rule fired. Without it a correct migration and an omitted one are indistinguishable in the report: `replaced_body` names what the SCRIPT overwrote, which after a correct migration is empty of the moved content precisely because the move succeeded. One row per block a rule fired on, naming which rule, whether the annotation zone had to be created, and how many lines were moved. ⛔ A direct structural write to `epic.md` under the carve-out is exactly the class this report may not leave silent — "a silent application is indistinguishable from a lossy one" is this document's own rule, and it binds its own writes first.
