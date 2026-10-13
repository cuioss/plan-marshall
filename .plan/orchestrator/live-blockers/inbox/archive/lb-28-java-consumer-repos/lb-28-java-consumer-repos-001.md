envelope_version=1
sender_type=plan
sender_id=lb-28-java-consumer-repos
epic=live-blockers
kind=candidate-lesson
created=2026-10-10T23:22:37Z

component=plan-marshall:script-shared
category=bug
bundle=plan-marshall

# New build-result fields added to to_dict but not projected by format_toon

## Source

Plan lb-28-java-consumer-repos, 6-finalize Q-Gate finding e6931a (pre-submission self-review, defect class contract_drift, severity warning, resolution fixed by commit 18c6495e5 after one loop-back round).

## What happened

The plan added two new fields to the Maven build result, `by_runner` and `population` (the latter carrying an `unmeasured` marker for runs whose test counts cannot be attributed). They were added to the result's `to_dict` (JSON) representation only. `format_toon` in `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_format.py` projects the `tests` section to a fixed key list (`passed` / `failed` / `skipped` / `duration_seconds`), so both new fields were silently dropped from the DEFAULT TOON output of `run`, `parse`, and the timeout/killed evidence path.

That contradicted two documents at once: `build-maven/standards/maven-impl.md:110-112`, which described the new fields, and `build-execution.md`'s statement that "Both formats return the same fields".

## Why it matters

The failure is an absence that reads as a fact. An agent running the default-format `maven run verify -pl core -am` sees no `by_runner` and reads the absence as a parallel/unmeasured build; a failing `-q` run's TOON `tests` block shows summed, ambiguous counts with no `population: unmeasured` marker, which is read as a measured result.

## Corrective rule

When a field is added to a build-result dataclass or its `to_dict`, treat `format_toon` as a second, independent projection that must be updated in the same change: project the field in the relevant TOON section, document it in `build-execution.md`'s result structure, and add a test that asserts the field on the TOON path (not only on the JSON path). A test suite that exercises only `--format json` cannot catch this drift because the JSON path is the one that was changed.

## Detection

The pre-submission self-review (`pm-plugin-development:ext-self-review-plan-marshall`) caught it as contract_drift before the PR merged; no reviewer or test did. Candidate structural guard: a parity test that asserts every key `to_dict` emits for the `tests` section also appears in the `format_toon` output, so a JSON-only addition fails at build time.
