envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-22-01
epic=review-apparatus
kind=candidate-lesson
created=2026-09-22T07:15:20Z

# Candidate lessons routed from lessons-handling-26-09-22-01

5 lessons matched to this epic's scope (automated PR review reliability, `automatic-review`,
review-retrospective, the participation taxonomy/classifier). All `active` in the source corpus.

## automatic-review shared-component cluster (4 lessons)
- **2026-09-20-00-001** (primary): producer FIND (`github_pr fetch_findings`) stores a CodeRabbit
  control-flow acknowledgement ("Already reviewed the last commit...") as a first-class pending
  pr-comment finding — a meta comment about the review LIFECYCLE, not about the code.
- **2026-09-19-21-001**: a required `cuioss-review-bot` can never verify on a first clean review (no
  commit permalink to anchor the verification against).
- **2026-09-19-21-002**: Trigger B's stale-bot selector cannot reach a required bot that has never
  published a finding.
- **2026-09-20-08-002**: no persisted reviewed-at-all handoff reaches order:990 (review-retrospective),
  forcing `unmeasurable` for every silent reviewer.

## review-retrospective undercount (standalone)
- **2026-09-20-08-001**: review-retrospective's kind-based CodeRabbit actionable-count metric
  under-reports whenever a review's overflow findings get nested as prose inside the meta status body
  ("Outside diff range comments (N)") instead of posted as separate inline comments with their own
  `hash_id` — GitHub's inline-comment posting cap causes this on any PR that exceeds it. Observed on
  PLAN-TRUTH-143/PR#1539: measured `actionable_count: 7`, true yield `9`.

## Disposition
All 5 are `standalone`/`clustered-into`, none `already-covered`. Source files removed from
`.plan/local/lessons-learned/` after this message is confirmed queued.
