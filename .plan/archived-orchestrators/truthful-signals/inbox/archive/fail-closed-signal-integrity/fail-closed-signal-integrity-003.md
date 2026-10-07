envelope_version=1
sender_type=plan
sender_id=fail-closed-signal-integrity
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T21:09:48Z

component=project:finalize-step-lessons-housekeeping
category=bug
bundle=plan-marshall

# lessons-housekeeping cannot satisfy edit-pushability and corpus access at one step order

`lessons-housekeeping` was moved into the settle band (`order: 4`) so that the edits it
makes are still pushable to the PR head. That move broke its access to the carried-lesson
corpus, because corpus resolution is main-anchored while the settle band runs against the
worktree.

Both halves are load-bearing and **there is no step order that satisfies both today**:

- Early enough to reach the main-anchored corpus → too early for its edits to be pushed.
- Late enough to be pushable → the corpus it must reconcile against is out of reach.

This is a structural conflict, not a bug in one of the two behaviours. It is filed as a
candidate lesson so the epic tracks it as a known-unsolved constraint rather than
rediscovering it at the next housekeeping change.

## Impact

Lesson housekeeping runs but silently reconciles against the wrong (or an empty) corpus
view, which reads as "nothing to housekeep" — another benign-looking verdict standing in for
"could not look". Directly compounded the D5 retirement blockage in this run.

## Solution

No solution exists at one step order. The candidate directions, none of them validated here:

1. Decouple corpus resolution from cwd — give the housekeeping step an explicit
   main-anchored store handle so its order stops determining what it can see.
2. Split the step: a main-anchored read/classify pass early, a pushable apply pass in the
   settle band, with the classification handed between them.

Direction 1 is the same root cause as the `restore-from-plan` fail-open (CWD-keyed store
resolution producing a benign-looking empty read) and should probably be sized with it.
