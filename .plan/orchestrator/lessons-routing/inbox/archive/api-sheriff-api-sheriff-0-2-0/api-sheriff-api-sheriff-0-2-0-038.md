envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=finding
created=2026-10-21T12:52:14Z

# Candidate lesson: dispatched leaves had no Grep tool; the orchestrator ran the move-refactor sweeps (plan-marshall:execution-context dispatch contract)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-42-validator-auth-oidc-rules (PR cuioss/API-Sheriff#502), source message 003.

RECURRENCE: same class as archived pm-mcp-core-m2-m4-093 ("Give leaves a sanctioned content search when Grep is denied"). The suggested fix here is the same: `architecture search --content` inside the leaf.

**Routing:** project/process candidate. It may also touch plan-marshall's dispatch contract. The drain decides.
**Suggested component:** plan-marshall:execution-context (process)
**Category:** improvement
**Source:** orchestrator observation during PLAN-V02-42.

## What happened

The harness did not grant the Grep tool to the dispatched execution-context leaves in this
run. Content searches the leaves needed (callers of moved ConfigValidator members, and doc
references naming ConfigValidator as an owner) were therefore run on the orchestrator side
and passed back in. That cost extra round-trips and orchestrator context.

## Corrective action

For a refactor that moves members between classes, run the caller and doc-reference sweep in
the leaf with `architecture search --content --pattern P`, which is the sanctioned first-class
search inside a leaf. Do not rely on Grep or hand the sweep back. Return a coverage gap only
for trees the inventory does not walk. Consider naming this in the outline or task description
for move-refactor plans.
