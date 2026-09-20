<!-- ⛔ RETIRED 2026-09-12 — ABSORBED INTO `PLAN-CIS-050`, NOT ABANDONED.

This spec is no longer emittable and its queue row is off the staged list. All four deliverables
survive inside `plans/PLAN-CIS-050-measurement-and-cost-integrity.md`:

  D0 (population gate)                 -> PLAN-CIS-050 D8
  D1 (PLAN-CIS-014 reduction half)     -> PLAN-CIS-050 D9
  D2 (PLAN-CIS-035 finding-yield)      -> PLAN-CIS-050 D10
  D3 (CIS-022 open ends + CIS-018)     -> PLAN-CIS-050 D11

⛔ THIS SPEC WAS THE EPIC'S SOLE EMITTABLE CANDIDATE when it was retired. The operator was told that
and chose the merge anyway (AskUserQuestion, 2026-09-12, "Merge it anyway"). It is recorded here so
no later reader mistakes the retirement for an oversight.

Why the merge is the right shape rather than merely a larger one: this spec's D1 and D2 were written
to report AROUND two defects — the total_tokens fabricated zero and the 1-vs-3 decimal rounding
split — precisely because those fixes lived in PLAN-CIS-050, which had not landed. Merging turns an
unpredictable cross-plan landing order into a within-plan instruction: fix the instruments (D1-D7),
then measure through them (D8-D11). Claim 4 below, which encoded that dependency, is DISSOLVED by
the merge rather than re-stamped.

The claim verdicts below (five corroborated, one contradicted/rescoped:yes) are left verbatim as the
record. Do not re-stamp them, and do not resurrect this file.
-->

# PLAN-CIS-057: The measurement residue a local corpus unblocks

epic: code-intelligence-substrate
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Authored by the orchestrator on 2026-08-22 during the landed-corpus ingest, because the
> 2026-08 cloud wave left this work uncovered. See § Provenance.

## Objective

Six of the plans that landed in the 2026-08 cloud wave shipped their git-derivable half and left a
measurement half explicitly blocked, every one of them on the same cause: **the archived-plan corpus
is git-ignored, so a fresh cloud clone cannot see it.** Each deferral was correct and each was
disclosed. But the corpus is not missing — **it is on this machine**, and none of those deliverables
has an owner, because the `5xx` remediation wave discharges audit gaps rather than blocked work.

This plan collects that residue and discharges it in one local run. It is deliberately a *sweep of
named leftovers*, not a new investigation: every item below already has a plan, a deliverable id,
and a stated Done-when. What it lacked was a machine that could see the data.

## Deliverables

⚠ **RE-SCOPE ALREADY TRIGGERED — 2026-08-24 `cleanup` re-grounding pass. Do not re-decide this at
outline.** § Claim Labels claim 4 assumed `PLAN-CIS-050` would have landed its fabricated-zero and
rounding fixes before this plan runs. Checked at HEAD `b95d78437`: **it has not.** `PLAN-CIS-050` is
`staged` with no PR and no landing, sitting fifth in the staged order, so those fixes are absent from
`main`. ⇒ **The branch this spec pre-authorised fires: D1 and D2 report AROUND the fabricated-zero
and rounding defects, not through them.** The verdict is stamped on the claim itself
(`verdict: contradicted`, `rescoped: yes`). ⭐ If `PLAN-CIS-050` lands before this plan starts,
re-check the claim rather than assuming either branch — the verdict carries its `checked_at` sha for
exactly that comparison.

⭐ **D0's population gate is pre-answered as non-empty** (claim 3, corroborated): 13 archived plans
under `.plan/local/archived-plans/` carry the exploration field set. That settles *existence*, not
per-deliverable sufficiency — D0 still publishes the count, date range and field presence, and each
deliverable still applies its own minimum.

Four deliverables, each discharging a named residue item.

1. **D0 — Population gate (gating).** Publish the archived-plan corpus reachable from this checkout —
   count, date range, and which of the fields the deliverables below depend on are actually present.
   ⛔ **Each deliverable below states its own minimum population; if D0 cannot meet one, that
   deliverable reports `unmeasured` with the count, and the plan continues.** A partial discharge
   that names what it could not reach is the correct outcome; a fabricated figure is not.

2. **D1 — `PLAN-CIS-014`'s reduction half.** Its D1(b) (which path is reducible), D3 (the reduction
   itself) and D4(b) (its delivery test) are undischarged and **no successor plan names the two hot
   paths**. Identify them from the corpus, make the reduction, and pin it. ⚠ Two high-severity
   defects in that plan's own shipped roll-up must be treated as **input, not as tooling to trust**:
   the published denominator rounds a sub-second corpus to `0.0s`, and the per-plan reader has no
   line-shape guard, so a failed script's captured `stdout:` continuation can manufacture a call
   that never ran. **Fixing those two belongs to `PLAN-CIS-050`** — this plan must not scope on the
   roll-up's numbers until it has confirmed which of the two fixes has landed, and must say which.

3. **D2 — `PLAN-CIS-035`'s finding-yield sweep.** Its D3 and D4 (the per-class shares of dispatch
   spend) halted on the corpus. Run them. ⛔ **Do NOT restore the retired "a third of finalize spend"
   figure** — it is retired, and the run that retired it did so correctly. ⛔ And do not aggregate
   over `total_tokens` until confirming whether that column's fabricated-zero default (that plan's
   G1) has been fixed by `PLAN-CIS-050`; if it has not, the sweep must exclude or separately report
   the rows that default it.

4. **D3 — `PLAN-CIS-022`'s two open ends, and `PLAN-CIS-018`'s blocked count.** Three named items,
   one window:
   - `reconcile-ledgers` **has zero workflow call sites** — the plan's Goal is reached only in
     principle. Wire it, or record with evidence why it should stay uncalled. ⚠ A `RecursionError`
     cliff at roughly 1000 same-timestamp rows per phase is **contained only by the absence of a
     caller** — wiring it without addressing that cliff moves a latent defect into a live path.
   - That plan's D3 Done-when was verified only store→render; **the reverse walk (render→store),
     which is its literal requirement, was never performed.** Perform it.
   - `PLAN-CIS-018`'s D4 population count of affected historical rows was correctly blocked and
     shipped a documented-rule fallback instead. Derive the count.

**Split verdict:** four deliverables against three source plans. They share D0's corpus read and
nothing else, so the alternative is three plans each re-running the same gate. Proceeding unsplit is
deliberate and recorded here.

## Claim Labels

- **OBSERVED**: every item above is a residue explicitly declared by its own run and independently
  confirmed still open by that run's audit. Per-item evidence is archived under
  `cloud-runs/{270,070,340,310}-*/` and summarised in the corresponding `landings/PLAN-CIS-*.md`.
  - verdict: corroborated | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: Re-derived at HEAD: all four named archive directories exist under cloud-runs/ - 270-aggregate-cost-invisible-to-per-call-ceiling, 070-dispatch-spend-on-dispatches-that-produced-nothing, 340-token-ledgers-disagree-and-the-smallest-is-named-actual, 310-main-sha-records-the-pinned-cwd. Each residue item's evidence is reachable where the spec says it is.
- **OBSERVED**: `reconcile-ledgers` has zero workflow call sites — `PLAN-CIS-022` audit G4.
  - verdict: corroborated | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: Re-derived at HEAD with a stated population: architecture search --content for reconcile-ledgers and reconcile_ledgers resolves ONLY to manage-metrics.py (implementation plus argparse wiring), its own SKILL.md documentation, and three test files under test/plan-marshall/manage-metrics/. Zero phase, workflow or SKILL call sites outside manage-metrics itself. The verb is still unreachable from any workflow.
- **OBSERVED**: `PLAN-CIS-014`'s roll-up denominator rounds to `0.0s` on a sub-second corpus, and its
  per-plan reader manufactured a 9.99 s call from a failing script's `stdout:` line — both reproduced
  by execution during the audit.
  - verdict: corroborated | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: UPGRADED from the prior unverifiable, and the upgrade is the point: both defects are confirmable by SOURCE READ, not only by execution. audit.py:3228 still rounds total_seconds to 1 decimal while rollup_total at :3184 rounds to 3, and audit.py's own comment at :3161-3176 documents that 0.0s-denominator mismatch as known and unfixed. analyze-logs.py:408-427 extract_script_durations still applies _DURATION_RE/_NOTATION_RE to EVERY line with no header-line gate, matching G14 verbatim, and no test guards a stdout continuation line. Both live.
- **HYPOTHESIS**: the local corpus carries enough archived plans with the required fields to
  discharge D1, D2 and D3 — confirm/refute at D0 (verify-at-outline). **This is the plan's gating
  risk**, and a partial discharge is an acceptable outcome.
  - verdict: corroborated | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: Re-counted directly at HEAD, because the crawled inventory does not cover the gitignored .plan/local/ tree: an os.walk over .plan/local/archived-plans/ finds exploration_index_answerable_bytes in 35 work/metrics.toon files, up from the spec-cited 13. The gating hypothesis clears by a wider margin than stated. ⛔ The cited count of 13 is STALE - re-derive at outline, do not carry it forward.
- **HYPOTHESIS**: `PLAN-CIS-050` has landed the fabricated-zero and rounding fixes before this plan
  runs — confirm/refute at outline (verify-at-outline). **If it has not, D1 and D2 re-scope to
  report around those defects rather than through them.**
  - verdict: contradicted | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: yes | evidence: REFUTED at HEAD: the status.json row for PLAN-CIS-050 reads status staged with empty pr and empty landing, so it has NOT landed and its fabricated-zero and rounding fixes are not in the tree. The refutation is ALREADY ABSORBED by the spec as written - D1/D2 carry a pre-authorised re-scope-around-the-defects branch for exactly this case, and that branch now fires. rescoped yes, because the spec anticipated this state rather than needing amendment for it.
- **Verify-first clause:** re-derive at outline that each residue item is still open. Any item
  closed since 2026-08-22 is struck, not re-implemented.
  - verdict: corroborated | checked_at: 28b578f1ed435973e53c510f0c8225446cc024aa | by: code-intelligence-substrate/cleanup | rescoped: n/a | evidence: The verify-first clause was discharged by INDEPENDENT re-derivation rather than by the now-stale git-log-touched-paths heuristic - #1342, #1359 and #1370 all touched plan-retrospective and manage-metrics without closing any named item. Item by item: reconcile-ledgers still has 0 call sites (claim 1); CIS-014's G1 and G14 defects are still present in source (claim 2); PLAN-CIS-050 is still staged (claim 4). No named residue item has closed.

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

- **HYPOTHESIS**: `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py`
  — `reconcile-ledgers` and its caller (verify-at-outline)
- **HYPOTHESIS**: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py`
  — the per-class dispatch-spend sweep (verify-at-outline)
- **HYPOTHESIS**: `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/_ledger_reconciliation.py`
  — the reverse render→store walk (verify-at-outline)
- **HYPOTHESIS**: the phase-handshake capture surface for `PLAN-CIS-018`'s D4 count
  (verify-at-outline). ⚠ That plan's D4 rule as shipped **instructs a direct `.plan/` file read**,
  which violates the repo's standing scripts-only access rule; `phase_handshake list` already
  projects what is needed. **Correct the rule while discharging it** — do not follow it as written.
- Test surface: each deliverable's own tests, each with a matched negative control.

⛔ **Surface collision warning.** `manage-metrics.py` and `analyze-logs.py` are both contended with
`PLAN-CIS-050`. **These two plans may not be emitted together.**

## Dependencies and Sequencing

- **Depends on**: nothing hard. ⭐ **Strongly prefers `PLAN-CIS-050` to land first** — that plan fixes
  the fabricated zeros and the rounding defect that D1 and D2 would otherwise measure through. This
  is a preference, not a prerequisite: the claim labels above make both orders workable, and the
  plan reports which order it ran in.
- **Overlaps with**: `PLAN-CIS-050` on `manage-metrics.py` and `analyze-logs.py` — mutually exclusive
  for emission.
- **Adjacent to**: `PLAN-CIS-056`, which owns the headline exploration/residency measurement. Same
  corpus, different files, different question. The two are separable and may be sequenced either way.

## Provenance

Authored 2026-08-22 by the orchestrator during the landed-corpus ingest. It exists because the `5xx`
wave discharges the audit's gaps and **nothing discharges the deliverables the cloud lane could not
reach.** The pattern is worth recording in its own right: the cloud lane's structural blind spot is
the git-ignored corpus, and every plan that hit it deferred correctly and identically. That is a
*lane* property, not a per-plan failure — see `epic.md` § Structural Findings.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-057-corpus-blocked-measurement-residue.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message —
the orchestrator owns every other ledger write — and reports its outcome through its PR and its
inbox message.
