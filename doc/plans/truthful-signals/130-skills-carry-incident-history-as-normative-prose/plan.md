> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# Skills carry incident history as normative prose

**Epic:** truthful-signals
**Branch prefix:** chore

## Problem

Marketplace skill documents embed references to specific past PRs and incidents — *"Observed on
plan-marshall#1045"*, *"the PR #866 failure mode"*, *"post-#1053"*, *"since #849"*. This is **history,
not contract**. It costs context on every load, and it teaches the reader to reason from an incident
they **cannot see** instead of from the mechanism in front of them.

⛔ **This is already a written rule, not a new preference.** `CLAUDE.md` § Documentation Standards
states: *"No version history — never add changelogs, 'RECENT CHANGES', or dated update sections"*;
*"No timestamps — no dates or version numbers in document content"*; *"Current state only — document
present requirements, not transitional information."* **The rule exists and is unenforced.**

⛔ **The distinction that makes this non-trivial: not every reference is noise, and a blanket delete
would destroy meaning.** Every occurrence falls into exactly one of two arms:

- **Pure noise — DELETE.** An entire incident narrative sitting inside a normative barrier
  specification, where the **preceding sentence already states the mechanism**. The narrative adds
  nothing a reader can act on. One such passage recounts a whole review-coverage failure — which bot
  reviewed, what the completeness call returned, how the step went `done` through a hatch — where the
  sentence above it already says the operative thing: the resulting record is byte-identical to one
  earned by a genuine pass, so nothing downstream could distinguish *reviewed* from *forced*.
- **A NAMED MECHANISM — REPLACE, do not delete.** Elsewhere, *"the PR #866 failure mode"* and *"the
  residual PR #866 signature"* are used **twice, as a term of art**, for a real behaviour: *GitHub
  accepts a merge call on a merge-queue-required branch and closes the PR unmerged instead of merging
  it.* Deleting the phrase deletes the concept. **Replace the incident label with the mechanism it
  names.**

⛔ **A blanket regex delete is an explicitly prohibited implementation.**

## Goal

No marketplace skill document reasons from an incident the reader cannot see; every mechanism those
incidents named is stated in its own right; and a rule prevents the pattern from returning.

## Deliverables

1. **D1 — GATE: derive the population.** Mutates nothing. Widen well beyond the seed pattern to cover
   bare `#NNNN` in prose, pull-request URLs, dated phrasings ("as of 2026-07"), and version-pinned
   narration ("before 0.1.1240"). Report the count and the population scanned.
   *Done when:* the derived occurrence list exists with its derivation method stated.
   ⛔ **Do not begin edits until the population is derived.** The seed pattern — `plan-marshall#[0-9]+`,
   `PR #[0-9]+`, `(#[0-9]{3,4})`, `post-#[0-9]+`, `since #[0-9]+`, `Observed on ` — was one person's
   first cut. It is **a SAMPLE, not the population**, and the roughly 22 files / 30 occurrences it
   found are a **floor, not a total**.
2. **D2 — Classify every occurrence as DELETE or REPLACE**, with the verdict recorded **per
   occurrence**. A REPLACE names the mechanism that supersedes the incident label.
   *Done when:* every occurrence in D1's list carries exactly one verdict and REPLACE verdicts name
   their mechanism.
3. **D3 — Apply the classified edits.**
   *Done when:* the edits are applied and **every normative claim is preserved**.
   ⛔ **The test of a correct edit is that a reader who never saw the incident can still act correctly
   on the remaining prose.** Where removing a narrative would leave the mechanism unstated, **state the
   mechanism** — do not simply delete and shorten. Shortening a document by removing the only place a
   behaviour was explained is a regression wearing a cleanup label.
4. **D4 — A plugin-doctor rule so this cannot regress.** Flags incident references in marketplace docs
   and scripts.
   *Done when:* the rule ships, is **population-derived over the bundle tree** (never a hand-maintained
   list of known-bad files), and **publishes the population it examined**.
   ⚠ The hand-maintained-mirror archetype is at n≥5 in this epic — a rule that hardcodes today's
   offenders is the same defect one level up.
   ⚠ **The rule needs a sanctioned exemption** for genuinely-referential contexts **if D2 finds any**
   (an ADR legitimately citing its own decision record, for instance). **If D2 finds none, the rule is
   unconditional and says so** — an unused exemption mechanism is a hole nobody is watching.
5. **D5 — Tests, each verified to FAIL pre-fix.**
   - (a) The rule fires on a document carrying an `Observed on plan-marshall#NNNN` narrative.
   - (b) The rule does **not** fire on the D3-corrected mechanism prose. ⛔ This negative case is the
     one that proves REPLACE was implemented rather than DELETE.
   - (c) The rule's file population is derived and **asserted non-empty**.
   *Done when:* all three hold, and the report states each was seen red first.
6. **D6 — Two transitional-content instances one step outside the skills.** Same class, different
   location:
   - A measurement analysis document embedding a **point-in-time snapshot** — a "recent two-week
     analysis window", a transcript count, hard token totals, and named plans with billed figures.
     ⭐⭐ **This epic has independently retired every per-phase token figure as unreliable**, so the
     document is not merely stale by policy: **it publishes numbers the epic no longer stands behind.**
     Trim to the durable decision and its rationale, or relocate it to a dated record whose snapshot
     nature is explicit.
   - A refactor README maintaining "Landed" / "Resolved" / "open" status tables.
     ⛔ **This one is a DECISION, not a defect.** The source review filed it under *open decisions for
     maintainers*, and a roadmap may legitimately be exempt. **Confirm the exception is intentional; if
     kept, quarantine it clearly as planning material.** ⛔ **Do not silently delete a maintainer's
     roadmap on a standards argument** — that is a decision this run has no operator to make.
   *Done when:* the first is trimmed or relocated, and the second is either explicitly exempted with
   its quarantine stated, or recorded as needing an operator decision.

Six deliverables, at the split presumption — D6 is small and bounded, and separating it would produce a
second PR for two files.

## Out of scope

- **The root README surfacing only the snapshot install form.** The source review marks it *low,
  optional, purely navigational*, and the link resolves. Recorded here **so it is not re-filed as a
  gap** by a later sweep.
- **Building a fourth population-derived detector framework.** Three sibling plans in this epic already
  add plugin-doctor detectors. **Co-design the pattern; do not build a fourth.** If one has landed,
  read what it built before adding a parallel mechanism.
- **Rewriting history in the orchestrator ledger or in run reports.** Those are **records**, where
  incident references are correct and load-bearing. The rule targets normative documents only, and D4
  must not be scoped so widely that it flags a record for being a record.

## Expected surface

- `marketplace/bundles/**` — the identified files span `plan-marshall` and `pm-plugin-development`.
  Named dense sites, all **leads to re-ground by quoted phrase**: `ext-self-review-plan-marshall/SKILL.md`,
  `workflow-integration-github/scripts/_github_pr.py`, `automatic-review/standards/pr-agent.md`,
  `tools-integration-ci/standards/pr-operations.md`, `phase-6-finalize/standards/branch-cleanup.md`,
  `phase-6-finalize/SKILL.md`.
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/**` — the D4 rule home and the rule
  catalogue.
- The plugin-doctor tests.
- `doc/analysis/uncompressed-output-measurement.md` and `doc/refactor/README.md` (D6).
- **Open-ended:** whatever D1's widened derivation surfaces.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| `CLAUDE.md` § Documentation Standards prohibits version history, timestamps, and transitional content | OBSERVED | `CLAUDE.md` — re-read it; this is the plan's entire authority |
| Roughly 22 files carry ~30 occurrences under the seed pattern | HYPOTHESIS | ⛔ **D1's derivation.** The figure is a **floor** produced by one pattern, not a population — re-derive |
| A branch-cleanup document carries a full incident narrative whose mechanism the preceding sentence already states | HYPOTHESIS | that file — locate **by quoted phrase**, not by line number |
| Two occurrences use "PR #866" as a term of art for a real merge-queue behaviour | HYPOTHESIS | the pr-operations standard — by quoted phrase. ⛔ **These are the REPLACE arm**; getting this wrong deletes a concept |
| The true population exceeds the seed pattern | HYPOTHESIS | **D1 itself** |
| No occurrence requires a permanent exemption | HYPOTHESIS | **D2's classification.** ⛔ An asserted **absence**, and it decides whether D4 needs an exemption mechanism at all |
| The measurement document still exists and embeds a point-in-time snapshot | HYPOTHESIS | that file |
| The refactor README still maintains status tables | HYPOTHESIS | that file — ⛔ and its disposition is a **decision**, not a defect |
| Per-phase token figures have been retired as unreliable by this epic | HYPOTHESIS | ⛔ **not verifiable from this clone** — it comes from the epic ledger. Treat as motivation for trimming the document, not as evidence to cite in it |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim. ⚠ **Every line number this
plan might have inherited is stale by construction; re-ground by symbol or quoted phrase.**

## Verification

- ⛔ **D3's edits are text-whose-value-is-what-a-reader-does**, so they get a **cold read** — and it is
  the check that decides whether this plan succeeded. Give the Step 6 verification sub-agent the
  **edited** passages with no other context, and ask what behaviour each describes and what it should
  do about it. If a reader who never saw the incident cannot act correctly, the edit deleted meaning
  rather than noise.
- ⛔ **D5(b) is the load-bearing negative test.** A rule that fires on the corrected mechanism prose
  would push a future author back toward deleting the concept — the opposite of what D2's REPLACE arm
  decided.
- **D4 must publish its population size.** A rule reporting clean over an empty file set is
  indistinguishable from a clean tree, and that archetype is this epic's namesake.
- Report the derived population and the occurrence count **separately**. A count of files examined is a
  **volume**, not coverage.
- Doc and Python changes are expected, so the build gate takes its full path.

## Notes

- ⛔ **Sequencing: this is wide, shallow, and lands in files other plans edit.** It reaches
  `branch-cleanup.md`, `pr-operations.md`, `pr-agent.md`, `_github_pr.py`, and
  `phase-6-finalize/SKILL.md` — all high-traffic. **Sequence LAST among the finalize-surface plans**,
  or **scope D3 to exclude any file with an in-flight owner and record the exclusions as residue.**
  Silently editing a file another plan is mid-way through is how both PRs end up in conflict.
- ⛔ **Do not go looking for the orchestrator spec, the retired review document, or any landing
  record.** The first and last live under `.plan/`, which is git-ignored and absent from this clone;
  the review is being retired and its still-valid findings are transcribed into D6. Everything needed
  is in this file.
