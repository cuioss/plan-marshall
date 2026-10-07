envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-08-01
epic=code-intelligence-substrate
kind=finding
created=2026-08-08T16:27:57Z

## Routed lessons cluster C12 — outline scope derivation is incomplete (17 corpus instances)

**From**: `lessons-handling-26-08-08-01` (lessons-handling orchestrator run, 2026-08-08).
**Suggested home**: `PLAN-CIS-015` (outline-plan-scope-derivation-integrity).
**You decide**: fold, restage, split, or decline. Nothing was written into your tree.

⚠ **Scope-bloat warning, stated up front**: this is the second-largest cluster in the corpus and
it is almost certainly too large to fold whole. I would expect it to split into at least
*"the derived set is incomplete"* and *"the derived bucket is wrong"*. I am handing it over
undivided rather than pre-cutting it, because the cut depends on `PLAN-CIS-015`'s own shape,
which you own.

### Sub-group A — the derived set is incomplete (the sweep did not see everything)

| Lesson | Claim |
|--------|-------|
| 2026-07-21-17-004 | outline pass 1 verifies declared paths **exist** but never that a declared set is **complete** |
| 2026-07-22-10-002 | files entering scope **after** the discovery sweep has run bypass its assessment entirely |
| 2026-06-29-16-001 | plans under-scope the **mirror contract surface** (doc catalogues, cited-sibling docs, count-pinning tests) of a code/registry change |
| 2026-07-21-16-002 | deliverables mutating the same symbols need an explicit dependency edge; one pass shipped a missing edge, a misclassified touched-skill, an undercounted touched-skill list and an under-scoped count-prose criterion |
| 2026-06-21-02-001 | outline mandated an edit to a symbol a prior shipped plan had already **removed** |
| 2026-06-20-12-001 | task descriptions drift from the deliverable outline by **inventing CLI shapes** not in it |
| 2026-07-25-19-001 | corroborating outputs of one extractor must share ONE input population; retaining the wider input behind a no-op docstring keeps the false-fact channel open |

### Sub-group B — the derived bucket or classification is wrong

| Lesson | Claim |
|--------|-------|
| 2026-07-22-16-001 | a **read-only reference file** listed under Affected files flips the execution-manifest footprint bucket and the module declaration |
| 2026-07-22-20-004 | the deliverable file-type bucket is declared from **narrative intent** instead of derived from Affected files, dropping a required profile and skipping the very build that validates the change |
| 2026-07-29-18-001 | a lane variant that collapses a phase envelope must **re-home the folded step's writes** |
| 2026-07-28-19-004 | the planning-lane router's pre-override input is **overwritten by its output**, so an operator lane escalation leaves no auditable record of what the router got wrong |
| 2026-06-29-02-001 | `get-module-context` resolved `use_worktree=true` and required `worktree_path` **before the worktree was materialized** |
| 2026-07-26-16-001 | `get-module-context` treats the legitimate `not_yet_materialized` state as `worktree_resolution_failed` |

### Sub-group C — the criterion cannot be met as written

| Lesson | Claim |
|--------|-------|
| 2026-07-27-08-003 | a success criterion resting on **pre-existing test coverage** must locate that coverage at authoring time, or the change ships unsubstantiated |
| 2026-07-29-19-001 | a staged spec premise **expires** — re-measure at outline, never inherit it |
| 2026-08-03-06-004 | a plan whose deliverable the lifecycle consumes at a phase it has **already passed** is not self-exercising, and the outline should say so |
| 2026-07-29-18-009 | a plan fixing an accumulate-vs-replace defect can **reproduce it in its own run** — self-check before finalize |

### Why this is yours rather than truthful-signals'

Every member is about **deriving a set or a classification from the codebase** — which files are
in scope, which module owns them, which bucket they fall in, whether a claimed coverage exists.
That is the code-intelligence substrate, not signal truthfulness. The two epics touch at
`2026-07-29-19-001` (a premise expires), which is also a verify-first-contract concern; if
`truthful-signals` claims it, no objection from me.

`2026-07-26-16-001` and `2026-06-29-02-001` are near-duplicates on the same
`get-module-context` worktree-state surface and should be treated as one item.

### Claim labels

- **OBSERVED**: lesson ids, components, categories, titles; `PLAN-CIS-015` id/slug/status.
- **HYPOTHESIS (verify-at-outline)**: that each derivation gap is still open. Confirm/refute
  artifacts: the `phase-3-outline` discovery-sweep pass, and `manage-solution-outline`'s
  `get-module-context` worktree-state branch.

### Provenance

Corpus snapshot: `.plan/local/orchestrator/lessons-handling-26-08-08-01/archive/{lesson_id}.md`.
Dispositions: `.plan/local/orchestrator/lessons-handling-26-08-08-01/dispositions.md`.
Nothing retired; retirement is deferred behind `PLAN-TRUTH-044`.
