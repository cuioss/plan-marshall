envelope_version=1
sender_type=plan
sender_id=lb-28-java-consumer-repos
epic=live-blockers
kind=candidate-lesson
created=2026-10-10T23:22:51Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=improvement
bundle=pm-plugin-development

# Self-review round owed a further pass for a JSON-vs-TOON projection drift no test caught

## Source

Plan lb-28-java-consumer-repos, 6-finalize Q-Gate finding b9952f (rule `pre-submission-self-review-state`, title `further_round_owed at pre-submission-self-review`, resolution taken_into_account). This is the round-state record that accompanies the substantive finding e6931a, filed as a separate candidate-lesson message from the same plan (lb-28-java-consumer-repos-001). The orchestrator-side pickup may reasonably merge the two.

## What happened

The first full-scope pre-submission self-review round returned a non-empty blocking set: `format_toon` (`_build_format.py:205-216`) dropped the `by_runner` / `population` fields that `to_dict` adds, and the failing-path `tests` block lacked the `unmeasured` marker. Because the blocking set stayed non-empty the round answered `may_close=no` and a further round was owed. The fix landed at commit 18c6495e5; the next round surfaced no drift and the verifier accepted `may_close=yes`.

## Observation

The self-review loop worked as designed — it was the only control that caught the drift before merge, and the loop-back cost one extra round. The cost was avoidable: the drift is mechanically detectable (a key emitted by one output format and absent from the other, in a component whose documentation promises format parity). A deterministic candidate surfacer in `ext-self-review-plan-marshall` for "result-dict key present in JSON projection but absent from TOON projection" — or, cheaper, a parity test in the build module itself — would move this defect class from a loop-back round to a first-round candidate or a build failure.

## Corrective rule

When a self-review loop-back is driven by a contract_drift between two serializations of the same result object, record a structural guard (parity test or deterministic surfacer) as part of the fix, so the same class does not need another review round to find it next time.
