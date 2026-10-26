# SPDX-License-Identifier: FSL-1.1-ALv2
"""Every ``resolve_bundles_root`` call site is exercised by the flat fixture.

``resolve_bundles_root`` runs at IMPORT time in six modules, so a flat deployment
that the walk cannot resolve fails before a command starts — that is the defect
this guard exists to keep closed. The guard is deliberately a call-site
inventory, not a per-module spot check:

* every ``resolve_bundles_root(...)`` Call node under ``marketplace/bundles`` is
  discovered by AST (docstring mentions and the definition are not calls), and
* it must be DECLARED below as either an import-time or a function-level site, and
* every declared module is imported against the marker-less flat fixture, so an
  import-time site is genuinely executed on a flat tree.

A seventh import-time call site therefore cannot be added quietly: it appears in
the discovered set, the declared set does not carry it, and the test reds until
it is declared — and, once declared, imported in the flat fixture.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from typing import Any, cast

import pytest
from _flat_install_fixtures import (
    MARKETPLACE_ROOT,
    flat_install_tree,
    run_python_in_flat,
)

#: Modules that call ``resolve_bundles_root`` at MODULE level: the call runs on
#: import, so a flat tree that the walk cannot resolve makes the command dead
#: before argparse runs.
IMPORT_TIME_MODULES: frozenset[str] = frozenset(
    {
        'marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_core.py',
        'marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_build.py',
        'marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_validation.py',
        'marketplace/bundles/pm-plugin-development/skills/plan-marshall-plugin/scripts/plugin_discover.py',
        'marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_doctor_shared.py',
        'marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_cmd_extension.py',
    }
)

#: Modules whose call sites sit inside functions. They are declared so the guard
#: sees the whole population, and they are imported in the flat fixture like the
#: rest; the endpoint each one hides behind is named beside it.
FUNCTION_LEVEL_MODULES: frozenset[str] = frozenset(
    {
        # ``manage-architecture`` query/build/enrich entry points.
        'marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_architecture_core.py',
        'marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_query.py',
        # ``_dep_index``'s marketplace fallback when no source tree answers.
        'marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/scripts/_dep_index.py',
        # ``get_marketplace_bundles_path`` — the extension-discovery cache fallback.
        'marketplace/bundles/plan-marshall/skills/extension-api/scripts/extension_discovery.py',
        # ``runbook_lane resolve`` / its skill probe.
        'marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py',
        # persona resolution, metrics, recipe scoring.
        'marketplace/bundles/plan-marshall/skills/manage-personas/scripts/manage_personas.py',
        'marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py',
        'marketplace/bundles/plan-marshall/skills/script-shared/scripts/recipe_scoring.py',
    }
)

_CALL_NAME = 'resolve_bundles_root'


def _call_sites(module_path: Path) -> list[bool]:
    """Return one entry per ``resolve_bundles_root`` call: ``True`` when module-level."""
    tree = ast.parse(module_path.read_text(encoding='utf-8'), filename=str(module_path))
    module_level: list[bool] = []

    class _Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.depth = 0

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self.depth += 1
            self.generic_visit(node)
            self.depth -= 1

        visit_AsyncFunctionDef = visit_FunctionDef  # type: ignore[assignment]

        def visit_Call(self, node: ast.Call) -> None:
            func = node.func
            name = func.id if isinstance(func, ast.Name) else func.attr if isinstance(func, ast.Attribute) else ''
            if name == _CALL_NAME:
                module_level.append(self.depth == 0)
            self.generic_visit(node)

    _Visitor().visit(tree)
    return module_level


def _discovered_call_sites() -> tuple[set[str], set[str]]:
    """Return ``(import_time_modules, function_level_modules)`` for the live tree."""
    repo_root = MARKETPLACE_ROOT.parents[1]
    import_time: set[str] = set()
    function_level: set[str] = set()
    for module_path in sorted(MARKETPLACE_ROOT.rglob('*.py')):
        if '__pycache__' in module_path.parts:
            continue
        module_level = _call_sites(module_path)
        if not module_level:
            continue
        relative = module_path.relative_to(repo_root).as_posix()
        (import_time if any(module_level) else function_level).add(relative)
    return import_time, function_level


@pytest.fixture(scope='module')
def flat_install(flat_install_tree: Path) -> Path:
    """The session's marker-less flat deployment."""
    return flat_install_tree


def test_the_fixture_carries_no_bundle_marker(flat_install: Path) -> None:
    """The fixture is the tree that ships: skill root, target manifest, no bundle."""
    assert (flat_install / 'skills').is_dir()
    assert not list(flat_install.rglob('.claude-plugin')), 'a bundle marker would let the nested probes answer'


def test_every_import_time_call_site_is_declared() -> None:
    discovered, _ = _discovered_call_sites()

    assert discovered == set(IMPORT_TIME_MODULES), (
        'the import-time resolve_bundles_root population changed: '
        f'undeclared={sorted(discovered - set(IMPORT_TIME_MODULES))}, '
        f'stale={sorted(set(IMPORT_TIME_MODULES) - discovered)}'
    )


def test_every_function_level_call_site_is_declared() -> None:
    _, discovered = _discovered_call_sites()

    assert discovered == set(FUNCTION_LEVEL_MODULES), (
        'the function-level resolve_bundles_root population changed: '
        f'undeclared={sorted(discovered - set(FUNCTION_LEVEL_MODULES))}, '
        f'stale={sorted(set(FUNCTION_LEVEL_MODULES) - discovered)}'
    )


def test_every_declared_module_imports_in_the_flat_fixture(flat_install: Path, tmp_path: Path) -> None:
    """Each declared module loads from the flat tree, with nothing but it on the path."""
    declared = sorted(set(IMPORT_TIME_MODULES) | set(FUNCTION_LEVEL_MODULES))

    completed = run_python_in_flat(flat_install, tmp_path, _import_program(flat_install, declared))

    assert completed.returncode == 0, completed.stderr
    results = json.loads(completed.stdout)
    failures = {relative: detail for relative, detail in results.items() if detail != 'ok'}

    assert not failures, failures


def _flat_module_path(flat_root: Path, relative: str) -> Path:
    """Map a nested source path onto its flat deployed path."""
    parts = Path(relative).parts
    # marketplace/bundles/{bundle}/skills/{skill}/scripts/{name}
    bundle = parts[2]
    skill = parts[4]
    tail = Path(*parts[5:])
    return flat_root / 'skills' / f'{bundle}-{skill}' / tail


def _import_program(flat_root: Path, declared: list[str]) -> str:
    """Return the driver that imports every declared module from the flat tree."""
    mapping = {relative: str(_flat_module_path(flat_root, relative)) for relative in declared}
    return f"""
import importlib.util, json, sys
mapping = {json.dumps(mapping)}
results = {{}}
for index, (relative, path) in enumerate(mapping.items()):
    try:
        spec = importlib.util.spec_from_file_location(f'flat_probe_{{index}}', path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        results[relative] = 'ok'
    except BaseException as exc:
        results[relative] = f'{{type(exc).__name__}}: {{exc}}'
print(json.dumps(results))
"""


def test_the_marketplace_authoring_tools_report_the_absent_tree_in_a_flat_install(
    flat_install: Path, tmp_path: Path
) -> None:
    """Each ``pm-plugin-development`` module answers "no marketplace tree", its own way.

    None of the three is usable on an installed tree — and none of them may crash
    or invent a tree there. ``plugin_discover`` reports the empty module list it
    reports for any non-marketplace project; ``_doctor_shared`` refuses to hand
    back the deploy root as a bundles directory; ``_cmd_extension`` carries no
    marketplace path at all, so its scan reports the absence instead of probing a
    path that cannot exist. ``_manifest_validation`` keeps its documented
    ``parent.parent`` anchor derivation, with only its relativiser falling back.
    """
    results = _run_behaviour_program(flat_install, tmp_path)

    assert results['plugin_discover_modules'] == []
    assert results['doctor_marketplace_root'] is None
    assert results['extension_marketplace_root'] is None
    assert 'deployed (flat) install' in results['extension_absence']
    assert '--marketplace-root' in results['extension_absence']
    # The anchor is still ``resolve_bundles_root(...).parent.parent``: a flat root
    # is not special-cased, so the cache shape's derivation cannot drift.
    assert Path(results['manifest_repo_root']) == flat_install.parent.parent


def _run_behaviour_program(flat_install: Path, project_dir: Path) -> dict[str, Any]:
    """Import the three authoring modules from the flat tree and collect their answers."""
    completed = run_python_in_flat(flat_install, project_dir, _behaviour_program(flat_install))
    assert completed.returncode == 0, completed.stderr
    return cast('dict[str, Any]', json.loads(completed.stdout))


def _behaviour_program(flat_root: Path) -> str:
    """Return the driver that exercises the authoring tools inside the flat tree."""
    return f"""
import importlib.util, json, os, sys

root = {str(flat_root)!r}

def load(bundle, skill, script, name):
    path = f'{{root}}/skills/{{bundle}}-{{skill}}/scripts/{{script}}'
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

results = {{}}
discover = load('pm-plugin-development', 'plan-marshall-plugin', 'plugin_discover.py', 'flat_plugin_discover')
results['plugin_discover_modules'] = discover.discover_plugin_modules(os.getcwd())

shared = load('pm-plugin-development', 'plugin-doctor', '_doctor_shared.py', 'flat_doctor_shared')
found = shared.find_marketplace_root()
results['doctor_marketplace_root'] = None if found is None else str(found)

extension = load('pm-plugin-development', 'plugin-doctor', '_cmd_extension.py', 'flat_cmd_extension')
results['extension_marketplace_root'] = (
    None if extension._MARKETPLACE_FROM_SCRIPT is None else str(extension._MARKETPLACE_FROM_SCRIPT)
)
results['extension_absence'] = extension._NO_MARKETPLACE_TREE_MESSAGE

manifest = load('plan-marshall', 'manage-execution-manifest', '_manifest_validation.py', 'flat_manifest_validation')
results['manifest_repo_root'] = str(manifest._REPO_ROOT)

print(json.dumps(results))
"""
