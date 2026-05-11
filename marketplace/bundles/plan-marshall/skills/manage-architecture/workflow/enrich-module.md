---
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# Manage Architecture: Enrich Module

Per-module enrichment workflow. Reads a module's discovered data, samples its documentation and source, infers `purpose` / `responsibility` / `key_packages` / `dependencies` / `skill_domains`, and writes the enrichment via the `architecture enrich` script API.

Dispatched under the `cross.manage-architecture-enrich-module` role key — the only per-iteration **parallel** dispatch in the post-refactor contract. Phase-6-finalize `architecture-refresh` Tier-1 dispatches one execution-context per affected module, all in parallel.

## Inputs

| Prompt-body field | Required | Description |
|-------------------|:--------:|-------------|
| `plan_id` | Yes | Plan identifier (or sentinel `none` for stand-alone enrichment runs). |
| `WORKTREE` | Yes | Repo-relative working-directory path. |
| `module` | Yes | The module name to enrich (matches `architecture modules` output). |

Skills the caller MUST forward in `skills[]`: `plan-marshall:manage-architecture`.

## Workflow

The per-module enrichment body is the canonical Steps 5–8 documented in [`../SKILL.md`](../SKILL.md) §§ "Steps 5-8: Per-Module Enrichment", "Step 6: Write Responsibility", "Step 7: Key Packages & Dependencies", "Step 8: Resolve Skill Domains". Execute those four steps for the single `{module}` provided in the prompt body. Do NOT iterate — each dispatch handles one module; the caller fans out across modules in parallel.

The intra-module step ordering MUST be preserved:
- Step 5 (load raw data) feeds Steps 6–7.
- Step 8 (resolve skill domains) runs last and depends on Steps 6–7.

## Output

```toon
status: success | error
display_detail: "<≤80 char ASCII summary>"
module: {module}
purpose: {library|extension|deployment|runtime|parent|bom|integration-tests|benchmark}
responsibility_written: true | false
key_packages_count: {N}
dependencies_count: {N}
skill_domains_count: {N}
```

`display_detail` shape on success: `"enriched {module}: purpose={purpose}, keys={key_packages_count}"`.
