# PLAN-TRUTH-016: Skills carry incident history as normative prose

> Renamed from **PLAN-118** on 2026-07-30 (see `plan-id-rename-map.md`).

epic: truthful-signals
workstream: WS-01

## Objective

Marketplace skill documents embed references to specific past PRs and incidents
(`Observed on plan-marshall#1045`, `the PR #866 failure mode`, `post-#1053`, `since #849`). This is
history, not contract. It violates the project's own documentation standard, it costs context on
every load, and it teaches the reader to reason from an incident they cannot see instead of from the
mechanism in front of them.

⛔ **This is already a written rule, not a new preference.** `CLAUDE.md` § Documentation Standards:
*"No version history — Never add changelogs, 'RECENT CHANGES', or dated update sections"*,
*"No timestamps — No dates or version numbers in document content"*, *"Current state only — Document
present requirements, not transitional information."* The rule exists and is unenforced.

## Measured scope

Orchestrator sweep at HEAD 2026-07-29 over `marketplace/bundles/`:

- **22 files** carry at least one occurrence; **~30 occurrences** total.
- Densest: `ext-self-review-plan-marshall/SKILL.md` (3), `workflow-integration-github/scripts/_github_pr.py` (3),
  `automatic-review/standards/pr-agent.md` (3), `tools-integration-ci/standards/pr-operations.md` (2),
  `phase-6-finalize/standards/branch-cleanup.md` (2), `phase-6-finalize/SKILL.md` (2).
- Detection pattern used: `plan-marshall#[0-9]+`, `PR #[0-9]+`, `(#[0-9]{3,4})`, `post-#[0-9]+`,
  `since #[0-9]+`, `Observed on `.

⚠ **That pattern is the orchestrator's first cut and is a SAMPLE, not the population.** It will miss
bare `#1045` in prose, `plan-marshall/pull/NNNN` URLs, dated phrasings ("as of 2026-07"), and
version-pinned narration ("before 0.1.1240"). **D1 owns deriving the real population.**

## ⛔ The distinction that makes this plan non-trivial

**Not every reference is pure noise, and a blanket delete would destroy meaning.**

- **Pure noise — DELETE.** `branch-cleanup.md:581`: *"Observed on plan-marshall#1045: the fix commit
  was reviewed by CodeRabbit and never by the required `pr-agent`, `review_completeness` returned
  `participation_complete: false` with `unproven_bots: [pr-agent, sourcery]`, the step went `done`
  through the hatch, and `final_merge_without_asking: true` carried it to merge unchallenged."* An
  entire incident narrative inside a normative barrier spec. The **preceding sentence already states
  the mechanism** ("the resulting record is byte-identical to one earned by a genuine pass — so
  nothing downstream could previously distinguish *reviewed* from *forced*"). The narrative adds
  nothing a reader can act on.
- **A NAMED MECHANISM — REPLACE, do not delete.** `pr-operations.md:196` and `:205` use
  *"the PR #866 failure mode"* / *"the residual PR #866 signature"* as a **term of art**, twice, for
  a real behaviour: *GitHub accepts a merge call on a merge-queue-required branch and closes the PR
  unmerged instead of merging it.* Deleting the phrase deletes the concept. **Replace the incident
  label with the mechanism it names.**

**Every occurrence is classified into exactly one of those two arms.** A blanket regex delete is an
explicitly prohibited implementation.

## Deliverables

1. **D1 — GATE (mutates nothing): DERIVE the population.** Widen beyond the orchestrator's seed
   pattern to cover bare `#NNNN` in prose, PR URLs, dated phrasings, and version-pinned narration.
   Report the count. ⛔ **Do not begin edits until the population is derived** — the seed pattern's
   22 files is a floor, not a total.
2. **D2 — classify every occurrence into DELETE or REPLACE**, with the verdict recorded per
   occurrence. A REPLACE names the mechanism that supersedes the incident label.
3. **D3 — apply the classified edits.** ⛔ **Preserve every normative claim.** The test of a correct
   edit is that a reader who never saw the incident can still act correctly on the remaining prose.
   Where removing the narrative would leave the mechanism unstated, **state the mechanism** — do not
   simply delete and shorten.
4. **D4 — a plugin-doctor rule so this cannot regress.** The rule flags incident references in
   marketplace docs and scripts. ⚠ It must be **population-derived over the bundle tree**, not a
   hand-maintained list of known-bad files — the hand-maintained-mirror archetype is at n=5 in this
   epic. ⚠ It needs a **sanctioned exemption** for genuinely-referential contexts if D2 finds any
   (e.g. an ADR that legitimately cites its own decision record); if D2 finds none, the rule is
   unconditional and says so.
5. **D5 — tests, each verified to FAIL pre-fix.** (a) The D4 rule fires on a doc carrying
   `Observed on plan-marshall#NNNN`. (b) It does NOT fire on the D3-corrected `pr-operations.md`
   mechanism prose. (c) The rule's file population is derived and asserted non-empty.

## Claim Labels

- OBSERVED (orchestrator-verified 2026-07-29): the 22-file / ~30-occurrence count under the stated
  pattern; the `branch-cleanup.md:581` narrative; the two `pr-operations.md` named-mechanism uses;
  the `CLAUDE.md` documentation standard.
- HYPOTHESIS: the true population exceeds the seed pattern — **confirm/refute at D1**.
  **Confirm/refute artifact**: D1's derived occurrence list.
- HYPOTHESIS: no occurrence requires a permanent exemption — **confirm/refute at D2**.
- ⚠ Line numbers are OBSERVED at 2026-07-29 HEAD. **Re-ground by SYMBOL / quoted phrase.**

## Expected Surface

- OBSERVED: `marketplace/bundles/**` — 22 identified files across `plan-marshall` and
  `pm-plugin-development`
- HYPOTHESIS: additional files D1's widened derivation surfaces
- OBSERVED: `pm-plugin-development/skills/plugin-doctor/**` (the D4 rule home + rule catalogue)
- OBSERVED: the corresponding plugin-doctor tests

## Dependencies and Sequencing

- Depends on: none.
- ⛔ **Wide but shallow, and it touches files other plans are editing.** It reaches
  `branch-cleanup.md` (**PLAN-117**, **PLAN-119**), `pr-operations.md` (**PLAN-115 LAUNCHED**),
  `pr-agent.md` and `_github_pr.py` (**PLAN-116**), `phase-6-finalize/SKILL.md` (**PLAN-112
  LAUNCHED**, **PLAN-TRUTH-001**). **Sequence LAST among the finalize-surface plans, or scope D3 to exclude
  files with an in-flight owner and record the exclusions as residue.**
- Overlaps with: PLAN-TRUTH-004 / PLAN-TRUTH-002 / PLAN-TRUTH-003 (plugin-doctor rule surface) — **co-design the
  population-derived detector pattern; do not build a fourth.**

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-016-skills-carry-incident-history-as-normative-prose.md"
```

## ⭐ FOLDED IN 2026-08-09 — two transitional-content instances from the retired 2026-07-04 review

This plan owns *documents carrying content the project's own standards prohibit*. Two review findings
are the same class one step out from skills, re-verified at HEAD:

- **[C-G4]** `doc/analysis/uncompressed-output-measurement.md` embeds a **point-in-time snapshot** — a
  "recent 2-week analysis window", 123 transcripts, hard token totals and named plans with billed
  figures. ✅ Re-verified: the file still exists. This is transitional measurement content in a
  published doc, against the *current-state only* standard. ⭐⭐ **And this epic has independently
  retired every per-phase token figure as unreliable** — so the doc is not merely stale-by-policy, it
  **publishes numbers the epic no longer stands behind.** Trim to the durable decision + rationale, or
  relocate to a dated record whose snapshot nature is explicit.
- **[C-G5]** `doc/refactor/README.md` maintains **"Landed"/"Resolved"/"open" status tables**. ✅
  Re-verified: the file still exists. ⛔ **This one is a DECISION, not a defect** — the review lists it
  under *Open Decisions for Maintainers*, and a roadmap may legitimately be exempt. **Confirm the
  exception is intentional; if kept, quarantine it clearly as planning material.** Do not silently
  delete a maintainer's roadmap on a standards argument.

⚠ **[C-G6]** (the root README surfacing only the snapshot install form) is **dropped, not folded** —
the review itself marks it *Low (optional)* and purely navigational, and the link resolves. Recorded
so it is not re-filed as a gap.

## Write-Boundary

This plan MUST NOT create or edit any file under `.plan/local/orchestrator/`. Its only channels back
to the epic are its PR and its `inbox/` OUTBOX.
