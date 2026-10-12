envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-12T13:53:21Z

# Lessons ingest: a required review bot goes stale after a fix commit and the review step loops until an operator override

Severity: **critical** for the Antigravity instance (operator ruling 2026-10-12), high otherwise (backlog § 4.4, § 4.8). Bundle: `plan-marshall` (`automatic-review`, `phase-6-finalize` branch-cleanup, `workflow-integration-github`, `plan-marshall/workflow/verification-feedback.md`).

Source: pm-mcp-core epic `pm-mcp-core-m2-m4`, six plans. Full bodies: `lessons-routing/lessons-archive/filed-live-blockers/`.

| Message | Plan | Statement |
|---|---|---|
| `pm-mcp-core-m2-m4-128` | PLAN-41 (#34), Antigravity | `re_review_on_loopback: true`, yet no `/review` followed the last fix commit (applied inline in finalize, no loop-back); merged under `barrier-ask-override`. Since PLAN-38 the re-review fired on every Claude Code plan. |
| `pm-mcp-core-m2-m4-005` | #18, #19, #20 | `cuioss-review-bot` reviews only on request; with `re_review_on_loopback=false` every fix commit leaves it `participated_stale`, loop-back twice, overnight wait, operator moves it to optional. Three plans in a row. |
| `pm-mcp-core-m2-m4-041` | PLAN-04 (#25) | With `use_merge_queue=true` there is no local rebase, so branch-cleanup trigger A never fires; #24's re-request change did not produce a re-review; operator override. |
| `pm-mcp-core-m2-m4-053` | PLAN-06 (#26) | Manifest says `re_review_on_loopback: true`; the leaf read `false` from another source and posted no trigger; merged under override. |
| `pm-mcp-core-m2-m4-034` | PLAN-38 (#24) | A `.plan/`-only diff cannot be reviewed by either required bot (path filters); automatic-review loops back with both `absent`. |
| `pm-mcp-core-m2-m4-061` | PLAN-05 (#28) | `post_responses` sent "fixed" replies before the fix commit existed; no deferral option (backlog § 4.4 "Fixed posted before the fix exists"). |

Asked for: any commit pushed after the last bot review re-arms the re-review trigger whatever path produced it (inline finalize fix, merge-queue flow); the leaf reads `re_review_on_loopback` from the manifest step params and logs value and source; a required bot whose path filter excludes the whole diff counts as expected-absent; "fixed" replies deferred until the commit is on the remote.

Owner today: PLAN-LB-24 (`review-step`, running). #1742 (`7dd1d3433`) and #1752 (`4a985a1bf`) touched this surface after most of these runs; the ingest did not establish which items they closed. `lessons-routing-003` (2026-10-09) filed the same subject — treat this as recurrence evidence plus the merge-queue, `.plan/`-only and Antigravity-inline cases.
