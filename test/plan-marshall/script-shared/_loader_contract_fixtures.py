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
#: and loses the registration entirely. It is the second most common of the three
#: shapes and about a quarter of all loader call sites, so getting it wrong hid a
#: whole class of registration without emptying the guard.
REGISTERING_HELPERS: dict[str, bool] = {
    'load_script_module': True,
    'load_skill_module': True,
    'parse_ns': False,
}


#: The single construction both loaders funnel through, and so the marker that
#: identifies a registering helper without anyone listing one.
REGISTRATION_PRIMITIVE = '_exec_module_from_path'


def _module_level_call_names(tree: ast.Module) -> dict[str, set[str]]:
    """Return each module-level function's name mapped to the names it calls."""
    calls: dict[str, set[str]] = {}
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        called: set[str] = set()
        for inner in ast.walk(node):
            if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Name):
                called.add(inner.func.id)
        calls[node.name] = called
    return calls


def registering_helpers_in_conftest(conftest_path: Path) -> set[str]:
    """Return the PUBLIC ``conftest`` helpers that publish a module in ``sys.modules``.

    Derived from the live source rather than copied from it, which is what keeps
    :data:`REGISTERING_HELPERS` an assertion about ``conftest`` instead of a mirror
    that can silently fall behind it. A helper registers when it calls
    :data:`REGISTRATION_PRIMITIVE` -- the one construction both loaders funnel
    through, by that function's own contract -- or when it delegates to a helper
    that does. Both hops occur today: the two loaders take the first, ``parse_ns``
    the second.

    A fourth loader added later is therefore covered by the scan without anyone
    remembering to list it, and one added by some route that bypasses the primitive
    makes this derivation disagree with the declared mapping, which is a red build
    rather than a silent gap.
    """
    tree = ast.parse(conftest_path.read_text(encoding='utf-8'), filename=str(conftest_path))
    calls = _module_level_call_names(tree)

    registering = {name for name, called in calls.items() if REGISTRATION_PRIMITIVE in called}
    grew = True
    while grew:
        grew = False
        for name, called in calls.items():
            if name not in registering and called & registering:
                registering.add(name)
                grew = True
    return {name for name in registering if not name.startswith('_')}


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


#: Positional indices in every helper here: ``(bundle, skill, script[, module_name])``.
SCRIPT_ARG_INDEX = 2
MODULE_NAME_ARG_INDEX = 3


def _positionals_are_indexable(call: ast.Call) -> bool:
    """Return whether the call's positionals can be read by index.

    ⚠️ This and the ``.py`` suffix check in :func:`_registered_name` are REDUNDANT
    with each other on the current tree: removing either alone changes no result,
    because the other still rejects the two sites where unpacking shifts the index.
    Only removing both reintroduces the defect. They are kept as a pair because they
    fail differently — this one refuses to guess, the suffix check refuses to
    believe — and the mutation record says so rather than claiming each is
    independently load-bearing.

    A ``*args`` unpacking BEFORE the script position makes every later index
    meaningless — ``parse_ns(*_SCRIPT, '--plan-id', p)`` has no script at index 2.
    Reading one anyway yields a confident wrong answer (the flag token) rather than
    a visible gap, which is the same failure as mistaking ``parse_ns``'s fourth
    positional for a module name. A star AFTER the script is the ordinary
    ``*argv`` spelling and disturbs nothing.
    """
    for index, argument in enumerate(call.args):
        if isinstance(argument, ast.Starred):
            return index > SCRIPT_ARG_INDEX
    return True


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
    indexable = _positionals_are_indexable(call)
    if takes_module_name:
        # The KEYWORD spelling is immune to unpacking, so it is read first and
        # without the indexability guard: ``load_script_module(*_PAIR, 'x.py',
        # module_name='y')`` names its registration unambiguously however the
        # earlier arguments arrived.
        for keyword in call.keywords:
            if keyword.arg == 'module_name':
                return _string_value(keyword.value, constants)
        if indexable and len(call.args) > MODULE_NAME_ARG_INDEX:
            return _string_value(call.args[MODULE_NAME_ARG_INDEX], constants)
    if indexable and len(call.args) > SCRIPT_ARG_INDEX:
        script = _string_value(call.args[SCRIPT_ARG_INDEX], constants)
        # A script argument ends in ``.py``. Requiring that is what makes reading
        # the WRONG position fail visibly instead of confidently: a subcommand
        # (``'run'``) or a flag (``'--plan-id'``) reached by a mis-counted index
        # lands here, and returning None puts it in the disclosed unresolved tally
        # rather than inventing a registration that does not exist.
        if script and script.endswith('.py'):
            return Path(script).stem
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
