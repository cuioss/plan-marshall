envelope_version=1
sender_type=plan
sender_id=pr-065-settings-repo-accumulates-never-lands
epic=review-apparatus
kind=candidate-lesson
created=2026-09-14T19:21:47Z

component=plan-marshall:manage-change-ledger
category=anti-pattern
source_signal=script_failure_cluster
source_plan=pr-065-settings-repo-accumulates-never-lands
evidence=work-log ERROR 366ded (2026-09-14T06:07:18Z)

# manage-change-ledger called with an unregistered verb

`plan-marshall:manage-change-ledger:manage-change-ledger` rejected a call with
`exit_code=2 failure_kind=argparse_rejection`; the executor answered with the
registered set: `['append', 'classify-outcome', 'query', 'worktree-sha']`.

The change-ledger surface is small and verb-named in a way that invites
paraphrase (`record`, `read`, `verify`, `check-freshness` all read as plausible
synonyms of the four real verbs). The call was composed in the middle of an
execute-phase freshness check, where the surrounding prose talks about
"verifying the worktree state" rather than about `query` / `worktree-sha`.

## Candidate rule

Same class as the manage-solution-outline cluster in this run: the workflow
sentence describes an intent whose nearest verb is not the declared verb. Four
verbs is a set small enough to inline at every call site that references the
ledger, which removes the paraphrase surface entirely.
