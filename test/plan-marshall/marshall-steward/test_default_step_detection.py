#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the marshall-steward default-finalize-step detection helper.

The wizard surfaces newly-added built-in default finalize steps when an
existing project's ``marshal.json`` predates them. ``determine_mode.py``
exposes ``detect_missing_default_finalize_steps(plan_dir)`` and a
``check-missing-finalize-steps`` subcommand for that flow.

Whenever the discovered default-on built-in finalize-step set grows (a new
phase-6-finalize step doc declares ``implements: ...ext-point-finalize-step``
with ``default_on: true``), projects whose ``marshal.json`` was seeded before
the new entries were added must have those entries surfaced so the wizard can
prompt to add them. This test suite pins that contract — it is intentionally
agnostic to which specific defaults are present, exercising the helper across
"missing several", "complete", and "partially missing" fixtures. The canonical
set is derived from the reusable ``extension_discovery.find_implementors`` query
(the SOLE finalize-step discovery path), not a hand-maintained constant.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from conftest import MARKETPLACE_ROOT

_SCRIPTS_DIR = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'marshall-steward' / 'scripts'
)
_DETERMINE_MODE = _SCRIPTS_DIR / 'determine_mode.py'

_MANAGE_CONFIG_SCRIPTS_DIR = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'manage-config' / 'scripts'
)
if str(_MANAGE_CONFIG_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_MANAGE_CONFIG_SCRIPTS_DIR))
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_dm = _load_module('_marshall_steward_determine_mode', _DETERMINE_MODE)
detect_missing_default_finalize_steps = _dm.detect_missing_default_finalize_steps


def _canonical_built_in_finalize_steps() -> list[str]:
    """Return the discovered default-on built-in finalize-step ids, in seed order.

    Mirrors ``determine_mode._canonical_built_in_finalize_steps`` (and
    ``_seed_finalize_steps``): the default-on built-in set discovered via
    ``extension_discovery.find_implementors``, sorted by ``(order, name)``. The
    hand-maintained ``BUILT_IN_FINALIZE_STEPS`` constant was removed.
    """
    from _config_defaults import FINALIZE_STEP_EXT_POINT
    from extension_discovery import find_implementors

    default_on = sorted(
        (
            rec
            for rec in find_implementors(FINALIZE_STEP_EXT_POINT)
            if rec.get('default_on') and rec.get('source') == 'built-in'
        ),
        key=lambda rec: (rec.get('order', 0), rec.get('name', '')),
    )
    return [rec['name'] for rec in default_on if rec.get('name')]


def _write_marshal(plan_dir: Path, steps: list[str]) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    marshal = {
        'plan': {
            'phase-6-finalize': {
                'steps': steps,
            },
        },
    }
    (plan_dir / 'marshal.json').write_text(json.dumps(marshal, indent=2), encoding='utf-8')


def test_missing_marshal_returns_empty_list(tmp_path: Path):
    """No marshal.json → nothing to compare against → empty list."""
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    assert detect_missing_default_finalize_steps(plan_dir) == []


def test_missing_default_steps_are_surfaced(tmp_path: Path):
    """Marshal.json missing one or more default-on built-in entries → all
    missing entries surface. Deliberately drops several built-ins to verify
    the helper finds the actual gaps regardless of which entries are absent.
    """
    plan_dir = tmp_path / '.plan'
    minimal_steps = [
        'default:pre-push-quality-gate',
        'default:push',
        'default:archive-plan',
    ]
    _write_marshal(plan_dir, minimal_steps)

    missing = detect_missing_default_finalize_steps(plan_dir)

    # Every built-in not in minimal_steps surfaces.
    assert 'default:create-pr' in missing
    assert 'default:automated-review' in missing
    assert 'default:lessons-capture' in missing
    assert 'default:record-metrics' in missing
    # Dropped entries do NOT surface (they're already present).
    assert 'default:pre-push-quality-gate' not in missing
    assert 'default:push' not in missing


def test_complete_marshal_has_no_missing_defaults(tmp_path: Path):
    """Marshal.json that already contains every default-on built-in entry → empty list."""
    plan_dir = tmp_path / '.plan'

    _write_marshal(plan_dir, _canonical_built_in_finalize_steps())
    assert detect_missing_default_finalize_steps(plan_dir) == []


def test_partially_missing_only_lists_the_gaps(tmp_path: Path):
    """Marshal.json with one absent built-in → only that one surfaces."""
    plan_dir = tmp_path / '.plan'

    # Drop a single built-in from an otherwise-complete list.
    canonical = _canonical_built_in_finalize_steps()
    incomplete = [s for s in canonical if s != 'default:lessons-capture']
    _write_marshal(plan_dir, incomplete)

    missing = detect_missing_default_finalize_steps(plan_dir)
    assert missing == ['default:lessons-capture']


def test_malformed_marshal_returns_empty_list(tmp_path: Path):
    """Garbled marshal.json → graceful empty list (helper is non-fatal)."""
    plan_dir = tmp_path / '.plan'
    plan_dir.mkdir()
    (plan_dir / 'marshal.json').write_text('{not valid json', encoding='utf-8')
    assert detect_missing_default_finalize_steps(plan_dir) == []
