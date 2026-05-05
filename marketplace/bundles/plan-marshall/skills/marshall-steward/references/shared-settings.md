# Shared: Configuration Settings

> **DEPRECATED**: Configuration options are now managed by `plan-marshall:manage-config`.
> This file is retained for reference during the transition period.
> Wizard-flow.md and menu-configuration.md now delegate to manage-config script calls.

Reusable configuration workflows for plan phases, review gates, and quality pipelines. Previously used by both wizard-flow and menu-configuration.

---

## Plan Phase Settings

Configure plan phase settings for branching, compatibility, and commit strategy.

These settings take effect during their respective phases:
- **Branch strategy** → consumed by phase-1-init (branch creation)
- **Backward compatibility** → consumed by phase-2-refine (requirement analysis) and phase-5-execute (implementation decisions)
- **Commit strategy** → consumed by phase-5-execute (when to commit) and phase-6-finalize (final commit)

### Branch Strategy

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

### Backward Compatibility

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

### Commit Strategy

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

### Rebase on Execute Start

```
AskUserQuestion:
  question: "Sync feature branch against origin/{base} at the start of phase-5-execute?"
  header: "Sync"
  options:
    - label: "Enabled (Recommended)"
      description: "Run the sync-with-main step before the task loop; catches drift before coding starts"
    - label: "Disabled"
      description: "Skip the sync step; rely on phase-6-finalize 'pr update-branch' as the only sync point"
  multiSelect: false
```

Maps to values: `true`, `false` (default `true`)

Apply selection:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set --field rebase_on_execute_start --value {true|false}
```

### Rebase Strategy

```
AskUserQuestion:
  question: "Strategy used by the phase-5-execute sync-with-main step?"
  header: "Rebase"
  options:
    - label: "Merge (Recommended)"
      description: "git merge --no-edit origin/{base} — no history rewrite, PR-safe"
    - label: "Rebase"
      description: "git rebase origin/{base} — rewrites history, requires force-push when PR is already open"
  multiSelect: false
```

Maps to values: `merge`, `rebase` (default `merge`)

Apply selection:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set --field rebase_strategy --value {merge|rebase}
```

---

## Review Gates

Configure whether phase transitions pause for user review or auto-continue.

Default: none selected (conservative — all transitions pause for user review before proceeding to the next phase).

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

---

## Quality Pipeline Configuration

Configure verification (phase 5 sub-loop) and finalize (phase 6-finalize) pipeline settings.

### Verification Steps

Discover available verify steps from all sources:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  list-verify-steps
```

Present the merged list (built-in + extension steps) as a multi-select:

```
AskUserQuestion:
  question: "Which verification steps to include?"
  header: "Verify Steps"
  multiSelect: true
  options:
    # Dynamic from list-verify-steps output:
    - label: "1_quality_check (Recommended)"
      description: "Build quality gate using canonical commands"
    - label: "2_build_verify (Recommended)"
      description: "Build verification using canonical commands"
    # Plus any extension steps from discovery
```

Apply: write the selected steps as an ordered list:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set-steps --steps {comma_separated_selected_steps}
```

**Domain verification steps** are auto-populated from extensions during skill domain configuration. Each domain bundle declares its verification steps via `provides_verify_steps()` in `extension.py`. Precedence: extension steps > project steps > built-in steps.

### Finalize Steps

Discover available finalize steps from four sources:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  list-finalize-steps
```

This returns all discoverable steps from:
1. **Built-in steps**: Hard-coded in `_config_defaults.BUILT_IN_FINALIZE_STEPS` with descriptions
2. **Project steps**: Discovered from `.claude/skills/finalize-step-*` directories
3. **Extension steps**: Discovered via `provides_finalize_steps()` on domain extensions
4. **Bundle-optional steps**: Declared in `_config_defaults.OPTIONAL_BUNDLE_FINALIZE_STEPS` (e.g., `plan-marshall:plan-retrospective`). These surface in the discovery list but are intentionally omitted from `DEFAULT_PLAN_FINALIZE['steps']`, so projects must explicitly select them here to opt in.

Precedence: extension steps > project steps > built-in steps (names must be unique). Bundle-optional entries are deduplicated against the earlier three sources and appended last.

Present the merged list as a multi-select. If total steps exceed 4, use paging (4 options per page with "More..." option).

```
AskUserQuestion:
  question: "Which finalize steps to include?"
  header: "Finalize Steps"
  multiSelect: true
  options:
    # Built-in steps (from list-finalize-steps output):
    - label: "commit_push (Recommended)"
      description: "Commit and push changes"
    - label: "create_pr"
      description: "Create pull request"
    - label: "automated_review"
      description: "CI automated review"
    - label: "sonar_roundtrip"
      description: "Sonar analysis roundtrip"
    # Page 2 (if paging needed):
    - label: "lessons_capture (Recommended)"
      description: "Record lessons learned"
    - label: "branch_cleanup"
      description: "Merge PR (with --delete-branch) and pull latest"
    - label: "archive"
      description: "Archive the completed plan"
    # Bundle-optional steps (opt-in; listed but absent from default config):
    - label: "plan-marshall:plan-retrospective (Opt-in)"
      description: "Capture a structured retrospective of the completed plan"
    # Extension/project steps (dynamic, from list-finalize-steps):
    # - label: "{step_name}"
    #   description: "{step_description}"
```

Apply: write the selected steps as an ordered list:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize set-steps --steps {comma_separated_selected_steps}
```

### Max Iterations

```
AskUserQuestion:
  questions:
    - question: "Max iterations for verification (phase 5 sub-loop)?"
      header: "Verify Iters"
      multiSelect: false
      options:
        - label: "5 (Recommended)"
          description: "Standard retry limit for quality checks"
        - label: "3"
          description: "Fewer retries, faster completion"
        - label: "10"
          description: "More retries for complex projects"
    - question: "Max iterations for finalize phase (phase 6-finalize)?"
      header: "Finalize Iters"
      multiSelect: false
      options:
        - label: "3 (Recommended)"
          description: "Standard retry limit for commit/PR/CI"
        - label: "1"
          description: "Single attempt, fail fast"
        - label: "5"
          description: "More retries for CI roundtrips"
```

Apply selections:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set-max-iterations --value {5|3|10}
```

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize set-max-iterations --value {3|1|5}
```
