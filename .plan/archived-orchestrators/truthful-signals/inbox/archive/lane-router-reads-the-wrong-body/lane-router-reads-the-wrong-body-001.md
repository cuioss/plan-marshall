envelope_version=1
sender_type=plan
sender_id=lane-router-reads-the-wrong-body
epic=truthful-signals
kind=landing
created=2026-07-29T09:52:56Z

## What landed

**Plan**: `lane-router-reads-the-wrong-body` — "Lane router reads the wrong body and counts the wrong things"
**PR**: [#1049](https://github.com/cuioss/plan-marshall/pull/1049) — `fix(planning-lane): score actual request body, not truncated header`
**Branch**: `feature/lane-router-reads-the-wrong-body` → `main`
**State at emission**: PR open, `mergeable: mergeable`, `merge_state: clean`, all checks green. Merge happens after this step in the finalize order.

**Diff footprint** (6 files, +839 / -48):

| File | Role |
|------|------|
| `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_planning_lane.py` | The fix — scope-estimate scorer now reads the actual request body |
| `marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py` | Wiring |
| `marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md` | Contract doc |
| `marketplace/bundles/plan-marshall/skills/phase-1-init/SKILL.md` | Caller contract |
| `test/.../manage-status/test_planning_lane.py` | Extended |
| `test/.../test_planning_lane_request_body.py` | New — body-read regression suite |

Theme fit: **confident-signal-hides-a-caveat**. The lane router emitted a confident `planning_lane` verdict computed from a body it never actually read.

## Verification state

- `quality-gate` green (1 bundle + whole-tree).
- `verify plan-marshall` green — 13528 tests.
- `ci-verify`: all checks green.
- ⛔ **`verify:coverage` WAS NOT RUN.** `marshalld` refused the submit with `executor_mismatch` — this plan edits the bundle that defines the executor, so the anti-laundering wall fired correctly. Inline execution needs ~1387s against a 600s Bash ceiling. **Operator chose to skip.** Note the wrapper's own routing seam DID reach the daemon successfully for every other build in this run (`mechanism=daemon_longpoll`); only the raw `submit` verb refused. That asymmetry is filed as a candidate below.

## Review coverage — REDUCED BY OPERATOR DECISION

- `coderabbit` (required bot) was **rate-limited and did NOT review #1049**. Verified through `ci pr comments` — the evidence standard, not the check state: the bot posted `Review limit reached, next review in 52 minutes`.
- `sourcery` hit its **weekly hard quota**.
- Only `pr-agent` reviewed. `review-retrospective`: 1 reviewer compared, 0 actionable comments.
- The operator explicitly chose **merge-anyway**.
- ✅ **The participation guard behaved correctly**: it detected the non-participation and looped back rather than reporting a clean review. This is the inverse of the #1026 finding (a *detected* refusal reported as a clean review). Record the positive.
- ⚠ Standing obligation applies: this landing owes a **post-merge PR revisit** — the merge outruns the review, and a late coderabbit review after the 52-minute window is a recurrence, not an incident. Scan sibling PRs too.

## Residue the epic should track

Eight candidate-lesson messages follow this landing. The two highest-value ones for the epic's theme:

1. **The plan reproduced its own target defect at init** — `scope-estimate-heuristic` scored `distinct_path_count=1` and the sole counted path was the plan-spec boilerplate citation `persona-marshall-orchestrator/standards/orchestration-model.md`. A *citation*, not a target. Every real target was missed. That produced `planning_lane=light` + `execution_profile=minimal`; only a manual operator escalation to `deep` prevented the light route. Same self-sealing shape as the spec's Seventh Instance. Final status.json shows `planning_lane: deep, lane_escalated: true, escalation_trigger: premise, confidence: 99.5` — the escalation is visible, the near-miss is not.

2. **The spec's own stated mechanism for Defect A was WRONG, and the fix corrected it.** The spec claimed `## Original Input` is EMPTY (0 bytes) with a fallback to the `source_id` header. Refuted at HEAD. Real mechanism: the section is **TRUNCATED, not empty**. Same verdict, different evidence. Write-up at `work/d1-verdict.md`.

Two adjacent defects were found and **deliberately NOT fixed** in this plan — they need routing:

- `_GLOB_RE` at `_cmd_planning_lane.py:122` **matches markdown bold** (`\*\*` alternative fires on `**bold**`), and the glob check short-circuits before path counting. Likely **PLAN-57** territory. Under the new whole-body read it will fire MORE often.
- A **live value divergence in this very plan**: `phase-2-refine` logged `Scope: surgical - Modules: 1, Files: 3` yet `references.json` held `single_module`. Undetermined mechanism; leans toward a dropped persist (PLAN-86 unchecked-persist archetype).

Plus a doc-contract contradiction (`dispatch-inline-split.md` vs two other docs, 2-vs-1 against the declared source of truth) and a freshness-gate weakness (`--help` invocations recorded as build evidence).
