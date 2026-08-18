#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Static-scan machinery for the shared loader's ``sys.modules`` contract.

Walks the test tree and answers two questions the guard in
``test_conftest_loader_contract.py`` asserts on: which module names a file-load
publishes, and which names are imported plainly. Both are derived from the tree
rather than listed, so a call site added later is covered without anyone
remembering.
"""

import ast
from collections import defaultdict
from pathlib import Path

from conftest import TEST_ROOT

#: Helpers whose call publishes a module in ``sys.modules``, mapped to whether the
#: helper accepts a ``module_name`` override.
#:
#: ⛔ ``parse_ns`` does NOT. Its signature is ``(bundle, skill, script, *argv)``, so
#: its fourth positional is the first ARGV TOKEN, not a module name — reading it as
#: one attributes the call to a subcommand string (``'run'``, ``'read'``, ``'list'``)
#: and loses the registration entirely. It is by far the most common of the three
#: call shapes, so getting this wrong makes the guard inert on its main input.
REGISTERING_HELPERS: dict[str, bool] = {
    'load_script_module': True,
    'load_skill_module': True,
    'parse_ns': False,
}


def _module_level_string_constants(tree: ast.Module) -> dict[str, str]:
    """Return the module-level ``NAME = 'literal'`` bindings in ``tree``.

    Loader arguments are frequently hoisted into module constants, so resolving
    them is what keeps the enumeration below from silently missing those call sites.
    """
    constants: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not (isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                constants[target.id] = node.value.value
    return constants


def _string_value(node: ast.AST | None, constants: dict[str, str]) -> str | None:
    """Resolve ``node`` to a string, through a module-level constant if need be."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name):
        return constants.get(node.id)
    return None


def _opts_out_of_registration(call: ast.Call) -> bool:
    """Return whether ``call`` passes a literal ``register=False``.

    The single reading of that argument, so the name resolution below and the
    unresolved-site tally cannot disagree about which calls publish anything.
    """
    for keyword in call.keywords:
        if keyword.arg == 'register' and isinstance(keyword.value, ast.Constant):
            return keyword.value.value is False
    return False


def _registered_name(
    call: ast.Call, constants: dict[str, str], takes_module_name: bool
) -> str | None:
    """Return the ``sys.modules`` name ``call`` publishes, or ``None``.

    ``None`` covers both a call that publishes nothing (``register=False``) and one
    whose name cannot be resolved statically; the two are separated by the caller.

    ``takes_module_name`` is why this is not one rule for all three helpers: only the
    two loaders accept an override, and only for them is a fourth positional a module
    name rather than an argv token.
    """
    if _opts_out_of_registration(call):
        return None
    if takes_module_name:
        keywords = {kw.arg: kw.value for kw in call.keywords}
        explicit = keywords.get('module_name') or (call.args[3] if len(call.args) > 3 else None)
        if explicit is not None:
            return _string_value(explicit, constants)
    if len(call.args) > 2:
        script = _string_value(call.args[2], constants)
        return Path(script).stem if script else None
    return None


def _scan_test_tree() -> tuple[dict[str, set[str]], dict[str, set[str]], list[str]]:
    """Return (names registered by a file-load, names imported plainly, unresolved sites).

    Both mappings are derived by walking every module under the test tree, so a call
    site added later is covered without anyone remembering to list it.
    """
    registered: dict[str, set[str]] = defaultdict(set)
    plain: dict[str, set[str]] = defaultdict(set)
    unresolved: list[str] = []

    for path in sorted(TEST_ROOT.rglob('*.py')):
        rel = str(path.relative_to(TEST_ROOT))
        try:
            tree = ast.parse(path.read_text(encoding='utf-8', errors='replace'), filename=rel)
        except SyntaxError:
            continue
        constants = _module_level_string_constants(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                name = (
                    func.attr
                    if isinstance(func, ast.Attribute)
                    else func.id
                    if isinstance(func, ast.Name)
                    else None
                )
                if name not in REGISTERING_HELPERS:
                    continue
                registered_as = _registered_name(node, constants, REGISTERING_HELPERS[name])
                if registered_as:
                    registered[registered_as].add(rel)
                elif not _opts_out_of_registration(node):
                    unresolved.append(f'{rel}:{node.lineno}')
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if '.' not in alias.name:
                        plain[alias.name].add(rel)
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module and '.' not in node.module:
                    plain[node.module].add(rel)
    return registered, plain, unresolved
