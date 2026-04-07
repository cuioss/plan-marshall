---
name: manage-credentials
description: "Credential management for external tool authentication — secure storage, interactive configuration, and REST client infrastructure"
user-invocable: false
tools:
  - Bash
  - Read
  - Write
  - AskUserQuestion
---

# Manage Credentials

Credential management skill for plan-marshall. Stores credentials outside LLM reach in `~/.plan-marshall-credentials/`, handles all user interaction via Python scripts (the LLM never sees secrets), and provides a `RestClient` for authenticated HTTP requests.

## Enforcement

**Execution mode**: Route to appropriate subcommand script via `credentials.py` dispatcher.

**Prohibited actions:**
- Never print, log, serialize, or expose credentials to stdout, stderr, or TOON output
- Never read credential files directly — all access goes through `_credentials_core.py`
- Never bypass HTTPS enforcement when auth headers are configured
- Never pass secrets as CLI arguments or through the LLM — secrets go into files directly by the user

**Constraints:**
- Primary security boundary is `chmod 700` on `~/.plan-marshall-credentials/`
- Deny rules are defense-in-depth only — fundamentally incomplete blocklist
- All file creation uses atomic `os.open()` with mode `0o600` (no umask race)
- All path resolution validates via `os.path.realpath()` (symlink protection)
- All project names sanitized via `re.sub(r'[^a-zA-Z0-9._-]', '', name)` (path traversal protection)

## Subcommands

| Subcommand | Description |
|------------|-------------|
| `configure` | Create credential file with placeholder secrets |
| `check` | Check if credential is complete (no placeholders remaining) |
| `list-providers` | List available credential providers from extensions |
| `edit` | Update non-secret fields (URL, auth type) |
| `verify` | HTTP connectivity test, updates `verified_at` |
| `list` | List configured skills (no secrets in output) |
| `remove` | Remove credential file and metadata |
| `ensure-denied` | Add deny rules to Claude Code settings |

## Script Notation

```
plan-marshall:manage-credentials:credentials
```

## Workflows

### Configure New Credentials

**Three-step workflow** — the LLM collects non-secret values, the script creates a file with placeholder secrets, and the user edits the file directly:

1. **LLM phase**: Collect provider, URL, and auth type via `AskUserQuestion`
2. **Run configure** to create credential file with placeholders:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-credentials:credentials configure \
     --skill {skill} --url {url} --auth-type {auth_type} [--scope global|project] \
     [--extra KEY=VALUE ...]
   ```
3. **If `needs_editing: true`**: Tell user to open the file path and replace placeholders with real secrets
4. **After user confirms**: Run check to verify completeness:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-credentials:credentials check \
     --skill {skill} [--scope global|project]
   ```
5. **Optionally verify** connectivity:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-credentials:credentials verify \
     --skill {skill} [--scope global|project]
   ```

**CLI args**:
- `--skill <name>` — Required. Skill name matching a credential extension
- `--url <url>` — Base URL (uses provider default if omitted)
- `--auth-type none|token|basic` — Auth type (uses provider default if omitted)
- `--extra KEY=VALUE ...` — Extra fields (e.g., `--extra organization=cuioss project_key=cuioss_repo`)

**Return statuses**:
- `created` — New file created. If `needs_editing: true`, user must edit the file to add secrets.
- `exists_complete` — File already exists with real secrets. LLM asks user whether to reuse.
- `exists_incomplete` — File exists but has placeholder secrets. LLM tells user to finish editing.

### Check Credential Completeness

```bash
python3 .plan/execute-script.py plan-marshall:manage-credentials:credentials check \
  --skill {skill} [--scope global|project]
```

Returns `complete`, `incomplete`, or `not_found`. Use after the user edits a credential file.

### List Available Providers

```bash
python3 .plan/execute-script.py plan-marshall:manage-credentials:credentials list-providers
```

Returns available credential extensions (what CAN be configured), not what IS configured. Use this in wizard/menu workflows to discover providers.

### List Configured Skills

```bash
python3 .plan/execute-script.py plan-marshall:manage-credentials:credentials list [--scope global|project|all]
```

### Edit Existing Credentials

Updates non-secret fields (URL, auth type) via CLI args. For secret changes, the user edits the credential file directly.

```bash
python3 .plan/execute-script.py plan-marshall:manage-credentials:credentials edit \
  --skill <name> [--url <url>] [--auth-type none|token|basic] [--scope global|project]
```

Returns `path` and `needs_editing` status. If secrets need updating, tell the user to edit the file at the returned path.

### Verify Connectivity

```bash
python3 .plan/execute-script.py plan-marshall:manage-credentials:credentials verify [--skill <name>] [--scope global|project]
```

### Remove Credentials

```bash
python3 .plan/execute-script.py plan-marshall:manage-credentials:credentials remove [--skill <name>] [--scope global|project]
```

### Add Deny Rules

```bash
python3 .plan/execute-script.py plan-marshall:manage-credentials:credentials ensure-denied [--target global|project]
```

## Security Model

See `standards/security-considerations.md` for full threat model and implementation constraints.

## Related

| Skill | Purpose |
|-------|---------|
| `plan-marshall:marshall-steward` | Invokes credential management via wizard and menu |
| `plan-marshall:workflow-integration-sonar` | First consumer of credential extension API |
| `plan-marshall:extension-api` | Discovery pattern reference |
| `plan-marshall:tools-permission-doctor` | Deny rule manipulation reference |
