# PLAN-LB-139: The review-contract scanners take a lead-in from the preceding paragraph only and read the `=` form of a placeholder

epic: live-blockers
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-139-review-contract-scanners.md` and is queued as one row file, `queue/PLAN-LB-139.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Regrouped on the operator's word of 2026-11-09 from the one live deliverable of the parked PLAN-LB-41 (D3). Its D1 (the code-review
> packs in `marketplace/targets/README.md`) and D5 (the `cuioss-review-bot.md` UNVERIFIED marks) closed when PLAN-LB-127
> (`e71329548`) deleted the target and the standard; its D2 (the `review_support` documentation) moved to PLAN-LB-133 D4; its D4 (two
> declined CodeRabbit findings, `c455b2` on #1759 and a rule-catalog citation check on #1754) is not located at HEAD (no newline guard
> or citation-check module is evident) and is dropped unless the operator names the code. Re-grounded against `main` at `9cd644892`
> by a read-only leaf on 2026-11-09. Every Done-when below fails at `9cd644892`. No Sonar. No token or measurement work.

## Objective

The scanners that guard the review-contract documents (`_review_contract_scanners.py`) accumulate a block's lead-in from every
paragraph and heading since the previous block, so any bash block can pass the "names the rule" check on a citation two paragraphs
above it, and the two quoted-placeholder patterns match `--flag value` but not `--flag=value`. A stricter scanner may find a real
defect in the documents; this plan makes the scanners strict and fixes what they then find.

## Deliverables

1. **The lead-in is the preceding paragraph only, and the quoted-placeholder patterns read the `=` form.**
   - `bash_blocks_with_lead_in` (`test/plan-marshall/phase-6-finalize/_review_contract_scanners.py` L48-74) resets the accumulated
     lead-in at a heading and at a blank-line paragraph break, so only the immediately preceding paragraph counts (with
     `after_block=False` the first block's lead-in is built from every non-blank line of the document today, L72).
   - `DOUBLE_QUOTED_PLACEHOLDER_RE` (L27) and `SINGLE_QUOTED_PLACEHOLDER_RE` (L28) use `(?:\s+|=)` after the flag, as
     `FREE_TEXT_ARGUMENT_RE` (L30) already does; `unquoted_free_text_arguments` (L141) already handles `=`.
   - The two contract tests (`test_code_review_contract.py`, `test_functional_review_contract.py`) pass on the real documents, or the
     documents are corrected where the stricter scanner now finds a real defect; each such correction is named in the PR.

   *Done when:* each of these fails at `9cd644892`: a fixture whose citation sits two paragraphs above the first bash block fails the
   "names the rule" check; a fixture with ``--message="{x}"`` is flagged by the double-quote pattern and ``--message='{x}'`` by the
   single-quote pattern. And these hold at `9cd644892` and must keep holding: a citation in the immediately preceding paragraph
   passes; the space-separated forms are still flagged.

Split guard: one deliverable.

## Standing Constraints

- Settle each HYPOTHESIS first. A refuted claim is dropped from its deliverable and the PR says so.
- A stricter scanner is not loosened to keep a document passing: a real defect in a document is corrected in the document.
- Documentation states the current behaviour; no comment or document describes a change or the old behaviour.
- Tests state their purpose, use the `PLAN_MARSHALL_HOME` fixture and are shown red where the Done-when says so.
- No token or measurement work. No Sonar.

## Claim Labels

- OBSERVED: `bash_blocks_with_lead_in` builds the lead-in from every non-blank line since the previous block, headings included (`test/plan-marshall/phase-6-finalize/_review_contract_scanners.py` L48-74)
- OBSERVED: the two quoted-placeholder patterns use `\s+` only (L27, L28) while `FREE_TEXT_ARGUMENT_RE` uses `(?:\s+|=)` (L30)
- OBSERVED: the scanner is used by `test/plan-marshall/phase-6-finalize/test_code_review_contract.py` (`import _review_contract_scanners as scan`, L47) and `test/plan-marshall/phase-6-finalize/test_functional_review_contract.py`
- HYPOTHESIS: the stricter scanner finds a defect in `phase-6-finalize/workflow/code-review.md` or `functional-review.md` — confirm by running both contract tests against the real documents after the change (verify-at-outline)

## Expected Surface

- OBSERVED: `test/plan-marshall/phase-6-finalize/_review_contract_scanners.py`
- OBSERVED: `test/plan-marshall/phase-6-finalize/test_code_review_contract.py` and `test/plan-marshall/phase-6-finalize/test_functional_review_contract.py` — new cases
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/code-review.md` and `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/functional-review.md` — only where the stricter scanner finds a real defect (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/test_review_contract_scanners.py` — new, if the controls do not fit the two contract tests (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none open.
- Overlaps with: PLAN-LB-133 on `functional-review.md` (a different line) and PLAN-LB-131 on the `phase-6-finalize` tests directory; the gate decides.
- Adjacent to: the contract documents themselves, edited only where a defect is found.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-139-review-contract-scanners.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
