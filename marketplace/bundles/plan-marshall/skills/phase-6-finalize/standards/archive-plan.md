---
lane:
  class: core
  cost_size: XS
name: default:archive-plan
description: Archive the completed plan
order: 1100
mutates_source: false
destroys:
  - plan-directory
default_on: true
presets:
  - local
  - standard
  - full
implements: plan-marshall:extension-api/standards/ext-point-finalize-step
---

# Archive Plan

Pure executor for the `archive-plan` finalize step. Archives the completed plan to `.plan/archived-plans/`.

## Exit-code convention for every script call

Every `python3 .plan/execute-script.py` call in this document — of EVERY notation, **not only `manage-*`** — carries the following exit-code contract unless a step explicitly states otherwise. The scope is widened past `manage-*` because this document invokes non-`manage-*` scripts too, and a `manage-*`-scoped convention left exactly those calls uncovered — the swallowed-rejection gap.

- **`exit_code == 0` AND `status: success`**: parse the returned TOON and use the value as the step describes.
- **`exit_code == 0` with a `status` other than `success`**: NOT a usable value — STOP exactly as the `exit_code != 0` disposition below requires, with one difference in what the error TOON carries: on this path the diagnostic is on STDOUT, not stderr. Preserve the stdout **error envelope** — the `status`, `error`, and `message` fields — verbatim into the returned error TOON; they are the only account of the cause that exists. A zero exit is not evidence the operation succeeded; a script MAY print `status: error` and still exit 0. Read `status` FIRST, and never read a **success-payload** field off a non-`success` return — the three diagnostic fields above are not success payload, and discarding them leaves the step reporting a failure with no cause.
- **`exit_code != 0`**: STOP and return an error TOON to the orchestrator carrying the script's stderr verbatim. Non-zero exits include `argparse_rejection` (exit 2) — silent swallowing of `wrong_parameters` rejections is the prohibited anti-pattern; "log and continue" is equally forbidden.

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `archive-plan` in `manifest.phase_6.steps`. When the dispatcher runs this step, the document executes top to bottom — there is no skip-conditional branching at this layer.

**CRITICAL**: Archive MUST be the last **plan-file** step in the pipeline because it moves plan files (including status.json), which breaks `manage-status transition` and other manage-* scripts. All plan-file operations must complete before archive. The session-store sweep below is the one section that deliberately runs AFTER the archive call — it touches no plan file, only the per-session cache under `~/.cache/plan-marshall/sessions/`.

Lesson-sourced plans carry their `lesson-{id}.md` file along when the plan directory is archived — no separate mark-applied step is needed.

## Pre-Archive Foreign-PR Landing Gate

**Runs FIRST, before "Mark Step Complete" and before the archive call.** A *foreign* deliverable — one whose change lands in a different repository than the one being planned — has its done-ness measured at the commit by the rest of the pipeline, which is structurally wrong: nothing carries that commit into review or merge, so a foreign task can report `done` with **no PR anywhere**. This gate measures foreign done-ness at the PR instead, and refuses to archive while any foreign deliverable's change is `pushed_no_pr` (committed and pushed to a branch that no pull request carries).

The gate reads two deterministic signals — the `foreign` column on `manage-solution-outline list-deliverables` (the population it iterates) and the `ci pr landing-state` verb (the per-repository done-ness discriminator) — not artifact prose.

```bash
python3 .plan/execute-script.py plan-marshall:phase-6-finalize:foreign_pr_gate \
  check --plan-id {plan_id}
```

Parse the returned TOON `status`. The gate CLEARS only when it has positively read an in-model landing state for every foreign deliverable's repository and none is `pushed_no_pr`; every other outcome STOPS the archive:

- **`status: clear`** — no foreign deliverable is `pushed_no_pr`, and every foreign repository's landing state was read (this includes the common zero-foreign-deliverable case). Proceed to "Mark Step Complete" below.
- **`status: blocked`** — at least one foreign deliverable's repository is `pushed_no_pr`. **STOP. Do NOT mark the step done and do NOT archive.** Return an error TOON to the orchestrator carrying the gate's `message` and its `blocking[]` rows verbatim (each names a `repo_root` and the `deliverables` that targeted it). The condition is **blocking**, not advisory: the plan cannot complete until a pull request is opened for each blocking foreign change, because a change with no PR anywhere is not done.
- **`exit_code != 0` / `status: error`** — the gate could not evaluate or could not read the evidence for at least one foreign deliverable: the solution outline could not be listed, the project root could not be resolved, a foreign repository root could not be resolved, or its landing state came back unreadable or outside the declared model (the `unresolved[]` rows name each). Per the exit-code convention above, STOP and return the error TOON verbatim. The gate fails **closed** — an un-evaluable or un-read landing gate must not certify the population clean; resolve every `unresolved[]` item (bring the foreign checkout into reach, or open its PR) before re-running.

## Mark Step Complete

Record that this step ran on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time. This MUST happen BEFORE the archive call below, because archive moves `status.json` out of `.plan/plans/{plan_id}/` and any subsequent `mark-step-done` call would fail to locate the plan.

Pass a `--display-detail` value alongside `--outcome done` so the output-template renderer can surface the archive destination. `{archive_path}` is the canonical archive location `.plan/archived-plans/{date}-{plan_id}` (the same path `manage-status archive` will move the plan directory to in the next call):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step archive-plan --outcome done \
  --display-detail "-> {archive_path}"
```

## Archive

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage-status archive \
  --plan-id {plan_id}
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[STATUS] (plan-marshall:phase-6-finalize) Plan archived: {plan_id}"
```

## Sweep the session-binding store

This section runs **after** the archive above — deliberately, and it is the only
part of this document that does. By this point the plan whose finalize is
executing has already left `.plan/local/plans/`, so its own now-stale
`active-plan` slot is collected by the same sweep that collects every other
archived plan's residue. Running the sweep before the archive would leave this
plan's slot behind until some later plan's finalize happened to run.

This is the **automatic caller** for the session-store GC — without it the sweep
has no scheduled invocation and the per-session cache grows unboundedly across
plans.

**Main-anchored-caller invariant**: this step runs at `order: 1100` (the terminus
of the banded allocation contract), after `default:branch-cleanup` has removed the
worktree, so the process cwd is the main checkout. That is load-bearing, not incidental — `session_binding._plan_is_live`
resolves plan directories **relative to the process cwd**, so a sweep fired from
inside a worktree would find none of the main checkout's live plan dirs and would
judge every other live plan's binding stale. Any future caller of `session doctor
--fix` MUST likewise run main-anchored.

The sweep is **best-effort**: it MUST NOT fail the finalize. A non-zero exit or an
unparseable TOON is logged and stepped over, never escalated — the plan is already
archived and the pipeline is complete.

This section carries **no `mark-step-done` call of its own** — the step's single
terminal record was already landed in "Mark Step Complete" above, before the
archive moved `status.json` out of reach.

1. Run the GC:

   ```bash
   python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime \
     session doctor --fix
   ```

   Parse `scanned`, `stale_count`, `gc_removed`, `conflict_count`, and
   `orphans_removed` from the returned TOON.

2. Report the outcome to the **global** work log:

   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
     work --level INFO --message "[STATUS] (plan-marshall:phase-6-finalize) Session-binding store swept: plan_id={plan_id} scanned={scanned} stale_count={stale_count} gc_removed={gc_removed} conflict_count={conflict_count} orphans_removed={orphans_removed}"
   ```

   **`--plan-id` is deliberately omitted here — do NOT add it.** This is the
   documented global-log path (see `manage-logging`, the `work` verb's
   global-store form, which omits `--plan-id` by design), not a WL-C omission
   defect. Adding `--plan-id {plan_id}` would be the anti-pattern in this one
   position: the plan directory has just been moved to `archived-plans/`, so a
   plan-scoped write would either fail to resolve or bury a cross-plan
   housekeeping record inside an archived plan's own log where no later sweep can
   read it. The sweep is machine-global housekeeping across every plan's session
   slots, so its record belongs in the global log — the `plan_id=` token in the
   message body carries the provenance instead.
