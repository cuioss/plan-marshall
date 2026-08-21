# Security Considerations

Reference document for the manage-providers skill covering threat model, security boundaries, and implementation constraints.

## Threat Model

### Threat 1: LLM Credential Exfiltration

**Primary boundary**: `chmod 700` on `~/.plan-marshall/credentials/` directory (under the machine-global home root, overridable via `PLAN_MARSHALL_HOME`). The OS prevents any process running as a different user from reading.

**Defense-in-depth**: whatever the active target's runtime uses to deny reads of that directory — on a target with a permission model, rules covering the read tool, the file-dumping shell binaries, and inline-script invocation, in every spelling of the path that model distinguishes. The rules are not enumerated here: the set is rendered by the runtime (`platform-runtime`, `permission fix --operation protect-path`), and a second copy in prose is a copy that goes stale. See [`../SKILL.md`](../SKILL.md) § "Protect the Credentials Directory" for the command and its behaviour on a target with no permission backend.

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

**The pattern set is not restated here.** It is rendered by the active target's runtime from the
credentials directory it is asked to protect — `platform-runtime`, `permission fix --operation
protect-path` — and a copy in prose is a copy that drifts. Read the set from
`platform-runtime/scripts/claude_runtime.py` (`_protect_path_deny_rules`, and the vectors it
iterates) or from a settings file the command has written.

What the coverage *is*, stated as intent rather than as syntax: the `Read` tool, the file-dumping
shell binaries the vector list names, and inline-script invocation. Each is rendered in the tilde
and absolute spellings of the path; a directory outside the home has only one spelling, so it
yields correspondingly fewer rules covering the same ground.

**What that does not cover** is as important as what it does, so it is stated rather than left to
be inferred from a pattern list: other spellings of the same directory (an unexpanded `$HOME`, a
cwd-relative read, a `..`-bearing form) are not rendered, and tools other than `Read` and `Bash`
— `Grep`, `Glob`, `Write`, `Edit` — get no rule at all. The list below is the standing set of
acknowledged gaps.

### Acknowledged Bypass Limitations

- New shell commands not in the blocklist
- Scripting runtimes (ruby, perl, node) not covered
- Tools other than `Read` and the named `Bash` binaries — `Grep` returns file content and is not denied; `Write` and `Edit` are not denied either
- Path spellings other than the two rendered — an unexpanded `$HOME`, a cwd-relative read, a `..`-bearing form
- Indirect reads via symlinks (mitigated by `os.path.realpath()` validation), and a symlinked credentials directory, whose rules name the link rather than its target
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
