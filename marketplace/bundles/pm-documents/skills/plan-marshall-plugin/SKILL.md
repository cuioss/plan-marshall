---
name: plan-marshall-plugin
description: Documentation domain manifest for plan-marshall workflow integration
implements: plan-marshall:extension-api/standards/ext-point-domain-bundle
user-invocable: false
mode: manifest
---

# Plan Marshall Plugin - Documentation Domain

Domain extension providing documentation skill registration to plan-marshall workflows.

## Enforcement

**Execution mode**: Extension manifest; modify only via Extension API contract.

**Prohibited actions:**
- Do not modify extension.py without updating this manifest documentation
- Do not bypass ExtensionBase inheritance for domain registration
- Do not hardcode skill paths; use bundle notation

**Constraints:**
- Extension must implement `get_skill_domains()` from `ExtensionBase`
- Domain identity must match the bundle name convention (documentation)
- Profile-based skill organization must align with plugin.json registration

## Purpose

- Domain identity and workflow extensions (triage)
- Profile-based skill organization for documentation projects
- Module discovery over the doc tree, and ownership of the documentation corpus
  across the code-intelligence substrate (path attribution and edge derivation)

## Extension API

Configuration in `extension.py` implements the Extension API contract across three
axes (see `plan-marshall:extension-api`). The Axis-C and Axis-D faces are opted
into by multiple inheritance:

| Axis | Function | Purpose |
|------|----------|---------|
| A | `get_skill_domains()` | Domain metadata with profiles |
| A | `provides_triage()` | Returns `pm-documents:ext-triage-docs` |
| A | `provides_recipes()` | Returns `recipe-doc-verify`, `recipe-verify-architecture-diagrams`, `recipe-verify-ascii-diagrams` |
| A | `discover_modules()` | Discovers the `documentation` module when `doc/` (or `docs/`) holds `.adoc`/`.md` files **at any depth** — a nested-doc project has the same discovery seat as a top-level one |
| D | `path_attributor_id()` / `claim_paths()` | Claims the documentation corpus for the `documentation` module |
| C | `derivation_resolver_id()` / `derive_edges()` | Derives module edges from cross-document references and reports the unresolvable ones |

## Documentation surface ownership

The documentation domain **owns** its corpus across the Tier-0 substrate (see
`doc/concepts/code-intelligence.adoc`). Three properties define that ownership:

**Attribution (Axis-D).** `claim_paths()` claims `doc`, `README.md`, and
`CONTRIBUTING.md` for the `documentation` module, so `which-module` resolves the
doc corpus to the documentation domain with provenance rather than to the generic
project-root module. The claim is **per file, not by a root glob**: `CLAUDE.md` and
`AGENTS.md` are agent-instruction files, not prose documentation, and are
deliberately NOT claimed.

**De-duplication precedence.** The `documentation` module walks `doc/**`, and the
project-root module's whole-tree crawl walks it too, so one physical file would
yield a row per attributing module from the `find` / `search` inventory readers. An
explicit Axis-D claim takes precedence over the root crawl: the readers collapse a
claimed path's duplicate rows onto the owning module's single row, so one physical
file yields one row. The precedence is keyed on the ownership claim, so an
**unclaimed** duplicate is left untouched. This is the one architecture-core hook
the seam required — the claim itself goes through the extension point, but the
inventory readers had no notion of an ownership claim overriding a crawl row.

**Content search (existing seam).** Once the `documentation` module inventories
`doc/**`, `architecture search --content` answers "which document mentions X" over
the doc corpus through the **existing** content-search seam — the doc-domain
contribution is the corpus inventory, NOT a second, parallel search verb.

## Cross-document reference resolution

`derive_edges()` (Axis-C) joins over the `component_refs` the discovery pass
materializes from the doc corpus (`scripts/doc_references.py`), so a doc that
references another module's file becomes a `documentation → {module}` edge and a
reference whose target does not exist is reported as an unresolved suppression note
— the deleted-file / dangling-reference class only this domain detects.

Resolution is **convention-tolerant by design**, because a false "dangling
reference" is the misleading signal the substrate exists to avoid: a heading
contributes every id form a reference might legitimately use (AsciiDoc auto-id,
GitHub slug, raw title), inline-code and fenced-code references are treated as
examples rather than live references, and a bare `xref:id[]` is resolved as an
anchor, not a file. The bias is one-directional — it can only make a reference
resolve, never falsely fail one. The per-file, per-line broken-link report (with
line numbers) remains the province of `pm-documents:ref-asciidoc`'s
`asciidoc verify-links` command; the resolver contributes the module-graph-level
signal.

## Integration

This extension is discovered by:
- `extension-api` - Domain registration
- `skill-domains` - Domain configuration
- `marshall-steward` - Project setup wizard

## References

- `plan-marshall:extension-api` - Extension API contract
- `pm-documents:ref-asciidoc` - AsciiDoc formatting and validation
- `pm-documents:ref-documentation` - Content quality and review
