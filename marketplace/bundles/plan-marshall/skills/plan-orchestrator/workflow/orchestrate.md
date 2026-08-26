# Orchestrate Workflow (status / next)

Shared workflow doc for the two queue-facing verbs: `status` (report the queue and resume state) and `next` (emit the next ready-to-run `/plan-marshall` command). The doc branches on the invoked verb after the shared read steps. The emit-only hand-off rule and the surface-disjointness rule are owned by [`persona-plan-orchestrator/standards/orchestration-model.md`](../../persona-plan-orchestrator/standards/orchestration-model.md); when this doc and the standard disagree, the standard wins.

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

The on-query epic discovery / store scan enumerates BOTH `.plan/local/orchestrator/` and `.plan/local/archived-orchestrators/`, and the `read` verb resolves an archived epic transparently via the read-fallback — so a slug naming an archived (closed-and-relocated) epic is still discoverable and reportable here without re-anchoring.

### Step 3 (verb = `status`): Report

Render the queue report from the machine authority: per-plan status (staged / launched / shipped / parked), workstream grouping, open defects and watches from `epic.md`, and the `resume_anchor`. An archived epic reports identically — its tree is resolved from `archived-orchestrators/` and its `status.json` is the same machine authority. When the report reveals stale prose in `epic.md` (a queue row disagreeing with `status.json`), reconcile status.json → epic.md and regenerate both derivable blocks (START-HERE and the Ordered Queue table — the one invocation emits both):

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator resume-summary \
  --slug {slug}
```

Skip Steps 4–6 and return.

### Step 4 (verb = `next`): Select up to `N − R` launchable plans

Read the epic's `parallelization_scope` knob — `N`, the maximum number of concurrently-launched plans, defaulting to `1` (strictly sequential) when unset:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {slug} --get --field parallelization_scope --store orchestrator
```

Count `R`, the plans currently in `launched` status, and select up to `N − R` candidates — a block sized by the scope knob rather than a hardcoded single (at the default `N = 1` that block is exactly one). Walk `staged` plans in queue order whose dependencies (sequencing notes in their `plans/PLAN-NN-{plan_slug}.md` spec) are satisfied, and admit a candidate ONLY when both admission tests pass:

- **Disjoint** — its expected surface overlaps neither any currently-launched plan nor any candidate already selected this round.
- **Prep-ready** — decided from the PARSER, not from a reader's judgement over the spec prose. Read the corpus's verdicts once:

  ```bash
  python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator corpus verdicts \
    --slug {slug}
  ```

  **Joining a candidate to its rows.** `corpus verdicts` keys each row by `spec` — the spec FILE NAME, e.g. `PLAN-01-alpha.md` — and `claim_index`; it carries no plan id. Candidate selection here works over plan ids (`PLAN-NN`). A candidate's rows are therefore the rows whose `spec` begins with that candidate's `PLAN-NN-` prefix, and that prefix join is the ONE rule relating the two. It applies wherever this payload meets a plan id, including the `stale_verdicts[T]{plan,...}` rows of the report shape below.

  A candidate is prep-ready **iff** no row of its spec carries `admits: false`. `corpus verdicts` is the field's only interpreter, so the admission outcome is a property of one parse rather than of two readers agreeing. The admission table — which of the six states admits and which blocks, and why — is defined once at [orchestration-model.md § Re-Grounding Verdict Field](../../persona-plan-orchestrator/standards/orchestration-model.md#re-grounding-verdict-field) and is not restated here.

  **A section the parser could not read now contributes such a row.** Rows are addressed at two scopes, and a spec whose `## Claim Labels` section the parser could not read — content is present, but authored as a table or as prose rather than as top-level bullets — while carrying no section-scoped verdict contributes exactly one row with `scope: section`, `claim_index: -1` and `admits: false`. Such a candidate is therefore **not** prep-ready, where previously it contributed no row at all and passed the test vacuously. The one-call remedy is `corpus set-verdict --section-scope`, which settles the section without re-authoring any claim prose; a spec is never asked to convert its section into bullets to become emittable. A section reported `absent` or `empty` contributes no row and still admits — the block is caused by unreadability alone.

Four rules govern the outcome, every one of them decided by the parser rather than by a reader: an **OPEN (absent) clause does NOT fail the test** — settling it is the LAUNCHED plan's own job per [orchestration-model.md § Verify-First Contract for Inferred Claims](../../persona-plan-orchestrator/standards/orchestration-model.md#verify-first-contract-for-inferred-claims), so blocking on an unchecked clause would make the verifying phase unreachable and the spec permanently unemittable; **only a refutation the spec has not absorbed blocks**; an **`unverifiable` verdict never blocks**, because an unreachable population is not a refutation; and a **malformed field blocks**, reported as `indeterminate` with the offending line quoted, so a typo can never hide a refutation.

**Staleness is reported, never promoted.** A row whose `stale` flag is set rides into the report alongside the admission outcome and does not change it — neither silently promoted to blocking as HEAD advances, nor silently dropped.

A candidate failing either test is sequenced, not emitted. **Never emit a colliding or unprepared plan merely to fill a slot** — when fewer than `N − R` candidates qualify, report the shortfall with the blocking reason per candidate instead. A prep-ready shortfall reason is **derived from the blocking row**, naming the claim and its verdict (`claim {claim_index}: contradicted, not re-scoped`, `claim {claim_index}: indeterminate — {quoted line}`) rather than being a hand-typed sentence. A `scope: section` row carries no addressable ordinal, so its reason names the section instead (`claim section: unreadable, not settled — {quoted first line}`).

### Step 5 (verb = `next`): Emit the commands

EMIT one ready-to-run command per selected candidate — the whole `N − R` block in one copy-paste surface — each a **one-line pointer** to its staged spec. The spec is the single source of the brief, so no request text is transcribed into the command:

```text
/plan-marshall task="implement .plan/local/orchestrator/{slug}/plans/PLAN-NN-{plan_slug}.md"
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

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status update-field \
  --plan-id {slug} --field resume_anchor --value "{next action}" --store orchestrator
```

Word the `resume_anchor` to reflect the Step 5 `auto_emit` branch: under `auto_emit == true` the `launched` transitions are already recorded, so the anchor names the auto-emitted `launched` block awaiting the operator-confirmed start (`launched → running`); under `auto_emit == false` (default) it names the emitted block awaiting operator-confirmed launch. Neither wording ever asserts a `running`/started state the orchestrator did not observe the operator confirm — the emit≠running invariant holds here too.

Regenerate both derivable blocks — START-HERE and the Ordered Queue table (the single `resume-summary` invocation emits both) — after any queue-touching change, and paste each between its own markers.

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
emitted[E]{plan,command}:
  PLAN-NN,/plan-marshall task="implement .plan/local/orchestrator/{slug}/plans/PLAN-NN-{plan_slug}.md"
shortfall[S]{plan,reason}:
  PLAN-MM,"overlaps {surface} with PLAN-KK"
  PLAN-PP,"claim 2: contradicted, not re-scoped"
  PLAN-QQ,"claim 0: indeterminate — {offending line}"
  PLAN-RR,"claim section: unreadable, not settled — {quoted first line}"
stale_verdicts[T]{plan,claim_index,sha}:
  PLAN-NN,1,9f3a1c2
```

`display_detail` is ≤80 chars, ASCII, no trailing period. `emitted[]` is empty when no candidate qualifies; `shortfall[]` is empty when the block fills every slot, and otherwise names one blocking reason per unemittable candidate — a prep-ready reason is derived from the blocking `corpus verdicts` row (its claim index and verdict, or the section when the row is section-scoped), never hand-typed. `stale_verdicts[]` reports every row the parser flagged stale and carries no admission consequence: a candidate with stale verdicts and no blocking row is emitted normally.

`specs_scanned`, `claim_section_states[]` and `unreadable_claim_section_count` are forwarded from the same `corpus verdicts` read, so the reader sees how many candidates the section-scoped row class is holding and over what population that was computed. The tally spans the whole four-member vocabulary, so a state no spec is in reports a stated zero rather than being absent — `unreadable_claim_section_count: 0` beside a non-zero `specs_scanned` is a measured "nothing unreadable", never an unasked question.
