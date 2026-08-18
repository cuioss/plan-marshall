#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the shared loader's addressing reach and its ``sys.modules`` hazard.

Two contracts of ``test/conftest.py``'s loader pair:

* **Reach** — ``load_skill_module`` / ``get_skill_dir`` address a module at a
  skill's ROOT. Without them the only module a bundle's ``plan-marshall-plugin``
  skill ships, its ``extension.py``, is unreachable through the shared helpers,
  because most such skills have no ``scripts/`` directory for the scripts-relative
  pair to resolve against.
* **Registration** — a module loaded by file is published in ``sys.modules`` under
  its stem, which REPLACES whatever that name held. A test module that imports the
  same name plainly then holds a copy no longer reachable through ``sys.modules``,
  and reloading it fails depending on collection order — a flaky green rather than
  a clean red. The guard below enumerates the names the loaders are actually called
  with and fails when that set of collisions grows.
"""

import ast
import sys
from collections import defaultdict
from pathlib import Path

import pytest

from conftest import (
    MARKETPLACE_ROOT,
    TEST_ROOT,
    get_scripts_dir,
    get_skill_dir,
    load_script_module,
    load_skill_module,
    parse_ns,
)

#: The skill every bundle uses for its plan-marshall extension entry point.
EXTENSION_SKILL = 'plan-marshall-plugin'

#: Helpers whose call publishes a module in ``sys.modules``. ``parse_ns`` belongs
#: here because it loads the script through ``load_script_module`` to reach the
#: parser, so it registers exactly as the direct call does.
REGISTERING_HELPERS = frozenset({'load_script_module', 'load_skill_module', 'parse_ns'})

#: How many loader call sites the walker cannot resolve statically today. Asserted
#: as a ceiling so the guard's blind spot is a visible, non-growing quantity rather
#: than an unstated narrowing of what it checks.
UNRESOLVED_CALL_SITE_BOUND = 88

#: Names a file-load registers that some test module ALSO imports plainly.
#:
#: Each entry is a live collision, not an approved pattern: the loaded copy
#: displaces the imported one, and only collection order decides whether that is
#: observable. They are pinned rather than fixed because the call sites are spread
#: across directories this module does not own.
#:
#: ⛔ The guard is a growth check, so this baseline is the ONLY thing standing
#: between a new collision and a silent flaky green. Never add a name here to make
#: a red build pass — pass ``register=False`` to the loader (or ``parse_ns``) at the
#: new call site instead, which is what the escape exists for. Remove a name when
#: its collision is genuinely gone; a stale entry fails its own test below.
KNOWN_REGISTRATION_COLLISIONS = frozenset({
    '_architecture_core',
    '_build_execute_factory',
    '_cmd_effort',
    '_config_defaults',
    '_cred_edit',
    '_findings_core',
    '_github_pr',
    '_gradle_cmd_discover',
    '_gradle_execute',
    '_maven_execute',
    '_pyproject_execute',
    'effort_presets',
    'finalize_step_presets',
    'github_pr',
    'manage_terminal_title',
    'plan_logging',
    'recipe_scoring',
    'review_completeness',
    'run_config',
})


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


def _registered_name(call: ast.Call, constants: dict[str, str]) -> str | None:
    """Return the ``sys.modules`` name ``call`` publishes, or ``None``.

    ``None`` covers both a call that publishes nothing (``register=False``) and one
    whose name cannot be resolved statically; the two are separated by the caller.
    """
    if _opts_out_of_registration(call):
        return None
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
                registered_as = _registered_name(node, constants)
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


@pytest.fixture(scope='module')
def tree_scan():
    """The registered-name and plain-import maps derived from the whole test tree."""
    return _scan_test_tree()


# ---------------------------------------------------------------------------
# Reach — a module at the skill root
# ---------------------------------------------------------------------------


def _bundles_with_a_root_extension() -> list[str]:
    """Return every bundle shipping ``skills/plan-marshall-plugin/extension.py``."""
    return sorted(
        path.parents[2].name
        for path in MARKETPLACE_ROOT.glob(f'*/skills/{EXTENSION_SKILL}/extension.py')
    )


def test_the_root_extension_shape_is_present():
    """Bundles ship their extension entry point at the skill root.

    The precondition every case below depends on: without it they would pass
    against an empty population and prove nothing.
    """
    assert len(_bundles_with_a_root_extension()) >= 5


@pytest.mark.parametrize('bundle', _bundles_with_a_root_extension())
def test_skill_root_extension_is_loadable(bundle):
    """Every bundle's root-level ``extension.py`` loads through the shared loader."""
    module = load_skill_module(bundle, EXTENSION_SKILL, 'extension.py', register=False)

    assert hasattr(module, 'Extension')


def test_skill_dir_resolves_a_skill_that_ships_no_scripts_tree():
    """``get_skill_dir`` reaches a skill the scripts-relative accessor cannot.

    Both halves are asserted together because the contrast is the reason the
    skill-root accessor exists: a skill with no ``scripts/`` directory is addressable
    by one and raises on the other.
    """
    without_scripts = [
        bundle
        for bundle in _bundles_with_a_root_extension()
        if not (MARKETPLACE_ROOT / bundle / 'skills' / EXTENSION_SKILL / 'scripts').is_dir()
    ]
    assert without_scripts, 'expected at least one extension skill with no scripts/ tree'
    bundle = without_scripts[0]

    assert get_skill_dir(bundle, EXTENSION_SKILL).is_dir()
    with pytest.raises(FileNotFoundError):
        get_scripts_dir(bundle, EXTENSION_SKILL)


def test_absent_skill_raises():
    """``get_skill_dir`` fails loudly for a skill that does not exist."""
    with pytest.raises(FileNotFoundError):
        get_skill_dir('plan-marshall', 'no-such-skill')


# ---------------------------------------------------------------------------
# Registration — the sys.modules displacement guard
# ---------------------------------------------------------------------------


#: The script used to observe registration. Chosen because no test module imports
#: its stem plainly, so exercising the default registration here cannot itself
#: create the collision the guard below exists to detect.
PROBE_BUNDLE = 'plan-marshall'
PROBE_SKILL = 'manage-providers'
PROBE_SCRIPT = 'credentials.py'
PROBE_NAME = 'credentials'


def test_registration_is_the_default(monkeypatch):
    """A load with no ``register`` argument publishes the module under its stem.

    The control for the opt-out below: without it, an escape that suppressed nothing
    and an escape that worked would be indistinguishable.
    """
    monkeypatch.delitem(sys.modules, PROBE_NAME, raising=False)

    module = load_script_module(PROBE_BUNDLE, PROBE_SKILL, PROBE_SCRIPT)

    assert sys.modules.get(PROBE_NAME) is module


def test_register_false_publishes_nothing(monkeypatch):
    """``register=False`` returns the module without touching ``sys.modules``.

    This is the escape a caller takes to avoid displacing a name another test module
    imports plainly, so it has to be the absence of a registration rather than a
    registration under a different name.
    """
    monkeypatch.delitem(sys.modules, PROBE_NAME, raising=False)

    module = load_script_module(PROBE_BUNDLE, PROBE_SKILL, PROBE_SCRIPT, register=False)

    assert module is not None
    assert PROBE_NAME not in sys.modules


def test_register_false_reaches_parse_ns(monkeypatch):
    """``parse_ns`` forwards the opt-out to the load it performs.

    ``parse_ns`` loads the script to reach its parser, so it registers exactly as a
    direct load does — and it is the call a test is most likely to make. An opt-out
    that stopped at the loader would leave the common path unable to use it.
    """
    monkeypatch.delitem(sys.modules, PROBE_NAME, raising=False)

    namespace = parse_ns(
        PROBE_BUNDLE, PROBE_SKILL, PROBE_SCRIPT, 'list-providers', register=False
    )

    assert namespace.command == 'list-providers'
    assert PROBE_NAME not in sys.modules


def test_the_scan_finds_the_loader_call_sites(tree_scan):
    """The enumeration resolves known-present call sites in both directions.

    A positive control for the walker itself: every assertion below is about a set
    it produces, so a walker that silently matched nothing would make them all pass.
    """
    registered, plain, _ = tree_scan

    loaders = registered['_build_execute_factory']
    assert any(site.endswith('build_test_helpers.py') for site in loaders), loaders
    assert 'conftest.py' in plain['_build_execute_factory']


def test_no_new_shared_registration_collision(tree_scan):
    """No name beyond the pinned set is both loaded by file and imported plainly.

    This is the growth check. A registration that acquires a plain importer — or a
    new file-load of an already plainly-imported name — lands here rather than
    surfacing later as an order-dependent reload failure.
    """
    registered, plain, _ = tree_scan

    live = set(registered) & set(plain)
    new = live - KNOWN_REGISTRATION_COLLISIONS

    assert new == set(), (
        f'new sys.modules registration collision(s): {sorted(new)}. '
        'Pass register=False at the loading call site when only the returned module '
        'is needed, or give it an explicit module_name that cannot collide. '
        'Do not add the name to KNOWN_REGISTRATION_COLLISIONS to clear this.'
    )


def test_no_pinned_collision_has_been_resolved_without_unpinning(tree_scan):
    """Every pinned name is still a live collision.

    Reported separately from growth so the two failures are not confused: this one
    means a collision was fixed and the baseline was left behind, and the remedy is
    to delete the name rather than to restore the collision.
    """
    registered, plain, _ = tree_scan

    live = set(registered) & set(plain)
    stale = KNOWN_REGISTRATION_COLLISIONS - live

    assert stale == set(), (
        f'no longer a collision: {sorted(stale)} — remove from '
        'KNOWN_REGISTRATION_COLLISIONS so the baseline keeps describing the tree.'
    )


def test_unresolved_call_sites_are_reported_not_hidden(tree_scan):
    """The scan's coverage limit is visible rather than silently narrowing the guard.

    A loader call whose module name is neither a literal nor a module-level constant
    cannot be resolved statically, so it contributes no name to the collision set.
    That is a bound on what the guard can see, and a zero here would be a stronger
    claim than the walker can make — so the count is asserted as a known quantity
    that a later change has to look at, not assumed away.
    """
    _, _, unresolved = tree_scan

    assert len(unresolved) <= UNRESOLVED_CALL_SITE_BOUND, (
        f'{len(unresolved)} loader call sites could not be resolved statically, over '
        f'the {UNRESOLVED_CALL_SITE_BOUND} this bound was set against. The guard cannot '
        'see these, so a collision introduced at one is invisible: hoist the argument '
        'into a module-level constant, or pass a literal.'
    )
