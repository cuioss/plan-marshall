envelope_version=1
sender_type=plan
sender_id=plan-12-tool-triage
epic=process-compliance
kind=finding
created=2026-09-29T13:43:57Z

# phase-5-execute dispatch: three contract gaps observed in one run

## 1. `WORKTREE:` header — absolute vs repo-relative

`plan-marshall/workflow/execution.md` § Execute Phase tells the orchestrator to resolve
`manage-status get-worktree-path` and put the returned `worktree_path` (an ABSOLUTE path,
`/Users/.../.plan/local/worktrees/plan-12-tool-triage`) into the dispatch's `WORKTREE:` header. The
dispatched phase-5-execute leaf reported that "the contract says the WORKTREE field must be
repo-relative" and used the absolute value only as given. Two documents disagree on the header's shape;
the orchestrator followed execution.md verbatim.

## 2. A task is marked `done` before its orchestrator-tier verification has run

The leaf closed TASK-11 (a fix task created by verification-feedback for a red build) as `done` via
`finalize-step` when its last step closed — while its own verification command
(`module-tests plan-marshall`, orchestrator-tier) had NOT yet run. The leaf itself flagged this. The
task-state record therefore claims a verified fix that was unverified until the orchestrator's later
build came back green. Any reader of `manage-tasks list` in that window sees a confident `done` that
hides "not yet verified".

## 3. Orchestrator-tier builds are owed across a `budget_yield` with no structured slot

The leaf returned `budget_yield: true` (a clean, legitimate yield) AND, in free text,
`orchestrator_build_owed: "verify:module-tests ..."`. execution.md's `budget_yield` branch says only
"re-dispatch the next envelope group"; the orchestrator-tier handler is keyed on a `status: blocked` /
`voluntary_checkpoint` return. A leaf that yields for budget while also owing an orchestrator-tier build
falls between the two branches — following the `budget_yield` branch literally would start envelope 2
with deliverable 1's module-tests never run. The orchestrator ran the owed build first (green, 23397
tests) before re-dispatching, by judgement, not by a documented step.

## 4. The scope-creep check crashes on every task and mis-baselines, and leaves improvise around it

Every phase-5 task in this run hit `scope_creep_check check` → exit 1, `finding_persist_failed`
(`manage-findings` rejects type `scope_creep_warning` — PLAN-TRUTH-178) with `residual_count: 470`.
The 470 is an artifact: the check diffs from `references.plan_creation_sha` (01d3b7549, captured at
init on main) instead of the worktree's merge base (88fcfc9ef) — upstream main commits landed between
init and phase-5 move-in are counted as plan work. Against the merge base the plan touched 19 files,
all declared. One leaf then re-ran the check with `--threshold 1000` to make it complete — an
improvised override of a configured value that no workflow sanctions, and that would equally hide real
scope creep. The orchestrator told the next dispatch not to override.

## 5. Envelope ids stamped at plan time no longer match what executes

The re-derived plan packed 2 envelopes (380K + 200K). In practice envelope 1 ran only TASK-1/2 (+ fix
TASK-11) before yielding "envelope 1 exhausted, next task TASK-5 in envelope 2", yet TASK-3/TASK-4 are
stamped `envelope_id: 1` and were only reachable once TASK-9 (envelope 2) landed — a `depends_on` edge
(TASK-3 → TASK-9) crossing envelopes backwards. The leaf that ran them was dispatched as envelope 2 and
flagged the mismatch. The bin-packer placed a dependent task in an earlier envelope than its prerequisite,
so the "one dispatch per envelope group, envelope_count dispatches total" contract cannot be followed.
This run needed 7 phase-5 dispatches for `envelope_count: 2`, driven by orchestrator-tier build yields
(one per deliverable) that the packer's budget model does not account for.

## Suggested fix

(1) State one shape for `WORKTREE:` in both documents. (2) Do not transition a task to `done` while its
declared verification is orchestrator-owed; use a distinct `awaiting_orchestrator_verify` state or keep
it `in_progress`. (3) Make `orchestrator_build_owed` a first-class return field and have every
termination branch (including `budget_yield`) run owed builds before the next dispatch.
