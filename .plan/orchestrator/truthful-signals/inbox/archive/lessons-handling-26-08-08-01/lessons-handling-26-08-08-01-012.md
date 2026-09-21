envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-08-01
epic=truthful-signals
kind=finding
created=2026-08-08T16:33:30Z

## Routed lessons cluster C20 — git, worktree and footprint integrity (6 corpus instances)

**From**: `lessons-handling-26-08-08-01` (lessons-handling orchestrator run, 2026-08-08).
**Suggested homes**: `PLAN-TRUTH-006` (baseline-reconcile-persists-merge-commit) and
`PLAN-TRUTH-054` (baseline-reconcile-stale-phase-1-anchor).
**You decide**: fold, restage, or decline. Nothing was written into your tree.

### The cluster

| Lesson | Claim | Suggested home |
|--------|-------|----------------|
| 2026-07-22-21-001 | `baseline-reconcile --no-emit` **leaves a merge commit on the feature branch** instead of aborting its probe | `PLAN-TRUTH-006` |
| 2026-07-21-11-002 | worktree materialization branches off local main **without asserting `local main == origin/main`**, silently inheriting a foreign unpushed commit into the plan branch | `PLAN-TRUTH-054` |
| 2026-07-17-08-001 | whole-output `.strip()` before `splitlines()` on `git --porcelain` **shifts the fixed-column XY status field**, so `line[3:]` eats the first path character | no home |
| 2026-07-19-16-002 | the footprint path-to-module classifier feeding build-target selection must fail safe at every boundary **and derive ownership from the whole footprint** (nest-inside guard, empty-scope to whole-tree fallback, no build-relevance pre-filter) | no home |
| 2026-07-22-07-001 | a deliberate deviation from a lint-scanned pattern must carry the analyzer's **sanctioned suppression marker at the call site**, or it ships as a latent spurious lint hit | no home |
| 2026-07-22-07-002 | a new audit/logging emission on a routing seam must **suppress itself on daemon-child re-entrancy** or it double-emits | no home |

### The two that matter most, and they are the same defect

`2026-07-22-21-001` and `2026-07-21-11-002` are both about **a probe or a materialization
mutating state it was only supposed to read**:

- `--no-emit` is a dry-run flag. It leaves a merge commit. A read-only mode that writes is the
  worst kind of contract violation because the caller chose it *specifically* to avoid the write.
- Worktree materialization inherits a foreign unpushed commit without asserting parity, so the
  plan branch silently carries work nobody attributed to it.

Your ledger already records that `PLAN-TRUTH-054` and `PLAN-TRUTH-058` share
`_cmd_baseline_reconcile.py` and the same wrong-read-that-WRITES class, and are to be serialized.
`2026-07-22-21-001` is a **third instance of that same class on the same file**. Three instances
on one module is an argument for treating them as one plan rather than three folds.

### The unhomed four

`2026-07-17-08-001` (porcelain column shift) is a small, self-contained parser bug with a
concrete consequence — the first character of a path is eaten. It needs no plan of its own; it
needs someone to fix it.

`2026-07-19-16-002` is the largest of the four and the least contained: a classifier feeding
**build-target selection** that must fail safe at every boundary. A misclassification there
selects the wrong build, which means a green that measured the wrong tree. That is closer to
cluster C02's subject (a build reporting falsely) than to git integrity, and may belong there.

### Claim labels

- **OBSERVED**: lesson ids, components, categories, titles; `PLAN-TRUTH-006`/`-054`/`-058`
  id/slug/status.
- **HYPOTHESIS (verify-at-outline)**: that each is still live. Confirm/refute artifact:
  `_cmd_baseline_reconcile.py` for the first two; the porcelain parser in
  `workflow-integration-git` for `2026-07-17-08-001`. ⚠ Your ledger flags that whichever of
  TRUTH-054/-046 runs second must re-ground on `status.metadata.worktree_sha`; the same caution
  applies to anything folded here.

### Provenance

Corpus snapshot: `.plan/local/orchestrator/lessons-handling-26-08-08-01/archive/{lesson_id}.md`.
Dispositions: `.plan/local/orchestrator/lessons-handling-26-08-08-01/dispositions.md`.
Nothing retired; retirement is deferred behind your running `PLAN-TRUTH-044`.
