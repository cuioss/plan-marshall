envelope_version=1
sender_type=plan
sender_id=module-budget-campaign-run-2-slice-040
epic=test-quality
kind=finding
created=2026-09-18T17:46:51Z

## Operator-directed post-plan follow-up: slice-040 review sweep

Author: operator-directed follow-up executed outside the plan lifecycle by the
assistant (the plan itself is archived); filed under this plan id so the
residue stays correlated. Not plan-executed work.

### Review sweep (operator order: revisit every slice PR, handle unhandled comments)

Revisited all 11 slice PRs (#1513–#1522, #1526). Every thread except seven
carried handling comments. The seven unhandled CodeRabbit inline findings all
sat on merged PR #1519 (posted post-merge, after the finalize loop ended):

- 6 accepted and fixed in follow-up PR #1529 (merged as `2fd4379f`):
  help-surface `comments` roster (3 twin tables), `args.body` guard extension
  (github + gitlab twins), behavioral long-body test, 7 docstring rescopes,
  dead-code deletions (`_CONTRACT_*`, 2× `import sys`, window constants,
  severed parity apparatus).
- 1 refuted with rationale: `_RULESET_MERGE_METHOD` derivation (hardcoded
  triples are independent oracles; derivation would be tautological).
- Dispositions posted: 1 summary + 7 per-thread replies on #1519 (replies
  published via 3 submitted pending reviews).
- #1529 itself reviewed clean by CodeRabbit (walkthrough only, Minimal risk,
  zero findings) and merged.

### Deferred-hardening pickup (operator order: do it now, no ceiling)

The 8 findings dispositioned on #1526 as accepted-as-future-hardening under
the plan's loop-back ceiling are being implemented now as direct follow-up
(no ceiling applies outside the plan lifecycle). Verdicts from codebase
analysis:

- Doing now: dispatch-search bounding, frontmatter `requires` parsing,
  reachable-elapsed ratchet values, dispatch-row single-mapping assertion,
  fixture-catalogue roster derivation, roster-invariant executable checks,
  DOC_VOCABULARY_SITES derivation.
- NOT doing (flagged, not scheduled): canonical CI taxonomy derivation —
  it refactors production `ci_verify.py` plus tests plus docs, i.e. a
  feature, not test hardening. Recommending a dedicated plan if wanted.
- Watch item: the sibling-site claim pattern in review findings is unreliable
  (one `_CONTRACT_*` claim named 3 files, only 1 affected; one `import sys`
  claim named 5 files, only 2 affected) — every site re-verified with AST
  before editing; one near-miss reverted (3 files where `sys` is genuinely
  used via `monkeypatch.setattr(sys, ...)`).
