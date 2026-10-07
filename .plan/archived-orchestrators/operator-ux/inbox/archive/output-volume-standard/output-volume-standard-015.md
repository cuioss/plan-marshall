envelope_version=1
sender_type=plan
sender_id=output-volume-standard
epic=operator-ux
kind=candidate-lesson
created=2026-09-03T16:09:01Z

component=plan-marshall:automatic-review
category=bug

# Script-failure record: review_completeness rejected the empty --measured-diff-size its own doc prescribes

## Observation

`plan-marshall:automatic-review:review_completeness check` exited 2 with `failure_kind=argparse_rejection` during `default:branch-cleanup`:

```
usage: review_completeness.py check [-h] --plan-id PLAN_ID
                                     [--required-bots [REQUIRED_BOTS]]
                                     [--optional-bots [OPTIONAL_BOTS]]
                                     [--participated-bots [PARTICIPATED_BOTS]]
                                     ...
```

The caller supplied `--measured-diff-size ""` because `fetch_findings` returned an empty `measured_diff_size` and the prescribing document documents the empty string as the fallback. The bracketed `[FLAG [FLAG]]` usage lines above show which flags carry the `nargs='?'` defence — `--measured-diff-size` is not among them, so the executor's empty-argument strip left argparse with a flag and no value.

## Cross-reference — same defect, doc side

This is the SCRIPT-FAILURE record of the same defect already filed as a Q-Gate finding on the documentation side (`2b85dc`, phase `6-finalize`, component `plan-marshall:phase-6-finalize`, resolved `taken_into_account`). They are transmitted separately because they are two distinct records behind two distinct signal sources; the orchestrator should merge them into one lesson rather than file two.

The remedy stated there applies here and is the script-side half of it: give `--measured-diff-size` `nargs='?'` with `const=''` so its declared surface matches the empty value its callers are documented to pass, OR have the caller omit the flag entirely.

## Recommended rule (script-side)

When a flag's documented value domain includes the empty string, its argparse declaration must accept the empty string. The generated executor strips empty-string arguments before argparse sees them, so on this platform "accepts empty" specifically means `nargs='?'` with an explicit `const`. A scalar flag sitting beside sibling list flags that DO carry the defence is the exact shape that goes unnoticed, because the usage line reads as uniform.

## Evidence

- Plan: `output-volume-standard` (epic `operator-ux`)
- Work log 2026-09-03T10:23:04Z, during `default:branch-cleanup`
- Worked around in-run by omitting the flag; `review_completeness check` then returned `participation_complete: true`
- One of 4 distinct failing script notations on this run
