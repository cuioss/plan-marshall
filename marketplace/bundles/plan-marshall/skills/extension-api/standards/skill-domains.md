# Skill Domains Contract

Required method that defines domain identity and profile-based skill organization.

## Purpose

Defines the extension's domain identity and organizes skills into profiles for context-appropriate loading. This is the only **required** (abstract) method in `ExtensionBase`. It enables:

- Domain identity (key, name, description) for marshal.json registration
- Profile-based skill organization for phase-appropriate knowledge loading
- Separation of core patterns from implementation, testing, and quality skills
- Default vs optional skill distinction within each profile

---

## Lifecycle Position

The method is invoked by `marshall-steward` during domain configuration:

```
1. Extension discovery and loading
2. ➤ get_skill_domains() → domain metadata + skill profiles
3. Domain registered in marshal.json under skill_domains.{domain_key}
4. Profiles consumed by phase skills to load domain-specific knowledge
```

**Timing**: Called during `/marshall-steward` domain configuration (`skill-domains configure`). The returned structure defines the domain's identity and skill organization for the entire planning lifecycle.

---

## Method Signature

```python
def get_skill_domains(self) -> dict:
    """Return domain metadata for skill loading.

    Returns:
        Dict with domain identity and profile-based skill organization:
        {
            "domain": {
                "key": str,          # Unique domain identifier
                "name": str,         # Human-readable name
                "description": str   # Domain description
            },
            "profiles": {
                "core": {
                    "defaults": list[str],    # Always-loaded skills
                    "optionals": list[str]    # On-demand skills
                },
                "implementation": {...},
                "testing": {...},      # or "module_testing"
                "quality": {...}
            }
        }

    This method is abstract — all extensions MUST implement it.
    """
```

---

## Return Structure

### Domain Object

| Field | Type | Description |
|-------|------|-------------|
| `domain.key` | str | Unique domain identifier (e.g., `java`, `javascript`, `documentation`) |
| `domain.name` | str | Human-readable name (e.g., `Java Development`) |
| `domain.description` | str | Domain description for display |

### Profiles Map

Each profile contains `defaults` (always loaded) and `optionals` (loaded on demand):

| Profile | Purpose | When Loaded |
|---------|---------|-------------|
| `core` | Foundation patterns and standards | Always — base knowledge for the domain |
| `implementation` | Runtime patterns (CDI, frameworks) | During implementation tasks |
| `module_testing` | Test frameworks and patterns | During testing tasks |
| `quality` | Documentation, code quality standards | During quality and verification tasks |
| `documentation` | Documentation-specific standards (optional) | Domain-specific extra profile |

**Skill Reference Format**: `bundle:skill` strings pointing to registered skills (e.g., `pm-dev-java:java-core`).

### Defaults vs Optionals

- **defaults**: Skills loaded automatically when the profile is activated
- **optionals**: Skills available for on-demand loading when specific knowledge is needed

### Storage in marshal.json

The returned structure is stored in `marshal.json` under `skill_domains.{domain_key}`:

```json
{
  "skill_domains": {
    "java": {
      "bundle": "pm-dev-java",
      "outline_skill": null,
      "workflow_skill_extensions": {
        "triage": "pm-dev-java:ext-triage-java"
      }
    }
  }
}
```

The `bundle` field is a **reverse mapping** added automatically by `skill-domains configure` — it records which bundle provides this domain. Since domain keys (e.g., `java`) differ from bundle names (e.g., `pm-dev-java`), this field is needed to locate the source `extension.py` for runtime operations.

---

## Implementation Pattern

```python
from extension_base import ExtensionBase


class Extension(ExtensionBase):
    """Domain extension with skill domains."""

    def get_skill_domains(self) -> dict:
        """Domain metadata for skill loading."""
        return {
            "domain": {
                "key": "java",
                "name": "Java Development",
                "description": "Java code patterns, JUnit testing, Maven builds"
            },
            "profiles": {
                "core": {
                    "defaults": ["pm-dev-java:java-core"],
                    "optionals": []
                },
                "implementation": {
                    "defaults": [],
                    "optionals": ["pm-dev-java:java-cdi"]
                },
                "module_testing": {
                    "defaults": ["pm-dev-java:junit-core"],
                    "optionals": ["pm-dev-java:junit-integration"]
                },
                "quality": {
                    "defaults": ["pm-dev-java:javadoc"],
                    "optionals": []
                }
            }
        }
```

---

## Existing Implementations

| Bundle | Domain Key | Core Skills | Notable Profiles |
|--------|-----------|-------------|------------------|
| pm-dev-java | `java` | java-core | implementation, module_testing, quality |
| pm-dev-java-cui | `java-cui` | cui-logging, cui-testing | Additive to pm-dev-java |
| pm-dev-frontend | `javascript` | cui-javascript | implementation, module_testing, quality |
| pm-documents | `documentation` | ref-documentation | Extra `documentation` profile |
| pm-requirements | `requirements` | requirements-authoring | planning, traceability |
| pm-plugin-development | `plan-marshall-plugin-dev` | plugin-architecture | plugin-script-architecture |
| pm-dev-python | `python` | python-core | implementation, module_testing, quality |

---

## Validation

Extensions are validated by `plugin-doctor extension`:

```bash
python3 .plan/execute-script.py pm-plugin-development:plugin-doctor:validate extension \
    --extension path/to/extension.py
```

Validation checks:
- `get_skill_domains()` returns valid structure with `domain.key`, `domain.name`, `profiles`
- Required profiles exist (`core`, `implementation`, `module_testing` or `testing`, `quality`)
- Each profile has `defaults` and `optionals` lists
- Skill references (`bundle:skill`) point to existing registered skills

---

## Design Rationale

### Why Profile-Based?

Profiles organize skills by usage context rather than flat lists because:

1. **Context-appropriate loading** — implementation tasks don't need testing standards
2. **Performance** — only load skills needed for the current task profile
3. **Clarity** — clear purpose for each skill in the domain

### Why Required?

This is the only abstract method because every domain must:

1. **Declare identity** — the domain key is used throughout marshal.json
2. **Provide skills** — skills are the primary value a domain extension contributes

---

## Related Specifications

- [extension-contract.md](extension-contract.md) — Extension API contract
- [architecture-overview.md](architecture-overview.md) — System flow and data dependencies
