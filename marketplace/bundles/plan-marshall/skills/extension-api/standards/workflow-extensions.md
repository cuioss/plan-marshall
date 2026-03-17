# Workflow Extension Contracts

The extension API defines four optional hooks that domain bundles can implement to customize workflow behavior. Each hook is invoked by `marshall-steward` during domain configuration and persisted in `marshal.json` for runtime resolution. All hooks have safe defaults (None or empty) so bundles only implement what they need.

## Config Callback (`config_defaults`)

Sets project-specific configuration defaults in `marshal.json` before other components access them. Enables domain-specific defaults, project-aware configuration, and user-overridable settings.

**Lifecycle**: Called after extensions are loaded but before any workflow logic accesses configuration.

```
Extension discovery → load → ➤ config_defaults() → plugin access / workflow execution
```

### Method Signature

```python
def config_defaults(self, project_root: str) -> None:
    """Configure project-specific defaults in marshal.json.

    Contract:
        - MUST only write values if they don't already exist (write-once)
        - MUST NOT override user-defined configuration
        - SHOULD use direct import from _config_core module
    """
    pass
```

### Write-Once Semantics

The critical contract: **only write if the key doesn't exist**. The `extension-defaults set-default` command implements this automatically.

### Implementation Pattern

**Recommended** — direct import:

```python
from _config_core import ext_defaults_set_default

class Extension(ExtensionBase):
    def config_defaults(self, project_root: str) -> None:
        ext_defaults_set_default("build.maven.profiles.skip", "itest,native", project_root)
        ext_defaults_set_default("build.maven.profiles.map.canonical", "pre-commit:quality-gate", project_root)
```

**Alternative** — CLI via subprocess:

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config ext-defaults set-default \
  --key "my_bundle.my_setting" --value "default_value"
```

### Available Operations

| Operation | Description |
|-----------|-------------|
| `ext-defaults set-default` | Set value only if key doesn't exist (write-once) |
| `ext-defaults get/set/list/remove` | Generic key-value operations in `extension_defaults` |

---

## Triage Extension (`provides_triage`)

Declares a domain-specific triage skill containing finding decision-making knowledge — suppression syntax, severity guidelines, and acceptable-to-accept criteria.

**Lifecycle**: Called during `skill-domains configure`. Stored in `marshal.json` and resolved at runtime when findings need triage.

```
Extension discovery → get_skill_domains() → ➤ provides_triage() → stored in marshal.json → resolved by execute/finalize phases
```

### Method Signature

```python
def provides_triage(self) -> str | None:
    """Return triage skill reference as 'bundle:skill', or None."""
    return None
```

### Required Skill Sections

The referenced triage skill MUST include:

| Section | Purpose | Content |
|---------|---------|---------|
| `## Suppression Syntax` | How to suppress findings | Annotation/comment syntax per finding type |
| `## Severity Guidelines` | When to fix vs suppress vs accept | Decision table by severity |
| `## Acceptable to Accept` | What can be accepted without fixing | Situations where accepting is appropriate |

### Triage Decision Flow

```
1. Run verification (build, test, lint, Sonar)
2. Collect findings
3. For each finding:
   a. Determine domain from file path/extension
   b. resolve-workflow-skill-extension --domain {domain} --type triage
   c. If extension exists: load skill, apply severity/suppression rules
   d. If no extension: use default severity mapping
   e. Decide: fix | suppress | accept
4. Apply fixes/suppressions → re-run verification if changes made
```

### Storage in marshal.json

```json
{
  "skill_domains": {
    "java": {
      "bundle": "pm-dev-java",
      "workflow_skill_extensions": {
        "triage": "pm-dev-java:ext-triage-java"
      }
    }
  }
}
```

### Resolution Command

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-workflow-skill-extension --domain java --type triage
```

### Implementation Pattern

```python
class Extension(ExtensionBase):
    def provides_triage(self) -> str | None:
        return 'pm-dev-java:ext-triage-java'
```

### Existing Implementations

| Bundle | Domain | Triage Skill |
|--------|--------|-------------|
| pm-dev-java | java | `pm-dev-java:ext-triage-java` |
| pm-dev-frontend | javascript | `pm-dev-frontend:ext-triage-js` |
| pm-documents | documentation | `pm-documents:ext-triage-docs` |
| pm-requirements | requirements | `pm-requirements:ext-triage-reqs` |
| pm-plugin-development | plan-marshall-plugin-dev | `pm-plugin-development:ext-triage-plugin` |

Bundles without triage (returns `None`): pm-dev-java-cui (relies on base bundle).

---

## Outline Extension (`provides_outline_skill`)

Declares a domain-specific outline skill with change-type routing for solution outline creation. The skill provides `standards/change-{type}.md` files with domain-specific discovery, analysis, and deliverable logic.

**Lifecycle**: Called during `skill-domains configure`. Stored in `marshal.json` and resolved at runtime by phase-3-outline.

```
Extension discovery → get_skill_domains() → ➤ provides_outline_skill() → stored in marshal.json → resolved by workflow-outline-change-type
```

### Method Signature

```python
def provides_outline_skill(self) -> str | None:
    """Return domain-specific outline skill reference as 'bundle:skill', or None.

    Fallback: If None, generic plan-marshall:workflow-outline-change-type
    standards are used.
    """
    return None
```

### Skill Structure Convention

```
{bundle}/skills/{skill}/
├── SKILL.md                       # Shared workflow steps
└── standards/
    ├── change-feature.md          # Create new components
    ├── change-enhancement.md      # Improve existing components
    ├── change-bug_fix.md          # Fix component bugs
    └── change-tech_debt.md        # Refactor/cleanup
```

| Change Type | Description |
|-------------|-------------|
| `feature` | New functionality or component |
| `enhancement` | Improve existing functionality |
| `bug_fix` | Fix a defect or issue |
| `tech_debt` | Refactoring, cleanup, removal |
| `analysis` | Investigate, research, understand |
| `verification` | Validate, check, confirm |

Not all change types need coverage — unsupported types fall back to `plan-marshall:workflow-outline-change-type/standards/change-{type}.md`.

### Storage in marshal.json

The outline skill reference is stored at the domain level (not inside `workflow_skill_extensions`):

```json
{
  "skill_domains": {
    "plan-marshall-plugin-dev": {
      "bundle": "pm-plugin-development",
      "outline_skill": "pm-plugin-development:ext-outline-workflow",
      "workflow_skill_extensions": {
        "triage": "pm-plugin-development:ext-triage-plugin"
      }
    }
  }
}
```

### Resolution Command

```bash
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  resolve-outline-skill --domain plan-marshall-plugin-dev
```

Returns `source: domain_specific` when a custom skill exists, or `source: generic_fallback` when using defaults.

### Implementation Pattern

```python
class Extension(ExtensionBase):
    def provides_outline_skill(self) -> str | None:
        return 'pm-plugin-development:ext-outline-workflow'
```

### Existing Implementations

| Bundle | Domain | Outline Skill |
|--------|--------|--------------|
| pm-plugin-development | plan-marshall-plugin-dev | `pm-plugin-development:ext-outline-workflow` |

All other domains return `None` and use the generic `plan-marshall:workflow-outline-change-type` standards.

---

## Verify Steps (`provides_verify_steps`)

Declares domain-specific verification agents that run after implementation tasks complete. Steps are user-configurable (enable/disable per step).

**Lifecycle**: Called during `skill-domains configure`. Steps stored in `marshal.json` and consumed by phase-4-plan to create holistic verification tasks.

```
Extension discovery → get_skill_domains() → ➤ provides_verify_steps() → stored in marshal.json → phase-4-plan creates tasks → phase-5-execute runs agents
```

### Method Signature

```python
def provides_verify_steps(self) -> list[dict]:
    """Return domain-specific verification steps.

    Each step dict contains:
        - name: Step identifier (e.g., 'technical_impl')
        - agent: Fully-qualified agent reference ('bundle:agent')
        - description: Human-readable description for wizard presentation
    """
    return []
```

### Return Structure

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Step identifier — used as key suffix in marshal.json |
| `agent` | str | Fully-qualified agent reference (`bundle:agent`) |
| `description` | str | Human-readable description for `/marshall-steward` wizard |

### Storage in marshal.json

Stored under `plan.phase-5-execute.verification_domain_steps.{domain_key}` with numbered keys:

```json
{
  "plan": {
    "phase-5-execute": {
      "verification_domain_steps": {
        "java": {
          "1_technical_impl": "pm-dev-java:java-verify-agent",
          "2_technical_test": "pm-dev-java:java-coverage-agent"
        },
        "documentation": {
          "1_doc_sync": "pm-documents:doc-verify"
        }
      }
    }
  }
}
```

Key format: `{number}_{step_name}`. Value: agent reference string, or `false` to disable.

### Enable/Disable Commands

```bash
# Disable a step
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set-domain-step --domain java --step 1_technical_impl --enabled false

# Change the agent for a step
python3 .plan/execute-script.py plan-marshall:manage-config:manage-config \
  plan phase-5-execute set-domain-step-agent --domain java --step 1_technical_impl --agent pm-dev-java:java-verify-agent
```

### Runtime Consumption

Phase-4-plan reads the stored configuration and creates holistic verification tasks:

1. Read config: `plan phase-5-execute get --trace-plan-id {plan_id}`
2. For each enabled domain step: create a verification task with `profile: verification`, `deliverable: 0`, `origin: holistic`, `depends_on: [ALL non-holistic tasks]`
3. Tasks invoke the declared agent during phase-5-execute

### Implementation Pattern

```python
class Extension(ExtensionBase):
    def provides_verify_steps(self) -> list[dict]:
        return [
            {
                'name': 'technical_impl',
                'agent': 'pm-dev-java:java-verify-agent',
                'description': 'Verify implementation standards compliance',
            },
            {
                'name': 'technical_test',
                'agent': 'pm-dev-java:java-coverage-agent',
                'description': 'Verify test coverage meets thresholds',
            },
        ]
```

### Existing Implementations

| Bundle | Domain | Steps | Details |
|--------|--------|-------|---------|
| pm-dev-java | java | 2 | `technical_impl` (java-verify-agent), `technical_test` (java-coverage-agent) |
| pm-documents | documentation | 1 | `doc_sync` (doc-verify) |
| pm-requirements | requirements | 1 | `formal_spec` (spec-verify) |

Bundles without verification steps (returns `[]`): pm-dev-frontend, pm-dev-java-cui, pm-plugin-development.

---

## Design Rationale

All four hooks follow the same extension model:

1. **Domain ownership** — each domain declares its own capabilities rather than core code hardcoding domain-specific behavior
2. **Safe defaults** — all hooks return None or empty, so bundles only implement what they need
3. **Discoverability** — `/marshall-steward` exposes all available hooks during configuration
4. **Separation of concerns** — workflow skills own the process, extension skills own domain knowledge
5. **User override** — configuration is persisted in `marshal.json` where users can inspect and modify it

## Related Specifications

- [extension-contract.md](extension-contract.md) — Extension API contract (base class, discovery, validation rules)
