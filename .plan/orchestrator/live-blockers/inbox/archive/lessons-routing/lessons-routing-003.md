envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-09T14:43:47Z

# Lessons ingest: review step — stale required bot, unrunnable poll wait, "fixed" before the commit

Severity: high. Bundle: `plan-marshall` (`automatic-review`, `plan-marshall` workflow). Backlog
reference: `backlog.md` § 4.4 and § 1.5.

Three lessons were retired from the lessons corpus by the `lessons-routing` ingest of 2026-10-09 and
are handed to this epic. Their full bodies and evidence are kept at
`lessons-routing/lessons-archive/filed-live-blockers/`.

| Lesson | Statement |
|---|---|
| `2026-10-03-18-001` | After a loop-back commit moves HEAD, a required bot whose only comment predates it is `participated_stale`. Trigger B selects bots from staged findings only, and cuioss-review-bot's comment is filtered as noise, so no code path posts its re-review. The step loops and needs `--force` on `mark-step-done`. |
| `2026-10-07-07-007` | The completion poll is paced by a standalone `sleep 30`, which the harness refuses in a dispatched leaf, so the 600-second bound is unreachable. The step was marked done while CodeRabbit was still in progress; participation passed on earlier comments and the PR merged. |
| `2026-10-07-07-008` | The triage dispatch posted "Fixed in a follow-up commit" and resolved three threads while the edits were uncommitted and untested; verify passed about 25 minutes later. RESPOND runs inside the same dispatch as the inline edits, ahead of the commit. |

## What to check here

PLAN-LB-24 (`review-step`) is running and PLAN-LB-25 carries the wait procedures from PLAN-LB-05. The
ingest did not read either spec in full, so it does not know whether these two proposed actions are
in scope:

- the pre-merge barrier re-reads `bot_completion` for required bots and refuses a merge while one is
  `in_progress` for the merge-candidate SHA (`2026-10-07-07-007`);
- a `fixed` disposition is transmitted only with the commit SHA it refers to, after the verify build
  is green (`2026-10-07-07-008`).

Fold what is absent into the plan that owns the surface, or record it as covered.
