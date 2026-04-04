# Shared: Review Gates

Configure whether phase transitions pause for user review or auto-continue.

---

```
AskUserQuestion:
  question: "Which phase transitions should auto-continue without pausing for review?"
  header: "Review Gates"
  multiSelect: true
  options:
    - label: "Plan without asking"
      description: "Auto-continue from outline (phase 3) to planning (phase 4)"
    - label: "Execute without asking"
      description: "Auto-continue from planning (phase 4) to execution (phase 5)"
    - label: "Finalize without asking"
      description: "Auto-continue from execution (phase 5) to finalize (phase 6)"
```

Default: none selected (conservative — all transitions pause for review).

Apply: for each selected gate, set to `true`. For each deselected gate, set to `false`.

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-3-outline set --field plan_without_asking --value {true|false}
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-4-plan set --field execute_without_asking --value {true|false}
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set --field finalize_without_asking --value {true|false}
```
