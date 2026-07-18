# Menu Option: Health Check

Verify the planning system setup and diagnose issues. Run all checks and report results.

---

## Step 1: Verify Executor

Check executor exists, is valid, and in sync with marketplace:

```bash
python3 .plan/execute-script.py plan-marshall:tools-script-executor:generate_executor verify
```

**Output (TOON)**:
```toon
status	script_count
ok	47
```

If status is `error` or executor missing: Offer to regenerate via Maintenance menu.

---

## Step 2: Check Executor Drift

Compare executor mappings with current marketplace state:

```bash
python3 .plan/execute-script.py plan-marshall:tools-script-executor:generate_executor drift
```

**Output (TOON)**:
```toon
status	added	removed	changed
ok	0	0	0
```

If drift detected (added/removed/changed > 0): Offer to regenerate executor.

---

## Step 3: Verify Plugin Wildcards

Check that enabled plugins have corresponding Skill/SlashCommand wildcards:

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix ensure-wildcards \
  --settings ~/.claude/settings.json \
  --marketplace-json marketplace/.claude-plugin/marketplace.json \
  --dry-run
```

**Interpret results**:
- `added: []` → All wildcards present PASS
- `added: [...]` → Missing wildcards, offer to add them

### Sub-check: Project-step permission rules

Check that every `project:{skill}` step referenced in `marshal.json` has a matching `Skill({skill})` allow rule in project settings:

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-doctor:permission_doctor detect-missing-project-step-permissions \
  --marshal .plan/marshal.json \
  --scope project
```

**Interpret results**:
- `missing: []` → All project-step permissions present PASS
- `missing: [...]` → Missing rules, report alongside wildcard gaps

Aggregate gaps from both checks into a single prompt. If either `added` (wildcards) or `missing` (project-step rules) is non-empty, ask user once:

```text
AskUserQuestion:
  question: "Found {N_wildcards} missing plugin wildcards and {N_project_steps} missing project-step rules. Add them?"
  options:
    - label: "Yes"
      description: "Add missing wildcards to global settings and project-step rules to project settings"
      value: "yes"
    - label: "No"
      description: "Skip (may cause permission prompts)"
      value: "no"
```

If yes:
- Run `ensure-wildcards` without `--dry-run` (if wildcards were missing)
- Run the fix without `--dry-run` (if project-step rules were missing):
  ```bash
  python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix apply-project-step-permissions \
    --marshal .plan/marshal.json \
    --settings .claude/settings.json
  ```

Include `project_step_permissions` alongside `wildcards` in the Step 7 summary TOON (e.g., `project_step_permissions: {total: 2, missing: 0}`).

---

## Step 4: Check for Stale Permissions

Detect permissions that are redundant (exact duplicates of global rules or covered by a broader global wildcard) or misplaced (marketplace permissions sitting in project-local settings when they should be global):

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-doctor:permission_doctor detect-redundant --scope both
```

**Interpret results**:
- `summary.redundant_count: 0` AND `summary.marketplace_in_local_count: 0` → No redundant permissions PASS
- `summary.redundant_count > 0` OR `summary.marketplace_in_local_count > 0` → Issues found, offer to fix

When issues are found, first preview the changes with `--dry-run`:

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix remove-redundant \
  --scope both \
  --dry-run
```

Then prompt the user once:

```text
AskUserQuestion:
  question: "Found {redundant_count} redundant permissions and {marketplace_count} marketplace permissions in project-local settings. Remove redundant entries and move marketplace permissions to global settings?"
  options:
    - label: "Yes"
      description: "Remove redundant local permissions and move marketplace permissions to global settings"
      value: "yes"
    - label: "No"
      description: "Skip (permissions stay as-is)"
      value: "no"
```

If yes, apply the fix:

```bash
python3 .plan/execute-script.py plan-marshall:tools-permission-fix:permission_fix remove-redundant \
  --scope both
```

Include `redundant_permissions` in the Step 7 summary TOON (e.g., `redundant_permissions: {redundant: 0, marketplace_moved: 0}`).

---

## Step 5: Check Project Structure

Verify project structure knowledge base exists:

```bash
python3 .plan/execute-script.py plan-marshall:marshall-steward:determine_mode check-structure
```

**Interpret results**:
- `status: exists` → Project structure configured PASS
- `status: missing` → No project structure (placement context unavailable)

If missing, show info message (not blocking):
```text
[INFO] Project structure not configured. Solution outline will use standard codebase analysis.
       To enable: /marshall-steward → Configuration → Project Structure → Regenerate
```

---

## Step 6: Verify CI Tools

Check CI provider detection and tool availability:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci_health status
```

**Interpret results**:
- `overall: healthy` → All CI tools ready PASS
- `overall: degraded` → Provider detected but tool not authenticated
- `overall: unknown` → Could not detect CI provider

If tool not authenticated, show:
```text
AskUserQuestion:
  question: "CI tool '{tool}' is not authenticated. Run '{tool} auth login' to authenticate."
  options:
    - label: "Continue"
      description: "Skip CI tool verification"
      value: "continue"
```

---

## Step 6b: Check Terminal Title Hook

Verify whether the SessionStart hook for the dynamic terminal title is installed:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime \
  health-check --checks all
```

Inspect the `hook` entry in the `results` array:
- `hook.healthy: true` → Terminal title hook installed PASS
- `hook.healthy: false` → Hook not installed; offer to enable

When `hook.healthy` is false, prompt the user:

```text
AskUserQuestion:
  question: "The terminal title SessionStart hook is not installed. Enable it now? (Shows active plan, phase, and status in the terminal tab.)"
  options:
    - label: "Enable"
      description: "Install the SessionStart hook into ./.claude/settings.local.json"
      value: "enable"
    - label: "Skip"
      description: "Leave terminal title disabled"
      value: "skip"
```

If the user chooses **Enable**, install the hook:

```bash
python3 .plan/execute-script.py plan-marshall:platform-runtime:platform_runtime \
  project install-hook --target .claude/settings.local.json
```

Report the result:
- `status: success` with `already_present: false` → Hook installed successfully
- `status: success` with `already_present: true` → Hook was already present
- `status: error` → Report `message` and advise checking write permissions on `./.claude/settings.local.json`
- `status: no-op` → Platform does not support this hook (e.g. OpenCode); report info and continue

If the user chooses **Skip**: continue to Step 7.

Include `terminal_title` in the Step 7 summary TOON (e.g., `terminal_title: {hook_installed: true}`).

---

## Step 6c: Check for Dropped Finalize Steps

Detect finalize steps absent from `marshal.json::plan.phase-6-finalize.steps` — both newly-added built-in `default:` steps and, critically for the **meta-project**, any shipped `project:` finalize-step skill that was dropped from the steps array. Re-running the steward must NOT silently lose hand-maintained project-local finalize steps:

```bash
python3 .plan/execute-script.py plan-marshall:marshall-steward:determine_mode check-missing-finalize-steps
```

The check discovers shipped `project:` steps from `<project-root>/.claude/skills/finalize-step-*` (each `finalize-step-<name>/SKILL.md` maps to `project:finalize-step-<name>`) and compares them against the configured steps. **Interpret results**:

- `status: ok` → No dropped finalize steps PASS
- `status: missing` → One or both of:
  - `missing_default_finalize_steps` — newly-added built-in defaults absent from the array
  - `missing_project_finalize_steps` — shipped `project:` steps absent from the array (the meta-project drift case)

When `missing_project_finalize_steps` is non-empty, show:

```text
[WARN] Project-local finalize steps shipped under .claude/skills/ are missing from
       phase-6-finalize.steps: {missing_project_finalize_steps}. These are hand-maintained
       on the meta-project (presets are consumer-scoped and never seed project: steps).
       Re-add them to plan.phase-6-finalize.steps to restore the dropped steps.
```

Consumer projects ship no `project:` finalize steps, so `missing_project_finalize_steps` is always absent there — the warning is meta-project-specific. Include `finalize_steps` in the Step 7 summary TOON (e.g., `finalize_steps: {missing_default: 0, missing_project: 0}`).

---

## Step 6d: Check Executor / Config Staleness

Run the deterministic staleness preflight. See [SKILL.md § "Executor & Config Staleness Signaling"](../SKILL.md#executor--config-staleness-signaling) for the canonical asymmetric-ownership rules (executor = safe derived state, ADR-002; `marshal.json` = user decisions, never auto-mutated) this check applies:

```bash
python3 .plan/execute-script.py plan-marshall:marshall-steward:determine_mode check-staleness
```

**Interpret results** (the `marshal_status: unknown` case is evaluated FIRST, regardless of the other fields, so an unresolvable-manifest verdict is never mistaken for a clean `fresh` pass):

- `marshal_status: unknown` → the installed `dist-manifest.json` could not be resolved, so version-based staleness cannot be determined — the preflight failed CLOSED. Surface the cannot-determine warning (echo the returned `warning` field) rather than reporting a clean pass:

```text
[WARN] Executor/config staleness could not be determined: {warning}.
       Verify the install, or regenerate the executor manually
       (Maintenance → Regenerate Executor), then re-run /marshall-steward.
```

- `executor_action: fresh` → Executor version current PASS
- `executor_action: regenerated` → Executor was stale and regenerated in place. Surface the session-restart guardrail (see [SKILL.md](../SKILL.md#session-restart-required-after-executor--agent-changes)) — the emitted agent set may have changed, so the running session must restart before dispatching against it.
- `marshal_status: fresh` → Config seed current PASS
- `marshal_status: stale` → The config seed is behind the installed distribution. Advise (non-blocking):

```text
[INFO] marshal.json config seed is stale relative to the installed distribution.
       Re-run /marshall-steward (menu mode) to refresh the provisioning stamps via
       the config reconcile (Re-Run Remediation Pass step d). marshal.json is never
       auto-mutated.
```

A fresh install with no resolvable manifest reports `executor_action: fresh` / `marshal_status: unknown` with a populated `warning` field — the fail-closed verdict, never a vacuous `fresh` (`installed_version` resolves to the `unknown` sentinel rather than the empty sentinel). Include `staleness` in the Step 7 summary TOON (e.g., `staleness: {executor_action: fresh, marshal_status: fresh, warning: ""}`).

---

## Step 7: Summary

Output health check summary. Use `status: success` and `overall: HEALTHY` when all checks passed. Use `status: warning` and `overall: DEGRADED` when any check reported issues.

**Healthy System** (all checks passed):
```toon
status: success
operation: health_check

executor:
  valid: true
  script_count: 47
  drift: none
wildcards:
  total: 16
  missing: 0
project_step_permissions:
  total: 2
  missing: 0
redundant_permissions:
  redundant: 0
  marketplace_moved: 0
project_structure: configured
ci:
  provider: github
  required_tool: gh
  tool_ready: true
terminal_title:
  hook_installed: true

overall: HEALTHY
```

**System with Issues** (one or more checks reported problems):
```toon
status: warning
operation: health_check

executor:
  valid: true
  script_count: 47
  drift: 3 added, 1 removed
wildcards:
  total: 16
  missing: 2
project_step_permissions:
  total: 2
  missing: 1
redundant_permissions:
  redundant: 8
  marketplace_moved: 11
project_structure: missing
ci:
  provider: github
  required_tool: gh
  tool_ready: false
terminal_title:
  hook_installed: false

issues:
  - Executor drift detected (regenerate recommended)
  - 2 plugin wildcards missing
  - 1 project-step permission rule missing
  - 8 redundant permissions + 11 misplaced marketplace permissions in project settings
  - Project structure not configured
  - CI tool 'gh' not authenticated
  - Terminal title SessionStart hook not installed

fixes_available: true
```

---

After health check completes, return to Main Menu.
