---
implements: plan-marshall:extension-api/standards/ext-point-execution-context-workflow
---

# Manage Architecture: Enrich Module

Per-module enrichment workflow. Reads a module's discovered data, samples its documentation and source, infers `purpose` / `responsibility` / `key_packages` / `dependencies` / `skill_domains`, and writes the enrichment via the `architecture enrich` script API.

Dispatched under `--phase phase-6-finalize` (no `--role` — manage-architecture-enrich-module tracks `phase-6-finalize.default`) — **the only per-iteration parallel dispatch in the marketplace**. Phase-6-finalize `architecture-refresh` Tier-1 dispatches one execution-context per affected module, all in parallel. This is the documented exception to granularity Heuristic 3 (per-iteration dispatch only when models differ OR iterations parallelise): modules are independent and parallelism saves wall-time, so N parallel envelopes beat one envelope iterating N modules sequentially. Every other per-X loop in the system iterates **in-context inside one envelope** — see [`../../extension-api/standards/dispatch-granularity.md`](../../extension-api/standards/dispatch-granularity.md) § 4 for the full rule.

## Inputs

| Prompt-body field | Required | Description |
|-------------------|:--------:|-------------|
| `plan_id` | Yes | Plan identifier (or sentinel `none` for stand-alone enrichment runs). |
| `WORKTREE` | Yes | Repo-relative working-directory path. |
| `module` | Yes | The module name to enrich (matches `architecture modules` output). |

Skills the caller MUST forward in `skills[]`: `plan-marshall:manage-architecture`.

## Workflow

The per-module enrichment body is the canonical Steps 5–8 documented in [`../../manage-architecture/SKILL.md`](../../manage-architecture/SKILL.md) §§ "Steps 5-8: Per-Module Enrichment", "Step 6: Write Responsibility", "Step 7: Key Packages & Dependencies", "Step 8: Resolve Skill Domains". Execute those four steps for the single `{module}` provided in the prompt body. Do NOT iterate — each dispatch handles one module; the caller fans out across modules in parallel.

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
