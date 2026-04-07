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
- Never use `input()` for secret values — always use `getpass.getpass()`

**Constraints:**
- Primary security boundary is `chmod 700` on `~/.plan-marshall-credentials/`
- Deny rules are defense-in-depth only — fundamentally incomplete blocklist
- All file creation uses atomic `os.open()` with mode `0o600` (no umask race)
- All path resolution validates via `os.path.realpath()` (symlink protection)
- All project names sanitized via `re.sub(r'[^a-zA-Z0-9._-]', '', name)` (path traversal protection)

## Subcommands

| Subcommand | Description |
|------------|-------------|
| `configure` | Credential setup (interactive or fully CLI-driven) |
| `list-providers` | List available credential providers from extensions |
| `edit` | Edit existing credentials (re-prompts, preserves defaults) |
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

**Two-phase workflow** — the LLM collects non-secret values, then the script runs interactively for secrets:

1. **LLM phase**: Collect provider, URL, and auth type via `AskUserQuestion`
2. **Build command** with CLI args:
   ```bash
   python3 .plan/execute-script.py plan-marshall:manage-credentials:credentials configure \
     --skill {skill} --url {url} --auth-type {auth_type} [--verify|--no-verify] [--scope global|project]
   ```
3. **For `auth_type=none`**: Run via executor (no interactive input needed — completes without TTY)
4. **For `auth_type=token` or `auth_type=basic`**: Run interactively via `!` prefix (secrets need TTY):
   ```
   ! python3 .plan/execute-script.py plan-marshall:manage-credentials:credentials configure \
     --skill {skill} --url {url} --auth-type {auth_type} --verify
   ```

**CLI args** (skip corresponding prompts when provided):
- `--skill <name>` — Skip provider selection menu
- `--url <url>` — Skip URL prompt
- `--auth-type none|token|basic` — Skip auth type prompt
- `--token <token>` — API token (skips interactive token prompt)
- `--username <user>` / `--password <pass>` — Basic auth credentials (skips interactive prompts)
- `--verify` / `--no-verify` — Skip verify prompt
- `--extra KEY=VALUE ...` — Extra fields (e.g., `--extra organization=cuioss project_key=cuioss_repo`)

**Fully non-interactive example** (all values as CLI args, no TTY needed):
```bash
python3 .plan/execute-script.py plan-marshall:manage-credentials:credentials configure \
  --skill workflow-integration-sonar --url https://sonarcloud.io --auth-type token \
  --token {token} --extra organization=cuioss project_key=cuioss_plan-marshall --no-verify
```

Without `--skill` in interactive mode: discovers all available credential extensions, presents numbered selection menu.

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

Same two-phase pattern as configure:

1. **LLM phase**: Collect URL and auth type changes via `AskUserQuestion`
2. **For `auth_type=none`**: Run via executor
3. **For `auth_type=token` or `auth_type=basic`**: Run interactively via `!` prefix

```bash
python3 .plan/execute-script.py plan-marshall:manage-credentials:credentials edit \
  --skill <name> [--url <url>] [--auth-type none|token|basic] [--scope global|project]
```

In non-TTY mode, URL and auth type keep existing values if CLI args are not provided. Secrets keep existing values when not running interactively.

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
