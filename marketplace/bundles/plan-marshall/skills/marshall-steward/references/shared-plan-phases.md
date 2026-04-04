# Shared: Plan Phase Settings

Configure plan phase settings for branching, compatibility, and commit strategy.

---

## Branch Strategy

```
AskUserQuestion:
  question: "Branch strategy for plan execution?"
  header: "Branching"
  options:
    - label: "Feature branch (Recommended)"
      description: "Create feature branch per plan"
    - label: "Direct"
      description: "Work on current branch"
  multiSelect: false
```

Apply selection:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-1-init set --field branch_strategy --value {direct|feature}
```

## Backward Compatibility

```
AskUserQuestion:
  question: "Backward compatibility approach during plan execution?"
  header: "Compat"
  options:
    - label: "Breaking (Recommended)"
      description: "Clean-slate approach, no deprecation nor transitionary comments"
    - label: "Deprecation"
      description: "Add deprecation markers to old code, provide migration path"
    - label: "Smart and ask"
      description: "Assess impact and ask user when backward compatibility is uncertain"
  multiSelect: false
```

Maps to values: `breaking`, `deprecation`, `smart_and_ask`

Apply selection:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-2-refine set --field compatibility --value {breaking|deprecation|smart_and_ask}
```

## Commit Strategy

```
AskUserQuestion:
  question: "Commit strategy during plan execution?"
  header: "Commits"
  options:
    - label: "Per deliverable (Recommended)"
      description: "Commit after all tasks for each deliverable complete (impl + tests)"
    - label: "Per plan"
      description: "Single commit of all changes at finalize"
    - label: "None"
      description: "No automatic commits"
  multiSelect: false
```

Maps to values: `per_deliverable`, `per_plan`, `none`

Apply selection:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set --field commit_strategy --value {per_deliverable|per_plan|none}
```
