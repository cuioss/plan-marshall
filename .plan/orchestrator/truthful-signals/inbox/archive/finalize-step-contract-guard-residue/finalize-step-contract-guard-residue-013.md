envelope_version=1
sender_type=plan
sender_id=finalize-step-contract-guard-residue
epic=truthful-signals
kind=landing
created=2026-08-24T10:41:04Z

## What landed

finalize-step-contract-guard-residue shipped as #1339 (merged).

```landing-facts
schema=landing-facts/1
plan_id=finalize-step-contract-guard-residue
epic=truthful-signals
pr=#1339
merge_state=merged
deliverables_total=9
deliverables_done=9
total_tokens=5748385
total_wall_seconds=90888
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done
step.branch-cleanup.action=merged
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.merge_state=merged
step.branch-cleanup.upstream_commit_count=4
step.create-pr.pr_number=1339
step.finalize-step-sync-baseline.action=rebased
step.finalize-step-sync-baseline.upstream_commit_count=2
step.record-metrics.total_tokens=5748385
step.record-metrics.total_wall_seconds=90888
step.record-metrics.any_phase_missing_end_time=false
total_billing_weighted=145505241
merge_commit=b95d78437e5b6e20fdfc66198a71c91b52380ad5
```

## Residue

Narrative items no step recorded as a fact. Each is first-party from this run.

**The plan reproduced its own target archetype twelve times, in its own work.**
`pre-submission-self-review` fired 8 times (7 recorded `failed`) and produced 20
findings, all resolved. One over-claim — describing a `mention AND NOT
_REFUTATION_RE` predicate as a general "claim test" — appeared at FOUR sites and
was corrected in the order the tooling could see them: docstrings (rounds 3-4),
assertion messages (round 5), a comment (round 6). Root cause filed as lesson
2026-08-23-22-001: the self-review surfacer emits only `context: docstring`
prose, so assertion messages and comments are invisible to every round. The
operational consequence is sharper than the gap: when a delta's whole content is
uncovered prose, the candidate set is byte-identical to the previous round's, so
a round driven by it returns a clean verdict certifying nothing about the change.

**Delta rounds cannot close the step, and the switch to full surface was not
cosmetic.** Rounds 2-6 were single-file deltas. The first full-surface round
found SEVEN further findings, two of them in a file outside this plan's diff
(`marshall-steward/references/architecture-setup.md`), where D6's push removal
had left wizard prose describing behaviour that no longer exists — and where this
plan had itself asserted the two files "stay aligned" without checking.

**External review contributed nothing measurable on this diff.** 3 bots: pr-agent
(required) published an empty result, coderabbit refused on quota (awaitable),
sourcery refused structurally on size. `participation_complete: true` carries
`proves: participation_only`. Measured first-party: the PR is 179,695 diff
CHARACTERS against sourcery's stated 150,000 cap — 19.8% over — while `test/`
alone (129,556) and non-`test/` (50,139) each clear it, so a source/test split
would have gotten both halves reviewed. coderabbit's refusal was awaitable and
`review_rate_window_await: false` is what made it permanent.

**The pre-merge barrier earned its place.** Its re-fetch stored one comment
`automatic-review` had never seen, at the same HEAD that step reported
`0 comment(s) found` for. Non-actionable in the end, but a genuine post-FIND
pre-merge window catch.

**Four orchestrator-caused defects, recorded rather than absorbed.** (1) A
`mutates_source` step ordered above a `head_dependent` gate strands that gate's
verdict on a superseded tree within a single forward pass — `pre-push-quality-gate`
recorded 250aa788, `simplify` then advanced HEAD to 990d88010; CI covered the
merged tree, the local gate's record did not. Filed as inbox 012. (2) Finding
f40bc9 sat pending from round 2 to the closing round because its fix was made and
never recorded; it would have blocked the merge gate. (3) The required
`candidates` prompt field was omitted on the first self-review dispatch,
contributing to a `step_record_missing` guard trip. (4) Two concurrent
module-tests builds produced a 1030s run and a spurious subprocess-timeout
"failure" that was contention, not a defect. `lessons-capture` (order 991) was
also skipped by the forward pass and run late, before this emission.

**The retrospective's own largest finding was true of itself and is now
resolved.** It reported `6-finalize` — 48% of dispatched tokens — as structurally
unbillable, because it runs at 995 while `record-metrics` closes the phase at 998.
It published 63,456,072 at n=5/6. Running `end-phase` then `enrich` in the
documented order closed the window: the final ledger reads 145,505,241 at n=6/6,
2.3x its figure, and its own caveat ("plausibly under half the real total") was
well-calibrated.

**Three further instrument defects, filed as lessons or inbox messages, not
fixed here:** `review_commitments reconcile` returns `clear` over a commitment
population that is empty BY CONSTRUCTION at its order (2026-08-24-08-001);
`pr_intent_section` appends the Intent block after the PR body footer, contra its
template (2026-08-24-08-002); `automatic-review`'s Branch A `display_detail`
template cannot satisfy the 80-char ASCII constraint the same document states
(2026-08-24-09-001). Plus inbox 009: `architecture search --content` does not
cover `.claude/**` or `.github/**` while CLAUDE.md's hard rule names both in its
allowlist parenthetical — a `count: 0` meaning *could not look*, wearing the
representation of *looked, found nothing*.
