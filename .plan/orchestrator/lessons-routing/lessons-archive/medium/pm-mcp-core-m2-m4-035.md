envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-10T20:00:35Z

# Candidate lesson: init scope heuristic counts every file path in the spec body, including read-only references and exclusions

**Signal source**: Q-Gate finding (`signal_qgate_pending_count`); finding `edbdc6`, resolution `taken_into_account` in phase 2-refine

**Components**: `plan-marshall:phase-1-init` (scope / planning-lane routing heuristic), with `plan-marshall:phase-2-refine` as the corrector

## Observation

The ingested orchestrator spec body named 8 file paths. Most of them were read-only references or explicit exclusions, not files to modify. The init scope heuristic counted all 8 and routed a one-line config change to the deep lane with `multi_module` scope. Refine then corrected it to `surgical`, which the Q-Gate finding `edbdc6` records.

The run recovered, but only because refine caught the misrouting. A spec that carries rich context (references, do-not-touch lists) inflates the computed scope.

## Suggested corrective action (for orchestrator triage)

When an orchestrator spec declares an `## Expected Surface`, have init weight the scope on the declared surface (claimed versus excluded entries) rather than on a raw path count over the whole body. Otherwise, at least leave out paths that appear under reference or exclusion headings. On the epic side, spec authors could keep the Expected Surface precise so the declared claimed set drives routing.

Category guess: improvement

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-38-review-bot-re-review-003.md` from plan plan-38-review-bot-re-review (PLAN-38, #24)
