envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-09-04T08:09:54Z

# Carried-out finding 1d5140 — ci_verify run reports persisted=false / persist_skipped_reason=head_sha while it DID persist head_at_completion

**Origin** `review-apparatus` / PLAN-PR-038 (`review-packs-become-published-artifacts`), PR #1388, merged `ef974632c`.
**Rescued from a dead store.** The plan directory was archived before these findings had a carry-out route; the orchestrator recovered them by reading `.plan/local/archived-plans/2026-09-03-review-packs-become-published-artifacts/artifacts/findings/` directly. ⭐ The data survives archival — only the *route* was missing.

| Field | Value |
|---|---|
| `hash_id` | `1d5140` |
| type / severity | `bug` / `warning` |
| resolution at archive | `pending` (never promoted) |
| component | `plan-marshall:phase-6-finalize` |
| file | `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/ci_verify.py` |

**Routing rationale.** Not a PR/review-apparatus finding — it is an instrument-truthfulness defect, so it routes here under the three-way rule (PR/review → `review-apparatus`; everything else not-ours → `truthful-signals`).

## Title

ci_verify run reports persisted=false / persist_skipped_reason=head_sha while it DID persist head_at_completion

## Detail (verbatim from the archived store)

Observed live at PR #1388, head 0a6fa35f7. The green pass-through of ci_verify run returned: outcome=green, run_id=33805898878, head_sha='' (empty), persisted=false, persist_skipped_reason=head_sha, findings_filed=0, step_marked_done=true. Read literally, that payload says the step was marked done WITHOUT a head_at_completion anchor - which for a head_dependent step (ci-verify declares head_dependent: true) is the documented absent-SHA case that makes the dispatcher re-fire on re-entry and report the prior verdict UNVERIFIED. Acting on that reading, the orchestrator re-stamped the anchor via mark-step-done --head-at-completion. The re-stamp's own return then showed previous_head_at_completion: 0a6fa35f7a2537e6e707cd9326ffb8b4839d513a - i.e. the anchor was ALREADY correctly persisted and the payload's persisted=false / persist_skipped_reason=head_sha / head_sha='' were all wrong about what the script had just done. IMPACT: the payload is the only account a consumer has of whether the anchor landed. A consumer that trusts persisted=false does redundant work (the benign case, observed here); a consumer that trusts a persisted=true when the write did NOT land would leave a head_dependent step anchored to nothing and never notice. The empty head_sha field compounds it: the run_id is populated from the same CI read, so the head was available. REMEDY: report persisted/persist_skipped_reason from the actual write result rather than from a pre-write branch, and populate head_sha from the same source the anchor is written from - or, if the anchor is written by a path that does not return through this payload, say so rather than reporting a skip.
