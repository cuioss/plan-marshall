# Shared: Quality Pipeline Configuration

Configure verification (phase 5 sub-loop) and finalize (phase 6-finalize) pipeline settings.

---

## Verification Steps

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

**Domain verification steps** are auto-populated from extensions during skill domain configuration. Each domain bundle declares its verification steps via `provides_verify_steps()` in `extension.py`.

---

## Finalize Steps

Discover available finalize steps from three sources:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  list-finalize-steps
```

This returns all discoverable steps from:
1. **Built-in steps**: Hard-coded in `_config_defaults.BUILT_IN_FINALIZE_STEPS` with descriptions
2. **Project steps**: Discovered from `.claude/skills/finalize-step-*` directories
3. **Extension steps**: Discovered via `provides_finalize_steps()` on domain extensions

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
    - label: "knowledge_capture (Recommended)"
      description: "Capture learnings to memory"
    - label: "lessons_capture (Recommended)"
      description: "Record lessons learned"
    - label: "branch_cleanup"
      description: "Merge PR (with --delete-branch) and pull latest"
    - label: "archive"
      description: "Archive the completed plan"
    # Extension/project steps (dynamic, from list-finalize-steps):
    # - label: "{step_name}"
    #   description: "{step_description}"
```

Apply: write the selected steps as an ordered list:
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize set-steps --steps {comma_separated_selected_steps}
```

---

## Max Iterations

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
