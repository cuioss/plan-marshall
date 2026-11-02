envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=finding
created=2026-10-30T05:35:57Z

# Recurrence: branch-cleanup's post-merge CI wait blocks on the PR-attached post-merge run until it exceeds its per-call bound (plan-marshall:phase-6-finalize default:branch-cleanup)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-51-lane-conditional-guards (PR cuioss/API-Sheriff#538), inbox message plan-v02-51-lane-conditional-guards-003.

Recurrence of lessons-routing message api-sheriff-api-sheriff-0-2-0-032 (post-merge `ci checks wait --adaptive` ran into its deadline only because the post-merge Performance Benchmark was still running). Same root, now seen from the branch-cleanup step.

- The merge queue merged #538 as 7755b948. In this repository `.github/workflows/benchmark.yml` is `pull_request: closed` gated on `merged == true`, so the post-merge benchmark run stays attached to the PR. The branch-cleanup wait picked that run up and blocked past its per-call bound.
- It then logged (WARNING, 2026-10-30T00:29:55Z): "post-merge CI wait skipped after it exceeded the call bound on the PR-attached post-merge run; the PR is already merged and post-merge verification belongs to the orchestrator — continuing with branch cleanup". Cost: about 7 minutes of a finalize envelope on a wait that cannot change any plan outcome. The orchestrator then read the run: it completed `success` (40979220423).
- The project contract (Git Workflow step 8) already says the plan reports the merge and stops, and that post-merge verification belongs to the orchestrator. The step reaches the right outcome only by timing out.

Suggested direction (the plan's): once the merge is corroborated, the post-merge tail should not wait on CI runs at all, including PR-attached runs triggered by the PR's own close or merge event. Record the merge and continue to the ref prune.

Evidence: work log 00e208 (WARNING), decision log 69fa5a (queue-landing gate, merged after 1363 s) and dc46d9 (post-merge cleanup dispatched 00:30:25) in plan-v02-51-lane-conditional-guards.
