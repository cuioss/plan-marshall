envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:01:45Z

# Candidate lesson: a test helper's glob was narrower than the coverage its own docstring claimed

- source_signal: qgate / 6-finalize
- record_id: d49a51
- component: pm-plugin-development:ext-self-review-plan-marshall
- file: test/plan-marshall/extension-api/test_extension_discovery_behavior.py:720
- resolution: fixed in commit 75ad8fac — glob widened to `marketplace/**/*.py`

## What happened

`_code_read_keys` documented that it scans "marketplace/ or test/", but actually walked `marketplace/**/scripts/*.py` — excluding `marketplace/targets/**` and every non-`scripts/` subdirectory under `marketplace/bundles/**`. The guard reported clean over a population smaller than the one it claimed.

## Candidate rule

A scanning helper's docstring is a coverage claim. When the claim and the glob disagree, the guard is a silent under-scan: it can only ever return findings from the narrow set while every reader believes the wide set was checked. Assert the scanned population size, or derive the glob from the documented claim.
