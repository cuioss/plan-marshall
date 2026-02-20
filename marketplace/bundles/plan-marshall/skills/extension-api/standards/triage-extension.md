# Triage Extension Contract

Extension hook for declaring a domain-specific triage skill that provides finding decision-making knowledge.

## Purpose

Provides a hook for extensions to declare a triage skill — a reference skill containing domain-specific knowledge for handling findings during verification and finalize phases. This enables:

- Domain-specific suppression syntax (e.g., `@SuppressWarnings` for Java, `// eslint-disable` for JavaScript)
- Severity-to-decision guidelines tailored to each domain
- Knowledge of what findings are acceptable to accept without fixing

---

## Lifecycle Position

The hook is invoked by `marshall-steward` during domain configuration:

```
1. Extension discovery and loading
2. get_skill_domains() → domain metadata
3. ➤ provides_triage() → triage skill reference per domain
4. Stored in marshal.json under skill_domains.{domain}.workflow_skill_extensions.triage
5. Resolved at runtime by workflow skills (execute, finalize)
```

**Timing**: Called during `/marshall-steward` domain configuration (`skill-domains configure`). The returned skill reference is persisted in `marshal.json` and resolved at runtime when findings need triage.

---

## Method Signature

```python
def provides_triage(self) -> str | None:
    """Return triage skill reference if available.

    Returns:
        Skill reference as 'bundle:skill' (e.g., 'pm-dev-java:ext-triage-java')
        or None if no triage capability.

    Purpose:
        Triage skills categorize and prioritize findings during
        the plan-finalize phase.

    Default: None
    """
    return None
```

---

## Required Skill Sections

The referenced triage skill MUST include these sections:

| Section | Purpose | Content |
|---------|---------|---------|
| `## Suppression Syntax` | How to suppress findings | Annotation/comment syntax per finding type |
| `## Severity Guidelines` | When to fix vs suppress vs accept | Decision table by severity |
| `## Acceptable to Accept` | What can be accepted without fixing | Situations where accepting is appropriate |

For detailed section templates and examples, see the [workflow triage extension contract](../../../../pm-workflow/skills/workflow-extension-api/standards/extensions/triage-extension.md).

---

## Storage in marshal.json

The triage skill reference is stored under `workflow_skill_extensions.triage` within the domain configuration:

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

---

## Resolution Command

Runtime resolution of the triage skill for a domain:

```bash
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  resolve-workflow-skill-extension --domain java --type triage
```

**Output**:
```toon
status	success
domain	java
type	triage
extension	pm-dev-java:ext-triage-java
```

If no triage extension exists for a domain, `extension` returns `null`.

---

## Implementation Pattern

```python
from extension_base import ExtensionBase


class Extension(ExtensionBase):
    """Domain extension with triage capability."""

    def provides_triage(self) -> str | None:
        """Return triage skill reference."""
        return 'pm-dev-java:ext-triage-java'
```

The referenced skill (e.g., `pm-dev-java:ext-triage-java`) is a read-only reference skill containing the three required sections.

---

## Existing Implementations

| Bundle | Domain | Triage Skill |
|--------|--------|-------------|
| pm-dev-java | java | `pm-dev-java:ext-triage-java` |
| pm-dev-frontend | javascript | `pm-dev-frontend:ext-triage-js` |
| pm-documents | documentation | `pm-documents:ext-triage-docs` |
| pm-requirements | requirements | `pm-requirements:ext-triage-reqs` |
| pm-plugin-development | plan-marshall-plugin-dev | `pm-plugin-development:ext-triage-plugin` |

Bundles without triage (returns `None`): pm-dev-java-cui (relies on base bundle pm-dev-java).

---

## Design Rationale

### Why Separate Skills?

Triage knowledge lives in dedicated skills rather than inline because:

1. **Separation of concerns** — workflow skills own the process, triage skills own domain knowledge
2. **Reusability** — triage knowledge is loaded by both execute (verification) and finalize phases
3. **Maintainability** — domain experts update triage knowledge independently of workflow logic

### Why Optional?

Not all domains need custom triage:

1. **Additive bundles** (e.g., pm-dev-java-cui) rely on the base bundle's triage
2. **New domains** can start without triage and add it later
3. **Default behavior** — when no triage exists, the workflow uses generic severity mapping

---

## Related Specifications

- [extension-contract.md](extension-contract.md) — Extension API contract
- [triage-extension.md (workflow)](../../../../pm-workflow/skills/workflow-extension-api/standards/extensions/triage-extension.md) — Workflow integration details, required section templates, triage decision flow
- [extension-mechanism.md](../../../../pm-workflow/skills/workflow-extension-api/standards/extensions/extension-mechanism.md) — Extension mechanism overview
