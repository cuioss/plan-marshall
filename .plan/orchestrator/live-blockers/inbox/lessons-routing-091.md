envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-15T21:16:41Z

# HIGH, recurrence evidence only: six subjects `live-blockers` already owns are still live in API-Sheriff, with new members

Filed by the `lessons-routing` drain of 2026-11-15 (second grading of messages the Linux session's 38-message drain of the same day also read; that drain graded the same items medium or covered). Source messages: `api-sheriff-api-sheriff-0-2-0-081`, `-082`, `-084` and `-085`. All six subjects were filed high earlier; this message asks for no new work, only that each owner carries a current data point. Bundle: `plan-marshall`.

| # | Subject (earlier filing) | New evidence | Source |
|---|---|---|---|
| 1 | The merge gate ignores an operator re-fire waiver for head-dependent review steps (`lessons-routing-060`, archived in `live-blockers`) | Two more plans: PLAN-V02-53 offered `loop-back close --waive-refire` and the gate (`merge_candidate_not_gated`) refused anyway, so all three reviews re-ran; PLAN-V02-56 waived simplify, security-audit and code-review at head 2a6d1a1c, the gate refused, the merge mutex had to be released, and the three steps were re-run over the one commit before the merge succeeded. Suggested: warn up front that the gate still needs a narrow re-run at the final head, or run it as part of the waiver | -081 item 3, -082 item 1 |
| 2 | `automatic-review` force-marked `done` before the required bot's review exists (`as-074`) | PLAN-V02-54 (api-sheriff-0-2-0, #553): same shape, so the class is live after the first report | -084 recurrence |
| 3 | `module-tests` DEGRADED at whole-tree scope in a Maven reactor (`-031`, `-058`; the zero-bundle half is fixed by #1866) | PLAN-V02-52 (#554, 2026-11-01) ran DEGRADED at whole-tree scope after #1866; unrouted recurrences on PLAN-V02-14, -19, -21, -26 | -085 recurrence B |
| 4 | No CI verb reads a `main` run by merge commit (truthful-signals `api-sheriff-deployment-configurability-013`, folded into PLAN-TRUTH-150, carried in `live-blockers` `backlog.md` section 2.7) | Still open at plan-marshall HEAD: `ci checks status` takes only `--pr-number` / `--head`. api-sheriff-0-2-0 owed the post-merge `deploy-snapshot` check on every landing and could not read it through the abstraction | -085 recurrence A |
| 5 | Script-surface drift: documented verbs or flags the scripts do not declare (`lessons-routing-044`) | New members: `manage-solution-outline --number` (the invented-flag class, `-044`), and `review_completeness --participated-bots coderabbit` rejected as `malformed_bot_flag` because only that flag takes `bot_kind:evidence_kind` pairs (doc-drift, the call site does not show the asymmetry). NOT a member: the sender's `review_completeness roster` and `manage-logging signal-scan` items are refuted at HEAD, where both verbs are registered (`review_completeness.py:2172`, `:2796`; `manage-logging.py:293`, `:315`, as checked by the Linux session's drain of the same day); the sender ran an older executor | -081 item 1, -082 item 4 |
| 6 | A CI wait after a push is not bound to the pushed head (`pm-mcp-core-m2-m4-235`, `-253`) | PLAN-V02-53: a background `pr checks --watch` started right after a push exited at once on the previous head's checks and reported "done" | -081 item 5 |

## Evidence

The senders' observations; nothing here was re-run on the plan-marshall side. Rows 1 and 5 were matched to earlier filings by id from `lessons-archive/INDEX.md`; rows 2, 3, 4 and 6 name the earlier subject as the sender did.
