# Decompose Verb Workflow

Workflow doc for the `decompose` verb: decompose the epic into workstream charters and staged plan specs, and populate the `status.json` queue. The granularity model (Epic → Workstream → Plan), the scope-bloat split guard, and the surface-disjointness rule are owned by [`persona-marshall-orchestrator/standards/orchestration-model.md`](../../persona-marshall-orchestrator/standards/orchestration-model.md); when this doc and the standard disagree, the standard wins.

## Inputs

| Parameter | Required | Description |
|-----------|:--------:|-------------|
| `slug` | Yes | Epic slug of an existing (`init`-scaffolded) epic. |
| source material | Yes | The epic's raw input — pasted content (the orchestrator's primary input mode), on-disk documents named by the operator, or both. Third-party text embedded in pastes routes through the [`plan-marshall:untrusted-ingestion`](../../untrusted-ingestion/SKILL.md) posture before influencing any write. |

## Workflow

### Step 1: Push the orchestrator terminal title

Per the [Terminal-Title Repaint Contract](../../persona-marshall-orchestrator/standards/orchestration-model.md#terminal-title-repaint-contract), push the `Orchestrator-{SlugName}` title through the platform-runtime seam before the verb's first read:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime session push-title-token \
  --store orchestrator --slug {slug}
```

### Step 2: Read the current epic state

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read \
  --plan-id {slug} --store orchestrator
```

Read `epic.md` (Vision, any existing queue) via the Read tool. Decomposition is re-entrant: an existing queue is extended and reconciled, never blindly overwritten.

The source-material read completes here and the judgement work begins, so this is where the [Dispatch Decision Rule](../../persona-marshall-orchestrator/standards/orchestration-model.md#dispatch-decision-rule) draws its seam.

- **Dispatchable** — the **on-disk half** of the source-material corpus read, the candidate workstream/plan **mapping**, and the prior-art / collision search across the existing queue and the repo surfaces the epic touches, when the corpus is large enough to clear the depth test. The Inputs table above defines source material as pasted content, on-disk documents, or both; the dispatchable corpus is the on-disk documents ONLY. Dispatch as ONE envelope that iterates internally — never one per candidate plan. Vehicle is `execution-context-{level}` under the S1 read-only instruction. Return shape: `candidates[N]{workstream_slug,plan_slug,expected_surface,rationale}` and `collisions[M]{plan_a,plan_b,overlap}`. The return is a **proposal the orchestrator adjudicates**, never a decision it applies.
- **Inline-only** — the operator's pasted source material (the rule's already-in-context clause); the Step 3 workstream cuts and the Step 4 scope-bloat split-guard verdicts, which fail **fork-freedom**; and the Step 5 queue writes and phase advance, the Step 6 `epic.md` reconciliation and START-HERE regeneration, and the Step 7 decision logging and resume-anchor write, which fail **write-freedom**. Any operator escalation is likewise inline.

### Step 3: Cut workstreams

Partition the epic into workstreams — coherent slices with their own charter (a surface, a theme, a dependency chain). For each workstream, instantiate `workstreams/WS-NN-{ws_slug}.md` from [`templates/workstream.md`](../templates/workstream.md) via the Write tool. A single-plan workstream is legitimate; the tier exists for grouping and charter, not mandatory fan-out.

### Step 4: Stage plan specs

For each shippable unit inside a workstream, instantiate `plans/PLAN-NN-{plan_slug}.md` from [`templates/plan-spec.md`](../templates/plan-spec.md) via the Write tool, recording the plan's **expected surface** (files/modules touched) — the disjointness input `next` consumes. Apply the scope-bloat split guard: a spec approaching six or more deliverables is presumptively split along deliverable-group boundaries; proceeding unsplit requires a recorded decision (Step 7 logging shape).

### Step 5: Populate the status.json queue

Write the queue into the machine authority — one `plans[]` entry per staged spec (`{id, slug, workstream, status: staged, plan_marshall_plan_id: "", pr: "", landing: ""}`), plus the `workstreams[]` list:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status update-field \
  --plan-id {slug} --field workstreams --value {workstreams_json_array} --store orchestrator
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status update-field \
  --plan-id {slug} --field plans --value {plans_json_array} --store orchestrator
```

The `{workstreams_json_array}` / `{plans_json_array}` placeholders are a complete JSON array that MUST be passed as ONE shell-safe `--value` argument — single-quote the whole payload so the shell never word-splits or glob-expands the brackets, commas, and quotes. Never interpolate the raw JSON unquoted onto the command line.

Advance the epic phase:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status update-field \
  --plan-id {slug} --field phase --value orchestrating --store orchestrator
```

### Step 6: Reconcile epic.md and regenerate START HERE

Mirror the queue into `epic.md`'s Ordered Queue table (reconciliation direction is always status.json → epic.md), including each plan's expected surface and sequencing notes. Then regenerate the START-HERE block and paste it verbatim between the generated-block markers:

```bash
python3 .plan/execute-script.py plan-marshall:marshall-orchestrator:orchestrator resume-summary \
  --slug {slug}
```

### Step 7: Log decisions and set the resume anchor

Log every decomposition decision (workstream cuts, split-guard verdicts, sequencing):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging decision \
  --plan-id {slug} --level INFO --message "{decision statement}" --store orchestrator
```

Set the resume anchor (typically "run /marshall-orchestrator next slug={slug}"):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status update-field \
  --plan-id {slug} --field resume_anchor --value "{next action}" --store orchestrator
```

## Output

```toon
status: success | error
display_detail: "epic {slug} decomposed: {W} workstreams, {P} staged plans"
slug: {slug}
phase: orchestrating
workstreams: {W}
plans_staged: {P}
resume_anchor: "{next action}"
```

`display_detail` is ≤80 chars, ASCII, no trailing period.
