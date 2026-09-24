# Orchestrate Workflow (status / next)

Shared workflow doc for the two queue-facing verbs: `status` (report the queue and resume state) and `next` (emit the next ready-to-run `/plan-marshall` command). The doc branches on the invoked verb after the shared read steps. The emit-only hand-off rule and the surface-disjointness rule are owned by [`persona-plan-orchestrator/standards/orchestration-model.md`](../../persona-plan-orchestrator/standards/orchestration-model.md); when this doc and the standard disagree, the standard wins.

## Exit-code convention for every script call

The exit-code contract for every `python3 .plan/execute-script.py` call in this document — of EVERY notation, not only `manage-*` — is stated once in [`tools-script-executor/standards/exit-code-convention.md`](../../tools-script-executor/standards/exit-code-convention.md); it is not restated here.

## Inputs

| Parameter | Required | Description |
|-----------|:--------:|-------------|
| `slug` | Yes | Epic slug of an existing epic. |
| verb | Yes | `status` or `next` — resolved by the SKILL router (no verb defaults to `status`). |

## Workflow

### Step 1: Push the orchestrator terminal title (shared)

Per the [Terminal-Title Repaint Contract](../../persona-plan-orchestrator/standards/orchestration-model.md#terminal-title-repaint-contract), push the `Orchestrator-{SlugName}` title through the platform-runtime seam before the first read. The `slug` is an input to both verbs, so this single shared step covers `status` and `next` alike:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime session push-title-token \
  --store orchestrator --slug {slug}
```

### Step 2: Read the queue (shared)

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator queue \
  --slug {slug}
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read \
  --plan-id {slug} --store orchestrator
```

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator resume-summary \
  --slug {slug}
```

The `queue` read returns the queue rows from `queue/{PLAN-ID}.json` in `(seq, id)` order, plus `unreadable_rows` naming any row file it could not read. The `manage-status read` returns the header and the anchor from `resume_anchor.md`. `resume-summary` renders START HERE and the Ordered Queue from the same ledger and writes nothing; its `view_current` says whether the committed `queue-view.md` still matches. A `legacy_layout` refusal from any of the three means the ledger was never migrated — run `orchestrator migrate-layout --slug {slug}` (see [`plan-orchestrator/SKILL.md`](../SKILL.md) § Canonical invocations → `migrate-layout`) before continuing.

The on-query epic discovery / store scan enumerates BOTH `.plan/orchestrator/` and `.plan/archived-orchestrators/`, and the `read` verb resolves an archived epic transparently via the read-fallback — so a slug naming an archived (closed-and-relocated) epic is still discoverable and reportable here without re-anchoring.

### Step 3 (verb = `status`): Report

Render the queue report from the Step 2 reads: per-plan status from the queue rows (staged / launched / running / parked, and the terminal rows by their own status), workstream grouping, open defects and watches from `epic.md`, and the resume anchor. An archived epic reports identically — its tree is resolved from `archived-orchestrators/` and its ledger files are the same machine authority. Name every row file `unreadable_rows` reports, rather than omitting it from the report.

When `resume-summary` reported `view_current: false`, the committed `queue-view.md` is behind the ledger; bring it level:

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator regenerate-view \
  --slug {slug}
```

When the report reveals stale prose in `epic.md` (a queue annotation disagreeing with the queue rows), correct the narrative — the reconciliation direction is always ledger files → `queue-view.md` and `epic.md`.

Skip Steps 4–6 and return.

### Step 4 (verb = `next`): Select up to `N − R` launchable plans

Read the epic's `parallelization_scope` knob — `N`, the maximum number of concurrently-launched plans, defaulting to `1` (strictly sequential) when unset:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {slug} --get --field parallelization_scope --store orchestrator
```

Count `R`, the plans currently in `launched` status, and select up to `N − R` candidates — a block sized by the scope knob rather than a hardcoded single (at the default `N = 1` that block is exactly one). Walk `staged` plans in queue order whose dependencies (sequencing notes in their `plans/PLAN-NN-{plan_slug}.md` spec) are satisfied, and admit a candidate ONLY when both admission tests pass:

- **Disjoint** — decided from the PARSER, not from a reader's judgement over the rendered `Surface (expected)` cell. The test has two halves and they come from **two different reads**, because no single verb produces both. Read the corpus's declared surfaces once:

  ```bash
  python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator corpus surfaces \
    --slug {slug}
  ```

  …and the corpus's collision rows once, in the same round:

  ```bash
  python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator corpus cross-check \
    --slug {slug}
  ```

  A candidate is disjoint **iff** ALL THREE hold: its `corpus surfaces` row carries `admits_disjointness_check: true`, `corpus cross-check` reports no `file_overlap_matches[]` row naming that candidate's spec, AND that same `corpus cross-check` payload carries `candidate_comparison_determinate: true`. Each read supplies exactly the half the other cannot: `corpus surfaces` publishes only THIS epic's own declarations — per-spec `derivation_status`, `admits_disjointness_check` and `claimed_count`, plus a flat `claimed[]` list — and carries no launched-plan surface and no intersection; `corpus cross-check` is the sole producer of the intersection, comparing each spec against the live plan set (`candidate_kind: live_plan`, whose surface is that plan's `references.json` `affected_files`), against sibling epics' specs, and against this corpus's own other specs (`candidate_kind: corpus_spec` — which is what catches a collision with a candidate already selected this round). Asking `corpus surfaces` alone for the overlap half asks it for a field it does not emit.

  **Joining a candidate to its rows.** `corpus surfaces` rows carry both `plan_id` and `spec` (the spec FILE NAME) and its `claimed[]` entries key by `plan_id`; `corpus cross-check` rows key by `spec`. A candidate reaches all three by the same `PLAN-NN-` prefix rule the prep-ready test uses — one join rule, stated once, for every test.

  ⛔ **An absent or unresolvable declaration is `indeterminate`, never `disjoint`.** `admits_disjointness_check` is `true` only for a `declarative` surface; every other `derivation_status` (`derived`, `prose`, `absent`, `unreadable`) leaves the candidate with no comparable path set, so it contributes NO row to the overlap matcher and its clean reading is SILENCE rather than a checked negative. Such a candidate is sequenced with a surface-side shortfall reason — it is never emitted on the strength of an overlap check that had nothing to compare. Governing authority: **ADR-019** (*An audit separates what it could not evaluate from what it evaluated and found wanting*, `doc/adr/`), the same rule the payload names in its own `governing_authority` field.

  ⛔ **The same rule binds the OTHER side of the comparison.** A candidate that declared nothing comparable is just as invisible to the overlap matcher as a spec that did, and the silence looks identical from the spec's row. `corpus cross-check` therefore publishes `candidate_derivation_states[]` — a `comparable` / `indeterminate` / `unreadable` tally broken down per `candidate_kind` (`sibling_epic_spec`, `live_plan`, `corpus_spec`) — beside `candidate_population[]`, the candidate count each kind's tally was computed over. Both span their whole vocabularies, so a kind this epic has no candidate of, and a state no candidate is in, report stated zeros rather than vanishing. **Read `file_overlap_matches[]` together with `candidates_indeterminate`:** an empty match list beside a non-zero indeterminate count is an UNCHECKED negative and never a clean pass, and a candidate's own derivation status is the reason. The payload names that rule in `candidate_governing_authority` (ADR-019 again). `indeterminate` and `unreadable` are held apart because they are two different zeros — a candidate that was read and declared nothing comparable, and a candidate nothing could read at all.

  ⛔ **The third conjunct is where that rule is ENFORCED, not merely read.** Publishing `candidates_indeterminate` beside an empty match list tells a reader the negative is unchecked; it does not stop the admission. `candidate_comparison_determinate` is the verdict the gate consults — true only when the WHOLE candidate population was comparable — and it **fails closed**: an indeterminate comparison refuses the candidate rather than admitting it on an unexamined population. Do NOT re-derive the verdict from the tally at this site; the payload carries it, and a reason assembled here from a count can be wrong about the very payload it is quoting.

  This is the exact defect the gate carried: a spec declaring only directories or globs resolved to zero paths under the retired reader, so the machine reported no collision against it and the gate read that silence as disjoint. A plan the gate cannot see is a plan the gate cannot serialize.
- **Prep-ready** — decided from the PARSER, not from a reader's judgement over the spec prose. Read the corpus's verdicts once:

  ```bash
  python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator corpus verdicts \
    --slug {slug}
  ```

  **Joining a candidate to its rows.** `corpus verdicts` keys each row by `spec` — the spec FILE NAME, e.g. `PLAN-01-alpha.md` — and `claim_index`; it carries no plan id. Candidate selection here works over plan ids (`PLAN-NN`). A candidate's rows are therefore the rows whose `spec` begins with that candidate's `PLAN-NN-` prefix, and that prefix join is the ONE rule relating the two. It applies wherever this payload meets a plan id, including the `stale_verdicts[T]{plan,...}` rows of the report shape below.

  A candidate is prep-ready **iff** no row of its spec carries `admits: false`. `corpus verdicts` is the field's only interpreter, so the admission outcome is a property of one parse rather than of two readers agreeing. The admission table — which of the six states admits and which blocks, and why — is defined once at [orchestration-model.md § Re-Grounding Verdict Field](../../persona-plan-orchestrator/standards/orchestration-model.md#re-grounding-verdict-field) and is not restated here.

  **A section the parser could not read now contributes such a row.** Rows are addressed at two scopes, and a spec whose `## Claim Labels` section the parser could not read — content is present, but authored as a table or as prose rather than as top-level bullets — while carrying no section-scoped verdict contributes exactly one row with `scope: section`, `claim_index: -1` and `admits: false`. Such a candidate is therefore **not** prep-ready, where previously it contributed no row at all and passed the test vacuously. The one-call remedy is `corpus set-verdict --section-scope`, which settles the section without re-authoring any claim prose; a spec is never asked to convert its section into bullets to become emittable. A section reported `absent` or `empty` contributes no row and still admits.

Four rules govern the outcome, every one of them decided by the parser rather than by a reader: an **OPEN (absent) clause does NOT fail the test** — settling it is the LAUNCHED plan's own job per [orchestration-model.md § Verify-First Contract for Inferred Claims](../../persona-plan-orchestrator/standards/orchestration-model.md#verify-first-contract-for-inferred-claims), so blocking on an unchecked clause would make the verifying phase unreachable and the spec permanently unemittable; **only a refutation the spec has not absorbed blocks**; an **`unverifiable` verdict never blocks**, because an unreachable population is not a refutation; and a **malformed field blocks**, reported as `indeterminate` with the offending line quoted, so a typo can never hide a refutation.

**Staleness is reported, never promoted.** A row's `stale` flag says the spec's own declared surface moved between the sha the verdict was checked at and HEAD — or that the comparison could not be made, which its `staleness_basis` names. Either way the row rides into the report alongside the admission outcome and does not change it — neither silently promoted to blocking when a declared surface moves, nor silently dropped. The derivation and the closed basis vocabulary are defined once at [orchestration-model.md § Re-Grounding Verdict Field](../../persona-plan-orchestrator/standards/orchestration-model.md#re-grounding-verdict-field).

A candidate failing either test is sequenced, not emitted. **Never emit a colliding, unresolvable, or unprepared plan merely to fill a slot** — when fewer than `N − R` candidates qualify, report the shortfall with the blocking reason per candidate instead. Every reason is **derived from the blocking row**, never hand-typed:

- A prep-ready reason names the claim and its verdict (`claim {claim_index}: contradicted, not re-scoped`, `claim {claim_index}: indeterminate — {quoted line}`), read from the blocking `corpus verdicts` row. A `scope: section` row carries no addressable ordinal, so its reason names the section instead — its `synthesised` field distinguishes an unreadable section never settled from one whose stamped verdict blocks on its own terms, and the two do not share a reason.
- A disjointness reason is read from the blocking row of whichever read established it — and the three conjuncts of the test are established by different reads, so their reasons have different sources. An OVERLAP names the intersecting paths and the plan they collide with (`overlaps {paths} with PLAN-KK`), read from the blocking `corpus cross-check` `file_overlap_matches[]` row: `overlapping_files` supplies the paths and `candidate` the colliding plan or spec. An INDETERMINATE SURFACE — the candidate's OWN declaration — names the derivation status that made the check impossible (`surface indeterminate: {derivation_status} — no comparable path declared`), read from the `corpus surfaces` row. An INDETERMINATE COMPARISON — the other side of the same test — is the `candidate_indeterminate_reason` string the `corpus cross-check` payload already carries, transcribed verbatim rather than re-composed: it names which candidate kind contributed which non-contributing state. The three are separate reasons because they are separate facts: the first is a checked collision, the second is a candidate that declared nothing to check, the third is a population that was never comparable — and reporting any of them alike would hide exactly the case this gate was rebuilt to surface.

### Step 5 (verb = `next`): Emit the commands

EMIT one ready-to-run command per selected candidate — the whole `N − R` block in one copy-paste surface — each a **one-line pointer** to its staged spec. The spec is the single source of the brief, so no request text is transcribed into the command:

```text
/plan-marshall task="implement .plan/orchestrator/{slug}/plans/PLAN-NN-{plan_slug}.md"
```

The one-line pointer is the whole hand-off. The plan lifecycle ingests the referenced spec file's *contents* at `phase-1-init` — the file-pointer branch of Step 4 "From Description" reads the path through the deterministic `request create --body-file` seam, so the referenced spec becomes the request body and the pointer alone is a self-sufficient brief. The emit therefore surfaces NO inlined spec body and NO operator-facing spec preview: there is deliberately no surface at this step that reproduces the spec text. Should a future author ever need to show a spec body at an orchestrator surface, it MUST be obtained by a `Read` of the spec path — a deterministic file read — NEVER by LLM retyping, paraphrase, or reconstruction from context; a re-introduced "verbatim spec text" inline is exactly the retyping-drift this retirement removed.

The verb NEVER launches the plan inline — the operator runs the emitted command; implementation happens exclusively inside the plan lifecycle. This holds for every command in the block: the orchestrator emits `N − R` ready commands and launches none of them.

**`auto_emit` gate — record the `launched` transition.** Read the orchestrator-tier autonomy knob (default `false`), the orchestrator-tier analog of the plan-tier autonomy family (`finalize_without_asking` / `loop_back_without_asking`):

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config orchestrator get \
  --field auto_emit
```

Branch on the resolved value. The Step 4 candidate selection (disjoint + prep-ready + the `N − R` slot count) is unchanged under either branch — only whether the emitted block's `launched` transition is auto-recorded or operator-gated changes:

- **`auto_emit == true`** — auto-fill toward `parallelization_scope`: immediately record the `launched` transition for every selected candidate in the emitted `N − R` block (once per plan), then continue. Do NOT wait for a per-plan operator confirmation.

  ```bash
  python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator queue \
    --slug {slug} --transition PLAN-NN --status launched
  ```

- **`auto_emit == false` (default)** — today's stage-and-wait cadence, verbatim: emit the block, and record the `launched` transition only when the operator confirms a launch (once per launched plan).

  ```bash
  python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator queue \
    --slug {slug} --transition PLAN-NN --status launched
  ```

**The emit≠running invariant is absolute — neither branch ever records the operator-confirmed started/`running` state.** `auto_emit` automates the *emit* (marking each emitted plan `launched`), never the *start*: the `launched → running` transition stays operator-owned under both knob values. A shortfall (no qualifying candidate for a slot — Step 4's disjointness / prep-readiness guards refused it) emits nothing and logs the blocking reason per candidate under **both** knob values; `auto_emit=true` never emits a colliding, blocked, or unprepared plan merely to fill a slot.

### Step 6 (verb = `next`): Log and set the resume anchor

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging decision \
  --plan-id {slug} --level INFO --message "{emit decision: PLAN-NN emitted, disjointness verdict}" --store orchestrator
```

The anchor is written to the anchor file, `resume_anchor.md`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status update-field \
  --plan-id {slug} --field resume_anchor --value "{next action}" --store orchestrator
```

Word the `resume_anchor` to reflect the Step 5 `auto_emit` branch: under `auto_emit == true` the `launched` transitions are already recorded, so the anchor names the auto-emitted `launched` block awaiting the operator-confirmed start (`launched → running`); under `auto_emit == false` (default) it names the emitted block awaiting operator-confirmed launch. Neither wording ever asserts a `running`/started state the orchestrator did not observe the operator confirm — the emit≠running invariant holds here too.

START HERE renders the anchor and the Ordered Queue renders each `launched` transition Step 5 recorded, so regenerate the view after the anchor write, and commit it with the anchor file and any row file Step 5 changed:

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator regenerate-view \
  --slug {slug}
```

⛔ Never paste either block into `epic.md`, and never hand-edit `queue-view.md`.

## Output

`status` verb:

```toon
status: success | error
display_detail: "epic {slug}: {S} staged, {L} launched, {D} shipped"
slug: {slug}
verb: status
resume_anchor: "{anchor}"
```

`next` verb:

```toon
status: success | error
display_detail: "epic {slug}: emitted {E} of {N-R} slots"
slug: {slug}
verb: next
parallelization_scope: {N}
launched_count: {R}
specs_scanned: {P}
claim_section_states[4]{state,count}:
  absent,{A}
  empty,{Y}
  unreadable,{U}
  parsed,{Q}
unreadable_claim_section_count: {U}
surface_states[5]{derivation_status,count}:
  declarative,{D}
  derived,{V}
  prose,{O}
  absent,{B}
  unreadable,{W}
surface_admitting_count: {D}
surface_indeterminate_count: {I}
candidate_population[3]{candidate_kind,population}:
  sibling_epic_spec,{SP}
  live_plan,{LP}
  corpus_spec,{CP}
candidate_derivation_states[9]{candidate_kind,derivation_status,count}:
  sibling_epic_spec,comparable,{SC}
  sibling_epic_spec,indeterminate,{SI}
  sibling_epic_spec,unreadable,{SX}
  live_plan,comparable,{LC}
  live_plan,indeterminate,{LI}
  live_plan,unreadable,{LX}
  corpus_spec,comparable,{CC}
  corpus_spec,indeterminate,{CI}
  corpus_spec,unreadable,{CX}
candidates_comparable: {CM}
candidates_indeterminate: {CU}
emitted[E]{plan,command}:
  PLAN-NN,/plan-marshall task="implement .plan/orchestrator/{slug}/plans/PLAN-NN-{plan_slug}.md"
shortfall[S]{plan,reason}:
  PLAN-MM,"overlaps {paths} with PLAN-KK"
  PLAN-LL,"surface indeterminate: prose — no comparable path declared"
  PLAN-PP,"claim 2: contradicted, not re-scoped"
  PLAN-QQ,"claim 0: indeterminate — {offending line}"
  PLAN-RR,"claim section: unreadable, not settled — {quoted first line}"
stale_verdicts[T]{plan,claim_index,sha,staleness_basis}:
  PLAN-NN,1,9f3a1c2,declared_surface_touched
```

`display_detail` is ≤80 chars, ASCII, no trailing period. `emitted[]` is empty when no candidate qualifies; `shortfall[]` is empty when the block fills every slot, and otherwise names one blocking reason per unemittable candidate — every reason is derived from its blocking row (a `corpus verdicts` row for prep-readiness, a `corpus surfaces` row for disjointness), never hand-typed. `stale_verdicts[]` reports every row the parser flagged stale and carries no admission consequence: a candidate with stale verdicts and no blocking row is emitted normally. Each row carries the `staleness_basis` the flag was computed on, forwarded verbatim from its `corpus verdicts` row, so a row flagged because the spec's declared surface actually moved (`declared_surface_touched`) is distinguishable from one flagged because the comparison could not be made at all (`surface_not_declarative`, `tree_diff_unavailable`) — the fail-closed bases, which say the grounding was never checked rather than that it moved.

`specs_scanned`, `claim_section_states[]` and `unreadable_claim_section_count` are forwarded from the same `corpus verdicts` read, so the reader sees how much of each section the parser could read and over what population that was computed. The tally spans the whole four-member vocabulary, so a state no spec is in reports a stated zero rather than being absent — `unreadable_claim_section_count: 0` beside a non-zero `specs_scanned` is a measured "nothing unreadable", never an unasked question.

`surface_states[]`, `surface_admitting_count` and `surface_indeterminate_count` are the disjointness half of the same disclosure, forwarded from the `corpus surfaces` read. The tally likewise spans its whole five-member vocabulary, so a class no spec is in reports a stated zero. Together they are what makes a `shortfall[]` of zero legible: a round that emitted every slot with `surface_indeterminate_count: 0` checked every candidate's surface, whereas the same empty shortfall beside a non-zero indeterminate count means some candidate's disjointness was never checkable — and only the published population tells those two apart.

`candidate_population[]`, `candidate_derivation_states[]`, `candidates_comparable` and `candidates_indeterminate` complete that disclosure on the CANDIDATE side, forwarded from the `corpus cross-check` read. The surface tally measures what THIS epic's specs declared; these measure what the specs were compared AGAINST, per `candidate_kind`, and each tally rides with the candidate population it was computed over. Both spans are whole-vocabulary, so a kind with no candidate — and a state no candidate is in — reports a stated zero. The two halves answer different questions and neither substitutes for the other: `surface_indeterminate_count: 0` says every candidate's own declaration was resolvable, while `candidates_indeterminate: 0` says everything it was compared against declared a comparable surface. An emitted block with no overlap shortfall is a checked negative only when BOTH are zero; a non-zero `candidates_indeterminate` means some part of the comparison never happened, whatever the spec side reported.
