# Merge-Queue Provisioning Reference

Idempotent probe→ask→configure provisioning of the platform merge queue (GitHub
merge queue / GitLab merge train). Referenced by `wizard-flow.md` Step 13.5 and
by the Configuration menu's "Merge Queue" entry.

This step introduces **no provider branching of its own** — it always calls the
provider-agnostic `ci repo merge-queue probe` / `ci repo merge-queue enable`
verbs (see `tools-integration-ci/standards/pr-operations.md` § "Workflow: Repo
Merge-Queue Probe / Enable") and delegates persistence to `manage-config`. It
adds no new script entry point.

## When it runs

The provisioning step runs after CI provider detection (Step 13), because it
requires an authenticated CI provider (`gh` / `glab`) to probe the platform. It
is **optional and idempotent**: a re-run against an already-configured project
surfaces nothing and mutates nothing.

## The provisioning flow

### Step MQ-1: Probe eligibility

Probe the platform merge-queue state via the provider-agnostic verb:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci repo merge-queue probe
```

Parse `status` and (on success) `eligibility` from the returned TOON.
`eligibility` is one of the shared discriminators: `eligible_configured`,
`eligible_unconfigured`, `ineligible`, `unsupported`. A `status: error` from an
auth-scope failure carries the actionable remedy — surface it to the operator
verbatim and stop (never a stack trace).

### Step MQ-2: Branch on the discriminator

**On `eligible_configured`** — the platform merge queue is already configured.
Run the `enable` verb anyway: on GitHub it reconciles the named ruleset's merge
method against the configured `pr_merge_strategy` (see
`tools-integration-ci/standards/pr-operations.md` § "Workflow: Repo Merge-Queue
Probe / Enable"), so it may return `changed: true` with the reconcile detail
rather than the historical unconditional no-op:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci repo merge-queue enable
```

Log the outcome the verb actually reports — the `detail` field names what (if
anything) was reconciled:

- `changed: false` →

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    work --level INFO \
    --message "[STEWARD] (plan-marshall:marshall-steward) Merge queue already configured — no change made"
  ```

- `changed: true` →

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    work --level INFO \
    --message "[STEWARD] (plan-marshall:marshall-steward) Merge queue already configured — reconciled: {detail from enable TOON}"
  ```

**On `eligible_unconfigured`** — available but not yet configured. Fire exactly
ONE `AskUserQuestion`:

```text
AskUserQuestion:
  questions:
    - question: "The platform merge queue is available but not configured. Enable it now?"
      header: "Merge Queue"
      options:
        - label: "Enable now (Recommended)"
          description: "Configure the platform merge queue and set use_merge_queue=true"
        - label: "Skip"
          description: "Leave the merge queue unconfigured; use_merge_queue stays off"
      multiSelect: false
```

Log the operator's answer as a STEWARD decision (one entry per answer):

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --level INFO \
  --message "[STEWARD] (plan-marshall:marshall-steward) Merge-queue enable decision: {enable|skip}"
```

On **Enable now**, configure the platform merge queue, then persist the opt-in:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci repo merge-queue enable
```

Assert the response is `status: success`. Then persist `use_merge_queue=true`.
`use_merge_queue` is a step-owned param of the `default:branch-cleanup` step in
the phase-6-finalize keyed-map `steps` structure (mirroring `pr_merge_strategy`):

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize step set --step-id default:branch-cleanup --param use_merge_queue --value true
```

On **Skip**, leave `use_merge_queue` at its default (off) and make no `enable`
call.

**On `ineligible` / `unsupported`** — the platform gates the feature off (GitLab
merge trains require Premium/Ultimate; a GitHub org policy or missing
Administration scope disallows it). Refuse with the actionable message the probe
returned (naming the tier / branch-protection remedy) — never a stack trace:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --level WARNING \
  --message "[STEWARD] (plan-marshall:marshall-steward) Merge queue ineligible — {actionable remedy from probe detail}; leaving use_merge_queue off"
```

Do NOT set `use_merge_queue=true` on an `ineligible` / `unsupported` probe — the
`manage-config` set-time validation would reject it anyway (see
[`manage-config` api-reference.md § Probe-backed set-time validation (`use_merge_queue`)](../../manage-config/standards/api-reference.md#probe-backed-set-time-validation-use_merge_queue)).

## Idempotence and non-clobbering

- The queue's merge method **tracks `pr_merge_strategy`** (the
  `default:branch-cleanup` step param) from project config at enable time: a
  fresh provision writes the mapped method, and a re-run against a configured
  repo reconciles any drift.
- The step is **idempotent** in the reconciled sense: a re-run against an
  `eligible_configured` project mutates nothing when the queue's configured
  merge method already matches `pr_merge_strategy` (`changed: false`, the
  "already configured — no change made" note). A method drift is corrected
  exactly once (`changed: true` with the reconcile detail); the run after that
  is a no-op again.
- The `enable` verb is itself idempotent under the same definition, so a
  double-invocation is safe.
- The step **never clobbers** an operator's prior `use_merge_queue` choice: it
  only writes `use_merge_queue=true` on an explicit "Enable now" answer against
  an `eligible_unconfigured` probe.
