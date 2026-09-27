# PLAN-LR-01: Derive the corpus and the audience axis

epic: lessons-routing
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Objective

**The epic's gate.** Nothing else here is designed until two populations exist, because every candidate
answer downstream is a function of them and both are currently guesses.

⛔ **This plan changes no behaviour.** It is a derivation plan whose entire output is two published
populations and one settled question. A deliverable that edits a routing code path belongs to a later
plan and must be refused here.

## Deliverables

Four deliverables. This plan is deliberately small; its value is that everything after it stops
guessing.

**D1 — enumerate the real consumer-repo corpus, with its denominator.** Project memory names four
consumer repos (`nifi-extensions`, `cui-jsf-test-basic`, `TokenSheriff`, `API-Sheriff`); **two were
sampled at staging and the other two were not.** For every consumer repo reachable on this machine,
enumerate `.plan/local/lessons-learned/` and classify each lesson: component, whether its component
bears a bundle prefix, and whether the *reader of that store* could act on it.

⛔ **Publish the population AND its denominator.** *"Five stranded findings"* is inadmissible without
*"across N of M consumer repos, M enumerated as follows"*. ⚠ An unreachable repo is reported as
unreachable — **not** omitted, and **not** counted as zero. This epic's parent project has recorded
that an omission is indistinguishable from an empty population.

⭐ **Lead from cleanup 2026-09-23 (re-derive, do not inherit): all four repos are reachable and the
corpus has moved since staging.** A spot-check found `cui-jsf-test-basic` 4 lessons (3 stranded,
unchanged), `API-Sheriff` **16** live lessons + 32 tombstones (its 2 originally-named lessons are
retired — the corpus this plan will read is NOT the one staged against), `nifi-extensions` (never
sampled before) 20 lessons including **2 more** stranded `plan-marshall:*` findings, `TokenSheriff` 0
live + 59 tombstones. This makes the denominator cheaply derivable (0 of 4 unreachable) but the
POPULATION itself is a moving target — do not treat the counts above as D1's answer; re-run the
enumeration fresh at outline and expect a different total than either the staging snapshot or this note.

**D2 — SETTLED at cleanup 2026-09-23, re-derive-to-confirm rather than investigate from scratch.**
`cui-jsf-test-basic` holds three `plan-marshall:*` lessons; the `wrong_store` guard was introduced
2026-07-17 (`git log -S wrong_store` → `0797452a4`, "fix(manage-lessons): refuse to file a lesson into
a wrong-store repo") and the three lessons are dated 2026-06-15/16 — **a month before the guard
existed**. They predate the guard; they were not filed with `--allow-foreign-store`. ⚠ **Re-derive
this at outline** (the commit hash and the three `created=` dates) rather than trusting this note
verbatim — the point of D2 is a checked answer, not an inherited one — but do not re-investigate the
bypass hypothesis as live: it is refuted. This also falsifies the "laundering" framing in
`PLAN-LR-02` D3 (see that spec) — the three known lessons were never routed through
`--allow-foreign-store` at all. ⚠ **`nifi-extensions` was NOT part of the original 4-lesson
`cui-jsf-test-basic` question and needs its own check**: it independently carries a stranded
`plan-marshall:build-maven` lesson dated `2026-07-16-21-002` — one day BEFORE the guard's commit —
which is genuinely ambiguous (same-day-adjacent) and does need D2's original investigation applied to
it, unlike the three now-settled `cui-jsf-test-basic` ones.

**D3 — read the three stranded upstream findings and state what they say.** They are real findings
about *this* project, filed by a real consumer, that nobody here has read. ⭐ **This is the deliverable
most likely to be undervalued and it should not be**: the epic exists because these were lost, and the
cheapest possible proof that the loss matters is to find out what was in them. ⚠ Their disposition —
folding into an existing epic, staging work, or discarding — is the ORCHESTRATOR's, not this plan's.
Report them; do not route them.

**D4 — settle the audience axis: derived or declared?** Two candidate designs, and the choice governs
every later plan:

| | Derived | Declared |
|---|---|---|
| Mechanism | infer audience from the component prefix and the repo's own identity | the filer states the audience at `add` time |
| For | no new field; works on the existing corpus retroactively | unambiguous; survives a component whose prefix means nothing to the resolver |
| Against | **it is what the current guard does, and it is what fails** — `api-sheriff:maven-build` and `plan-marshall:build-maven` are indistinguishable to it | a new required argument on a widely-called verb; a filer can get it wrong |

⭐ **State a recommendation with its reasoning; do NOT implement either.** ⛔ The known-failing
predicate — *does `marketplace/bundles/{prefix}` exist in this repo* — is the control case any proposed
derivation must be tested against, because it is the one design already proven to return the same
answer for both classes.

## Expected Surface

Read-only. This plan writes a findings artifact and edits no routing code.

- `marketplace/bundles/plan-marshall/skills/manage-lessons/**` *(READ-ONLY — the guard and store
  resolution, for D2 and D4)*
- consumer repo checkouts under `~/git/**/.plan/local/lessons-learned/` *(READ-ONLY, cross-repo)*

## Dependencies and Sequencing

⛔ **Re-derive with `corpus cross-check` at emit time.** This is a new epic and its corpus has not been
cross-checked against the four sibling epics; the parent project has recorded three consecutive
occasions on which a hand-written collision map missed cross-epic overlaps.

- **Depends on:** nothing. **Blocks:** every other plan in this epic.
- ⚠ Cross-repo reads are within the small-ops carve-out (read-only, `git -C`), but this plan touches
  repositories outside this checkout. ⛔ **It may not WRITE to any consumer repo.**

## Claim Labels

Every claim below was read first-party at HEAD `77c9dc70a` on 2026-08-24 unless labelled otherwise.

- OBSERVED: `.plan/*` is git-ignored with exceptions only for `marshal.json` and `project-architecture/`, so the lessons corpus is untracked by construction — read at `.gitignore` § line 45, corroborated by `git ls-files .plan/local` returning 0 tracked files. (Stale count corrected 2026-09-23: `.plan/orchestrator/` and `.plan/archived-orchestrators/` were un-ignored by `#1557` after staging, so `git ls-files .plan` is now 5151, not the original 15 — the load-bearing part of the claim, that `.plan/local/` specifically stays untracked, is unaffected and re-verified directly above.)
  - verdict: contradicted | checked_at: 14d8f3ccd | by: lessons-routing/cleanup | rescoped: yes | evidence: git ls-files .plan = 5151 not 15 (orchestrator dirs un-ignored by #1557 after staging); git ls-files .plan/local = 0, confirming the load-bearing conclusion (lessons corpus untracked) survives; spec text corrected to cite the local-only count
- OBSERVED: `cui-jsf-test-basic` holds 4 lessons, 3 of them `plan-marshall:*` — read at `~/git/cui-jsf-test-basic/.plan/local/lessons-learned/*.md` § `component=` headers.
  - verdict: corroborated | checked_at: 14d8f3ccd | by: lessons-routing/cleanup | rescoped: n/a | evidence: git -C ~/git/cui-jsf-test-basic ls-files --others --ignored --exclude-standard = 4 .md; component headers confirm cui-jsf-test-basic + 3x plan-marshall:*
- OBSERVED: `API-Sheriff` has no `marketplace/bundles/` directory, so `api-sheriff:maven-build` fails the `wrong_store` ownership predicate exactly as `plan-marshall:build-maven` does — read at `~/git/API-Sheriff/` § absent path.
  - verdict: corroborated | checked_at: 14d8f3ccd | by: lessons-routing/cleanup | rescoped: n/a | evidence: git -C ~/git/API-Sheriff ls-files marketplace returns empty; repo confirmed via rev-parse --show-toplevel
- OBSERVED: `--allow-foreign-store` leaves no trace on the filed lesson distinguishing a bypassed filing from a native one — read at `manage-lessons/SKILL.md` § `:108`, and confirmed against the stored lesson headers, which carry no such marker.
  - verdict: corroborated | checked_at: 14d8f3ccd | by: lessons-routing/cleanup | rescoped: n/a | evidence: SKILL.md:108 documents no recording; _lessons_io.guard_component_store_match returns silently on override; write_lesson_to renders only metadata.items(); empirically 16 API-Sheriff lessons filed today carry no such marker
- HYPOTHESIS: the three stranded lessons were filed WITH `--allow-foreign-store` rather than before the guard existed — confirm/refute at `manage-lessons` git history § the commit adding the `wrong_store` guard, against the lessons' `created=` dates (verify-at-outline). **This is D2's whole subject; it is a hypothesis, not a premise.**
  - verdict: contradicted | checked_at: 14d8f3ccd | by: lessons-routing/cleanup | rescoped: yes | evidence: REFUTED: wrong_store guard introduced 2026-07-17 (git log -S wrong_store -> 0797452a4); the 3 cui-jsf-test-basic lessons are dated 2026-06-15/16, a month before the guard existed - they predate it and were not filed with --allow-foreign-store. D2 rewritten to record this as settled; nifi-extensions' own same-day-adjacent lesson flagged as the remaining genuinely ambiguous case
- HYPOTHESIS: the four consumer repos named in project memory are the complete population — confirm/refute at `~/git/` § checkout enumeration (verify-at-outline). D1's denominator depends on it.
  - verdict: unverifiable | checked_at: 14d8f3ccd | by: lessons-routing/cleanup | rescoped: n/a | evidence: all 4 named repos confirmed reachable (git -C {repo} rev-parse --show-toplevel succeeds for all); completeness of the wider ~/git population needs a directory enumeration outside this tool's reach in a cleanup pass
- Verify-first clause: D1's published denominator must name every consumer repo it could NOT reach, since an unreachable repo reported as zero is the failure this plan exists to measure.
  - verdict: corroborated | checked_at: 14d8f3ccd | by: lessons-routing/cleanup | rescoped: n/a | evidence: still binding and now cheap: 0 of 4 named repos unreachable, verified per-repo via git -C rev-parse + ls-files --others --ignored
