envelope_version=1
sender_type=plan
sender_id=a-failing-ci-call-reports-success
epic=review-apparatus
kind=candidate-lesson
created=2026-08-27T15:42:32Z

# github_re_review head_sha_verified misses a SHA embedded in a commit URL

component: plan-marshall:workflow-integration-github
category: bug
confidence: high
source_plan: a-failing-ci-call-reports-success
source_pr: 1356
finding_id: 5ec6d3

## Context

Surfaced during this plan's finalize and filed rather than fixed, so it is live in
merged main. `github_re_review`'s `head_sha_verified` check does not match a commit
SHA when that SHA is carried inside a commit URL rather than appearing bare. A
review that genuinely did address the current HEAD is then read as not having done
so.

## Root cause

The verification matches a bare-SHA shape against review text. A bot that
references the reviewed commit by URL — a normal and increasingly common form —
presents the same SHA in a shape the matcher does not recognise, so the check
fails closed against a review that was in fact current.

## Proposed action

Widen the SHA extraction to recover a SHA embedded in a commit URL as well as a
bare one, and add a matched positive/negative control: a review whose only SHA
reference is a URL must verify, and a review referencing a genuinely different SHA
must still fail. The consequence of leaving it is not cosmetic — it manufactures a
false incremental-review decline and blocks the pre-merge barrier on a PR whose
review is current, which is a merge-stopping false negative.

## Evidence

- finding 5ec6d3, filed during 6-finalize, resolution not `fixed`
- aspect: request_result_alignment — `github_ops.py` plus `test_github_ops.py` and `test_pr_landing_state.py` entered the footprint as late discovery from this investigation, undeclared by any deliverable
- aspect: log_analysis — `github_re_review` recorded 6 calls totalling 430,350 ms
