# Orchestrate Workflow (status / next)

Shared workflow doc for the two queue-facing verbs: `status` (report the queue and resume state) and `next` (emit the next ready-to-run `/plan-marshall` command). The doc branches on the invoked verb after the shared read steps. The emit-only hand-off rule and the surface-disjointness rule are owned by [`persona-marshall-orchestrator/standards/orchestration-model.md`](../../persona-marshall-orchestrator/standards/orchestration-model.md); when this doc and the standard disagree, the standard wins.

## Inputs

| Parameter | Required | Description |
|-----------|:--------:|-------------|
| `slug` | Yes | Epic slug of an existing epic. |
| verb | Yes | `status` or `next` — resolved by the SKILL router (no verb defaults to `status`). |

## Workflow

### Step 1: Push the orchestrator terminal title (shared)

Per the [Terminal-Title Repaint Contract](../../persona-marshall-orchestrator/standards/orchestration-model.md#terminal-title-repaint-contract), push the `Orchestrator-{SlugName}` title through the platform-runtime seam before the first read. The `slug` is an input to both verbs, so this single shared step covers `status` and `next` alike:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime session push-title-token \
  --store orchestrator --slug {slug}
```

### Step 2: Read the queue (shared)

```bash
python3 .plan/execute-script.py plan-marshall:marshall-orchestrator:orchestrator queue \
  --slug {slug}
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read \
  --plan-id {slug} --store orchestrator
```

The on-query epic discovery / store scan enumerates BOTH `.plan/local/orchestrator/` and `.plan/local/archived-orchestrators/`, and the `read` verb resolves an archived epic transparently via the read-fallback — so a slug naming an archived (closed-and-relocated) epic is still discoverable and reportable here without re-anchoring.

### Step 3 (verb = `status`): Report

Render the queue report from the machine authority: per-plan status (staged / launched / shipped / parked), workstream grouping, open defects and watches from `epic.md`, and the `resume_anchor`. An archived epic reports identically — its tree is resolved from `archived-orchestrators/` and its `status.json` is the same machine authority. When the report reveals stale prose in `epic.md` (a queue row disagreeing with `status.json`), reconcile status.json → epic.md and regenerate the START-HERE block:

```bash
python3 .plan/execute-script.py plan-marshall:marshall-orchestrator:orchestrator resume-summary \
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
- **Prep-ready** — its spec owes no re-grounding, and carries no verify-first clause that a prior orchestrator corroboration has REFUTED without the spec being re-scoped to reflect the refutation (see the spec template's `## Claim Labels`).

An OPEN verify-first clause — one authored by `decompose.md` Step 4 and not yet checked by anyone — does NOT fail the Prep-ready test. Per [orchestration-model.md § Verify-First Contract for Inferred Claims](../../persona-marshall-orchestrator/standards/orchestration-model.md#verify-first-contract-for-inferred-claims), settling such a clause is the LAUNCHED plan's own job (refine owns the verification; outline owns it when refine did not run), so blocking emission on an unchecked clause would make the verifying phase unreachable and the spec permanently unemittable. Only a clause a fresh orchestrator check has already contradicted — typically the [`analyze.md` Step 2](analyze.md) dispatchable ground-truth corroboration returning `verdict: contradicted` — blocks emission, and only until the spec is re-scoped against that refutation.

A candidate failing either test is sequenced, not emitted. **Never emit a colliding or unprepared plan merely to fill a slot** — when fewer than `N − R` candidates qualify, report the shortfall with the blocking reason per candidate (the overlapping surface, or the refuted-and-unaddressed claim) instead.

### Step 5 (verb = `next`): Emit the commands

EMIT one ready-to-run command per selected candidate — the whole `N − R` block in one copy-paste surface — each a **one-line pointer** to its staged spec. The spec is the single source of the brief, so no request text is transcribed into the command:

```text
/plan-marshall task="implement .plan/local/orchestrator/{slug}/plans/PLAN-NN-{plan_slug}.md"
```

**Lifecycle prerequisite.** The one-line form is lossless only once the plan lifecycle ingests a referenced spec file's *contents*. It does not do so today: `phase-1-init` uses the description verbatim and reads no path named inside it, and `phase-2-refine` existence-checks file-path claims rather than ingesting them. PLAN-41 owns that lifecycle change. Until it lands, the emit inlines the spec body beneath the pointer line — the pointer is the target emit contract, not yet the sufficient one.

The verb NEVER launches the plan inline — the operator runs the emitted command; implementation happens exclusively inside the plan lifecycle. This holds for every command in the block: the orchestrator emits `N − R` ready commands and launches none of them. When the operator confirms a launch, record the transition (once per launched plan):

```bash
python3 .plan/execute-script.py plan-marshall:marshall-orchestrator:orchestrator queue \
  --slug {slug} --transition PLAN-NN --status launched
```

### Step 6 (verb = `next`): Log and set the resume anchor

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging decision \
  --plan-id {slug} --level INFO --message "{emit decision: PLAN-NN emitted, disjointness verdict}" --store orchestrator
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status update-field \
  --plan-id {slug} --field resume_anchor --value "{next action}" --store orchestrator
```

Regenerate the START-HERE block (Step 3 invocation) after any queue-touching change.

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
emitted[E]{plan,command}:
  PLAN-NN,/plan-marshall task="implement .plan/local/orchestrator/{slug}/plans/PLAN-NN-{plan_slug}.md"
shortfall[S]{plan,reason}:
  PLAN-MM,"overlaps {surface} with PLAN-KK"
  PLAN-PP,"refuted verify-first clause not yet re-scoped"
```

`display_detail` is ≤80 chars, ASCII, no trailing period. `emitted[]` is empty when no candidate qualifies; `shortfall[]` is empty when the block fills every slot, and otherwise names one blocking reason per unemittable candidate.
