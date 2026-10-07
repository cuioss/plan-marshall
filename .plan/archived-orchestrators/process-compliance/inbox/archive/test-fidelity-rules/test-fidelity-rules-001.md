envelope_version=1
sender_type=plan
sender_id=test-fidelity-rules
epic=process-compliance
kind=finding
created=2026-09-19T10:14:54Z

# Process-rule gap: no script-mediated read path for orchestrator staged specs

## Observed

- The sanctioned PLAN-180 Hand-Off Command is `/plan-marshall task="implement .plan/local/orchestrator/test-quality/plans/PLAN-180-test-fidelity-rules.md"`.
- `plan-marshall:manage-files:manage-files read` resolves only the plan store (`.plan/local/plans/{plan_id}`); it has no orchestrator-store read verb.
- `plan-marshall:plan-orchestrator:orchestrator corpus *` verbs reconcile and publish surfaces/verdicts but return no full spec body.
- Phase-1-init Step 4 file-pointer branch ingests via `manage-plan-documents request create --body-file {spec_path}`, which is the only script-mediated read of the spec encountered. That ingestion path is documented for request creation, not as a general orchestrator-spec reader.

## Conflict

- AGENTS.md hard rule: `.plan/` access via scripts only — never Read `.plan/` files directly.
- Orchestration-model small-ops carve-out: reads are unrestricted in location because reading mutates nothing.
- To implement the Hand-Off Command, the executor must obtain the spec body. With no general orchestrator-spec read verb, strict compliance forces a choice between a direct `Read` of a `.plan/` file (AGENTS.md violation) and leaving the brief unread (cannot implement).

## What was done on this run

- Listed spec presence via `manage-files discover` (script-mediated).
- Ingested the spec body via `manage-plan-documents request create --body-file` under plan `test-fidelity-rules` (script-mediated, phase-1-init Step 4 file-pointer branch).
- Performed outline-verification reads of the spec and its lesson evidence via direct `Read` under the small-ops read-only-analysis carve-out, logged here as the residual gap.

## Request

- Publish one sanctioned orchestrator spec reader (for example `orchestrator corpus read --slug {slug} --plan {plan-nn}` returning the full body), or document that Hand-Off Command ingestion via `request create --body-file` is the sanctioned read path and that outline-verification re-reads ride the same verb.
- Until then, this filing records the deviation and its justification rather than leaving it silent.
