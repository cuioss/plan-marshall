#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Test-tree conventions analyzer for plugin-doctor.

Hosts the rules documented in `standards/doctor-test-conventions.md`:

- analyze_unique_fixture_basenames    -- Rule 1 (severity: error)
- analyze_subprocess_pythonpath       -- Rule 2 (severity: error)
- analyze_validator_regex_vs_corpus   -- Rule 3 (severity: error)
- analyze_test_module_line_budget     -- Rule 4 (severity: warning)
- analyze_test_helper_module_misnamed -- Rule 5 (severity: error)
- analyze_test_module_preamble        -- Rule 6 (severity: warning)
- analyze_test_docstring_prose        -- Rule 7 (severity: warning)

Rules 4-7 are the structural half of the house style stated in
`plan-marshall:persona-module-tester` and `pm-dev-python:pytest-testing`.

Rules 4, 6 and 7 ship at ``warning`` because the tree still violates them at
scale: a build-failing rule landed over a non-compliant tree would fail every
subsequent build until the reduction work completes. Each is flipped to
``error`` once its own violation count reaches zero.

Rule 5 (``test-helper-module-misnamed``) has reached that point and ships at
``error``. Its single violation was remediated exactly as the rule prescribes —
a collected module carrying no test renamed to a ``_{domain}_fixtures.py``
helper — so the rule now guards a clean tree rather than describing a
non-compliant one.

Each rule returns a list of finding dicts in the standard plugin-doctor shape
(type, rule_id, file, line, severity, fixable, description, details).
"""

from __future__ import annotations

import ast
import io
import re
import shlex
import subprocess
import tokenize
from collections import defaultdict
from pathlib import Path

from _analyze_incident_reference_in_docs import _PLAN_MARSHALL_REF_RE
from _analyze_lesson_id_in_skill_prose import _LESSON_BACKTICK_ID_RE, _LESSON_ID_RE
from _doctor_shared import Finding
from _rule_registry import RuleDescriptor

# Test-tree convention rules (cmd_test_conventions). Rules 1-3 and rule 5 are
# build-failing; rules 4, 6 and 7 report at warning severity until their own
# violation counts reach zero.
RULE_DESCRIPTORS = [
    RuleDescriptor(rule_id='unique-fixture-basenames', severity='error', category='structural', scope='corpus-relational'),
    RuleDescriptor(rule_id='subprocess-pythonpath', severity='error', category='structural', scope='corpus-relational'),
    RuleDescriptor(
        rule_id='identifier-validator-corpus',
        severity='error',
        category='structural',
        scope='corpus-relational',
    ),
    RuleDescriptor(rule_id='test-module-line-budget', severity='warning', category='structural', scope='file-local'),
    RuleDescriptor(rule_id='test-helper-module-misnamed', severity='error', category='structural', scope='file-local'),
    RuleDescriptor(rule_id='test-module-preamble-boilerplate', severity='warning', category='structural', scope='file-local'),
    RuleDescriptor(rule_id='test-docstring-historical-prose', severity='warning', category='content', scope='file-local'),
]

GENERIC_HELPER_BASENAMES = frozenset({'_fixtures.py', '_helpers.py', '_common.py'})

ID_LINE_PATTERN = re.compile(r'^\s*(?:- )?id:\s*(?P<id>\S+)\s*$', re.MULTILINE)

# --- Rule 4 -----------------------------------------------------------------

#: Module line budget. Derived above the corpus median (~327 lines) so it
#: describes the tree's own compliant majority rather than an aspiration.
TEST_MODULE_LINE_BUDGET = 400

# --- Rule 6 -----------------------------------------------------------------

#: ``Path(__file__).parent.parent.parent`` and deeper. A chain this long is
#: resolving the repository root by counting directories from the test file's
#: own location, which breaks the moment the file moves.
PARENT_CHAIN_MIN_DEPTH = 3

# --- Rule 7 -----------------------------------------------------------------
#
# The lesson-id and plan-marshall-reference matchers are imported from the two
# analyzers that already detect this prose over ``marketplace/bundles/**``
# rather than restated here: one textual shape, one matcher. Only the two
# shapes those analyzers do not carry are defined locally.

#: ``PR #123`` / ``pull request #123`` and the bare ``#123`` — the incident
#: analyzer detects ``plan-marshall#123`` but neither of these spellings, and
#: both occur in this repository's test prose.
#:
#: ⛔ The bare alternative is bounded on three sides, and every bound answers a
#: false positive a cold read of this corpus actually returned:
#:
#: 1. ``(?<![\w#\-])`` rejects a preceding word character, ``#``, or hyphen. The
#:    word-character half keeps the bare alternative off ``plan-marshall#123``,
#:    which the reference analyzer already owns. The hyphen half keeps it off a
#:    compound token that embeds a number — ``pre-#812`` is a schema-state
#:    literal the corpus asserts on, not a citation of 812.
#:
#:    ⛔ It is a NEGATIVE lookbehind, so it SUCCEEDS at position 0, and that is
#:    deliberate: a docstring may open with its citation, and a lookbehind
#:    demanding a preceding character would silence exactly those. The comment
#:    case that motivates a start-of-segment bound is handled where it belongs
#:    instead — :func:`_iter_prose_segments` strips a comment's ``#`` delimiter,
#:    so ``#123 note`` reaches the matchers as ``123 note`` and offers no ``#``.
#: 2. ``\d{2,}`` — the BARE form requires at least two digits. A one-digit
#:    ``#1`` is overwhelmingly intra-document enumeration ("mis-attribution
#:    #1"), not a record id. This bound is affordable precisely because it is
#:    local to the bare form: an unambiguous ``PR #7`` still matches through the
#:    first alternative, which carries no digit bound.
#: 3. ``\b`` after the digits keeps it off an identifier that merely starts with
#:    digits.
_PR_REFERENCE_RE = re.compile(
    r'\b(?:PR|pull request)\s*#\d+|(?<![\w#\-])#\d{2,}\b',
    re.IGNORECASE,
)

#: Plan and deliverable identifiers: ``TASK-001``, ``deliverable D3``,
#: ``Deliverable 2``, ``plan `some-plan-slug` ``.
#:
#: The ``D`` is optional because both spellings occur: the ordinal is the
#: citation whether or not the author wrote the letter, and a rule that matched
#: only the lettered form would report one half of a corpus that writes both.
_PLAN_DELIVERABLE_ID_RE = re.compile(
    r'\bTASK-\d{3}\b|\bdeliverable\s+D?\d+\b|\bplan\s+`[a-z0-9][a-z0-9-]{4,}`',
    re.IGNORECASE,
)

#: (kind, pattern) pairs. ``kind`` lands in the finding details so a consumer
#: can tell which citation shape fired without re-matching.
_HISTORICAL_PROSE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ('lesson_id', _LESSON_ID_RE),
    ('lesson_id_backtick', _LESSON_BACKTICK_ID_RE),
    ('plan_marshall_ref', _PLAN_MARSHALL_REF_RE),
    ('pr_reference', _PR_REFERENCE_RE),
    ('plan_deliverable_id', _PLAN_DELIVERABLE_ID_RE),
]


def _iter_helper_modules(test_root: Path) -> list[Path]:
    """Return every ``_*.py`` file under ``test_root`` excluding ``__init__``-style files."""
    if not test_root.is_dir():
        return []
    results: list[Path] = []
    for path in test_root.rglob('_*.py'):
        if not path.is_file():
            continue
        if path.name.startswith('__'):
            continue
        results.append(path)
    return results


def analyze_unique_fixture_basenames(test_root: Path) -> list[dict]:
    """Rule 1 -- unique fixture-module basenames.

    Flags two distinct violation classes within ``test_root``:

    1. Files whose basename matches a generic helper name with no domain prefix
       (``_fixtures.py``, ``_helpers.py``, ``_common.py``).
    2. Cross-directory basename collisions where two helper modules in
       different directories share the same basename. Both offending files
       are reported so the developer can choose which to rename.

    Each finding follows the standard plugin-doctor shape used by
    ``_doctor_analysis``.
    """
    findings: list[dict] = []
    helper_modules = _iter_helper_modules(test_root)

    by_basename: dict[str, list[Path]] = defaultdict(list)
    for path in helper_modules:
        by_basename[path.name].append(path)

    seen_files: set[Path] = set()

    for path in helper_modules:
        if path.name in GENERIC_HELPER_BASENAMES:
            findings.append(_build_generic_basename_finding(path))
            seen_files.add(path)

    for basename, paths in by_basename.items():
        if len(paths) <= 1:
            continue
        for path in paths:
            if path in seen_files:
                continue
            other_paths = sorted(other for other in paths if other != path)
            findings.append(_build_collision_finding(path, basename, other_paths))
            seen_files.add(path)

    findings.sort(key=lambda f: (f['file'], f['type']))
    return findings


def _build_generic_basename_finding(path: Path) -> dict:
    description = (
        f"helper module basename '{path.name}' is generic — rename to "
        f"'_<domain>_{path.name[1:]}' to avoid pytest sys.modules collisions"
    )
    return Finding(
        type='unique-fixture-basenames',
        file=str(path),
        line=1,
        severity='error',
        fixable=False,
        rule_id='unique-fixture-basenames',
        description=description,
        details={
            'kind': 'generic_basename',
            'basename': path.name,
            'standard_anchor': 'doctor-test-conventions.md#unique-fixture-basenames',
        },
    ).to_dict()


def analyze_subprocess_pythonpath(test_root: Path) -> list[dict]:
    """Rule 2 -- subprocess.run PYTHONPATH propagation.

    AST scan of every ``*.py`` under ``test_root`` for ``subprocess.run``
    calls whose first positional argument is a list starting with
    ``sys.executable``. Such calls MUST either route through
    ``conftest.run_script(...)`` or pass an ``env=`` keyword that propagates
    ``PYTHONPATH`` from ``sys.path``. Calls missing both safeguards are
    flagged.
    """
    if not test_root.is_dir():
        return []

    findings: list[dict] = []
    for path in test_root.rglob('*.py'):
        if not path.is_file():
            continue
        if path.name.startswith('__'):
            continue
        try:
            source = path.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue
        bare_run_imported = _imports_bare_run(tree)
        for finding in _scan_module_for_subprocess_pythonpath(path, tree, bare_run_imported):
            findings.append(finding)
    findings.sort(key=lambda f: (f['file'], f.get('line', 0)))
    return findings


def _imports_bare_run(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == 'subprocess':
            for alias in node.names:
                if alias.name == 'run':
                    return True
    return False


def _scan_module_for_subprocess_pythonpath(path: Path, tree: ast.AST, bare_run_imported: bool) -> list[dict]:
    results: list[dict] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not _is_subprocess_run_call(node, bare_run_imported):
            continue
        if not _first_arg_is_sys_executable_list(node):
            continue
        if _is_run_script_call(node):
            continue
        if _has_pythonpath_env_kwarg(node):
            continue
        results.append(_build_subprocess_pythonpath_finding(path, node))
    return results


def _is_subprocess_run_call(node: ast.Call, bare_run_imported: bool) -> bool:
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr == 'run':
        value = func.value
        if isinstance(value, ast.Name) and value.id == 'subprocess':
            return True
    if bare_run_imported and isinstance(func, ast.Name) and func.id == 'run':
        return True
    return False


def _first_arg_is_sys_executable_list(node: ast.Call) -> bool:
    if not node.args:
        return False
    first = node.args[0]
    if not isinstance(first, ast.List) or not first.elts:
        return False
    head = first.elts[0]
    return (
        isinstance(head, ast.Attribute)
        and head.attr == 'executable'
        and isinstance(head.value, ast.Name)
        and head.value.id == 'sys'
    )


def _is_run_script_call(node: ast.Call) -> bool:
    """Return True when the call routes through conftest.run_script."""
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr == 'run_script':
        return True
    if isinstance(func, ast.Name) and func.id == 'run_script':
        return True
    return False


def _has_pythonpath_env_kwarg(node: ast.Call) -> bool:
    """Heuristic: env= kwarg whose value introduces PYTHONPATH from sys.path."""
    env_value = None
    for kw in node.keywords:
        if kw.arg == 'env':
            env_value = kw.value
            break
    if env_value is None:
        return False

    # env=existing_env_var (e.g., env=env). Trust prior assignment if the
    # name appears in scope; we cannot reason about it statically without
    # a full data-flow pass, so accept it conservatively when the symbol
    # name strongly implies env construction.
    if isinstance(env_value, ast.Name) and env_value.id in {'env', 'subprocess_env', 'child_env'}:
        return True

    # env={"PYTHONPATH": ..., **os.environ} dict literal
    if isinstance(env_value, ast.Dict):
        for key in env_value.keys:
            if isinstance(key, ast.Constant) and key.value == 'PYTHONPATH':
                return True

    # env=os.environ.copy() | {"PYTHONPATH": ...} (BinOp dict-merge in 3.9+)
    if isinstance(env_value, ast.BinOp) and isinstance(env_value.op, ast.BitOr):
        for side in (env_value.left, env_value.right):
            if isinstance(side, ast.Dict):
                for key in side.keys:
                    if isinstance(key, ast.Constant) and key.value == 'PYTHONPATH':
                        return True

    return False


def _build_subprocess_pythonpath_finding(path: Path, node: ast.Call) -> dict:
    description = (
        'subprocess.run([sys.executable, ...]) without PYTHONPATH propagation — '
        "wrap via conftest.run_script(...) or add env={'PYTHONPATH': os.pathsep.join(sys.path), ...}"
    )
    return Finding(
        type='subprocess-pythonpath',
        file=str(path),
        line=getattr(node, 'lineno', 1),
        severity='error',
        fixable=False,
        rule_id='subprocess-pythonpath',
        description=description,
        details={
            'standard_anchor': 'doctor-test-conventions.md#subprocess-pythonpath',
        },
    ).to_dict()


def analyze_validator_regex_vs_corpus(registry: list[dict], project_root: Path | None = None) -> list[dict]:
    """Rule 3 -- identifier-validator regex round-trips real corpus.

    For every entry in ``registry``, extract the regex literal from
    ``validator_path`` via AST, run ``list_command`` via subprocess, parse
    IDs from the TOON output, and assert that the regex fullmatches every
    extracted ID. An empty registry is a no-op.

    Each registry entry is a dict with keys ``validator_path``,
    ``regex_constant``, and ``list_command``. ``project_root`` defaults to
    the current working directory and is the cwd used to spawn
    ``list_command``.
    """
    if not registry:
        return []

    cwd = project_root or Path.cwd()
    findings: list[dict] = []

    for entry in registry:
        validator_path = Path(entry['validator_path'])
        regex_constant = entry['regex_constant']
        list_command = entry['list_command']

        if not validator_path.is_absolute():
            validator_path = (cwd / validator_path).resolve()

        if not validator_path.is_file():
            findings.append(_build_corpus_error_finding(validator_path, regex_constant, list_command, 'validator_not_found'))
            continue

        regex_pattern = _extract_regex_pattern(validator_path, regex_constant)
        if regex_pattern is None:
            findings.append(_build_corpus_error_finding(validator_path, regex_constant, list_command, 'regex_constant_not_found'))
            continue

        try:
            compiled = re.compile(regex_pattern)
        except re.error as exc:
            findings.append(_build_corpus_error_finding(validator_path, regex_constant, list_command, f'regex_compile_error:{exc}'))
            continue

        try:
            corpus_output = _run_list_command(list_command, cwd)
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or '').strip().splitlines()[-1] if exc.stderr else 'no stderr'
            findings.append(_build_corpus_error_finding(validator_path, regex_constant, list_command, f'list_command_failed:{stderr}'))
            continue

        ids = _extract_ids_from_corpus(corpus_output)
        if not ids:
            findings.append(_build_corpus_error_finding(validator_path, regex_constant, list_command, 'no_ids_in_corpus'))
            continue

        for identifier in ids:
            if compiled.fullmatch(identifier) is None:
                findings.append(_build_corpus_finding(validator_path, regex_pattern, list_command, identifier))

    return findings


def _extract_regex_pattern(validator_path: Path, regex_constant: str) -> str | None:
    """Read the regex literal assigned to ``regex_constant`` via AST."""
    try:
        source = validator_path.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return None
    try:
        tree = ast.parse(source, filename=str(validator_path))
    except SyntaxError:
        return None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == regex_constant for target in node.targets):
            continue
        return _resolve_regex_value(node.value)
    return None


def _resolve_regex_value(value: ast.expr) -> str | None:
    """Pull a string-literal pattern out of common regex constant shapes."""
    if isinstance(value, ast.Constant) and isinstance(value.value, str):
        return value.value
    if isinstance(value, ast.Call):
        # re.compile(r"...") / re.compile(r"...", flags)
        if value.args and isinstance(value.args[0], ast.Constant) and isinstance(value.args[0].value, str):
            return value.args[0].value
    return None


def _run_list_command(list_command: str, cwd: Path) -> str:
    args = shlex.split(list_command)
    completed = subprocess.run(  # noqa: S603 - registry-controlled command
        args, capture_output=True, text=True, cwd=str(cwd), check=True, timeout=30
    )
    return completed.stdout


def _extract_ids_from_corpus(corpus_output: str) -> list[str]:
    matches = [match.group('id').strip().strip('"') for match in ID_LINE_PATTERN.finditer(corpus_output)]
    return [m for m in matches if m]


def _build_corpus_finding(validator_path: Path, pattern: str, list_command: str, identifier: str) -> dict:
    description = (
        f"regex r'{pattern}' rejects ID '{identifier}' returned by `{list_command}` — "
        'anchor the regex against repository data'
    )
    return Finding(
        type='identifier-validator-corpus',
        file=str(validator_path),
        line=1,
        severity='error',
        fixable=False,
        rule_id='identifier-validator-corpus',
        description=description,
        details={
            'pattern': pattern,
            'list_command': list_command,
            'rejected_id': identifier,
            'standard_anchor': 'doctor-test-conventions.md#identifier-validator-corpus',
        },
    ).to_dict()


def _build_corpus_error_finding(validator_path: Path, regex_constant: str, list_command: str, reason: str) -> dict:
    description = (
        f"identifier-validator-corpus check failed for {validator_path.name} "
        f"({regex_constant} via `{list_command}`) — reason: {reason}"
    )
    return Finding(
        type='identifier-validator-corpus',
        file=str(validator_path),
        line=1,
        severity='error',
        fixable=False,
        rule_id='identifier-validator-corpus',
        description=description,
        details={
            'regex_constant': regex_constant,
            'list_command': list_command,
            'reason': reason,
            'standard_anchor': 'doctor-test-conventions.md#identifier-validator-corpus',
        },
    ).to_dict()


def _build_collision_finding(path: Path, basename: str, other_paths: list[Path]) -> dict:
    others_repr = ', '.join(str(other) for other in other_paths)
    description = (
        f"helper module basename '{basename}' collides with sibling test "
        f"directories ({others_repr}) — pytest sys.modules will register "
        f"only one; rename one or both to a domain-prefixed name"
    )
    return Finding(
        type='unique-fixture-basenames',
        file=str(path),
        line=1,
        severity='error',
        fixable=False,
        rule_id='unique-fixture-basenames',
        description=description,
        details={
            'kind': 'cross_directory_collision',
            'basename': basename,
            'colliding_with': [str(other) for other in other_paths],
            'standard_anchor': 'doctor-test-conventions.md#unique-fixture-basenames',
        },
    ).to_dict()


# ---------------------------------------------------------------------------
# Shared traversal helpers for the file-local test-tree rules (4-7)
# ---------------------------------------------------------------------------


def _iter_test_tree_modules(test_root: Path) -> list[Path]:
    """Return every ``*.py`` under ``test_root``, excluding dunder modules."""
    if not test_root.is_dir():
        return []
    return [path for path in sorted(test_root.rglob('*.py')) if path.is_file() and not path.name.startswith('__')]


def _is_collected_module(path: Path) -> bool:
    """Return True when pytest's default collection patterns match ``path``."""
    return path.name.startswith('test_') or path.name.endswith('_test.py')


def _read_source(path: Path) -> str | None:
    """Read ``path``, returning None when it cannot be read."""
    try:
        return path.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return None


# ---------------------------------------------------------------------------
# Rule 4 -- test-module-line-budget
# ---------------------------------------------------------------------------


def analyze_test_module_line_budget(test_root: Path, budget: int = TEST_MODULE_LINE_BUDGET) -> list[dict]:
    """Rule 4 -- flag a collected test module over the line budget.

    A module over budget is split by behaviour cluster into
    ``test_{unit}_{cluster}.py``. The finding carries the module's own line
    count and the budget so the message states the overage rather than
    merely naming the rule.
    """
    findings: list[dict] = []
    for path in _iter_test_tree_modules(test_root):
        if not _is_collected_module(path):
            continue
        source = _read_source(path)
        if source is None:
            continue
        line_count = len(source.splitlines())
        if line_count > budget:
            findings.append(_build_line_budget_finding(path, line_count, budget))
    return findings


def _build_line_budget_finding(path: Path, line_count: int, budget: int) -> dict:
    description = (
        f'test module is {line_count} lines, over the {budget}-line budget '
        f'(by {line_count - budget}) — split by behaviour cluster into '
        f'test_{{unit}}_{{cluster}}.py, not in arbitrary halves'
    )
    return Finding(
        type='test-module-line-budget',
        file=str(path),
        line=1,
        severity='warning',
        fixable=False,
        rule_id='test-module-line-budget',
        description=description,
        details={
            'line_count': line_count,
            'budget': budget,
            'over_by': line_count - budget,
            'standard_anchor': 'doctor-test-conventions.md#test-module-line-budget',
        },
    ).to_dict()


# ---------------------------------------------------------------------------
# Rule 5 -- test-helper-module-misnamed
# ---------------------------------------------------------------------------


def analyze_test_helper_module_misnamed(test_root: Path) -> list[dict]:
    """Rule 5 -- flag a collected module that declares no test.

    A module matching pytest's collection patterns (``test_*.py`` /
    ``*_test.py``) that declares neither a ``test*`` function nor a ``Test*``
    class is collected, contributes nothing, and is invisible in the run: it
    reads as covered while asserting nothing. Such a module is a helper and
    belongs under a ``_{domain}_fixtures.py`` name, outside the collection
    patterns.
    """
    findings: list[dict] = []
    for path in _iter_test_tree_modules(test_root):
        if not _is_collected_module(path):
            continue
        source = _read_source(path)
        if source is None:
            continue
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue
        if not _declares_any_test(tree):
            findings.append(_build_helper_misnamed_finding(path))
    return findings


def _declares_any_test(tree: ast.AST) -> bool:
    """Return True when the module declares a pytest-collectable test."""
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) and node.name.startswith('test'):
            return True
        if isinstance(node, ast.ClassDef) and node.name.startswith('Test'):
            return True
    return False


def _build_helper_misnamed_finding(path: Path) -> dict:
    description = (
        f"module '{path.name}' matches pytest's collection patterns but declares no test "
        f'function or Test* class — it is collected, contributes nothing, and is invisible '
        f'in the run; rename to _<domain>_fixtures.py'
    )
    return Finding(
        type='test-helper-module-misnamed',
        file=str(path),
        line=1,
        severity='error',
        fixable=False,
        rule_id='test-helper-module-misnamed',
        description=description,
        details={
            'basename': path.name,
            'standard_anchor': 'doctor-test-conventions.md#test-helper-module-misnamed',
        },
    ).to_dict()


# ---------------------------------------------------------------------------
# Rule 6 -- test-module-preamble-boilerplate
# ---------------------------------------------------------------------------


def analyze_test_module_preamble(test_root: Path) -> list[dict]:
    """Rule 6 -- flag hand-rolled import preambles under the test tree.

    Two shapes are flagged, both of which resolve a module by the test file's
    own location rather than by identity:

    1. A ``spec_from_file_location`` call — re-implements the shared loader.
    2. A ``Path(__file__).parent`` chain of depth three or more — counts
       directories to the repository root, and breaks when the file moves.

    Both have a ``conftest`` helper that resolves by ``(bundle, skill, file)``
    instead, in two variants that differ only in what the path is relative to:
    ``load_script_module`` / ``get_scripts_dir`` for the skill's ``scripts/``
    subtree, and ``load_skill_module`` / ``get_skill_dir`` for the skill root. The
    second pair is what makes the remedy applicable to a bundle's
    ``plan-marshall-plugin`` ``extension.py``, which sits at the skill root — most
    such skills ship no ``scripts/`` directory, so the scripts-relative pair cannot
    address the file at all.
    """
    findings: list[dict] = []
    for path in _iter_test_tree_modules(test_root):
        source = _read_source(path)
        if source is None:
            continue
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if _is_spec_from_file_location(node):
                findings.append(_build_preamble_finding(path, node, 'spec_from_file_location'))
        nested = _nested_parent_attribute_ids(tree)
        for node in ast.walk(tree):
            if id(node) in nested:
                # An inner link of a longer chain — the outermost node reports it.
                continue
            depth = _parent_chain_depth(node) or _parents_index_depth(node)
            if depth >= PARENT_CHAIN_MIN_DEPTH:
                findings.append(_build_preamble_finding(path, node, 'parent_chain', depth=depth))
    findings.sort(key=lambda f: (f['file'], f.get('line', 0)))
    return findings


def _is_spec_from_file_location(node: ast.Call) -> bool:
    """Return True for ``spec_from_file_location(...)`` in either import form."""
    func = node.func
    if isinstance(func, ast.Attribute) and func.attr == 'spec_from_file_location':
        return True
    return isinstance(func, ast.Name) and func.id == 'spec_from_file_location'


def _nested_parent_attribute_ids(tree: ast.AST) -> set[int]:
    """Return the node ids of every ``.parent`` attribute nested inside another.

    ``ast.walk`` visits each link of a ``.parent`` chain, and every suffix of a
    long chain is itself a valid chain — so a depth-4 chain would otherwise
    report once at depth 4 and again at depth 3. Excluding the inner links
    leaves exactly the outermost node per chain.
    """
    nested: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == 'parent':
            value = node.value
            if isinstance(value, ast.Attribute) and value.attr == 'parent':
                nested.add(id(value))
    return nested


def _parent_chain_depth(node: ast.AST) -> int:
    """Return the ``.parent`` chain depth rooted at ``Path(__file__)``.

    Returns 0 for any node that does not terminate in ``Path(__file__)``.
    Callers exclude inner chain links via :func:`_nested_parent_attribute_ids`
    so one chain yields exactly one finding rather than one per link.
    """
    if not isinstance(node, ast.Attribute) or node.attr != 'parent':
        return 0
    depth = 0
    current: ast.AST = node
    while isinstance(current, ast.Attribute) and current.attr == 'parent':
        depth += 1
        current = current.value
    if not _is_path_dunder_file(current):
        return 0
    return depth


#: Path methods that return an equivalent path and so do not break the chain.
#: ``Path(__file__).resolve().parents[3]`` is the same directory-counting idiom
#: as ``Path(__file__).parent.parent.parent`` and is flagged identically.
_PATH_PASSTHROUGH_METHODS = frozenset({'resolve', 'absolute', 'expanduser'})


def _is_path_dunder_file(node: ast.AST) -> bool:
    """Return True for ``Path(__file__)``, through any path-preserving calls.

    Unwraps ``.resolve()`` / ``.absolute()`` / ``.expanduser()`` first: those
    return an equivalent path, so a chain rooted at one of them counts
    directories exactly as a bare ``Path(__file__)`` chain does.
    """
    current = node
    while (
        isinstance(current, ast.Call)
        and isinstance(current.func, ast.Attribute)
        and current.func.attr in _PATH_PASSTHROUGH_METHODS
    ):
        current = current.func.value
    if not isinstance(current, ast.Call):
        return False
    func = current.func
    is_path = (isinstance(func, ast.Name) and func.id == 'Path') or (
        isinstance(func, ast.Attribute) and func.attr == 'Path'
    )
    if not is_path or not current.args:
        return False
    first = current.args[0]
    return isinstance(first, ast.Name) and first.id == '__file__'


def _parents_index_depth(node: ast.AST) -> int:
    """Return N for ``Path(__file__)[…].parents[N]``, else 0.

    ``parents[N]`` is the indexed spelling of an N-deep ``.parent`` chain and
    carries the same brittleness, so it is measured on the same scale. Without
    this the rule's count is gameable: respelling a flagged chain as
    ``parents[N]`` would clear the finding while changing nothing.
    """
    if not isinstance(node, ast.Subscript):
        return 0
    value = node.value
    if not isinstance(value, ast.Attribute) or value.attr != 'parents':
        return 0
    index = node.slice
    if not isinstance(index, ast.Constant) or not isinstance(index.value, int) or index.value < 1:
        return 0
    receiver = value.value
    # The two spellings compose: `Path(__file__).parent.parents[3]` counts 4.
    # Measuring only the pure forms would leave the mixed one as an escape.
    chain_depth = _parent_chain_depth(receiver)
    if chain_depth:
        return chain_depth + index.value
    if _is_path_dunder_file(receiver):
        return index.value
    return 0


def _build_preamble_finding(path: Path, node: ast.AST, kind: str, depth: int | None = None) -> dict:
    if kind == 'spec_from_file_location':
        description = (
            'hand-rolled spec_from_file_location preamble — use '
            'conftest.load_script_module(bundle, skill, filename) for a module under '
            'scripts/, or conftest.load_skill_module(bundle, skill, filename, '
            'module_name) for one at the skill root (every bundle ships an '
            'extension.py, so pass a distinct module_name — or register=False — or '
            'they displace each other); both resolve by identity '
            "instead of by the test file's own location"
        )
    else:
        description = (
            f'Path(__file__) followed by a {depth}-deep .parent chain — use '
            'conftest.get_scripts_dir(bundle, skill), or conftest.get_skill_dir(bundle, '
            'skill) for a skill that ships no scripts/ directory; a directory-counting '
            'chain breaks the moment the test module moves'
        )
    details: dict = {
        'kind': kind,
        'standard_anchor': 'doctor-test-conventions.md#test-module-preamble-boilerplate',
    }
    if depth is not None:
        details['parent_chain_depth'] = depth
    return Finding(
        type='test-module-preamble-boilerplate',
        file=str(path),
        line=getattr(node, 'lineno', 1),
        severity='warning',
        fixable=False,
        rule_id='test-module-preamble-boilerplate',
        description=description,
        details=details,
    ).to_dict()


# ---------------------------------------------------------------------------
# Rule 7 -- test-docstring-historical-prose
# ---------------------------------------------------------------------------


def analyze_test_docstring_prose(test_root: Path) -> list[dict]:
    """Rule 7 -- flag historical citations in test docstrings and comments.

    A test docstring states the invariant in the present tense; it does not
    cite the incident that produced the test. This is ``CLAUDE.md``
    Documentation Standards applied to the test tree, and it reuses the
    matchers the ``no-incident-references`` and ``no-lesson-id-in-skill-prose``
    analyzers already apply over ``marketplace/bundles/**``.

    The scan is deliberately restricted to **docstrings and comments**. The
    same textual shapes appear far more often as string-literal test *data* —
    a lesson id fed to a validator under test is the corpus the test exists to
    check, not a citation — and flagging those would make the rule unusable.
    That prose-vs-data split is the rule's structural discriminator.

    A second discriminator runs *inside* prose, because the first one is not
    enough: prose also has to name values. A docstring saying ``get_next_id``
    returns ``<YYYY-MM-DD-HH-NNN>`` states the contract under test, and a comment
    naming the ``TASK-<NNN>`` file a command creates names a product artifact —
    neither cites a record. Both are distinguishable from a citation by
    formatting rather than by shape: **an identifier named as a value is written
    in an inline literal** (backticks or quotes), while a citation appears bare
    in the narrative. So a match inside an inline literal is exempt, and the
    convention that makes the rule teachable is "backtick the value you name".
    """
    findings: list[dict] = []
    for path in _iter_test_tree_modules(test_root):
        source = _read_source(path)
        if source is None:
            continue
        for lineno, text in _iter_prose_segments(source, path):
            literal_spans = _inline_literal_spans(text)
            for kind, pattern in _HISTORICAL_PROSE_PATTERNS:
                match = _first_bare_match(pattern, text, literal_spans)
                if match:
                    # Offset to the citation's own line, not the segment's first
                    # line — the finding exists to be navigated to.
                    hit_line = lineno + text[: match.start()].count('\n')
                    findings.append(_build_docstring_prose_finding(path, hit_line, kind, match.group(0)))
                    break
    findings.sort(key=lambda f: (f['file'], f.get('line', 0)))
    return findings


#: Inline-literal spellings that mark an identifier as a *named value* rather
#: than a citation: double- and single-backtick code spans, and quoted strings.
#: Double backticks are matched first so the inner single-backtick pattern
#: cannot split a ``…`` span in half.
#:
#: ⛔ Two bounds on the quote alternatives, and BOTH are needed. English prose is
#: full of apostrophes, and an apostrophe is not a quote delimiter:
#:
#: 1. No alternative may cross a newline. A prose segment arrives as ONE
#:    multi-line string, so without this a possessive on one line and a
#:    contraction ten lines later open a single "literal" span swallowing
#:    everything between.
#: 2. A quote delimiter may not sit against a word character. The newline bound
#:    alone does NOT fix the same-line case: in ``The resolver's PR #515 guard
#:    doesn't fall through``, the two apostrophes are on one line and still span
#:    the citation. A possessive or contraction apostrophe is always preceded by
#:    a word character, while an opening delimiter never is.
#:
#: Both were observed silently exempting real citations on this repository's own
#: corpus — a false negative, the direction that matters.
_INLINE_LITERAL_RE = re.compile(
    r"``[^`\n]+``"
    r"|`[^`\n]+`"
    r"|(?<!\w)'[^'\n]+'(?!\w)"
    r"|(?<!\w)\"[^\"\n]+\"(?!\w)"
)


def _inline_literal_spans(text: str) -> list[tuple[int, int]]:
    """Return ``(start, end)`` for every inline literal in ``text``."""
    return [m.span() for m in _INLINE_LITERAL_RE.finditer(text)]


def _first_bare_match(
    pattern: re.Pattern, text: str, literal_spans: list[tuple[int, int]]
) -> re.Match | None:
    """Return the first match of ``pattern`` that is not inside an inline literal.

    A match inside a literal is an identifier the prose is *naming* — the value
    a function returns, the fixture a test seeds, the file a command creates —
    not a record the prose cites.
    """
    for match in pattern.finditer(text):
        start = match.start()
        if any(lo <= start < hi for lo, hi in literal_spans):
            continue
        return match
    return None


def _iter_prose_segments(source: str, path: Path) -> list[tuple[int, str]]:
    """Return ``(lineno, text)`` for every docstring and ``#`` comment.

    Only these two contexts carry prose. Every other string in a test module is
    data the test operates on.

    A comment's text is returned WITHOUT its leading ``#``: the delimiter is
    punctuation the tokenizer supplies rather than something the author wrote, and
    leaving it attached makes every comment look like it opens with a
    ``#``-prefixed token. A docstring is returned verbatim, so a citation sitting
    at its very first character is still there to be matched.
    """
    segments: list[tuple[int, str]] = []
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return segments
    for node in ast.walk(tree):
        if not isinstance(node, ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        docstring = ast.get_docstring(node, clean=False)
        if not docstring:
            continue
        # Anchor on the docstring literal itself, not the def/class line, so a
        # citation deep in a long docstring reports a navigable location.
        first_stmt = node.body[0] if node.body else None
        lineno: int = getattr(node, 'lineno', 1)
        if isinstance(first_stmt, ast.Expr):
            lineno = first_stmt.value.lineno
        segments.append((lineno, docstring))
    try:
        for token in tokenize.generate_tokens(io.StringIO(source).readline):
            if token.type == tokenize.COMMENT:
                # Strip the ``#`` delimiter the tokenizer supplies. It is
                # punctuation rather than prose, and leaving it attached makes
                # every comment appear to open with a ``#``-prefixed token, which
                # a bare record-number matcher reads as a citation. Stripping it
                # here is what lets those matchers use a plain negative lookbehind
                # and so stay able to fire at the start of a DOCSTRING, where a
                # citation legitimately can sit.
                segments.append((token.start[0], token.string[1:]))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        # A module that does not tokenize still yields its parsed docstrings.
        pass
    return segments


def _build_docstring_prose_finding(path: Path, lineno: int, kind: str, matched: str) -> dict:
    description = (
        f"historical citation '{matched}' in test prose — a docstring states the "
        f'invariant in the present tense, not the incident that produced the test '
        f'(the history is in git; the citation costs context on every read)'
    )
    return Finding(
        type='test-docstring-historical-prose',
        file=str(path),
        line=lineno,
        severity='warning',
        fixable=False,
        rule_id='test-docstring-historical-prose',
        description=description,
        details={
            'kind': kind,
            'matched': matched,
            'standard_anchor': 'doctor-test-conventions.md#test-docstring-historical-prose',
        },
    ).to_dict()
