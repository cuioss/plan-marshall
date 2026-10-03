# PLAN-PRQ-01: The quality chain has no score, and an assessment is graded at report time

> ⛔⛔ **SUPERSEDED BY PM-MCP (2026-09-26, operator decision; row status `parked`).** `plan-marshall-mcp` replaces both the
> process prose and the Python scripts this plan edits, so implementing it here is legacy work. Its
> implementation-independent content (rules, invariants, classifications, data, fixtures) was extracted to
> `plan-marshall-mcp/doc/known-defects/post-run-quality-carry-over.md` as PM-MCP input.
> **Do NOT emit; un-park only by explicit operator decision.** The spec body below stays intact as the evidence chain.

epic: post-run-quality
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

## Provenance

**TRANSFERRED 2026-09-17 from `truthful-signals` PLAN-TRUTH-152**, which is itself the merge of
PLAN-TRUTH-123 (the quality chain) and PLAN-TRUTH-130 (assessments graded at report time). The source
spec and both of its superseded sources stay on disk in that epic as the audit record and are the
authority for every carried claim:

- `.plan/archived-orchestrators/truthful-signals-26-09-21/plans/PLAN-TRUTH-152-the-retrospective-quality-chain-and-assessments-graded-at-report-time.md`
- `.plan/archived-orchestrators/truthful-signals-26-09-21/plans/PLAN-TRUTH-123-the-quality-chain-has-no-score-and-a-disabled-gate-is-indistinguishable-from-a-clean-one.md`
- `.plan/archived-orchestrators/truthful-signals-26-09-21/plans/PLAN-TRUTH-130-an-assessment-is-read-at-report-time-and-grades-a-correct-action-as-a-violation.md`

The source row is retired in `truthful-signals-26-09-21` (now `transferred` — the earlier `parked`
workaround note above no longer applies; `queue --transition` accepts `transferred` in the settled status
vocabulary) with a pointer here.

⛔ **RE-GROUNDED 2026-09-22 (cleanup, `checked_at: 7d82d5d90`).** The three paths above were corrected
from `.plan/local/orchestrator/truthful-signals/plans/…` — dead at HEAD since the 7d82d5d90 live/archived
epic-store split relocated `truthful-signals-26-09-21` (a CLOSED epic) to `archived-orchestrators/`. The
`## Claim Labels` section's own re-derivation instruction was unexecutable against the stale paths;
`orchestrator corpus read --slug truthful-signals --plan PLAN-TRUTH-123|-130|-152` all return
`spec_not_found` because the epic is `truthful-signals-26-09-21`, not `truthful-signals`. D0 cannot execute
against the source epic's live queue without the corrected slug either.

## Objective

**The post-run quality chain produces a verdict with no score and no stated basis, so a gate that was
DISABLED is indistinguishable from one that ran and found nothing — and an assessment recorded at outline
is graded at report time against a tree that has moved since, so a correct action is reported as a
violation.** Both halves are the same failure at different tiers: a judgement published without the state
it was computed against.

## Deliverables

11 deliverables carried from the source spec, within the epic's operator-set ceiling of 12. **D0 is a
gate: nothing downstream starts until every carried claim is re-grounded at HEAD** — the sources were
authored before PR #1488, #1494 and #1501 landed in this area.

1. **D0 — GATE: re-ground at HEAD; derive the mechanism population, settle the disposition→point mapping
   against the real corpus, and enumerate every surface that grades a recorded action against a mutable
   stored judgement.** Publish each population and its size. ⛔ **CORRECTED 2026-09-21 (cleanup,
   `checked_at: e8a71650`)**: this D0 diverged from the source (`PLAN-TRUTH-152`) at transfer — the
   source's exact wording for the enumeration target ("enumerate every surface that grades a recorded
   action against a mutable stored judgement") is restored above, replacing the transfer's shortened
   "grades an assessment". The "publish each population and its size" sentence was NOT in the source; it
   is KEPT here as a deliberate epic-level addition (matching this epic's own standing population-derived
   discipline), not silently dropped — but it is now labelled as an addition rather than inherited
   silently from the transfer.
2. **D1 — The coordinator: ONE script, one entry point, two consumers.**
3. **D2 — The scoring core: signal presence first, yield second, and the two are NEVER folded into one
   number.** Folding them is what makes a disabled gate read like a clean one.
4. **D3 — Consumer 1: the corpus quality report, and the first run's README complement.**
5. **D4 — Consumer 2: augment the per-plan `plan-retrospective` output.**
6. **D5 — An assessment carries an effective-from instant, and the report joins on it.**
7. **D6 — Supersession is recorded, not overwritten.**
8. **D7 — An operator override is distinguishable from drift, at the report.**
9. **D8 — Close the outline write-back gap.**
10. **D9 — The tests, and they are the deliverable that outlives the rest.** Plus matched controls for
    every assessment-grading member.
11. **D10 — CONSUME the unified ledger vocabulary — do not build it.** The source recorded that its
    D8-class vocabulary work MOVED to `truthful-signals` PLAN-TRUTH-146. ⛔ That plan stays in that epic;
    this one consumes its output and must not re-implement it. ⛔⛔ **CORRECTED 2026-09-21 (cleanup,
    `checked_at: e8a71650`): the source states a HARD ordering, not a soft one.** `PLAN-TRUTH-152:35`
    ("this plan CONSUMES the vocabulary and must land after it") and `:72` ("⛔ Sequenced AFTER
    PLAN-TRUTH-146") both state PRQ-01 must land after PLAN-TRUTH-146 — the transfer softened this into
    "Depends on: none" plus "if PRQ-01 launches first, D10 states the dependency rather than filling it",
    which concealed a real ordering constraint from the emit-time check. `PLAN-TRUTH-146` is still
    `staged` as of `e8a71650`. See the restored dependency in `## Dependencies and Sequencing`.

## Claim Labels

⛔ Every claim below is a POINTER at the source spec that authored it, which is on disk at the path in
`## Provenance`. Re-derive each from the source's own `## Claim Labels` section at HEAD, never from this
restatement — D0 owns that re-grounding.

- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-123 still holds at HEAD — confirm/refute at
  that spec's `## Claim Labels` (verify-at-outline)
  - verdict: contradicted | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: yes | evidence: PLAN-TRUTH-123 carries 23 claims: 18 corroborated/3 contradicted(rescoped:yes)/2 unverifiable -- not every premise holds; its own RE-SCOPED table records the 3 unrepaired. Sibling premise (review_commitments.py COMMITTED/RELEASED_RESOLUTIONS) holds byte-exact. Rescoped: D0 already owns reading persisted verdicts, contradictions narrow the reportable population rather than invalidate the plan
- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-130 still holds at HEAD — confirm/refute at
  that spec's `## Claim Labels` (verify-at-outline)
  - verdict: contradicted | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: yes | evidence: PLAN-TRUTH-130 bullet 6 carries no verdict and is recorded REFUTED in its own RE-SCOPED table. Re-derived first-party: light-lane.md:155 documents a mainline deliverable-revision path that touches no assessment -- a carried premise demonstrably fails (contradiction, not unverifiability). Mechanism half stands: effective_from 0 hits repo-wide, add_assessment single-sited, check-outline-vs-shipped sole consumer -- D5 premise intact, refutation supplies D0's worked example
- OBSERVED: the transfer changed no deliverable's content. The 11 above are the source's D0–D10 verbatim
  in substance; only the epic, the workstream and this provenance framing differ. Re-read the source to
  confirm before scoping.
  - verdict: corroborated | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: n/a | evidence: all three divergences the prior contradicted verdict (e8a71650) found have since been REPAIRED in PRQ-01's own text: D0 now carries PLAN-TRUTH-152:25's exact wording, Dependencies now states the hard PLAN-TRUTH-146 ordering, Expected Surface re-counted 21/21 identical sets including the recursive glob. D1-D10 match -152's substance

## Expected Surface

Carried from the source spec, which derived it through `epic_spec_parser` as the union of its two
superseded sources — not retyped from memory.

- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/`
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/**` (restored 2026-09-21 — the
  transfer dropped this recursive glob; source had 21 Expected Surface entries, this spec had 20. Read by
  the disjointness gate, not cosmetic.)
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/retro_sections.py`
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/compile-report.py`
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/SKILL.md`
- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/`
- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_gate_coverage.py`
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_commitments.py`
- `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py`
- `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/constants.py`
- `marketplace/bundles/plan-marshall/skills/manage-findings/**`
- `marketplace/bundles/plan-marshall/skills/phase-3-outline/**`
- `marketplace/bundles/plan-marshall/skills/manage-references/**`
- `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`
- `.claude/skills/audit-archived-plan-retrospectives/SKILL.md`
- `.claude/skills/audit-archived-plan-retrospectives/checks/`
- `doc/analyzis-cloud-plan/`
- `test/plan-marshall/plan-retrospective/`
- `test/plan-marshall/plan-retrospective/**`
- `test/plan-marshall/audit-archived-plan-retrospectives/`
- `test/plan-marshall/manage-findings/**`

## Dependencies and Sequencing

- ⛔⛔ **Depends on: `truthful-signals` PLAN-TRUTH-146 (HARD — corrected 2026-09-21, restoring the
  source's stated ordering).** D10 CONSUMES `PLAN-TRUTH-146`'s unified ledger vocabulary and MUST land
  after it, per the source spec (`PLAN-TRUTH-152:35,:72`) — this plan must NOT be emitted while
  `PLAN-TRUTH-146` is still unlanded. A cross-epic dependency **no disjointness gate can see**, since the
  two live in different ledgers; check `truthful-signals`' queue before emitting this spec.
- ⛔ Never pair with PLAN-PRQ-02 (shared `plan-retrospective/scripts/`). At `parallelization_scope: 1`
  that is automatic.
- ⚠ Shares `.claude/skills/audit-archived-plan-retrospectives/**` with PLAN-PRQ-03 — sequence.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/post-run-quality/plans/PLAN-PRQ-01-retrospective-quality-chain-and-assessments-graded-at-report-time.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
