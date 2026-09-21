# PLAN-PRQ-03: The census does not census itself, and a re-check persists nothing

epic: post-run-quality
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

## Provenance

Staged 2026-09-17 at epic creation from a read-only inventory sweep of the corpus-level auditing surface.
Both members are stated by the instruments' own documentation — this spec did not infer either.

## Objective

**The archived-plan auditor is the only place cross-plan quality is measured, and it exempts itself from
the one check built to catch exactly its own failure mode.** Its SKILL.md says so in terms:
*"⛔ The census does not census itself. … That is the detector-inside-its-own-population failure mode,
standing unresolved in the instrument built to surface it."* Alongside it, two corpus questions cannot be
answered at all because their producer persists nothing: `recipe-plan-review` performs a request-vs-landed
re-check whose result exists only in the session that ran it.

An auditor that excludes itself from its own population publishes a clean reading it has not earned — the
epic's theme, one tier up, in the instrument the epic will otherwise be graded by.

## Deliverables

Four deliverables. D0 is a gate.

**D0 — GATE: derive the self-exclusion population across the whole auditor, not just the census.**
Enumerate all 24 checks and state, per check, whether its own output participates in the populations the
auditor scores — and enumerate every post-run producer whose result is NOT persisted anywhere a corpus
question can reach (`recipe-plan-review` is one known member; publish the rest). ⛔ Two populations, both
published with their sizes, before any fix.

**D1 — The suspect-zero census AND `retire-on-quiet` include themselves.** ⛔ **RE-GROUNDED 2026-09-18
(cleanup, `checked_at: 1605831c5`): TWO self-excluded meta blocks, not one.** `SKILL.md:231-232` itself
says so — *"`suspect-zero-census` **and `retire-on-quiet`** are meta blocks and are not in
`CHECK_NAMES`"*. Confirmed in code: `audit.py:237` `CHECK_NAMES` has exactly 24 entries (1:1 with
`checks/*.md`); `suspect_zero_census` iterates `CHECK_NAMES` (`:5860`) so every one of the 24 gets a row,
while `emit_suspect_zero_census_block` (`:5909`) AND `emit_retire_on_quiet_block` (`:5956`) both emit
blocks appended OUTSIDE that loop (`:9452-9462`). The census classifies a check's zero as
`structural` / `starved` / `gated` / `no_count` / `disciplinary` / `no_block` / `fired`; BOTH meta blocks'
own zeros must be classifiable by the same vocabulary and appear in the same table. If self-inclusion is
genuinely impossible for either, D1 ships the stated reason and the detector that would catch a regression
instead — but the source text says "standing unresolved", not "impossible", so the burden is on
refutation.

**D2 — Every remaining self-exclusion D0 found is closed or named.** Closed where mechanical; where not,
recorded in the check's own `checks/{name}.md` with the reason, so a reader of that check sees the
exemption at the point of use rather than in a summary elsewhere.

**D3 — The unpersisted re-check gets a persisted result, and the controls.** `recipe-plan-review` (and any
sibling D0 found) writes its verdict where the auditor can read it — the existing
`.plan/local/audit-reports/` layout is the natural home. Plus matched controls: a check that legitimately
has no population still reports its stated zero, and a self-included census still reports a real figure
when its own checks fired.

## Claim Labels

- OBSERVED: `.claude/skills/audit-archived-plan-retrospectives/SKILL.md:231-236` states the census's
  self-exclusion verbatim, including the phrase "standing unresolved in the instrument built to surface
  it" (inventory sweep, 2026-09-17).
- OBSERVED: the auditor registers **24 checks**, each with a `checks/{name}.md` sub-doc, with a
  deterministic core in `scripts/audit.py` and LLM orchestration in SKILL.md (inventory sweep).
- OBSERVED: `.claude/skills/recipe-plan-review/SKILL.md` declares itself LLM-only with no backing script
  and no persisted artifact — by design, per its own line 30 (inventory sweep).
- OBSERVED: `input-integrity` is the auditor's declared "no-false-healthy foundation", and blind plans'
  rows must be annotated "floor, not truth" — so the auditor already HAS the vocabulary D1 needs
  (inventory sweep).
- ⚠ HYPOTHESIS: the census is the only self-exclusion, and the other 23 checks participate in their own
  populations. ⛔ Asserted by nobody — D0 owns the derivation, and an asserted absence is the higher-risk
  half (verify-at-outline).
  - verdict: contradicted | checked_at: 1605831c5 | by: post-run-quality/cleanup | rescoped: yes | evidence: Two self-excluded meta blocks, not one -- SKILL.md:231-232 itself says so: suspect-zero-census AND retire-on-quiet are meta blocks, not in CHECK_NAMES. audit.py:237 CHECK_NAMES has 24 entries 1:1 with checks/*.md; suspect_zero_census iterates CHECK_NAMES (:5860); emit_suspect_zero_census_block (:5909) and emit_retire_on_quiet_block (:5956) both append outside the loop (:9452-9462). D1 as written closes only half the population.
- ⚠ HYPOTHESIS: `.plan/local/audit-reports/` is a suitable home for D3's persisted verdict — confirm at
  the auditor's own persistence step before adding a second layout (verify-at-outline).
  - verdict: corroborated | checked_at: 1605831c5 | by: post-run-quality/cleanup | rescoped: n/a | evidence: audit.py:5333 AUDIT_REPORTS_REL='.plan/local/audit-reports'; :5345-5348 persistence fn writes {run-timestamp}.toon with a path-traversal guard; :839 retire-on-quiet already reads back from the same dir -- a two-way store, not write-only. 31 entries on disk. No second layout needed.

## Expected Surface

- OBSERVED: `.claude/skills/audit-archived-plan-retrospectives/SKILL.md` — the census contract and its self-exclusion (D1, D2)
- OBSERVED: `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` — the deterministic core (D0, D1, D3)
- OBSERVED: `.claude/skills/audit-archived-plan-retrospectives/checks/` — the 24 per-check docs (D0, D2)
- OBSERVED: `.claude/skills/recipe-plan-review/SKILL.md` — the unpersisted re-check (D3)
- HYPOTHESIS: `test/plan-marshall/audit-archived-plan-retrospectives/` — coverage and the matched controls (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none. D0 derives its populations from the checks directory itself.
- ⚠ Shares `.claude/skills/audit-archived-plan-retrospectives/**` with PLAN-PRQ-01 (carried from its
  source spec) — sequence; at `parallelization_scope: 1` that is automatic.
- ⭐ This spec's surface is entirely project-local `.claude/skills/**`, so it is disjoint from every other
  spec in this epic except PRQ-01 — the natural partner if the scope knob is raised.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/post-run-quality/plans/PLAN-PRQ-03-the-census-does-not-census-itself-and-a-re-check-persists-nothing.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
