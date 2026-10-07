<!-- ⛔ RETIRED 2026-09-12 — ABSORBED INTO `PLAN-CIS-054`, NOT ABANDONED.

This spec is no longer emittable and its queue row is off the staged list. All five deliverables
survive inside `plans/PLAN-CIS-054-documentation-surface-truthfulness.md`:

  D0 (population gate)                  -> PLAN-CIS-054 D7
  D1 (per-phase sub-source aggregator)  -> PLAN-CIS-054 D8
  D3 (settle/refute the split)          -> PLAN-CIS-054 D9
  D4 (settle/refute the re-read multiple) -> PLAN-CIS-054 D10
  D2 (re-scope the residency instrument) -> PLAN-CIS-054 D11, deliberately ordered last

Reason for the merge (operator direction, 2026-09-12): larger plans, ceiling twelve deliverables,
grouped by shared target. The pairing is CAUSAL: PLAN-CIS-054 corrects documents that state figures;
this spec SETTLES those figures. Split apart, every figure this measurement moved would leave a
stale sentence standing in a document the other plan owns until that plan ran - which is the drift
class PLAN-CIS-054 exists to close, reproduced by its own scheduling.

⚠ D0's population gate is the SAME gate PLAN-CIS-050 D8 runs over the same git-ignored
.plan/local/archived-plans/ tree. Both merged specs now carry a must-not-diverge rule: whichever
runs second cites the first's published population rather than deriving a second one.

⚠ This spec was NOT prep-blocked - all seven of its claims were corroborated. It was blocked on a
SURFACE collision with live PR #1398 on audit.py, which the merge does not dissolve; PLAN-CIS-054
inherits it. Do not read the retirement as a verdict on this spec's quality.

The claim verdicts below are left verbatim as the record. Do not re-stamp them, and do not
resurrect this file.
-->

# PLAN-CIS-056: The exploration split becomes measurable

epic: code-intelligence-substrate
workstream: WS-06

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Authored by the orchestrator on 2026-08-22 during the landed-corpus ingest, because the
> 2026-08 cloud wave left this work uncovered. See § Provenance.

## Objective

⭐⭐ **THE n=1 PREMISE IS NOW OUT OF DATE — folded in 2026-08-24 from inbox `truthful-signals-046`.
A SECOND INDEPENDENT MEASUREMENT EXISTS.** Read this before the paragraph below, which still says
"n=1 since it was first observed" and is preserved as the plan's original framing.

Source: the run report of plan `fix-provider-abstraction-mismatch`, a **different plan on a different
machine**, PR #1332 (`be2a030e9`) with follow-on #1335 (`51ff9e59e`) — both landings verified
first-party against `origin/main` by the sending orchestrator. Within finalize's **3,310,715
exploration result bytes**:

| Bucket | Bytes | Share | This epic's figure |
|---|---|---|---|
| `exploration_index_answerable_bytes` | 678,109 | **20.5 %** | ≈15.9 % — **DISAGREES** |
| `exploration_doc_residency_bytes` | 2,158,790 | **65.2 %** | ≈65.2 % — **AGREES to the decimal** |

⭐ **Doc-residency lands on 65.2 % again, on a different plan and a different machine.** That is the
larger bucket and the one WS-06's reasoning rests on. Index-answerable disagrees (20.5 % vs 15.9 %),
and **the disagreement is as informative as the agreement** — D3/D4 must report both, not average them.

⛔ **THREE CAVEATS THAT ARE NOT DECORATION, and D0 must carry them into how it reports:**
1. ⛔⛔ **45.3 % of that finalize `cache_read` is UNATTRIBUTED** (332,987,179 of 733M). The class shares
   are computed over a population **whose largest single member is "unknown"**. Whatever the attributed
   shares mean, they do not describe half the bytes. ⛔ Do not quote a class share from this data point
   without its unattributed remainder beside it.
2. ⚠ **The exploration buckets are a share OF EXPLORATION RESULT BYTES, not of billing.** The sender's
   three-population discipline holds (dispatched 6,365,935 · inline main-context 22,990,033 ·
   billing-weighted 133,692,078, never summed), so the figures are internally consistent — but the two
   denominators are different questions and must not be crossed.
3. ⛔ **NOT REPRODUCED. This is a SECOND DATA POINT, not a confirmation** — the sender states plainly
   that it re-derived none of these figures; they are that machine's ledger. **The distinction is the
   whole value: do not collapse it.** n is now 2, and 2 is still small.

⇒ **This plan's D0 gate does not change**, but its framing does: it is no longer building the first
measurement, it is building the instrument that lets this epic **reconcile two existing ones** and say
which bucket replicates. The local corpus (13 archived plans carrying the field set, corroborated by
the 2026-08-24 re-grounding pass) is the third.

---

The epic's headline result — that roughly half of every tool-result byte is plan-marshall reading
its own skills, standards and workflow docs — has been **n=1 since it was first observed**, and the
plan staged to settle it (`PLAN-CIS-036`) halted at its D0 gate because no corpus was reachable in a
cloud clone. That halt was correct. **Its hand-off was not**: the run reported, in four places, that
*nothing needs building, only the corpus needs to be present*, and its own audit proved that false.
No instrument exists anywhere in the retrospective auditor that reads the three exploration
sub-source fields the split is defined over; the nearest existing check pools all six phases into
one figure, which is exactly what the measurement forbids.

This plan builds the missing instrument — **which needs no corpus and could have been built in the
cloud** — and then runs the measurement over the local corpus, which this machine has and a cloud
clone does not. It ends with the headline figures either **settled over a stated population** or
**refuted**, and never again quotable as n=1.

## Deliverables

Five deliverables.

1. **D0 — Population gate (gating; this one can halt the plan).** Before any other work, derive and
   publish the corpus actually reachable from this checkout: how many archived plans carry a
   `metrics.toon`, how many of those carry per-phase exploration sub-source fields, and at which
   schema version. **Publish the count with the command that produced it.** If the population is
   smaller than the schema change that introduced the sub-source fields allows, say so and report
   what the measurement can and cannot answer at that n — do not proceed to D3/D4 on a population
   that cannot support them. ⛔ A figure without its denominator is the defect this whole epic
   exists to remove; it is not permitted in this plan's own output.

2. **D1 — The per-phase exploration sub-source aggregator.** Build the check that reads
   `index_answerable`, `doc_residency` and `unattributed` **per phase** and reports the split with
   its population. This is the instrument `PLAN-CIS-036`'s report claimed already existed. It is
   git-derivable and depends on no corpus. Requirements carried from that plan's audit (its G3, G4
   and G7): the aggregator MUST NOT pool phases into one figure; it MUST apply the schema-partiality
   read, so a phase whose fields are absent reports `unmeasured` rather than a zero; and it MUST
   apply the re-entry guard, so a re-entered phase is not double-counted.

3. **D2 — Re-scope the residency instrument, and say what it can answer.** `PLAN-CIS-039`'s D1 rests
   on `exploration_doc_residency_bytes`, which is **a one-integer-per-phase proxy, not a per-document
   consumption measure**. Establish from source what question that field can actually answer, and
   either name the instrument that answers the per-document question or record that none exists and
   what it would take. ⛔ Do NOT re-run `PLAN-CIS-039` as written — re-running it would measure the
   wrong thing with a clean conscience.

4. **D3 — Settle or refute the exploration split.** Run D1's aggregator over D0's population and
   publish `index_answerable` / `doc_residency` / `unattributed` shares, plus exploration's share of
   tool-result bytes, **each with its population**. Compare against the standing n=1 observations
   (index-answerable 15.9%, doc-residency 65.2%, exploration ≈77%) and state, per figure, whether it
   is confirmed, moved, or refuted. ⚠ The one prior partial result already contradicts the epic's
   assumption: `2-refine` measured as the worst phase (3.3% index-answerable / 90.7% doc-residency),
   not `6-finalize`. Expect the ranking to move.

5. **D4 — Settle or refute the re-read multiple.** `PLAN-CIS-040` shipped the currency correction and
   **deliberately deleted** §6's numeric figures rather than restating them, leaving the
   resident-context-times-turns model confirmed but its multiple unmeasured. Publish
   `resident_context` and `turns` per phase over D0's population and derive the re-read multiple,
   stating whether the standing 44.6x and the `cost(byte) ≈ 1.25 + 0.1 × turns_remaining` form hold.
   ⛔ The **model** is already confirmed and independently re-derived twice — do not re-litigate it.
   Only the multiple is open.

**Split verdict:** five deliverables, below the ~6 threshold. D3 and D4 are separable in principle,
but both consume D0's population and D1's aggregator, and splitting them would run the same gate
twice. Proceeding unsplit is deliberate and recorded here.

## Claim Labels

- **OBSERVED**: no check in the retrospective auditor reads the three exploration sub-source fields —
  content search for `index_answerable` / `doc_residency` under
  `.claude/skills/audit-archived-plan-retrospectives/` returned **0 matches** against a control of 33
  matches elsewhere. Established by `PLAN-CIS-036`'s audit; archived at
  `cloud-runs/080-exploration-split-measured-on-one-phase-and-it-is-the-worst-case/verification.md`.
  - verdict: corroborated | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: Re-derived at HEAD over a stated population: full-text scan of audit.py (9910 lines) returns zero hits for index_answerable or doc_residency. The adjacent exploration-share check (CHECK_ERA #1043, _parse_exploration_counters at audit.py:7192) sums exploration_tool_calls/result_bytes per phase into ONE corpus figure - a different split (exploration vs work/execute/orchestration/unclassified), not the three sub-source fields. PR #1342 touched audit.py inside the window but added no such reader.
- **OBSERVED**: `PLAN-CIS-036` halted at D0 with 0 of 5 deliverables and merged as PR #1178 — see
  `landings/PLAN-CIS-036.md`.
  - verdict: corroborated | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: Corroborated from the landing record: landings/PLAN-CIS-036.md carries pr 1178, merge_commit dd0b70b10, and an Outcome line reading blocked - 0 of 5 deliverables - halted at D0. PR 1178 is independently confirmed present in main's commit history.
- **OBSERVED**: `exploration_doc_residency_bytes` is one integer per phase, not a per-document
  measure — established by `PLAN-CIS-039`'s audit (G1/G2), archived at
  `cloud-runs/020-corpus-residency-admission-control/gaps.md`.
  - verdict: corroborated | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: Re-derived at HEAD: manage-metrics/standards/data-format.md:163 types exploration_doc_residency_bytes as a single int populated by the enrich tool-call walk; :184 states the partition invariant against exploration_index_answerable_bytes and exploration_unattributed_bytes. No per-document breakdown field exists anywhere in the schema at this sha.
- **OBSERVED**: the cost model (`creation_multiplier + read_multiplier × turns_remaining`, 1.25x /
  0.1x) maps onto the published billing weights and was independently re-derived from
  `manage-metrics/standards/data-format.md` in two separate audits.
  - verdict: corroborated | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: Re-derived at HEAD: data-format.md:227 sets cache_read_input_tokens weight 0.1 and :228 cache_creation_input_tokens weight 1.25; :48 and :144 both define billing_weighted_total as input + output + round(0.1*cache_read) + round(1.25*cache_creation). #1342 touched this file for unrelated dispatch-boundary text without altering the constants.
- **HYPOTHESIS**: the local archived-plan corpus is large enough to move the headline figures off
  n=1 — confirm/refute at D0 (verify-at-outline). **This is the plan's gating risk.** If the local
  population is also thin, D3/D4 report what they can and the plan says so rather than publishing a
  figure its population cannot carry.
  - verdict: corroborated | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: Corroborated and STRENGTHENED, but the spec's cited count is now stale: the archived-plan corpus has grown from 13 dirs to 36, of which 35 carry exploration_index_answerable_bytes in work/metrics.toon (the one miss, 2026-08-25-plugin-doctor-detector-coverage-residue, has no metrics.toon at all). n=35 clears n=1 by a wide margin. ⛔ Do NOT carry the 13-of-13 figure forward - re-derive at outline.
- **HYPOTHESIS**: the schema-partiality read and the re-entry guard both already exist as reusable
  helpers and D1 can compose them rather than re-implement — confirm/refute in `manage-metrics` and
  `plan-retrospective` at outline (verify-at-outline).
  - verdict: corroborated | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: Re-derived at HEAD with the prior caveat intact: _boundary_measure_is_partial is present at manage-metrics.py:565 and the file was untouched across 91a07aaa4..HEAD. The re-entry half is NOT a callable guard but field-level close_count semantics - increment at :826-833, read/compare at :854-859, :1230, :1320, :1462-1485, :1660, :2143-2157, :2830 - so the claim overstates the reusable-helper framing for that half.
- **Verify-first clause:** re-derive at outline that no aggregator has been built since 2026-08-22.
  If one has, this plan re-scopes to *complete and correct it* rather than to build it.
  - verdict: corroborated | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: The verify-first clause discharged as a checked NEGATIVE, not silence. The flagged live plan DID land - PR #1342 / 91bbe7470 on 2026-08-24, touching exactly the audit.py + analyze-logs.py + data-format.md set the risk note named - but its 28-file diff covers build_share, the suspect-zero census and dispatch-boundary column-by-name resolution only; no index_answerable/doc_residency/unattributed aggregator. git log over 91a07aaa4..HEAD across manage-metrics.py, plan-retrospective and audit.py shows no other candidate commit.

## ⛔⛔ Cross-epic constraint on the corpus this plan measures (inbox `truthful-signals-042`, drained 2026-08-22)

**The pre-change archived corpus reports a FABRICATED ZERO that nothing on disk distinguishes from a
measurement.** `truthful-signals` established this first-party, by symbol, and it binds every D0
population gate below.

- `plan-retrospective/scripts/analyze-logs.py:597` keeps a correct `len(parts) < 5` floor, and the
  per-column rescue at `:616-621` marks a column `unmeasured` **only when it is ABSENT**.
- A nine-column **pre-change** row has all four appended cells **present, holding a literal `0`**, so
  `int('0')` succeeds ⇒ **measured zero**. The rescue never fires, because nothing is missing.
- ⛔ **The blast radius is TOTAL, not partial**: those four per-dispatch context-load columns were
  declared, wired, and zero on **every** pre-change row. **The entire pre-change archived corpus
  consists of exactly the rows this mis-reads.**

> **A three-state vocabulary cannot recover a distinction the two-state writer already destroyed.**

**What this means for this plan, concretely:**

1. **The honest population is runs from PR #1129 forward, not the whole archive.** D0 MUST partition
   its count by that boundary and publish both numbers. A D0 that reports one large corpus figure has
   already made the error this epic exists to detect.
2. ⛔ **A pre-change row's `0` MUST NOT be read as a measurement** — not aggregated, not averaged, not
   included in a denominator. If the post-#1129 population is too small to carry a figure, **that is
   the finding**, and it is reported as such rather than padded with historical rows.
3. **Recovery of the historical corpus is NOT this plan's work.** It is `truthful-signals`'
   `PLAN-TRUTH-077`, whose D2 adds a fourth state, `indeterminate`, explicitly not collapsed into
   `unmeasured`. ⚠ That plan's own D0 may find **there is no provenance discriminator at all**, in
   which case the historical figures are **permanently indeterminate rather than recoverable**.
   ⛔ **Do not wait for it, and do not stage a CIS-side version of it** — ownership is theirs and
   nothing is owed back.

## Expected Surface

- **HYPOTHESIS**: `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` — the new
  per-phase sub-source check (verify-at-outline)
- **HYPOTHESIS**: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py`
  — the pooled check that must not be the answer (verify-at-outline)
- **HYPOTHESIS**: `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py`
  — the sub-source field readers (verify-at-outline)
- **HYPOTHESIS**: `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md`
  — the schema the partiality read is derived from (verify-at-outline)
- **OBSERVED**: `doc/concepts/token-management.adoc` — where a settled figure is published
- Test surface: the aggregator's own tests, which **must include a matched negative control** — a
  phase with the fields absent must report `unmeasured`, and that assertion must fail if the
  partiality read is removed.

⛔ **Surface collision warning.** `audit.py` is contended: `PLAN-CIS-050`, `PLAN-CIS-051` and
`PLAN-CIS-053` all touch it, and the audit's own constraint is that they must not run concurrently
against it. **This plan is subject to the same constraint** — it may not be emitted alongside any of
those three.

## Dependencies and Sequencing

- **Depends on**: none. D1 needs no corpus and no sibling plan.
- **Overlaps with**: `PLAN-CIS-050`, `PLAN-CIS-051`, `PLAN-CIS-053` on `audit.py` — mutually
  exclusive for emission.
- **Adjacent to**: `PLAN-CIS-057`, which discharges the *other* corpus-blocked deliverables. The two
  are deliberately separate: this plan owns the headline question, that one owns the residue. They
  share the corpus but not a file.
- **Unblocks**: `PLAN-CIS-039` (parked) and the blocked deliverables of `PLAN-CIS-040`. Neither may
  be re-emitted until D2 has said what instrument answers their question.

## Provenance

Authored 2026-08-22 by the orchestrator during the landed-corpus ingest. It exists because **no `5xx`
fix plan covers this work**: that wave discharges the audit's 473 gaps against the substrate's own
correctness, while this plan discharges the measurement the epic was created to make. The distinction
is deliberate — see `epic.md` § Open Decisions.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-056-exploration-split-becomes-measurable.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message —
the orchestrator owns every other ledger write — and reports its outcome through its PR and its
inbox message.
