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
| `unknown` | 1 | `success` | A server ran but published **no verdict** for the file (`answered: false`, `reason: diagnostics_unanswered`). The `diagnose` payload then carries **no** `error_count`, `warning_count` or `diagnostics[]` at all — a zero there would be a clean signal nobody measured. |

`not_configured` and `unreachable` are separately representable, so an operator
can tell "install/configure a server" from "the configured server is broken".
`ok` with `answered: true` and `unknown` are likewise separately representable,
so a reader can tell "the parser examined this file and found nothing" from "the
parser said nothing about this file" — payloads that used to be identical in
every field.

`preflight` reports the configuration situations but names the healthy one
`ready` (configured **and** reachable) rather than `ok` — `ready` is a
*precondition* check, `ok` is the outcome of a run verb that actually executed.
It never returns `unknown`, which is a statement about one file's diagnostics
rather than about the server. A consumer that
gates before calling a run verb checks `preflight` for `state: ready`.

## The write side (`edit`) — an edit nobody read, re-checked by the parser

The real risk of a `WorkspaceEdit` touching many files is that it is a mutation
**nothing read**. The `edit` verb ships, rather than asserts, the design rule
that answers it:

1. **Footprint from the edit.** The touched-file list (`files[]`, each with an
   `edit_count`) is captured from the `WorkspaceEdit` itself — never from a diff
   taken afterwards.
2. **Apply, then verify.** The edit is applied to the footprint files, then
   diagnostics are re-run over exactly those files — each wait requiring a
   `publishDiagnostics` **newer** than the one cached before the change, so the
   post-edit check can never settle for the server's opinion of the pre-edit
   content.
3. **A worsened diagnostic *set* fails the step.** The pre-edit error
   diagnostics are retained **per file**; after the edit each file's set is
   diffed and the verb fails when **any** file gained an error. It returns
   `status: failed` with `reason: diagnostics_worsened`, **rolls the change
   back** (`rolled_back: true`), and reports `errors_before` / `errors_after`
   alongside `new_diagnostics[]`, which lists the **added** diagnostics only.
   A set rather than a footprint-wide count, because a count cannot see one
   error swapped for a different one in the same file, or an error moving from
   one footprint file to another: both net to zero. ⚠ This is not the only way
   `edit` fails-and-rolls-back — a **missing** verdict does too, for the
   opposite reason, and `status: failed` alone does not tell the two apart. See
   "not checked, not wrong" below before concluding the edit was faulty.
4. **All-or-nothing on disk.** An edit carrying a create/rename/delete-file
   resource operation is refused whole (`reason:
   unsupported_resource_operation`, with `notes[]` naming each and
   `unapplied_operation_count`) rather than applied minus the part this client
   cannot perform. A failure part-way through the apply loop restores every file
   already written and returns `reason: apply_failed` with `failed_path`. The
   refusal touches nothing, and a restore that succeeds leaves no file modified
   (`rolled_back: true`). ⚠ A restore can itself fail — a read-only path, a full
   disk — and then the tree **is** left partly edited: the payload says so with
   `rolled_back: false` plus `restore_error`, never swallowing it. Read that
   flag rather than assuming the tree is clean.

### `diagnostics_unavailable` / `diagnostics_unanswered` mean "not checked", not "wrong"

A file the server publishes **no** diagnostics for has no verdict, and this
client refuses to invent one: `edit` returns `status: failed` with
`reason: diagnostics_unavailable` and rolls back, `diagnose` returns
`state: unknown` with `reason: diagnostics_unanswered`.

**Read that as "unverified", and verify by build.** It does *not* say the edit
was wrong. The usual cause is the server, not the change: some servers answer
only pull-style diagnostic requests and never push at all, and a busy server can
miss the wait window. The edit is not implicated by either.

So the next step is the canonical build — run the project's architecture-resolved
`verify` command and judge the change on **its** result. Do not revert the change
as faulty, do not retry the rename expecting a different verdict, and do not
report a broken edit: all three read a missing measurement as a negative one,
which is exactly the confusion this
fail-closed direction exists to prevent. `reason: diagnostics_worsened` is the
one that says the edit was wrong; these two say only that nobody checked.

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
