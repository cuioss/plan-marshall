# Check: task-graph-redundancy (per-plan task-graph adjacency)

A **per-plan** check that reconstructs each plan's task graph from its
`tasks/TASK-*.json` files and surfaces five redundancy signals — duplicated work
baked into the task list, and heavy builds baked into per-task verification that
phase-5 execute / phase-6 finalize already run. The deterministic computation
lives in `scripts/audit.py` (`check_task_graph_redundancy` /
`emit_task_graph_redundancy_block`); this sub-document is the interpretation
guide.

The graph is reconstructed as **adjacency over step targets** — a
`file_owners: target → owning task numbers` map — not as a hash of step/command
strings. Adjacency over targets is whitespace- and arg-order-insensitive and
yields the file-overlap signals directly; string hashing would both miss
legitimate target overlaps that carry different commands and conflate distinct
steps.

## Inputs the check reads

| Input | Path | Fields used |
|-------|------|-------------|
| Tasks | `tasks/TASK-*.json` | `number`, `profile`, `deliverable`, `steps[].target`, `steps[].intent`, `verification.commands[]` |

Only the task JSON is read. The `in_task_build` signal is inferred from the
task's own `verification.commands` verbs alone — there is **no join against
`execution.toon`**, because whether a heavy build is baked into a task's
verification is fully determined by the task JSON; joining the manifest adds no
discriminating information and a fragile cross-file dependency.

## The five sub-checks

| Signal | Fires when | Computed from |
|--------|------------|---------------|
| `multi_task_file` | A file (step target) is edited by **≥2 tasks**. This is the **primary duplicate-task signal** — a merge candidate. | `file_owners: target → set(task numbers)`; flagged when `len(owners) > 1`. |
| `dup_substep` | The same `(target, intent)` pair is baked into **>1 task**. | A `(target, intent) → set(task numbers)` map; flagged when `len(owners) > 1`. |
| `in_task_build` | A task's `verification.commands` carries a **HEAVY** build/verify command — one of `module-tests` / `quality-gate` / `coverage`, or the full-suite `verify` verb — gated by a build-runner token. Phase-5/6 already run these, so a per-task copy is duplicated compute. | `is_heavy_build_cmd(cmd)` over each verification command; a scoped/light single-file or `--plan-id`-scoped check does NOT match. |
| `verif_task_fanout` | The plan has **>1** `module_testing`/`verification`-profile task — a collapse candidate. | Count of tasks whose `profile` is `module_testing` or `verification`. |
| `deliverable_fanout` | A deliverable's task count reaches the **per-run corpus outlier threshold** `max(3, median*2)`. | Per-deliverable task counts; the median is recomputed fresh from the loaded corpus each run (see below). |

### The per-run deliverable-fanout median (sub-check (e))

The deliverable→task fan-out threshold is **not** a hard-coded constant and is
**not** read from config. It is the **median per-deliverable task count over the
corpus scanned in the current run**, computed fresh from the in-memory corpus at
check time. A deliverable whose task count reaches `max(3, median * 2)` is an
outlier and flags `deliverable_fanout`. The threshold therefore adapts to the
corpus the run already loaded — no new threshold table entry and no new
`marshal.json` field. Because it needs the whole corpus, the cell is stamped in
`run_checks` after all per-plan rows are computed, not per-row.

## Emitted columns

```
check: task-graph-redundancy
status: success
plans_scanned: N
multi_task_file_plans: ...
dup_substep_plans: ...
in_task_build_plans: ...
verif_task_fanout_plans: ...
deliverable_fanout_plans: ...
deliverable_fanout_threshold: T
genuine_signal_count: G
rows[N]{plan_id,tasks,multi_task_file,dup_substep,in_task_build,verif_task_fanout,deliverable_fanout,severity}
```

| Column | Meaning |
|--------|---------|
| `tasks` | The plan's task count. |
| `multi_task_file` | `;`-joined files edited by ≥2 tasks, or empty. |
| `dup_substep` | `;`-joined `target [intent]` pairs baked into >1 task, or empty. |
| `in_task_build` | `;`-joined `T{n}:{verb}` heavy-build occurrences, or empty. |
| `verif_task_fanout` | `;`-joined task numbers when >1 module_testing/verification task, else empty. |
| `deliverable_fanout` | `max={count}>=thr={T}` when the plan's busiest deliverable reaches the per-run threshold, else empty. |
| `severity` | Uniform D1 severity column — see below. |

The summary header counts the plans flagged per signal and reports the per-run
`deliverable_fanout_threshold` so the systemic footprint is visible at a glance.

## Severity rule

All five sub-checks emit `genuine` — there is no informational-only sub-check. A
per-plan row is `severity: genuine` whenever **any** of the five signal cells is
populated, and `informational` otherwise. A clean plan — distinct step targets,
no heavy build in any task's verification, balanced deliverable fan-out — flags
none and is `informational`. `genuine_signal_count` counts the genuine rows.

## How the orchestrator interprets the rows

- **`multi_task_file`** — two or more tasks edit the same file. Read as a merge
  candidate: the tasks could often be a single task editing the file once. Cross-
  read with `dup_substep` — when the SAME `(target, intent)` is the overlap, the
  duplication is exact and the merge is safe; when only the target overlaps but
  the intents differ, the split may be intentional (e.g. a write-replace followed
  by a later refactor).
- **`dup_substep`** — the same `(target, intent)` baked into >1 task is almost
  always an accidental duplicate; verdict is a collapse to one task.
- **`in_task_build`** — a heavy build/verify baked into a task's verification
  that phase-5 execute / phase-6 finalize already run. The per-task copy is
  duplicated wall-clock; the verdict is to scope the per-task verification down
  to a light/targeted check and let the phase gate run the heavy suite once.
- **`verif_task_fanout`** — more than one test/verification task; often
  collapsible into one. Read against the plan's deliverable structure before
  filing — a legitimately large plan may warrant separate test tasks per
  deliverable.
- **`deliverable_fanout`** — a deliverable with an outlier task count relative to
  the per-run corpus. Read as a possible over-decomposition; confirm against the
  deliverable's actual surface before concluding it should have been fewer tasks.

Per the SKILL.md Step-3 contract, EVERY emitted row is adjudicated with a stated
verdict and cited evidence; a row may be dismissed as informational/expected ONLY
with a cited reason (the `severity: informational` cell).

## Cross-check-synthesis correlation

This check feeds the `cross-check-synthesis` coupling **`redundant_build_churn`**:
a plan whose task graph carries an `in_task_build` (a HEAVY build baked into a
task's verification — a STATIC redundancy) AND whose runtime sequence was flagged
`build_churn` / `phase_reentry` by `sequence-and-build-minimality`. The static
in_task_build redundancy and the observed runtime churn corroborate one wasted
heavy run. The coupling's caveat: confirm the two co-occur before filing — the
static signal alone is a smell, the runtime churn confirms it was paid.

## Critical rules

- The script is the single source of truth for the task-graph adjacency, the five
  signals, and the per-run median threshold. Do not re-derive a signal in chat.
- The heavy-build vocabulary (`HEAVY_BUILD_TOKENS`, `BUILD_RUNNERS`) and the
  `is_heavy_build_cmd` predicate are module constants/functions in
  `scripts/audit.py`. If the build-runner notations or heavy verbs change, edit
  the script rather than substituting a different reading.
- The deliverable-fanout threshold is corpus-relative and recomputed per run; it
  is never hard-coded and never persisted.
- This check is read-only; it never edits `.plan/` files.
