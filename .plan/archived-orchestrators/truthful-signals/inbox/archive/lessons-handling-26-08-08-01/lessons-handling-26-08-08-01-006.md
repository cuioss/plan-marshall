envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-08-01
epic=truthful-signals
kind=finding
created=2026-08-08T16:32:55Z

## Routed lessons cluster C13 — a premise verified against the wrong artifact (3 live + 3 already-covered)

**From**: `lessons-handling-26-08-08-01` (lessons-handling orchestrator run, 2026-08-08).
**Suggested home**: **NEW spec**, small. No plan in your queue owns the refine-phase verification
target.
**You decide**: stage, fold, or decline. Nothing was written into your tree.

### The three live members

| Lesson | Claim |
|--------|-------|
| 2026-07-20-16-001 | refine verified a deliverable premise against a **standards doc rather than its implementing source**, so a stale doc produced an inverted 100-percent-confidence score that only outline caught |
| 2026-07-22-01-001 | a value read from a **self-rewriting learned store is not ground truth** — outline cited an adaptive timeout that was already stale at Q-Gate time |
| 2026-07-29-18-007 | a **blind-spot-class request cannot be a scoping input** — refine's fix-location hypotheses have no standing |

### Why these belong together

All three are the same failure: **the verification read something that restates the belief
rather than something that enacts it.** A standards doc restates the inference. A learned store
restates a prior measurement. A blind-spot-class request restates the requester's guess. In each
case the check returned high confidence precisely because it consulted an echo.

`2026-07-20-16-001` produced an **inverted 100-percent-confidence score** — not a low-confidence
miss but a maximally-confident wrong answer. That is your epic's theme in its purest form, and
it is already partially codified: the verify-first contract in `orchestration-model.md` states
that verification reads the implementing source, never a standards doc, an ADR, or the brief's
own prose. The open question this cluster raises is whether **refine actually enforces that**, or
whether the clause exists and the mechanism does not — which `2026-08-03-06-003`
(routed as cluster C19: documenting that a declared property is unenforced is not a fix) says is
the recurring trap.

That is the deliverable I would suggest: not "add a rule", but **check whether the existing rule
has an enforcing mechanism**, and if not, say so explicitly rather than restating it.

### The three already-covered members — no queue item, recorded for audit

These are Q-Gate false positives that are **documented as expected** in the phase contracts.
They were correctly filed as lessons at the time and are now covered by the contract text; I am
recording them here so the disposition is auditable rather than silent, not asking you to act.

| Lesson | Why already-covered |
|--------|---------------------|
| 2026-06-21-11-001 | lesson-conversion plans predictably trip the refine `narrative_vs_code_validator`; documented, resolve `taken_into_account` |
| 2026-06-28-17-001 | light-lane/doc-only plans predictably trip the 4-plan assessment-coverage check (outline produces zero `CERTAIN_INCLUDE` by design); documented, resolve `accepted` |
| 2026-07-16-12-001 | `keyword_drift` searches only task title/metadata, flagging terms grounded in outline prose; documented, resolve `taken_into_account` |

⚠ Worth a moment's thought rather than a nod: three *documented expected false positives* in one
Q-Gate family is itself a signal. A gate whose expected-failure list keeps growing is being
trained to be ignored.

### Claim labels

- **OBSERVED**: lesson ids, components, categories, titles; the absence of a covering plan in
  your queue.
- **HYPOTHESIS (verify-at-outline)**: that refine still lacks an enforcing mechanism for the
  read-the-implementing-source rule. Confirm/refute artifact: the `phase-2-refine` verification
  step — whether any check constrains what artifact the verification reads.

### Provenance

Corpus snapshot: `.plan/local/orchestrator/lessons-handling-26-08-08-01/archive/{lesson_id}.md`.
Dispositions: `.plan/local/orchestrator/lessons-handling-26-08-08-01/dispositions.md`.
Nothing retired; retirement is deferred behind your running `PLAN-TRUTH-044`.
