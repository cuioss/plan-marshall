envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-08-01
epic=truthful-signals
kind=finding
created=2026-08-08T16:32:47Z

## Routed lessons cluster C10 — finalize step ordering and instrumentation (10 corpus instances)

**From**: `lessons-handling-26-08-08-01` (lessons-handling orchestrator run, 2026-08-08).
**Suggested home**: `PLAN-TRUTH-050` (the-operator-report-is-an-evidence-surface-the-inbox-cannot-see),
which already owns the finalize step-order space and carries an operator no-split directive.
**You decide**: fold, restage, or decline. Nothing was written into your tree.

### The cluster

Ten active lessons where a finalize step runs at a point that makes its own work unsound.

**A step runs after its input is destroyed, or before its input exists:**

| Lesson | Claim |
|--------|-------|
| 2026-07-28-19-005 | `plan-retrospective` runs at step 17 — **after** branch-cleanup destroys its footprint input and **before** sync-plugin-cache makes the plan's own fixes live, so no plan can self-verify a finalize-pipeline fix |
| 2026-07-29-18-003 | a finalize step that runs **before the merge window** cannot capture what the merge window reveals |
| 2026-06-21-01-001 | a self-modifying plan that removes a finalize step's standards file strands its own composed-at-outline `execution.toon`; validate-loadable fails until the manifest is recomposed |

**A boundary is detected instead of enforced:**

| Lesson | Claim |
|--------|-------|
| 2026-08-03-14-001 | the loop-back ceiling is **detected after it is crossed**, not enforced at the boundary |
| 2026-06-28-13-001 | a short-circuit/bypass branch must be documented **before** the dispatch it bypasses; spec ordering let a classifier failure override the never-rebase `needs_user` path |

**The gate's scope is narrower than the claim it licenses:**

| Lesson | Claim |
|--------|-------|
| 2026-07-17-09-002 | scoped finalize plugin-doctor (touched-skills-only) **misses a whole-tree rule violation** that CI's whole-tree run catches |
| 2026-07-21-21-002 | root-module footprint (`marketplace/targets/**`) falls through the per-bundle quality-gate sweep **un-gated** |
| 2026-06-25-08-003 | the `finalize-step-simplify` dispatched prompt omits the changeset-scope boundary, so the review **deletes pre-existing out-of-scope code** |
| 2026-07-16-17-009 | run a Sonar/quality pass on the diff before push on large plans to catch new-code gate failures locally |

**Instrumentation is absent on a real path:**

| Lesson | Claim |
|--------|-------|
| 2026-08-03-14-006 | operator resume after a loop-back halt emits **no step instrumentation at all** |

### The structural point

`2026-07-28-19-005` is the one to lead with, and it is self-referential in a way that matters to
your epic: **no plan can self-verify a finalize-pipeline fix**, because the step that would
verify it runs before the step that makes the fix live. That is the same shape as the recorded
finding that a plan fixing a finalize-time component cannot have that fix exercised by its own
finalize. Any plan taking this cluster inherits that limitation and should say so in its outline
rather than claim self-exercise — which `2026-08-03-06-004` (routed to
`code-intelligence-substrate`) states as a general rule.

`2026-08-03-14-006` pairs with it: the resume path emits nothing, so the one path most likely to
be exercised after a halt is also the one with no evidence trail.

⚠ **Adjacency**: `2026-06-25-08-003` (simplify deletes out-of-scope code) and cluster C05's
`2026-07-17-09-001` (simplify reverts a fix automatic-review made in the same run) are both
`finalize-step-simplify` scope-boundary defects. C05 went to `review-apparatus`. If they turn out
to be one surface, better to say so than to ship two.

### Claim labels

- **OBSERVED**: lesson ids, components, categories, titles; `PLAN-TRUTH-050` id/slug/status.
- **HYPOTHESIS (verify-at-outline)**: that each ordering is still as described. Confirm/refute
  artifact: the `phase-6-finalize` step order registry — the declared `order` value of each named
  step. ⚠ Your ledger already records that step 995/998/999 renumbering is in flight inside
  TRUTH-050 itself, so these orders are a moving target; re-read at outline, do not inherit.

### Provenance

Corpus snapshot: `.plan/local/orchestrator/lessons-handling-26-08-08-01/archive/{lesson_id}.md`.
Dispositions: `.plan/local/orchestrator/lessons-handling-26-08-08-01/dispositions.md`.
Nothing retired; retirement is deferred behind your running `PLAN-TRUTH-044`.
