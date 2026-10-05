envelope_version=1
sender_type=plan
sender_id=cross-check-dated-archive-self-collision
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-10-02T09:30:27Z

component=plan-marshall:phase-6-finalize
category=improvement
created=2026-10-02
source_plan=cross-check-dated-archive-self-collision
confidence=high

# Stop re-buying unchanged settle-band verdicts on every loop-back

## Context

The self-review loop ran four rounds. Before each round the three steps ahead of it re-fired because the commit had moved (logged reason: "verdict invalidated - verdict_inputs_undeclared"):

| Step | Dispatches | Tokens | Verdicts |
|------|------------|--------|----------|
| lessons-housekeeping | 4 | 540,442 | identical each time: 0 removed, 0 promoted, 0 adapted, 9 retained |
| finalize-step-simplify | 4 | 467,025 | 2 edits on the first, 0 edits after |
| plugin-doctor (scoped, 1 skill) | 4 | 430,756 | 0 issues each time |

That is 1,438,223 tokens of a 3,487,447-token finalize phase, on top of 1,714,458 for the four review rounds. The plan's whole budget anchor is 1.3M.

On the last re-entry all four steps were classified invalid again. The only commits since their verdicts were a docs-only deletion and the generated architecture descriptors that `architecture-refresh` commits - a finalize step ordered after the review band. The operator chose not to re-fire them.

## Root cause

Verdict currency is keyed on the commit alone for a step that declares no verdict inputs, so any commit invalidates it, including one that cannot change its answer. Two consequences are structural, not incidental:

- lessons-housekeeping depends on the lessons corpus and the plan's file set; neither changed across four firings.
- A finalize step that commits after the review band guarantees the band reads as invalid on every later re-entry.

## Proposed action

1. Declare verdict inputs for the three steps: housekeeping = lessons-corpus digest plus footprint path set; plugin-doctor = content of the gated skill directories; simplify = the footprint files' diff.
2. Leave finalize-internal generated commits (`.plan/project-architecture/**`) out of the currency comparison.
3. In housekeeping, retain a lesson whose component maps to no footprint path without an LLM pass (all 36 retain decisions in this run were of that kind).

## Evidence

- metrics dispatch boundaries, 6-finalize: 18 rows, token figures above
- work.log 2026-10-01T10:56:22Z, 10:58:21Z, 11:00:18Z (re-fire reasons)
- decision.log 2026-10-02T08:37:20Z (operator override on re-entry, four steps not re-stamped)
- status: `firing_count` 4 (housekeeping), 5 (simplify), 4 (plugin-doctor), 5 (self-review); simplify shows 5 against 4 dispatch rows and 4 completion lines - not reconciled here
