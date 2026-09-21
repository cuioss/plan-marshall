envelope_version=1
sender_type=plan
sender_id=post-run-steps-ordered-before-their-evidence
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-02T21:53:43Z

component=plan-marshall:phase-6-finalize
category=bug
title=A guard bound to a path its own pipeline deletes has a structurally unreachable failure arm

# A guard bound to a path its own pipeline deletes has a structurally unreachable failure arm

## Observation

PLAN-CIS-028's subject was "post-run review steps ordered before their evidence exists". The plan reproduced its own target defect **twice**, in the code it wrote to fix that defect:

1. **TASK-021's new `post_run_source_guard`** was wired to observe `{worktree_path}`. Branch cleanup removes that tree *before* any `post_run_review` step runs. The guard's `clean: false` arm was therefore structurally unreachable — a guard that could never fire, shipped inside the plan whose whole purpose was to stop steps from running before their evidence exists.
2. **`finalize-step-review-retrospective`** carried the same defect from the same move: it resolved `--head-at-completion` from the removed worktree.

Both were caught by **self-review**, not by the test suite.

## Why the tests did not catch it

The runtime tests exercised the **script** against a synthetic repo. They never exercised the **call-site binding** — which path the dispatcher actually hands the script at the moment the step runs. A script that behaves correctly against a tree that exists is fully green while the only tree it is ever given has already been deleted.

The two are different assertions:

- *"Given a repo at P, the guard reports dirty/clean correctly."* — what was tested.
- *"At the moment this step is dispatched, the P the dispatcher binds still exists."* — what was broken.

## Rule

- When a guard, check, or instrument observes a **path supplied by its caller**, the test that matters asserts the **call-site binding at dispatch time**, not the script's behaviour against a synthetic fixture. A green script-level test is not evidence the binding is live.
- Before shipping any new predicate, ask which arm can never be reached given the surrounding pipeline's ordering and cleanup. A predicate whose negative arm is unreachable is a vacuous guard — the recurring archetype, now with an instance **introduced by a fix for that same archetype**.
- Ordering-sensitive lifecycle facts (this tree is removed at step N) belong in the derivation guard, so a newly-added observer inherits the constraint instead of rediscovering it by review.

## Impact

Applies to every finalize step and every plan-marshall guard that takes a path/ref argument resolved by the dispatcher: `post_run_source_guard`, `finalize-step-review-retrospective` (`--head-at-completion`), and any future `post_run_review` / `head_dependent` step. Also generalizes to the recurring vacuous-guard family tracked across the epics.
