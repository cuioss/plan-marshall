# Decompose Verb Workflow

Workflow doc for the `decompose` verb: decompose the epic into workstream charters and staged plan specs, and populate the `status.json` queue. The granularity model (Epic → Workstream → Plan), the scope-bloat split guard, and the surface-disjointness rule are owned by [`persona-plan-orchestrator/standards/orchestration-model.md`](../../persona-plan-orchestrator/standards/orchestration-model.md); when this doc and the standard disagree, the standard wins.

## Exit-code convention for every script call

Every `python3 .plan/execute-script.py` call in this document — of EVERY notation, **not only `manage-*`** — carries the following exit-code contract unless a step explicitly states otherwise. The scope is widened past `manage-*` because this document invokes `orchestrator` and `platform_runtime` — a `manage-*`-scoped convention leaves exactly those calls with no rule at all, which is the swallowed-rejection gap.

- **`exit_code == 0` AND `status: success`**: parse the returned TOON and use the value as the step describes.
- **`exit_code == 0` with a `status` other than `success`, or with no parseable `status` at all**: NOT a usable value — STOP exactly as the `exit_code != 0` disposition below requires, with one difference in what the error TOON carries: on this path the diagnostic is on STDOUT, not stderr. Preserve the stdout **error envelope** as emitted — every field it carries, verbatim — into the returned error TOON; it is the only account of the cause that exists. Copy the whole envelope rather than a fixed field list, because the diagnostic fields vary by verb and `error` is sometimes a generic string whose real cause sits in one of the others. A zero exit is not evidence the operation succeeded; a script MAY print `status: error` and still exit 0. Read `status` FIRST, and never read a **success-payload** field off a non-`success` return. A malformed or truncated stdout carrying **no parseable `status` at all** takes this same path: an unreadable read is not evidence of success, so it fails closed onto STOP rather than falling through to the first clause.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

The middle clause is what the `ci` family makes load-bearing: a `ci` verb reports failure as `status: error` at exit 0 **by design**, so a caller must branch on the payload `status` and never on the exit code. That rule is stated authoritatively in `plan-marshall:tools-integration-ci`; it is not restated here.

Step-level exceptions — calls whose non-zero exit is itself the signal — are documented inline in the step that issues them.

## Inputs

| Parameter | Required | Description |
|-----------|:--------:|-------------|
| `slug` | Yes | Epic slug of an existing (`init`-scaffolded) epic. |
| source material | Yes | The epic's raw input — pasted content (the orchestrator's primary input mode), on-disk documents named by the operator, or both. Third-party text embedded in pastes routes through the [`plan-marshall:untrusted-ingestion`](../../untrusted-ingestion/SKILL.md) posture before influencing any write. |

## Workflow

### Step 1: Push the orchestrator terminal title

Per the [Terminal-Title Repaint Contract](../../persona-plan-orchestrator/standards/orchestration-model.md#terminal-title-repaint-contract), push the `Orchestrator-{SlugName}` title through the platform-runtime seam before the verb's first read:

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

The source-material read completes here and the judgement work begins, so this is where the [Dispatch Decision Rule](../../persona-plan-orchestrator/standards/orchestration-model.md#dispatch-decision-rule) draws its seam.

- **Dispatchable** — the **on-disk half** of the source-material corpus read, the candidate workstream/plan **mapping**, and the prior-art / collision search across the existing queue and the repo surfaces the epic touches, when the corpus is large enough to clear the depth test. The Inputs table above defines source material as pasted content, on-disk documents, or both; the dispatchable corpus is the on-disk documents ONLY. Dispatch as ONE envelope that iterates internally — never one per candidate plan. Vehicle is `execution-context-{level}` under the S1 read-only instruction. The dispatch level is config-resolved via `manage-config effort resolve-target --role orchestrator.decompose --plan-id none --caller plan-marshall:persona-plan-orchestrator --workflow {the doc the leaf loads}` (the four facts are NOT optional decoration: `--workflow` is what makes the resolve seam emit the `[DISPATCH]` line and its paired decision-log record, so a bare `--role` resolve leaves this dispatch with no trail at all — see [the canonical form](../../persona-plan-orchestrator/standards/orchestration-model.md#dispatch-decision-rule)) — the `orchestrator.decompose` surface, resolved through `orchestrator.effort.decompose` → `orchestrator.effort.default` → `plan.effort` → `inherit` and clamped by `orchestrator.effort.max` (see [`effort-roles.md` § Orchestrator role group](../../plan-marshall/standards/effort-roles.md)); its `target` field is the `execution-context-{level}` variant to dispatch. Return shape: `candidates[N]{workstream_slug,plan_slug,expected_surface,rationale}` and `collisions[M]{plan_a,plan_b,overlap}`. The return is a **proposal the orchestrator adjudicates**, never a decision it applies.
- **Inline-only** — the operator's pasted source material (the rule's already-in-context clause); the Step 3 workstream cuts and the Step 4 scope-bloat split-guard verdicts, which fail **fork-freedom**; and the Step 5 queue writes and phase advance, the Step 6 `epic.md` reconciliation and START-HERE regeneration, and the Step 7 decision logging and resume-anchor write, which fail **write-freedom**. Any operator escalation is likewise inline.

### Step 3: Cut workstreams

Partition the epic into workstreams — coherent slices with their own charter (a surface, a theme, a dependency chain). For each workstream, instantiate `workstreams/WS-NN-{ws_slug}.md` from [`templates/workstream.md`](../templates/workstream.md) via the Write tool. A single-plan workstream is legitimate; the tier exists for grouping and charter, not mandatory fan-out.

### Step 4: Stage plan specs

For each shippable unit inside a workstream, instantiate `plans/PLAN-NN-{plan_slug}.md` from [`templates/plan-spec.md`](../templates/plan-spec.md) via the Write tool, recording the plan's **expected surface** (files/modules touched) — the disjointness input `next` consumes. Apply the scope-bloat split guard: a spec approaching six or more deliverables is presumptively split along deliverable-group boundaries; proceeding unsplit requires a recorded decision (Step 7 logging shape). Every staged spec carries the template's `## Write-Boundary` note through to the executing plan, per the standard's [Ledger Write-Boundary](../../persona-plan-orchestrator/standards/orchestration-model.md#ledger-write-boundary) section.

Author every per-plan carry — claim labels, expected surface, re-grounding instruction, adjacency and overlap notes, verify-first clauses — **into the spec file itself**, never into a hand-off block. The spec MUST be self-sufficient: the emitted command is a one-line pointer to the spec path and carries no brief, so anything absent from the spec is lost to the executing plan.

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

### Step 6: Reconcile epic.md — regenerate both derivable blocks

The START-HERE block AND the Ordered Queue table are both GENERATED blocks (reconciliation direction is always status.json → epic.md). ⛔ **Do not hand-write the Ordered Queue table** — its derivable columns (`# | Plan | Workstream | Status | Surface`) are regenerated, and each plan's expected surface is derived from its spec's `## Expected Surface`. Regenerate both blocks and paste each verbatim between its own markers (`resume-summary` and `ordered-queue`):

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator resume-summary \
  --slug {slug}
```

Sequencing and disjointness notes the generator cannot derive go in the `### Queue annotations` zone below the Ordered Queue markers, keyed by plan id — never in the table between the markers.

### Step 7: Log decisions and set the resume anchor

Log every decomposition decision (workstream cuts, split-guard verdicts, sequencing):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging decision \
  --plan-id {slug} --level INFO --message "{decision statement}" --store orchestrator
```

Set the resume anchor (typically "run /plan-orchestrator next slug={slug}"):

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
