# Init Verb Workflow

Workflow doc for the `init` verb: scaffold a new epic tree under `.plan/local/orchestrator/{slug}/` and write the epic skeleton. The layout, authority, and carve-out contracts are owned by [`persona-marshall-orchestrator/standards/orchestration-model.md`](../../persona-marshall-orchestrator/standards/orchestration-model.md); when this doc and the standard disagree, the standard wins.

## Inputs

| Parameter | Required | Description |
|-----------|:--------:|-------------|
| `slug` | Yes | Epic slug (kebab-case). Names the `.plan/local/orchestrator/{slug}/` tree. |
| `title` | No | Human-facing epic title. Defaults to the slug when omitted. |

## Workflow

### Step 1: Push the orchestrator terminal title

Per the [Terminal-Title Repaint Contract](../../persona-marshall-orchestrator/standards/orchestration-model.md#terminal-title-repaint-contract), push the `Orchestrator-{SlugName}` title through the platform-runtime seam:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime session push-title-token \
  --store orchestrator --slug {slug}
```

On first `init` the epic's `status.json` does not exist yet, so this entry push cannot resolve the epic state and no-ops; Step 3 fires a follow-up repaint once `status.json` exists so the first-init title still renders. Re-running `init` on an existing tree (idempotent re-entry) repaints here directly.

### Step 2: Scaffold the epic tree

```bash
python3 .plan/execute-script.py plan-marshall:marshall-orchestrator:orchestrator scaffold \
  --slug {slug}
```

The scaffold is idempotent — re-running against an existing tree creates nothing and fails nothing.

### Step 3: Create the status document

Create the `kind=orchestrator` machine authority (`--phases` is ignored for this store; the schema carries a single three-value `phase` field starting at `init`):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status create \
  --plan-id {slug} --title "{title}" --store orchestrator
```

Now that `status.json` exists, fire the follow-up terminal-title repaint the Step 1 entry push could not resolve on a first `init` — this is the push that actually renders the `Orchestrator-{SlugName}` title on the very first run:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime session push-title-token \
  --store orchestrator --slug {slug}
```

### Step 4: Ask the parallelization scope (once per epic)

Read the knob first — the ask is idempotent and MUST be skipped when the field is already set (an `init` re-entry never re-prompts):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {slug} --get --field parallelization_scope --store orchestrator
```

When the field is unset, fire exactly ONE `AskUserQuestion` for the operator's **parallelization scope** — the maximum number of plans the orchestrator may have launched concurrently, `1` meaning strictly sequential and `N` meaning up to `N` concurrent plans. `init` runs in main context, so the prompt is fired natively here.

**Validate the answer before persisting it.** The operator's raw answer is untrusted input and MUST be reduced to a positive integer `N ≥ 1` before it reaches the `metadata --set` call — `orchestrate.md`'s `next` verb Step 4 computes `N - R` from the persisted value, so a zero, a negative number, or non-numeric text yields a nonsensical slot count or an unusable comparison downstream. Apply this reduction:

- The answer parses as an integer `≥ 1` → that integer is `N`; proceed to the persist call.
- The answer parses as an integer `≤ 0`, or does not parse as an integer at all → re-fire the `AskUserQuestion` exactly ONCE, stating that the scope must be a whole number of concurrent plans, `1` or greater.
- The re-prompted answer still fails the same test → fall back to the documented default `N = 1` (strictly sequential) and record the fallback in the decision log below.

Only a value that survived this reduction is persisted, so every reader of `parallelization_scope` — `next` included — is guaranteed a positive integer:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status metadata \
  --plan-id {slug} --set --field parallelization_scope --value {N} --store orchestrator
```

The knob bounds the `next` queue-fill selection — see [Parallelization by Surface Disjointness](../../persona-marshall-orchestrator/standards/orchestration-model.md#parallelization-by-surface-disjointness) for the consuming contract. Log the operator interaction:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging decision \
  --plan-id {slug} --level INFO --message "{parallelization_scope set to N by operator, or defaulted to 1 after an invalid answer}" --store orchestrator
```

### Step 5: Write the epic skeleton

Instantiate `epic.md` from [`templates/epic.md`](../templates/epic.md) via the Write tool — direct file access inside the epic's own tree is the direct-file-access carve-out. Fill the Vision section from the operator's framing; leave the Ordered Queue empty (populated by `decompose`) and the START-HERE generated-block markers in place. Optionally seed `references.json` (external repos, PRs, source documents) the same way.

### Step 6: Set the resume anchor and log

Set the resume anchor to the exact next action (typically "run /marshall-orchestrator decompose slug={slug}"):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status update-field \
  --plan-id {slug} --field resume_anchor --value "{next action}" --store orchestrator
```

Log the init decision:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging decision \
  --plan-id {slug} --level INFO --message "{init decision: epic created, vision summary}" --store orchestrator
```

## Output

```toon
status: success | error
display_detail: "epic {slug} scaffolded"
slug: {slug}
phase: init
resume_anchor: "{next action}"
```

`display_detail` is ≤80 chars, ASCII, no trailing period.
