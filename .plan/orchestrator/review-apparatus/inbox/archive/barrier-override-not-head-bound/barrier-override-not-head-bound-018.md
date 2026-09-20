envelope_version=1
sender_type=plan
sender_id=barrier-override-not-head-bound
epic=review-apparatus
kind=finding
created=2026-08-02T13:22:50Z

# An edit-in-place review bot's `reviewed_commit_sha` never advances, because dedup fires before the re-stamp

**Observed** (PR #1077, this plan's own finalize, 2026-08-02):

`automatic-review` re-entered at a new HEAD after a rebase + force-push
(`ae6c5615…` → `a2855290…`). Trigger B fired correctly, posted `/review`, and
pr-agent genuinely re-reviewed — its own comment body now reads
`(Review updated until commit …/a28552904929731157a175fa5df84f2e166e8d1f)`.

But the stored finding's `reviewed_commit_sha` still reads `ae6c5615…`.

**Mechanism.** pr-agent edits ONE persistent comment in place, so its
`comment_id` is unchanged across re-reviews. `fetch_findings` dedups on
`comment_id` and skipped it (`count_skipped_duplicate: 1`) — and the dedup fires
BEFORE the re-stamp the `automatic-review` SKILL describes ("re-runs
`fetch_findings` … this re-stamps every finding's `reviewed_commit_sha` to the
new HEAD"). For an edit-in-place bot, that documented re-stamp never happens.

**Why it matters to this epic.** Trigger B's own staleness check reads
`reviewed_commit_sha`. After a second HEAD advance it would compare the new HEAD
against a SHA that is now two generations stale — so the field that decides
"has this bot seen this tree" silently stops tracking the tree. That is the same
shape as PLAN-PR-015's subject (an approval bound to a HEAD it no longer
covers), one layer down: here the binding field exists but stops advancing.

⚠ **Adjacent but distinct from #1071** (re-review detection via timestamp for
edit-in-place bots). #1071 fixed *detecting* that a re-review happened; this is
about the *persisted binding* not being updated once it has. Check whether
#1071's timestamp path already supersedes the SHA read before staging work.

**Confirm/refute artifact**: the `pr-comment` findings store for
`barrier-override-not-head-bound` (archived at
`.plan/local/archived-plans/2026-08-02-barrier-override-not-head-bound/`),
finding `9ec99f`, field `reviewed_commit_sha`.
