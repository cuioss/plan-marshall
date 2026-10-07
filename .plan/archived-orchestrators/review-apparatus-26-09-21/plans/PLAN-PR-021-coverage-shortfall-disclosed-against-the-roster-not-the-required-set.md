# PLAN-PR-021: A coverage shortfall is disclosed against the roster, not against the required set

epic: review-apparatus
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-PR-021-coverage-shortfall-disclosed-against-the-roster-not-the-required-set.md`
> and is queued in the epic `status.json` `plans[]` field. The orchestrator EMITS the command below;
> it never launches the plan inline.

## Provenance

Staged from inbox message `truthful-signals-022.md` (2026-08-08), which is itself a RETRACTION of that
sender's own `truthful-signals-021.md`. Two of that earlier message's claims were withdrawn by the
sender; **this is the one item that survived**, and the sender explicitly handed the call to us.

⭐ **The naming follows the epic's standing practice change**: the plan id names the OBSERVATION — a
shortfall disclosed against the wrong denominator — not a hypothesised cause. The phrasing survives any
diagnostic outcome.

## Objective

`PLAN-TRUTH-061` (#1112) shipped a review-coverage shortfall disclosure at `cloud-plan-lane` § Step 8.
It derives its expected-reviewer population from the **registry roster** — every `author_login` in the
`automatic-review/standards/{bot_kind}.md` registry docs — and fires whenever *any* member of that
roster did not review. It never reads `required_bots` / `optional_bots`. So on a PR whose required
quorum is fully satisfied, the mechanism still announces a "shortfall" the moment an OPTIONAL bot is
silent. Make the disclosure state coverage against the denominator that actually governs the merge,
while keeping optional-bot silence visible as what it is: an accounted-for absence, not a gap.

⛔ **This is a false-alarm generator inside a disclosure mechanism** — the mirror image of the
vacuous-guard class this epic catalogues. Not a gate that passes having examined nothing, but a gate
that reports a gap that is not one. A disclosure that cries wolf gets tuned out, and then the real
shortfall reads as noise. The defect is the *miscalibration*, never the disclosing.

⛔ **Do NOT fix this by narrowing the population to the required set and dropping the rest.** The
roster-wide participation record is valuable and is deliberately population-derived — a hand-maintained
reviewer list is the very defect that step exists to prevent. What is wrong is the VERDICT computed
over it, not the population read. Removing optional bots from the record would trade a false alarm for
a blind spot.

## Deliverables

1. **D1 — the disclosure distinguishes required from optional when computing its verdict.** The
   participation record keeps ranging over the full roster; the *shortfall* statement is computed
   against `required_bots`. An optional bot that did not review is reported as an accounted-for
   absence with its reason, never as a shortfall. State both numbers rather than replacing one with the
   other — the reader needs "required quorum met (1 of 1); 2 optional reviewers silent" and not a bare
   ratio whose denominator is unstated.
2. **D2 — the denominator is NAMED wherever a coverage ratio is emitted.** ⛔ **CONSUME
   PLAN-PR-006's D1 counting rule; do NOT re-derive it.** Three plans in this epic need per-reviewer
   finding counts (PR-006 D1, PR-011 D4, this D2), and PR-006 D1 owns the rule for all three — see that
   spec § *D1 OWNS THE COUNTING RULE FOR THE WHOLE EPIC*. If PR-006 has not landed when this plan
   outlines, **state the rule here and hand it back**, so the epic still has exactly one. ⛔ **A bare "N of M" is the
   defect.** Every emitted ratio — in the Step 8 disclosure, in the § Report Reviewer-participation
   table, and in the run report's coverage line — names which population M is. This is the epic's
   standing publish-your-population rule applied to a disclosure surface.
3. **D3 — the config read is resolved, not assumed.** `required_bots` / `optional_bots` are read from
   the resolved step config, and the **`bot_lists_provenance`** field is honoured: an `answered`
   provenance is a deliberate operator answer, an unset one is not. ⛔ **An empty `required_bots`
   means the quorum is VACUOUSLY SATISFIED** per the contract — so the disclosure MUST distinguish
   "required quorum met" from "no required bots configured" and must never render the second as the
   first. This is the vacuous-authority archetype, and it is reachable by default in any project that
   has not answered the question.
4. **D4 — tests, each verified to FAIL pre-fix, and each proving discrimination by mutation.** At
   minimum: required-bot silent (real shortfall, must fire), optional-bot silent with required met
   (must NOT fire as a shortfall, must still be recorded), and empty `required_bots` (must render as
   vacuous, not as met). ⛔ Per lesson `2026-07-16-17-004`, a test that passes both pre- and post-fix
   is vacuous — prove each one discriminates.

Four deliverables — below the ~6 split guard, no split rationale owed.

## ⛔⛔ ABSORBED 2026-08-08 (inbox drain) — the OPPOSITE polarity of this plan's defect, on a live PR

Source: inbox `truthful-signals-024`, routed here under the three-way rule. PR **#1122**.
⛔ **LEAD, NOT FACT** — the sender explicitly did NOT run `ci pr comments --pr-number 1122`, so the
per-bot states are the `automatic-review` step's own report, not an independent measurement. Only
`ci pr comments` is evidence of participation. **Re-derive at outline before scoping on it.**

`automatic-review` recorded **"quorum met (participation only)"** with CodeRabbit **rate-limited,
never having reviewed any head**, and pr-agent and sourcery both `participated_but_empty`.
`required_bots='pr-agent'` alone (`bot_lists_provenance='answered'`) ⇒ the quorum was satisfied by a
bot that filed nothing. `review-retrospective` independently returned **`verdict unmeasurable`**.

### Why this sharpens THIS plan specifically

This plan's staged defect is a **false alarm**: the shortfall disclosure derives its population from
every registry `author_login` and fires when any ROSTER member is silent, even when the REQUIRED
quorum is fully met. #1122 is the **mirror image on the same mechanism**:

⛔⛔ **If the disclosure treats `participated_but_empty` as participation, it reports FULL COVERAGE on
a PR where nothing was reviewed.** That is the *false-clean* direction, and it is **worse than the
false-alarm direction this plan was staged for** — a false alarm costs credibility, a false clean
costs the review.

⇒ **The deliverable must fix BOTH polarities in one pass.** A fix that only swaps the denominator
from roster to required set makes the false-clean half *worse*, because it removes the incidental
noise that was the only thing drawing attention to a thin review.

### One check ANSWERED by the orchestrator — do not re-derive it

The sender asked whether `rate_limited` is in the #1118 taxonomy or fell outside it.
✅ **It is IN the taxonomy.** Read first-party at
`automatic-review/scripts/review_completeness.py`: `STATE_REFUSED_AWAITABLE` (`:132`) and
`STATE_REFUSED_HARD` (`:133`), split by the refusing bot's registry `rate_limit_class` (`:237`,
`awaitable_window`). A rate-limited bot does **not** collapse into "did not participate" — the
taxonomy-collapse failure the sender feared is **not** present here.
⚠ So the residual question is **not** whether the state exists; it is whether the **disclosure**
consumes it, and whether an OPTIONAL bot's refusal should surface at all when the required quorum is
met. That is this plan's D-level question.

## ⛔⛔ ABSORBED 2026-08-09 — a THIRD and FOURTH instance, and the instrument that should have caught it is blind in the same way

Two sources, both first-party to their reporters, both the false-clean polarity this plan now owns.

### `code-intelligence-substrate-011` — PR #1127, measured across three passes

| Bot | Required? | Outcome (3 passes) | Findings |
|---|---|---|---|
| **pr-agent** | **REQUIRED** | `participated_but_empty` all three | **0** |
| coderabbit | optional | participated | **16 records, 14 actionable, 11 fixed, 0 rejected**, incl. 3 real Majors |
| sourcery | optional | `hard_quota` all three | never saw the diff |

**The barrier passed with `participation_complete: true`.** ⛔ The required-reviewer predicate is
satisfied by PARTICIPATION, and `participated_but_empty` **is** participation — so the gate went green
on the reviewer that contributed nothing, while the reviewer that found every defect is one the gate
does not require, and the third is one it structurally cannot reach at that diff size.

⭐ **The reporter's framing, which is the sharpest statement of the class this epic has:** *not a check
that was wrong — a check whose predicate is satisfiable without the thing it exists to establish.*

### `generic-charter-language-specific-defect-008` — PR #1130, the instrument is blind too

⛔⛔ **`review-retrospective` recorded `outcome: done`, `display_detail: "0 pr-comment findings —
nothing to compare"` on precisely the run where reviewer coverage collapsed to zero.** The
review-quality instrument reported a benign no-op in exactly the condition it exists to detect,
because its population is `pr-comment` findings and an empty population reads as *nothing to compare*
rather than *the comparison was impossible*.

⇒ **D2's publish-your-population rule extends to `review-retrospective` itself.** When zero
`pr-comment` findings exist it must distinguish *reviewers ran and found nothing* from *no reviewer
produced content*, and grade the latter **`indeterminate`** — never `done` with a benign summary. ⛔ It
must not mark itself complete on a comparison it could not perform.

⚠ **A recoverable refusal that is not awaited is a discarded opportunity.** On #1130 coderabbit was
`refused_awaitable` while `review_rate_window_await` was **off for that plan**, so the one refusal
convertible into real review content was dropped **silently by configuration**. That the option
existed appears only in the override's `granted_over` prose. Surface it.

### The consolidated deliverable this adds

**Surface `participated_but_empty` distinctly at the barrier**, so a green participation check resting
entirely on empty participation is visible as such rather than indistinguishable from a substantive
clean review. ⛔ **This explicitly does NOT justify dropping or demoting pr-agent** — both reporters
said so unprompted, and so does this orchestrator. The ask is to make the gate's information content
legible, never to re-rank bots.
⚠ **The required-vs-optional composition question needs a corpus and is NOT in this plan.** It belongs
in the cross-plan `audit-archived-plan-retrospectives` quality-chain view. Both sibling epics agree and
neither is staging for it. ⛔ Do not derive a per-reviewer rate from these instances: pooling a
rate-limited absence, a size-capped absence, a participation-with-zero-yield, and a
required-present-empty mis-attributes all four.

## Claim Labels

- **OBSERVED** (orchestrator, first-party at the 2026-08-08 drain): the population is roster-derived —
  read at `.claude/skills/cloud-plan-lane/SKILL.md` § "Record per-reviewer participation, from the
  bodies": *"Read the `author_login` of every such registry doc — that set **is** the expected reviewer
  population for this PR"*, parsed by `automatic-review/scripts/bot_registry.py`.
- **OBSERVED** (orchestrator, first-party at the drain): the disclosure fires on ANY roster member —
  read at the same file § "Step 8 — Merge gate" condition 4: *"When **any** expected reviewer's verdict
  is not `reviewed`, state the shortfall"*. Neither `required_bots` nor `optional_bots` appears in that
  condition.
- **OBSERVED** (orchestrator, first-party at the drain): this project's resolved config is
  `required_bots = pr-agent`, `optional_bots = coderabbit,sourcery`,
  `bot_lists_provenance = answered` — read via
  `manage-config plan phase-6-finalize step get --step-id plan-marshall:automatic-review`.
- **OBSERVED** (orchestrator, first-party at the drain): an optional bot's absence never blocks — read
  at `automatic-review/standards/bot-participation-contract.md`:20 (region), *"An **optional** bot
  resolving to any member never blocks"*, and line 59's `refused_hard` disposition, *"whether the
  absence is tolerable is a required-vs-optional question, not a waiting question."*
- **HYPOTHESIS** (message-supplied, verify-at-outline): that the four landings the sender recomputed
  (#1107, #1112, #1117, #1113) each met their required quorum at 1 of 1. Confirm/refute artifact: the
  stored comment bodies per PR via `ci pr comments --pr-number N`, matched against
  `required_bots = pr-agent`. ⛔ **Do not inherit the sender's recomputation** — it is the same
  message that had to retract two of its own claims; corroborate before any figure derived from it is
  published.
- **HYPOTHESIS** (asserted absence, verify-at-outline): that NO other emitted coverage figure reads the
  roster as its denominator. Confirm/refute artifact: every emission site of a coverage ratio — the
  Step 8 disclosure, the § Report participation table, and the run-report coverage line. ⛔ **This is
  the higher-risk half of the verify-first contract**: an unverified absence here ships a fix that
  corrects one emitter while its siblings keep publishing the wrong denominator — precisely the
  scope-of-sweep ≠ scope-of-claim failure PLAN-PR-018 exists to close. **Publish `scope_searched` and
  `files_scanned` with the absence claim.**
- **Verify-first clause**: the sender asserts a "false-alarm generator". Settle at outline whether the
  disclosure has actually fired a false shortfall on a real run, or whether the defect is so far only
  derivable from the code. ⛔ **If no instance is found, that does not refute the finding** — the code
  path is OBSERVED — but the spec must then say so plainly rather than carrying an implied incident
  count of zero as though it were evidence of impact.

## Expected Surface

- **OBSERVED**: `.claude/skills/cloud-plan-lane/SKILL.md` § "Record per-reviewer participation" and
  § "Step 8 — Merge gate" condition 4 — the population read and the shortfall verdict.
- **OBSERVED**: `.claude/skills/cloud-plan-lane/SKILL.md` § Report — the coverage line that states
  N-of-M.
- **HYPOTHESIS** (verify-at-outline): `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py`
  — read-only here; the roster parse is CORRECT and is not the thing being changed.
- **HYPOTHESIS** (verify-at-outline): whichever site resolves `required_bots` / `optional_bots` from
  the step config, if D1 needs a resolver the lane does not already have. ⚠ **The cloud-plan-lane
  runs without the generated executor** (see `CLAUDE.md` § Standalone Plan Lane) — so a fix that
  reaches the config through `manage-config` would be inert in the lane it is fixing. Settle the
  read mechanism at outline before scoping D3.

## Dependencies and Sequencing

- **Depends on**: none. The surface is disjoint from the participation classifier (WS-01) and from
  `branch-cleanup.md` / the merge path (WS-04).
- **Overlaps with**: ⚠ **PLAN-PR-006**, on the required-vs-optional denominator question. PR-006 owns
  the ABSENCE-CAUSE partition (why a bot did not review); this plan owns the DENOMINATOR (whose absence
  counts). Related but genuinely different axes — ⛔ if outline finds they converge on one mechanism,
  say so rather than shipping two.
- **Overlaps with**: `truthful-signals` PLAN-TRUTH-061 (#1112) shipped the surface this plan corrects.
  Read its landing before scoping; this is a correction to shipped work, not a rediscovery of it.
- **Adjacent to**: `PLAN-PR-004` (pr-agent charter). Both concern the required bot — that one its
  output quality, this one its accounting. Untouched here.

## ⚠ Carried lead, NOT part of this plan's scope

The same contract states that `required_bots` **defaults to the empty string**, and that an empty
`required_bots` therefore means the quorum is **vacuously satisfied**. This project has answered the
question (`bot_lists_provenance: answered`), so it is unaffected — but any project that has NOT is
running a vacuously-satisfied review quorum by default. ⛔ **Unverified beyond this repo — a lead, not
a finding.** D3 makes the vacuous case *visible* where it occurs; auditing other repos for it is
separate work and belongs to whoever owns those repos.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-021-coverage-shortfall-disclosed-against-the-roster-not-the-required-set.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
