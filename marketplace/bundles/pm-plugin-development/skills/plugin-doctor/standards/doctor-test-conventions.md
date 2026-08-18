# Doctor Test Conventions Workflow

Test-tree conventions enforced across the `test/` directory of any plan-marshall consumer. Activated by `scope=test-conventions`. Four rules are build-failing (`error`); three report structural house-style violations at `warning` until their own violation counts reach zero — see the Severity Summary.

## Parameters

- `scope` (required): `test-conventions`
- `--test-root` (optional, default: `test/`): Path to the test tree being analyzed
- `--registry` (optional): Path to the validators registry. Defaults to the `## Rule 3 — Validator Registry` table in this document.

## Rules

The scope carries rules at two severities, and the split is deliberate:

- **`severity: error`** — `unique-fixture-basenames`, `subprocess-pythonpath`, `identifier-validator-corpus`, `test-helper-module-misnamed`. The doctor runner exits non-zero when any error finding is recorded.
- **`severity: warning`** — `test-module-line-budget`, `test-module-preamble-boilerplate`, `test-docstring-historical-prose`. These report their counts without failing the caller.

The warning rules ship at that severity because the tree still violates them at scale. A build-failing rule landed over a non-compliant tree fails every subsequent build until the tree complies — which would block the very work that would make it comply. `status` is therefore derived from **error-severity findings only**.

The severity is **per rule and conditional, not permanent**: each warning rule is flipped to `error` once its own violation count reaches zero. `test-helper-module-misnamed` is the first to have made that transition — its single violation was remediated exactly as the rule prescribes, so it now guards a clean tree rather than describing a non-compliant one.

### unique-fixture-basenames

**Anchor**: `#unique-fixture-basenames`

Reject helper modules under the test tree whose basename collides across sibling directories OR matches a generic name with no domain prefix.

**Detection**:

1. Enumerate every `*.py` file under `--test-root` whose basename starts with `_` and ends with `.py`.
2. Flag any file whose basename is exactly `_fixtures.py`, `_helpers.py`, or `_common.py` (plain, no domain prefix).
3. Flag any pair of files in different directories whose basenames are identical (case-sensitive).

**Violation message format**:

```text
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

```text
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

```text
{validator_path}: regex r'{pattern}' rejects ID '{id}' returned by `{list_command}` — anchor the regex against repository data.
```

**Suggested remediation**: Update the regex to match the rejected ID. Anchor every digit-width and segment count against the actual `manage-*:list` output, not against doc references or argparse `help=` text. Lesson `2026-04-29-10-001` documents the failure mode.

**Registry schema** (defined in the `## Rule 3 — Validator Registry` table below):

| Column | Type | Description |
|--------|------|-------------|
| `validator_path` | string | Path under `marketplace/bundles/` to the script defining the regex constant |
| `regex_constant` | string | Module-level constant name to extract via AST |
| `list_command` | string | Full executor command that produces the corpus (TOON output) |

### test-module-line-budget

**Anchor**: `#test-module-line-budget`

Flag a collected test module over the 400-line budget.

**Detection**:

1. Enumerate every `*.py` under `--test-root` matching pytest's collection patterns (`test_*.py` / `*_test.py`).
2. Count the module's lines.
3. Flag any module over `TEST_MODULE_LINE_BUDGET` (400).

**Violation message format**:

```text
{file_path}: test module is {n} lines, over the 400-line budget (by {n-400}) — split by behaviour cluster into test_{unit}_{cluster}.py, not in arbitrary halves.
```

The message carries the module's own line count and the budget, so the overage is readable without re-measuring.

**Suggested remediation**: Split by behaviour cluster into `test_{unit}_{cluster}.py` — one nameable subject per module. Do not split in arbitrary halves: that leaves one subject spread across two files and neither module describable, so the next author cannot tell which half a new test belongs in.

**Why**: The budget is derived from the corpus rather than invented — the median module measures ~327 lines, so 400 sits above the median and describes the tree's own compliant majority. It replaces a `~200` figure that roughly three quarters of the corpus violated and that no guard ever enforced; a rule the tree violates at that rate is a number readers learn to ignore. The authoring standard is `plan-marshall:persona-module-tester` § "Module Budget: 400 lines".

### test-helper-module-misnamed

**Anchor**: `#test-helper-module-misnamed`

Flag a module that matches pytest's collection patterns but declares no test.

**Detection**:

1. Enumerate every `*.py` under `--test-root` matching `test_*.py` / `*_test.py`.
2. Parse with `ast.parse`.
3. Flag any module declaring neither a function whose name starts with `test` nor a class whose name starts with `Test`.

**Violation message format**:

```text
{file_path}: module '{basename}' matches pytest's collection patterns but declares no test function or Test* class — it is collected, contributes nothing, and is invisible in the run; rename to _<domain>_fixtures.py.
```

**Suggested remediation**: Rename to `_{domain}_fixtures.py`, outside the collection patterns, and update every importer.

**Why**: Such a module is collected by pytest, contributes zero tests, and reports nothing — it reads as covered while asserting nothing. The naming convention that keeps helpers out of collection is `plan-marshall:persona-module-tester` § "Test Helper Module Organization"; this rule catches the case where a helper was given a collected name.

### test-module-preamble-boilerplate

**Anchor**: `#test-module-preamble-boilerplate`

Flag hand-rolled import preambles that resolve a module by the test file's own location.

**Detection**:

1. Parse every `*.py` under `--test-root` with `ast.parse`.
2. Flag any `spec_from_file_location` call (matched as an attribute access or a bare name, so both import forms are caught).
3. Flag any `Path(__file__)` followed by a directory-counting hop of depth **three or more**, in either spelling:
   - a `.parent` chain (`Path(__file__).parent.parent.parent`). Only the outermost `.parent` attribute of a chain is reported, so one chain yields one finding rather than one per link.
   - an indexed `parents[N]` access (`Path(__file__).resolve().parents[3]`).

   Path-preserving calls between the two — `.resolve()`, `.absolute()`, `.expanduser()` — do not break the chain, since they return an equivalent path. The two spellings **compose**: `Path(__file__).parent.parents[2]` counts 3. A `parents[...]` index that is negative or not a literal integer is not a directory count and is not flagged.

   **Both spellings are measured on the same scale deliberately.** They are the same idiom with the same brittleness, and covering only one would make the rule's own count gameable: a module could clear its finding by respelling `.parent.parent.parent` as `parents[3]` while changing nothing. That matters because the flip from `warning` to `error` is conditioned on the count reaching zero.

**Violation message format**:

```text
{file_path}:{lineno}: hand-rolled spec_from_file_location preamble — use conftest.load_script_module(bundle, skill, filename) for a module under scripts/, or conftest.load_skill_module(bundle, skill, filename, module_name) for one at the skill root (every bundle ships an extension.py, so pass a distinct module_name — or register=False — or they displace each other); both resolve by identity instead of by the test file's own location.
{file_path}:{lineno}: Path(__file__) followed by a {depth}-deep .parent chain — use conftest.get_scripts_dir(bundle, skill), or conftest.get_skill_dir(bundle, skill) for a skill that ships no scripts/ directory; a directory-counting chain breaks the moment the test module moves.
```

**Suggested remediation**: Replace with the `conftest` helpers, which resolve by `(bundle, skill, file)` identity rather than by location. `load_script_module(bundle, skill, filename)` / `get_scripts_dir(bundle, skill)` address the skill's `scripts/` subtree; `load_skill_module(bundle, skill, filename, module_name)` / `get_skill_dir(bundle, skill)` address the skill root, which is where a bundle's `plan-marshall-plugin` `extension.py` lives — most such skills ship no `scripts/` directory, so the scripts-relative pair cannot reach them. Pass a distinct `module_name` (or `register=False`) for that shape: every bundle ships its extension under the same filename, so the default `sys.modules` name is `extension` for all of them and each load displaces the last.

**One known-legitimate occurrence.** The rule fires on `test/conftest.py`'s own `_exec_module_from_path`, the construction both sanctioned loaders share, whose `spec_from_file_location` call *is* the helper the message points at — the suggested remediation there is circular. It ships unsuppressed on purpose: at `warning` severity one structurally-unfixable finding is cheaper than a path allowlist, which would also silence genuine defects elsewhere in the same file.

**Why**: Both shapes hard-code the test module's position in the directory tree. Moving the file — which the line-budget rule above actively encourages — silently breaks the resolution, and the failure surfaces as an import error far from its cause. Resolution by identity survives the move.

### test-docstring-historical-prose

**Anchor**: `#test-docstring-historical-prose`

Flag a docstring or comment under the test tree citing a lesson id, a PR reference, or a plan/deliverable id.

**Detection**:

1. Parse every `*.py` under `--test-root` with `ast.parse`.
2. Collect the prose segments — module, class, and function **docstrings** (via `ast.get_docstring`), plus every `#` **comment** (via `tokenize`).
3. Match each segment against the citation patterns. The lesson-id and `plan-marshall#NNNN` matchers are **imported from** `_analyze_lesson_id_in_skill_prose` and `_analyze_incident_reference_in_docs` rather than restated — one textual shape, one matcher. Two shapes those analyzers do not carry are defined locally: PR references (`PR #NNN` / `pull request #NNN`, and a bare `#NN` carrying at least two digits), and plan/deliverable ids (`TASK-NNN`, `deliverable D<n>` and `deliverable <n>` alike, ``plan `slug` ``).
4. Skip any match that sits inside an **inline literal** — a `` `…` `` / ` ``…`` ` code span, or a single- or double-quoted string — because prose in that position is naming a value, not citing a record.
5. Emit at most one finding per segment; `details.kind` names which citation shape fired.

**Two discriminators, and the rule is unusable without both.**

The first is **prose-vs-data**, and it is structural rather than an optimisation. The scan deliberately never reaches string literals used as data. The same textual shapes appear far more often as test *data* — a lesson id fed to the validator under test is the corpus the test exists to check — and flagging those would make the rule unusable. Measured over this tree with the shipped matchers: **286** prose segments carry at least one citation outside an inline literal — which is the rule's own finding count, since it emits at most one finding per segment — against **955** non-docstring string-literal constants carrying the same shapes, every one of which the AST scoping leaves alone. Both are re-derivable by walking `test/**/*.py`, feeding each `_iter_prose_segments` result to `_first_bare_match` over `_HISTORICAL_PROSE_PATTERNS` for the first figure, and matching the same patterns against every non-docstring `ast.Constant` string for the second.

The second runs **inside prose**, because scoping to prose is not enough: prose has to name values as well as cite records. A docstring stating that a generator returns a particular id, or a comment naming the task file a command creates, states the contract under test — it cites nothing. Shape cannot separate the two, but **formatting can**: an identifier named as a value is written in an inline literal, while a citation appears bare in the narrative. Hence the convention this rule teaches — **backtick the value you name** — and the exemption at detection step 4.

The exemption is **per occurrence, not per segment**: a docstring that names a value and cites a record still reports the citation, so backticking one identifier cannot launder the rest of the sentence.

Applied to one measured slice, this is the difference between a usable rule and an ignored one: over the ten `plan-marshall` plan-state directories, 24 findings survived a full citation strip, and **22 of them were id-shaped *values*** — an expected return, a seeded fixture filename, an ordering key, a created task file. The other two were genuine citations the strip had missed. So the residue was overwhelmingly, but not entirely, false positives; the two real ones were rewritten rather than exempted.

**Violation message format**:

```text
{file_path}:{lineno}: historical citation '{matched}' in test prose — a docstring states the invariant in the present tense, not the incident that produced the test.
```

**Suggested remediation**: Rewrite the docstring to state the invariant in the present tense. Where the invariant is genuinely non-obvious, a second paragraph explains *why it is load-bearing* — which stays true after the next refactor, unlike the citation. See `plan-marshall:persona-module-tester` § "Test Docstring Content" for a worked before/after.

**Why**: This is `CLAUDE.md` § Documentation Standards ("No version history", "Current state only") applied to a tree those standards were never scoped over. It is the same rule the `no-historical-prose-in-skills`, `no-incident-references`, and `no-lesson-id-in-skill-prose` rules already enforce across `marketplace/bundles/**` — this rule extends the identical detection to `test/`, where nothing previously enforced it. A citation reasons from something the reader cannot see: it costs context on every read and teaches the reader to reason from a PR number instead of from the mechanism in front of them.

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
| `#test-module-line-budget` | warning | reported; does not affect exit code |
| `#test-helper-module-misnamed` | **error** | exit ≠ 0 on violation — count reached zero, so the rule now guards a clean tree |
| `#test-module-preamble-boilerplate` | warning | reported; does not affect exit code |
| `#test-docstring-historical-prose` | warning | reported; does not affect exit code |

The four `error` rules ship with build-failing severity matching the existing doctor rule infrastructure. Suppression is not provided for them — the violations correspond to recurring failure modes documented in lessons learned.

The three `warning` rules report without failing the caller: `status` is derived from error-severity findings only, so `warning_count` can be non-zero while `status: pass`. They ship at `warning` because the tree still violates them at scale, and a build-failing rule landed over a non-compliant tree fails every subsequent build until the tree complies — blocking the very work that would make it comply. **The flip to `error` is per rule and conditioned on that rule's own violation count reaching zero**, not a permanent classification — `test-helper-module-misnamed` has already made that transition.

This scope is **not** part of the `quality-gate` subcommand; it runs on demand via `doctor-marketplace.py test-conventions --test-root {path}`.
