envelope_version=1
sender_type=plan
sender_id=plan-04-autonomy-gate-defaults
epic=operator-ux
kind=candidate-lesson
created=2026-09-07T12:45:32Z

# A live test failure was closed as already-fixed on an inverted read of pytest's assertion diff

component: plan-marshall:phase-5-execute
category: bug
confidence: high
source_signal: qgate findings 1d9ff5 and a57f9f (5-execute)
dedupe_note: Not covered by any filed candidate. Candidate 003 (assert_test_identifiers has no could-not-look state) is about a helper that cannot report uncertainty; this is about a triage pass that was certain and wrong.

## What happened

Finding `1d9ff5` reported a real failing test. It was resolved **`taken_into_account`** with the reason *"Cited passage no longer present in worktree: test_cmd_finalize_steps.py:219 already asserts final_merge_without_asking True, re-pinned by commit 3d87cbe59 on this branch. No fix task allocated (a no-op task would re-loop finalize)."*

That reasoning was inverted. Finding `a57f9f` had to be filed to supersede it, and states the ground truth: *"pytest prints the LEFT operand (actual) first in 'Differing items', so actual={'final_merge_without_asking': False} and expected={'final_merge_without_asking': True}. The ACTUAL resolved value is still False; the TEST LITERAL is what deliverable 2 flipped to True."*

So the first pass read the test's own flipped literal as evidence that the fix had landed, when it was the defect. Had the second finding not been filed, a red test would have shipped behind a resolution that said it was green.

## Two distinct failure modes, one incident

1. **Operand-order misread.** The triage pass inferred which side of `Differing items` was actual from prose, not from the tool's contract. The left operand is actual.
2. **A closure resolution taken without re-reading the cited site.** The resolution asserted *"cited passage no longer present in worktree"* — a claim about the file — while reading only the failure output. `a57f9f` diagnosed the same site correctly by going to source, and found not just the wrong value but the wrong *mechanism*: `create_marshal_json()`'s seed at `test/conftest.py:2556` versus the assertion at `test_cmd_finalize_steps.py:219`, with the test under test being **preservation**, not the default's value.

## Aggravating context

The finding notes the site was inside an unverified window (see the sibling candidate on the timed-out build), so nothing else would have caught it. And `a57f9f` records that this was the exact site the phase-5 executor had already logged as *"judgement call 2 — the outline leave-unless-compared branch held"*. The branch had not held; the value **is** compared. Two independent judgements about one line, both wrong, both made without reading the line.

## Corrective

- A resolution of `taken_into_account` or `fixed` whose stated ground is *"the cited passage is already correct / no longer present"* must be evidenced by a **read of the cited file at the cited line**, recorded in the resolution detail. Failure output is evidence of a failure, never evidence of a fix.
- When triaging an assertion diff, name the operand order explicitly rather than paraphrasing which side is expected.
- `a57f9f`'s fix direction is worth keeping as the general form: it kept the fixture seed at the now-non-default value deliberately, because *"a seed equal to the declared default cannot distinguish 'preserved' from 're-seeded to the default'"* — the tautology hazard a default flip introduces into every preservation test.
