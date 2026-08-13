# Run report — 170-finalize-dispatch-evidence-is-missing (run 01)

**Date (UTC):** 2026-08-13    **Branch:** `claude/finalize-dispatch-evidence-hgcl9s` (harness-assigned; kept as-is)    **PR:** _pending_    **Outcome:** _in progress_

This plan owns the **detector** (the execution-context dispatch audit) and the **per-task
artifact emitter**. The dispatch-line EMISSION is out of scope (owned by a sibling plan).

## Skills loaded

- `cloud-plan-lane` (first action, governs the run).
- `plan-marshall:ref-code-quality` (read by bundle path).
- `pm-plugin-development:plugin-script-architecture` (read by bundle path).
- `pm-dev-python:python-core`, `pm-dev-python:pytest-testing` (read by bundle path — Python production + tests).

GitHub access path: **GitHub MCP server** (cloud session). Branch form: **harness-assigned** `claude/*`.

## Outline findings (pre-implementation)

_Being established. Key facts settled in the clone:_

- The dispatch audit (aspect 11) is an **LLM-only aspect** — its detection logic is prose in
  `plan-retrospective/standards/execution-context-dispatch-audit.md`; there is **no deterministic
  script** implementing `shape_violation` / `dispatch_coverage_violation`. `audit.py`'s
  `check_dispatch_topology` (leaf invariant) and `check_finalize_flow_conformance` (ci_verify) are
  unrelated checks. ⇒ To make the detector *able to fail* and *testable* (D1/D5), a deterministic
  detector must be built (matching the SKILL's already-established script-backed-facts pattern for
  aspects 1-3, 8, 10, 12, 13).
- **D1 premise shift (settled in the clone):** a Surface B producer now EXISTS — the merged sibling
  plan (`truthful-signals/280`, PR #1200) moved dispatch-record emission into the `effort
  resolve-target` seam (`manage-config/scripts/_cmd_effort.py`), which writes both Surface A and
  Surface B when passed `--workflow`. So "no producer at all" is no longer literally true at HEAD;
  the vacuity now stems from the producer being **under-wired** (most dispatch sites still hand-write
  Surface A only and never emit Surface B). Detail recorded under Deliverables/D1.

## Deliverables

_In progress._

## Build gate

_Pending._

## Findings

_Pending._

## Reviewer participation

_Pending._

## Cost

_Pending._

## Contract check (Step 9)

_Pending._

## What have we learned (Step 9)

_Pending._

## Residue

_Pending._
