# Landing Analysis: PLAN-09 — plan-retrospective Check Correctness

epic: test-suite-quality
workstream: WS-03
pr: #998 — merged as `a594c94a4` (2026-07-25, squash → merge queue)

> Landing record. The lesson-consumption dispositions were verified against the live lessons
> store, not accepted from the plan report — the "trimmed, not retired" claims are the ones
> that most needed checking, and they hold.

## Deliverable Fidelity vs Spec

5 staged, 5 shipped, each with a regression test that fails when the check is voided (exactly the
"failed-open needs a fail-when-voided test" instruction). D1 verified in code: `_AFFECTED_FILE_BULLET_RE`
(`check-artifact-consistency.py:80`) now matches `` `path`[^\n]* `` — the intent annotation after the
closing backtick is accepted, closing the double-false-green. All five surfaces are `plan-retrospective`
scripts, as declared.

## Lesson consumption — verified against the live store, not the report

| Lesson | Reported | Store check | Verdict |
|--------|----------|-------------|---------|
| `2026-07-22-22-001` | retired | **absent** | ✅ retired |
| `2026-07-22-22-002` | retired | **absent** | ✅ retired (promotion also closed a live doc-contract drift) |
| `2026-07-22-12-002` | retired | **absent** | ✅ retired |
| `2026-06-20-17-003` | trimmed | **present, REWRITTEN** — title now "direct-gh-glab-usage and execution-context-dispatch-audit have no registerable SECTION_SPEC key" | ✅ correct trim — the chat-history-analysis instance was fixed (D3); the two still-unfixed members remain |
| `2026-07-17-11-001` | trimmed | **present, REWRITTEN** — title now "phase-5-execute never emits its 'Starting execute phase' line, so starting_markers is always 0" | ✅ correct trim + ownership reassigned to `phase-5-execute` |

**This is the consume-and-retire directive working as intended.** The plan retired only what it fully
fixed and trimmed (not falsely retired) the two lessons carrying open residue beyond its scope. The
verify-still-open gate did its job — no blind retirement.

## New lesson filed (the plan caught its own incomplete fix)

`2026-07-25-19-001` (`phase-3-outline`, anti-pattern) — CodeRabbit found that `cluster_dispatches` still
scanned `script_log_lines` while the corroborating marker counts scanned only `work_log_lines`, an
uncorroborable fact channel defended in the docstring as a "harmless no-op." **Neither outline nor
Q-Gate caught it** — the same vacuous-channel archetype the plan exists to remove, recurring inside the
plan's own code. Fixed with a dedicated regression test. This is a genuinely useful meta-lesson; it
stays as a standing lesson (a process gap, not a code defect to schedule).

## Two residue items this landing surfaced — candidates for follow-up, NOT silently dropped

1. **`2026-06-20-17-003` residue (plan-retrospective).** The completeness guard scans only `SKILL.md`,
   so `direct-gh-glab-usage` and `execution-context-dispatch-audit` are almost certainly the **same
   `SECTION_SPEC` defect a 2nd and 3rd time** — the aspect exists but has no registerable key. Same
   surface as PLAN-09. A natural follow-up: generalize the guard to scan all governing docs, not just
   `SKILL.md`, and register the two missing keys.
2. **`2026-07-17-11-001` residue (phase-5-execute).** The trimmed lesson's true root cause is that
   `phase-5-execute` never emits its documented "Starting execute phase" marker line, so
   `starting_markers` is structurally always 0. Different surface (phase-5, not retrospective) — a
   small marker-emission fix.

Both are recorded in Watches with owners; the grouping/scheduling decision is surfaced to the operator
(see the epic Decisions entry) rather than unilaterally staged, because it bears on whether this epic
keeps absorbing machinery defects its own fixes uncover.

## Metrics and Routing

- Tokens **3.5 M**; **4 h 38 m wall**. Review: 1 reviewer, 4 comments → 3 fix tasks, 75 % resolved-as-fixed
  — the first plan in the campaign with a **non-trivial bot yield** (contrast the near-zero yield on the
  test-refactor plans; a script-logic diff gives the bots something to bite).
- `finalize-step-simplify` deleted 1 dead function; `pre-submission-self-review` clean (117 candidates).
- Merged via queue (squash); main up-to-date, worktree removed, plan archived.
- **Unrelated:** working tree carries one uncommitted `marshal.json` change
  (`orchestrator.parallelization_scope`) from upstream PR #997 — not this plan's, not the epic's.

## Reconciliation Actions

- [x] status.json `plans[]` PLAN-09 → `shipped`
- [x] epic.md queue row reconciled; retrospective-tooling watch retired (3 lessons gone)
- [x] Watch added: `2026-06-20-17-003` residue (completeness guard scans only SKILL.md) — plan-retrospective
- [x] Watch added: `2026-07-17-11-001` residue (phase-5 marker line) — phase-5-execute
- [x] resume_anchor updated; START-HERE regenerated
- [x] Grouping/scheduling of the two residue items surfaced to the operator

## Follow-Ups

- Operator decision pending: fold the two residue items into a follow-up plan (WS-03 PLAN-10 candidate,
  plan-retrospective completeness-guard generalization) or spin out — see Decisions.
- `marshal.json` provisioned version stale — `/marshall-steward` when convenient.
