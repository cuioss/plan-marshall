# Verify Steps Contract

Extension hook for declaring domain-specific verification agents that run after implementation tasks complete.

## Purpose

Provides a hook for extensions to declare verification steps — domain-specific agents that validate implementation quality beyond build commands. This enables:

- Domain-specific verification (e.g., standards compliance, test coverage thresholds)
- Agent-based verification with structured assessment
- User-configurable enable/disable per step
- Separation of verification logic from implementation logic

---

## Lifecycle Position

The hook is invoked by `marshall-steward` during domain configuration:

```
1. Extension discovery and loading
2. get_skill_domains() → domain metadata
3. ➤ provides_verify_steps() → verification steps per domain
4. Steps stored in marshal.json under verification_domain_steps
5. phase-4-plan reads config → creates holistic verification TASKs
6. phase-5-execute runs verification agents
```

**Timing**: Called during `/marshall-steward` domain configuration (`skill-domains configure`). Steps are persisted in `marshal.json` and consumed at plan-time by phase-4-plan.

---

## Method Signature

```python
def provides_verify_steps(self) -> list[dict]:
    """Return domain-specific verification steps.

    Each step declares a verification agent that can be enabled during
    project configuration via /marshall-steward. Steps are persisted in
    marshal.json under plan.phase-5-execute.verification_domain_steps.{domain_key}.

    Returns:
        List of step dicts, each containing:
        - name: Step identifier (e.g., 'technical_impl')
        - agent: Fully-qualified agent reference (e.g., 'pm-dev-java:java-verify-agent')
        - description: Human-readable description for wizard presentation

    Default implementation returns empty list (no domain-specific verify steps).
    """
    return []
```

---

## Return Structure

Each dict in the returned list must contain:

| Field | Type | Description |
|-------|------|-------------|
| `name` | str | Step identifier — used as key suffix in marshal.json |
| `agent` | str | Fully-qualified agent reference (`bundle:agent`) |
| `description` | str | Human-readable description for `/marshall-steward` wizard |

---

## Storage in marshal.json

Steps are stored under `plan.phase-5-execute.verification_domain_steps.{domain_key}` using numbered keys:

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
        },
        "requirements": {
          "1_formal_spec": "pm-requirements:spec-verify"
        }
      }
    }
  }
}
```

**Key format**: `{number}_{step_name}` — the number determines execution order, the name comes from the step's `name` field.

**Value format**:
- String value → agent reference to invoke
- `false` → step is disabled (skipped)

---

## Enable/Disable Commands

Users can toggle individual steps after initial configuration:

```bash
# Disable a step
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-5-execute set-domain-step --domain java --step 1_technical_impl --enabled false

# Change the agent for a step
python3 .plan/execute-script.py plan-marshall:manage-plan-marshall-config:plan-marshall-config \
  plan phase-5-execute set-domain-step-agent --domain java --step 1_technical_impl --agent pm-dev-java:java-verify-agent
```

---

## Runtime Consumption

Phase-4-plan reads the stored configuration and creates holistic verification TASKs:

1. **Read config**: `plan phase-5-execute get --trace-plan-id {plan_id}`
2. **For each enabled domain step**: Create a verification task
3. **Task properties**:
   - `profile: verification`
   - `deliverable: 0` (not tied to a specific deliverable)
   - `origin: holistic`
   - `depends_on: [ALL non-holistic tasks]` (runs after all implementation)

The created tasks invoke the declared agent reference during phase-5-execute.

---

## Implementation Pattern

```python
from extension_base import ExtensionBase


class Extension(ExtensionBase):
    """Domain extension with verification steps."""

    def provides_verify_steps(self) -> list[dict]:
        """Return domain-specific verification steps."""
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

---

## Existing Implementations

| Bundle | Domain | Steps | Details |
|--------|--------|-------|---------|
| pm-dev-java | java | 2 | `technical_impl` (java-verify-agent), `technical_test` (java-coverage-agent) |
| pm-documents | documentation | 1 | `doc_sync` (doc-verify) |
| pm-requirements | requirements | 1 | `formal_spec` (spec-verify) |

Bundles without verification steps (returns `[]`): pm-dev-frontend, pm-dev-java-cui, pm-plugin-development.

---

## Design Rationale

### Why Extension-Declared?

Verification steps are declared by extensions rather than hardcoded because:

1. **Domain ownership** — each domain knows what to verify
2. **Extensibility** — new domains add steps without modifying core code
3. **Discoverability** — `/marshall-steward` shows all available steps during configuration

### Why Agent References?

Steps reference agents rather than embedding verification logic because:

1. **Separation of concerns** — agents encapsulate verification logic
2. **Reusability** — agents can be invoked independently
3. **Configurability** — users can swap agents per step

---

## Related Specifications

- [extension-contract.md](extension-contract.md) — Extension API contract
- [data-model.md](../../manage-plan-marshall-config/standards/data-model.md) — marshal.json structure for `verification_domain_steps`
- [phase-4-plan SKILL.md](../../../../pm-workflow/skills/phase-4-plan/SKILL.md) — Holistic verification task creation
