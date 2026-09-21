envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-09-13T14:56:35Z

# Two review-mechanics findings from PLAN-TRUTH-139's landing (PR #1479)

source_plan: plan-truth-139
source_pr: 1479
source_epic: truthful-signals

Forwarded verbatim from `plan-truth-139`'s candidate-lesson filings (`inbox/plan-truth-139-005.md`,
`inbox/plan-truth-139-006.md`), both `suggested_epic: review-apparatus` — review mechanics are this
epic's subject, not truthful-signals'.

## 1. A `review_body` carrying content beneath a status line must not be classified meta

component: plan-marshall:workflow-integration-github
category: improvement
confidence: high

The per-bot registry's `review_body_summary_patterns` rule strips CodeRabbit's `Actionable comments
posted: N` boilerplate. It is right about the boilerplate and wrong about the payload: it classifies the
WHOLE body by its opening line, so a `review_body` whose substantive content sits *beneath* the status
line is recorded as meta.

On PR #1479 two such bodies carried real claims and both were classified meta:

- `f7de42` — a **Major**, and the most consequential single finding of round 2. It arrived in the review
  body as an outside-diff comment because GitHub would not host it inline: `limit get` routed a READ
  through the committing `rmw_json`, so a corrupt `build-queue.json` is **erased by a read**, after which
  the next admission over-admits past the cap. Verified in triage: `rmw_json` always commits
  (`_locks_core.py:399`) and `_read_json_or_empty` silently yields `{}` on corrupt/non-dict input
  (283-303).
- `bde483` — two nitpicks, both accepted as real gaps: a mirrored ceiling constant with no drift test, and
  control-character coverage showing that removing `report_safe` would leave the suite green — the
  security fix this PR had just made was unpinned.

The consequence is measurable: CodeRabbit's `actionable_count` reads 15 when its substantive output was
17, and `escapes_total` (15) excludes both — the single most consequential finding of round 2 is in
neither the actionable count nor the gate-escape set. The honest denominator for its accuracy is 17: 16
fixed, 1 verified-and-declined, 0 wrong.

Root cause: the classifier's unit is the body, and its evidence is the opening line. A pattern designed
to recognise a *prefix* is being used to decide the disposition of the *whole document*.

Proposed action: match the status line and strip it, rather than classifying the body by its opening.
After stripping, a body with no remaining substantive content is meta; a body with remaining content is
actionable and its content is the finding.

Evidence: review-retrospective.md § "Two measurement artifacts in the numbers above" item 2;
§ Recommendations item 2; decision `f93fc5` (the triage pass overrode the classification by hand to see
`f7de42`, and verified `rmw_json` always commits / `_read_json_or_empty` silently yields `{}`).

## 2. Re-fire the pre-push quality gate after the `mutates_source` steps that follow it

component: plan-marshall:phase-6-finalize
category: improvement
confidence: high

The gate/review delta instrument on PR #1479 returned `verdict: excluded`,
`exclusion_reason: gate_tree_unsubstantiated`, `structural_share: null` (not 0). It counted 15 escapes
(`gate_addressable: 10`, `gate_structural: 5`) but could make no claim about gate/review parity.

Two structural reasons: (1) the reviewed tree has no single identity — `pr-comment` findings carry three
distinct `reviewed_commit_sha` values because the PR looped back twice and `fetch_findings` pre-filter 5
never re-stamps an existing value; (2) the gate tree is not any of them — `finalize-step-simplify` (order
8) and `finalize-step-security-audit` (order 9) both run AFTER `pre-push-quality-gate` and are
`mutates_source`, so the reviewer saw lines the gates never did. The gate tree was `0e8ac4423`, equal to
none of the three reviewed shas.

Concrete cost: the security-audit step hardened 4 files in commit `7e895b76`, after the gate had certified
an earlier tree, and the one boundary it missed became CodeRabbit Major `266f33`. The gate never saw
either the fix or the gap.

Proposed action: re-fire `pre-push-quality-gate` after the `mutates_source` steps that follow it, so the
gate tree and the pushed tree are the same tree — membership read from step declarations. Second, smaller
part: a loop-back invalidates the delta's tree identity, not just a step's freshness; if the delta is to
be measurable on looped-back PRs, per-iteration `reviewed_commit_sha` stamping needs reconciling — the
same re-stamp defect already noted against the participation ledger.

Evidence: review-retrospective.md § Review-versus-Gate Delta (`verdict: excluded`,
`exclusion_reason: gate_tree_unsubstantiated`, `gate_head_sha: 0e8ac4423`); § Recommendations items 3-4;
`phase_6.steps` ordering (`pre-push-quality-gate` position 3, `finalize-step-simplify` 6,
`finalize-step-security-audit` 7); `pre-push-quality-gate` `firing_count: 7` vs `automatic-review`
`firing_count: 4` with three distinct `reviewed_commit_sha` values.
