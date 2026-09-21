envelope_version=1
sender_type=plan
sender_id=pr-065-settings-repo-accumulates-never-lands
epic=review-apparatus
kind=candidate-lesson
created=2026-09-14T19:22:15Z

component=plan-marshall:phase-6-finalize
category=anti-pattern
source_signal=script_failure_cluster
source_plan=pr-065-settings-repo-accumulates-never-lands
evidence=work-log ERROR 968530 (2026-09-14T18:03:57Z)

# `ci_verify` called with a paraphrased verb against a one-verb script

`plan-marshall:phase-6-finalize:ci_verify` was rejected with
`Use a registered verb for ...: ['run']`.

The script declares exactly ONE verb. A single-verb script is the strongest
possible case of the verb-paraphrase signature: there is no discrimination to
make, only a word to quote, and the word was not quoted. The call was composed
during the `ci-verify` finalize step, where the step name, the workflow prose and
the script notation all read as "ci verify" and none of them contains `run`.

## Candidate rule

For a script whose whole surface is one verb, the notation and the verb should be
inlined together at every call site (`... :ci_verify run ...`). Where a step name
and its script's verb differ, the step's own doc is the place the mismatch has to
be visible — an agent reading "Executing step: default:ci-verify" has no signal
at all that the verb is `run`.
