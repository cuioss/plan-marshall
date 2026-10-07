envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-08-01
epic=truthful-signals
kind=finding
created=2026-08-08T16:33:10Z

## Routed lessons cluster C16 — test-authoring discipline (13 corpus instances)

**From**: `lessons-handling-26-08-08-01` (lessons-handling orchestrator run, 2026-08-08).
**Suggested home**: **NEW spec**.
⛔ **Do not route this back to `test-suite-quality`.** That epic is CLOSED and ARCHIVED at 10/10
and the standing instruction is not to reopen it a third time; its residue was already handed to
you. This cluster is more of that residue, not a reason to reopen.
**You decide**: stage, fold, split, or decline. Nothing was written into your tree.

### The cluster

Thirteen active lessons where a test passed while testing nothing, or failed while the code was
correct.

**The fixture does not represent production:**

| Lesson | Claim |
|--------|-------|
| 2026-07-09-14-001 | detector/parser fixtures must mirror the **post-normalization** production data shape, or a boundary-anchored regex passes tests yet is **dead in production** |
| 2026-07-17-08-002 | a new fail-loud precondition that breaks a pre-existing test means the fixture never seeded the now-required state — **fix the fixture, not the guard** |
| 2026-06-24-09-001 | a declarative key validated by a cross-cutting test in a **different module** is invisible to per-bundle module-tests; same-basename test files collide under pytest prepend import |

**The assertion targets the wrong surface:**

| Lesson | Claim |
|--------|-------|
| 2026-08-02-15-003 | **assert the surface the caller queries**, not the stage that feeds it |
| 2026-07-28-22-001 | a path-classifying predicate must match the **repo-RELATIVE** path, never the absolute path |
| 2026-07-28-08-002 | a doc-claimed concurrency property (idempotent, safe-to-resume) needs an **interleaving test**, not a prose-presence assertion |

**The harness itself breaks the property under test:**

| Lesson | Claim |
|--------|-------|
| 2026-07-22-11-001 | a cwd/state isolation guard written as an **autouse fixture cannot see monkeypatch restores** and false-positives on correct usage — it belongs in a `pytest_runtest_teardown` hook wrapper |
| 2026-07-23-10-001 | a per-session `--basetemp` **inside the repo tree** breaks isolation tests that assume `tmp_path` is outside any git repo; upward-walking resolvers escape the nested fixture into the real repo |
| 2026-07-21-17-001 | a shared test-helper module needs **BOTH** `sys.path` and `mypy_path` registration under `explicit_package_bases` |

**The gate that would run the test never runs:**

| Lesson | Claim |
|--------|-------|
| 2026-07-12-15-001 | a docs-only deliverable that changes a pinned script call-shape breaks narrative-contract module-tests, but **plugin-doctor-only verification never runs them** |
| 2026-07-12-18-002 | evolving a shared handler's argparse contract breaks synthetic-`Namespace` unit tests: use `getattr` for the new attribute and sweep the old required-flag contract tests |
| 2026-07-16-17-007 | wired-flow assertions must cover **every** new security binding/overload; finalize security-audit is the backstop |
| 2026-07-21-15-002 | fail-closed guard promotion owed to `persona-module-tester` (deferred post-merge) |

### The through-line

Seven of the thirteen are one statement: **a green test is evidence about the fixture, not about
production**, unless the fixture is derived from production. `2026-07-09-14-001` is the extreme
case — a regex that passes every test and is *dead in production* — and it is the argument for
the reference pattern the project already has: a **population-derived** detector, per
`test/_shared/_dispatch_roster.py`, where the test's own population is the live registry rather
than a hand-list.

That connects this cluster directly to `PLAN-TRUTH-042`: a check that can return 0 from an empty
population and a test that passes against a fixture production never produces are the same
defect at two altitudes. If TRUTH-042's detector work lands first, this cluster should reuse its
population-derivation rather than invent a second one.

`2026-07-21-15-002` is an **explicitly deferred debt** ("owed, deferred post-merge") — it should
either be scheduled or retired, not left as a standing note.

### Claim labels

- **OBSERVED**: lesson ids, components, categories, titles; the absence of a covering plan.
- **HYPOTHESIS (verify-at-outline)**: that each is still live. Confirm/refute artifacts: the
  named fixture or conftest in each case; for `2026-07-09-14-001`, the boundary-anchored regex
  itself, checked against real post-normalization input.

### Provenance

Corpus snapshot: `.plan/local/orchestrator/lessons-handling-26-08-08-01/archive/{lesson_id}.md`.
Dispositions: `.plan/local/orchestrator/lessons-handling-26-08-08-01/dispositions.md`.
Nothing retired; retirement is deferred behind your running `PLAN-TRUTH-044`.
