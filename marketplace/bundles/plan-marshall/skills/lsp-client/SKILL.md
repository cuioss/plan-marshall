---
name: lsp-client
description: Opt-in language-server client for phase-5-execute — locate symbols by coordinate (definition/references/documentSymbol/workspace-symbol) and apply a verified multi-file rename WorkspaceEdit whose footprint is captured from the edit and re-checked by diagnostics; consumption only, fail-soft to Read/Edit when unconfigured
user-invocable: false
mode: script-executor
scope: global
---

# LSP Client Skill

The **consumption** surface for a warm language server, reachable from a
`phase-5-execute` leaf for the two things a server is better at than reading
files: **locating** work by coordinate, and applying a **verified multi-file
edit**. `workspace/symbol`, `definition`, `references` and `documentSymbol`
return coordinates, not bodies; `rename` returns a `WorkspaceEdit` — one
complete, parser-verified, multi-file patch — and `publishDiagnostics` returns a
correctness signal without a build.

This skill is `script-deterministic` — every verb is a deterministic executor
call. The server is hosted **inside the envelope**: `lsp_client.py` spawns the
configured server (e.g. `pyright-langserver --stdio`) as a short-lived
subprocess, uses it for the call, and tears it down. There is no daemon, no
socket, and no long-lived child — cold start is paid once per call, and the
natural unit is a per-call batch of lookups or one edit-and-re-diagnose.

The client is deliberately **fail-soft and opt-in**. When no server is
configured for the language, or a configured server does not start, the verb
returns `degraded` with `fallback: read_edit`, and the caller takes today's
`Read` / `Edit` path — byte-identically to a project that never configured a
server.

## Enforcement

> **Base contract**: See [manage-contract.md](../ref-workflow-architecture/standards/manage-contract.md) for shared enforcement rules, TOON output format, and error-response patterns.

**Execution mode**: Run the verbs via the executor; parse the TOON output (`status`, `state`, `provider_count`) and route accordingly.

**Prohibited actions:**
- Do not treat a `degraded` return as an error — it is the opt-out signal. Fall back to `Read`/`Edit` and proceed.
- Do not derive an edit's footprint from a later `git diff` — the `edit` verb captures it from the `WorkspaceEdit` itself and returns it in `files[]`. Trust that footprint.
- Do not read the `diagnose` verb as a replacement for the quality gate — it **supplements** the gate, it does not replace it. Run the canonical build (`./pw verify`) before relying on a clean result.
- Do not invent script arguments not listed in the **Canonical invocations** section below.

**Constraints:**
- Strictly comply with all rules from persona-plan-marshall-agent, especially tool usage and workflow step discipline.
- All script output uses TOON format (see `plan-marshall:ref-toon-format`).
- The entry-point script (`lsp_client.py`) is invoked only through `python3 .plan/execute-script.py` with the 3-part notation.

## The coverage contract (no silent empty result)

Every verb keeps *no server ran* distinguishable from *the server ran and found
nothing* — the same fail-closed discipline the module graph applies one tier up
(`resolver_count` / `attributor_count` / `files_scanned`; see
`doc/concepts/code-intelligence.adoc`). The discriminator is `state` +
`provider_count`:

| `state` | `provider_count` | `status` | Meaning |
|---------|------------------|----------|---------|
| `not_configured` | 0 | `degraded` | No server is configured (or it is disabled) for this language. Absence of capability — fall back to `Read`/`Edit`. |
| `unreachable` | 0 | `degraded` | A server is configured but did not start/initialise; carries a `reason`. Fall back to `Read`/`Edit`. |
| `ok` | 1 | `success` | A server ran. An empty `locations[]` / `diagnostics[]` is then a **real, positive answer**, not a missing capability. |

`not_configured` and `unreachable` are separately representable, so an operator
can tell "install/configure a server" from "the configured server is broken".

## The write side (`edit`) — an edit nobody read, re-checked by the parser

The real risk of a `WorkspaceEdit` touching many files is that it is a mutation
**nothing read**. The `edit` verb ships, rather than asserts, the design rule
that answers it:

1. **Footprint from the edit.** The touched-file list (`files[]`, each with an
   `edit_count`) is captured from the `WorkspaceEdit` itself — never from a diff
   taken afterwards.
2. **Apply, then verify.** The edit is applied to the footprint files, then
   diagnostics are re-run over exactly those files.
3. **A worsened diagnostic set fails the step.** If the post-application error
   count exceeds the pre-application count, the verb returns `status: failed`
   with `reason: diagnostics_worsened`, **rolls the change back**
   (`rolled_back: true`), and reports `errors_before` / `errors_after` /
   `new_diagnostics[]`. An edit that broke the parse never lands silently.

## Diagnostics (`diagnose`) supplement the gate — they do not replace it

`diagnose` surfaces the class of errors a server sees ahead of the build
round-trip — unresolved imports, syntax errors, type errors. It is a **pre-build
correctness signal**, and every payload carries the boundary in `boundary_note`.
It does **not** run the project's quality gate, tests, linters, or coverage, and
a clean `diagnose` is **not** a green build. Run `./pw verify` (the canonical
build) before relying on a clean result. Use `diagnose` to catch a broken edit
early and cheaply; use the gate to decide the change is correct.

## Opt-in configuration

The client reads the machine-local `language_servers` section of
`run-configuration.json` (see
[`manage-run-config`](../manage-run-config/standards/run-config-standard.md) §
"Language-Servers Section"). The binding is machine-local because a language
server is locally-installed tooling that differs per machine. An unconfigured or
disabled language yields `state: not_configured` and the `Read`/`Edit` fallback —
so a project that never configures a server loses nothing. The configuration
surface is shared with the resolver-configuration work; this skill does not ship
a parallel store.

## Scripts

**Script**: `plan-marshall:lsp-client:lsp_client`

| Verb | Purpose |
|------|---------|
| `preflight` | Report `not_configured` \| `ready` (configured + reachable) \| `unreachable` + reason |
| `lookup` | Locate a symbol by coordinate (`definition` / `references` / `document-symbol` / `workspace-symbol`) |
| `edit` | Apply a verified symbol rename; footprint from the edit; worsened diagnostics fail and roll back |
| `diagnose` | Diagnostics for a file as a pre-build signal (supplements the gate) |

## Canonical invocations

The canonical argparse surface for `lsp_client.py`. The plugin-doctor analyzer
(`_analyze_manage_invocation.py`) reads this section as source-of-truth for the
`manage-invocation-invalid` and `missing-canonical-block` rules. Consuming docs
xref this section by name instead of restating the command inline. See
[`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### preflight

```bash
python3 .plan/execute-script.py plan-marshall:lsp-client:lsp_client preflight \
  [--language LANGUAGE] [--project-path PROJECT_PATH]
```

### lookup

```bash
python3 .plan/execute-script.py plan-marshall:lsp-client:lsp_client lookup \
  --kind (definition | references | document-symbol | workspace-symbol) \
  [--file FILE] [--line LINE] [--character CHARACTER] [--symbol SYMBOL] \
  [--language LANGUAGE] [--project-path PROJECT_PATH]
```

`--file` is required for `definition` / `references` / `document-symbol`;
`--symbol` is required for `workspace-symbol`.

### edit

```bash
python3 .plan/execute-script.py plan-marshall:lsp-client:lsp_client edit \
  --file FILE --line LINE --character CHARACTER --new-name NEW_NAME \
  [--language LANGUAGE] [--project-path PROJECT_PATH]
```

### diagnose

```bash
python3 .plan/execute-script.py plan-marshall:lsp-client:lsp_client diagnose \
  --file FILE [--language LANGUAGE] [--project-path PROJECT_PATH]
```

## Related

- `manage-run-config` — the machine-local `language_servers` configuration section this client reads.
- `execute-task` — the phase-5 leaf consumer that reaches lookup/edit when a server is configured, and falls back to `Read`/`Edit` when it is not.
- `ref-toon-format` — the TOON output format every verb returns.
