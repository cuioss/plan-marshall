---
name: manage-providers
description: "Provider management for external tool authentication across two transport lanes — system-authenticated CLI providers verified by running their declared command, and token-authenticated REST providers with secure credential storage, interactive configuration, and RestClient infrastructure"
user-invocable: false
mode: script-executor
---

# Manage Providers

Provider management skill for plan-marshall. It registers providers of two kinds, and both are first-class:

- **System-authenticated (CLI) providers** — `gh`, `glab`, `git`. The vendor CLI owns its own token store, so plan-marshall holds **no credential for them at all**. Registration records what command proves the tool is authenticated, and verification runs that command.
- **Token-authenticated (REST) providers** — Sonar and anything else reached over HTTP. For these the skill stores credentials outside LLM reach in `~/.plan-marshall/credentials/` (under the machine-global home root, overridable via the `PLAN_MARSHALL_HOME` env var), handles all user interaction via Python scripts (the LLM never sees secrets), and provides a `RestClient` for authenticated HTTP requests.

The credential machinery below — `configure`, `check`, `verify`, `remove`, the deny rules, the file permissions — belongs to the token-auth lane. A system-auth provider passes through none of it.

## Enforcement

**Execution mode**: Route to appropriate subcommand script via `credentials.py` dispatcher.

**Prohibited actions:**
- Never print, log, serialize, or expose credentials to stdout, stderr, or TOON output
- Never read credential files directly — all access goes through `_providers_core.py`
- Never bypass HTTPS enforcement when auth headers are configured
- Never pass secrets as CLI arguments or through the LLM — secrets go into files directly by the user

**Constraints:**
- Primary security boundary is `chmod 700` on `~/.plan-marshall/credentials/`
- Deny rules are defense-in-depth only — fundamentally incomplete blocklist
- All file creation uses atomic `os.open()` with mode `0o600` (no umask race)
- All path resolution validates via `os.path.realpath()` (symlink protection)
- All project names sanitized via `re.sub(r'[^a-zA-Z0-9._-]', '', name)` (path traversal protection)

## Architecture

### Two transport lanes

A declaration's own fields select its lane — there is no separate flag. Which field selects which lane, and what each lane authenticates and verifies with, is the declaration contract: see [`extension-api/standards/ext-point-provider.md`](../extension-api/standards/ext-point-provider.md) § "Two transport lanes". On this skill's side the split is `_providers_core.verify_system_auth()` running a declared `verify_command` for the CLI lane, against a `RestClient` round-trip for the REST lane.

This split is why the marshall-steward wizard's credential-setup flow **filters CI providers out**: `provider-setup.md` Step 13e excludes `workflow-integration-github` and `workflow-integration-gitlab` from the list it offers, because there is no credential for the wizard to collect. Steps 13a–13d handle those providers through their own CLI login instead. The decision behind the split is recorded in [ADR-018](../../../../../doc/adr/018-CI_providers_integrate_via_their_official_CLI_API_providers_via_RestClient.adoc).

### Discovery

Provider discovery uses a two-phase approach based on `marshal.json` declarations:

1. **Setup time** (`discover-and-persist`): Scans PYTHONPATH for `*_provider.py` files, calls `get_provider_declarations()` on each, and persists the combined declarations to `marshal.json` under the `providers` key. The marshall-steward wizard runs this during project setup.
2. **Runtime** (`list-providers`): Reads provider declarations directly from `marshal.json`. No filesystem scanning occurs at runtime.

Each provider module exports `get_provider_declarations()` returning a list of declaration dicts. Four fields are persisted to marshal.json — `skill_name`, `category`, `verify_command`, `description` — plus `url` when one resolves. All other fields (`display_name`, `default_url`, `header_name`, `header_value_template`, `verify_endpoint`, `verify_method`, `extra_fields`, `detection`) are wizard-time or runtime-only and are not stored. The `skill_name` field uses bundle-prefixed format (e.g., `plan-marshall:workflow-integration-sonar`).

`url` is derived rather than declared, and not every provider has one — [`ext-point-provider.md`](../extension-api/standards/ext-point-provider.md) § "Persisted vs Wizard-time Fields" carries the per-lane derivation. A CLI-lane provider resolves none, and `list-providers` omits the key rather than emitting an empty string, which would read as a provider configured with a blank URL.

`providers[].skill_name` stays bundle-prefixed, but the `credentials_config` storage key is canonicalized to the prefix-stripped form (e.g. `workflow-integration-sonar`), matching the credential filename under `~/.plan-marshall/credentials/`. Writes always key the block by that canonical form and drop any pre-existing key whose canonical form is the same, so a re-configure never leaves two shadow blocks for one provider; reads accept either spelling — an exact `skill_name` match first, then a canonical-equality scan.

Stale prefixed `credentials_config` keys written before this normalization are canonicalized transparently by `_providers_core` on the next `credentials_config` access — no operator action, no migration subcommand. The pass is idempotent: once every key is canonical it performs no write. When two source keys collapse onto one canonical key with differing bodies, the pass leaves both keys untouched rather than merging them, so no block is ever lost silently.

## Subcommands

| Subcommand | Description |
|------------|-------------|
| `configure` | Create credential file with placeholder secrets |
| `check` | Check if credential is complete (no placeholders remaining) |
| `discover-and-persist` | Scan PYTHONPATH for provider modules and persist declarations to marshal.json |
| `list-providers` | List available credential providers from marshal.json |
| `edit` | Update non-secret fields (URL, auth type) |
| `verify` | Token-auth lane only: HTTP connectivity test, writes `verified_at` timestamp into the credential file. System-auth providers are verified by `verify_system_auth()` running their `verify_command`, not by this subcommand |
| `list` | List configured skills by scanning `~/.plan-marshall/credentials/` (no secrets in output) |
| `remove` | Remove credential file |
| `ensure-denied` | Protect the credentials directory in the active target's settings (`no-op` on a target with no permission backend) |
| `migrate-home` | Explicitly run the lazy legacy-path migration (`~/.plan-marshall-credentials/` → `~/.plan-marshall/credentials/`); reports `migrated`, `already_migrated`, or `conflict` |

## Script Notation

```text
plan-marshall:manage-providers:credentials
```

## Workflows

### Configure New Credentials

**Three-step workflow** — the LLM collects non-secret values, the script creates a file with placeholder secrets, and the user edits the file directly:

1. **LLM phase**: Collect provider, URL, and auth type via `AskUserQuestion`
2. **Run configure** to create credential file with placeholders:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-providers:credentials configure \
     --skill {skill} --url {url} --auth-type {auth_type} [--scope global|project] \
     [--extra KEY=VALUE ...]
   ```
3. **If `warnings` is present**: relay each warning string to the user. A warning means a supplied `--extra` value (e.g. `organization`) disagreed with the project's `pom.xml` Sonar property; the script kept the supplied value but surfaces the mismatch so the user can reconcile it.
4. **If `needs_editing: true`**: Tell user to open the file path and replace placeholders with real secrets
5. **After user confirms**: Run check to verify completeness:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-providers:credentials check \
     --skill {skill} [--scope global|project]
   ```
6. **Optionally verify** connectivity:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-providers:credentials verify \
     --skill {skill} [--scope global|project]
   ```

**CLI args**:
- `--skill <name>` — Required. Skill name matching a credential extension
- `--url <url>` — Base URL (uses provider default if omitted)
- `--auth-type none|token|basic` — Auth type (uses provider default if omitted)
- `--extra KEY=VALUE ...` — Extra fields (e.g., `--extra organization=cuioss project_key=cuioss_repo`)

For the Sonar provider on a Maven project, `configure` auto-derives `organization` and `project_key` from the project's `pom.xml` `<sonar.organization>` / `<sonar.projectKey>` properties when they are not supplied via `--extra`. When such a value IS supplied via `--extra` and disagrees with the pom-derived value, the supplied value is kept and a non-fatal mismatch warning is surfaced (see `warnings` / `mismatches` below).

**Return statuses**:
- `created` — New file created. If `needs_editing: true`, user must edit the file to add secrets. May carry `warnings` (list of human-readable mismatch strings — relay each to the user) and `mismatches` (structured `{field, supplied, pom_value}` entries) when a supplied `--extra` value disagrees with the project's `pom.xml` Sonar property.
- `exists_complete` — File already exists with real secrets. LLM asks user whether to reuse.
- `exists_incomplete` — File exists but has placeholder secrets. LLM tells user to finish editing.

### Check Credential Completeness

```bash
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials check \
  --skill {skill} [--scope global|project]
```

Returns `complete`, `incomplete`, or `not_found`. Use after the user edits a credential file.

### Discover and Persist Providers

Run during project setup (typically by the marshall-steward wizard) to scan for provider modules and populate `marshal.json`:

```bash
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials discover-and-persist
```

Scans all PYTHONPATH directories (set by the executor) for `*_provider.py` files, loads each module, calls `get_provider_declarations()`, and writes the combined list to `marshal.json` under the `providers` key.

**Return fields**: `status`, `action`, `count`, `providers` (list of skill names).

### List Available Providers

```bash
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials list-providers
```

Reads the `providers` list from `marshal.json` (populated by `discover-and-persist`). Returns available credential providers (what CAN be configured), not what IS configured. Use this in wizard/menu workflows to discover providers.

If no providers are found, the output includes a hint to run `discover-and-persist` first.

### List Configured Skills

```bash
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials list [--scope global|project|all]
```

### Edit Existing Credentials

Updates non-secret fields (URL, auth type) via CLI args, and idempotently upserts extra provider-config fields (e.g. `organization`, `project_key`) via `--extra KEY=VALUE ...` without dropping the stored token. For secret changes, the user edits the credential file directly.

```bash
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials edit \
  --skill <name> [--url <url>] [--auth-type none|token|basic] [--scope global|project] \
  [--extra KEY=VALUE ...]
```

Returns `path` and `needs_editing` status, plus `extras_upserted` (the list of extra-field keys written) when `--extra` was supplied. If secrets need updating, tell the user to edit the file at the returned path.

### Verify Connectivity

```bash
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials verify [--skill <name>] [--scope global|project]
```

### Remove Credentials

```bash
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials remove [--skill <name>] [--scope global|project]
```

### Protect the Credentials Directory

```bash
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials ensure-denied [--target global|project]
```

The command states the goal; the active target's runtime decides what expresses it and writes it. A target with no permission backend returns `no-op` with a reason, and the directory's `0700` mode — the primary boundary — is re-asserted either way.

It can also fail, and a caller must not read failure as protection:

| `error` | Meaning | What to do |
|---|---|---|
| `unknown_target` | `runtime.target` names no registered runtime | Fix `runtime.target` in `marshal.json` |
| `invalid_operation` | The credentials directory cannot be expressed as a rule — it is relative, is the filesystem root, contains `..` or whitespace, or carries `(`, `)`, `*` or a control character | Set `PLAN_MARSHALL_HOME` to an absolute path, below the root, free of those — so the credentials directory beneath it is renderable. The `message` names the path and the reason |
| `invalid_settings` | The settings file cannot be used as settings. Four shapes reach this: unparseable JSON; a JSON root that is not an object; a `permissions` value that is not an object; and a `permissions.deny` that is not a list. The middle two parse as valid JSON, so a syntax check does not catch them | Repair the settings file; **nothing was written** in any of the four cases |
| `io_error` | The rules were rendered but the settings file could not be written | Check permissions on the settings file. **This run writes nothing** — the settings file is unchanged, so its protection is whatever it already contains |

## Security Model

See `standards/security-considerations.md` for full threat model and implementation constraints.

## Testing

Tests override the credentials directory via the `PLAN_MARSHALL_CREDENTIALS_DIR` environment variable (read at module import time in `_providers_core.CREDENTIALS_DIR`). This is a testing-only knob — not a user-facing setting. Tests should set it via `monkeypatch.setenv` before importing `_providers_core`, or patch `_providers_core.CREDENTIALS_DIR` directly and reload as needed.

## Canonical invocations

The canonical argparse surface for `credentials.py`. The plugin-doctor analyzer (`_analyze_manage_invocation.py`) reads this section as source-of-truth for the `manage-invocation-invalid` and `missing-canonical-block` rules. Consuming docs xref this section by name instead of restating the command inline. See [`pm-plugin-development:plugin-script-architecture` cross-skill-integration.md](../../../pm-plugin-development/skills/plugin-script-architecture/standards/cross-skill-integration.md) § "Script invocation in documentation".

### configure

```bash
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials configure \
  [--skill SKILL] [--scope {global,project}] [--url URL] [--auth-type {none,token,basic}] \
  [--extra KEY=VALUE ...]
```

### edit

```bash
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials edit \
  [--skill SKILL] [--scope {global,project}] [--url URL] [--auth-type {none,token,basic}] \
  [--extra KEY=VALUE ...]
```

### check

```bash
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials check \
  --skill SKILL [--scope {global,project}]
```

### verify

```bash
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials verify \
  [--skill SKILL] [--scope {global,project}]
```

### discover-and-persist

```bash
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials discover-and-persist \
  [--providers PROVIDERS]
```

### list-providers

```bash
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials list-providers
```

### find-by-category

```bash
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials find-by-category \
  --category CATEGORY
```

### list

```bash
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials list \
  [--scope {global,project,all}]
```

### remove

```bash
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials remove \
  [--skill SKILL] [--scope {global,project}]
```

### ensure-denied

```bash
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials ensure-denied \
  [--target {global,project}]
```

### migrate-home

```bash
python3 .plan/execute-script.py plan-marshall:manage-providers:credentials migrate-home
```

## Related

| Skill | Purpose |
|-------|---------|
| `plan-marshall:marshall-steward` | Invokes credential management via wizard and menu |
| `plan-marshall:workflow-integration-sonar` | First consumer of credential extension API |
| `plan-marshall:extension-api` | Discovery pattern reference |
| `plan-marshall:tools-permission-doctor` | Allow-list audit (redundancy, security anti-patterns, missing step permissions). It does **not** read the deny rules `ensure-denied` writes, so it will not tell you whether the credentials directory is protected |
