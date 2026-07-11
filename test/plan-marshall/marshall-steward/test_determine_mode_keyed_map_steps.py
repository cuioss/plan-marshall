#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Keyed-map regression tests for marshall-steward finalize-step detection.

The canonical serial form of ``marshal.json::plan["phase-6-finalize"]["steps"]``
is a KEYED-MAP — a dict mapping each step id to its (possibly empty) config
object, with ``{}`` for a config-less step (see ``conftest.MARSHAL_SCHEMA_DEFAULT``).
A legacy list-of-id-strings is also accepted for backward compatibility.

Before the keyed-map fix, ``determine_mode.py``'s detection helpers guarded on
``isinstance(steps, list)`` and treated every keyed-map ``steps`` block as
"cannot compare", silently reporting NO missing steps. The fix routes both the
default-step path (:func:`detect_missing_default_finalize_steps`) and the
project-step path (:func:`detect_missing_project_finalize_steps`, via
:func:`_read_finalize_steps`) through :func:`_extract_step_ids`, which yields the
dict keys for a keyed-map and the list verbatim for the legacy form.

This suite pins the keyed-map contract from both directions:

- the keyed-map form surfaces genuinely-missing steps (the blindness regression),
- the keyed-map form and the equivalent legacy list form produce IDENTICAL
  detection results (parity), and
- the :func:`_extract_step_ids` normalizer itself maps dict/list/other to
  keys/verbatim/``None``.

The list-form coverage lives in ``test_default_step_detection.py`` (default path)
and ``test_steward_determine_mode.py`` (project path); this file is the
keyed-map sibling and intentionally avoids restating the list-form cases.
"""

from __future__ import annotations

import json
from pathlib import Path

from conftest import load_script_module

_dm = load_script_module(
    'plan-marshall',
    'marshall-steward',
    'determine_mode.py',
    module_name='_marshall_steward_determine_mode_keyed_map',
)

detect_missing_default_finalize_steps = _dm.detect_missing_default_finalize_steps
detect_missing_project_finalize_steps = _dm.detect_missing_project_finalize_steps
discover_shipped_project_finalize_steps = _dm.discover_shipped_project_finalize_steps


# =============================================================================
# Fixtures
# =============================================================================

_PROJECT_STEPS = (
    'plugin-doctor',
    'deploy-target',
    'sync-plugin-cache',
)


def _write_marshal_steps(plan_dir: Path, steps: object) -> None:
    """Write ``marshal.json`` with ``phase-6-finalize.steps`` set verbatim.

    ``steps`` is written as-is, so callers can pass either the canonical
    keyed-map (``dict``) or the legacy list form.
    """
    plan_dir.mkdir(parents=True, exist_ok=True)
    marshal = {'plan': {'phase-6-finalize': {'steps': steps}}}
    (plan_dir / 'marshal.json').write_text(json.dumps(marshal, indent=2), encoding='utf-8')


def _keyed_map(step_ids: list[str]) -> dict[str, dict]:
    """Build a canonical keyed-map: each id maps to an empty config object."""
    return {step_id: {} for step_id in step_ids}


def _ship_project_finalize_skills(project_root: Path, names) -> None:
    """Create ``.claude/skills/finalize-step-<name>/SKILL.md`` for each name."""
    for name in names:
        skill_dir = project_root / '.claude' / 'skills' / f'finalize-step-{name}'
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / 'SKILL.md').write_text(f'# finalize-step-{name}\n', encoding='utf-8')


# =============================================================================
# _extract_step_ids — the normalizer the fix introduced
# =============================================================================


def test_extract_step_ids_dict_returns_keys():
    """A keyed-map yields its keys in insertion order (the execution order)."""
    steps = {'default:push': {}, 'default:create-pr': {'k': 'v'}, 'default:archive-plan': {}}
    assert _dm._extract_step_ids(steps) == ['default:push', 'default:create-pr', 'default:archive-plan']


def test_extract_step_ids_list_returns_verbatim():
    """A legacy list is returned unchanged."""
    steps = ['default:push', 'default:create-pr']
    assert _dm._extract_step_ids(steps) == ['default:push', 'default:create-pr']


def test_extract_step_ids_other_returns_none():
    """A non-dict, non-list value signals 'cannot compare' via ``None``."""
    assert _dm._extract_step_ids('default:push') is None
    assert _dm._extract_step_ids(None) is None
    assert _dm._extract_step_ids(42) is None


def test_read_finalize_steps_keyed_map_returns_keys(tmp_path: Path):
    """``_read_finalize_steps`` normalizes a keyed-map to its step-id keys."""
    _write_marshal_steps(tmp_path, _keyed_map(['default:push', 'default:create-pr']))
    assert _dm._read_finalize_steps(tmp_path) == ['default:push', 'default:create-pr']


# =============================================================================
# Default-step path: detect_missing_default_finalize_steps (keyed-map form)
# =============================================================================


def test_keyed_map_missing_default_steps_are_surfaced(tmp_path: Path):
    """Keyed-map ``steps`` missing built-ins → the gaps surface.

    This is the core blindness regression: before the fix, a dict ``steps``
    block was treated as "cannot compare" and the helper returned ``[]``,
    silently hiding every genuinely-missing built-in.
    """
    plan_dir = tmp_path / '.plan'
    minimal = _keyed_map(
        [
            'default:pre-push-quality-gate',
            'default:push',
            'default:archive-plan',
        ]
    )
    _write_marshal_steps(plan_dir, minimal)

    missing = detect_missing_default_finalize_steps(plan_dir)

    # Built-ins absent from the keyed-map surface as missing.
    assert 'default:create-pr' in missing
    assert 'default:lessons-capture' in missing
    # Present keyed-map entries do NOT surface.
    assert 'default:push' not in missing
    assert 'default:pre-push-quality-gate' not in missing


def test_keyed_map_complete_steps_has_no_missing_defaults(tmp_path: Path):
    """Keyed-map containing every canonical built-in → empty list."""
    plan_dir = tmp_path / '.plan'
    canonical = _dm._canonical_built_in_finalize_steps()
    _write_marshal_steps(plan_dir, _keyed_map(canonical))

    assert detect_missing_default_finalize_steps(plan_dir) == []


def test_keyed_map_and_list_parity_default(tmp_path: Path):
    """Keyed-map and equivalent legacy list produce identical detection.

    The whole point of ``_extract_step_ids`` is that the two serial forms are
    interchangeable for detection — a keyed-map and a list carrying the same
    step ids must yield the same missing set.
    """
    canonical = _dm._canonical_built_in_finalize_steps()
    present = [s for s in canonical if s != 'default:lessons-capture']

    list_dir = tmp_path / 'list'
    map_dir = tmp_path / 'map'
    _write_marshal_steps(list_dir, present)
    _write_marshal_steps(map_dir, _keyed_map(present))

    list_missing = detect_missing_default_finalize_steps(list_dir)
    map_missing = detect_missing_default_finalize_steps(map_dir)

    assert map_missing == list_missing == ['default:lessons-capture']


# =============================================================================
# Project-step path: detect_missing_project_finalize_steps (keyed-map form)
# =============================================================================


def test_keyed_map_dropped_project_step_is_surfaced(tmp_path: Path):
    """Keyed-map ``steps`` missing a shipped project step → it surfaces.

    Mirrors the default-path blindness regression for the project path:
    ``_read_finalize_steps`` previously returned ``None`` for a dict, so
    ``detect_missing_project_finalize_steps`` reported nothing missing.
    """
    project_root = tmp_path / 'repo'
    plan_dir = project_root / '.plan'
    _ship_project_finalize_skills(project_root, _PROJECT_STEPS)
    # Keyed-map with two shipped project steps dropped.
    present = {
        'default:pre-submission-self-review': {},
        'project:finalize-step-sync-plugin-cache': {},
        'default:push': {},
    }
    _write_marshal_steps(plan_dir, present)

    missing = detect_missing_project_finalize_steps(plan_dir, project_root)

    assert sorted(missing) == [
        'project:finalize-step-deploy-target',
        'project:finalize-step-plugin-doctor',
    ]


def test_keyed_map_all_project_steps_present_is_clean(tmp_path: Path):
    """Keyed-map containing every shipped project step → nothing missing."""
    project_root = tmp_path / 'repo'
    plan_dir = project_root / '.plan'
    _ship_project_finalize_skills(project_root, _PROJECT_STEPS)
    step_ids = [f'project:finalize-step-{n}' for n in _PROJECT_STEPS] + ['default:push']
    _write_marshal_steps(plan_dir, _keyed_map(step_ids))

    assert detect_missing_project_finalize_steps(plan_dir, project_root) == []


def test_keyed_map_and_list_parity_project(tmp_path: Path):
    """Keyed-map and equivalent legacy list agree for the project path too."""
    project_root = tmp_path / 'repo'
    _ship_project_finalize_skills(project_root, _PROJECT_STEPS)
    step_ids = [
        'default:pre-submission-self-review',
        'project:finalize-step-plugin-doctor',
        'default:push',
    ]

    list_dir = project_root / 'list-plan'
    map_dir = project_root / 'map-plan'
    _write_marshal_steps(list_dir, step_ids)
    _write_marshal_steps(map_dir, _keyed_map(step_ids))

    list_missing = sorted(detect_missing_project_finalize_steps(list_dir, project_root))
    map_missing = sorted(detect_missing_project_finalize_steps(map_dir, project_root))

    assert map_missing == list_missing
    assert map_missing == [
        'project:finalize-step-deploy-target',
        'project:finalize-step-sync-plugin-cache',
    ]
