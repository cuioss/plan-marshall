# Landing: PLAN-PR-013 — Participation credited from a superseded commit

epic: review-apparatus · workstream: WS-01 · shipped 2026-08-10
cloud run: `cloud-runs/010-participation-credited-from-a-superseded-commit/`
PR #1141 (`50f67ed2`) + report correction #1142

> Landing analysis over the cloud-wave corpus. The run's `report-01.md` is the run's own claim;
> `verification.md` is the independent ground truth. Where they disagree, verification wins and the
> divergence is recorded here rather than smoothed over.

**Verification verdict: `verified-with-gaps`.**

## What landed

The two headline defects are genuinely closed **for the single-evidence-comment path**.
`_has_update_movement` is gone from the tree; the credit is now a pure comparison against a recorded
merge-candidate SHA held in a currency ledger; `observed_keys` survives only as prose; and `declined`
is a real blocking taxonomy member wired trigger-A → pre-merge barrier, with idempotence tests that
fail pre-fix. 355 tests across six affected surfaces pass, and the currency machinery is byte-identical
between the landing commit and HEAD.

**Deliverables: 5 — 1 done (D0), 4 partial.**

| D | Outcome | What is missing |
|---|---------|-----------------|
| D0 | done | — |
| D1 | partial | The rule says it governs every crediting site; the code gates it on `participation_requires_update` (pr-agent only, 1 of 3 registered bots). |
| D2 | partial | One non-idempotent path (empty merge-candidate SHA + fresh edit) and the second-comment bypass. |
| D3 | partial | Met at trigger A only; the FIND step (trigger B) and the `not_triggered`-remediation consumer still read `matched` alone. |
| D4 | partial | 9 of 10 named tests exist; D4(d)'s **site**-population derivation was never built. |

## ⛔ The defect this plan is named after is STILL LIVE in merged main

`010 G1`, severity **blocker**. The participation loop short-circuits per bot
(`if _bot_kind in participated: continue`) and stages a ledger row only for the *credited* comment. A
currency-subject bot's **second** evidence comment therefore has no ledger row; at an advanced HEAD it
takes the unguarded first-observation arm and credits, and the `if bot not in participated`
subtraction then removes the bot from `stale_participation_bots[]` as well. Reproduced end-to-end
against the shipped producer by **both** verifications independently. PR-Agent declares two publish
shapes (`issue_comment` Guide + `inline` `/improve`), so it is reachable today.

Claimed by **PLAN-PR-024** (ex-`500`) D1.

## Report claims the verification found false

- §D2 names `_existing_pr_comment_shas` / `_recorded_dropped_comment_shas` as a two-source union —
  **neither symbol ever existed**, in HEAD or in the landing commit. The landed reader is
  `_recorded_currency_records`, one source. (Re-verified first-party: zero hits tree-wide.)
- §D4 names the test `test_currency_anchor_is_derived_from_both_sha_sources` — **never existed**. The
  real test is `test_currency_anchor_is_recorded_in_the_ledger_on_credit`, which asserts one source.
- "the empty-SHA case fails closed on both fetches" — overstated; true only of the `record is None`
  arm. Re-verified first-party: `github_pr.py:705` guards on `merge_candidate_sha`, `:708` does not.
- "four stale seven-member sites fixed" — understated; five *files*, one unnamed.
- The plan's ⭐ cold-read obligation was not discharged (three sub-agent findings, no verbatim reading).

## Gaps: 14 — 9 full, 3 partial, 2 uncovered

Full inventory in `cloud-runs/010-…/gaps.md`. Coverage summary:

- **full**: G1, G2, G3, G6, G7, G9, G11, G12, G13
- **partial**: G4 (3 test-prose passages named by no deliverable), G8 (PLAN-PR-025 D2's Done-when is
  weaker than the gap's), G10 (cold read half-discharged)
- **uncovered**: **G5** (report names symbols/test that never existed — both 5NN plans exclude report
  amendment by design), **G14** (the only guard on the recorded-but-ignored bit is a bare substring
  check over two markdown files; `test_branch_cleanup_merge_queue_routing.py` is in no plan's surface)

## Standing facts

- **A landing's late review-fix invalidates the prose that same landing wrote.** Three of `G4`'s eight
  stale contract passages were authored by #1141 and superseded by its own PR-review fix commit,
  because §§D2/D4 were never re-derived afterwards — which is also why the report names two symbols
  and one test that never existed. Any late fix obligates re-deriving every deliverable section that
  describes the design.
- **One grep does not find a stale-prose cluster.** The arm wording is paraphrased differently at
  different sites; the site count moved 6 → 7 → 8 across passes. Two patterns were required.
