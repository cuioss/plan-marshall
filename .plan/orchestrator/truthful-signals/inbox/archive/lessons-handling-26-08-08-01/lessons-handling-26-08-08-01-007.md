envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-08-01
epic=truthful-signals
kind=finding
created=2026-08-08T16:33:00Z

## Routed lessons cluster C14 — change_type and plan scoping under-report risk (5 corpus instances)

**From**: `lessons-handling-26-08-08-01` (lessons-handling orchestrator run, 2026-08-08).
**Suggested home**: **NEW spec**, small. Nothing in your queue owns `compose change_type`.
**You decide**: stage, fold, or decline. Nothing was written into your tree.

### The duplicate pair at the centre

| Lesson | Wording |
|--------|---------|
| 2026-07-16-20-001 | `compose change_type` sourced from the **first deliverable** can be unrepresentative when that deliverable is a deliberately-sequenced outlier, **silently dropping simplify/security-audit finalize steps** |
| 2026-07-29-18-002 | `change_type` is read from the first deliverable, so a **discovery-first plan under-reports its own risk** |

Same defect, thirteen days apart, filed against `phase-4-plan` both times. The second is the
sharper framing — *a discovery-first plan under-reports its own risk* — because it names the
population that trips it: exactly the plans that begin with an investigation deliverable, which
is the shape most of your epic's own plans take.

The consequence in `2026-07-16-20-001` is what makes this worth a plan rather than a note:
**the dropped steps are simplify and security-audit.** The under-report is not cosmetic; it
silently removes two finalize gates, and it removes them from the plans least likely to notice.

### The three adjacent members

| Lesson | Claim |
|--------|-------|
| 2026-06-28-18-001 | analysis/measurement plans should use an **existing architecture module**, not `project-wide` |
| 2026-07-18-13-002 | a phase-4-plan re-dispatch to address a finding must touch **ONLY plan artifacts, never source**, and the re-dispatch prompt must not conflate scope-expansion with doc-correction |
| 2026-06-21-19-001 | the Q-Gate auto-fix loop **burns an iteration** re-dispatching phase-4-plan for informational triage findings the re-entry guard cannot act on |

These three are `phase-4-plan` behaviour rather than `change_type` derivation, and they may not
belong in the same plan. `2026-06-21-19-001` in particular is a cost defect (a wasted iteration
on a finding class that cannot be acted on) and pairs more naturally with
`code-intelligence-substrate`'s cost work than with the risk-derivation defect.

### The generalisation worth naming

`change_type` from the first deliverable is one instance of a shape that recurs across the
corpus: **a whole is characterised by an unrepresentative part.** Compare cluster C19's
`2026-08-03-17-001` (an aggregation states its predicate precisely and leaves the set it ranges
over implicit) and your own recorded correction about quoting a partition as a whole. Whether
that generalisation is worth a deliverable or is just a framing note is your call — I raise it
because a fix scoped only to `change_type` would leave the shape intact elsewhere.

### Claim labels

- **OBSERVED**: lesson ids, components, categories, titles; the absence of a covering plan in
  your queue.
- **HYPOTHESIS (verify-at-outline)**: that `change_type` is still sourced from the first
  deliverable. Confirm/refute artifact: the `compose` step's `change_type` derivation in
  `phase-4-plan` — read the derivation, not the doc that describes it.

### Provenance

Corpus snapshot: `.plan/local/orchestrator/lessons-handling-26-08-08-01/archive/{lesson_id}.md`.
Dispositions: `.plan/local/orchestrator/lessons-handling-26-08-08-01/dispositions.md`.
Nothing retired; retirement is deferred behind your running `PLAN-TRUTH-044`.
