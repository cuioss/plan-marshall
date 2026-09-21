envelope_version=1
sender_type=plan
sender_id=test-fidelity-rules
epic=test-quality
kind=landing
created=2026-09-19T10:28:28Z

# PLAN-180 carve-1 report: D5 shipped as PR #1538, carves 2-4 staged

## Outcome

- PR: https://github.com/cuioss/plan-marshall/pull/1538 (open, branch
  `feature/test-fidelity-rules`, commit `5194a64d0`)
- Scope: deliverable 5 (fixture docstrings say yield only when the fixture
  yields) — rule prose + guard test with matched controls + 10 live fixes.
- Verification at push time: `module-tests pm-dev-python` 36/36 green,
  `quality-gate pm-dev-python` green, module-tests green for tools-file-ops
  (202), manage-status (825), tools-integration-ci (490), script-shared
  (1445), tools-script-executor (483). No new skips.

## Outline-verification verdicts (recorded for the remaining deliverables)

- D1 hoisted argv: fix present in `test_build_execute_routing.py:64-81`,
  rule prose absent — carve-2.
- D2 prune stubbing: fix present in `test_build_cmd_coverage.py:42-67`,
  rule prose absent — carve-2.
- D3 tool-default docs: remediated prose present, mechanism test absent —
  carve-2.
- D4 seam-pinned mirrors: rule gap confirmed (search count 0) — carve-3.
- D7 skills-root patch: fix and rule prose both present — done.
- D8 single registration: fix present, rule prose absent — carve-3.
- D9 basetemp relocation: staged as dedicated carve-4 (blast radius: producer
  in `build.py`, contract test pin, dozens of repo-local-ancestry reasoners).

## Process filings

Three findings filed by `test-fidelity-rules` to the process-compliance inbox:
`test-fidelity-rules-001` (orchestrator spec-read gap),
`test-fidelity-rules-002` (carve-1 report, 9-deliverable split, lifecycle
shortcut disclosure), `test-fidelity-rules-003` (D9 staging evidence).

## Ask of the orchestrator

- Confirm the carve-2/3/4 sequence, or re-scope.
- Drain this message on PR #1538 merge (landing) or on review findings
  (rework).
