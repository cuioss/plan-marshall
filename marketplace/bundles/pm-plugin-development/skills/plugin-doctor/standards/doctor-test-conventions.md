# Doctor Test Conventions Workflow

Test-tree conventions enforced as build-failing rules across the `test/` directory of any plan-marshall consumer. Activated by `scope=test-conventions`.

## Parameters

- `scope` (required): `test-conventions`
- `--test-root` (optional, default: `test/`): Path to the test tree being analyzed
- `--registry` (optional): Path to the validators registry. Defaults to the `## Rule 3 — Validator Registry` table in this document.

## Rules

All three rules emit findings with `severity: error`. The doctor runner exits non-zero when any error finding is recorded.

### unique-fixture-basenames

**Anchor**: `#unique-fixture-basenames`

Reject helper modules under the test tree whose basename collides across sibling directories OR matches a generic name with no domain prefix.

**Detection**:

1. Enumerate every `*.py` file under `--test-root` whose basename starts with `_` and ends with `.py`.
2. Flag any file whose basename is exactly `_fixtures.py`, `_helpers.py`, or `_common.py` (plain, no domain prefix).
3. Flag any pair of files in different directories whose basenames are identical (case-sensitive).

**Violation message format**:

```
{file_path}: helper module basename '{basename}' is generic — rename to '_<domain>_{basename}' to avoid pytest sys.modules collisions.
```

For collisions, the message names BOTH offending paths so the developer can choose which one to rename.

**Suggested remediation**: Rename the offending file to a domain-prefixed name (e.g., `_input_validation_fixtures.py`, `_plan_retrospective_fixtures.py`, `_manage_lessons_helpers.py`). Update every importer with the corresponding `from ._input_validation_fixtures import ...` rewrite.

**Why**: Pytest's default rootdir-based collection imports test-helper modules into `sys.modules` keyed by basename only. Two sibling test directories that both ship `_fixtures.py` race to register the name; whichever pytest collects second wins, and the loser's tests then import the wrong fixture surface or fail outright with `ImportError: while another module with the same name is already imported`. Lesson `2026-04-29-22-002` documents the original incident.

### subprocess-pythonpath

**Anchor**: `#subprocess-pythonpath`

Flag `subprocess.run([sys.executable, ...])` invocations under the test tree that fail to propagate `PYTHONPATH` from the parent pytest process.

**Detection**:

1. Parse every `*.py` file under `--test-root` with `ast.parse`.
2. Walk every `Call` node whose `func` resolves to `subprocess.run` (matched as `Attribute(Name("subprocess"), "run")` OR as a bare `Name("run")` when the file imports `from subprocess import run`).
3. Inspect the first positional argument:
   - If it is a `List` whose first element is `sys.executable` (matched as `Attribute(Name("sys"), "executable")`), the call is in-scope.
   - Otherwise, ignore the call.
4. For in-scope calls, check the `env` keyword:
   - If absent → violation.
   - If present, the value must build `PYTHONPATH` from `sys.path` (heuristic: `os.pathsep.join(sys.path)` assigned to `env["PYTHONPATH"]`, or a `dict(os.environ); d["PYTHONPATH"] = ...` shape).
5. Calls that route through `conftest.run_script(...)` are exempt (the helper sets `PYTHONPATH` from `_MARKETPLACE_SCRIPT_DIRS` internally).

**Violation message format**:

```
{file_path}:{lineno}: subprocess.run([sys.executable, ...]) without PYTHONPATH propagation — wrap via conftest.run_script(...) or add env={"PYTHONPATH": os.pathsep.join(sys.path), ...}.
```

**Suggested remediation**: Replace the bare `subprocess.run` call with `conftest.run_script(...)`. If `run_script` is unavailable for the call shape, build `env` explicitly:

```python
env = os.environ.copy()
env["PYTHONPATH"] = os.pathsep.join(sys.path)
result = subprocess.run([sys.executable, str(script_path), ...], env=env, ...)
```

**Why**: Subprocess invocations inherit a clean environment in CI runners. Without explicit `PYTHONPATH` propagation, sibling-skill imports fail with `ModuleNotFoundError` even though the test passes locally because pytest's `sys.path` configuration leaks into the parent shell. Lesson `2026-05-02-01-001` documents the original incident; the rule is AST-based so it survives whitespace and quoting variations.

### identifier-validator-corpus

**Anchor**: `#identifier-validator-corpus`

Validate that every registered identifier validator's regex round-trips every output line of its corresponding `manage-*:list` invocation.

**Detection**:

1. Read the validator registry (default: the `## Rule 3 — Validator Registry` table in this document).
2. For each `(validator_path, list_command)` pair:
   1. Read the regex literal from `validator_path` via AST inspection — locate the module-level constant (e.g., `LESSON_ID_REGEX = re.compile(r"...")`) and extract the pattern source. Do NOT execute the validator module.
   2. Run `list_command` and parse the IDs out of the TOON-shaped output (e.g., the `id:` lines).
   3. Compile the regex; for each ID, assert `regex.fullmatch(id) is not None`.
   4. Emit a finding for each ID the regex rejects.
3. An empty registry is a no-op (no findings, exit 0).

**Violation message format**:

```
{validator_path}: regex r'{pattern}' rejects ID '{id}' returned by `{list_command}` — anchor the regex against repository data.
```

**Suggested remediation**: Update the regex to match the rejected ID. Anchor every digit-width and segment count against the actual `manage-*:list` output, not against doc references or argparse `help=` text. Lesson `2026-04-29-10-001` documents the failure mode.

**Registry schema** (defined in the `## Rule 3 — Validator Registry` table below):

| Column | Type | Description |
|--------|------|-------------|
| `validator_path` | string | Path under `marketplace/bundles/` to the script defining the regex constant |
| `regex_constant` | string | Module-level constant name to extract via AST |
| `list_command` | string | Full executor command that produces the corpus (TOON output) |

## Rule 3 — Validator Registry

The empty-row template below is the default. Add new rows when authoring identifier validators that should be regex-vs-corpus checked.

| validator_path | regex_constant | list_command |
|----------------|----------------|--------------|
| _(empty — add registered pairs here)_ | _(constant name)_ | _(executor command)_ |

When the registry is empty, the rule reports zero findings and exits 0. The rule fires only against entries explicitly listed.

## Severity Summary

| Rule anchor | Severity | Default behavior |
|-------------|----------|------------------|
| `#unique-fixture-basenames` | error | exit ≠ 0 on violation |
| `#subprocess-pythonpath` | error | exit ≠ 0 on violation |
| `#identifier-validator-corpus` | error | exit ≠ 0 on violation |

All three rules ship with build-failing severity matching the existing doctor rule infrastructure. Suppression is not provided — the violations correspond to recurring failure modes documented in lessons learned.
