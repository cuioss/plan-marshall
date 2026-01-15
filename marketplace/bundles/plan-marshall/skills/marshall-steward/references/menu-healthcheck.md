# Menu Option: Health Check

Verify the planning system setup and diagnose issues. Run all checks and report results.

---

## Step 1: Verify Executor

Check executor exists, is valid, and in sync with marketplace:

```bash
python3 .plan/execute-script.py plan-marshall:tools-script-executor:generate-executor verify
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
python3 .plan/execute-script.py plan-marshall:tools-script-executor:generate-executor drift
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
python3 .plan/execute-script.py plan-marshall:permission-fix:permission-fix ensure-wildcards \
  --settings ~/.claude/settings.json \
  --marketplace-json marketplace/.claude-plugin/marketplace.json \
  --dry-run
```

**Interpret results**:
- `added: []` → All wildcards present ✓
- `added: [...]` → Missing wildcards, offer to add them

If missing wildcards found, ask user:
```
AskUserQuestion:
  question: "Found {N} missing plugin wildcards. Add them?"
  options:
    - label: "Yes"
      description: "Add missing wildcards to global settings"
      value: "yes"
    - label: "No"
      description: "Skip (may cause permission prompts)"
      value: "no"
```

If yes, run without `--dry-run`.

---

## Step 4: Check for Stale Permissions

Detect permissions for bundles that no longer exist:

```bash
python3 .plan/execute-script.py plan-marshall:permission-doctor:permission-doctor detect-redundant --scope both
```

Report any redundant or stale permissions found.

---

## Step 5: Check Project Structure

Verify project structure knowledge base exists:

```bash
python3 .plan/execute-script.py plan-marshall:marshall-steward:determine-mode check-structure
```

**Interpret results**:
- `status: exists` → Project structure configured ✓
- `status: missing` → No project structure (placement context unavailable)

If missing, show info message (not blocking):
```
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
- `overall: healthy` → All CI tools ready ✓
- `overall: degraded` → Provider detected but tool not authenticated
- `overall: unknown` → Could not detect CI provider

If tool not authenticated, show:
```
AskUserQuestion:
  question: "CI tool '{tool}' is not authenticated. Run '{tool} auth login' to authenticate."
  options:
    - label: "Continue"
      description: "Skip CI tool verification"
      value: "continue"
```

---

## Step 7: Summary

Output health check summary:

**Healthy System**:
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
redundant_permissions: 0
project_structure: configured
ci:
  provider: github
  required_tool: gh
  tool_ready: true

overall: HEALTHY
```

**System with Issues**:
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
redundant_permissions: 3
project_structure: missing
ci:
  provider: github
  required_tool: gh
  tool_ready: false

issues:
  - Executor drift detected (regenerate recommended)
  - 2 plugin wildcards missing
  - 3 redundant permissions in project settings
  - Project structure not configured
  - CI tool 'gh' not authenticated

fixes_available: true
```

---

After health check completes, return to Main Menu.
