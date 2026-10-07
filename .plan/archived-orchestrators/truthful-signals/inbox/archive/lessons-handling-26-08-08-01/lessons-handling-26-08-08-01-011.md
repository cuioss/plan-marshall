envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-08-01
epic=truthful-signals
kind=finding
created=2026-08-08T16:33:24Z

## Routed lessons cluster C19 — doc-contract divergence (18 corpus instances)

**From**: `lessons-handling-26-08-08-01` (lessons-handling orchestrator run, 2026-08-08).
**Suggested home**: `PLAN-TRUTH-012` (canonical-block-diverges-from-argparse-choices).
**You decide**: fold, restage, split, or decline. Nothing was written into your tree.

⚠ **Largest cluster in the corpus, and almost certainly too large to fold whole.** I am handing
it over undivided rather than pre-cutting it; the sub-groups below are how I would cut it.

### Sub-group A — the doc declares what the code does not do

| Lesson | Claim |
|--------|-------|
| 2026-07-21-17-002 | a newly-relied-upon script flag must be verified against the owning skill's **contract doc, not just argparse** — implemented is not documented |
| 2026-07-23-02-001 | a telemetry field promised in a documented command-return contract must be **populated in the return dict**, not only routed to a side-effect sink |
| 2026-07-28-23-003 | an **early-return branch that omits fields the doc declares unconditionally** is a doc-contract divergence |
| 2026-08-03-06-003 | **documenting that a declared property is unenforced is not a fix** — honesty is not enforcement |
| 2026-07-13-17-001 | static analyzers over-approximate when their model omits a runtime dispatch mechanism — allowlist the mechanism, keep validating the rest |

### Sub-group B — two documents disagree and nothing cross-checks them

| Lesson | Claim |
|--------|-------|
| 2026-07-28-19-003 | `architecture-refresh` is classified **dispatched** by the declared single source of truth and **inline** at two SKILL.md sites; the closure test opens both documents but never cross-checks them |
| 2026-06-24-23-001 | literal-count-drift counts per-bundle `extension.py` overrides, NOT the ext-point Current Implementations table — reconciling the two reintroduces the finding |
| 2026-06-25-10-001 | a standards doc narrating an authoritative machine-readable list must **enumerate it exactly**; prose that paraphrases the universe over- or under-states it |
| 2026-07-19-12-001 | adding an archived/frozen-store read fallback must be matched by an explicit archived-state guard on **every sibling mutation verb** and by output-contract reconciliation |
| 2026-07-30-15-001 | a centralizing refactor can silently **widen a lazy contract into an eager one** |
| 2026-08-02-15-002 | a precedence branch that discards a producer's output **must say so on that producer's report** |

### Sub-group C — the record itself is false or unanchored

| Lesson | Claim |
|--------|-------|
| 2026-07-27-23-002 | a wrong `[DISPATCH]` line is retracted by a second `[DISPATCH]`-tagged prose line, so the **audit population carries a known-false record no detector can filter** |
| 2026-07-20-01-001 | audit/reference docs citing **exact line numbers** drift the moment any earlier edit shifts them — anchor to symbols |
| 2026-07-29-17-002 | a **plan-ID renumber in one epic silently orphans citations in another** |
| 2026-07-22-16-004 | a doc-authored `/plan-marshall` hand-off command string must be validated against Action Resolution's actual parameter surface — an omitted `task=` silently resolves to `action=list` |
| 2026-06-28-17-002 | a taxonomy-renumber sweep must re-home each cross-reference **by semantic content**, not by substituting old number for new |
| 2026-06-28-12-001 | cross-references into a doc anchored to an older external taxonomy version must use **that doc's** version numbers |

### Sub-group D — a spec's own assertions are treated as evidence

| Lesson | Claim |
|--------|-------|
| 2026-07-29-09-001 | a staged spec's measured-value table and its hard constraints are **leads, not evidence** |
| 2026-08-03-18-001 | a spec's own assertion about its write surface is **not evidence for an emit-time disjointness decision** |

Both are addressed to the orchestrator role rather than to a script, and both are already
reflected in `orchestration-model.md`'s verify-first contract and in the standing rule that a
disjointness claim must be supported rather than asserted. They may be `already-covered` — but
the coverage should be checked against the clause's own worked example before anyone retires
them, which is the evidence standard your running `PLAN-TRUTH-044` governs.

### The sharpest member

`2026-07-27-23-002` is the one I would lead with. A retracted-but-still-present `[DISPATCH]`
line means the **audit population itself contains a record known to be false, and no detector
can filter it** — because the retraction is prose and the record is structured. Every count
derived from that population inherits the error silently. That is upstream of several of your
existing plans, `PLAN-TRUTH-045` (the dispatch audit) most directly.

### Claim labels

- **OBSERVED**: lesson ids, components, categories, titles; `PLAN-TRUTH-012`/`-045` id/slug/status.
- **HYPOTHESIS (verify-at-outline)**: that each divergence is still live. Confirm/refute artifact:
  for sub-group A, `plugin-doctor`'s `_analyze_manage_invocation.py` canonical-block reader
  versus the argparse surface it validates against.

### Provenance

Corpus snapshot: `.plan/local/orchestrator/lessons-handling-26-08-08-01/archive/{lesson_id}.md`.
Dispositions: `.plan/local/orchestrator/lessons-handling-26-08-08-01/dispositions.md`.
Nothing retired; retirement is deferred behind your running `PLAN-TRUTH-044`.
