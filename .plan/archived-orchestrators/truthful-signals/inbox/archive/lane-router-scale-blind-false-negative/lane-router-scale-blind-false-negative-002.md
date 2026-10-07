envelope_version=1
sender_type=plan
sender_id=lane-router-scale-blind-false-negative
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T18:49:21Z

component=plan-marshall:persona-module-tester
category=anti-pattern
bundle=plan-marshall

# A path-part skip-list is a vacuous-guard generator: every sweep needs a control assertion

New shape of the vacuous-guard archetype (predicate never fires), found **five times in
a single plan**. All five share one mechanic: a *skip* or *short-circuit* decision that
silently swallowed the entire population the check was supposed to examine, while the
check still reported PASS.

The five instances:

1. **`_GLOB_RE` matched markdown bold.** The bare `**` in the glob pattern matched
   `**bold**` in prose. Because the fan-out check short-circuits BEFORE the path count,
   the path count was **unreachable for the entire orchestrated-spec population** — not
   for an edge case, for all of it.
2. **The S7 `epic` keyword.** It would have matched the `epic:` metadata key that every
   orchestrated spec opens with, so the keyword signal was constant-true across the
   population it was meant to discriminate.
3. **`test_lane_refactor_cleanup_sweep.py::_iter_text_files` tested `_SKIP_DIR_PARTS`
   against the ABSOLUTE `path.parts`.** Under a plan worktree — which lives beneath
   `.plan/` — *every* file matched a skip part, so all four retired-token assertions
   passed while scanning **nothing**. This test had been vacuous in every worktree run
   since it was written.
4. **An ad-hoc sweep written DURING the review reproduced (3) verbatim**, minutes after
   the author had read and understood the fix for it. The shape is that easy to
   re-introduce.
5. **`scale_mismatch_light_routing` was structurally unreachable.**

## Solution

**Any path-part skip-list is guilty until positively shown to scan.** Treat "the sweep
reported zero hits" as an unresolved question, never as an answer.

Put a **control assertion** in every sweep: a known-present string that MUST be found,
or the sweep refuses to report a zero. A sweep that cannot find its own control is
reporting "I could not look", which is a different value from "I looked and found
nothing" — and the two must not share a representation.

Corollaries that each fell out of one of the five instances:

- Test a skip-list against the path **relative to the scan root**, never against
  `path.parts` of the absolute path. Absolute paths carry the harness's own directory
  names (`.plan/`, `worktrees/`, `local/`) and will match skip parts by accident.
- When a check short-circuits, the terms AFTER the short-circuit are only as reachable
  as the terms before it. Assert reachability of the later terms explicitly.
- A keyword signal must be checked against the metadata/boilerplate its population
  always contains, not only against the content it is meant to discriminate.

## Impact

Applies to every content sweep, retired-token check, compliance scan, and
population-derived detector in the repo. Pairs with the existing standing rule that
"every set-guarding detector must be population-derived" — this lesson adds that a
population-derived detector still has to prove it *reached* the population.
