---
name: default:knowledge-capture
description: Capture learnings to memory
order: 50
---

# Knowledge Capture

Record significant patterns discovered during implementation. Advisory only — does not block.

## Prerequisites

- Config field `5_knowledge_capture` is `true`

## Execution

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[SKILL] (plan-marshall:phase-6-finalize) Loading plan-marshall:manage-memories"
```

```
Skill: plan-marshall:manage-memories
```

**Use exactly this command** to save a memory (do not invent alternative flags):

```bash
python3 .plan/execute-script.py plan-marshall:manage-memories:manage-memory save \
  --category context \
  --identifier "{short-kebab-case-id}" \
  --content '{"pattern": "{description}", "context": "{when discovered}"}'
```

Note: `--content` must be valid JSON. Required flags: `--category`, `--identifier`, `--content`.

## Mark Step Complete

Before returning control to the finalize pipeline, record that this step ran on the live plan so the `phase_steps_complete` handshake invariant is satisfied at phase transition time.

Pass a `--display-detail` value alongside `--outcome done` so the output-template renderer can surface the capture outcome. The payload differs by branch:

**Branch A — pattern saved**: `{pattern_id}` is the `identifier` value passed to `manage-memory save` above.

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step knowledge-capture --outcome done \
  --display-detail "saved pattern: {pattern_id}"
```

**Branch B — no new pattern worth saving** (advisory step; the plan produced nothing novel enough to add to the memory store):

```bash
python3 .plan/execute-script.py plan-marshall:manage-status:manage_status mark-step-done \
  --plan-id {plan_id} --phase 6-finalize --step knowledge-capture --outcome done \
  --display-detail "no new pattern saved"
```
