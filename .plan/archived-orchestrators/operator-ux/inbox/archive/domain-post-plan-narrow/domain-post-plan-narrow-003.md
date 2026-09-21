envelope_version=1
sender_type=plan
sender_id=domain-post-plan-narrow
epic=operator-ux
kind=candidate-lesson
created=2026-09-06T07:28:06Z

# Candidate lesson (recurrence): `github_pr.py` rejected `--plan-id`, a third site of the undeclared/misplaced-`--plan-id` argparse class

**Source**: plan `domain-post-plan-narrow` (PLAN-03, epic `operator-ux`)
**Signal source**: script-failure cluster (`[ERROR] (plan-marshall:execute-script:2) script_failure`)
**Suggested component**: `plan-marshall:workflow-integration-github`
**Suggested category**: `bug`
**Dedup read**: RECURRENCE on the existing argparse-rejection cluster, not a new class.

## Observation

Work log, `2026-09-05T23:24:31Z`, ERROR `5b8d81`:

```text
script_failure notation=plan-marshall:workflow-integration-github:github_pr exit_code=2
failure_kind=argparse_rejection
detail=usage: github_pr.py [-h]
       {fetch-comments,fetch_findings,post_responses,pull_request_runs,bot_completion} ...
       github_pr.py: error: unrecognized arguments: --plan-id domain-post-plan-narrow
```

`github_pr.py` declares **no** `--plan-id` at any level — neither router-scoped nor verb-scoped — so this is neither of the two flag-position signatures the standard already names. It is the third variant: *the flag does not exist on this surface at all*, and the rejection message ("unrecognized arguments") is the same message the misplaced-position case produces, so a caller reading it cannot tell which of the three it hit.

## Nearest active lessons

- `2026-09-03-19-003` — *`ci pr prepare-body` must reject a router-position `--plan-id` by name instead of reporting it missing*.
- `2026-09-03-19-004` — *Name the rejected flag and the sibling verb's canonical form in argparse-rejection messages*.
- `2026-09-04-17-008` — *Publish each script's declared accept-set so an argparse rejection is preventable, not just diagnosable*.

All three are the same cluster; a `## Recurrence` note naming `github_pr` as a new site is preferable to a fourth lesson. The one thing the recurrence note should add: the existing three are written around a flag that *exists in the wrong position*, and this site is a flag that *exists nowhere on the surface* — the caller-side remedy (`2026-09-04-17-008`'s published accept-set) covers both, but `2026-09-03-19-004`'s message-wording remedy does not, because there is no sibling verb's canonical form to name.

## Candidate corrective

Publishing the declared accept-set per script (`2026-09-04-17-008`) is the corrective that covers this site. This recurrence raises that lesson's evidence, not a new rule.
