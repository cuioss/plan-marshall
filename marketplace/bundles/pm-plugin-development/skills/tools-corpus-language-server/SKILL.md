---
name: tools-corpus-language-server
description: Strictly opt-in language server over the marketplace skill corpus — go-to-definition, find-references and hover on skill and script notations, answered from the existing dependency index; a documented no-op when unconfigured
user-invocable: false
mode: script-executor
---

# Corpus Language Server Skill

The **presentation** surface for reference intelligence this repository already
has. The dependency index built by
[`tools-marketplace-inventory`](../tools-marketplace-inventory/SKILL.md) knows
five kinds of edge between components, with line-level provenance; this skill
answers `textDocument/definition`, `textDocument/references` and
`textDocument/hover` from it, over a notation token under a cursor.

⛔ **The index is consumed, never edited.** No detector, no edge type, and no
component-discovery rule changes to serve this surface.

## Enforcement

> **Base contract**: See [manage-contract.md](../../../plan-marshall/skills/ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error-response patterns.

**Execution mode**: Run the verbs via the executor; parse the TOON output (`status`, `state`, `provider_count`) and route accordingly.

**Prohibited actions:**
- Do not treat a `degraded` return as an error — it is the opt-out signal. Fall back to `Read`/`Grep` and proceed.
- Do not read an empty `references[]` as "the corpus contains no reference" — it means the **index** found none. See the completeness bound below.
- Do not present an unverified reference site as an exact location; the `verified` flag is part of the answer.
- Do not invent script arguments not listed in the **Canonical invocations** section below.

**Constraints:**
- Strictly comply with all rules from persona-plan-marshall-agent, especially tool usage and workflow step discipline.
- All CLI output uses TOON format (see `plan-marshall:ref-toon-format`).
- The entry-point script (`corpus_lsp.py`) is invoked only through `python3 .plan/execute-script.py` with the 3-part notation.

## Why the server is resident

Building the index costs about **1.9 s**, and that cost is paid **per process**.
A warm index answers every verb in **under 5 ms**. A surface that forks a process
per request is therefore a ~2 s-per-request surface no matter which protocol it
speaks, and a resident server is the only shape in which this substrate is
interactive at all — it pays the build once at `initialize`.

This is the measured reason the surface is a server rather than a one-shot verb.
The `query` verb exists for scripted and one-shot use and *does* pay the full
build each time; it is a convenience, not the interactive path.

## Opt-in, and where it is enforced

⭐ **The opt-in switch cannot live in the plugin manifest.** A plugin-declared LSP
server starts automatically when its plugin is enabled, so declaring the server
would *be* the opt-in and "strictly opt-in" would be unachievable. The switch is
therefore read by the server itself, from the project's `.plan/marshal.json`:

```json
{
  "code_intelligence": {
    "corpus_language_server": {
      "enabled": true
    }
  }
}
```

| Field | Type | Default | Meaning |
|-------|------|---------|---------|
| `enabled` | boolean | absent → `false` | Whether the surface answers at all. Only a literal `true` enables it. |
| `corpus_path` | string | `marketplace/bundles` | Corpus root, relative to the project root. |

The store is **project-local and version-controlled**, deliberately *not* the
machine-local `language_servers` section that `plan-marshall:lsp-client` reads.
That section binds a language to a **locally-installed third-party binary**,
which is machine-specific; this server ships with the repository and its command
is the same for every developer, so a git-ignored machine-local store would make
every developer configure an identical constant.

**When not enabled, the server still starts — and does nothing.** It advertises
**no capabilities**, answers every request with an empty result, and never builds
the index (so the 1.9 s cost is not paid either). A project that configures
nothing behaves exactly as it did before this skill existed.

## The coverage contract (no silent empty result)

The same fail-closed discipline `plan-marshall:lsp-client` applies, with the same
vocabulary, so a consumer reads one contract across both surfaces:

| `state` | `provider_count` | `status` | Meaning |
|---------|------------------|----------|---------|
| `not_configured` | 0 | `degraded` | The surface is absent or disabled, or the configured corpus path does not exist. Fall back to `Read`/`Grep`. |
| `ready` | 1 | `success` | `preflight` only: enabled, and the index builds. |
| `ok` | 1 | `success` | A run verb executed. An empty result is then a **real, positive answer**. |

⚠ **Completeness is bounded by index coverage.** `references` returns what the
index's detectors saw. An edge expressed in a form no detector recognises is
absent, so an empty `references[]` means *the index found no inbound edge*, never
*the corpus contains none*. Every `references` payload carries this bound in its
`completeness_note`.

## Reference provenance is verified, not assumed

The index attributes an edge cited in a skill's **sub-document** to the owning
skill, whose own file is `SKILL.md`. The recorded line number, however, belongs
to the sub-document. Following it naively sends an editor to that line number in
`SKILL.md` — a different file, usually a blank or unrelated line.

So every reference site is re-read before it is reported: the owner's file first,
then its sub-documents, for a line that actually contains the notation.

| `verified` | Meaning |
|---|---|
| `true` | The cited line was re-read and contains the notation — an exact location. |
| `false` | The site could not be confirmed (a non-positional frontmatter edge, or a line that no longer matches). Reported against the owner's file, and **never presented as exact**. |

## Diagnostics are deliberately absent

⛔ No diagnostic provider is advertised. Live broken-reference diagnostics are
deliverable D3 of the `240-skill-lsp-server` plan, **hard-gated** on the
validator-precision work: the validator's current unresolved set is
overwhelmingly false positives (documentation placeholders, foreign namespaces
such as build-command and Maven coordinates, and verb-suffixed notations whose
skill exists). Advertising a diagnostic provider before that precision work lands
would ship confident-wrong squiggles at the corpus's most visible surface.

## Scripts

**Script**: `pm-plugin-development:tools-corpus-language-server:corpus_lsp`

| Verb | Purpose |
|------|---------|
| `preflight` | Report `not_configured` \| `ready`, plus index coverage figures |
| `query` | Answer one `definition` / `references` / `hover` lookup without an LSP client |
| `serve` | Run the language server on stdio (JSON-RPC), for an editor or an agent LSP client |

## Canonical invocations

The canonical argparse surface for `corpus_lsp.py`. The plugin-doctor analyzer
(`_analyze_manage_invocation.py`) reads this section as source-of-truth for the
`manage-invocation-invalid` and `missing-canonical-block` rules. Consuming docs
xref this section by name instead of restating the command inline. See
[`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### preflight

```bash
python3 .plan/execute-script.py pm-plugin-development:tools-corpus-language-server:corpus_lsp preflight \
  [--project-path PROJECT_PATH]
```

### query

```bash
python3 .plan/execute-script.py pm-plugin-development:tools-corpus-language-server:corpus_lsp query \
  --kind (definition | references | hover) --notation NOTATION \
  [--project-path PROJECT_PATH]
```

### serve

```bash
python3 .plan/execute-script.py pm-plugin-development:tools-corpus-language-server:corpus_lsp serve \
  [--project-path PROJECT_PATH]
```

`serve` speaks JSON-RPC on stdio and does not emit TOON.

## Related Skills

- `pm-plugin-development:tools-marketplace-inventory` — builds the index this skill reads
- `plan-marshall:lsp-client` — the opposite direction: a client of a third-party code language server
- `pm-code-intelligence:plan-marshall-plugin` — LSP as a derivation-time edge producer for the module graph
