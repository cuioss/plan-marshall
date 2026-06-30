#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``descriptor-regression-check`` commit-gate verb.

Deliverable 2 of the accept/commit/write-gate hardening plan: the
``architecture-refresh`` finalize step must REFUSE to commit a regenerated
``_project.json`` whose project identity regressed — name overwritten with the
worktree/plan-id basename, or description/description_reasoning blanked from a
previously-curated value. ``cmd_descriptor_regression_check`` is the
deterministic predicate the commit gate consumes. These tests exercise each
regressive predicate, a benign (identity-preserved) refresh, and the
missing-baseline error contract.
"""

import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

from conftest import load_script_module

sys.path.insert(0, str(Path(__file__).parent))


_architecture_core = load_script_module(
    'plan-marshall', 'manage-architecture', '_architecture_core.py', '_architecture_core'
)
_cmd_client = load_script_module('plan-marshall', 'manage-architecture', '_cmd_client.py', '_cmd_client')

save_project_meta = _architecture_core.save_project_meta
cmd_descriptor_regression_check = _cmd_client.cmd_descriptor_regression_check


def _write_baseline(baseline_dir: str, meta: dict) -> None:
    """Write a baseline ``_project.json`` directly under ``baseline_dir``.

    ``_resolve_snapshot_dir`` accepts a snapshot root that contains
    ``_project.json`` directly, so the test writes the baseline at the simple
    shape rather than nesting a full ``.plan/project-architecture/`` subtree.
    """
    (Path(baseline_dir) / '_project.json').write_text(
        json.dumps(meta, indent=2, sort_keys=True), encoding='utf-8'
    )


def _curated_meta(name: str = 'curated-project') -> dict:
    """A descriptor with a curated name + description + reasoning."""
    return {
        'name': name,
        'description': 'A curated project description',
        'description_reasoning': 'From README.md first paragraph',
        'extensions_used': [],
        'modules': {'module-a': {}},
    }


def _run(baseline_dir: str, project_dir: str) -> dict:
    args = SimpleNamespace(pre=str(baseline_dir), project_dir=str(project_dir))
    return cmd_descriptor_regression_check(args)


def _violation_fields(result: dict) -> set[str]:
    return {v['field'] for v in result['violations']}


def test_name_overwritten_with_basename_is_regressive():
    """A regenerated name equal to the project-dir basename is regressive.

    This is the canonical worktree/plan-id corruption: ``discover --force``
    inside a worktree rewrote ``name`` to ``project_path.name``.
    """
    with tempfile.TemporaryDirectory() as baseline_dir, tempfile.TemporaryDirectory() as project_dir:
        _write_baseline(baseline_dir, _curated_meta(name='plan-marshall'))
        # Regenerated descriptor: name flipped to the project-dir basename.
        basename = Path(project_dir).resolve().name
        regenerated = _curated_meta(name=basename)
        save_project_meta(regenerated, project_dir)

        result = _run(baseline_dir, project_dir)

        assert result['status'] == 'success'
        assert result['regressive'] is True
        assert 'name' in _violation_fields(result)
        # The reason names the basename signature.
        name_violation = next(v for v in result['violations'] if v['field'] == 'name')
        assert basename in name_violation['reason']


def test_name_changed_to_other_value_is_regressive():
    """Any divergence from the curated baseline name is regressive."""
    with tempfile.TemporaryDirectory() as baseline_dir, tempfile.TemporaryDirectory() as project_dir:
        _write_baseline(baseline_dir, _curated_meta(name='plan-marshall'))
        regenerated = _curated_meta(name='something-else')
        save_project_meta(regenerated, project_dir)

        result = _run(baseline_dir, project_dir)

        assert result['regressive'] is True
        assert 'name' in _violation_fields(result)


def test_description_blanked_is_regressive():
    """A description transitioning from non-empty to empty is regressive."""
    with tempfile.TemporaryDirectory() as baseline_dir, tempfile.TemporaryDirectory() as project_dir:
        _write_baseline(baseline_dir, _curated_meta())
        regenerated = _curated_meta()
        regenerated['description'] = ''
        save_project_meta(regenerated, project_dir)

        result = _run(baseline_dir, project_dir)

        assert result['regressive'] is True
        assert _violation_fields(result) == {'description'}


def test_description_reasoning_blanked_is_regressive():
    """A blanked description_reasoning is regressive."""
    with tempfile.TemporaryDirectory() as baseline_dir, tempfile.TemporaryDirectory() as project_dir:
        _write_baseline(baseline_dir, _curated_meta())
        regenerated = _curated_meta()
        regenerated['description_reasoning'] = ''
        save_project_meta(regenerated, project_dir)

        result = _run(baseline_dir, project_dir)

        assert result['regressive'] is True
        assert _violation_fields(result) == {'description_reasoning'}


def test_benign_refresh_with_module_changes_is_not_regressive():
    """Identity preserved + only the module index shifting is benign."""
    with tempfile.TemporaryDirectory() as baseline_dir, tempfile.TemporaryDirectory() as project_dir:
        _write_baseline(baseline_dir, _curated_meta())
        # Regenerated descriptor: identity intact, an extra module added.
        regenerated = _curated_meta()
        regenerated['modules'] = {'module-a': {}, 'module-b': {}}
        save_project_meta(regenerated, project_dir)

        result = _run(baseline_dir, project_dir)

        assert result['status'] == 'success'
        assert result['regressive'] is False
        assert result['violations'] == []


def test_empty_baseline_name_never_flags_name():
    """A baseline with no curated name cannot lose one — name is not regressive."""
    with tempfile.TemporaryDirectory() as baseline_dir, tempfile.TemporaryDirectory() as project_dir:
        baseline = _curated_meta(name='')
        _write_baseline(baseline_dir, baseline)
        # Regenerated descriptor seeds a real name (an improvement, not a loss).
        regenerated = _curated_meta(name='now-named')
        save_project_meta(regenerated, project_dir)

        result = _run(baseline_dir, project_dir)

        assert result['regressive'] is False
        assert 'name' not in _violation_fields(result)


def test_multiple_violations_collected():
    """Name flip AND description blanking both surface as violations."""
    with tempfile.TemporaryDirectory() as baseline_dir, tempfile.TemporaryDirectory() as project_dir:
        _write_baseline(baseline_dir, _curated_meta(name='plan-marshall'))
        basename = Path(project_dir).resolve().name
        regenerated = _curated_meta(name=basename)
        regenerated['description'] = ''
        save_project_meta(regenerated, project_dir)

        result = _run(baseline_dir, project_dir)

        assert result['regressive'] is True
        assert _violation_fields(result) == {'name', 'description'}


def test_missing_baseline_returns_snapshot_not_found():
    """An absent baseline _project.json yields the snapshot_not_found error."""
    with tempfile.TemporaryDirectory() as baseline_dir, tempfile.TemporaryDirectory() as project_dir:
        # No _project.json written under baseline_dir.
        save_project_meta(_curated_meta(), project_dir)

        result = _run(baseline_dir, project_dir)

        assert result['status'] == 'error'
        assert result['error'] == 'snapshot_not_found'
        assert result['path'] == str(baseline_dir)
