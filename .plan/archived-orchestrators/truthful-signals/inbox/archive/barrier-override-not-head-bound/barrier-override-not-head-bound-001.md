envelope_version=1
sender_type=plan
sender_id=barrier-override-not-head-bound
epic=truthful-signals
kind=finding
created=2026-08-02T13:42:19Z

# `metrics.md` reports a "Total" that excludes 76% of the tokens the plan actually spent

**Source**: cost analysis of `barrier-override-not-head-bound` (PR #1077, merged 2026-08-02),
requested by the operator after the reported 4.1M looked disproportionate to a 9-file change.

## Provenance — the evidence root

Every measurement in this message is re-derivable from ONE archived plan directory. The plan is
**closed and archived**; nothing here needs the live store, and no figure is quoted from session
memory.

- **Evidence root**: `.plan/local/archived-plans/2026-08-02-barrier-override-not-head-bound/`
- **Plan id**: `barrier-override-not-head-bound` (epic `review-apparatus`, spec
  `PLAN-PR-015-a-barrier-override-is-not-bound-to-the-head-it-was-granted-against.md`)
- **PR**: #1077 · **squash-merge commit**: `967ba03f599c4227d52a2ec6564999a32462ba13` on `main`
- **Shipped diff**: 9 files, +2,083 / −16

Files under the evidence root that back the specific claims below:

| Claim | Artifact (relative to the evidence root) |
|---|---|
| the `Total` row and the six per-phase `Inline main-context tokens` lines | `metrics.md` |
| the finalize per-step token breakdown summing to 2,426,526 | `work/metrics-accumulator-6-finalize.toon` |
| `fired_signals: ["S7:risk_prose"]`, `scope_estimate: single_module` | `logs/decision.log` (planning-lane route entry) |
| per-dispatch termination causes incl. the session-limit kill | `work/metrics-dispatch-boundaries-6-finalize.toon` |
| the four self-review findings (`9e1caf`, `37dad6`, `d64379`, `454e1b`) | `artifacts/findings/qgate-6-finalize.jsonl` |
| the retrospective's own 2.3×-anchor claim | `quality-verification-report.md` |

⚠ This message is `sender_type: plan` from an **archived** sender — the sender cannot be asked
follow-up questions. The artifact table above is the substitute for that, so prefer re-deriving
from it over re-contacting the source.

## The signal defect (why this belongs to this epic)

`metrics.md` renders a row labelled **`**Total** … 4,135,327`**. That number counts
**dispatched subagent tokens only**. The same document, in per-phase detail, carries an
`Inline main-context tokens` line per phase that is explicitly *not* summed into it
("surfaced alongside the dispatched total, never replacing it"), and a
`Billing-weighted total` that is dismissed in its own parenthetical as
"not a work-comparable measure".

Measured on this plan:

| Population | Tokens | In the "Total" row? |
|---|---|---|
| Dispatched subagents | 4,135,327 | yes |
| Inline main-context (input+output+cache_creation) | 13,355,750 | **no** |
| Billing-weighted (incl. cache_read) | 66,476,321 | no |

So the headline understates work-comparable spend by ~4×, and the population it omits is
**3.2× larger than the one it reports**. A reader — human or the audit's own budget-anchor
check — reads `Total` as a total. It is a partition labelled as a whole.

⭐ This is the epic's own archetype at the measurement layer: the number is not wrong, it is
*confidently labelled*. `partial: false` was also returned (all six phases recorded), so every
completeness signal on the report reads green while three quarters of the spend is off-ledger.

**Confirm/refute artifact**:
`.plan/local/archived-plans/2026-08-02-barrier-override-not-head-bound/metrics.md` — compare the
`**Total**` row against the six per-phase `Inline main-context tokens` lines
(585,566 / 1,116,295 / 2,149,438 / 1,990,349 / 7,514,102; 1-init carries none).

⚠ **Do NOT "fix" this by adding the two numbers.** They are different populations measured
differently, and cache_read is genuinely not work-comparable. The defect is the **label and the
omission**, not the arithmetic: the row should either name what it counts
(`Total (dispatched)`) or carry the inline figure as a second first-class column. Deciding which
is the plan's job, not this finding's.

## Secondary: the audit's budget anchor is computed against the understated population

`plan-retrospective` compared 2,967,497 (a mid-finalize dispatched subtotal) against a 1.3M error
anchor and reported 2.3×. Final dispatched is 4,135,327 (3.2×). Including main context it is
~13× the anchor. Every budget verdict this project makes is therefore computed against the
partition, not the whole — so the anchor is calibrated to a number that omits the dominant cost.

## Where the spend actually went (evidence, not impression)

Dispatched, by phase — **execute was 11%**:

| Phase | Tokens | Share |
|---|---|---|
| 1-init | 41,003 | 1% |
| 2-refine | 226,454 | 5% |
| 3-outline | 535,346 | 13% |
| 4-plan | 439,628 | 11% |
| 5-execute (the shipped change) | 466,370 | 11% |
| 6-finalize | 2,426,526 | 59% |

Finalize, exact from the evidence root's `work/metrics-accumulator-6-finalize.toon`
(sums to 2,426,526):
self-review ×3 + fix ×2 = 1,040,087 · review-bot machinery (3 × automatic-review + unified
triage) = 504,514 · lessons (capture + housekeeping) = 270,864 · retrospectives (plan + review)
= 265,106 · create-pr = 151,835 · simplify = 143,200 · plugin-doctor = 50,920.

Shipped diff: 9 files, +2,083 / −16, of which 1,417 lines (68%) are tests.
≈2,000 dispatched tokens per shipped line; ≈8,400 including main context.

## Four causes, ranked by size

1. ⭐ **One routing predicate bought the deep lane — 1,201,428 tokens (29%).**
   `manage-status planning-lane route` returned `deep` with `fired_signals: ["S7:risk_prose"]` —
   a *single* signal — while `scope_estimate` was `single_module` and `change_type` was
   unresolved. The realized footprint was exactly the 9 declared files. The input it scored was
   an **epic plan spec**, which is written in ⛔/⚠ markup as a matter of the orchestrator's own
   authoring style. **The sensor read authoring rhetoric as risk.** Every epic-launched plan
   ingests such a spec, so this mis-fires structurally, not occasionally.
   *Confirm/refute*: the evidence root's `logs/decision.log`, planning-lane route entry
   (`decision_predicate: signal_set`, `fired_signals[1]`).

2. **Four independent review apparatuses inspected the same 9 files — 1,666,349 (40%).**
   q-gate-validation ×2 (443,068; the 4-plan pass returned zero new findings),
   pre-submission-self-review ×3 (687,311), retrospectives (265,106),
   lessons capture + housekeeping (270,864).

3. **Ceremony is near-constant in diff size.** 22 finalize steps; finalize cost 5.2× execute.

4. ⭐ **Main-context context growth is unbudgeted and dominant.** 13,355,750 inline; 281M
   cache_read in finalize alone. The orchestrator reads large standards/workflow docs inline to
   drive steps that are a handful of script calls (`branch-cleanup.md` is ~1,400 lines, read in
   four chunks, to drive a merge that took three script calls), and every doc stays resident for
   the remainder of the session. **No knob, lane, or posture bounds this**, which is why it does
   not appear in any budget verdict.

## Identified waste, with amounts

- Harness session-limit kill mid-`automatic-review`: **96,985 tokens, zero output** (re-dispatched
  fresh at 106,198).
- Second q-gate-validation at 4-plan: **227,776 for zero new findings**.
- Self-review rounds 2–3 re-ran the **entire** candidate surface (86 → 123 candidates) rather than
  the delta since the prior pass: **~467,000**.
- Review-bot arm: **504,514 to obtain one "No major issues detected" table** from one bot, while
  both substantive bots (coderabbit `awaitable_window`, sourcery `hard_quota`) refused.

## ⛔ The trap in the obvious remedy

"Run the `minimal` posture" would have dropped `pre-submission-self-review` — the one arm that
caught this plan reintroducing the exact fail-open shape it existed to remove (finding `9e1caf`:
a kind-agnostic authorization check that a `pre-merge-consent` granted seconds earlier at the
same HEAD would satisfy). **Cheaper, and it ships the defect.** The lever is review that scales
with the delta, never less review.

## Candidate remedies (sizes are what they would have saved HERE)

| # | Remedy | Saving | Owner epic |
|---|---|---|---|
| 1 | Require `S7:risk_prose` to co-fire with a scope/change-type signal, or exempt spec-pointer-ingested bodies from the prose sensor | ~700K | truthful-signals |
| 2 | Label/complete the `Total` row (this finding's head) + recalibrate the budget anchor to the population it actually measures | — | truthful-signals |
| 3 | Fire q-gate-validation once per plan (not per phase) for `single_module` scope | 228K | truthful-signals |
| 4 | Scope self-review re-runs to the delta — it already computes a candidate surface, it should diff it | ~350K | ⚠ **review-apparatus-shaped** |
| 5 | Short-circuit the review-bot wait/poll/triage machinery when every substantive bot reports a refusal class | ~300K | ⚠ **review-apparatus-shaped** |

⚠ **Routing note.** Items 4 and 5 govern the review apparatus, so under the three-way routing
rule they belong to `review-apparatus`, not here. They are recorded in this message for
completeness of the analysis only — **delegate them through that epic's INBOX rather than
staging them from this one.** Items 1–3 are measurement-truth work and are this epic's.

Items 1–5 total ≈1.6M, ~39% of dispatched spend, with no loss of the review that mattered.
Item 4 in the table above does not address the 13.4M main-context population at all — nothing
currently does.
