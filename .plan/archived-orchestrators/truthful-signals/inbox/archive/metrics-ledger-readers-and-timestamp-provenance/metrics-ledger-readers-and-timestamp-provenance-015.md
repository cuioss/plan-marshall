envelope_version=1
sender_type=plan
sender_id=metrics-ledger-readers-and-timestamp-provenance
epic=truthful-signals
kind=landing
created=2026-08-24T20:13:13Z
lifecycle=superseded
superseded_by=metrics-ledger-readers-and-timestamp-provenance-016.md

plan_id=metrics-ledger-readers-and-timestamp-provenance
pr=1342
merge_state=merged
merge_mechanism=merge_queue
merge_commit=91bbe7470
change_type=bug_fix
planning_lane=deep

# Landing: stop readers from reading absence as measurement

## Outcome

PR #1342 — `fix(plan-marshall): stop readers from reading absence as measurement` —
merged to main via the merge queue at `91bbe7470`. All six phases complete. Nineteen
completed tasks across nine deliverables; merged footprint 28 files, 16 of them Python
tests. Plan wall clock 22h29m; 6,568,833 tokens.

The plan's subject was this epic's own theme applied to readers: a count that was never
measured now renders as `unavailable` rather than as `0`, and gates that withheld only on
a missing denominator were widened to withhold on either side.

## Verification, and the caveat that matters

Local verification at the merge candidate: 21,896 tests green, per-bundle and whole-tree
quality gates, test-compile, whole-tree plugin-doctor across 37 rules.

CI green is NOT evidence for this PR, and that is recorded as an operator-ACCEPTED defect
(finding `21cc74`). PR #1342 has ZERO `pull_request`-event runs. All three runs are
push-event runs, and in each one `verify / verify` is SKIPPED — by design, because the
commit is covered by an open PR — while the required `verify / conclusion` reports SUCCESS
in seconds. The push run defers to a PR run that never fires. Confirmed materially, not
theoretically: at head `031e5293e` this configuration reported CI green while a local
module-tests run on the same tree was 17,977 passed / 2 failed, and those two failures were
caught by a review bot rather than by CI.

The merge rests on the local whole-tree verification and on the merge queue's own
`merge_group` run, which is not subject to the docs-only skip. The root cause of the
missing `pull_request` trigger is NOT established and must not be guessed.

## Findings routed to this epic

Ten `candidate-lesson` messages (001-010) were routed by `plan-retrospective` from a
16-aspect sweep. This step adds four more, covering how the run was DRIVEN rather than what
it produced:

- 011 — `mark-step-done` accepts a `head_at_completion` SHA it never resolves. Two
  fabricated full SHAs, the second immediately after the first was corrected; the value is
  the next self-review round's `--since-ref` anchor.
- 012 — convergent remedy for an over-claiming sentence is DELETION, not correction. Four
  findings reached it independently; one round was self-seeded by the previous round's own
  fix.
- 013 — a defect class closed by INSTANCE COUNT rather than by class left a third copy
  surviving at the render site.
- 014 — verify a review finding before ACTING on it, not only before rejecting it. A
  plausible remedy would have broken a deliberately frozen legacy decoder.

## Open state at landing

One Q-Gate finding remains PENDING and needs an operator decision:

- `191008` — `worktree-remove` timed out TWICE against a fixed 60s git budget, defeated by
  an 11.3 MB `.plan/temp/pytest-basetemp` tree containing nested git repositories created
  by worktree/lock test fixtures. The first attempt was killed partway through and had
  already deleted four tracked root files (`LICENSE.md`, `build.py`, `pw`, `pw.bat`); those
  were restored and the tree re-verified clean. The worktree at
  `.plan/local/worktrees/metrics-ledger-readers-and-timestamp-provenance` REMAINS ON DISK
  and is STALE, and the local branch cannot be deleted while it is checked out there. Plan
  state is not at risk — `integrate_into_main` already moved the plan dir back to main.
  Operator cleanup, when wanted, is a manual `rm` of that path followed by
  `git worktree prune`; automated deletion was declined. Two remedies named for a follow-up
  plan: give `worktree-remove` a caller-settable timeout, or have the test fixtures write
  basetemp outside the worktree.

Seven findings resolved `taken_into_account`, each naming a remedy for a follow-up plan and
each out of this plan's footprint: `f84182`, `5af193`, `2f0994`, `10d566`, `b2153c`,
`e0e2c8`, `dfcad2`.

## Operational note — reinforces message 001, deliberately NOT filed as a new lesson

Message 001 filed "a stale served skill body is indistinguishable from a live contract"
against a stale plugin-cache enum. This step hit the same class in a NEW SHAPE and reports
it here rather than as a duplicate candidate-lesson.

The plugin registry served this dispatch its skill bodies from cache `0.1.1240`, while the
executor — regenerated during this very finalize by `finalize-step-sync-plugin-cache` — is
`0.1.1542`. Between those two versions the skill `marshall-orchestrator` was RENAMED to
`plan-orchestrator`. The served body's "Canonical invocations" section, which plugin-doctor
treats as source of truth, therefore documents
`plan-marshall:marshall-orchestrator:orchestrator` — a notation the live executor rejects
with `Unknown notation`. Conversely the dispatch's own `skills[]` carried
`plan-marshall:plan-orchestrator`, the CORRECT current name, which the Skill tool refused
as `Unknown skill` because its registry is the stale one. Neither the served body nor the
skill registry was usable as the authority; the step proceeded by resolving the notation
from the executor's own `SCRIPTS` mapping table.

Two things distinguish this instance and are worth the epic's attention:

1. The failure was LOUD. The executor's unknown-notation refusal is correct behaviour and
   is what made recovery possible — this is the well-behaved end of the class, and worth
   recording as such alongside the silent cases.
2. The drift is partly SELF-INFLICTED BY THE FINALIZE ORDER. A finalize step regenerates
   the executor mid-run, so every subsequent leaf in the SAME finalize chain runs pre-sync
   skill bodies against a post-sync executor. Only a session restart re-seats skill bodies,
   and a finalize chain cannot restart itself. This is a structural ordering hazard, not
   only an instance of the known registry-pin incident class.
