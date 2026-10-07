envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:01:50Z

# Candidate lesson: a docstring contradicted the guard added in the same hunk

- source_signal: qgate / 6-finalize
- record_id: dfc3ee
- component: pm-plugin-development:ext-self-review-plan-marshall
- file: test/plan-marshall/phase-6-finalize/test_loop_back_outcome.py:487
- resolution: fixed (evidenced by landed change c5ed864ce)

## What happened

The docstring said a duplicate row recording done/failed "fails on its own row", while the conflicting-outcomes guard added in the SAME hunk intercepts that exact case first and says the opposite — "reported here rather than as a routing failure on one arbitrary row". The docstring clause was accurate only when both duplicate rows record the same outcome; when they differ (the case it names) the conflict guard fires and a debugger looks at the wrong assertion.

## Candidate rule

When a hunk adds an interceptor ahead of an existing failure path, the surrounding docstring describes the pre-interceptor behaviour and becomes wrong in exactly the scenario it names. Re-read the docstring against the new control flow within the same hunk — the contradiction is always local and always cheap to catch at authoring time.
