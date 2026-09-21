# PLAN-11: The scoping mechanism reaches the components that are waiting for it

epic: multiplattform
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> **Authored at ingestion** to build the prerequisites every blocked §D / §M11 candidate waits on.
> Source evidence: `landings/PLAN-02.md` § Follow-Ups, `../reference/coupling-inventory.md` §D,
> `../reference/marketplace-audit.md` §M11.

## Epic Constraints (bind every deliverable)

- **The principles bind:** no target enumeration in contracts, no wire format across the runtime boundary, no universal templating, honest no-ops. Read `../reference/principles.md`.
- **Counts and enumerations here are LEADS.** Re-derive at the moment of the claim.
- **Never edit another plan's surface**, even for an obvious adjacent fix.
- **Confirm the Expected Surface against the tree as the first action** and report any file the work needs beyond it.

## Objective

PLAN-02 built per-component `targets:` scoping end to end and gave it exactly **one** real consumer.
Meanwhile five candidates sit registered in the inventory's §D, each marked blocked — not on a
decision, but on two mechanisms nobody built: scoping at **file** level (a reference document inside
an otherwise target-neutral skill), and a **split** of `marshall-steward` so its Claude-only
terminal-title and enforcement-hook wizard surfaces can be scoped without taking the whole steward
with them. Build both prerequisites and apply them, so the mechanism stops being a capability with
one user and the §D backlog stops being permanently blocked.

## Deliverables

1. **D1 — File-level `targets:` scoping.** Extend the component-scoping mechanism so a single file inside a component can declare the targets it is emitted to, using the same registry-derived filter and the same fail-closed validation the component level already has. ⛔ **Do not invent a second mechanism** — this is an extension of `component_targets.py`, sharing its parser, its validation, and its error messages.
   *Done when:* a file declaring `targets: [claude]` inside an unscoped skill is emitted to the Claude tree and absent from the OpenCode tree; the same four rejection paths (unknown name, empty list, only-non-tree targets, and now a file whose declaration contradicts its component's) fail closed with file+value in the message; red-first tests for each.
2. **D2 — The `marshall-steward` split.** Separate the steward's Claude-only wizard surfaces (terminal-title, enforcement-hook) from its target-neutral body, so the Claude-only halves can carry a `targets:` declaration without making the whole steward Claude-only. The split boundary is the deliverable, not a mechanical file move: state it in the PR body.
   *Done when:* the steward's target-neutral operations remain available on every registered target; the two Claude-only wizard surfaces are scoped; the steward's own tests pass unchanged on the neutral half.
3. **D3 — Apply the scoping to the §D backlog.** Scope the five registered candidates: `hook-authoring-guide.md`, `permission-prompt-analysis.md`, `askuserquestion-patterns.md`, and the two marshall-steward wizard surfaces D2 separated.
   *Done when:* each of the five carries a declaration or is reported as a candidate that turned out **not** to need one, with the reason. ⛔ A candidate re-derived as target-neutral is a legitimate finding, not a failure — record it and leave it unscoped.
4. **D4 — Report the §D rows for retirement.** Re-run each §D row's own detection against the tree and report the result. ⛔ The plan does **not** edit `../reference/coupling-inventory.md` — it is ledger-resident and off-limits. A row whose detection still finds something **stays, narrowed to the residue**.
   *Done when:* the PR body and the inbox message carry each row's re-run detection and its verdict.

## Out of Scope

- **Widening the doctor rule's completeness** beyond what the stdlib constraint allows. The `targets-scope-invalid` rule is a deliberate approximation (self-measured 34.5% completeness at HEAD) because a consumer install has no PyYAML. D1 extends the *mechanism*; the doctor's ceiling is a separate, recorded question. Extend the rule to the file level **only within the same soundness-over-completeness stance**, and disclose the file-level ceiling the same way the component-level one is disclosed.
- **Deciding whether `targets:` is the right mechanism at all** versus a per-target ignore manifest — recorded as genuinely open in PLAN-02's residue and untouched by all 15 of its verification rounds. This plan extends the mechanism the repository chose; it does not re-open the choice.
- **The repo-scoping question** (whether the meta-repo `.claude/` tree is normative) — **PLAN-15**'s design work. ⛔ If PLAN-15's ADR concludes repo-scoping needs its own mechanism, this plan's D1 may need re-scoping; see Dependencies.
- **`pm-plugin-development`'s authoring surface** — PLAN-06's.

## Claim Labels

- OBSERVED: the mechanism has exactly **one** real consumer at HEAD `2cd1a19c` — `tools-fix-intellij-diagnostics.md`, confirmed by frontmatter read and by the on-disk `target/claude` vs `target/opencode` trees.
  - verdict: corroborated | checked_at: 1c4e6febb | by: multiplattform/cleanup | rescoped: n/a | evidence: Re-derived at 1c4e6febb. A search for a targets: frontmatter declaration returns TWO files: commands/tools-fix-intellij-diagnostics.md (the real consumer, declaring targets: [claude]) and plugin-architecture/references/frontmatter-standards.md, which DOCUMENTS the mechanism rather than consuming it. The claim's own test is 'real consumer', so one is correct - but the second hit is named here so the next reader does not re-derive a count of two and think the claim refuted.
- ⚙️ **RE-SCOPED at the 2026-09-06 re-grounding — the count was FIVE and is now SIX.** §D holds **seven** rows at `1c4e6febb`, of which **one is already scoped** (`tools-fix-intellij-diagnostics.md`, `targets: [claude]`) and **six are not**. All six are present on disk and none is newly scoped, so the claim's SUBSTANCE holds — only its cardinality was stale. ⛔ Re-derive the count from §D at run time rather than trusting any number written here: PLAN-06 and PLAN-07 defer candidates into this section, which is exactly how it grew.
  - verdict: contradicted | checked_at: 1c4e6febb | by: multiplattform/cleanup | rescoped: yes | evidence: Cardinality refuted, substance holds; absorbed into the claim text in the same act. Section D of the coupling inventory carries SEVEN rows at 1c4e6febb, one already scoped (tools-fix-intellij-diagnostics.md) and SIX unscoped - the claim said five. All six are present on disk and none is newly scoped, so what the claim asserts about their STATE is correct and only its count was stale. The claim now instructs re-deriving the count from section D at run time rather than trusting a written number.
- OBSERVED: the §D rows record the blockers explicitly — `Scoped: no — needs the steward skill split, which plan 020 left out of scope` for the two steward candidates, and the file-level extension for `askuserquestion-patterns.md`.
  - verdict: corroborated | checked_at: 1c4e6febb | by: multiplattform/cleanup | rescoped: n/a | evidence: Re-derived at 1c4e6febb by reading section D's Scoped column row by row. Every unscoped row states its own blocker rather than leaving it implied: three read 'a file inside a skill; it ships wherever its parent skill ships, and scoping it alone needs the file-level mechanism'; two read 'needs the steward skill split, which plan 020 left out of scope'; one reads 'a repo-scoping concern, not a target-scoping one'. The claim holds as written.
- OBSERVED: `component_targets.py` is registry-derived throughout (`registered_target_names`, `component_tree_target_names`, `emits_to`, `excluded_emission_roots`) and enumerates no target — the shape D1 must preserve.
  - verdict: corroborated | checked_at: 1c4e6febb | by: multiplattform/cleanup | rescoped: n/a | evidence: Re-derived at 1c4e6febb: component_targets.py carries 13 occurrences across the four named symbols (registered_target_names, component_tree_target_names, emits_to, excluded_emission_roots) and enumerates no target literal of its own. The registry-derived shape D1 must preserve is intact.
- OBSERVED: an unscoped component is emitted to every target — read at `component_targets.py::emits_to`.
  - verdict: corroborated | checked_at: 1c4e6febb | by: multiplattform/cleanup | rescoped: n/a | evidence: Re-derived by reading the predicate itself at component_targets.py:455-470. emits_to returns 'scope is None or target_name in scope', so a component with no declaration (scope is None) is emitted to EVERY target. Confirmed at the source rather than from the docstring.
- HYPOTHESIS: file-level scoping fits inside `component_targets.py`'s existing parser and validation without a parallel code path — confirm/refute at `component_targets.py` § `read_target_scope` and both emitters' consumption sites (verify-at-outline). ⛔ If it refutes — if a file-level declaration genuinely needs its own parser — **halt and report**, because a second mechanism is the exact outcome this plan exists to avoid.
  - verdict: unverifiable | checked_at: 1c4e6febb | by: multiplattform/cleanup | rescoped: n/a | evidence: The parser seam EXISTS and is named - read_target_scope at component_targets.py:383, with emits_to consuming it at :455 - so the site the hypothesis points at is real and locatable. But whether file-level scoping FITS INSIDE that parser and its validation without a parallel code path is a design judgement over both emitters' consumption sites, and existence establishes none of it. Recording it as verified because the function exists would be exactly the false-positive this field exists to prevent. It is verify-at-outline work and stays the plan's.
- HYPOTHESIS: the steward's Claude-only surfaces are separable from its neutral body along a clean boundary — confirm/refute at the steward's skill tree and its reference documents (verify-at-outline). This is the plan's largest unknown; a refutation re-scopes D2 and D3 rather than halting the plan.
  - verdict: unverifiable | checked_at: 1c4e6febb | by: multiplattform/cleanup | rescoped: n/a | evidence: Unchanged and deliberately so. Whether the steward's Claude-only surfaces separate from its neutral body along a CLEAN boundary is the plan's own largest unknown by its own words, and settling it means reading the whole steward skill tree and its reference documents against a boundary that does not yet exist. That is verify-at-outline work, not a ledger derivation. Section D independently records the same blocker on two rows ('needs the steward skill split, which plan 020 left out of scope'), which corroborates that the split is still OPEN but says nothing about whether it is clean.
- ⚙️ **RE-SCOPED at the 2026-09-06 re-grounding — REFUTED, and the anticipated cause is the actual one.** The hypothesis read *the §D candidate set is exactly five at run time* and predicted PLAN-06/PLAN-07 might register more. They did: §D now carries seven rows, six of them unscoped. The hypothesis is settled REFUTED rather than left open, and the plan's job is the six, not a re-count. ⭐ **One of the six is no longer a target-scoping question at all**: `wrapper-tangle-scan.py` is recorded as *a repo-scoping concern, not a target-scoping one*, and **ADR-020 (PLAN-15, PR #1420) now decides that class** — repository scope is distinct from target scope, and a shipped reference into the meta-repo's project-local tree declares itself at the reference site. Apply the ADR to that row rather than scoping it.
  - verdict: contradicted | checked_at: 1c4e6febb | by: multiplattform/cleanup | rescoped: yes | evidence: REFUTED, and by the exact cause the hypothesis predicted; absorbed into the claim text in the same act. It read 'the section D candidate set is exactly five at run time' and warned that PLAN-06 and PLAN-07 defer candidates in and may have registered more. They did: section D now carries SEVEN rows, six unscoped. The hypothesis is settled rather than left open. ALSO MATERIAL: one of the six - wrapper-tangle-scan.py - is recorded as 'a repo-scoping concern, not a target-scoping one', and ADR-020 from PLAN-15 (PR #1420) now DECIDES that class, so that row is answered by applying the ADR rather than by scoping it.

## Expected Surface

- OBSERVED: `marketplace/targets/component_targets.py` and both component-tree emitters' consumption sites — D1
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/**` — D2, D3
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/tools-permission-doctor/references/permission-prompt-analysis.md`, and the homes of `hook-authoring-guide.md` and `askuserquestion-patterns.md` — D3 (verify-at-outline: re-derive the actual paths from the §D rows, which name them by filename)
- HYPOTHESIS: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_target_scope.py` — D1's file-level extension of the doctor rule, **only if** it stays within the soundness stance (verify-at-outline). ⛔ This file is otherwise **PLAN-06's neighbourhood** — touch only the target-scope rule, and report if the change reaches further.
- OBSERVED: `test/marketplace/targets/**`, `test/plan-marshall/marshall-steward/**`

## Dependencies and Sequencing

- Depends on: **PLAN-02** (landed) for the component-level mechanism D1 extends.
- **Conditionally depends on PLAN-15.** If PLAN-15's ADR concludes that repo-scoping needs a mechanism distinct from target-scoping, D1's design changes. ⛔ **Resolve this before scoping D1**: read PLAN-15's row status; if PLAN-15 has not landed, either wait or record an explicit assumption in the PR body and the inbox message that D1 is target-scoping only.
- Overlaps with: **PLAN-05** and **PLAN-16** on `marketplace/targets/**`. ⛔ Not concurrent with either.
- Overlaps with: **PLAN-07** on the steward's surfaces — PLAN-07 fixes the steward's `--settings` literals and explicitly defers the wizard splits to this plan. ⛔ Not concurrent; run after PLAN-07 so D2 splits an already-literal-free surface.
- Overlaps with: **PLAN-06** at `_analyze_target_scope.py` only. Sequence or carve narrowly; report either way.
- Concurrent with: PLAN-04 (fully disjoint), PLAN-13 (fully disjoint).

## Verification

- The full verify gate, read from its exit status **and** its result `status`/`errors[]`.
- `generate.py --target all` exits 0 on the edited tree, and the Claude equality check still passes.
- Red-first tests for every D1 rejection path, including the new file-versus-component contradiction case.
- **The emission pin:** for each scoped file in D3, assert its presence in the Claude tree and its absence from the OpenCode tree — derived from the registry, not from a restated target list, with a non-vacuity guard.
- A cold read of the split steward: a reviewer reads it without the plan in context and reports which operations they believe work on a non-Claude target. Any answer that includes a scoped wizard surface means D2's boundary is unclear.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/multiplattform/plans/PLAN-11-target-scoping-adoption.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message —
the orchestrator owns every other ledger write. D4 **reports** its row re-derivations through that
message; the orchestrator retires the rows from the landing.
