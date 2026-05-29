#!/usr/bin/env python3
"""Plan-path-in-scripts analyzer for the ``plan-path-in-scripts`` rule.

This module detects hand-rolled re-implementations of canonical
``tools-file-ops:file_ops`` path helpers inside marketplace bundle scripts.
Two drift forms are detected via AST analysis:

**Form A — literal bypass**: A string constant (``ast.Constant``) whose value
contains ``.plan/plans/`` (the drifted form that omits ``/local/``) appears in
a code-active path-construction context: assignment target, string concatenation,
``Path(...)`` / ``os.path.join(...)`` call argument, or f-string nested
expression.  Module, class, and function **docstrings** (first ``ast.Expr`` in
a body) are excluded, as are strings in ``print()`` / ``help=`` annotation
positions.  The canonical resolved path is ``.plan/local/plans/``; the drifted
form creates a ghost ``.plan/plans/`` tree at the repo root on every invocation.

**Form B — parent-walking re-derivation**: A ``Path(__file__).parent…`` or
``os.path.dirname(__file__)`` expression chain whose final value is joined
(via ``/``, ``Path(…)``, or ``os.path.join``) against a ``.plan``-domain
subdirectory name (``plans``, ``lessons-learned``, ``logs``, ``archived-plans``,
``workspace``).  The canonical approach is to import and call
``tools-file-ops:file_ops.get_plan_dir`` / ``base_path`` / etc.

Exemptions (both forms)
-----------------------
1. **Canonical source** — ``file_ops.py`` (``tools-file-ops`` bundle) is never
   flagged; it IS the canonical implementation.
2. **Import bootstraps** — ``Path(__file__).parent…`` chains that appear
   exclusively as the argument to ``sys.path.insert`` or ``sys.path.append``
   are bootstrap idioms, not path-resolution drift.

Convention documented here
--------------------------
The canonical plan-directory helper is ``get_plan_dir(plan_id)`` from
``tools-file-ops:file_ops`` which resolves to
``<repo>/.plan/local/plans/{plan_id}``.  Production scripts must use the
helper rather than constructing the path by hand.

Findings have the shape::

    {
        'rule_id': 'plan-path-in-scripts',
        'file': '<absolute file path>',
        'line': <int, 1-based>,
        'category': 'production_script' | 'test_assertion',
        'snippet': '<line excerpt>',
    }

Public API
----------
- ``analyze_plan_path_in_scripts(marketplace_root)``: entry point — scans
  ``marketplace/bundles/**/scripts/**/*.py`` and emits findings for
  non-whitelisted drift occurrences.
- ``is_whitelisted(file_path)``: returns True when ``file_path`` matches a
  whitelist entry.
"""

from __future__ import annotations

import ast
from pathlib import Path

RULE_ID = 'plan-path-in-scripts'

# ---------------------------------------------------------------------------
# Form A constants
# ---------------------------------------------------------------------------

# The literal string that indicates form-A drift: .plan/plans/ WITHOUT /local/.
# The canonical form is .plan/local/plans/; this marker catches the shorter
# (drifted) form.  String ".plan/local/" is NOT flagged.
_FORM_A_MARKER = '.plan/plans/'

# ---------------------------------------------------------------------------
# Form B constants
# ---------------------------------------------------------------------------

# .plan-domain subdirectory names that are legal join targets only via the
# canonical helpers in file_ops.py.  A parent-walking chain that ultimately
# joins against one of these names is form-B drift.
_PLAN_DOMAIN_DIRS: frozenset[str] = frozenset({
    'plans',
    'lessons-learned',
    'logs',
    'archived-plans',
    'workspace',
})

# ---------------------------------------------------------------------------
# Whitelist — path-component-anchored
# ---------------------------------------------------------------------------
# Each entry is a frozenset of path component names that must ALL be present
# in the file's parts.  Component-presence test, not raw substring of the
# full path string.

_WHITELIST_COMPONENT_SETS: list[frozenset[str]] = [
    # lint-analyzer: this file itself (self-referential — the marker is the
    # detection target).
    frozenset({'_analyze_plan_path_in_scripts.py'}),
    # Canonical source: file_ops.py is the implementation of get_base_dir /
    # get_plan_dir / base_path — never flag it.
    frozenset({'tools-file-ops', 'file_ops.py'}),
]


def is_whitelisted(file_path: Path) -> bool:
    """Return True when ``file_path`` matches any whitelist entry.

    Each whitelist entry is a frozenset of path-component strings that must
    ALL appear as exact matches among the components of ``file_path``.
    """
    parts_set = set(file_path.parts)
    parts_set.add(file_path.name)
    for required_components in _WHITELIST_COMPONENT_SETS:
        if required_components.issubset(parts_set):
            return True
    return False


def _classify(file_path: Path) -> str:
    """Classify a file as ``production_script`` or ``test_assertion``."""
    for part in file_path.parts:
        if part in ('test', 'tests'):
            return 'test_assertion'
    name = file_path.name
    if name.startswith('test_') or name.endswith('_test.py'):
        return 'test_assertion'
    return 'production_script'


# ---------------------------------------------------------------------------
# AST helpers — docstring node identification
# ---------------------------------------------------------------------------


def _collect_docstring_node_ids(tree: ast.Module) -> set[int]:
    """Return the set of ``id()`` values of AST nodes that are docstrings.

    A node is a docstring when it appears as the first statement in a
    module, function, or class body and is an ``ast.Expr(ast.Constant)``
    expression.  These must NOT be flagged as form-A code literals.
    """
    docstring_ids: set[int] = set()
    for node in ast.walk(tree):
        body: list[ast.stmt] | None = None
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
            docstring_ids.add(id(body[0].value))
    return docstring_ids


# ---------------------------------------------------------------------------
# AST helpers — Form A: literal bypass detection
# ---------------------------------------------------------------------------


def _collect_form_a_node_ids(tree: ast.Module, docstring_ids: set[int]) -> list[int]:
    """Return line numbers for form-A findings (literal .plan/plans/ in code context).

    Scans for ``ast.Constant`` nodes whose string value contains ``_FORM_A_MARKER``
    in a code-active path-construction context.  Docstrings (``docstring_ids``)
    are excluded.

    Code-active contexts include:
    - Assignment RHS (``ast.Assign``, ``ast.AnnAssign``, ``ast.AugAssign``)
    - Binary addition (``ast.BinOp`` with ``ast.Add``) — string concatenation
    - ``Path(...)`` constructor argument
    - ``os.path.join(...)`` argument
    - Return values (``ast.Return``)
    - f-string (``ast.JoinedStr``) interpolated values

    Deliberately excluded (documentation positions):
    - Docstrings (module/function/class body first statement)
    - ``print(...)`` call arguments
    - Argparse ``help=`` keyword arguments
    - Any ``ast.Expr`` statement that is not a recognized path-construction call
    """
    findings: list[int] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant):
            continue
        if not isinstance(node.value, str):
            continue
        if _FORM_A_MARKER not in node.value:
            continue
        if id(node) in docstring_ids:
            continue
        # At this point we have a string containing .plan/plans/ that is not
        # a docstring.  We need to determine whether it is in a path-construction
        # context.  Since ast.walk does not give us parent context, we use a
        # conservative approach: any .plan/plans/ string literal that is NOT
        # inside a module/function/class docstring and is NOT the sole argument
        # to a print() call is considered a code-literal hit.
        #
        # The canonical false-positive cases (print(), help=) are handled by
        # the parent-context visitor below.
        findings.append(node.lineno if hasattr(node, 'lineno') else 0)  # type: ignore[attr-defined]

    return findings


class _FormAVisitor(ast.NodeVisitor):
    """Visitor that collects form-A findings with parent-context awareness.

    Walks the AST maintaining a parent stack so that string constants can be
    classified as code-literal (emit finding) or documentation (skip).
    """

    def __init__(self, docstring_ids: set[int]) -> None:
        self._docstring_ids = docstring_ids
        self._findings: list[tuple[int, str]] = []  # (line_no, snippet)
        self._parent_stack: list[ast.AST] = []

    @property
    def findings(self) -> list[tuple[int, str]]:
        return self._findings

    def _in_documentation_context(self) -> bool:
        """Return True when the current node is inside a pure-documentation call.

        Excluded contexts:
        - Argument to ``print(...)`` — informational display strings.
        - ``help=`` keyword argument in a call — argparse annotation.
        """
        for parent in reversed(self._parent_stack):
            if isinstance(parent, ast.Call):
                func = parent.func
                # print(...) call
                if isinstance(func, ast.Name) and func.id == 'print':
                    return True
                # help= keyword arg in any call (argparse add_argument, add_parser, etc.)
                for kw in parent.keywords:
                    if kw.arg == 'help':
                        return True
            # Stop propagating past assignment, return, or binary-op parents
            # (those ARE path-construction contexts)
            if isinstance(parent, (ast.Assign, ast.AnnAssign, ast.Return,
                                   ast.BinOp, ast.JoinedStr)):
                break
        return False

    def generic_visit(self, node: ast.AST) -> None:
        self._parent_stack.append(node)
        super().generic_visit(node)
        self._parent_stack.pop()

    def visit_Constant(self, node: ast.Constant) -> None:  # noqa: N802
        if (
            isinstance(node.value, str)
            and _FORM_A_MARKER in node.value
            and id(node) not in self._docstring_ids
            and not self._in_documentation_context()
        ):
            line_no = getattr(node, 'lineno', 0)
            self._findings.append((line_no, ''))
        self.generic_visit(node)


# ---------------------------------------------------------------------------
# AST helpers — Form B: parent-walking chain detection
# ---------------------------------------------------------------------------


def _is_file_dunder(node: ast.expr) -> bool:
    """Return True when ``node`` is the ``__file__`` name reference."""
    return isinstance(node, ast.Name) and node.id == '__file__'


def _is_path_parent_chain(node: ast.expr) -> bool:
    """Return True when ``node`` is a ``Path(__file__).parent[.parent…]``
    or ``Path(__file__).parents[…]`` chain.
    """
    return _walk_path_chain(node)


def _walk_path_chain(node: ast.expr) -> bool:
    """Recursive helper for _is_path_parent_chain."""
    # Path(__file__) — the root of any chain
    if isinstance(node, ast.Call):
        func = node.func
        is_path_call = (isinstance(func, ast.Name) and func.id == 'Path') or (
            isinstance(func, ast.Attribute)
            and func.attr == 'Path'
            and isinstance(func.value, ast.Name)
            and func.value.id == 'pathlib'
        )
        if is_path_call and len(node.args) == 1 and _is_file_dunder(node.args[0]):
            return True

    # <chain>.parent
    if isinstance(node, ast.Attribute) and node.attr == 'parent':
        return _walk_path_chain(node.value)

    # <chain>.parents[N]
    if isinstance(node, ast.Subscript):
        if isinstance(node.value, ast.Attribute) and node.value.attr == 'parents':
            return _walk_path_chain(node.value.value)

    return False


def _is_os_dirname_chain(node: ast.expr) -> bool:
    """Return True when ``node`` is an ``os.path.dirname(__file__)`` or
    nested ``os.path.dirname(os.path.dirname(…))`` chain.
    """
    if isinstance(node, ast.Call):
        func = node.func
        if (
            isinstance(func, ast.Attribute)
            and func.attr == 'dirname'
            and isinstance(func.value, ast.Attribute)
            and func.value.attr == 'path'
            and isinstance(func.value.value, ast.Name)
            and func.value.value.id == 'os'
        ):
            if len(node.args) == 1:
                arg = node.args[0]
                return _is_file_dunder(arg) or _is_os_dirname_chain(arg)
    return False


def _is_parent_walking_root(node: ast.expr) -> bool:
    """Return True when ``node`` is a file-relative parent-walking expression."""
    return _is_path_parent_chain(node) or _is_os_dirname_chain(node)


def _extract_joined_string(node: ast.expr) -> str | None:
    """Attempt to extract the rightmost string component from a Path division
    or os.path.join call rooted in a parent-walking expression.

    Returns the string value of the rightmost ``ast.Constant`` component
    (the subdirectory name being joined), or None when the pattern is not
    recognised.
    """
    # Unwrap str(...) wrapper
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == 'str'
        and len(node.args) == 1
    ):
        return _extract_joined_string(node.args[0])

    # Path(<chain>, "subdir", ...) constructor
    if isinstance(node, ast.Call):
        func = node.func
        is_path_call = (isinstance(func, ast.Name) and func.id == 'Path') or (
            isinstance(func, ast.Attribute)
            and func.attr == 'Path'
            and isinstance(func.value, ast.Name)
            and func.value.id == 'pathlib'
        )
        if is_path_call and len(node.args) >= 2:
            if _is_parent_walking_root(node.args[0]):
                parts = []
                for arg in node.args[1:]:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        parts.append(arg.value)
                if parts:
                    return parts[0]

        # os.path.join(<chain>, "subdir", ...)
        if (
            isinstance(func, ast.Attribute)
            and func.attr == 'join'
            and isinstance(func.value, ast.Attribute)
            and func.value.attr == 'path'
            and isinstance(func.value.value, ast.Name)
            and func.value.value.id == 'os'
        ):
            if len(node.args) >= 2 and _is_parent_walking_root(node.args[0]):
                second = node.args[1]
                if isinstance(second, ast.Constant) and isinstance(second.value, str):
                    return second.value

    # <chain> / "subdir" — BinOp with Div operator
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        right = node.right
        if isinstance(right, ast.Constant) and isinstance(right.value, str):
            if _lhs_rooted_in_parent_chain(node.left):
                return right.value
    return None


def _lhs_rooted_in_parent_chain(node: ast.expr) -> bool:
    """Return True when the left-hand side of a BinOp chain is ultimately
    rooted in a parent-walking expression.
    """
    if _is_parent_walking_root(node):
        return True
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        return _lhs_rooted_in_parent_chain(node.left)
    return False


def _collect_sys_path_insert_arg_lines(tree: ast.Module) -> set[int]:
    """Return the set of line numbers that are arguments to sys.path.insert /
    sys.path.append calls (import-bootstrap chains exempt from form-B).
    """
    exempt_lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            func = call.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr in ('insert', 'append')
                and isinstance(func.value, ast.Attribute)
                and func.value.attr == 'path'
                and isinstance(func.value.value, ast.Name)
                and func.value.value.id == 'sys'
            ):
                for arg in call.args:
                    for sub in ast.walk(arg):
                        if hasattr(sub, 'lineno'):
                            exempt_lines.add(sub.lineno)  # type: ignore[attr-defined]
    return exempt_lines


# ---------------------------------------------------------------------------
# File scanner
# ---------------------------------------------------------------------------


def _scan_file(file_path: Path) -> list[dict]:
    """Scan one Python file for plan-path drift using AST analysis.

    Detects:
    - **Form A**: string constants containing ``.plan/plans/`` (without
      ``/local/``) in code-active (path-construction) contexts.
    - **Form B**: ``Path(__file__).parent…`` / ``os.path.dirname(__file__)``
      chains joined against a ``.plan``-domain subdirectory name.

    Exemptions applied:
    - Module/function/class docstrings are excluded from form-A detection.
    - ``print()`` and ``help=`` annotation strings are excluded from form-A.
    - Lines in ``sys.path.insert`` / ``sys.path.append`` arguments are exempt
      from form-B detection.
    """
    try:
        text = file_path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(text, filename=str(file_path))
    except SyntaxError:
        return []

    lines = text.splitlines()
    findings: list[dict] = []
    category = _classify(file_path)

    # Collect docstring node ids for form-A exclusion
    docstring_ids = _collect_docstring_node_ids(tree)

    # Collect sys.path-insert exempt lines for form-B exclusion
    sys_path_exempt_lines = _collect_sys_path_insert_arg_lines(tree)

    # ---------------------------------------------------------------------------
    # Form A: parent-context-aware visitor
    # ---------------------------------------------------------------------------
    visitor = _FormAVisitor(docstring_ids)
    visitor.visit(tree)
    seen_form_a_lines: set[int] = set()
    for line_no, _ in visitor.findings:
        if line_no and line_no not in seen_form_a_lines:
            seen_form_a_lines.add(line_no)
            snippet = lines[line_no - 1].strip()[:120] if line_no <= len(lines) else ''
            findings.append(
                {
                    'rule_id': RULE_ID,
                    'file': str(file_path),
                    'line': line_no,
                    'category': category,
                    'snippet': snippet,
                }
            )

    # ---------------------------------------------------------------------------
    # Form B: parent-walking chain detection
    # ---------------------------------------------------------------------------
    seen_form_b_lines: set[int] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.expr):
            continue
        line_no = getattr(node, 'lineno', 0)
        if not line_no:
            continue
        if line_no in sys_path_exempt_lines:
            continue
        if line_no in seen_form_b_lines:
            continue

        joined = _extract_joined_string(node)
        if joined is not None and joined in _PLAN_DOMAIN_DIRS:
            seen_form_b_lines.add(line_no)
            snippet = lines[line_no - 1].strip()[:120] if line_no <= len(lines) else ''
            findings.append(
                {
                    'rule_id': RULE_ID,
                    'file': str(file_path),
                    'line': line_no,
                    'category': category,
                    'snippet': snippet,
                }
            )

    return findings


def analyze_plan_path_in_scripts(marketplace_root: Path) -> list[dict]:
    """Scan marketplace bundle scripts for non-whitelisted plan-path references.

    Scans:
    - ``<marketplace_root>/bundles/**/skills/*/scripts/**/*.py``

    Two drift forms are detected (see module docstring for full specification):
    - Form A: string constants containing ``.plan/plans/`` in path-construction
      contexts (code literals, not docstrings or annotation strings).
    - Form B: ``Path(__file__).parent…`` chains joined to ``.plan``-domain dirs.

    Test files are scanned but their findings are categorised as
    ``test_assertion`` rather than ``production_script`` so callers can apply
    different triage.

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

    bundles_root = marketplace_root / 'bundles'
    if not bundles_root.is_dir():
        return []

    for py_file in sorted(bundles_root.rglob('*.py')):
        if not py_file.is_file():
            continue
        if is_whitelisted(py_file):
            continue
        findings.extend(_scan_file(py_file))

    return findings
