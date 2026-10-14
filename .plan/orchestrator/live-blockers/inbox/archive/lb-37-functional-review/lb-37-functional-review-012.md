envelope_version=1
sender_type=plan
sender_id=lb-37-functional-review
epic=live-blockers
kind=finding
created=2026-10-14T06:50:27Z

# LB-37 leftovers: unfixed advisory findings, an unconfirmed declined finding, and known gaps in the new review-bot pass

These items were logged during PLAN-LB-37 (and its TASK-27 follow-up) but not fixed or confirmed. The operator prefers fixing over accepting, so each needs a decision or a small follow-up plan.

## A. Advisory findings from the in-house reviews (logged to the decision log, not fixed)

From the final functional-review and code-review rounds at `6fca9b207` (both closed with 0 blocking):

1. **`marketplace/targets/README.md` is stale** — it does not describe the cuioss-review-bot target's code-review pack set added by LB-37 (D10).
2. **D12 outline wording** — the solution outline's D12 description no longer matches what shipped; advisory only (the outline is archived with the plan, so this is a lesson about outline drift rather than a file to fix).
3. **`review_support` internal modules** — the phase-6-finalize `review_support` helper's internal modules (`_review_support_validate.py`, `_review_support_attribution.py`) were flagged as under-documented in the skill.
4. **Review-contract scanner edge cases** (`test/plan-marshall/phase-6-finalize/_review_contract_scanners.py`):
   - *lead-in borrowing*: the lead-in is accumulated up to the first block, so `workflow/code-review.md`'s first bash block borrows the citation from line 48 and can pass a placeholder-quoting check it should fail;
   - *`--flag=` form*: the citation regex matches `--flag\s+value` but not `--flag=value` (`\s+` instead of `(?:\s+|=)`), so the `=` form escapes the unquoted-placeholder scan.

## B. Declined review findings that deserve a second look

5. **CodeRabbit c455b2 on PR #1759** — a newline guard was proposed (declined with a reason at the time). Re-evaluate under the fix-over-accept preference.
6. **Part-1 CodeRabbit finding on the rule-catalog citation check** (stacked PR #1754) — declined during the run, never confirmed with the operator. Needs an explicit operator decision: fix or accept.

## C. Known gaps in the two-pass review bot (cuioss-organization v0.42.0, #326)

7. **The code-review comment shape is UNVERIFIED** in `automatic-review/standards/cuioss-review-bot.md` until a live `## PR Code Review Guide 🧭` comment is captured on the first plan-marshall PR after `187f7314a`. Confirm or correct the heading and the "(Code review updated until commit …)" wording, and replace the UNVERIFIED marks.
8. **65,000-character comment cap** — documented in cuioss-review-bot `doc/consumer-guide.adoc` as PR-Agent's truncation (an over-cap review cannot match and fails the gate closed), but not verified in the pinned image and not mentioned in #326. Verify, or remove the claim.
9. **`/improve` has no fail-closed oracle** (pre-existing, carried over), and both `/review` passes still "last write wins" on overlapping comment-triggered runs (now detected by the content-match gate, but not prevented).
10. **`/review -i` now fails the `review / code-review` job** by design (the command check refuses any option). Decide whether that is acceptable for maintainers or whether specific harmless options should be allowed.
