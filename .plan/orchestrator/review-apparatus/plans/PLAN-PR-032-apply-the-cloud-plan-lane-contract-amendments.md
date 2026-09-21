# PLAN-PR-032: Apply the cloud-plan-lane contract amendments — from outside the lane

epic: review-apparatus
workstream: WS-02

> Staged plan spec, created 2026-08-23 by the cloud-wave ingestion. See
> `../cloud-wave-audit.md` § 5 for why this plan exists and why only a plan OUTSIDE the lane can do it.

## Objective

Three gaps from the cloud wave have been open since 2026-08-11 for one structural reason: they require
editing `.claude/skills/cloud-plan-lane/SKILL.md`, and **the lane contract forbids a run governed by it
from amending it**. Every plan that met one of these recorded a *proposal* and stopped. The consequence
is not theoretical — 27 commits have touched that file since plan 050 merged, none applied its
proposal, and the proposal is now a **regression** if applied verbatim.

`050 G4`'s own Task names the escape: *"Then apply — the proposal-only prohibition binds a run governed
by that contract, not a run outside the lane."* A `/plan-marshall` run is not a lane run. This plan
re-anchors the proposals against the current text and **applies** them.

## Problem

Three defects, one file.

**1. The lane's reviewer-participation verdict set cannot express "reviewed, found nothing".**
`cloud-plan-lane/SKILL.md` § Step 7 carries four verdicts — `reviewed` / `rate-limited` / `silent` /
`unreadable`. There is no `reviewed-empty`, so a reviewer that ran and produced nothing is recorded as
`reviewed`, indistinguishable from one that produced nine findings. Verified at HEAD:
`grep -n 'reviewed-empty'` over the whole file returns **zero**. There is also no required/optional
classification, so the shortfall disclosure is computed against the **roster**, not against the
**required set** — the defect the whole of PLAN-PR-021 was about, still live in the lane's own contract.

**2. The shortfall disclosure and the report template both emit a bare `N-of-M`.** Step 8's shortfall
condition and the § Report reviewer-participation template each state coverage as an unqualified ratio
with no named denominator. The § Report template is the site every future run-report reader actually
sees, and it is the one an applier has to invent text for.

**3. A run recorded a bot `silent` that had published a rate-limit notice — on a surface the contract
already mandates reading.** Plan 060's run called `sourcery-ai` silent; PR #1182's *reviews* surface
carried a `sourcery-ai[bot]` review (id 4915308445) whose body was a weekly rate-limit notice. **A rate
limit reopens; a skip does not**, so the disclosure understated what a short wait would have bought.

⛔ **The obvious remedy is REFUTED and must not be implemented.** The lane already enumerates three
publish surfaces (`SKILL.md:1291`, table at `:1296-1300` naming *Review summary bodies* →
`gh pr view --json reviews` / `get_reviews`), and `:1302-1308` carries a worked example of exactly this
failure. The contract is not missing the surface. **The real question is why a run following that
contract did not read it** — which is a question about enforceability, not about enumeration.

## Deliverables

**D0 — GATE, mutates nothing.** Re-anchor all three proposals against the current file by their quoted
text, never by line number. Record, per proposal: the current span, what has grown inside it since the
proposal was written, and the exact replacement. **HALT and report if any anchor no longer resolves** —
a proposal whose anchor has dissolved is re-derived from its gap, not guessed at. Re-read
`../cloud-runs/050-…/gaps.md` § G4 and § G5 and `../cloud-runs/060-…/gaps.md` § G6 at this step; they
are the specification, and they carry the evidence.

**D1 — Apply the Step 7 verdict amendment.** Add `reviewed-empty` and a required/optional classification
to the verdict table, **keeping the `unreadable` row, its ⛔ block and the merge-gate paragraph intact**
(landed by #1281 after the proposal was written), and **keeping the whole `Reopens?` subsection**
(landed by #1244), folding D1a's awaitable-vs-hard wording into it rather than duplicating it.

**D2 — Apply the Step 8 shortfall amendment.** Re-point at the current **condition 5** (the proposal
named condition 4) and give the disclosure a required-set shortfall predicate: `k of |required_bots|`
and `j of |optional_bots|`, each naming its population, plus the record's own `roster r of |roster|`.
⛔ **Do not import the string "This is a disclosure requirement, and it is NOT a block"** — it does not
exist in the contract, and the current wording is deliberately weaker because condition 6 carves
CodeRabbit out. Preserve that qualification.

**D3 — Apply the § Report template amendment.** The reviewer-participation table gains a
`Class (required / optional / unclassified)` column and the `reviewed-empty` value; the closing line's
bare `N-of-M` is replaced by the two named ratios.

**D4 — Make the three-surface read evidenced rather than merely mandated.** The contract already
requires reading all three surfaces. Add the one thing that would have caught plan 060's run: the
reviewer-participation record must state, per reviewer, **which surface the verdict was read from** —
so `silent` becomes a claim about three surfaces that were checked, not a claim a reader cannot audit.
A verdict with no surface named is `unreadable`, not `silent`.

## Claim Labels

- OBSERVED: `reviewed-empty` appears nowhere in `cloud-plan-lane/SKILL.md` — `grep`, zero hits, whole
  file, 2026-08-23.
  - verdict: corroborated | checked_at: 7845a4b9a383a4d58c9314bfce89970ced67c4f7 | by: review-apparatus/cleanup | rescoped: n/a | evidence: Re-grounded at HEAD 7845a4b9a, method: whole-spec-file intersection against git diff --name-only 26645688b..HEAD (197 paths). Fail-closed by design - the scan is over the WHOLE spec file, not a parsed Expected Surface section, because two section parsers disagreed on this corpus. Basename matching stays DISCARDED as non-discriminating. NO running-row exclusion applied this pass: the queue has no running plan. Intersection: 0 hit(s). EMPTY INTERSECTION - nothing in the window touched this spec, so its premise is unmoved. This is a checked negative, not an unchecked one.
- OBSERVED: the § Step 7 verdict block spans `:1327-1388`; the `unreadable` row is at `:1337`, its ⛔
  block at `:1339-1342`, the merge-gate paragraph at `:1354-1359`, the `Reopens?` subsection at
  `:1365-1384`. Read at HEAD `e8324d241`.
- OBSERVED: the shortfall disclosure is Step 8 **condition 5** (`:1686`), carrying a `Reopens?` clause;
  Step 8 begins at `:1553`.
- OBSERVED: the § Report reviewer-participation template is at `:2101-2113`; its closing line
  ("State the coverage as N-of-M") is `:2113`. **The proposal cited `:1736-1746` — ~360 lines of
  drift.** Match on text, never on line.
- OBSERVED: the lane enumerates three publish surfaces at `:1291` with a table at `:1296-1300`, and a
  worked example of the 060 failure at `:1302-1308`. Step 7 binds it at `:1282` and `:1329`.
- OBSERVED: 27 commits have touched this file since plan 050's merge `b286928c`; none applied the
  proposal.
- HYPOTHESIS: D4's per-reviewer surface attribution is implementable without changing the verdict
  vocabulary — confirm/refute against § Step 7's record shape at outline (verify-at-outline).
- Verify-first clause: re-read the three gap entries in `../cloud-runs/` before scoping. The proposals
  in the landed run reports are **stale by construction** and are leads, not specifications.

## Expected Surface

- OBSERVED: `.claude/skills/cloud-plan-lane/SKILL.md` — §§ Step 7, Step 8 condition 5, Report
- ⛔ **Epic-tree record, NOT repository source — read input only.** `../cloud-runs/` resolves under `.plan/local/orchestrator/review-apparatus/`, which is **git-ignored**; the records were moved out of `doc/plans/` at the cloud-wave ingest (`26f2f417b`, #1333). An edit here reaches **no PR diff** and is machine-local. Read it; do not count it as delivered surface.
- OBSERVED: `../cloud-runs/050-coverage-shortfall-disclosed-against-the-roster-not-the-required-set/gaps.md` (read only)
- OBSERVED: `../cloud-runs/060-a-prose-routing-table-is-not-an-enforcement-boundary/gaps.md` (read only)

**One file changes.** This plan is disjoint from every other spec in the epic by construction — no
other plan may write `.claude/skills/cloud-plan-lane/SKILL.md`, which is precisely why they all deferred.

## Dependencies and Sequencing

- Depends on: none within this epic. **Emittable immediately**, subject to the cross-epic constraint
  below.
- Overlaps with: none in this epic. PLAN-PR-026 D6 and PLAN-PR-031 D5 each hold a *proposal* against
  this file; both explicitly forbid touching it. **Once this plan lands, drop PLAN-PR-031 D5 items 1-3
  and PLAN-PR-026 D6's lane item** — they become discharged, and leaving them staged re-opens the
  proposal-only loop this plan exists to close.

⛔⛔ **CROSS-EPIC COLLISION — a single ledger cannot see this, so it is written down here.**
`corpus cross-check` at ingestion found **five sibling-epic specs** whose expected surface includes
`.claude/skills/cloud-plan-lane/SKILL.md`. Two matter:

| Sibling spec | Its status | Subject | Verdict |
|---|---|---|---|
| `truthful-signals/PLAN-TRUTH-075-cloud-lane-build-gate-reads-one-field-short` | **launched** | the lane's build gate | **LIVE COLLISION** — emitted, not started. Do not emit this plan while that one is un-landed without confirming with the operator. |
| `code-intelligence-substrate/PLAN-CIS-055-cloud-plan-lane-contract-proposals` | staged | the Step 1 skill-loading table, blocked-run reporting, post-PR push batching, the § Step 8 **conditions sequencing note** | **NOT a duplicate** — different passages — but it edits §§ Step 7 and Step 8, the same two sections this plan rewrites. Sequence, never pair. |

✅ **Checked and cleared as non-duplicates:** `truthful-signals/PLAN-TRUTH-061` (**shipped #1112** — it
is the plan that *introduced* the disclosure this plan repairs, not a competitor), `PLAN-TRUTH-063`
(shipped #1137), and `PLAN-TRUTH-092` (staged; run-report accuracy, not the verdict set). None declares
`reviewed-empty`, the required/optional classification, or the shortfall predicate — verified by grep
over all four specs.
- Adjacent to: `finalize-step-review-retrospective/SKILL.md`, which carries the in-lifecycle analogue
  of the same disclosure. It stays untouched — PLAN-PR-026 and PLAN-PR-030 own it.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-032-apply-the-cloud-plan-lane-contract-amendments.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
