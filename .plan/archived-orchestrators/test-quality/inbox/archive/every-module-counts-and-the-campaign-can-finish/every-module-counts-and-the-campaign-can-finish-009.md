envelope_version=1
sender_type=plan
sender_id=every-module-counts-and-the-campaign-can-finish
epic=test-quality
kind=candidate-lesson
created=2026-09-04T16:32:19Z

component=plan-marshall:persona-module-tester
category=bug
confidence=high
source_plan=every-module-counts-and-the-campaign-can-finish

# The suite was never order-independent and nothing measured it, including a test that deleted the live session's basetemp

## Context

TASK-010's criteria required the tree green in default AND reverse directory order (`PM_TEST_ORDER=reverse`). Default order was green. Reverse order was red — and provenance was established rather than assumed: a baseline reverse run on the MAIN checkout, with none of the branch present, was ALSO red, with a different pair of failures. Two branch reverse runs disagreed with each other (3 failures, then zero failures but a lost xdist worker and 23231 of 23993 tests).

Order-independence was therefore not a property this repository had. It had simply never been asked for, so nothing had ever measured it.

Held to the line by the operator rather than deferred, TASK-013 fixed it at the cause and found four defects, not the three visible from the failures:

1. `sys.path` accumulation across modules
2. `ci_base._DEFAULT_CWD` leaking between tests
3. `platform_runtime` module identity vs dotted-string patching
4. `cmd_coverage`'s unstubbed `_prune_basetemp_roots` calling `rmtree` on the RUNNING session's own pytest basetemp when the module happened to run late — which is what reverse order turned into roughly 1500 setup errors

## Root cause

Defect 4 is the one worth carrying: a test exercising a cleanup command executed the real cleanup against the live test session's own scratch tree. It was invisible in default order purely because the module ran early enough that the damage landed after everything that needed the directory. Ordering was not the bug; ordering was the only thing hiding it.

Defects 1-3 are the ordinary shared-mutable-state family (import side effects, module-level cached defaults, module identity under patching), and they were latent on `main` too.

## Proposed action

1. Add reverse-order to the gate so the property, now that it holds, cannot silently regress. It was established twice on the committed tree (24099 tests each, no lost worker, no short count) — the cost of keeping it is a second run, the cost of losing it is another campaign.
2. Treat "a test invokes a command whose real side effect is deletion under the temp root" as a reviewable pattern in its own right. Fixes 1 and 2 landed as autouse fixtures in `test/conftest.py` so they are inherited rather than applied per victim; fix 4 landed in the single shared capture helper. That inheritance shape is the reusable part.
3. Nothing was skipped, xfailed, reordered or serialized to reach green — worth recording as the standard the fix met.

## Evidence

- qgate finding 93eff1 (5-execute, `plan-marshall:persona-module-tester`, warning), resolution `fixed`
- Baseline reverse run on `origin/main` red with a DIFFERENT failing pair — the defect predates the branch
- Commit 72bd40ae0; two inherited reds found and fixed separately (660a5aaa1 stale roster pin, c23f8580b rebase import order)
- Default-order verify green over compile/lint/test; coverage green
