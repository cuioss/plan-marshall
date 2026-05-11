#!/usr/bin/env python3
"""Orphan-argparse-flags analyzer for the ``orphan-argparse-flag`` rule.

This module detects ``argparse`` flags that are declared in a ``manage-*``
script but never read in the corresponding subcommand handler body.  Orphan
flags accumulate when configuration keys are removed or renamed without also
removing the argparse declaration — they create a false user interface that
accepts an argument that has no effect.

Detection algorithm (AST-based)
--------------------------------
1. Parse the target script with ``ast.parse``.
2. Walk the AST to build a subparser tree using the same logic as
   ``_analyze_verb_chains.py`` (``build_subparser_tree``).
3. For each registered subparser, collect the ``add_argument(...)`` calls
   attached to that parser variable and note the ``dest`` names (derived
   from the longest ``--flag-name`` by replacing ``-`` with ``_``).
4. For each flag's handler function (resolved via ``set_defaults(func=...)``
   or by name convention ``cmd_{subcommand}``), check whether ``args.{dest}``
   or a safe-access pattern (``vars(args)``, ``**kwargs``) appears anywhere
   in the function body.
5. Flags that are never read — and whose handler does not use ``vars(args)``
   or ``**kwargs`` (which makes static analysis impossible) — emit a finding.

Safe-access exception
---------------------
When a handler uses ``vars(args)``, ``getattr(args, ...)`` with a variable
attribute name, or ``**vars(args)`` / ``**{...}`` unpacking, the analyzer
CANNOT prove that a given flag is unused.  In that case it emits NO finding
for any flag in that handler (conservative / no-over-fire rule).

Findings have the shape::

    {
        'rule_id': 'orphan-argparse-flag',
        'file': '<absolute script path>',
        'line': <int, 1-based line of the add_argument call>,
        'flag_name': '--flag-name',
        'subcommand': '<registered subparser verb>',
    }

Public API
----------
- ``analyze_orphan_argparse_flags(script_path)``: entry point — scans one
  Python script and returns findings.
"""

from __future__ import annotations

import ast
from pathlib import Path

RULE_ID = 'orphan-argparse-flag'

# ---------------------------------------------------------------------------
# AST helpers (reuse patterns from _analyze_verb_chains.py)
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


def _kw_string(call: ast.Call, kwname: str) -> str | None:
    for kw in call.keywords:
        if kw.arg == kwname and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
            return kw.value.value
    return None


# ---------------------------------------------------------------------------
# Flag declaration collector
# ---------------------------------------------------------------------------


def _flag_dest(flag_name: str) -> str:
    """Convert ``--flag-name`` to dest attribute name ``flag_name``."""
    stripped = flag_name.lstrip('-')
    return stripped.replace('-', '_')


def _collect_flag_declarations(
    tree: ast.AST,
    parser_var_names: set[str],
) -> list[dict]:
    """Collect ``add_argument(...)`` calls attached to known parser variables.

    Returns a list of dicts:
        {var: <parser_var_name>, flag_name: '--foo', dest: 'foo', line: N}
    """
    declarations: list[dict] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _call_func_name(node) != 'add_argument':
            continue
        receiver = _attr_receiver_name(node)
        if receiver is None or receiver not in parser_var_names:
            continue
        # Find the flag name (first positional arg starting with '--')
        flag = None
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                if arg.value.startswith('--'):
                    flag = arg.value
                    break
        if flag is None:
            continue
        # Explicit dest kwarg overrides the default derivation.
        dest = _kw_string(node, 'dest') or _flag_dest(flag)
        declarations.append(
            {
                'var': receiver,
                'flag_name': flag,
                'dest': dest,
                'line': node.lineno,
            }
        )
    return declarations


# ---------------------------------------------------------------------------
# Subparser → handler mapping
# ---------------------------------------------------------------------------


def _collect_set_defaults(tree: ast.AST) -> dict[str, str]:
    """Return a mapping of parser-variable-name → handler-function-name.

    Recognises ``p_foo.set_defaults(func=cmd_foo)`` patterns.
    """
    mapping: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _call_func_name(node) != 'set_defaults':
            continue
        receiver = _attr_receiver_name(node)
        if receiver is None:
            continue
        for kw in node.keywords:
            if kw.arg == 'func' and isinstance(kw.value, ast.Name):
                mapping[receiver] = kw.value.id
    return mapping


def _collect_function_bodies(tree: ast.AST) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    """Return a mapping of function-name → FunctionDef node (sync or async)."""
    funcs: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs[node.name] = node
    return funcs


# ---------------------------------------------------------------------------
# Handler usage analysis
# ---------------------------------------------------------------------------


def _handler_uses_vars_args(func_body: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    """Return True when the handler uses ``vars(args)`` or ``**kwargs``-like patterns.

    When True, static analysis cannot determine which attrs are accessed —
    emit no findings for that handler (conservative no-over-fire rule).
    """
    for node in ast.walk(func_body):
        # vars(args) call
        if isinstance(node, ast.Call):
            if _call_func_name(node) == 'vars':
                return True
            # getattr(args, variable_name) — dynamic attribute access
            if _call_func_name(node) == 'getattr':
                return True
        # **vars(args) or **kwargs dict unpacking
        if isinstance(node, ast.keyword) and node.arg is None:
            return True
    return False


def _handler_reads_attr(func_body: ast.FunctionDef | ast.AsyncFunctionDef, dest: str) -> bool:
    """Return True when ``func_body`` contains ``args.{dest}`` attribute access."""
    for node in ast.walk(func_body):
        if isinstance(node, ast.Attribute):
            attr = node.attr
            if attr == dest:
                return True
    return False


# ---------------------------------------------------------------------------
# Subparser tree builder (minimal version — only track var names and verbs)
# ---------------------------------------------------------------------------


def _build_parser_var_map(tree: ast.AST) -> tuple[dict[str, str], dict[str, str]]:
    """Build two mappings from the AST.

    Returns:
        parser_to_verb: parser-variable-name → verb registered with add_parser
        subs_to_parser: subparsers-handle-variable → owning parser variable

    Both root parser variables (ArgumentParser) map to an empty string for verb.
    """
    parser_to_verb: dict[str, str] = {}  # var → verb ('' for root)
    subs_to_parser: dict[str, str] = {}  # subparsers-handle → parent parser var

    assignments: list[ast.Assign] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            assignments.append(node)
    assignments.sort(key=lambda a: (a.lineno, a.col_offset))

    for stmt in assignments:
        if not isinstance(stmt.value, ast.Call):
            continue
        call = stmt.value
        name = _call_func_name(call)
        targets = [t.id for t in stmt.targets if isinstance(t, ast.Name)]
        if not targets:
            continue

        if name == 'ArgumentParser':
            for var in targets:
                parser_to_verb[var] = ''

        elif name == 'add_subparsers':
            owner = _attr_receiver_name(call)
            if owner and owner in parser_to_verb:
                for var in targets:
                    subs_to_parser[var] = owner

        elif name == 'add_parser':
            handle = _attr_receiver_name(call)
            if handle and handle in subs_to_parser:
                verb = _first_string_arg(call) or ''
                for var in targets:
                    parser_to_verb[var] = verb

    return parser_to_verb, subs_to_parser


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def analyze_orphan_argparse_flags(script_path: Path) -> list[dict]:
    """Scan ``script_path`` for declared argparse flags that are never read.

    Parameters
    ----------
    script_path:
        Absolute path to a Python script to analyze.

    Returns
    -------
    list[dict]
        Findings for orphan flags.  Empty for a clean script, an unreadable
        file, or one where static analysis cannot determine usage
        (e.g. handler uses ``vars(args)``).
    """
    try:
        source = script_path.read_text(encoding='utf-8')
    except (OSError, UnicodeDecodeError):
        return []

    try:
        tree = ast.parse(source, filename=str(script_path))
    except SyntaxError:
        return []

    # Build parser variable → verb mapping.
    parser_to_verb, subs_to_parser = _build_parser_var_map(tree)
    all_parser_vars = set(parser_to_verb.keys())

    # Collect flag declarations attached to any parser variable.
    flag_decls = _collect_flag_declarations(tree, all_parser_vars)
    if not flag_decls:
        return []

    # Build set_defaults → handler mapping.
    set_defaults_map = _collect_set_defaults(tree)

    # Build function-name → function-body mapping.
    func_bodies = _collect_function_bodies(tree)

    findings: list[dict] = []

    for decl in flag_decls:
        parser_var = decl['var']
        verb = parser_to_verb.get(parser_var, '')
        flag_name = decl['flag_name']
        dest = decl['dest']

        # Determine the handler for this parser variable.
        # Primary: set_defaults(func=...) on the same parser variable.
        handler_name = set_defaults_map.get(parser_var)

        # Fallback: if the verb is non-empty try the conventional name cmd_{verb}.
        if handler_name is None and verb:
            candidate = 'cmd_' + verb.replace('-', '_')
            if candidate in func_bodies:
                handler_name = candidate

        if handler_name is None:
            # No handler found — cannot determine usage, skip conservatively.
            continue

        handler = func_bodies.get(handler_name)
        if handler is None:
            continue

        # Conservative: if handler uses vars(args) or dynamic access, skip.
        if _handler_uses_vars_args(handler):
            continue

        # Check whether the handler body reads args.{dest}.
        if not _handler_reads_attr(handler, dest):
            findings.append(
                {
                    'rule_id': RULE_ID,
                    'file': str(script_path),
                    'line': decl['line'],
                    'flag_name': flag_name,
                    'subcommand': verb or '<root>',
                }
            )

    return findings
