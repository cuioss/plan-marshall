#!/usr/bin/env python3
"""cmd_* find_marketplace_root anchoring analyzer.

This module implements the ``cmd-root-anchoring-missing`` rule, which checks
that every ``cmd_*`` function in a dispatcher script:

1. Opens with a ``find_marketplace_root(...)`` call (the "prelude"), and
2. Has a corresponding argparse subparser that declares a
   ``--marketplace-root`` flag.

The rule ensures that dispatcher subcommands are properly anchored to the
marketplace root directory, rather than relying on an implicit working
directory assumption that breaks when the script is called from an unexpected
location.

Detection algorithm (AST-based)
---------------------------------
1. Parse the target script with ``ast.parse``.
2. Identify "dispatcher scripts" via a configurable heuristic: scripts whose
   argparse subparsers use ``set_defaults(func=cmd_*)`` for at least one
   ``cmd_*`` function.  (Scripts that do not follow the ``cmd_*`` convention
   are out of scope.)
3. For each ``cmd_*`` function defined at module top level:
   a. Check the function body for a ``find_marketplace_root(...)`` call
      in the first few (up to ``_PRELUDE_LOOK_AHEAD``) non-trivial
      statements.  Comments and type aliases between statements are allowed
      (order-tolerant check).
   b. Identify the argparse subparser registered for this command via the
      ``set_defaults(func=cmd_*)`` link and check whether it declares a
      ``--marketplace-root`` flag.
4. Functions missing either piece emit a finding with the appropriate
   ``missing`` value.

Findings have the shape::

    {
        'rule_id': 'cmd-root-anchoring-missing',
        'file': '<absolute script path>',
        'line': <int, 1-based line of the function def>,
        'function_name': 'cmd_something',
        'missing': 'prelude' | 'flag' | 'both',
    }

Public API
----------
- ``analyze_cmd_root_anchoring(script_path)``: entry point — scans one
  Python script and returns findings.
"""

from __future__ import annotations

import ast
from pathlib import Path

RULE_ID = 'cmd-root-anchoring-missing'

# Maximum number of top-level statements to look at in the function body
# when searching for the ``find_marketplace_root`` prelude.  Comments and
# type aliases between assignments do not count toward this limit.
_PRELUDE_LOOK_AHEAD = 10

# The canonical function name that must appear in the prelude.
_ROOT_FUNC_NAME = 'find_marketplace_root'

# The flag that must be declared on the corresponding subparser.
_MARKETPLACE_ROOT_FLAG = '--marketplace-root'


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _call_func_name(node: ast.Call) -> str | None:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


def _attr_receiver_name(call: ast.Call) -> str | None:
    func = call.func
    if not isinstance(func, ast.Attribute):
        return None
    value = func.value
    if isinstance(value, ast.Name):
        return value.id
    return None


def _first_string_arg(node: ast.Call) -> str | None:
    if not node.args:
        return None
    arg0 = node.args[0]
    if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
        return arg0.value
    return None


# ---------------------------------------------------------------------------
# Prelude detection
# ---------------------------------------------------------------------------


def _has_root_prelude(func: ast.FunctionDef) -> bool:
    """Return True when ``func`` contains a ``find_marketplace_root(...)`` call.

    The check is order-tolerant: it looks through all statements in the
    function body (up to ``_PRELUDE_LOOK_AHEAD`` non-trivial ones) rather
    than demanding the call appears at a fixed line number.  This allows
    comments, docstrings, and local assignments to appear between the function
    signature and the ``find_marketplace_root`` call.
    """
    checked = 0
    for stmt in ast.walk(func):
        if isinstance(stmt, ast.Call):
            name = _call_func_name(stmt)
            if name == _ROOT_FUNC_NAME:
                return True
        if isinstance(stmt, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Expr)):
            checked += 1
            if checked > _PRELUDE_LOOK_AHEAD:
                break
    return False


# ---------------------------------------------------------------------------
# Subparser mapping builder
# ---------------------------------------------------------------------------


def _build_subparser_flag_map(tree: ast.AST) -> tuple[dict[str, str], dict[str, list[str]]]:
    """Build two mappings from the AST.

    Returns:
        func_to_parser_var: handler-function-name → parser-variable-name
        parser_flags: parser-variable-name → list of declared flags

    The first mapping is built from ``set_defaults(func=cmd_*)`` calls.
    The second is built from ``add_argument('--flag', ...)`` calls.
    """
    func_to_parser_var: dict[str, str] = {}
    parser_flags: dict[str, list[str]] = {}

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        name = _call_func_name(node)

        if name == 'set_defaults':
            receiver = _attr_receiver_name(node)
            if receiver is None:
                continue
            for kw in node.keywords:
                if kw.arg == 'func' and isinstance(kw.value, ast.Name):
                    func_to_parser_var[kw.value.id] = receiver

        elif name == 'add_argument':
            receiver = _attr_receiver_name(node)
            if receiver is None:
                continue
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    if arg.value.startswith('--'):
                        parser_flags.setdefault(receiver, []).append(arg.value)

    return func_to_parser_var, parser_flags


# ---------------------------------------------------------------------------
# Dispatcher heuristic
# ---------------------------------------------------------------------------


def _is_dispatcher_script(tree: ast.AST) -> bool:
    """Return True when the script looks like a dispatcher.

    Heuristic: at least one ``set_defaults(func=<Name>)`` call where the
    function name starts with ``cmd_``.  Scripts that don't use this pattern
    are out of scope.
    """
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _call_func_name(node) != 'set_defaults':
            continue
        for kw in node.keywords:
            if kw.arg == 'func' and isinstance(kw.value, ast.Name):
                if kw.value.id.startswith('cmd_'):
                    return True
    return False


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def analyze_cmd_root_anchoring(script_path: Path) -> list[dict]:
    """Scan ``script_path`` for ``cmd_*`` functions missing the root anchoring prelude or flag.

    Only applies to dispatcher scripts (those with ``set_defaults(func=cmd_*)``).
    Scripts without this pattern are returned with an empty findings list.

    Parameters
    ----------
    script_path:
        Absolute path to a Python script to analyze.

    Returns
    -------
    list[dict]
        Findings for ``cmd_*`` functions missing the prelude and/or the flag.
        Empty for clean scripts, non-dispatcher scripts, unreadable files,
        or files with syntax errors.
    """
    try:
        source = script_path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source, filename=str(script_path))
    except SyntaxError:
        return []

    if not _is_dispatcher_script(tree):
        return []

    func_to_parser_var, parser_flags = _build_subparser_flag_map(tree)

    # Collect all top-level cmd_* function definitions.
    cmd_functions: list[ast.FunctionDef] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith('cmd_'):
                cmd_functions.append(node)

    findings: list[dict] = []

    for func in cmd_functions:
        has_prelude = _has_root_prelude(func)

        parser_var = func_to_parser_var.get(func.name)
        has_flag = False
        if parser_var is not None:
            flags_for_parser = parser_flags.get(parser_var, [])
            has_flag = _MARKETPLACE_ROOT_FLAG in flags_for_parser

        if not has_prelude and not has_flag:
            missing = 'both'
        elif not has_prelude:
            missing = 'prelude'
        elif not has_flag:
            missing = 'flag'
        else:
            continue  # both present — compliant

        findings.append(
            {
                'rule_id': RULE_ID,
                'file': str(script_path),
                'line': func.lineno,
                'function_name': func.name,
                'missing': missing,
            }
        )

    return findings
