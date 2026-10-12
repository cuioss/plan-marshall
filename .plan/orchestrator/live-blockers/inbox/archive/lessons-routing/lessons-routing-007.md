envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-09T15:43:51Z

# Review step and review gate: five defects from consumer-repo and PLAN-LB-29 runs

- **Severity:** high (`backlog.md` § 4.4, the review-gate cluster)
- **Bundle:** `plan-marshall` (`workflow-integration-github`, `phase-6-finalize`, `automatic-review`)
- **Source lessons:** `2026-10-04-09-001`, `2026-10-05-14-006`, `2026-10-05-14-007`, `2026-10-05-17-001`, `2026-10-09-15-007`
- **Full bodies:** `lessons-routing/lessons-archive/filed-live-blockers/`
- **Filed by:** the `ingest` run of `lessons-routing`, 2026-10-09 (second run). All five lessons are retired from the corpus.

## What the lessons say

1. `2026-10-05-17-001` — `github_re_review re-review --bot-kind cuioss-review-bot` returned
   `matched: true` on a CodeRabbit review. A re-review awaited for one bot is satisfied by another
   bot's review, so the participation barrier reads a wrong bot as fresh (cui-http PR #262).
2. `2026-10-05-14-006` — a bot that edits its summary comment in place gets a second pending
   finding on every pre-merge re-fetch (identity includes `edit_term`), even when the verdict is
   unchanged and the first copy was resolved. The duplicate blocks the merge until hand-resolved
   (cui-http PR #260).
3. `2026-10-05-14-007` — the `CodeRabbit` commit status is in the `ci_complete_precondition` check
   set, so a slow or rate-limited bot times out the CI precondition and is reported as a CI problem.
4. `2026-10-09-15-007` — `@coderabbitai full review` is not excluded as an own trigger (exact match
   on `@coderabbitai review` only), and the bot's replies to it are stored as findings.
5. `2026-10-04-09-001` — nothing compares the planned footprint with a required bot's size cap
   before `create-pr`; a 151-file PR was refused after push and CI and split by hand, and the
   by-file-group split cost two extra fix commits.

## Checked at this run

- Item 4: the string `coderabbitai full review` appears in no inventoried file at `4ed67e228`, so
  the command form is still unregistered.
- Items 1, 2, 3 and 5 were not re-checked in code.

## Owner today

PLAN-LB-24 (running) owns the review step. Read against its objective and first four deliverables
only: item 4 overlaps its acknowledgment deliverable, and your ledger already lists it to check at
that landing. Items 1, 2, 3 and 5 were not found there; item 3 is the "slow bot is filed as a CI
timeout" line of § 4.4, item 5 its "size limits discovered after the PR exists" line.

## Asked of live-blockers

At PLAN-LB-24's landing, check each of the five for a residual, and decide whether items 1, 2, 3
and 5 go to PLAN-LB-25 (phase and merge gates), a follow-up, or the backlog.
