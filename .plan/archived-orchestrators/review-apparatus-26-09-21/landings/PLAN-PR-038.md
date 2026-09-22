# Landing — PLAN-PR-038: review packs become published artifacts

**PR** [#1388](https://github.com/cuioss/plan-marshall/pull/1388) · **merged** via merge queue at `ef974632c` · **WS-03**
**Plan** `review-packs-become-published-artifacts` · 5/5 deliverables · 4,063,723 tokens · 53h42m wall
**Landing message** `inbox/review-packs-become-published-artifacts-017.md` — `landing-check: complete: true`, `missing_keys[0]`

⚠ **This landing was NOT in the operator's paste** — it was discovered by cross-reading `git log` and the live plan store during PLAN-PR-044's analysis, and corroborated at PR #1388 (`state: merged`, `merge_commit_sha: ef974632ca...`). The ledger had this row at `staged` until the preceding status pass corrected it to `running`; without that cross-read it would have shipped invisibly.

## ⛔⛔ Residue — the merge cleared its review barrier by AUTHORIZATION, not by participation

`participation_complete` was **`false`** with `unproven_bots=[pr-agent, sourcery]`. A HEAD-bound `barrier-ask-override` over gap-class `review-barrier-gap` was granted at `0a6fa35f7`.

⭐⭐ **The gap it covers is a DETECTOR gap, not a review gap** — finding `e8bde7`. `head_sha_verified` is derived from the signal **type**: a review object verifies, an `issue_comment` does not. pr-agent re-reviews by **editing one issue comment in place**, so it can **never** yield `head_sha_verified: true`. ⇒ A plan with pr-agent in `required_bots` cannot clear a `participated_stale` block by the remedy the contract prescribes for that state. pr-agent **did** review this exact HEAD and reported no major issues — its own matched-comment body names the commit.

⛔ This is squarely this epic's subject matter, and it is a **live, unowned defect**: the prescribed remedy for a state is unreachable for one of the required bots.

⚠ Two further participation facts, recorded so the override does not read as a lone anomaly:

- **Sourcery refused structurally** — a declared diff-size ceiling (cap 150000 against 2963 changed lines). Not clearable by waiting or re-triggering.
- **CodeRabbit's included review budget was spent on both rounds** (1 review/hour; `0 remain` after the second).

⇒ On this PR, **all three** configured reviewers failed to produce a clearing signal, each for a different reason, and the merge proceeded on an operator-minted HEAD-bound override. The override mechanism worked as designed; what it covered was three simultaneous instrument failures.

## Reconciliation actions

- Queue row `PLAN-PR-038` → `shipped`; `pr` = `1388`; `landing` = `landings/PLAN-PR-038.md`.
- The `head_sha_verified` / in-place-edit detector gap is recorded as an Open Defect and is **not owned by any staged spec**.
