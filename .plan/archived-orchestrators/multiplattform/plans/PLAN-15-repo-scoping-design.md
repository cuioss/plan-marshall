# PLAN-15: Decide whether the meta-repo tree is normative, before anything scopes against it

epic: multiplattform
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> **Authored at ingestion** to draw audit cluster §M10, which the epic's own authoring run recorded
> as "registered; no drawing plan yet". Source evidence: `../reference/marketplace-audit.md` §M10;
> `archive/report-authoring-02.md` § Residue.

## Epic Constraints (bind every deliverable)

- **The principles bind:** no target enumeration in contracts, no wire format across the runtime boundary, no universal templating, honest no-ops. Read `../reference/principles.md`.
- **Counts and enumerations here are LEADS.** Re-derive at the moment of the claim.
- **Never edit another plan's surface**, even for an obvious adjacent fix.
- **Confirm the Expected Surface against the tree as the first action** and report any file the work needs beyond it.

## Objective

Audit cluster §M10 registers a set of sites that treat **this repository's own `.claude/` tree** as
normative — a six-level relative link in a finalize-step document, a lockstep obligation in
`manage-metrics/standards/data-format.md` pinned to a meta-repo audit script, a comment in
`analyze-logs.py`, the steward's maintenance and upgrade references, and `_gate_coverage.py`'s
ParityCell `.claude` lint-scope strings. It is the **only cluster in the audit with no drawing plan**,
and the reason is real: it is not a mechanical fix. These sites conflate two different scopings —
*which target* a component is emitted to, and *which repository* a path belongs to (the meta-repo
that builds the marketplace, versus a consumer project that installs it). Settle that distinction as a
decision before any code scopes against it, then apply it.

⛔ **This is a design plan. Its first deliverable is an ADR, and D2/D3 are contingent on what the ADR
decides.** A run that begins by editing the §M10 sites has skipped the deliverable that matters.

## Deliverables

1. **D1 — The ADR.** Author an ADR settling: (a) is the meta-repo `.claude/` tree normative for anything a consumer project reads, or is every such reference a meta-repo-only concern? (b) is repo-scope a distinct axis from target-scope, or a special case of it? (c) which of the two mechanisms — the `targets:` declaration or something else — should carry it, if either should. Record the alternatives considered and the reason each was rejected.
   *Done when:* the ADR is authored per the project's ADR conventions, states a decision rather than a survey, and names the consequence for each §M10 site.
2. **D2 — Apply the decision to the §M10 sites.** Each site is corrected per D1's decision: re-pointed, declared meta-repo-only, made repo-scope-aware, or recorded as correct-as-is with the reason.
   *Done when:* every §M10 site carries the disposition D1 assigns it, and none is left unaddressed. ⛔ **"Correct as is" is a legitimate disposition and must be recorded with its reason** — a silently skipped site is indistinguishable from an overlooked one.
3. **D3 — The distinction is stated where an author will meet it.** Wherever the repository documents component scoping, a reader learns that repo-scope and target-scope are different questions and which mechanism answers which.
   *Done when:* an author reading the scoping documentation can answer "is this path a meta-repo concern or a target concern?" without reading the ADR.

## Out of Scope

- **Building a repo-scoping mechanism** unless D1 concludes one is needed. ⛔ If it does, that is a **separate plan** the orchestrator stages from this plan's landing — not scope this plan absorbs. Say so in the PR body and the inbox message.
- **The §D / §M11 target-specific candidates** — PLAN-11's. This plan may *inform* PLAN-11's D1 design; it does not implement it.
- **`marketplace/targets/component_targets.py`** — PLAN-11's surface. ⛔ D2 does not edit the scoping mechanism; if the decision requires a mechanism change, it is reported and staged, not made here.

## Claim Labels

- OBSERVED: §M10 is registered with **no drawing plan** — read at `../reference/marketplace-audit.md` §M10, whose own text says "Registered; no drawing plan yet", and corroborated at `archive/report-authoring-02.md` § Residue, which records the same as deliberate.
- OBSERVED, set is a lead: the §M10 sites are `finalize-step-preference-emitter.md`'s six-level relative link, `manage-metrics/standards/data-format.md`'s lockstep obligation on the meta-repo audit script, an `analyze-logs.py` comment, `cwd-keyed-store-resolution-audit.md`, the steward maintenance/upgrade references, and `_gate_coverage.py`'s ParityCell `.claude` lint-scope strings. ⛔ **Not re-derived at ingestion** — re-derive the full set from the audit's named sweep patterns before D2; the list here is the audit's, not a fresh observation.
- OBSERVED: the audit itself frames §M10 as the same class as the §D "wrapper-tangle" note — a design question rather than a mechanical fix. This is why D1 precedes D2.
- HYPOTHESIS: repo-scope and target-scope are genuinely distinct axes — this is the question D1 settles, and it may settle it either way. ⛔ **Neither answer is a failure**; concluding they are the same axis is a real result that simplifies PLAN-11. Confirm/refute by reading the §M10 sites against `component_targets.py::emits_to`'s actual semantics (verify-at-outline).
- HYPOTHESIS: no §M10 site is already fixed by a landed plan — confirm/refute by re-deriving each site at HEAD (verify-at-outline). PLAN-03's residual sweep touched neighbouring files and may have closed one incidentally.

## Expected Surface

- OBSERVED: `doc/adr/` — D1, one new ADR
- HYPOTHESIS: the §M10 sites — `marketplace/bundles/plan-marshall/skills/**` (the finalize-step document, `manage-metrics/standards/data-format.md`, `analyze-logs.py`, the steward references) and `_gate_coverage.py` — D2 (verify-at-outline: re-derive the exact paths from the audit's sweep patterns)
- HYPOTHESIS: the scoping documentation's home — `marketplace/bundles/pm-plugin-development/skills/plugin-architecture/references/frontmatter-standards.md` § Target Scoping, and/or `doc/developer/marketplace-build.adoc` — D3 (verify-at-outline)
- ⛔ **Excluded:** `marketplace/targets/component_targets.py` and the doctor's target-scope rule — PLAN-11's.

## Dependencies and Sequencing

- Depends on: none. **D1 is buildable today** and is the highest-value deliverable in this plan.
- **Blocks PLAN-11 conditionally.** PLAN-11's D1 designs file-level scoping; if D1 here concludes repo-scope needs its own axis, PLAN-11's design changes. ⛔ **Prefer running this plan before PLAN-11.** If PLAN-11 runs first, it must record an explicit assumption that its D1 is target-scoping only.
- Overlaps with: **PLAN-07** on `marketplace/bundles/plan-marshall/skills/**` — several §M10 sites sit inside PLAN-07's §M5–§M9 surface, and `manage-metrics/standards/data-format.md` is also **PLAN-12's D3**. ⛔ **Three-way contested file.** Sequence after both PLAN-07 and PLAN-12, and re-derive rather than assuming what they left.
- Overlaps with: **PLAN-06** on `frontmatter-standards.md` if D3 lands there. Sequence.
- Concurrent with: PLAN-04, PLAN-13 (both fully disjoint) — **while D1 is the active deliverable**, this plan is effectively disjoint from everything, since an ADR touches only `doc/adr/`. The contention starts at D2.

## Verification

- The full verify gate if D2 touches Python; documentation-only otherwise.
- **D1's quality gate is a cold read, not a checklist:** a reviewer reads the ADR without the plan in context and answers "for a path in this repository, how do I tell whether it is a meta-repo concern or a target concern?" An answer that restates the question, or that needs the §M10 site list to be intelligible, means the ADR decided nothing.
- D2's completeness verified by re-running the audit's §M10 sweep patterns over the changed tree — every hit carries a disposition, including "correct as is".
- The PR body enumerates every site and its disposition. ⛔ A site the plan declined to touch is a **first-class report field**, for the same reason a silent application is indistinguishable from a lossy one.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/multiplattform/plans/PLAN-15-repo-scoping-design.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source, tests, and `doc/adr/`. It
creates and edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}`
message — the orchestrator owns every other ledger write. If D1 concludes a new mechanism is needed,
the plan **reports** that through its inbox message and the orchestrator stages the follow-up plan;
the plan does not stage it itself.
