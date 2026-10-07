envelope_version=1
sender_type=plan
sender_id=fail-closed-signal-integrity
epic=truthful-signals
kind=finding
created=2026-08-02T22:10:56Z

# D5 lesson retirement — completed late, with three trims still owed

## What happened

`project:finalize-step-lessons-housekeeping` classified all 8 carried lessons
correctly at order 4 but could not APPLY any disposition: `restore-from-plan`
returned `success / no_lesson_file` while all 8 `lesson-*.md` files sat in the plan
directory, because the plan dir was worktree-resident and the verb resolves
main-anchored only (filed separately as `-002.md`).

The orchestrator applied the classification manually AFTER `integrate_into_main`
moved the plan directory back to main, at which point `restore-from-plan` worked on
the first attempt and returned `restored_count: 8`. That is the confirmation the
`-002.md` root cause is exactly the worktree-residency condition and nothing else.

## Applied (4 retired, tombstoned)

- `2026-07-22-16-003` — failure mode eliminated; the stamp is now a conjunction with
  a build-executing-subcommand allow-list. No residue.
- `2026-07-11-15-001` — rule promoted to clause (d). ⚠ Its FIRST retirement
  justification this run was false: it cited a worked example that itself branched
  on a change flag and so demonstrated the anti-pattern the clause forbids. The
  example was corrected in the same PR before the retirement was re-applied.
- `2026-07-07-17-001` — rules 1–2 → clauses (a)/(b); rule 3 residue promoted to
  `persona-module-tester/standards/testing-coverage.md`.
- `2026-07-24-13-002` — corrective rule → clause (c); test residue promoted to the
  same standards file.

## Retained (1, deliberate)

- `2026-07-23-01-002` — bias-to-retain. It governs a *gate* whose scope filter
  excludes items lacking the key it enforces, not a classifier verdict, and the
  vacuous-guard archetype is an open recurrence.

## ⛔ STILL OWED — three trims, not applied

These are **partially** covered. Each has a covered portion that should be cut and
an uncovered portion that must survive. Nothing was edited, so each lesson currently
carries its covered half as if still open:

- `2026-07-16-14-001` — axes 2–3 are covered by clauses (b)/(c)/(e). **KEEP** axis 1
  (a scoping input must be required) and axis 4 (an exactly-once guard must be
  evaluated before the classification it suppresses). Clause (a) governs match-table
  row order, which is a different thing — do not treat it as covering axis 4.
- `2026-06-21-21-001` — only the fail-open `None`-wildcard bullet is covered.
  **KEEP** the naive-vs-aware datetime normalization bullet and the
  `gh api --paginate` requires `--slurp` bullet.
- `2026-07-22-12-003` — rule 1 is covered by clause (e). **KEEP** rules 2–3
  (corroborate a routed build's outer envelope against the daemon job log; an
  implausible duration is a first-class failure signal).

The trims were deferred on cost at the end of a 13-hour run, not on judgement. A
trim requires rewriting each body to drop only the covered portion, which is
exactly the operation most likely to lose the uncovered half if done carelessly —
so it wants a fresh context, not a tired one.

## Standing hazard this exposes

The housekeeping step's classification and its application are separated by an
ordering constraint that currently cannot satisfy both halves (filed as `-003.md`).
Until that is resolved, **a green `lessons-housekeeping` step does not mean any
lesson was actually retired** — it may mean only that the classification ran. That
is the same read-a-confident-signal hazard this epic tracks, one layer up.
