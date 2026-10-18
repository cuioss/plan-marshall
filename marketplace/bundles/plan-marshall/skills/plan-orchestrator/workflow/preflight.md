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
| `model` | No | Self-reported model identifier the executing LLM ran under. Forwarded to `runtime-info` as `--model` and stamped into the plan's runtime metadata. |
| `effort` | No | Self-reported effort level. Forwarded to `runtime-info` as `--effort` and stamped into the plan's runtime metadata. |

The two self-report values are what the executing LLM knows about itself and no
script can read; they are recorded with their `self_reported` source tag. On
OpenCode the model is measured from the session database instead (see
`platform-runtime/standards/runtime-info.md`).

## Workflow

### Step 1: Invoke the pre-flight entry point

```bash
python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator preflight \
  --plan-id {plan_id} --model {model} --effort {effort}
```

This is the deterministic script-side invocation. It settles the plan's title
state best-effort (`session push-title-token --plan-id`, the plan-scoped form
of the terminal-title repaint obligation — no epic slug is in scope), then
resolves the plan directory, invokes `platform_runtime runtime-info` (forwarding
`--model` / `--effort` when given) for the
active target, and read-merge-writes the returned payload into `client.toon`
in the plan directory (`.plan/local/plans/{plan_id}/client.toon`,
worktree-resident when the plan runs in a worktree). Each run appends a new
timestamp-keyed entry and never overwrites prior entries.

The same run stamps the plan's runtime metadata into `status.json` — `harness`,
`harness_source`, `model`, `models`, `model_source`, `effort`, `effort_source`,
`bundle_version` and `executor_version` — through manage-status's shared status
writer. Only the fields the collected payload carried are written, and those
the stamper manages but the payload did NOT carry are REMOVED: the stamper owns
those keys, so a later preflight that could not read a field never leaves the
earlier run's value in place for the landing to attribute to this run.
`models` rides beside `model` so a MIXED OpenCode session tree keeps the distinct
`{model}/{variant}` labels the landing needs to name.
The stamp is attempted as soon as the collector returns a usable payload,
INDEPENDENT of the artifact write: a `client.toon` that cannot be read or written
is no reason to lose the collected attributes, and the two outcomes are reported
separately (`artifact_written` / `metadata_stamped`). The stamp is best-effort: a
plan with no readable status document, or a write failure, reports
`metadata_stamped: false` and never blocks plan start.

### Step 2: Continue plan start regardless of outcome

The hook is best-effort by contract: a collector failure degrades to
`degraded: true` with `artifact_written: false` and still returns
`status: success`. A pre-flight probe never blocks plan start — continue
with plan start whether or not the artifact was written.

## Output

```toon
status: success
operation: preflight
display_detail: "preflight client.toon written for {plan_id}"
plan_id: {plan_id}
degraded: true | false
degrade_reason: "{what failed}"
artifact_written: true | false
artifact: client.toon
metadata_stamped: true | false
```

`display_detail` is composed by the calling workflow and is ≤80 chars, ASCII,
no trailing period. `artifact` is present only when `artifact_written` is
true. `metadata_stamped` is present whenever the collector returned a usable
payload — the stamp is attempted independently of the artifact write, so it is
reported on the artifact-failure paths too — and records whether the runtime
metadata reached `status.json`. `degraded` names
whether any preflight-path step failed and
`degrade_reason` names which one; it is present only when `degraded` is true.
The plan starts either way.
