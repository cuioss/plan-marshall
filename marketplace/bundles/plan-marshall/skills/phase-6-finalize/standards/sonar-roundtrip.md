# Sonar Roundtrip

Sonar quality gate check and issue resolution.

## Prerequisites

- Config field `4_sonar_roundtrip` is `true`

## Execution

```bash
python3 .plan/execute-script.py plan-marshall:manage-logging:manage-logging \
  work --plan-id {plan_id} --level INFO --message "[SKILL] (plan-marshall:phase-6-finalize) Loading plan-marshall:workflow-integration-sonar"
```

```
Skill: plan-marshall:workflow-integration-sonar
```

Handles Sonar quality gate and issue resolution. On findings, follows the same loop-back pattern as automated review:

1. Create fix tasks for Sonar issues
2. Loop back to phase-5-execute via `manage-status transition --loop-back 5-execute`
3. Continue until clean or max iterations (3)
