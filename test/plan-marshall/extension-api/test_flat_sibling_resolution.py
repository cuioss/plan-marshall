# SPDX-License-Identifier: FSL-1.1-ALv2
"""The step docs, build extensions and sibling scripts resolve on every deployed shape.

PLAN-LB-96 made the bundles root and the extension discovery flat-aware. The
readers that address a SIBLING skill by joining a bare skill name onto the skills
root were left behind, so on a flat install (``{root}/skills/{bundle}-{skill}/``)
they built ``{root}/skills/phase-6-finalize/…`` — a path no flat tree carries —
and the file read that depends on it failed. The consequence the operator met is
the worst of the family: ``marshall-steward``'s upgrade could not complete on any
flat install.

This module pins the three readers the plan names, on all three deployed shapes:

* FLAT — the marker-less tree PLAN-LB-96's fixture builds, exercised in a
  subprocess whose only import root is that tree, so the deployed ``__file__`` is
  the one the production read uses;
* NESTED — the marketplace source checkout itself, unchanged;
* VERSIONED CACHE — a synthetic ``{cache}/{bundle}/{version}/skills/…`` tree, whose
  version directory is the one the running script came from.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, cast

import pytest
from _flat_install_fixtures import (
    MARKETPLACE_ROOT,
    flat_install_tree,
    run_python_in_flat,
)

from conftest import load_script_module

_BUNDLE = 'plan-marshall'
_CC_SCRIPT = ('plan-marshall', 'extension-api', 'configurable_contract.py')
_DISC_SCRIPT = ('plan-marshall', 'extension-api', 'extension_discovery.py')

#: The steps the flat install must resolve, with the skill-relative doc each one
#: lives at. ``push`` is the standards-resident case (``workflow/`` is searched
#: first and misses), ``sonar-roundtrip`` the workflow-resident one, and the two
#: ``automatic-review`` spellings are the promoted out-of-phase-6 step.
_STEP_DOCS: dict[str, str] = {
    'plan-marshall:automatic-review': 'automatic-review/SKILL.md',
    'automatic-review': 'automatic-review/SKILL.md',
    'default:push': 'phase-6-finalize/standards/push.md',
    'default:sonar-roundtrip': 'phase-6-finalize/workflow/sonar-roundtrip.md',
}

#: The four build skills whose ``scripts/extension.py`` the discovery must find.
_BUILD_SKILLS = ('build-pyproject', 'build-maven', 'build-gradle', 'build-npm')


def _load_from_path(path: Path, module_name: str):
    """Load a module from an absolute path, so its ``__file__`` is the DEPLOYED one.

    ``conftest.load_script_module`` anchors on ``(bundle, skill, script_file)`` in
    the SOURCE tree, which is what the nested case wants. The cache case must load
    the copy that sits inside the version directory, because the anchor under test
    is that module's own location.
    """
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None and spec.loader is not None, path
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _flat_skill_dir(root: Path, bundle: str, skill: str) -> Path:
    return root / 'skills' / f'{bundle}-{skill}'


def _resolution_program(root: Path) -> str:
    """Return the driver that resolves every reader from the tree at ``root``.

    Loading by file path is deliberate: it makes ``Path(__file__)`` inside each
    module the DEPLOYED path, which is exactly what the resolution under test
    anchors on.
    """
    return f"""
import importlib.util, json, sys

root = {str(root)!r}
bundle = {_BUNDLE!r}


def load(skill, script, name):
    path = f'{{root}}/skills/{{bundle}}-{{skill}}/scripts/{{script}}'
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


contract = load('extension-api', 'configurable_contract.py', 'probe_configurable_contract')
discovery = load('extension-api', 'extension_discovery.py', 'probe_extension_discovery')

results = {{}}
results['step_docs'] = {{}}
for step_id in {json.dumps(sorted(_STEP_DOCS))}:
    path = contract.resolve_step_doc_path(step_id)
    results['step_docs'][step_id] = {{'path': str(path), 'is_file': path.is_file()}}

results['build_extensions'] = [
    {{'path': str(path), 'is_file': path.is_file()}} for path in discovery.get_build_extension_paths()
]
extension_api = discovery.get_extension_api_scripts_path()
results['extension_api_scripts'] = {{'path': str(extension_api), 'is_dir': extension_api.is_dir()}}
results['phase5_implementors'] = len(
    discovery._scan_phase5_for_implementors('plan-marshall:extension-api/standards/ext-point-build-verify-step')
)
print(json.dumps(results))
"""


def _run_resolution(root: Path, project_dir: Path) -> dict[str, Any]:
    completed = run_python_in_flat(root, project_dir, _resolution_program(root))
    assert completed.returncode == 0, completed.stderr
    return cast('dict[str, Any]', json.loads(completed.stdout))


def _assert_resolved(results: dict[str, Any], expected_suffixes: dict[str, str]) -> None:
    """Every step doc and build-extension path exists and ends at the expected file."""
    for step_id, suffix in expected_suffixes.items():
        entry = results['step_docs'][step_id]
        assert entry['is_file'], f'{step_id} resolved to {entry["path"]}, which does not exist'
        assert entry['path'].endswith(suffix), f'{step_id} resolved to {entry["path"]}, expected …/{suffix}'

    extensions = results['build_extensions']
    assert [Path(entry['path']).name for entry in extensions] == ['extension.py'] * len(_BUILD_SKILLS), extensions
    assert all(entry['is_file'] for entry in extensions), extensions
    found_skills = [Path(entry['path']).parent.parent.name for entry in extensions]
    for skill in _BUILD_SKILLS:
        assert any(name.endswith(skill) for name in found_skills), (skill, found_skills)

    assert results['extension_api_scripts']['is_dir'], results['extension_api_scripts']
    assert results['phase5_implementors'] > 0, 'the phase-5 standards scan found no implementor on this shape'


# =============================================================================
# FLAT — the tree that ships
# =============================================================================


@pytest.fixture(scope='module')
def flat_install(flat_install_tree: Path) -> Path:
    return flat_install_tree


def test_the_flat_tree_carries_no_bundle_marker(flat_install: Path) -> None:
    """The fixture stays the shape under test: a flat skill root and no bundle dir."""
    assert (flat_install / 'skills').is_dir()
    assert not list(flat_install.rglob('.claude-plugin'))


def test_every_named_reader_resolves_on_a_flat_tree(flat_install: Path, tmp_path: Path) -> None:
    """Each doc, build extension and sibling scripts dir resolves under a flat install."""
    project = tmp_path / 'project'
    project.mkdir()
    results = _run_resolution(flat_install, project)

    _assert_resolved(results, _STEP_DOCS)
    for entry in results['step_docs'].values():
        assert '/skills/plan-marshall-' in entry['path'], entry['path']


def test_a_missing_skill_names_both_shapes(flat_install: Path, tmp_path: Path) -> None:
    """A genuinely absent skill reports the nested AND the flat candidate it probed.

    On a flat install the old behaviour reported only the nested spelling, which
    reads as "this install is incomplete" even when the flat tree carries the file.
    The report now names both, so the operator can tell which shape was expected.
    """
    project = tmp_path / 'project'
    project.mkdir()
    script = _flat_skill_dir(flat_install, _BUNDLE, 'extension-api') / 'scripts' / 'configurable_contract.py'
    program = f"""
import sys
sys.path.insert(0, {str(script.parent)!r})
import marketplace_bundles
try:
    marketplace_bundles.require_sibling_skill_path(
        __import__('pathlib').Path({str(script)!r}), 'plan-marshall', 'skills/no-such-skill/SKILL.md'
    )
except marketplace_bundles.SkillPathNotFound as exc:
    print(str(exc))
else:
    raise SystemExit('the lookup for an absent skill did not raise')
"""
    completed = run_python_in_flat(flat_install, project, program)

    assert completed.returncode == 0, completed.stderr
    report = completed.stdout
    assert 'no-such-skill' in report, report
    assert 'nested' in report and 'flat' in report, report
    assert 'plan-marshall-no-such-skill' in report, report


# =============================================================================
# NESTED — the marketplace source checkout, unchanged
# =============================================================================


def test_the_nested_source_tree_resolves_what_it_resolved_before() -> None:
    """The source checkout keeps resolving to its own bundle tree."""
    contract = load_script_module(*_CC_SCRIPT, 'nested_configurable_contract', register=False)
    discovery = load_script_module(*_DISC_SCRIPT, 'nested_extension_discovery', register=False)

    for step_id, suffix in _STEP_DOCS.items():
        path = contract.resolve_step_doc_path(step_id)
        assert path.is_file(), f'{step_id} -> {path}'
        assert path.as_posix().endswith(suffix), path
        assert path.is_relative_to(MARKETPLACE_ROOT), path

    extensions = discovery.get_build_extension_paths()
    assert len(extensions) == len(_BUILD_SKILLS), extensions
    for path in extensions:
        assert path.is_file(), path
        assert path.is_relative_to(MARKETPLACE_ROOT), path

    assert discovery.get_extension_api_scripts_path().is_dir()


# =============================================================================
# VERSIONED CACHE — the version dir the running script came from
# =============================================================================


def _build_versioned_cache(tmp_path: Path, version: str = '0.1.4242') -> Path:
    """Create ``{cache}/plan-marshall/{version}/skills/…`` for the readers under test.

    Only the skills the readers address are copied: the resolution is what is under
    test, not the size of the tree. The bundle marker goes in the VERSION dir, which
    is the shape ``resolve_bundles_root`` recognises for a cache.
    """
    cache = tmp_path / 'cache'
    version_dir = cache / _BUNDLE / version
    (version_dir / '.claude-plugin').mkdir(parents=True)
    (version_dir / '.claude-plugin' / 'plugin.json').write_text(
        json.dumps({'name': _BUNDLE, 'version': version}), encoding='utf-8'
    )
    for skill in ('extension-api', 'phase-6-finalize', 'automatic-review', 'phase-5-execute', 'script-shared'):
        source = MARKETPLACE_ROOT / _BUNDLE / 'skills' / skill
        shutil.copytree(
            source,
            version_dir / 'skills' / skill,
            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'),
        )
    for skill in _BUILD_SKILLS:
        source = MARKETPLACE_ROOT / _BUNDLE / 'skills' / skill / 'scripts' / 'extension.py'
        target = version_dir / 'skills' / skill / 'scripts' / 'extension.py'
        target.parent.mkdir(parents=True)
        shutil.copy2(source, target)
    return cache


def test_the_versioned_cache_resolves_inside_the_running_version_dir(tmp_path: Path) -> None:
    """The cache reader anchors on the version dir the script came from, not the newest."""
    cache = _build_versioned_cache(tmp_path)
    version_dir = cache / _BUNDLE / '0.1.4242'
    scripts_dir = version_dir / 'skills' / 'extension-api' / 'scripts'
    contract = _load_from_path(scripts_dir / 'configurable_contract.py', 'cache_configurable_contract')
    discovery = _load_from_path(scripts_dir / 'extension_discovery.py', 'cache_extension_discovery')

    for step_id, suffix in _STEP_DOCS.items():
        path = contract.resolve_step_doc_path(step_id)
        assert path.is_file(), f'{step_id} -> {path}'
        assert path.is_relative_to(version_dir), path
        assert path.as_posix().endswith(suffix), path

    extensions = discovery.get_build_extension_paths()
    assert len(extensions) == len(_BUILD_SKILLS), extensions
    for path in extensions:
        assert path.is_file(), path
        assert path.is_relative_to(version_dir), path
