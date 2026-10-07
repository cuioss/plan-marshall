envelope_version=1
sender_type=plan
sender_id=disjointness-gate-reads-declared-surface-wrong
epic=truthful-signals
kind=landing
created=2026-08-30T10:51:24Z

## What landed

disjointness-gate-reads-declared-surface-wrong shipped as #1366 (merged).

```landing-facts
schema=landing-facts/1
plan_id=disjointness-gate-reads-declared-surface-wrong
epic=truthful-signals
pr=#1366
merge_state=merged
deliverables_total=5
deliverables_done=5
total_tokens=6111067
total_wall_seconds=88375
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:pending
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.merge_state=merged
step.create-pr.pr_number=1366
step.record-metrics.any_phase_missing_end_time=false
step.finalize-step-sync-baseline.action=rebased
step.finalize-step-sync-baseline.upstream_commit_count=3
merge_commit_sha=b758d5c02ef9f3ced8693829eaae51f985d6c1c0
realized_footprint_count=23
```

## Residue

**The self-review gate was STOPPED, not satisfied.** `pre-submission-self-review` ran six rounds
producing 13 findings, all resolved, 0 pending — but no full-scope round ever returned zero, which is
the workflow's stated close condition. The operator elected to stop and push. Its step record and the
PR body both say so. A further carrier of the single-reader over-claim may survive outside the 23-file
plan surface; no completeness claim is made.

**The plan's own archetype recurred inside its own fixes, five layers deep.** Rounds 2, 4, 5 and 6 each
found defects created by the previous round's fix. Two completeness claims about the same semantic class
were asserted and refuted: round 4 closed it by ENUMERATION (round 5 found three more carriers inside a
file round 4 had already edited), and round 5 closed it by a 5270-file STRING SWEEP (round 6 found a
carrier phrased in none of those strings — the sweep was not incomplete but incapable, since a regex
over phrasings cannot enumerate a semantic class). CodeRabbit's `c3ddfb` then showed the triage fix had
traded `indeterminate_count` for `claimed_count` — cardinality where membership was needed. A fifth
instance sits in the lesson corpus itself: message 008 enumerated "three prior instances already filed"
and omitted `418f3d`.

**Five finalize-machinery findings are LIVE at landing, none fixed in-run** — all are this plan's own
subject one level up, and three of them are ONE conflation (a review-bot refusal handled as review
evidence at three call sites):
- `fffb89` (bug) — `github_re_review` returned `matched: true` where the matched comment WAS the
  rate-limit refusal notice.
- `942346` (bug) — `fetch_findings` stored that refusal as a triageable finding while reporting
  `count_skipped_refusal: 2`.
- `071a67` (bug, error) — that stored refusal's `reviewed_commit_sha` carries the CURRENT head, so
  trigger B reads `head_sha == reviewed_commit_sha` and SKIPS the re-review that would cure it. Self-sealing.
- `6742d8` (anti-pattern) — `reviewed_commit_sha` stamped from the landing HEAD rather than the tree the
  bot actually reviewed. The mechanism that closes `071a67`'s loop.
- `418f3d` (anti-pattern) — `review_commitments reconcile` returned `clear` over
  `commitments_considered: 0` while 13 findings were resolved across six commits. A sub-finding beneath
  it deserves separate attention: the seam anchored 0 of 13.

Two lower-durability findings also remain pending: `3ba537` (`pr_intent_section` appends `## Intent`
after the footer, contradicting `pr-template.md`; its 1500-char budget clipped the non-goals tail) and
`e5bbe0` (`automatic-review` Branch A `display_detail` expands to 87 chars, breaking the <=80 ASCII rule
that same document binds itself to).

**Review coverage of the merged tree is thinner than the green suggests.** The final commit `e60da719c`
was reviewed by `pr-agent` alone, which found nothing on any HEAD. CodeRabbit — the only reviewer that
found any defect (10 findings, 2 Majors, 1 refuted) — was quota-exhausted and never reviewed it; it is
credited `participated` only because it declares no `participation_requires_update`, so no currency test
runs for it. Sourcery contributed no review at all on this PR and will not on any diff this size
(`refused_structural`, 150000-char cap vs 2460 changed lines). The quorum was legitimately satisfied on
the required bot; it must not be read as a reviewed diff.

**The retrospective found a fourth layer in its OWN instruments**, none of it reported by any aspect
script: footprint derivation is rename-blind (true recall 100%, reported 90.9%); `reconcile-ledgers` is
unstable under its own timeout parameter (300s -> 24 findings, 900s -> 20); the red CI run was never
archived, so the artifact store alone says CI was never red; and the `Phase Dispatch Boundaries` section
can NEVER render (`should_emit` reads the key top-level, `analyze-logs` emits it nested), hiding
`error_total_tokens` of 1344170 — 24.8% of the plan — while classifying it as the benign half.

**Cost.** 6-finalize consumed 3.79M of the plan's 6.11M tokens. The largest idle block was
`branch-cleanup` waiting 6h03m on an operator prompt after its own classifier had already returned
`conflict_count: 0`. One ~1h wait was served on a CodeRabbit rate window that the next iteration
established was never workflow-sanctioned (`review_rate_window_await: false`, and the bot is optional);
it was served on an explicit operator directive, and it bought nothing.

**Declared-vs-realized, measured on this plan itself.** The staged spec declared 5 paths; the realized
footprint is 23. This plan is an instance of the under-declaration it was written to measure, exactly as
its own Expected Surface predicted.
