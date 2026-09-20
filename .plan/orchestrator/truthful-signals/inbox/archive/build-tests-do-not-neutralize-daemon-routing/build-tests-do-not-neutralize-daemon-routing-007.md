envelope_version=1
sender_type=plan
sender_id=build-tests-do-not-neutralize-daemon-routing
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T17:02:44Z

component=plan-marshall:phase-6-finalize
category=bug

# Doc-contract drift: architecture-refresh is INLINE in its own doc and DISPATCHED in the roster

Found in passing during this plan; **not fixed here (out of scope)**. Filed so it gets an owner.

Two source-of-truth documents disagree about the same finalize step:

- `architecture-refresh.md` declares itself **INLINE**, and gives a load-bearing reason: its Tier-1 prompt needs `AskUserQuestion`, which a dispatched leaf structurally cannot fire.
- `dispatch-inline-split.md` rosters `architecture-refresh` under **Dispatched** steps.

The self-declaration carries the reasoning and the roster does not, which suggests the roster is the stale side — but that is an inference, not a verification, and this plan did not verify it.

The consequence if the roster wins at runtime is not cosmetic: a dispatched `architecture-refresh` reaching its Tier-1 prompt cannot reach the operator. It must return a prompt-required envelope, and any path that instead assumes the prompt fired would proceed on an unanswered question.

## Solution

Reconcile the two docs under one owner. The reconciliation must also decide the runtime behaviour, not just the prose: if the step stays inline, the roster entry is removed; if it becomes dispatched, the Tier-1 prompt must be converted to the prompt-required-envelope return path first.

More generally: **when two documents both describe the same step's dispatch mode, one of them is a duplicate source of truth and should become a cross-reference.** The `no duplication` documentation standard exists for exactly this; a roster that restates each step's mode inevitably drifts from the steps themselves.

## Impact

One concrete instance of the recurring `doc-contract-divergence` archetype, with a runtime consequence attached (unreachable operator input) rather than a purely editorial one. The structural fix — roster cross-references the step docs instead of restating their modes — would retire the whole class for the finalize step roster.
