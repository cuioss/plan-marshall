envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=candidate-lesson
created=2026-08-01T20:10:04Z

## Delegation from `review-apparatus` — 12 items from PLAN-PR-014 / PR #1070

**REMOVED from the review-apparatus ledger.** Source plan `crashed-participation-gate-records-a-pass`,
PR **#1070**, merged `40bfba08c` at `2026-08-01T19:18:00Z`. Four sibling messages were RETAINED as
review-domain (participation/refusal classification and the producer pre-filter); these twelve are
yours. ⭐ Items 4–11 each self-suggested `truthful-signals` in their own `suggested_epic` field —
this routing agrees with the source, it does not override it.

⚠ **Item 2 is the one to look at first — the operator explicitly asked for it to be prioritised.**

---

### 1. ⭐ Quoting an empty placeholder can NEVER fix an argparse crash
`component=plan-marshall:tools-script-executor` · anti-pattern

The generated executor strips every empty-string argument before argparse runs
(`.plan/execute-script.py:989`, `script_args = [a for a in script_args if a]`), so `--flag ""` and a
bare `--flag` are indistinguishable downstream. ⛔ **This is a doc-truthfulness defect, not just a
coding tip**: PR #1070's own callouts shipped the wrong story (quoting and the parser framed as
complementary defences) and were corrected in `5d10ad536`. An author trusting the old text could add a
list flag, quote it, skip `nargs='?'`, and reintroduce the crash. `nargs='?'` was doing all the work.

### 2. ⭐⭐ The empty-flag exit-2 population across marketplace scripts is UNMEASURED — PRIORITISE
`component=plan-marshall:tools-script-executor` · improvement

PR #1070 fixed **seven** flags across **two** parsers (`review_completeness.py check` ×5,
`github_pr.py fetch_findings` ×2). ⛔ **It measured nothing beyond those two parsers and claims nothing
about the rest of the marketplace.** Any script with an optional list flag lacking `nargs='?'`, reachable
with an empty value, has the same latent exit-2.

**Evidence the class bites outside this repo, on a gate that reported success**: on `cuioss/API-Sheriff`
PR #138, `review_completeness check` exit-2'd on **4 invocations** while `automatic-review` still
recorded `done` — the quorum gate was structurally absent for most of that run.

⇒ Derive the population as its own plan: optional argparse flags without `nargs` × invocation sites
interpolating a possibly-empty `{placeholder}`. ⛔ Do not assume the count is small.

### 3. Two prescribed `manage-logging` messages contain a literal semicolon and can never be emitted
`component=plan-marshall:phase-6-finalize` · bug

⭐ **SECOND SIGHTING of a shape already delegated to you** as `review-apparatus-009` (the project-local
`finalize-step-plugin-doctor` Step 5 WARNING). Same mechanism: the one-command-per-Bash-call hook
inspects the raw command line, so a `;` inside the `--message` argument is indistinguishable from a
command separator and the call is refused outright. ⇒ **Two independent sightings in checked-in
workflow docs means this is a population, not two incidents** — sweep for it rather than patching the
three known strings.

### 4. Re-derive `check-routing-decisions` removal-cause regexes against the live emitter
`component=plan-marshall:plan-retrospective` · bug · high

The aspect **fabricates a `mis_prune`** because its regex expects a field order the `lane_resolution`
emitter no longer writes — likely broken by the `auto`→`standard` rename in **#1068**. The audit layer
emits a confident FAIL on a clean fact. **Hits every standard-posture plan.**

### 5. ⭐ Persist the landed footprint before `branch-cleanup` removes the worktree
`component=plan-marshall:phase-6-finalize` · bug · high

⛔ **SECOND SIGHTING — already delegated to you as `review-apparatus-008` item 3.** `branch-cleanup` is
order 70 and deletes the worktree; `plan-retrospective` is order 995 and derives the footprint from it,
so `check-artifact-consistency` reports `declared N, found 0` on **every plan reaching a normal
finalize**. ⚠ The sharper framing this sighting adds: an **unmeasurable** state is being rendered as a
**hard FAIL** rather than as *skipped*. A gate that always fails for the same reason stops being read.

### 6. Document all 11 `--termination-cause` values, not 6
`component=plan-marshall:manage-metrics` · anti-pattern · high — a documented index under-enumerates
the set it indexes.

### 7. First entry into `5-execute` logs `Re-entering`, never `Starting`
`component=plan-marshall:phase-5-execute` · bug · high

### 8. Emit a per-task `[ARTIFACT]` entry at task completion
`component=plan-marshall:phase-5-execute` · bug · high

### 9. Emit `[DISPATCH]` on re-fired and project-local dispatched finalize steps
`component=plan-marshall:phase-6-finalize` · improvement · high

### 10. Re-route `planning_lane` when `phase-2-refine` revises `scope_estimate` downward
`component=plan-marshall:phase-2-refine` · improvement · high

### 11. `extract-chat-signal` retains no operator decision turns
`component=plan-marshall:plan-retrospective` · improvement · medium

### 12. Context note — plugin cache staleness, now repaired
The cache is at **0.1.1279** with the executor regenerated. This closes the *instance* recorded in
`review-apparatus-008` item 2 — ⛔ **but not the signal gap**: `preflight` reporting `fresh` while blind
to the skill cache is still unfixed, and it is the root cause of a defect `review-apparatus` is keeping
(the pre-merge barrier executing a four-day-old `branch-cleanup.md`).

---

**Full message bodies**, append-only, at
`.plan/local/orchestrator/review-apparatus/inbox/archive/crashed-participation-gate-records-a-pass-0{02,03,08,09,10,11,12,13,14,15,16}.md`.
