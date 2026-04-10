# Provider Setup Reference

Extracted provider-related wizard logic covering discovery, activation, CI detection, and credential setup. Referenced by `wizard-flow.md` Steps 5b, 14, and 15.

## Provider Discovery and Activation (Step 5b)

Scan executor SCRIPTS entries for `*_provider.py` files, group discovered providers by category, and persist only the activated subset to `marshal.json`. This must run after the executor is generated (Step 4) and marshal.json is initialized (Step 5), but before CI detection (Step 14) or credential setup (Step 15) which read from the providers list.

### Step 5b-1: Discover available providers

Discovery-only mode — no persistence:

```bash
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials discover-and-persist
```

### Step 5b-2: Group discovered providers by category

Partition the discovered providers into three categories based on each provider's `category` field. Provider `skill_name` values use bundle-prefixed format (e.g., `plan-marshall:workflow-integration-github`):

| Category | Providers | Selection behavior |
|----------|-----------|-------------------|
| `version-control` | git | Auto-selected (exactly 1 required) |
| `ci` | github, gitlab | Single-select with skip option |
| `other` | sonar, etc. | Multi-select |

### Step 5b-3: Auto-select version-control providers

The `version-control` category requires exactly one provider and is always active. Inform the user without prompting:

> "Git provider is always active (version-control category requires exactly 1)."

No `AskUserQuestion` for this category.

### Step 5b-4: Present CI providers as single-select

Present CI-category providers with a "Skip" option for projects that do not use CI:

```
AskUserQuestion:
  questions:
    - question: "Which CI provider should be activated?"
      header: "CI Provider"
      options:
        # Dynamic from ci-category providers:
        - label: "{display_name}"
          description: "{skill_name} — {description}"
        - label: "Skip"
          description: "No CI provider for this project"
      multiSelect: false
```

If user selects "Skip", no CI provider is activated.

### Step 5b-5: Present other providers as multiSelect

Only present this step if the `other` category contains at least one provider:

```
AskUserQuestion:
  questions:
    - question: "Which additional providers should be activated?"
      header: "Other"
      options:
        # Dynamic from other-category providers:
        - label: "{display_name}"
          description: "{skill_name} — {description}"
      multiSelect: true
```

### Step 5b-6: Persist activated providers

Build the combined provider list from: auto-selected git + user-selected CI (if any) + user-selected others. Call discover-and-persist with the combined list:

```bash
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials discover-and-persist \
  --providers {comma-separated bundle-prefixed skill_names from combined selection}
```

Example with bundle-prefixed names:
```bash
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials discover-and-persist \
  --providers plan-marshall:workflow-integration-git,plan-marshall:workflow-integration-github
```

**Output (TOON)**:
```toon
status: success
action: discover-and-persist
discovered: 4
activated: 2
providers:
  - plan-marshall:workflow-integration-github
  - plan-marshall:workflow-integration-git
```

| Field | Description |
|-------|-------------|
| `discovered` | Number of provider declarations found |
| `activated` | Number of providers the user selected (including auto-selected) |
| `providers` | List of bundle-prefixed `skill_name` values for activated providers |

**Why here**: Steps 14 and 15 call `list-providers` and `load_declared_providers()`, both of which read from `marshal.json`. Without this step, the providers list would be empty and CI detection / credential setup would fail.

---

## CI Provider Detection (Step 14)

Detect CI provider and verify system-authenticated tools using the unified provider model.

### Step 14a: Query system providers

Read provider declarations from marshal.json (populated by Step 5b). Provider `skill_name` values use bundle-prefixed format:

```bash
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials list-providers
```

Parse the `providers` array. Filter entries where `skill_name` is `plan-marshall:workflow-integration-github` or `plan-marshall:workflow-integration-gitlab`. These are the CI provider declarations. Only activated providers (persisted in Step 5b) appear in this list.

### Step 14b: Detect CI provider from repository

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci_health detect
```

This detects the CI provider (github/gitlab) from the git remote URL and CI config files.

### Step 14c: Verify the detected provider's CLI tool

Match the detected provider to its system provider declaration from Step 14a. Run the provider's `verify_command` to check authentication:

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci_health verify --tool {required_tool}
```

Where `{required_tool}` is `gh` for GitHub or `glab` for GitLab (derived from the system provider's `verify_command`).

Display detection result to user. If tool not authenticated, warn:
- "GitHub detected but 'gh' not authenticated. Run 'gh auth login' for CI operations."
- "GitLab detected but 'glab' not authenticated. Run 'glab auth login' for CI operations."

### Step 14d: Persist CI configuration

```bash
python3 .plan/execute-script.py plan-marshall:tools-integration-ci:ci_health persist
```

**Output**: CI configuration persisted to marshal.json with detected provider and authenticated tools.

---

## Credential Setup (Step 15, Optional)

### Step 15a: Read activated providers

Read activated providers from marshal.json (only providers selected by the user in Step 5b are present; filter out CI providers like `plan-marshall:workflow-integration-github` and `plan-marshall:workflow-integration-gitlab` since those are handled in Step 14):

```bash
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials list-providers
```

Parse the `providers` array from output. If `count == 0`, skip to Step 16.

### Step 15b: Ask user

```
AskUserQuestion:
  questions:
    - question: "Configure credentials for external tools?"
      header: "Credentials"
      options:
        - label: "Skip (Recommended)"
          description: "Configure credentials later via /marshall-steward menu"
        - label: "Configure now"
          description: "Set up credentials for SonarCloud or other external tools"
      multiSelect: false
```

If user selects "Skip" -> Continue to Step 16.

### Step 15c: Collect credential values

If user selects "Configure now", collect non-secret values step by step.

**IMPORTANT**: Each AskUserQuestion below MUST be followed by the next step. Do NOT abort or skip if a user answer seems unexpected. Always proceed to Step 15e and run the configure command.

1. Credential scope:

```
AskUserQuestion:
  questions:
    - question: "Credential scope?"
      header: "Scope"
      options:
        - label: "Global (Recommended)"
          description: "Shared across all projects using plan-marshall"
        - label: "Project"
          description: "Specific to this project only"
      multiSelect: false
```

Map selection to `--scope global` or `--scope project` for Step 15e.

2. Provider selection (only if multiple providers, otherwise use the single one):

```
AskUserQuestion:
  questions:
    - question: "Which credential provider?"
      header: "Provider"
      options:
        # Dynamic from Step 15a provider list
        - label: "{provider_display_name}"
          description: "{provider_description}"
      multiSelect: false
```

3. URL and auth type (use provider defaults as recommended options):

```
AskUserQuestion:
  questions:
    - question: "Base URL for {display_name}?"
      header: "URL"
      options:
        - label: "{default_url} (Recommended)"
          description: "Default URL for this provider"
      multiSelect: false
    - question: "Authentication type?"
      header: "Auth"
      options:
        - label: "{provider_auth_type} (Recommended)"
          description: "Default auth type for this provider"
        - label: "none"
          description: "No authentication needed"
      multiSelect: false
```

### Step 15d: Auto-detect extra fields

Check if the selected provider has `extra_fields` in the `list-providers` output. If yes, auto-detect values and confirm with user.

For `workflow-integration-sonar` (has `extra_fields: organization, project_key`):

1. Read `repo_url` from the CI provider entry in marshal.json (persisted during Step 14d):
```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config ci get
```

2. Extract organization from `repo_url` (e.g., `https://github.com/cuioss/plan-marshall` -> org=`cuioss`, repo=`plan-marshall`)
3. Derive project key as `{org}_{repo}` (e.g., `cuioss_plan-marshall`)
4. Confirm with user:

```
AskUserQuestion:
  questions:
    - question: "SonarCloud organization?"
      header: "Organization"
      options:
        - label: "{detected_org} (Recommended)"
          description: "Detected from repository URL"
      multiSelect: false
    - question: "SonarCloud project key?"
      header: "Project"
      options:
        - label: "{detected_project_key} (Recommended)"
          description: "Detected as org_repo from repository URL"
      multiSelect: false
```

User can accept recommended values or type custom values via "Other".

### Step 15e: Run configure

**ALWAYS execute this step** -- creates credential file with placeholder secrets.

Build the command from collected values (no secret args -- secrets go into the file as placeholders):

```bash
# With extra fields:
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials configure \
  --skill {skill} --url {url} --auth-type {auth_type} --scope {scope} \
  --extra organization={org} project_key={project_key}

# Without extra fields:
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials configure \
  --skill {skill} --url {url} --auth-type {auth_type} --scope {scope}
```

**CRITICAL**:
- Include `--scope` from Step 15c (global or project).
- Omit `--extra` if the provider has no `extra_fields` in the `list-providers` output.
- The keys used in `--extra` (e.g., `organization`, `project_key`) must match the `key` field from the provider's `extra_fields` array returned by `list-providers`.

### Step 15e2: Handle editing

If configure returns `needs_editing: true`, tell user to edit the credential file:

1. Tell user: "Open `{path}` and replace the placeholder with your actual token/password."
2. Wait for user to confirm they've edited the file.
3. Run check to verify no placeholders remain:

```bash
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials check --skill {skill} --scope {scope}
```

If check returns `incomplete`, tell user which placeholders remain and ask them to edit again.

If configure returns `exists_complete`, ask user whether to reuse the existing credential or reconfigure (remove + configure).

### Step 15f: Verify connectivity (optional)

```bash
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials verify --skill {skill}
```

### Step 15g: Add deny rules

```bash
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials ensure-denied --target project
```

### Step 15h: Sonar integration

If the configured skill was `workflow-integration-sonar`, add sonar-roundtrip to finalize steps:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-6-finalize add-step --step default:sonar-roundtrip --after default:automated-review
```

---

## Provider Reconfiguration (Menu Mode)

For reconfiguring activated providers after initial setup, use the marshall-steward menu. The menu should support:

- **Add provider**: Run discovery (Step 5b-1), show only non-activated providers, activate selected ones
- **Remove provider**: List activated providers, remove selected from marshal.json
- **Reset all providers**: Clear providers list in marshal.json, re-run full Step 5b flow
