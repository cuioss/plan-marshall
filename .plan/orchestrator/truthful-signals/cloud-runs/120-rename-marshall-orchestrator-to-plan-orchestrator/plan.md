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

# Rename `marshall-orchestrator` → `plan-orchestrator` (and its persona)

**Epic:** truthful-signals
**Branch prefix:** chore

## Problem

Two skills carry "marshall" in a name where it does not belong, because they orchestrate **plans**,
not the marshal configuration surface:

- `marshall-orchestrator` → `plan-orchestrator` (the verb skill)
- `persona-marshall-orchestrator` → `persona-plan-orchestrator` (the persona)

The rename is purely cosmetic in effect and **maximal in blast radius**: it moves three directories
and rewrites every reference to them across bundles, docs, tests, registration, and the generated
executor's three-part script notation.

⛔ **THIS IS AN EXCLUSIVE PLAN.** It cannot run concurrently with anything touching the orchestrator
surface, and that is most of this epic's queue — around ten other staged plans name
`marshall-orchestrator` in their expected surface. A large rename landing mid-flight against any of
them produces a rebase conflict in every one.

⭐ **And it must be sequenced LAST on that surface, never first.** Every other orchestrator plan
changes *behaviour* and is the reason the surface exists; this one changes only *names*. Renaming
first forces ten specs to be re-grounded against new paths for zero behavioural gain. Renaming last
re-grounds exactly one spec — this one — against a settled surface. **A pure-rename plan should always
be the last writer on its surface.**

## Goal

Neither skill name contains "marshall" anywhere in source, documentation, tests, or registration; the
generated executor resolves the new three-part notation; and nothing that legitimately contains
"marshall" has been touched.

## Deliverables

1. **D0 — GATE: re-derive the surface at HEAD.** Mutates nothing. Produce the full file list, and
   **classify every hit as rename-target versus must-not-touch**.
   *Done when:* the list exists with both classifications, and the population it was derived from is
   stated.
   ⛔ **THE EXCLUSION SET IS THE ENTIRE RISK OF THIS PLAN.** `marshall-steward`, `marshalld`,
   `marshal.json`, and the `plan-marshall` bundle name must **not** change. A naive
   `marshall` → `plan` substitution corrupts all four. **Match `marshall-orchestrator` and
   `persona-marshall-orchestrator` exactly**, never the bare word.
   ⛔ **Do not scope from any count in this document.** Two successive readings of this surface
   disagreed by roughly 74% in file count — an earlier enumeration found ~131 references across 31
   files, a later one ~210 lines across 54 files. The surface **grows**, which is precisely why D0 is a
   gate.
   ⚠ Note the subset relation: `persona-marshall-orchestrator` **contains** `marshall-orchestrator` as
   a substring, so the two match sets overlap. The file count is the union, not the sum — an error
   that would otherwise inflate the reported surface.
2. **D1 — Rename the three directories.** The two skill directories under
   `marketplace/bundles/plan-marshall/skills/`, and the test directory under `test/plan-marshall/`.
   *Done when:* all three are moved with history preserved.
3. **D2 — Update every in-tree reference to the two skills**, including the three-part script notation
   (`plan-marshall:marshall-orchestrator:orchestrator` → `plan-marshall:plan-orchestrator:orchestrator`;
   the third segment is unchanged).
   *Done when:* D0's rename-target list is fully applied and its must-not-touch list is untouched.
4. **D3 — Update the cross-referencing skills and the concept documentation.** The skills that
   cross-reference the orchestrator store (`platform-runtime`, `manage-logging`, `manage-status`,
   `manage-terminal-title`, plus whatever else D0 finds), the bundle `plugin.json` and README, and the
   AsciiDoc concept files.
   *Done when:* all are updated. ⚠ **The concept docs were called out for explicit re-checking** —
   they are the surface most likely to be missed by a source-focused sweep.
5. **D4 — Regenerate the executor** against the new three-part paths.
   *Done when:* the executor resolves the new notation.
6. **D5 — Acceptance, each check verified.** Zero remaining `marshall-orchestrator` /
   `persona-marshall-orchestrator` strings under `marketplace/`, `doc/`, `test/`, `plugin.json`, and
   the README; the plugin-doctor gate clean; the full test suite green.
   ⛔ **A search returning zero is only meaningful with a matched positive control.** Assert the sweep
   **finds a deliberately-planted occurrence** before trusting the zero — otherwise the acceptance
   check is this epic's own vacuous-guard archetype, passing because it examined nothing.
7. **D6 — The `.plan/` ledger is explicitly NOT rewritten.** The orchestrator tree holds hundreds of
   references as **historical records, not source**.
   *Done when:* this is stated as a non-goal in the report and asserted, so nobody "completes" the
   rename by editing history.
   ⚠ Not reachable from this clone in any case — `.plan/` is git-ignored — but the non-goal is stated
   so a future local run does not do it.

Seven deliverables, under the raised cap. ⛔ **NOT to be merged with any other plan** — merging
anything in would widen an already-maximal blast radius.

## Out of scope

- **`marshall-steward`, `marshalld`, `marshal.json`, and the `plan-marshall` bundle name.** All four
  legitimately contain "marshall" or "marshal". They are the reason this rename must match exact
  compound tokens rather than a word, and touching any of them is a corruption, not a completion.
- **Any behaviour change whatsoever.** This is a rename. A defect noticed in passing is **reported,
  not fixed** — a behavioural diff hidden inside a 54-file rename is unreviewable, and the review
  budget for this PR is already spent on verifying that nothing changed.
- **Rewriting the orchestrator ledger's historical references.** See D6. Records are not source.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/marshall-orchestrator/` → `.../plan-orchestrator/`
- `marketplace/bundles/plan-marshall/skills/persona-marshall-orchestrator/` →
  `.../persona-plan-orchestrator/`
- `test/plan-marshall/marshall-orchestrator/` → `test/plan-marshall/plan-orchestrator/`
- `marketplace/bundles/plan-marshall/.claude-plugin/plugin.json` and
  `marketplace/bundles/plan-marshall/README.md` — registration.
- Cross-referencing skills: `platform-runtime`, `manage-logging`, `manage-status`,
  `manage-terminal-title`, plus whatever D0 adds.
- `doc/concepts/orchestration.adoc`, `doc/concepts/personas.adoc`, and the planning-workflow and
  top-level README AsciiDoc files.
- Tests: `test_orchestrator.py`, `test_orchestrator_archive.py`, `test_logging_orchestrator_store.py`.
- The generated executor.

⛔ **This enumeration is a LEAD, superseded by D0's derivation.** It is written down so D0 has
something to reconcile against, not so it can be trusted.

## Claim labels

⚠⚠ **This plan is derived from a spec that carried NO claim-label section.** Labels were deliberately
**not** retrofitted at authoring time: assigning `OBSERVED` to a claim the author did not personally
verify manufactures provenance, and a wrong label reads as a checked one.

⇒ **Treat EVERY claim below as `HYPOTHESIS` until this run verifies it**, including every count and
every path. ⭐ **Asserted absences are the higher-risk half.**

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The surface is ~210 matching lines across 54 unique files | HYPOTHESIS | ⛔ **D0's own derivation.** Two prior readings disagreed by ~74% in file count. **Do not scope on either number** |
| `persona-marshall-orchestrator` matches are a strict subset of `marshall-orchestrator` matches | HYPOTHESIS | the two searches — cheap to check, and it decides whether the surface is a union or a sum |
| Exactly three directories need renaming | HYPOTHESIS | a directory listing under the two parent paths. An asserted **completeness** claim, which is the absence-shaped half |
| `marshall-steward`, `marshalld`, `marshal.json`, and `plan-marshall` must not be touched | HYPOTHESIS | each is a real, separate thing — confirm each exists under its own name before excluding it, so the exclusion list is derived rather than assumed |
| The concept AsciiDoc files reference the old names | HYPOTHESIS | those files. ⚠ **Explicitly called out for re-checking** because a source-focused sweep misses documentation |
| The executor's third notation segment (`orchestrator`) is unchanged by the rename | HYPOTHESIS | the executor generation path — a wrong assumption here silently breaks every orchestrator invocation |
| No consumer outside this repository depends on the old skill name | HYPOTHESIS | ⛔ asserted **absence**, and **not verifiable from this clone**. Record it as unverifiable rather than asserting it |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D5's zero-result sweep needs a matched positive control, and this is the single most important
  check in the plan.** Plant a known occurrence, confirm the sweep finds it, remove it, then trust the
  zero. Without the control, "grep returned nothing" is indistinguishable from "grep was pointed at
  the wrong tree" — which is exactly the vacuous-guard archetype this epic exists to close, and it
  would be badly ironic to ship it inside a truthful-signals plan.
- **Assert the must-not-touch set is genuinely untouched**, by name, in the report. A rename that
  quietly caught `marshall-steward` would pass a "zero remaining old strings" check while breaking a
  different skill.
- **The full test suite must be green, not merely the orchestrator tests** — a rename's failure mode is
  a reference somewhere nobody thought to look.
- Python, doc, test, and registration changes are expected, so the build gate takes its full path.

## Notes

- ⚠ **Sequencing is a hard constraint, not a preference.** Run this **alone**, and **last** among the
  plans touching the orchestrator surface. Effective concurrency for its duration is one.
- **After this lands**, the orchestrator command path becomes
  `plan-marshall:plan-orchestrator:orchestrator` and the old path stops resolving. Anything holding
  the old string — including local tooling and any operator's muscle memory — needs the executor
  regenerated and the plugin cache synced before it works again. Say so in the report.
- ⭐ **A precondition note that outlived its precondition** was found in the source spec: it insisted
  the hand-off must carry the brief inline because a referenced-spec-reading feature did not exist
  yet. That feature had since shipped, and following the stale note would have re-introduced the exact
  retyping drift its retirement removed. The general shape — **a blocking note nobody re-read after
  its blocker cleared** — recurred on at least three specs in the same review. Worth watching for in
  this one too.
- This plan is **off the epic's truthful-signals theme**: it is the epic's closing refactor, carried
  here at the operator's request.
- ⛔ **Do not go looking for the orchestrator spec or any landing record.** They live under `.plan/`,
  which is git-ignored and absent from this clone. Everything needed is in this file.
