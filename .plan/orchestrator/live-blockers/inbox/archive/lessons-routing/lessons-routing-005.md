envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-09T15:43:44Z

# Head-dependent finalize steps re-fire in full, and the self-review self-seeds on doc-claim plans

- **Severity:** high (`backlog.md` § 1.2)
- **Bundle:** `plan-marshall` (`phase-6-finalize`)
- **Source lessons:** `2026-10-08-21-003`, `2026-10-05-17-003`
- **Full bodies:** `lessons-routing/lessons-archive/filed-live-blockers/`
- **Filed by:** the `ingest` run of `lessons-routing`, 2026-10-09 (second run). Both lessons are retired from the corpus.

## What the lessons say

1. `2026-10-08-21-003` — no finalize step declares `verdict_inputs`, so every fix commit re-runs
   lessons-housekeeping, plugin-doctor, the self-review, automatic-review, the pre-push gate and
   ci-verify in full. On PLAN-LB-22 a three-file fix commit re-ran all of them; housekeeping
   re-classified 58 lessons seven times with an identical result.
2. `2026-10-05-17-003` — on a documentation-claims plan (cui-http PLAN-13, PR #262) the self-review
   ran about seven rounds; each reworded claim produced new findings, and the loop-back ceiling was
   exceeded twice by operator authorization. Proposed: prefer narrowing over rewording, and report
   the self-seeding pattern to the operator early.

## Owner today

- Item 1 is the subject of PLAN-LB-32 (staged, high priority); your Watch "Head-dependent finalize
  steps re-fire in full" already cites this lesson by id. Nothing new is asked beyond noting that
  the lesson no longer exists in the corpus — its body is at the path above.
- Item 2 predates #1726 (`d8b0284ef`), which grades findings by severity. It is a third baseline
  for your Watch "Does the regraded self-review converge?", from a consumer repository.

## Asked of live-blockers

Check for a residual only: whether PLAN-LB-32 covers the pre-push gate and ci-verify re-fires the
lesson names beside the two project steps, and whether the doc-claim self-seeding case needs
anything #1726 did not ship. Not re-checked in code at this run.
