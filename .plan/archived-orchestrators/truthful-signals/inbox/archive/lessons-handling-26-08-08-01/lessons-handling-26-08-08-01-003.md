envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-08-01
epic=truthful-signals
kind=finding
created=2026-08-08T16:32:43Z

## Routed lessons cluster C04 — vacuous guards and degenerate zeros (15 corpus instances)

**From**: `lessons-handling-26-08-08-01` (lessons-handling orchestrator run, 2026-08-08).
**Suggested home**: `PLAN-TRUTH-042` (a-rule-that-is-green-because-it-examined-nothing).
⚠ **TRUTH-042 is RUNNING.** This arrives as a mid-flight observation, deliberately NOT as a spec
edit. Absorb it, defer it, or decline it — your call, and declining mid-run is a legitimate answer.

### The cluster

Fifteen active lessons: the largest severity-weighted cluster in the 203-lesson corpus, and the
one the project's own records flag as *repeatedly reintroduced by a fix for it*.

**The guard's predicate excludes the case it exists to catch:**

| Lesson | Claim |
|--------|-------|
| 2026-07-28-20-002 | vacuous guard: a guard whose predicate excludes its **own motivating case** |
| 2026-07-23-01-002 | a gate that skips items lacking the very key it enforces (`if key is None: continue`) is vacuous for exactly the misconfigured items it exists to catch |
| 2026-08-03-14-004 | `RE_ENTRY_COVERAGE` guard is vacuous **at exactly the value it exists to catch** |
| 2026-08-03-06-001 | a guard bound to a caller-supplied path **its own pipeline deletes** has a structurally unreachable failure arm |
| 2026-07-28-19-006 | a regression detector's non-degeneracy anchor **omits the very member the fix just added**, and its guards skip-on-missing rather than fail — three instances inside one plan's own tests |

**The zero is unmeasured rather than healthy:**

| Lesson | Claim |
|--------|-------|
| 2026-07-26-22-002 | merge-window-accounting scans the global logs for a `[LOCK]` marker **never emitted there**, so its zero-contention report is unmeasured, not healthy |
| 2026-07-26-22-001 | `decision-rules.md` claims the composer's recipe-provenance surrogate matches the audit re-derivation, but the audit omits the `recipe_key` fallback: **Row 2 is vacuous** and recipe-routed plans report false drift |
| 2026-07-21-11-003 | the module-tests divergence gate has **no zero-scoped-modules branch**, so a docs-only footprint falls into a scoped run with a null target |
| 2026-06-24-14-002 | a scoring-blend's **max attainable score** must be checked against the gating threshold it feeds, or the gate is structurally unreachable |

**The discriminator cannot separate the states it must:**

| Lesson | Claim |
|--------|-------|
| 2026-07-29-18-005 | a discriminator over a derived collection's keys **cannot separate unknown from empty** |
| 2026-08-02-15-001 | a **seeded empty container is not a declaration** — test the value, not the key |
| 2026-07-26-19-001 | an equality-based sentinel-tuple emptiness check treats numeric `0`/`0.0` as empty (`False == 0`), so a non-empty-payload guard **silently drops the content it exists to detect** |
| 2026-06-24-18-003 | counterfactual/replay checks must treat a missing/unreadable input as **inconclusive**, never coerce it into a signal value |

**The check is the wrong kind of check:**

| Lesson | Claim |
|--------|-------|
| 2026-07-29-17-001 | a closure invariant that checks **completeness never checks correctness** |
| 2026-07-16-14-001 | a new outcome-classifier seam ships **fail-open on multiple independent axes** (optional scoping key, classify-before-exactly-once-gate); all in-house gates green, only post-push review bots caught them |

### What fifteen instances buys TRUTH-042

The plan's title is the abstract claim. This is the population. Three things the set says that
no single member does:

1. **The four sub-shapes above are distinguishable and probably need different detectors.** A
   predicate-excludes-its-case guard and a zero-from-an-unemitted-marker are both "green because
   it examined nothing", but the first is found by reading the guard and the second only by
   checking the producer emits what the consumer scans for.
2. **`2026-07-28-19-006` is the reflexive instance**: three vacuous guards shipped *inside one
   plan's own tests*, in a plan about guards. Any detector this work builds must be run against
   its own diff, or it reproduces its target — which `2026-07-29-18-009` (routed to
   `code-intelligence-substrate`) says independently.
3. ⚠ **This is a sample.** Fifteen lessons somebody filed, not fifteen of N. Per your own
   standing rule, any set-guarding detector built from it must be **population-derived** and must
   publish the population size — a check that can return 0 from an empty population is itself
   the defect being fixed.

### Claim labels

- **OBSERVED**: lesson ids, components, categories, titles; `PLAN-TRUTH-042` id/slug/status=running.
- **HYPOTHESIS (verify-at-outline)**: that each named guard is still vacuous. Confirm/refute
  artifact: each guard's own predicate, read at the site named in the lesson body.

### Provenance

Corpus snapshot: `.plan/local/orchestrator/lessons-handling-26-08-08-01/archive/{lesson_id}.md`.
Dispositions: `.plan/local/orchestrator/lessons-handling-26-08-08-01/dispositions.md`.
Nothing retired; retirement is deferred behind your running `PLAN-TRUTH-044`.
