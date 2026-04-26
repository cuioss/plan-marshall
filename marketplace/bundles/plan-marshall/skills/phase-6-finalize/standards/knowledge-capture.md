---
name: default:knowledge-capture
description: Capture learnings to memory
order: 50
---

# Knowledge Capture

Pure executor for the `knowledge-capture` finalize step. Records significant patterns discovered during implementation. Advisory only — does not block.

This document carries NO step-activation logic. Activation is controlled by the dispatcher in `phase-6-finalize/SKILL.md` Step 3 and is driven solely by presence of `knowledge-capture` in `manifest.phase_6.steps`. When the dispatcher runs this step, the document executes top to bottom — there is no skip-conditional branching at this layer.

This step runs as a Task agent (`plan-marshall:knowledge-capture-agent`) under a 5-minute (300 s) per-agent timeout budget enforced by the SKILL.md Step 3 dispatch loop. On timeout the dispatcher records `outcome=failed` with `display_detail="timed out after 300s"` and continues — knowledge capture is advisory and never blocks the rest of the pipeline.

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
