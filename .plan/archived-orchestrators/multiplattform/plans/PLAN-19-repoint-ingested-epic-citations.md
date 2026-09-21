# PLAN-19: No version-controlled document cites a path that no longer exists

epic: multiplattform
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> **Authored at ingestion**, and it exists because of the ingestion itself: absorbing
> `doc/plans/multiplattform/` into this git-ignored ledger left four version-controlled documents
> citing a directory that is now gone.

⚠️ **This plan repairs a regression this epic's own ingestion introduced.** It is not discovered
work — it is a known, dated consequence of an operator decision recorded in `epic.md` § Decisions
("Fully ingest — stage a plan to reword every citation"). Treat it as high-priority: every commit to
`main` between the ingestion and this plan's landing carries the dangling references.

[RE-GROUNDED at HEAD `3bc01075`.] Since this spec was authored, `doc/plans/` was retired **entirely**
(commit `3bc01075`, on top of both epic ingestions), and that commit closed **D2** as declared
collateral. **Three of the original four deliverables remain open**, re-derived by sweep at that HEAD:
`AGENTS.md` (2 occurrences), `doc/adr/011` (2), `rule-provenance.md` (1). The scope-bloat guard is not
in play at three deliverables.

## Epic Constraints (bind every deliverable)

- **The principles bind:** no target enumeration in contracts, no wire format across the runtime boundary, no universal templating, honest no-ops. Read `../reference/principles.md` — ⛔ **which is exactly the file whose git-visible copy this plan is removing the last citations of.** The ledger copy remains the epic's evidence; it is simply no longer a *citable* authority for version-controlled documents. That distinction is the whole point of the plan.
- **Counts and enumerations here are LEADS.** Re-derive at the moment of the claim.
- **Never edit another plan's surface**, even for an obvious adjacent fix.
- **Confirm the Expected Surface against the tree as the first action** and report any file the work needs beyond it.

## Objective

`doc/plans/multiplattform/` was ingested into the orchestrator ledger and removed from version
control. Four version-controlled documents still cite it, two of them with **live relative links
that no longer resolve** — including one in shipped bundle content, where a broken link reaches
every consumer of the marketplace. Reword each citation so it names the **concept, the enacting
code, or a durable identifier** (a merged PR number), never a filesystem path into a git-ignored
tree.

⛔ **The rule for every rewrite: a version-controlled document may not cite `.plan/` either.**
Repointing a dead `doc/plans/` path at a `.plan/orchestrator/` path trades a broken link for
an invisible one — `.plan/` is git-ignored, so the new target is absent from every clone. That is
strictly worse, because it *looks* resolvable.

## Deliverables

1. **D1 — `AGENTS.md`.** Two prose statements say open multi-target work is "planned under `doc/plans/multiplattform/`", one adding that its `reference/principles.md` carries the cross-cutting constraints and the other that its `README.md` carries the architecture baseline and plan queue. Reword both to state the constraints themselves, or to name `marketplace/targets/` and `TARGET_REGISTRY` — the code that is actually the source of truth — without pointing at a plan directory.
   *Done when:* neither statement names a plan directory, and a reader still learns where multi-target work is defined.
2. ✅ **D2 — `marketplace/targets/opencode/transforms.md` — ALREADY CLOSED, not by this plan.**
   ⛔ **Do not re-do it.** At authoring time this was the most consequential of the four: a live
   markdown link into `doc/plans/` in *shipped bundle content*. Commit `3bc01075`
   ("chore(plans): retire the doc/plans tree") de-referenced it as declared collateral — its message
   names this link explicitly as *"already broken by the multiplattform ingestion and … fixed here
   since it is the same one-line class."* Re-derived at HEAD `3bc01075`: `transforms.md:32` now
   carries a prose note pointing at git history and **no link into `doc/plans/` or `.plan/`**.
   *Verify only:* re-run the D2 done-when check and record it as already satisfied. If it is not, the
   re-grounding was wrong and the deliverable reopens.
3. **D3 — `doc/adr/011`.** Two citations in its references section: `doc/plans/multiplattform/reference/principles.md` cited as §1 authority, and `doc/plans/multiplattform/020-target-scoped-components.md` (note: a **path that never existed in that form** — the plan lived at `020-target-scoped-components/plan.md`, so this citation was already wrong before the ingestion). Restate the §1 principle inline as the ADR's own statement of the constraint it relies on, and repoint the second at the shipped mechanism (`marketplace/targets/component_targets.py`) or at PR #1313.
   *Done when:* the ADR's references resolve, and its §1 authority is stated rather than delegated to an unreachable document. ⛔ **An ADR is a durable decision record** — a citation it cannot resolve undermines the decision it documents, which is why this is a deliverable rather than a nit.
4. **D4 — `plugin-doctor/references/rule-provenance.md`.** Line 267 attributes the `targets-scope-invalid` rule to "Plan `multiplattform/020-target-scoped-components` (D4)". Repoint the provenance at a durable identifier — PR #1313, and/or the enacting code `marketplace/targets/component_targets.py` — keeping the attribution meaningful.
   *Done when:* the provenance names something a reader can actually reach.

## Out of Scope

- ✅ **`doc/plans/test-quality/090-harness-and-rule-gaps/report-01.md` — MOOT at HEAD `3bc01075`.** It was excluded as a dated run record; the whole `doc/plans/` tree has since been retired, so the file no longer exists. The exclusion needs no action and is kept only so a reader of the original scope sees what happened to it.
- ⛔ **`.claude/skills/author-cloud-plan/SKILL.md`'s four citations of `doc/plans/_template/plan.md`.** Commit `3bc01075` deleted that template and **recorded the dangle as an accepted consequence in its own message**. It is the same defect class this plan repairs, but it belongs to the **lane skills**, which are project-local and outside this epic's surface entirely. Report it; do not fix it here. (Raised as an epic Open Defect.)
- **Restating the principles document in full anywhere.** D1–D4 state only the specific constraint each citing sentence relies on. Reproducing the whole document in git would re-create the duplication the ingestion removed.
- **Creating a new version-controlled home for `principles.md`.** This was the explicitly rejected alternative (see `epic.md` § Decisions). ⛔ Do not reintroduce it as a convenience.
- **Any other file's content.** This is a citation-repair plan.

## Claim Labels

- OBSERVED, **count corrected at re-grounding**: four version-controlled files cited the ingested tree at HEAD `2cd1a19c`; **three still do at HEAD `3bc01075`** — `AGENTS.md` (2 occurrences, lines 7 and 74), `doc/adr/011-…adoc` (2, lines 384 and 389), `rule-provenance.md` (1, line 267). `transforms.md` dropped out when `3bc01075` fixed it. Re-derived by a repository-wide `grep` over `*.md` and `*.adoc` excluding `.plan/` and this analysis's own reports.
  - verdict: contradicted | checked_at: 3bc01075 | by: multiplattform/cleanup | rescoped: yes | evidence: Count corrected: four citing files at 2cd1a19c, three at 3bc01075. transforms.md dropped out when commit 3bc01075 de-referenced its link as declared collateral. D2 re-scoped to verify-only; spec now states three open deliverables.
- ⚠️ OBSERVED, **and it is NOT one of the three**: `AGENTS.md:39` also names `doc/plans/` — but generically, describing the standalone-plan-lane rule, which `3bc01075` deliberately KEPT. ⛔ Do not sweep it up with the multiplattform-specific citations at lines 7 and 74. Rewording it would silently retire a lane contract this plan has no mandate over.
  - verdict: corroborated | checked_at: 3bc01075 | by: multiplattform/cleanup | rescoped: n/a | evidence: AGENTS.md:39 confirmed to name doc/plans generically for the standalone-plan-lane rule, which 3bc01075 explicitly kept. Distinct from the multiplattform-specific citations at lines 7 and 74.
- ⚠️ OBSERVED, **and this bounds the claim above**: the content sweep is **inventory-scoped**. Always-ignored directories, gitignored paths, and dotfile trees outside the `.claude/**` / `.github/**` allowlist are **not** searched. The four-file figure is therefore *"not in any inventoried file"*, **not** *"not in the tree"*. ⛔ Re-derive with `Glob`/`Grep` over the uninventoried paths before claiming completeness.
  - verdict: corroborated | checked_at: 3bc01075 | by: multiplattform/cleanup | rescoped: n/a | evidence: The inventory-scope bound still holds and still matters: the re-grounding sweep used repository-wide grep over md/adoc rather than the inventory-scoped content search, which is the remedy this claim asks for.
- OBSERVED (**superseded at HEAD `3bc01075` — kept as the record of why D2 existed**): `transforms.md:31` carried a resolvable-looking relative markdown link three levels up into `doc/plans/`, in shipped bundle content. Commit `3bc01075` de-referenced it; line 32 now carries a prose pointer to git history and no link. D2 is verify-only.
  - verdict: contradicted | checked_at: 3bc01075 | by: multiplattform/cleanup | rescoped: yes | evidence: No longer true at HEAD: commit 3bc01075 de-referenced the transforms.md link. transforms.md:32 now carries a prose pointer to git history and no link into doc/plans or .plan. D2 re-scoped to verify-only.
- OBSERVED: ADR-011's second citation names `doc/plans/multiplattform/020-target-scoped-components.md`, a **flat path that never existed** — the plan was a directory (`020-target-scoped-components/plan.md`). The citation was already broken before the ingestion, which makes it a pre-existing defect this plan happens to reach, not damage the ingestion caused.
  - verdict: corroborated | checked_at: 3bc01075 | by: multiplattform/cleanup | rescoped: n/a | evidence: ADR-011:389 still names doc/plans/multiplattform/020-target-scoped-components.md, a flat path that never existed - the plan lived at 020-target-scoped-components/plan.md. Pre-existing defect, unchanged by either ingestion or by 3bc01075.
- OBSERVED: the ingestion is the cause, and it was an operator decision, not a discovery — recorded in `epic.md` § Decisions.
  - verdict: corroborated | checked_at: 3bc01075 | by: multiplattform/cleanup | rescoped: n/a | evidence: Unchanged: the ingestion remains the cause of the three surviving citations, recorded as an operator decision in epic.md Decisions rather than as a discovery.
- HYPOTHESIS: every dangling citation can be repaired by restating the constraint rather than relocating a document — confirm/refute per site during D1–D4 (verify-at-outline). ⛔ If a site genuinely needs a citable document that no longer exists in git, **stop and report**: that reopens the operator's ingestion decision and is not this plan's to make.
  - verdict: corroborated | checked_at: 3bc01075 | by: multiplattform/cleanup | rescoped: n/a | evidence: Partially settled by precedent rather than by argument: commit 3bc01075 repaired the transforms.md site by exactly this method - de-referencing to a prose pointer rather than relocating a document - so the approach is demonstrated on one of the four sites.

## Expected Surface

- OBSERVED: `AGENTS.md` — D1, **lines 7 and 74 only** (line 39 is the lane rule; see Claim Labels)
- OBSERVED: `doc/adr/011-The_waiting_capability_is_a_hybrid_target-neutral_policy_over_a_declinable_runtime_primitive.adoc` — D3
- OBSERVED: `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/rule-provenance.md` — D4

⛔ D2's file is deliberately absent from this list — see Dependencies below for why.

## Dependencies and Sequencing

- Depends on: none. **Buildable immediately**, and it should be — it repairs a live regression.
- ✅ **The `marketplace/targets/**` overlap is GONE.** It existed only because of D2, which `3bc01075` closed. This plan no longer edits anything under `marketplace/targets/`, so it is **no longer sequenced against PLAN-05 or PLAN-16** and may run beside either.
- ⛔ **D2's file (`transforms.md`, under `marketplace/targets/opencode/`) is deliberately kept OUT of § Expected Surface**, and the path is named here rather than there on purpose. D2 only *reads* it to confirm `3bc01075`'s fix; a read is not a surface. Naming it in that section would render it into the ledger's derived Surface column and manufacture a collision with PLAN-05, which genuinely owns the file — the derived column extracts every backticked path in the section, including one named to be excluded.
- Overlaps with: **PLAN-06** and **PLAN-11** at `pm-plugin-development/**` — `rule-provenance.md` is named in **PLAN-06's D3** ("`rule-provenance.md` names the undeclared members"). ⛔ **Genuine same-file collision.** Sequence PLAN-19 **before** PLAN-06 — this plan's D4 is a one-line provenance edit, while PLAN-06's D3 restructures the rule-pack declaration; doing the small one first avoids rebasing it onto a restructured file.
- Concurrent with: PLAN-04 (fully disjoint), PLAN-13 (fully disjoint).
- **Recommended position: emit early**, beside PLAN-04, ahead of PLAN-16. It is small, unblocked, and every day it waits is a day `main` carries a distributed broken link.

## Verification

- **The link check is the gate:** every markdown/AsciiDoc link in the four touched files resolves against the tree at HEAD. ⛔ Assert specifically that no touched file links into `doc/plans/` **or** `.plan/` — the second half is what catches the "repointed at an invisible target" failure.
- Re-run the citation sweep over the changed tree, **plus** a `Glob`/`Grep` pass over the uninventoried paths the claim-labels bound names, and report the population each covered.
- **A cold read of each rewritten sentence:** a reviewer reads it without the plan in context and answers "what constraint is this telling me, and can I get to its source?" An answer that names a document they cannot open means the rewrite failed.
- `generate.py --target all` exits 0 and the Claude equality check passes — D2 edits shipped bundle content.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/multiplattform/plans/PLAN-19-repoint-ingested-epic-citations.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message —
the orchestrator owns every other ledger write.
