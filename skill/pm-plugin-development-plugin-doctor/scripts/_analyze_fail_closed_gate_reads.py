#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Fail-closed-gate-read and redundant-contract-typed-isinstance analyzer.

This module detects two forward-enforcement anti-patterns via AST analysis over
``marketplace/bundles/**/skills/*/scripts/**/*.py`` (test files excluded). It
mirrors the established ``analyze_{rule}(marketplace_root) -> list[findings]``
contract of ``_analyze_plan_path_in_scripts.py`` and
``_analyze_executor_path_in_production.py``.

Form A — fail-closed-gate-read
------------------------------
A read-only gate/boundary verb (a function that forms a verdict by reading a
file without mutating state) MUST fail closed: the file read has to be enclosed
in a ``try`` whose handler catches ``OSError`` so a path that passed an
``.exists()`` probe but raises on read (permission denied, the path resolving to
a directory, a mid-read deletion race) surfaces as a structured error rather
than crashing the verdict path.

Form A flags a file read — ``<x>.read_text(...)``, ``open(...)``,
``json.load(...)`` / ``json.loads(...)`` over a read, or
``parse_toon(<x>.read_text(...))`` — that sits inside a gate-verb function
(name matches the gate-verb pattern) and is NOT lexically enclosed by a ``try``
in that function whose ``except`` catches ``OSError`` (or a broader
``Exception`` / bare ``except``).

Form B — redundant-isinstance-on-contract-typed-param
-----------------------------------------------------
An ``isinstance(param, <Cls>)`` guard where ``param`` is a function parameter
annotated with that same concrete class (e.g. ``metadata: dict[str, Any]`` then
``isinstance(metadata, dict)``) is defensive theatre: the annotation is the
contract, so in correct code the guard can never be false. It misleads the next
reader. Runtime type checks are reserved for genuine polymorphism
(``Any`` / union runtime types) or untrusted-input ingestion boundaries — those
shapes are NOT flagged.

Exemptions
----------
1. **Canonical source** — ``tools-file-ops/scripts/file_ops.py`` is never
   flagged; it IS the canonical fail-closed read implementation
   (``read_json`` etc.).
2. **Self-reference** — this analyzer file is never flagged.

Findings have the shape::

    {
        'rule_id': 'fail-closed-gate-read' | 'redundant-contract-typed-isinstance',
        'file': '<absolute file path>',
        'line': <int, 1-based>,
        'category': 'production_script',
        'snippet': '<line excerpt>',
    }

Public API
----------
- ``analyze_fail_closed_gate_reads(marketplace_root)``: entry point — scans the
  bundle scripts tree and emits findings for both forms.
- ``is_whitelisted(file_path)``: returns True when ``file_path`` matches a
  whitelist entry.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator
from pathlib import Path

from _rule_registry import RuleDescriptor

RULE_FAIL_CLOSED_GATE_READ = 'fail-closed-gate-read'
RULE_REDUNDANT_ISINSTANCE = 'redundant-contract-typed-isinstance'

# Two rules emitted by one whole-tree pass — declared as a descriptor list.
RULE_DESCRIPTORS = [
    RuleDescriptor(
        rule_id=RULE_FAIL_CLOSED_GATE_READ,
        severity='error',
        category='safety',
        scope='file-local',
    ),
    RuleDescriptor(
        rule_id=RULE_REDUNDANT_ISINSTANCE,
        severity='error',
        category='structural',
        scope='file-local',
    ),
]

# ---------------------------------------------------------------------------
# Gate-verb name pattern (Form A)
# ---------------------------------------------------------------------------
# A function whose name marks it a read-only gate/boundary verb: command
# handlers (``cmd_*``), ``*_status`` boundary verbs, ``assert_*`` / ``*_verify``
# / ``*_validate`` gate verbs, and the consistency-check ``check_*`` / ``load_*``
# helpers a gate verb calls to form its verdict.
_GATE_VERB_NAME_RE = re.compile(
    r'^(cmd_.+|.+_status|assert_.+|.+_verify|verify_.+|.+_validate|validate_.+|check_.+|load_.+)$'
)

# ---------------------------------------------------------------------------
# Concrete builtin contract types eligible for the Form-B redundant guard.
# Only concrete, non-polymorphic builtins: a parameter annotated with one of
# these and guarded by isinstance(param, <same>) is the defensive-theatre form.
# ---------------------------------------------------------------------------
_CONCRETE_CONTRACT_TYPES: frozenset[str] = frozenset(
    {'dict', 'list', 'str', 'int', 'float', 'bool', 'set', 'tuple', 'bytes', 'frozenset'}
)

# ---------------------------------------------------------------------------
# Whitelist — path-suffix-anchored (exact directory structure)
# ---------------------------------------------------------------------------

_WHITELIST_SUFFIXES: list[tuple[str, ...]] = [
    # Self-reference: this analyzer file (the markers are the detection target).
    ('pm-plugin-development', 'skills', 'plugin-doctor', 'scripts', '_analyze_fail_closed_gate_reads.py'),
    # Canonical source: file_ops.py IS the fail-closed read implementation.
    ('tools-file-ops', 'scripts', 'file_ops.py'),
]


def is_whitelisted(file_path: Path) -> bool:
    """Return True when ``file_path`` matches any whitelist entry.

    Each whitelist entry is a suffix tuple that must match the trailing
    components of ``file_path`` exactly — only canonical path shapes are
    exempt, not any path that happens to contain the component strings.
    """
    parts = file_path.parts
    for suffix in _WHITELIST_SUFFIXES:
        if len(parts) >= len(suffix) and parts[-len(suffix):] == suffix:
            return True
    return False


# ---------------------------------------------------------------------------
# File iteration / parse helpers (mirror _analyze_simplicity conventions)
# ---------------------------------------------------------------------------


def _iter_script_files(marketplace_root: Path) -> list[Path]:
    """Enumerate marketplace bundle Python scripts (excluding test files)."""
    bundles_root = marketplace_root / 'bundles'
    if not bundles_root.is_dir():
        return []
    targets: list[Path] = []
    for py_file in bundles_root.glob('*/skills/*/scripts/**/*.py'):
        if not py_file.is_file():
            continue
        name = py_file.name
        if name.startswith('test_') or name.endswith('_test.py'):
            continue
        if any(part in ('test', 'tests') for part in py_file.parts):
            continue
        targets.append(py_file)
    return sorted(set(targets))


def _parse(file_path: Path) -> tuple[str, ast.Module] | None:
    """Read and AST-parse a file, returning ``(source, tree)`` or ``None``."""
    try:
        source = file_path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return None
    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return None
    return source, tree


def _functions(tree: ast.Module) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    """Return all function definitions in a module (including nested)."""
    return [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]


def _walk_local(node: ast.AST) -> Iterator[ast.AST]:
    """Yield ``node`` and its descendants WITHOUT descending into nested scopes.

    Like ``ast.walk`` but it stops at nested ``FunctionDef`` / ``AsyncFunctionDef``
    / ``ClassDef`` boundaries: a nested helper's reads, ``OSError`` handlers, and
    ``isinstance`` guards belong to that inner scope (scanned independently via
    ``_functions``), not to the enclosing gate verb. ``node`` itself is always
    descended into; a nested scope node below it is yielded but not entered.
    """
    stack: list[ast.AST] = [node]
    while stack:
        current = stack.pop()
        yield current
        if current is not node and isinstance(
            current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            continue
        stack.extend(ast.iter_child_nodes(current))


# ---------------------------------------------------------------------------
# Form A — fail-closed-gate-read detection
# ---------------------------------------------------------------------------


def _is_gate_verb(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return True when the function name marks it a read-only gate/boundary verb."""
    return bool(_GATE_VERB_NAME_RE.match(func.name))


def _is_file_read_call(node: ast.AST) -> bool:
    """Return True when ``node`` is a file-read call that can raise ``OSError``.

    Recognised read shapes:
    - ``<x>.read_text(...)`` / ``<x>.read_bytes(...)`` (pathlib reads)
    - ``open(...)`` (builtin open)
    - ``json.load(...)`` / ``json.loads(...)`` (the loads form only when its
      argument is itself a read call — a bare ``json.loads(string)`` over an
      in-memory value cannot raise OSError and is not flagged)
    - ``parse_toon(<read>)`` (only when wrapping a read call)
    """
    if not isinstance(node, ast.Call):
        return False
    func = node.func

    # <x>.read_text(...) / <x>.read_bytes(...)
    if isinstance(func, ast.Attribute) and func.attr in ('read_text', 'read_bytes'):
        return True

    # open(...)
    if isinstance(func, ast.Name) and func.id == 'open':
        return True

    # json.load(<file_obj>) — direct file read
    if (
        isinstance(func, ast.Attribute)
        and func.attr == 'load'
        and isinstance(func.value, ast.Name)
        and func.value.id == 'json'
    ):
        return True

    # json.loads(<read>) / parse_toon(<read>) — only when an argument is a read.
    # Inspect BOTH positional args and keyword-argument values, so a keyword-passed
    # read (e.g. ``json.loads(s=<read>)``) is detected, not just ``node.args[0]``.
    wraps_read = (
        isinstance(func, ast.Attribute)
        and func.attr == 'loads'
        and isinstance(func.value, ast.Name)
        and func.value.id == 'json'
    ) or (isinstance(func, ast.Name) and func.id == 'parse_toon')
    if wraps_read:
        arg_exprs = [*node.args, *(kw.value for kw in node.keywords)]
        return any(_contains_file_read(arg) for arg in arg_exprs)

    return False


def _contains_file_read(node: ast.AST) -> bool:
    """Return True when ``node`` or a descendant is a file-read call."""
    return any(_is_file_read_call(sub) for sub in ast.walk(node))


def _try_blocks_catching_oserror(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[ast.Try]:
    """Return the ``ast.Try`` nodes in ``func`` whose handlers catch ``OSError``.

    A handler catches OSError when it is a bare ``except:``, ``except Exception``,
    ``except OSError``, or any tuple/name handler that names ``OSError`` or
    ``Exception`` (``IsADirectoryError`` / ``PermissionError`` / ``FileNotFoundError``
    are OSError subclasses but a handler naming only a narrow subclass does NOT
    cover the general OSError contract, so only ``OSError`` / ``Exception`` /
    bare are treated as fail-closed).
    """
    catching: list[ast.Try] = []
    for node in _walk_local(func):
        if not isinstance(node, ast.Try):
            continue
        if any(_handler_catches_oserror(h) for h in node.handlers):
            catching.append(node)
    return catching


def _handler_catches_oserror(handler: ast.ExceptHandler) -> bool:
    """Return True when ``handler`` catches OSError (bare / Exception / OSError)."""
    exc = handler.type
    if exc is None:  # bare except:
        return True
    names: list[str] = []
    if isinstance(exc, ast.Tuple):
        names = [e.id for e in exc.elts if isinstance(e, ast.Name)]
    elif isinstance(exc, ast.Name):
        names = [exc.id]
    return any(n in ('OSError', 'Exception', 'BaseException') for n in names)


def _node_lines(node: ast.AST) -> set[int]:
    """Return the set of source line numbers spanned by ``node``."""
    lines: set[int] = set()
    for sub in ast.walk(node):
        lineno = getattr(sub, 'lineno', None)
        if isinstance(lineno, int):
            lines.add(lineno)
    return lines


def _scan_form_a(
    func: ast.FunctionDef | ast.AsyncFunctionDef, file_path: Path, lines: list[str]
) -> list[dict]:
    """Collect Form-A findings for unguarded file reads inside a gate verb."""
    if not _is_gate_verb(func):
        return []

    # Lines covered by a try whose handler catches OSError — reads on these lines
    # are fail-closed and exempt.
    guarded_lines: set[int] = set()
    for try_node in _try_blocks_catching_oserror(func):
        for stmt in try_node.body:
            guarded_lines |= _node_lines(stmt)

    findings: list[dict] = []
    seen: set[int] = set()
    for node in _walk_local(func):
        if not _is_file_read_call(node):
            continue
        line_no = getattr(node, 'lineno', 0)
        if not line_no or line_no in seen:
            continue
        if line_no in guarded_lines:
            continue
        seen.add(line_no)
        snippet = lines[line_no - 1].strip()[:120] if line_no <= len(lines) else ''
        findings.append(
            {
                'rule_id': RULE_FAIL_CLOSED_GATE_READ,
                'file': str(file_path),
                'line': line_no,
                'category': 'production_script',
                'snippet': snippet,
            }
        )
    return findings


# ---------------------------------------------------------------------------
# Form B — redundant-contract-typed-isinstance detection
# ---------------------------------------------------------------------------


def _annotation_base_name(annotation: ast.expr | None) -> str | None:
    """Return the concrete base type name of a parameter annotation, or None.

    Resolves ``dict`` from ``dict`` and ``dict[str, Any]``; returns None for
    ``Any``, unions (``X | Y``, ``Optional[X]``, ``Union[...]``), and any
    annotation whose base is not a concrete contract type.
    """
    if annotation is None:
        return None
    # Bare name: ``dict``, ``list``, ...
    if isinstance(annotation, ast.Name):
        return annotation.id if annotation.id in _CONCRETE_CONTRACT_TYPES else None
    # Subscripted: ``dict[str, Any]`` → base ``dict``. Reject Optional/Union.
    if isinstance(annotation, ast.Subscript):
        base = annotation.value
        if isinstance(base, ast.Name):
            if base.id in ('Optional', 'Union'):
                return None
            return base.id if base.id in _CONCRETE_CONTRACT_TYPES else None
    # ``X | Y`` union, string-forward-ref, Any, etc. → not a concrete contract.
    return None


def _contract_typed_params(
    func: ast.FunctionDef | ast.AsyncFunctionDef,
) -> dict[str, str]:
    """Map each parameter name to its concrete contract base type (if any)."""
    a = func.args
    mapping: dict[str, str] = {}
    for arg in (*a.posonlyargs, *a.args, *a.kwonlyargs):
        base = _annotation_base_name(arg.annotation)
        if base is not None:
            mapping[arg.arg] = base
    return mapping


def _scan_form_b(
    func: ast.FunctionDef | ast.AsyncFunctionDef, file_path: Path, lines: list[str]
) -> list[dict]:
    """Collect Form-B findings for redundant isinstance guards on contract params."""
    contract_params = _contract_typed_params(func)
    if not contract_params:
        return []

    findings: list[dict] = []
    seen: set[int] = set()
    for node in _walk_local(func):
        if not isinstance(node, ast.Call):
            continue
        if not (isinstance(node.func, ast.Name) and node.func.id == 'isinstance'):
            continue
        if len(node.args) != 2:
            continue
        target, type_arg = node.args
        if not isinstance(target, ast.Name):
            continue
        declared = contract_params.get(target.id)
        if declared is None:
            continue
        # The isinstance check's class must be exactly the declared contract type.
        if not (isinstance(type_arg, ast.Name) and type_arg.id == declared):
            continue
        line_no = getattr(node, 'lineno', 0)
        if not line_no or line_no in seen:
            continue
        seen.add(line_no)
        snippet = lines[line_no - 1].strip()[:120] if line_no <= len(lines) else ''
        findings.append(
            {
                'rule_id': RULE_REDUNDANT_ISINSTANCE,
                'file': str(file_path),
                'line': line_no,
                'category': 'production_script',
                'snippet': snippet,
            }
        )
    return findings


# ---------------------------------------------------------------------------
# File scanner + entry point
# ---------------------------------------------------------------------------


def _scan_file(file_path: Path) -> list[dict]:
    """Scan one Python file for Form-A and Form-B findings."""
    parsed = _parse(file_path)
    if parsed is None:
        return []
    source, tree = parsed
    lines = source.splitlines()

    findings: list[dict] = []
    for func in _functions(tree):
        findings.extend(_scan_form_a(func, file_path, lines))
        findings.extend(_scan_form_b(func, file_path, lines))
    return findings


def analyze_fail_closed_gate_reads(marketplace_root: Path) -> list[dict]:
    """Scan marketplace bundle scripts for fail-closed-read and redundant-isinstance drift.

    Scans ``<marketplace_root>/bundles/*/skills/*/scripts/**/*.py`` (test files
    excluded). Two forms are detected (see module docstring):

    - Form A (``fail-closed-gate-read``): an unguarded file read inside a
      read-only gate/boundary verb.
    - Form B (``redundant-contract-typed-isinstance``): an ``isinstance`` guard
      on a parameter already annotated with that concrete contract type.

    Parameters
    ----------
    marketplace_root:
        Path to the ``marketplace/`` directory.

    Returns
    -------
    list[dict]
        Findings for non-whitelisted drift occurrences.
    """
    findings: list[dict] = []
    for py_file in _iter_script_files(marketplace_root):
        if is_whitelisted(py_file):
            continue
        findings.extend(_scan_file(py_file))
    return findings
