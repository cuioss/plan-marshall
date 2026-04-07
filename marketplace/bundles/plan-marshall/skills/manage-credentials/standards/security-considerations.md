# Security Considerations

Reference document for the manage-credentials skill covering threat model, security boundaries, and implementation constraints.

## Threat Model

### Threat 1: LLM Credential Exfiltration

**Primary boundary**: `chmod 700` on `~/.plan-marshall-credentials/` directory. The OS prevents any process running as a different user from reading.

**Defense-in-depth**: Claude Code deny rules covering `Read`, `Bash(cat)`, `Bash(head)`, `Bash(tail)`, `Bash(less)`, `Bash(more)`, `Bash(cp)`, `Bash(grep)`, `Bash(python3 -c)`, `Bash(base64)` — both `~` and absolute path forms.

**Limitation acknowledged**: Deny rules are fundamentally a blocklist. New bypass vectors (e.g., new Bash commands, scripting runtimes) are always possible. `chmod 700` is the real security control.

### Threat 2: Secret Leakage in Output

- **TOON output**: No CLI subcommand exposes credentials. The `get_authenticated_client()` Python API keeps secrets in-process only.
- **Tracebacks**: `RestClient.request()` catches all exceptions and re-raises `RestClientError` with `from None` to strip local variable context (which contains `_headers`).
- **Error responses**: `_redact_body()` scrubs token/password patterns from API error responses before they reach exception messages.
- **JSON parse errors**: `load_credential()` catches `JSONDecodeError` generically — never includes file content in error messages.

### Threat 3: Credential File Tampering

- **Atomic file creation**: `os.open(path, O_WRONLY|O_CREAT|O_TRUNC, 0o600)` — no umask race window.
- **Post-write verification**: `save_credential()` checks file permissions after write, raises on mismatch.
- **Symlink protection**: `resolve_credential_path()` validates via `os.path.realpath()` that the resolved path is under `CREDENTIALS_DIR`.
- **Path traversal protection**: `get_project_name()` sanitizes with `re.sub(r'[^a-zA-Z0-9._-]', '', name)`.

### Threat 4: Network Credential Leakage

- **HTTPS-only**: `RestClient.__init__()` rejects `http://` URLs when auth headers are present.
- **Explicit SSL context**: `ssl.create_default_context()` — proper certificate verification, no bypass.
- **No credentials in URLs**: Auth always via headers, never query parameters.

## Implementation Constraints (Hard Rules)

These constraints apply to all scripts in this skill:

1. Never print/log/serialize credentials to stdout, stderr, or TOON output
2. Always use `os.open()` with mode `0o600` for atomic file creation (no umask race)
3. Always verify resolved paths are under `CREDENTIALS_DIR` via `os.path.realpath()` (symlink protection)
4. Always sanitize project names via `re.sub(r'[^a-zA-Z0-9._-]', '', name)` (path traversal protection)
5. Always catch exceptions without exposing `_headers` in tracebacks (`from None`)
6. Always redact potential credential patterns in API error responses
7. Always reject HTTP URLs when auth headers are configured (HTTPS-only)
8. Always use `ssl.create_default_context()` (no unverified contexts)

## Deny Rule Coverage

### Covered Patterns

```
Read(~/.plan-marshall-credentials/**)
Read({abs_path}/**)
Bash(cat ~/.plan-marshall-credentials/*)
Bash(cat {abs_path}/*)
Bash(head ~/.plan-marshall-credentials/*)
Bash(tail ~/.plan-marshall-credentials/*)
Bash(less ~/.plan-marshall-credentials/*)
Bash(more ~/.plan-marshall-credentials/*)
Bash(cp ~/.plan-marshall-credentials/*)
Bash(grep ~/.plan-marshall-credentials/*)
Bash(python3 -c *plan-marshall-credentials*)
Bash(base64 ~/.plan-marshall-credentials/*)
```

### Acknowledged Bypass Limitations

- New shell commands not in the blocklist
- Scripting runtimes (ruby, perl, node) not covered
- Indirect reads via symlinks (mitigated by `os.path.realpath()` validation)
- Process-level reads by same-user processes

## Testing Requirements

Every security constraint must have a corresponding test:

| Constraint | Test |
|------------|------|
| HTTPS enforcement | Verify `RestClient` rejects `http://` with auth headers |
| Permission checks | Verify files created with `0o600`, directories with `0o700` |
| Path traversal | Verify malicious project names are sanitized |
| Symlink protection | Verify symlinks outside `CREDENTIALS_DIR` are rejected |
| Credential redaction | Verify error responses are scrubbed |
| Traceback safety | Verify `_headers` doesn't appear in exception context |
| No secrets in output | Verify TOON output of all subcommands contains no credentials |
