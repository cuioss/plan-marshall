envelope_version=1
sender_type=plan
sender_id=lb-49-opencode-measurement
epic=live-blockers
kind=landing
created=2026-10-22T11:29:58Z

# lb-49-opencode-measurement landed: OpenCode session-database token and sub-agent measurement

``` landing-facts
schema=landing-facts/1
plan_id=lb-49-opencode-measurement
pr=1833
merge_state=merged
cleanup_owed=false
deliverables_total=4
deliverables_done=4
total_tokens=16614516
harness=opencode
model=deepseek-v4.1-flash
effort=level-5
plugin_version=0.1.1983
steps=finalize-step-sync-baseline:executed,project:finalize-step-lessons-housekeeping:executed,project:finalize-step-plugin-doctor:executed,functional-review:executed,code-review:executed,architecture-refresh:executed,pre-push-quality-gate:executed,push:executed,create-pr:executed,ci-verify:executed,automatic-review:executed,branch-cleanup:executed,project:finalize-step-deploy-target:executed,project:finalize-step-sync-plugin-cache:executed,project:finalize-step-review-retrospective:executed,finalize-step-preference-emitter:executed,plan-marshall:plan-retrospective:executed,record-metrics:executed,finalize-step-print-phase-breakdown:executed,emit-landing:executed,archive-plan:executed
```

Measured OpenCode usage from the session database: main-session and descendant sub-agent tokens are summed per phase window, and every unavailable source returns a named reason instead of a zero.
