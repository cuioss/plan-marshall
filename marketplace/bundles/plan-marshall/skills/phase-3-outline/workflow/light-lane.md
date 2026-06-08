---
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# Light-Lane Collapsed Scoping Workflow

Single-envelope collapsed planning lane for `planning_lane == light` plans. It folds **refine-no-loop** (read the clarified request + declared affected files, no clarification iteration), **Simple-outline** (derive Simple-Track deliverables directly), and **deliverable-derivation** into ONE `execution-context` dispatch — replacing the deep lane's refine-loop → Complex-outline → q-gate-validation pipeline for the surgical / single-module band the lane router classified light.

Discovery is **bounded by construction** (DQ2): the lane reads ONLY the declared affected files plus their one-hop direct neighbours, capped at `AFFECTED_NEIGHBOUR_CAP = 25` files — there is NO codebase-sweep step. A monotonic one-way escalation ratchet (DQ3) self-promotes the plan to the deep lane the moment evidence contradicts the cheap light classification; the leaf returns `outcome: escalate_to_deep` and the orchestrator owns the deep-lane re-dispatch.

This workflow reuses the existing [Deliverable Template](../SKILL.md#deliverable-template-inline-reference), the [File-type classifier](../standards/outline-workflow-detail.md#file-type-classifier), and the [Step 9c design-intent classification](../standards/outline-workflow-detail.md#step-9c-read-target-skill-design-intent) verbatim — it introduces no new deliverable schema and no new script entry point.

## Inputs

| Prompt-body field | Required | Description |
|-------------------|:--------:|-------------|
| `plan_id` | Yes | Plan identifier. |
| `WORKTREE` | Yes | Repo-relative working directory (`.` for main checkout). |

Skills the caller MUST forward in `skills[]`: `plan-marshall:manage-plan-documents` (request read), `plan-marshall:manage-solution-outline` (outline write), `plan-marshall:manage-references` (scope/track persist), `plan-marshall:manage-status` (metadata read + escalation), `plan-marshall:manage-architecture` (bounded neighbour resolution), `plan-marshall:manage-logging` (decision + work entries).

## Constants

| Constant | Value | Meaning |
|----------|-------|---------|
| `AFFECTED_NEIGHBOUR_CAP` | `25` | Hard cap on the bounded read set (`\|A\| + \|neighbours\| ≤ 25`). Hitting the cap is itself an escalation trigger (DQ3). |
| `SINGLE_BAND_MAX` | `8` | The surgical/single-module declared-file band. `\|A\| > SINGLE_BAND_MAX` is an escalation trigger. |

## Exit-code convention for `manage-*` script calls

Every `manage-*` script call in this document carries the following exit-code contract unless a step explicitly states otherwise:

- **`exit_code == 0`**: parse the returned TOON and use the value as the step describes.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

## Workflow

### Step 1: Read the Clarified Request and Seed Set A (no clarification loop)

Read the clarified request narrative (falling back to the original input) — this is the refine-no-loop collapse: there is NO iterate-to-confidence loop in the light lane. The cheap lane router already decided the request was concrete enough to plan directly.

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-documents:manage-plan-documents \
  request read --plan-id {plan_id} --section clarified_request
```

`--section clarified_request` falls back to `original_input` automatically when the clarified section is absent. Extract the **declared affected files** — the explicit repo-relative file paths named in the request body. This is the seed set `A`. Resolution uses the same path regex the lane router's S5 concreteness signal uses; do NOT discover files the request did not name.

### Step 2: Resolve the DQ2 Bounded Read Set (A + one-hop neighbours, capped)

For each file `f ∈ A`, resolve exactly ONE hop of direct neighbours — never transitive, never a sweep:

1. **Imports/includes that `f` itself declares** — parse `f`'s own import/from/require lines, resolve each to an in-repo path. The neighbour's own imports are NOT followed.
2. **The paired test (or paired production file)** of `f` via the deterministic test-path mapping (`marketplace/bundles/{b}/skills/{s}/scripts/x.py` ↔ `test/{b}/{s}/test_x.py`).
3. **The owning `SKILL.md`** — the `marketplace/bundles/{b}/skills/{s}/SKILL.md` enclosing `f`, so the Step 9c design-intent read is satisfiable without discovery.

Neighbour resolution uses the **structured architecture inventory**, never a Grep/Glob sweep:

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  which-module --path {f}
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  files --module {module}
```

**Cap check (DQ2 / DQ3 trigger):** if `|A| + |neighbours| > AFFECTED_NEIGHBOUR_CAP` (25), the light lane does NOT silently truncate. The cap-hit is the cheap structural proxy for "this change is bigger than declared" — record `discovery_bound_hit: true` with the file count and jump directly to **Step 4 (Escalation Ratchet)** with `trigger = explosion`. Otherwise record the bounded read set and continue.

Log the bound for auditability:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[STATUS] (plan-marshall:phase-3-outline:light-lane) Bounded read set: |A|={a_count} + neighbours={neighbour_count} = {total} (cap {cap})"
```

### Step 3: Minimal Premise-Check (cheap refine Step 3c)

Run the **minimal premise-check** — the cheap version of the deep refine's premise / narrative-vs-code safety check (refine Step 3c). Reading ONLY the bounded set from Step 2, verify that the request's premise is consistent with the read code: the files the request says it will change exist and are shaped the way the request assumes (the "looks concrete but the fix is wrong/obsolete" lesson-derived failure mode).

**On a premise contradiction** (the request's stated premise contradicts the read code): jump to **Step 4 (Escalation Ratchet)** with `trigger = premise`.

The premise-check is gated by `ceremony_policy.planning.revalidation` — when that gate resolves to `never`, skip the check (the operator owns the risk, having been warned at config-set time per the DQ4 footgun catalogue). `auto` / `always` run it.

### Step 4: Escalation Ratchet (DQ3 — one-way light→deep)

The ratchet is monotonic light→deep; it never reverts. ANY of the following triggers fires escalation:

1. **Affected-file-set explosion** — the Step 2 cap-hit (`|A| + |neighbours| > 25`), OR the declared count alone exceeds the band (`|A| > SINGLE_BAND_MAX = 8`).
2. **Premise-check failure** — Step 3 found the request premise contradicts the read code.
3. **Cross-cutting impact** — a declared affected file is a published cross-bundle public symbol whose one-hop neighbour resolution reveals consumers OUTSIDE the bounded set.

On a fire, escalate via the D4 one-way escalate verb (see `manage-status` Canonical invocations → `planning-lane`), set the trigger, and return the escalate signal to the orchestrator. The leaf does NOT dispatch the deep lane itself (leaf-cannot-dispatch) — it returns `outcome: escalate_to_deep` and the orchestrator owns the deep-lane re-dispatch:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status planning-lane escalate \
  --plan-id {plan_id} --trigger {explosion|premise|cross_cutting} --persist
```

The escalate verb sets `status.metadata.planning_lane = deep`, `lane_escalated = true`, and `escalation_trigger`; the flag is sticky and there is no downgrade. Then return the escalate TOON (see Output § escalate). When NO trigger fires, continue to Step 5.

### Step 5: Derive Simple-Track Deliverables and Write the Outline

No clarification loop, no Complex-Track discovery — derive the deliverables directly from the bounded read set, reusing the existing Simple-Track authoring rules verbatim:

1. **Classify each deliverable's `affected_files`** against the [File-type classifier](../standards/outline-workflow-detail.md#file-type-classifier) (six buckets) BEFORE assigning `profiles[]`. Record the resolved bucket in the `<!-- bucket: ... -->` comment on the `**Profiles:**` line.
2. **For any deliverable that touches an existing skill**, run the [Step 9c design-intent classification](../standards/outline-workflow-detail.md#step-9c-read-target-skill-design-intent) and emit the resulting `**Design notes:**` block — the owning `SKILL.md` is already in the bounded read set (Step 2), so this needs no extra discovery.
3. **Author each deliverable** using the [Deliverable Template](../SKILL.md#deliverable-template-inline-reference) verbatim (field order, `**Intent gloss:**` where the title head morpheme is a planning-domain verb, per-file `(intent)` markers). Resolve verification commands via `architecture resolve`.

Write `solution_outline.md` via the standard three-step path-allocate flow (resolve path → Write tool → validate). Use `write` on first entry, `update` on re-entry:

```bash
# 1. Resolve the target path
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  resolve-path --plan-id {plan_id}
# 2. Write the outline content (title, plan_id, compatibility header, Summary,
#    Overview, Deliverables) directly to the resolved path via the Write tool.
# 3. Validate on disk
python3 .plan/execute-script.py plan-marshall:manage-solution-outline:manage-solution-outline \
  write --plan-id {plan_id}
```

Persist the (possibly refined) scope/track to references.json so phase-4-plan reads a consistent value:

```bash
python3 .plan/execute-script.py plan-marshall:manage-references:manage-references \
  set --plan-id {plan_id} --field scope_estimate --value {scope_estimate}
```

Log completion:

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO \
  --message "[STATUS] (plan-marshall:phase-3-outline:light-lane) Derived {deliverable_count} deliverable(s) from bounded read set — light lane, no escalation"
```

### Step 6: Transition Phase

The light lane completes the outline phase in one envelope; transition to phase-4-plan:

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status transition \
  --plan-id {plan_id} --completed 3-outline
```

## Output

The minimum contract this workflow doc (an `ext-point-execution-context-workflow` implementor) MUST return:

```toon
status: success | error
display_detail: "<≤80 char ASCII summary, no trailing period>"
```

### success (deliverables derived)

```toon
status: success
display_detail: "light lane: {deliverable_count} deliverables, no escalation"
plan_id: {plan_id}
planning_lane: light
deliverable_count: {N}
discovery_bound_hit: false
qgate_validation_required: false
```

`qgate_validation_required` is always `false` on the light lane — the bounded read set + premise-check + escalation ratchet are the light lane's verification, and the deep-lane q-gate-validation is reached only via escalation.

### escalate (DQ3 ratchet fired)

```toon
status: success
display_detail: "escalate_to_deep: {trigger}"
plan_id: {plan_id}
outcome: escalate_to_deep
escalation_trigger: {explosion|premise|cross_cutting}
planning_lane: deep
lane_escalated: true
```

The orchestrator (`plan-marshall:plan-marshall/workflow/planning-outline.md`) reads `outcome: escalate_to_deep` and re-dispatches the deep lane (refine-loop + Complex-outline) fresh. The leaf never dispatches it.

## Related

- [`phase-3-outline/SKILL.md`](../SKILL.md) — the lane-routing preamble that dispatches this doc when `planning_lane == light`, and the Deliverable Template / File-type classifier this doc reuses.
- [`manage-status` Canonical invocations → `planning-lane`](../../manage-status/SKILL.md#planning-lane) — the D4 `route` / `escalate` subcommand contract.
- [`dispatch-granularity.md`](../../extension-api/standards/dispatch-granularity.md) — why the light lane collapses three phases into one envelope (bundle when steps share context).
