# Pre-flight Hook Workflow

Workflow doc for the plan-start pre-flight hook: the single entry point for
runtime collection. Starting a plan invokes the deterministic
`orchestrator.py preflight` entry point first; it calls
`platform_runtime runtime-info` and writes the returned payload as the
per-plan `client.toon` pre-flight artifact. The script/LLM boundary is
preserved: the collector call plus the artifact write are script-side and
deterministic, while the surrounding plan-start routing stays LLM
verb-router prose.

## Exit-code convention for every script call

The exit-code contract for every `python3 .plan/execute-script.py` call in this document — of EVERY notation, not only `manage-*` — is stated once in [`tools-script-executor/standards/exit-code-convention.md`](../../tools-script-executor/standards/exit-code-convention.md); it is not restated here.

## Inputs

| Parameter | Required | Description |
|-----------|:--------:|-------------|
| `plan_id` | Yes | Plan identifier the `client.toon` artifact is written for. |

## Workflow

### Step 1: Invoke the pre-flight entry point

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator preflight \
  --plan-id {plan_id}
```

This is the deterministic script-side invocation. It settles the plan's title
state best-effort (`session push-title-token --plan-id`, the plan-scoped form
of the terminal-title repaint obligation — no epic slug is in scope), then
resolves the plan directory, invokes `platform_runtime runtime-info` for the
active target, and read-merge-writes the returned payload into `client.toon`
in the plan directory (`.plan/local/plans/{plan_id}/client.toon`,
worktree-resident when the plan runs in a worktree). Each run appends a new
timestamp-keyed entry and never overwrites prior entries.

### Step 2: Continue plan start regardless of outcome

The hook is best-effort by contract: a collector failure degrades to
`degraded: true` with `artifact_written: false` and still returns
`status: success`. A pre-flight probe never blocks plan start — continue
with plan start whether or not the artifact was written.

## Output

```toon
status: success
display_detail: "preflight client.toon written for {plan_id}"
plan_id: {plan_id}
degraded: true | false
artifact_written: true | false
artifact: client.toon
```

`display_detail` is composed by the calling workflow and is ≤80 chars, ASCII,
no trailing period. `artifact` is present only when `artifact_written` is
true. `degraded` names whether the collector path failed; the plan starts
either way.
