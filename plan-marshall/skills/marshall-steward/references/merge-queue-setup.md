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

### Step MQ-0: Defer gate (externally-managed queue)

Before probing, read the project-level defer signal:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  project get --field merge_queue_managed_externally
```

**When the value is `true`**, the org — not plan-marshall — owns the merge
queue. Skip the `AskUserQuestion` entirely and make **no** `enable` call. Run
only the probe (Step MQ-1) to read the platform's reported state, align
`use_merge_queue` to it, log the defer as a STEWARD decision, and stop — do not
continue to Step MQ-2:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  decision --level INFO \
  --message "[STEWARD] (plan-marshall:marshall-steward) Merge-queue provisioning deferred — merge_queue_managed_externally=true; probe-only, no enable call, no operator prompt"
```

Aligning means persisting `use_merge_queue=true` when the probe reports
`eligible_configured`, and leaving it at its default (off) otherwise, via the
same documented step-set call used in Step MQ-2. The set-time validation defers
on this field too, so the write is permitted without a probe verdict (see
[`manage-config` api-reference.md § Probe-backed set-time validation (`use_merge_queue`)](../../manage-config/standards/api-reference.md#probe-backed-set-time-validation-use_merge_queue)).

**When the value is `false` or absent**, continue to Step MQ-1 unchanged.

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
anything) was reconciled. Branch on `externally_managed` first:

- `externally_managed: true` → the queue is configured under a ruleset
  plan-marshall does not own. Make **no** reconcile call. Persist
  `use_merge_queue=true` via the documented step-set call below, and log:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    work --level INFO \
    --message "[STEWARD] (plan-marshall:marshall-steward) Merge queue externally managed — {detail from enable TOON}; use_merge_queue=true"
  ```

When `externally_managed` is absent or `false`, plan-marshall owns the ruleset
and the existing reconcile behaviour applies unchanged:

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

Inspect the returned `status` rather than asserting `status: success`
unconditionally — on GitHub the `enable` verb refuses when the target repo's
`.github/workflows` carry no `merge_group` CI trigger (the bricks-main footgun:
every queued PR would form a merge group that never receives a required check,
stalling the queue and blocking all merges to the default branch). This refusal
is **distinct** from the auth-scope and `ineligible` / `unsupported` refusals
already documented — the platform allows the feature and auth is sufficient, but
provisioning the queue anyway would brick the default branch.

- **On `status: error`** naming a missing `merge_group` trigger — surface the
  actionable message to the operator verbatim and leave `use_merge_queue` at its
  default (off), exactly as the `ineligible` / `unsupported` branch below does.
  Do NOT persist `use_merge_queue=true`:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    work --level WARNING \
    --message "[STEWARD] (plan-marshall:marshall-steward) Merge queue enable refused — {actionable merge_group message from enable error}; leaving use_merge_queue off"
  ```

- **On `status: success`** — persist the opt-in. `use_merge_queue` is a step-owned
  param of the `default:branch-cleanup` step in the phase-6-finalize keyed-map
  `steps` structure (mirroring `pr_merge_strategy`):

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
    plan phase-6-finalize step set --step-id default:branch-cleanup --param use_merge_queue --value true
  ```

  A successful create may also carry a `warnings[]` field. These are
  **advisory** — the queue WAS created and `use_merge_queue=true` is still
  persisted. This is categorically different from the three refusal paths
  (missing `merge_group` trigger, auth-scope, `ineligible` / `unsupported`),
  each of which leaves `use_merge_queue` off. Surface every entry to the
  operator verbatim, one line each:

  ```bash
  python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
    work --level WARNING \
    --message "[STEWARD] (plan-marshall:marshall-steward) Merge queue created with warning — {warning entry from enable TOON}"
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
  `eligible_configured` project that plan-marshall owns mutates nothing when the
  queue's configured merge method already matches `pr_merge_strategy`
  (`changed: false`, the "already configured — no change made" note). A method
  drift is corrected exactly once (`changed: true` with the reconcile detail);
  the run after that is a no-op again. On the **foreign-ruleset** path that
  "no change made" note does not apply — the verb returns its own
  `externally_managed: true` envelope with a distinct detail, and nothing is
  compared or corrected.
- The `enable` verb is itself idempotent under the same definition, so a
  double-invocation is safe.
- The step **never clobbers** an operator's prior `use_merge_queue` choice: it
  only writes `use_merge_queue=true` on an explicit "Enable now" answer against
  an `eligible_unconfigured` probe, on the externally-managed path (Step MQ-0's
  defer alignment, and the `externally_managed: true` sub-branch), or where the
  probe already reports the queue configured.
- The step **never touches a ruleset plan-marshall did not create** — no create,
  reconcile, rename, or delete. On an externally-managed queue the step reports
  and aligns local config only.
