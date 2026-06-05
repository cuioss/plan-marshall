# Extension Point: Retrospective Aspects

> **Type**: Workflow Skill Extension | **Hook Method**: `provides_retrospective_aspects()` | **Implementations**: 1 | **Status**: Active

## Overview

Retrospective-aspect extensions declare domain-specific analysis aspects that `plan-marshall:plan-retrospective` merges into its aspect dispatch (Step 3) when the plan being audited belongs to the contributing domain. The generic retrospective ships a fixed set of domain-invariant aspects (artifact consistency, log analysis, invariant outcomes, plan efficiency, request-result alignment, and the generic CI-leak surfaces A+B of `direct-gh-glab-usage`). A domain extension contributes ADDITIONAL deterministic, script-backed aspects that are only meaningful for plans authored against that domain — e.g. a marketplace-CI-wrapper-tangle scan that only makes sense when the plan touched plan-marshall's own CI abstraction sources.

Aspects are gated by plan domain at compose time: the retrospective resolves the plan's domain, queries every extension's `provides_retrospective_aspects()`, and merges only the aspects whose `domain` matches the plan's domain into the aspect table. Aspects from non-matching domains are skipped. This keeps the generic retrospective domain-invariant while letting domain bundles attach their own deterministic checks.

## Implementor Requirements

### Interface Contract

Each retrospective aspect is a **deterministic, script-backed fragment producer** — the same shape as the generic script-backed aspects (artifact-consistency, log-analysis, direct-gh-glab-usage). The aspect script:

- Accepts `run --mode {live,archived}` plus the standard resolution flags (`--plan-id` for live mode, `--archived-plan-path` for archived mode).
- Emits a TOON fragment to stdout following the aspect's documented schema (`status`, `aspect`, `counts`, `findings[]`).
- Always exits `0` — findings are carried in the TOON output, never in the exit code (matching the convention in `analyze-logs.py`, `check-artifact-consistency.py`, and `direct-gh-glab-usage.py`).

The retrospective orchestrator pipes the script's stdout to a fragment file, then registers it via `collect-fragments add`, exactly as it does for the built-in script-backed aspects.

### Implementation Pattern

```python
class Extension(ExtensionBase):
    def provides_retrospective_aspects(self) -> list[dict]:
        return [
            {
                'aspect': 'wrapper-tangle',
                'domain': 'plan-marshall-plugin-dev',
                'script': 'pm-plugin-development:plan-marshall-plugin:wrapper-tangle-scan',
                'reference': 'pm-plugin-development:plan-marshall-plugin/references/wrapper-tangle.md',
                'description': 'Scan plan-marshall CI-wrapper sources for tangled gh/glab + local-git mutations',
                'order': 500,
            },
        ]
```

> **Note**: `order` is NOT enforced at runtime. It is the relative sort key the retrospective uses when merging domain aspects into the aspect table; aspects with identical order keep discovery order. The retrospective iterates the merged table as written and does not re-sort or validate the ordering beyond the initial merge.

## Runtime Invocation Contract

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `mode` | str | Yes | `live` or `archived` — resolution mode forwarded by the retrospective |
| `plan_id` | str | Conditional | Live plan identifier (live mode) |
| `archived_plan_path` | str | Conditional | Absolute path to an archived plan directory (archived mode) |

### Pre-Conditions

- The plan being audited belongs to the aspect's declared `domain`.
- The aspect script is registered with the executor (resolvable via its `script` notation).

### Post-Conditions

- A TOON fragment is produced on stdout and registered into the retrospective's fragment bundle.
- Findings are surfaced verbatim in the compiled `quality-verification-report.md`.

## Hook API

### Python API

```python
def provides_retrospective_aspects(self) -> list[dict]:
    """Return domain-specific retrospective aspects.

    Each aspect dict contains:
        - aspect: str — Short aspect name used as the fragment key
          (e.g., 'wrapper-tangle'). Becomes the --aspect value passed to
          collect-fragments add.
        - domain: str — Domain key gating the aspect. The retrospective
          merges the aspect only when the audited plan's domain matches
          this value (e.g., 'plan-marshall-plugin-dev').
        - script: str — Fully-qualified executor notation for the aspect's
          deterministic fragment producer
          (e.g., 'pm-plugin-development:plan-marshall-plugin:wrapper-tangle-scan').
        - reference: str — Skill-relative reference doc path documenting the
          aspect's detection contract and finding schema.
        - description: str — Human-readable description for report context.
        - order: int — Relative sort key used when merging domain aspects
          into the aspect table. Not enforced at runtime.

    Default: []
    """
```

### Return Structure

| Field | Type | Description |
|-------|------|-------------|
| `aspect` | str | Short aspect name; used as the fragment key and the `--aspect` value for `collect-fragments add` |
| `domain` | str | Domain key gating the aspect — merged only when the audited plan's domain matches |
| `script` | str | Fully-qualified executor notation for the aspect's deterministic fragment producer |
| `reference` | str | Skill-relative reference doc path documenting the aspect's contract |
| `description` | str | Human-readable description for report context |
| `order` | int | Relative sort key used at merge time; not enforced at runtime |

## Resolution

The retrospective resolves domain-contributed aspects via the extension-discovery CLI. The aspects are returned for ALL extensions; the retrospective filters by the audited plan's domain at merge time.

```bash
# List all domain-contributed retrospective aspects (all extensions)
python3 .plan/execute-script.py plan-marshall:extension-api:extension_discovery \
  list-retrospective-aspects
```

The TOON output carries one row per declared aspect with its `aspect`, `domain`, `script`, `reference`, `description`, and `order` fields. The retrospective merges only rows whose `domain` matches the audited plan's domain (resolved from `status.metadata` / the plan's task domains).

## Current Implementations

| Bundle | Domain | Aspect | Script | Detects |
|--------|--------|--------|--------|---------|
| `pm-plugin-development` | `plan-marshall-plugin-dev` | `wrapper-tangle` | `pm-plugin-development:plan-marshall-plugin:wrapper-tangle-scan` | CI-wrapper source files (`tools-integration-ci`, `workflow-integration-{github,gitlab}`) whose subprocess/`run_gh`/`run_glab` args tangle a `gh`/`glab` CLI invocation with a local-git mutation (`checkout`, `branch -d/-D`, `--delete-branch`, `--remove-source-branch`) |

The `wrapper-tangle` aspect is the former **Surface C** of the generic `plan-marshall:plan-retrospective:direct-gh-glab-usage` aspect. Surfaces A (plan logs) and B (plan diff) remain in the generic, domain-invariant `direct-gh-glab-usage` aspect; Surface C moved here because scanning plan-marshall's own CI-abstraction sources is only meaningful for plans authored against the `plan-marshall-plugin-dev` domain.
