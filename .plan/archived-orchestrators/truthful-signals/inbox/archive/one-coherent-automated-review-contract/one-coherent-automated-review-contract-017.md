envelope_version=1
sender_type=plan
sender_id=one-coherent-automated-review-contract
epic=truthful-signals
kind=finding
created=2026-07-29T05:22:35Z

## `record-step` for `archive-plan` can never succeed — archive moves the manifest before the row can be written

**Observed during the PLAN-92 / PR #1041 finalize run, at the end of the Step 3 FOR loop.**

### What happened

The dispatcher's item-5e contract says a `record-step` execution-log row is
recorded for **EVERY** finalize step — dispatched or inline:

> *"Unlike 5b/5c/5d, this row is recorded for EVERY finalize step — dispatched
> OR inline — so a skipped or inline step still lands an `execution_log` row"*

Following that for `archive-plan` produced:

```
status: error
error: file_not_found
message: execution.toon not found for plan one-coherent-automated-review-contract
```

### Why it is structurally unsatisfiable

`execution.toon` lives inside the plan directory. `archive-plan` **moves that
directory** to `.plan/local/archived-plans/{date}-{plan_id}/`. The row for
`archive-plan` can only be written after `archive-plan` runs, and by then its
target no longer exists at the path the writer resolves.

Two documented constraints collide:

- item 5e: record a row for every step, after the step completes
- `archive-plan` ordering: *"This step MUST be last in the default order
  because it moves plan files (including status.json), which breaks manage-\*
  scripts"*

`archive-plan` is therefore the one step whose 5e row is unwritable by
construction. This is not a race and not environment-specific — it is
guaranteed on every plan that archives.

### Impact

Low, but it is a real hole in an audit surface that is described as complete.
The `execution_log[]` is the per-step breakdown behind the phase token
aggregate, and it will always be missing exactly one row, with no marker
explaining the absence. Anything that reasons over "did every manifest step
land an execution_log row?" gets a false negative on every plan.

Also worth noting: the failure surfaces as a plain `file_not_found` **error**
from a step that in fact completed successfully. A finalize driver that
honours the document's exit-code convention literally —

> *"`exit_code != 0`: STOP and return an error TOON to the orchestrator"*

— would halt on the last step of a plan that had, at that point, fully
succeeded and archived.

### Theme fit

A **confident-signal-hides-a-caveat** instance of the small, structural kind:
the manifest's `execution_log` presents as a complete per-step record and is
documented as one ("EVERY finalize step"), while being provably incomplete by
exactly one row on every single plan. The gap is invisible unless you count
rows against the manifest's step list.

### Fix owed

Pick one — all three are cheap; the current state (silent guaranteed gap plus
a spurious error) is the only bad option:

1. **Write the row before the move.** Have `archive-plan` itself record its
   own `execution_log` row as its first action, while the plan dir is still
   live — mirroring how it already marks its own step done and sets
   `current_phase: complete` atomically before moving.
2. **Redirect post-archive writes.** Let `record-step` resolve the archived
   plan dir as a fallback when the live one is gone, so the row lands in the
   archived manifest.
3. **Document the carve-out.** Amend item 5e to state that `archive-plan` is
   exempt, and why — so the absent row is a known-and-explained hole rather
   than an undetected one, and so a driver does not treat the resulting
   `file_not_found` as a halt condition.

Option 1 is preferred: it keeps `execution_log` genuinely complete, which is
what makes the "row per manifest step" invariant checkable at all.
