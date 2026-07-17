# Decompose Verb Workflow

Workflow doc for the `decompose` verb: decompose the epic into workstream charters and staged plan specs, and populate the `status.json` queue. The granularity model (Epic → Workstream → Plan), the scope-bloat split guard, and the surface-disjointness rule are owned by [`persona-marshall-orchestrator/standards/orchestration-model.md`](../../persona-marshall-orchestrator/standards/orchestration-model.md); when this doc and the standard disagree, the standard wins.

## Inputs

| Parameter | Required | Description |
|-----------|:--------:|-------------|
| `slug` | Yes | Epic slug of an existing (`init`-scaffolded) epic. |
| source material | Yes | The epic's raw input — pasted content (the orchestrator's primary input mode), on-disk documents named by the operator, or both. Third-party text embedded in pastes routes through the [`plan-marshall:untrusted-ingestion`](../../untrusted-ingestion/SKILL.md) posture before influencing any write. |

## Workflow

### Step 1: Read the current epic state

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status read \
  --plan-id {slug} --store orchestrator
```

Read `epic.md` (Vision, any existing queue) via the Read tool. Decomposition is re-entrant: an existing queue is extended and reconciled, never blindly overwritten.

### Step 2: Cut workstreams

Partition the epic into workstreams — coherent slices with their own charter (a surface, a theme, a dependency chain). For each workstream, instantiate `workstreams/WS-NN-{ws_slug}.md` from [`templates/workstream.md`](../templates/workstream.md) via the Write tool. A single-plan workstream is legitimate; the tier exists for grouping and charter, not mandatory fan-out.

### Step 3: Stage plan specs

For each shippable unit inside a workstream, instantiate `plans/PLAN-NN-{plan_slug}.md` from [`templates/plan-spec.md`](../templates/plan-spec.md) via the Write tool, recording the plan's **expected surface** (files/modules touched) — the disjointness input `next` consumes. Apply the scope-bloat split guard: a spec approaching six or more deliverables is presumptively split along deliverable-group boundaries; proceeding unsplit requires a recorded decision (Step 6 logging shape).

### Step 4: Populate the status.json queue

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

### Step 5: Reconcile epic.md and regenerate START HERE

Mirror the queue into `epic.md`'s Ordered Queue table (reconciliation direction is always status.json → epic.md), including each plan's expected surface and sequencing notes. Then regenerate the START-HERE block and paste it verbatim between the generated-block markers:

```bash
python3 .plan/execute-script.py plan-marshall:marshall-orchestrator:orchestrator resume-summary \
  --slug {slug}
```

### Step 6: Log decisions and set the resume anchor

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
