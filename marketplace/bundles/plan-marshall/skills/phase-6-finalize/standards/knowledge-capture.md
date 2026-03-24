# Knowledge Capture

Record significant patterns discovered during implementation. Advisory only — does not block.

## Prerequisites

- Config field `5_knowledge_capture` is `true`

## Execution

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-log \
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
