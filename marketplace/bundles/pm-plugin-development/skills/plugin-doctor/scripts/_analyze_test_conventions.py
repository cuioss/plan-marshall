#!/usr/bin/env python3
"""Test-tree conventions analyzer for plugin-doctor.

Hosts the three build-failing rules documented in
`standards/doctor-test-conventions.md`:

- analyze_unique_fixture_basenames -- Rule 1
- analyze_subprocess_pythonpath    -- Rule 2 (added by a later task)
- analyze_validator_regex_vs_corpus -- Rule 3 (added by a later task)

Each rule returns a list of finding dicts in the standard plugin-doctor shape
(type, rule_id, file, line, severity, fixable, description, details).
"""

from __future__ import annotations

import ast
import re
import shlex
import subprocess
from collections import defaultdict
from pathlib import Path

GENERIC_HELPER_BASENAMES = frozenset({'_fixtures.py', '_helpers.py', '_common.py'})

ID_LINE_PATTERN = re.compile(r'^\s*(?:- )?id:\s*(?P<id>\S+)\s*$', re.MULTILINE)


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
    return {
        'type': 'unique-fixture-basenames',
        'rule_id': 'unique-fixture-basenames',
        'file': str(path),
        'line': 1,
        'severity': 'error',
        'fixable': False,
        'description': description,
        'details': {
            'kind': 'generic_basename',
            'basename': path.name,
            'standard_anchor': 'doctor-test-conventions.md#unique-fixture-basenames',
        },
    }


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
    return {
        'type': 'subprocess-pythonpath',
        'rule_id': 'subprocess-pythonpath',
        'file': str(path),
        'line': getattr(node, 'lineno', 1),
        'severity': 'error',
        'fixable': False,
        'description': description,
        'details': {
            'standard_anchor': 'doctor-test-conventions.md#subprocess-pythonpath',
        },
    }


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
    return {
        'type': 'identifier-validator-corpus',
        'rule_id': 'identifier-validator-corpus',
        'file': str(validator_path),
        'line': 1,
        'severity': 'error',
        'fixable': False,
        'description': description,
        'details': {
            'pattern': pattern,
            'list_command': list_command,
            'rejected_id': identifier,
            'standard_anchor': 'doctor-test-conventions.md#identifier-validator-corpus',
        },
    }


def _build_corpus_error_finding(validator_path: Path, regex_constant: str, list_command: str, reason: str) -> dict:
    description = (
        f"identifier-validator-corpus check failed for {validator_path.name} "
        f"({regex_constant} via `{list_command}`) — reason: {reason}"
    )
    return {
        'type': 'identifier-validator-corpus',
        'rule_id': 'identifier-validator-corpus',
        'file': str(validator_path),
        'line': 1,
        'severity': 'error',
        'fixable': False,
        'description': description,
        'details': {
            'regex_constant': regex_constant,
            'list_command': list_command,
            'reason': reason,
            'standard_anchor': 'doctor-test-conventions.md#identifier-validator-corpus',
        },
    }


def _build_collision_finding(path: Path, basename: str, other_paths: list[Path]) -> dict:
    others_repr = ', '.join(str(other) for other in other_paths)
    description = (
        f"helper module basename '{basename}' collides with sibling test "
        f"directories ({others_repr}) — pytest sys.modules will register "
        f"only one; rename one or both to a domain-prefixed name"
    )
    return {
        'type': 'unique-fixture-basenames',
        'rule_id': 'unique-fixture-basenames',
        'file': str(path),
        'line': 1,
        'severity': 'error',
        'fixable': False,
        'description': description,
        'details': {
            'kind': 'cross_directory_collision',
            'basename': basename,
            'colliding_with': [str(other) for other in other_paths],
            'standard_anchor': 'doctor-test-conventions.md#unique-fixture-basenames',
        },
    }
