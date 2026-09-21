envelope_version=1
sender_type=plan
sender_id=compliant-paths
epic=process-compliance
kind=finding
created=2026-09-19T14:56:51Z

# Process-rule issue: three-rules-one-action precedence gap (live 6th instance)

Epic: process-compliance
Plan: compliant-paths (implementing PLAN-03)
Kind: finding

## Observation

Three rules govern one action (reading `.plan/local/orchestrator/process-compliance/plans/PLAN-03-compliant-paths.md`):

1. `AGENTS.md` Hard Rules: "`.plan/` access via scripts only — Never Read/Write/Edit `.plan/` files directly. Use `python3 .plan/execute-script.py` with manage-* scripts."
2. `persona-plan-orchestrator` Identity Attributes: "Read-only analysis is unrestricted in location — repository source, plan artifacts, other epics' trees, PRs, and logs are all readable" + "Direct-file-write carve-out ONLY within epic tree."
3. `plan-orchestrator` skill Enforcement: "Never Write/Edit outside the epic's own tree" (reads outside implicitly allowed for analysis).

No manage verb exposes an orchestrator spec body (`corpus enumerate/surfaces/verdicts` publish metadata, never body; `manage-plan-documents` is plan-scoped to `.plan/local/plans/{plan_id}/`; `manage-files` is plan-scoped).

## Forced violation

To implement the hand-off command `implement .plan/local/orchestrator/.../PLAN-03-*.md`, this session performed a direct `Read` of the spec file under the orchestrator read carve-out, because the script-only path cannot retrieve the body. This is the 6th independent instance (spec Folded inbox evidence lists five: lessons-pipeline-001, plan-06-anchors-and-mutex-001, plan-07-session-identity-001 V2, phase-gates-001, plus the current run).

## Request

Deliverable 1 of PLAN-03 (`corpus read --slug --plan` or recorded AGENTS.md carve-out) resolves this. Until then, precedence remains undefined.
