# Python Script Surface

The marketplace ships ~hundreds of Python scripts — every `manage-*`, build, extension, and workflow-helper script — that a *consumer project* drives through the executor. Each script runs with the developer's full filesystem and process privileges, reads the consumer project's environment and files, and is handed data declared by third-party domain bundles. That makes the scripts, not "an application", the meta-project's primary injection surface. This standard covers the four sinks where an untrusted value reaches a dangerous operation: subprocess invocation, path traversal, environment trust, and unvalidated extension config-key handling.

The conceptual foundations — why each boundary value is untrusted, the allow-list / canonicalize-before-validate / fail-closed architecture, and the OWASP risk mapping — live in the centralized persona; this standard owns only the marketplace mechanics and cross-references upward.

| Foundation | Home |
|------------|------|
| Trust-boundary architecture, allow-list vs deny-list, canonicalize-before-validate, fail-closed | [`input-validation-trust-boundaries.md`](../../../../plan-marshall/skills/persona-security-expert/standards/input-validation-trust-boundaries.md) |
| Injection / path-traversal risk categories | [`owasp-top-ten.md`](../../../../plan-marshall/skills/persona-security-expert/standards/owasp-top-ten.md) |
| Secure-by-default, fail-securely, complete-mediation principles | [`secure-design-principles.md`](../../../../plan-marshall/skills/persona-security-expert/standards/secure-design-principles.md) |

## Sink summary

The secure-by-default choice at each marketplace boundary. The Python stdlib mechanics are shared with `pm-dev-python:python-security`; this table is the marketplace-script application of them.

| Sink | Untrusted source in a marketplace script | Insecure | Secure |
|------|------------------------------------------|----------|--------|
| Subprocess | build command args, resolved executables, branch/path values from a consumer repo | `shell=True` with an interpolated string | argv list, no shell; `shlex.quote` only when a shell is unavoidable |
| Path | environment (`PLUGIN_CACHE_PATH`), CLI `--project-dir`, file contents from the consumer project | `Path(untrusted)` consumed directly | resolve, then confirm containment in a known safe base before use |
| Environment | `os.environ.get(...)` overrides | trust the value verbatim | treat as untrusted; validate shape and containment before building a `Path`/argv from it |
| Extension data | `get_skill_domains()` `domain`/profile/notation keys | route verbatim into fs/subprocess/import | confirm against the declared allow-list of known domains/profiles before any downstream use |

## Subprocess invocation

**Maps to:** CWE-78 (OS Command Injection) · OWASP A03 Injection · ASVS V5

Marketplace scripts shell out to build tools (`mvn`, `gradle`, `npm`, `pw`), to `git`, and to the executor itself. The argument values frequently originate in a consumer project — a branch name, a module path, a resolved build executable. Build the call as an argv list passed to `subprocess.run([...])` with no shell; never assemble a command string and run it with `shell=True`. When a shell is genuinely unavoidable, every interpolated value must pass through `shlex.quote`. A branch name like `feature/x; rm -rf ~` is a realistic injection payload when a consumer repo's refs reach a `shell=True` string.

## Path traversal at the filesystem boundary

**Maps to:** CWE-22 (Path Traversal) · OWASP A01 Broken Access Control · ASVS V12

Scripts resolve worktree paths, plan directories, cache roots, and `--project-dir` values. A value sourced from environment, a CLI flag, or a consumer file can carry `../` segments or an absolute path that escapes the intended root. Canonicalize with `Path(...).resolve()` and then confirm the result is contained within a known safe base (`resolved.is_relative_to(safe_base)`) BEFORE reading, writing, or globbing under it. Validation must happen after canonicalization — checking the raw string for `..` before resolving is defeated by symlinks and encoding tricks.

### Inline example (a): `PLUGIN_CACHE_PATH` environment trust

`extension_discovery.get_plugin_cache_path()` honors an explicit environment override:

```python
def get_plugin_cache_path() -> Path:
    env_path = os.environ.get('PLUGIN_CACHE_PATH')
    if env_path:
        return Path(env_path)
    return Path(get_bundle_cache_roots()[0]).expanduser()
```

The override path is read from the environment and turned into a `Path` with no validation, then handed to callers that descend into it to discover and **load** extension modules (`find_extension_path` → `load_extension_module`, which `exec_module`s the file). In a meta-project a consumer drives, `PLUGIN_CACHE_PATH` is an untrusted boundary: an attacker-controlled value can point discovery at an arbitrary directory whose `extension.py` is then executed. The secure shape is to treat the env value as untrusted — resolve it, confirm it is a directory contained within an expected cache-root location (or an explicitly allow-listed override root), and fail closed when it is not — rather than constructing the `Path` verbatim. This is an illustrative review target, not a filed finding.

## Unvalidated extension config-key handling

**Maps to:** CWE-20 (Improper Input Validation) · OWASP A03 Injection · ASVS V5

Extension data is **bundle-author-controlled, not core-controlled**. `get_skill_domains()` returns dicts whose `domain`, profile, and skill-notation strings flow into downstream filesystem, import, and dispatch operations. A value that is implicitly trusted because "it came from our own extension API" is still untrusted from core's perspective — a third-party or malformed bundle can return anything.

### Inline example (b): `domain`-key values from `get_skill_domains()`

`get_skill_domains_from_extensions()` copies each domain dict through and forwards it downstream:

```python
all_domains = module.get_skill_domains()
for domain_info in all_domains:
    if domain_info and domain_info.get('domain'):
        entry = dict(domain_info)
        entry['bundle'] = ext['bundle']
        domains.append(entry)
```

The only check is truthiness of the `domain` key — its *value* is never confirmed against the set of known domains. Downstream consumers that use that `domain` string to build a path, select a skill to load, or key a dispatch inherit whatever the extension returned. The secure shape is to validate each extension-provided `domain`/profile/notation against the declared allow-list of known domains and profiles before any downstream filesystem, import, or dispatch use, and to drop (fail closed) an entry whose key is not recognized. Inline example only — no lesson filing, no separate finding cross-reference.

## Review checklist

- Every `subprocess` call uses an argv list and `shell=False` (or quotes every interpolated value when a shell is unavoidable).
- Every `Path` built from environment, a CLI flag, or consumer-file content is resolved and confirmed contained in a safe base before use.
- Every `os.environ.get(...)` override that becomes a path/argv/target is validated, not trusted verbatim.
- Every extension-provided `domain`/profile/notation value is confirmed against the known allow-list before it reaches a filesystem, import, or dispatch sink.
- Boundary failures fail closed — the script rejects the value and surfaces an error, never coerces it through.
