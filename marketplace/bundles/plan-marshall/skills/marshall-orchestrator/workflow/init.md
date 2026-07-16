# Init Verb Workflow

Workflow doc for the `init` verb: scaffold a new epic tree under `.plan/local/orchestrator/{slug}/` and write the epic skeleton. The layout, authority, and carve-out contracts are owned by [`persona-marshall-orchestrator/standards/orchestration-model.md`](../../persona-marshall-orchestrator/standards/orchestration-model.md); when this doc and the standard disagree, the standard wins.

## Inputs

| Parameter | Required | Description |
|-----------|:--------:|-------------|
| `slug` | Yes | Epic slug (kebab-case). Names the `.plan/local/orchestrator/{slug}/` tree. |
| `title` | No | Human-facing epic title. Defaults to the slug when omitted. |

## Workflow

### Step 1: Push the orchestrator terminal title

Session-opening verbs surface the epic in the terminal title. Push the `Orchestrator-{SlugName}` title through the platform-runtime seam:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime session push-title-token \
  --store orchestrator --slug {slug}
```

The push is best-effort and gating is inherited: when the terminal-title surface is not configured (no controlling terminal, hooks off), the seam is a silent no-op — no push happens and the verb proceeds normally. On first `init` the epic's `status.json` does not exist yet, so this entry push no-ops; re-running `init` on an existing tree (idempotent re-entry) repaints.

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

### Step 4: Write the epic skeleton

Instantiate `epic.md` from [`templates/epic.md`](../templates/epic.md) via the Write tool — direct file access inside the epic's own tree is the direct-file-access carve-out. Fill the Vision section from the operator's framing; leave the Ordered Queue empty (populated by `decompose`) and the START-HERE generated-block markers in place. Optionally seed `references.json` (external repos, PRs, source documents) the same way.

### Step 5: Set the resume anchor and log

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
