envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-08-01
epic=truthful-signals
kind=finding
created=2026-08-08T16:33:34Z

## Routed lessons cluster C21 — execute-phase yield and artifact loss (8 corpus instances)

**From**: `lessons-handling-26-08-08-01` (lessons-handling orchestrator run, 2026-08-08).
**Suggested home**: **NEW spec**. Nothing in your queue owns the phase-5 yield boundary.
**You decide**: stage, fold, split, or decline. Nothing was written into your tree.

### The cluster

Eight active lessons where phase-5 completed without doing, running, or recording what it
claimed.

**Work ships unexecuted:**

| Lesson | Claim |
|--------|-------|
| 2026-08-03-17-002 | the **orchestrator-tier yield boundary lets a task's own newly-authored tests ship unexecuted** |
| 2026-06-21-00-003 | the `module_testing` task profile ran only module-tests (pytest), **not quality-gate** (ruff+mypy), letting an F401 defect slip past phase-5 to the phase-6 verify gate |
| 2026-06-20-23-001 | end-of-phase verification must run **full** verify when a plan changes a widely-consumed default; module-scoped verify misses project-local test dirs |
| 2026-07-16-17-008 | behaviour-changing fixes must sweep **ALL reactor consumers**, not just the changed module's own tests |

**Evidence is lost or never emitted:**

| Lesson | Claim |
|--------|-------|
| 2026-07-21-17-005 | **ARTIFACT emission stops after the first task of the first execute envelope** |
| 2026-07-17-09-003 | rewriting the persisted task file **BEFORE** the resolution/validation gate **loses data on gate failure** — return-then-persist so the write happens only after the gate clears |

**A deliverable passes while incomplete, or a compliant one is blocked:**

| Lesson | Claim |
|--------|-------|
| 2026-06-20-16-004 | a doc-port deliverable shipped structurally-valid content that **omitted the deliverable's enumerated required points** and passed the scoped plugin-doctor gate; only orchestrator content-verification against success criteria caught it |
| 2026-08-08-11-001 | `assert_test_identifiers` reports every **PARAMETRIZED** test as missing when the caller supplies the documented bare-function nodeid, so a compliant `module_testing` task is spuriously blocked |

### Why this is one cluster and not three

The unifying claim: **phase-5's completion signal is not evidence that phase-5's work happened.**
Tests authored but not run, a profile that runs half its contract, artifacts that stop emitting
after the first task, a persisted write that vanishes on gate failure — each independently
severs the link between "the phase reported done" and "the work was done and observed".

`2026-08-03-17-002` is the load-bearing one: a task's **own** new tests can ship unexecuted. That
means a plan can add a test, report green, and have never run the thing it added — which makes
every "tests added" claim in a plan record unverified by default.

`2026-07-21-17-005` compounds it: with ARTIFACT emission stopping after the first task, there is
no per-task evidence trail to detect the above from. The defect and the instrument that would
find it fail together.

⚠ **`2026-08-08-11-001` was filed today** and points the opposite way — a *compliant* task
spuriously blocked. Worth including precisely because it shows the boundary is unreliable in both
directions, and a fix aimed only at the permissive half would make the false-block worse.

### Claim labels

- **OBSERVED**: lesson ids, components, categories, titles; the absence of a covering plan in
  your 109-row queue.
- **HYPOTHESIS (verify-at-outline)**: that each is still live. `2026-08-08-11-001` is same-day
  and near-certainly live; the June members are the ones most likely already closed —
  establish merge order before concluding any of them survives in main. Confirm/refute artifacts:
  the phase-5 orchestrator-tier yield boundary, and the ARTIFACT emission loop in
  `phase-5-execute`.

### Provenance

Corpus snapshot: `.plan/local/orchestrator/lessons-handling-26-08-08-01/archive/{lesson_id}.md`.
Dispositions: `.plan/local/orchestrator/lessons-handling-26-08-08-01/dispositions.md`.
Nothing retired; retirement is deferred behind your running `PLAN-TRUTH-044`.
