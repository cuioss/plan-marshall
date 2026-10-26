# SPDX-License-Identifier: FSL-1.1-ALv2
"""The ``marshall-steward`` upgrade reconcile runs on a flat install.

The operator met this failure as a dead end: the upgrade's Stage-2 ``sync-defaults
--backfill-bot-roster`` stopped with ``step body doc not found:
~/.config/opencode/skills/automatic-review/SKILL.md``, so a flat install could not
be brought to a new version at all. The verbs are driven here against the
marker-less flat fixture with the tree's REAL frontmatter — the doc read is the
whole mechanism under test — and the same verbs are driven against the marketplace
source checkout as the nested twin.

The comparison is the assertion: a flat install must answer what a nested one
answers, because both read the same bytes out of the same skill.

``PLAN_BASE_DIR`` is pinned for every run. Without it the verb walks up from the
project directory for a ``.plan/local`` ancestor, finds the repository that hosts
the pytest basetemp, and reads (and rewrites) THAT config — which is both wrong
and destructive.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from _flat_install_fixtures import (
    flat_install_tree_with_frontmatter,
    run_python_in_flat,
    run_script_in_flat,
)
from toon_parser import parse_toon

from conftest import PROJECT_ROOT, run_script

_MANAGE_CONFIG = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-config'
    / 'scripts'
    / 'manage-config.py'
)
_SOURCES = PROJECT_ROOT / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills'
_FLAT_RELATIVE = Path('skills') / 'plan-marshall-manage-config' / 'scripts' / 'manage-config.py'

#: The bot roster the upgrade's opted-in back-fill writes. Both machines that met
#: the defect expected the same values; the pair is asserted by NAME here and then
#: compared verbatim against the nested run.
_REQUIRED_BOT = 'coderabbit'
_OPTIONAL_BOT = 'sourcery'


def _write_marshal(project: Path) -> Path:
    plan_dir = project / '.plan'
    plan_dir.mkdir(parents=True, exist_ok=True)
    marshal = plan_dir / 'marshal.json'
    marshal.write_text('{}\n', encoding='utf-8')
    return marshal


def _read_marshal(project: Path) -> dict[str, Any]:
    return cast('dict[str, Any]', json.loads((project / '.plan' / 'marshal.json').read_text(encoding='utf-8')))


def _roster(project: Path) -> dict[str, Any]:
    steps = _read_marshal(project)['plan']['phase-6-finalize']['steps']
    return cast('dict[str, Any]', steps['plan-marshall:automatic-review'])


def _pin(project: Path) -> dict[str, str]:
    """Pin the plan base so the verb operates on ``project``, not on this repository."""
    return {'PLAN_BASE_DIR': str(project / '.plan')}


@pytest.fixture(scope='module')
def flat_install(flat_install_tree_with_frontmatter: Path) -> Path:
    return flat_install_tree_with_frontmatter


def _flat_script(flat_install: Path) -> Path:
    return flat_install / _FLAT_RELATIVE


def test_sync_defaults_backfills_the_bot_roster_on_a_flat_install(flat_install: Path, tmp_path: Path) -> None:
    """The verb the operator's upgrade stopped at completes, and writes the roster."""
    flat_project = tmp_path / 'flat-project'
    _write_marshal(flat_project)

    completed = run_script_in_flat(
        flat_install,
        flat_project,
        _flat_script(flat_install),
        'sync-defaults',
        '--backfill-bot-roster',
        env_overrides=_pin(flat_project),
    )

    assert completed.returncode == 0, completed.stderr
    payload = parse_toon(completed.stdout)
    assert payload.get('status') == 'success', payload

    roster = _roster(flat_project)
    assert _REQUIRED_BOT in roster.get('required_bots', ''), roster
    assert _OPTIONAL_BOT in roster.get('optional_bots', ''), roster


def test_the_flat_roster_is_the_nested_roster(flat_install: Path, tmp_path: Path) -> None:
    """The roster a flat install reads is byte-for-byte the nested one."""
    flat_project = tmp_path / 'flat-project'
    _write_marshal(flat_project)
    nested_project = tmp_path / 'nested-project'
    _write_marshal(nested_project)

    flat = run_script_in_flat(
        flat_install,
        flat_project,
        _flat_script(flat_install),
        'sync-defaults',
        '--backfill-bot-roster',
        env_overrides=_pin(flat_project),
    )
    nested = run_script(
        _MANAGE_CONFIG,
        'sync-defaults',
        '--backfill-bot-roster',
        cwd=nested_project,
        env_overrides=_pin(nested_project),
    )

    assert flat.returncode == 0, flat.stderr
    assert nested.returncode == 0, nested.stderr
    flat_payload = parse_toon(flat.stdout)
    nested_payload = parse_toon(nested.stdout)
    assert flat_payload.get('status') == nested_payload.get('status') == 'success', (flat_payload, nested_payload)

    assert _roster(flat_project) == _roster(nested_project)


def test_step_get_answers_on_a_flat_install(flat_install: Path, tmp_path: Path) -> None:
    """Reading a finalize step's params works on the flat tree, as on the nested one."""
    flat_project = tmp_path / 'flat-project'
    _write_marshal(flat_project)
    nested_project = tmp_path / 'nested-project'
    _write_marshal(nested_project)
    flat_sync = run_script_in_flat(
        flat_install,
        flat_project,
        _flat_script(flat_install),
        'sync-defaults',
        '--backfill-bot-roster',
        env_overrides=_pin(flat_project),
    )
    nested_sync = run_script(
        _MANAGE_CONFIG, 'sync-defaults', '--backfill-bot-roster', cwd=nested_project, env_overrides=_pin(nested_project)
    )
    assert flat_sync.returncode == 0, flat_sync.stderr
    assert nested_sync.returncode == 0, nested_sync.stderr

    flat = run_script_in_flat(
        flat_install,
        flat_project,
        _flat_script(flat_install),
        'plan',
        'phase-6-finalize',
        'step',
        'get',
        '--step-id',
        'plan-marshall:automatic-review',
        env_overrides=_pin(flat_project),
    )
    nested = run_script(
        _MANAGE_CONFIG,
        'plan',
        'phase-6-finalize',
        'step',
        'get',
        '--step-id',
        'plan-marshall:automatic-review',
        cwd=nested_project,
        env_overrides=_pin(nested_project),
    )

    assert flat.returncode == 0, flat.stderr
    assert nested.returncode == 0, nested.stderr
    flat_payload = parse_toon(flat.stdout)
    nested_payload = parse_toon(nested.stdout)
    assert flat_payload.get('status') == 'success', flat_payload
    assert flat_payload.get('params') == nested_payload.get('params'), (flat_payload, nested_payload)


def test_the_manifest_verbs_answer_on_a_flat_install(flat_install: Path, tmp_path: Path) -> None:
    """``compose`` and ``validate-loadable`` answer identically on a flat and a nested install.

    Both verbs run through the entry point that imports ``_manifest_validation`` at
    module import, and both resolve each phase-6 step's body doc — the loadability
    check is exactly the "does this step's standards file exist" surface a bare
    sibling join turned into a false negative on a flat tree. The comparison is the
    assertion: only the TOON ``status`` is compared, because the manifests' paths
    differ by construction.
    """
    invocations = (
        (
            'manage-execution-manifest',
            'compose',
            '--plan-id',
            'd4-probe',
            '--plan-change-type',
            'feature',
            '--track',
            'simple',
            '--scope-estimate',
            'surgical',
        ),
        ('manage-execution-manifest', 'validate-loadable', '--plan-id', 'd4-probe', '--all'),
    )
    flat_project = tmp_path / 'flat-project'
    _write_marshal(flat_project)
    nested_project = tmp_path / 'nested-project'
    _write_marshal(nested_project)
    for project, runner in ((flat_project, 'flat'), (nested_project, 'nested')):
        if runner == 'flat':
            seeded = run_script_in_flat(
                flat_install,
                project,
                _flat_script(flat_install),
                'sync-defaults',
                '--backfill-bot-roster',
                env_overrides=_pin(project),
            )
        else:
            seeded = run_script(
                _MANAGE_CONFIG,
                'sync-defaults',
                '--backfill-bot-roster',
                cwd=project,
                env_overrides=_pin(project),
            )
        assert seeded.returncode == 0, (runner, seeded.stderr)

    for skill, *verb in invocations:
        flat_script = flat_install / 'skills' / f'plan-marshall-{skill}' / 'scripts' / f'{skill}.py'
        nested_script = _SOURCES / skill / 'scripts' / f'{skill}.py'
        flat = run_script_in_flat(flat_install, flat_project, flat_script, *verb, env_overrides=_pin(flat_project))
        nested = run_script(nested_script, *verb, cwd=nested_project, env_overrides=_pin(nested_project))

        assert flat.returncode == 0, (verb[0], flat.stderr, flat.stdout)
        assert nested.returncode == 0, (verb[0], nested.stderr, nested.stdout)
        flat_payload = parse_toon(flat.stdout)
        nested_payload = parse_toon(nested.stdout)
        assert flat_payload.get('status') == nested_payload.get('status') == 'success', (
            verb[0],
            flat_payload,
            nested_payload,
        )


def test_the_manifest_loadability_path_imports_on_a_flat_install(flat_install: Path, tmp_path: Path) -> None:
    """``_manifest_validation`` resolves its step docs at import time on the flat tree.

    Its two module-level constants are the import-time joins that made the whole
    manifest surface dead on a flat install; the module is loaded from the deployed
    copy, so the assertion is on the deployed ``__file__``.
    """
    project = tmp_path / 'project'
    project.mkdir()
    script = flat_install / 'skills' / 'plan-marshall-manage-execution-manifest' / 'scripts' / '_manifest_validation.py'
    program = f"""
import importlib.util, json, sys
path = {str(script)!r}
spec = importlib.util.spec_from_file_location('probe_manifest_validation', path)
module = importlib.util.module_from_spec(spec)
sys.modules['probe_manifest_validation'] = module
spec.loader.exec_module(module)
results = {{
    'phase_6_dir': str(module._PHASE_6_SKILL_DIR),
    'phase_6_dir_exists': module._PHASE_6_SKILL_DIR.is_dir(),
    'automatic_review_md': str(module._AUTOMATIC_REVIEW_SKILL_MD),
    'automatic_review_exists': module._AUTOMATIC_REVIEW_SKILL_MD.is_file(),
    'push_doc': str(module._resolve_standards_path('default:push')),
    'push_doc_exists': module._resolve_standards_path('default:push').is_file(),
    'sonar_doc': str(module._resolve_standards_path('default:sonar-roundtrip')),
    'sonar_doc_exists': module._resolve_standards_path('default:sonar-roundtrip').is_file(),
}}
print(json.dumps(results))
"""
    completed = run_python_in_flat(flat_install, project, program)

    assert completed.returncode == 0, completed.stderr
    results = cast('dict[str, Any]', json.loads(completed.stdout))
    assert results['phase_6_dir_exists'], results['phase_6_dir']
    assert results['automatic_review_exists'], results['automatic_review_md']
    assert results['push_doc_exists'], results['push_doc']
    assert results['sonar_doc_exists'], results['sonar_doc']
