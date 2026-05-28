#!/usr/bin/env python3
"""Simplification rule detectors for the five ``SIMPLICITY_*`` rules.

These five detectors are the mechanical enforcement layer for the
"minimum viable code" posture defined in
``plan-marshall:dev-general-code-quality`` →
``standards/code-organization.md`` § ``#minimum-viable-code``. They detect the
deterministically-recognisable subset of that section's anti-patterns in
marketplace bundle scripts; the cognitive judgement calls are handled by the
``default:finalize-step-simplify`` phase-6 step.

Rules
-----
- ``SIMPLICITY_UNUSED_PARAMETER`` — a function whose body discards a parameter
  via ``del <param>`` (the "preserved for future use" pattern), or a parameter
  tagged with a trailing ``# unused`` marker.
- ``SIMPLICITY_BACKWARD_COMPAT_REEXPORT`` — an import line tagged with a
  ``# backward compat`` / ``# re-exported for`` comment.
- ``SIMPLICITY_DEFENSIVE_CATCHALL`` — an ``except Exception`` handler tagged
  ``# defensive only`` or ``# pragma: no cover -- defensive``.
- ``SIMPLICITY_THIN_WRAPPER`` — a function whose body is a single ``return``
  forwarding its arguments to one other call (a thin pass-through wrapper).
- ``SIMPLICITY_SIGNATURE_DOCSTRING`` — a function docstring whose first
  paragraph only restates ``Args:`` / ``Returns:`` with no other content.

Each detector takes a ``marketplace_root`` (the ``marketplace/`` directory) and
returns a list of finding dicts. Findings carry ``rule_id`` / ``type`` /
``file`` / ``line`` / ``severity`` / ``fixable`` / ``description`` so they merge
into the plugin-doctor issue stream the same way ``argparse_safety`` findings
do. Only ``SIMPLICITY_SIGNATURE_DOCSTRING`` carries ``fixable: True`` — its
mechanical fix (delete the restating docstring) is the one safe auto-apply in
the cluster. The other four are ``fixable: False``: removing an unused
parameter, a re-export shim, a defensive catch-all, or a thin wrapper all
change a signature or require rewriting call sites, so they are
confirm-before-apply (risky) decisions.

The scan is a lightweight AST walk plus a per-line regex pass — no parser or
subprocess is executed.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

RULE_UNUSED_PARAMETER = 'SIMPLICITY_UNUSED_PARAMETER'
RULE_BACKWARD_COMPAT_REEXPORT = 'SIMPLICITY_BACKWARD_COMPAT_REEXPORT'
RULE_DEFENSIVE_CATCHALL = 'SIMPLICITY_DEFENSIVE_CATCHALL'
RULE_THIN_WRAPPER = 'SIMPLICITY_THIN_WRAPPER'
RULE_SIGNATURE_DOCSTRING = 'SIMPLICITY_SIGNATURE_DOCSTRING'

# Comment markers that flag a backward-compat re-export (case-insensitive).
_REEXPORT_COMMENT_RE = re.compile(r'#.*\b(backward[ -]?compat|re-?exported for)\b', re.IGNORECASE)

# Comment markers that flag a deliberately-defensive catch-all handler.
_DEFENSIVE_COMMENT_RE = re.compile(r'#.*\b(defensive only|pragma:\s*no cover\s*--\s*defensive)\b', re.IGNORECASE)

# Trailing ``# unused`` marker on a parameter / assignment line.
_UNUSED_MARKER_RE = re.compile(r'#\s*unused\b', re.IGNORECASE)


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


def _param_names(func: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    """Collect every parameter name declared by a function signature."""
    a = func.args
    names = {arg.arg for arg in (*a.posonlyargs, *a.args, *a.kwonlyargs)}
    if a.vararg:
        names.add(a.vararg.arg)
    if a.kwarg:
        names.add(a.kwarg.arg)
    return names


def _finding(rule_id: str, file_path: Path, line: int, description: str, *, fixable: bool) -> dict:
    return {
        'rule_id': rule_id,
        'type': rule_id,
        'file': str(file_path),
        'line': line,
        'severity': 'warning',
        'fixable': fixable,
        'description': f'{description} ({rule_id})',
    }


def analyze_unused_parameter(marketplace_root: Path) -> list[dict]:
    """Detect parameters discarded via ``del <param>`` or tagged ``# unused``.

    The ``del <param>`` form is the canonical "preserved for future use"
    pattern — the parameter is declared to keep the signature stable but
    immediately discarded so no code path reads it. Risky to fix (signature
    change), so ``fixable: False``.
    """
    findings: list[dict] = []
    for file_path in _iter_script_files(marketplace_root):
        parsed = _parse(file_path)
        if parsed is None:
            continue
        source, tree = parsed
        lines = source.splitlines()
        for func in _functions(tree):
            params = _param_names(func)
            if not params:
                continue
            for node in ast.walk(func):
                if not isinstance(node, ast.Delete):
                    continue
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in params:
                        findings.append(
                            _finding(
                                RULE_UNUSED_PARAMETER,
                                file_path,
                                node.lineno,
                                f"Parameter `{target.id}` discarded via `del` — preserved-for-future-use; "
                                f"remove it and add back when a real caller needs it",
                                fixable=False,
                            )
                        )
        for idx, line in enumerate(lines, start=1):
            if _UNUSED_MARKER_RE.search(line) and ('def ' in line or '):' in line or ',' in line):
                findings.append(
                    _finding(
                        RULE_UNUSED_PARAMETER,
                        file_path,
                        idx,
                        'Parameter tagged `# unused` — remove it instead of marking it',
                        fixable=False,
                    )
                )
    return findings


def analyze_backward_compat_reexport(marketplace_root: Path) -> list[dict]:
    """Detect import lines tagged with a backward-compat re-export comment."""
    findings: list[dict] = []
    for file_path in _iter_script_files(marketplace_root):
        try:
            text = file_path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        for idx, line in enumerate(text.splitlines(), start=1):
            stripped = line.lstrip()
            if not (stripped.startswith('import ') or stripped.startswith('from ')):
                continue
            if _REEXPORT_COMMENT_RE.search(line):
                findings.append(
                    _finding(
                        RULE_BACKWARD_COMPAT_REEXPORT,
                        file_path,
                        idx,
                        'Backward-compat re-export — inline the import at its single call site and delete the shim',
                        fixable=False,
                    )
                )
    return findings


def analyze_defensive_catchall(marketplace_root: Path) -> list[dict]:
    """Detect ``except Exception`` handlers tagged as deliberately defensive."""
    findings: list[dict] = []
    for file_path in _iter_script_files(marketplace_root):
        parsed = _parse(file_path)
        if parsed is None:
            continue
        source, tree = parsed
        lines = source.splitlines()
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            etype = node.type
            is_broad = etype is None or (isinstance(etype, ast.Name) and etype.id in ('Exception', 'BaseException'))
            if not is_broad:
                continue
            # Inspect the handler header line and the first body line for the marker.
            window = [node.lineno]
            if node.body:
                window.append(node.body[0].lineno)
            for ln in window:
                if 1 <= ln <= len(lines) and _DEFENSIVE_COMMENT_RE.search(lines[ln - 1]):
                    findings.append(
                        _finding(
                            RULE_DEFENSIVE_CATCHALL,
                            file_path,
                            node.lineno,
                            'Defensive catch-all — let the exception propagate instead of swallowing it',
                            fixable=False,
                        )
                    )
                    break
    return findings


def _is_thin_wrapper(func: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return True when the function body is a single ``return <call>(...)``.

    The body may carry a leading docstring; the only executable statement must
    be a ``return`` whose value is a function call (the forwarding target).
    """
    body = list(func.body)
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        body = body[1:]  # skip docstring
    if len(body) != 1:
        return False
    stmt = body[0]
    return isinstance(stmt, ast.Return) and isinstance(stmt.value, ast.Call)


def analyze_thin_wrapper(marketplace_root: Path) -> list[dict]:
    """Detect functions whose body is a single argument-forwarding ``return``."""
    findings: list[dict] = []
    for file_path in _iter_script_files(marketplace_root):
        parsed = _parse(file_path)
        if parsed is None:
            continue
        _source, tree = parsed
        for func in _functions(tree):
            if _is_thin_wrapper(func):
                findings.append(
                    _finding(
                        RULE_THIN_WRAPPER,
                        file_path,
                        func.lineno,
                        f"Thin wrapper `{func.name}` forwards args to one call — inline it at the call site",
                        fixable=False,
                    )
                )
    return findings


def _first_docstring_paragraph(docstring: str) -> str:
    """Return the first blank-line-delimited paragraph of a docstring."""
    paragraph: list[str] = []
    for line in docstring.strip().splitlines():
        if not line.strip():
            break
        paragraph.append(line.strip())
    return ' '.join(paragraph)


def _restates_signature_only(docstring: str) -> bool:
    """Return True when a docstring's only content restates Args:/Returns:.

    A signature-restating docstring has a first paragraph that is empty or
    merely names ``Args:`` / ``Returns:`` headers, with no intent ("WHY")
    content elsewhere.
    """
    body = docstring.strip()
    if not body:
        return False
    first = _first_docstring_paragraph(body)
    # The docstring must consist ONLY of Args:/Returns: structural headers —
    # the first paragraph carries no prose summary line.
    structural_only = bool(re.fullmatch(r'(args|arguments|returns|return|params|parameters)\s*:?', first, re.IGNORECASE))
    return structural_only


def analyze_signature_docstring(marketplace_root: Path) -> list[dict]:
    """Detect docstrings whose first paragraph only restates Args:/Returns:."""
    findings: list[dict] = []
    for file_path in _iter_script_files(marketplace_root):
        parsed = _parse(file_path)
        if parsed is None:
            continue
        _source, tree = parsed
        for func in _functions(tree):
            docstring = ast.get_docstring(func, clean=False)
            if docstring and _restates_signature_only(docstring):
                findings.append(
                    _finding(
                        RULE_SIGNATURE_DOCSTRING,
                        file_path,
                        func.lineno,
                        f"Docstring for `{func.name}` only restates the signature — delete it or add a rationale",
                        fixable=True,
                    )
                )
    return findings


def scan_simplicity(marketplace_root: Path) -> list[dict]:
    """Run all five ``SIMPLICITY_*`` detectors over the marketplace tree.

    Aggregates the findings from every detector into one list, mirroring the
    ``scan_argparse_safety`` marketplace-wide entry point.
    """
    findings: list[dict] = []
    findings.extend(analyze_unused_parameter(marketplace_root))
    findings.extend(analyze_backward_compat_reexport(marketplace_root))
    findings.extend(analyze_defensive_catchall(marketplace_root))
    findings.extend(analyze_thin_wrapper(marketplace_root))
    findings.extend(analyze_signature_docstring(marketplace_root))
    return findings
