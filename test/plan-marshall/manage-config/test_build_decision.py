#!/usr/bin/env python3
"""Tests for the centralized build-decision API.

Covers the two halves of deliverable 4:

- ``should_execute_build`` (module-level in ``script-shared``/``extension_base``):
  the pure build-necessity decision over the ``build.map`` globs and
  the live plan footprint. Both verdicts are exercised:
    * empty build_map           -> not_necessary (reason populated)
    * empty footprint           -> not_necessary (reason populated)
    * footprint matches no glob -> not_necessary (reason populated)
    * footprint intersects glob -> build
- ``cmd_build_decision`` (the ``manage-config build-decision`` handler): wraps
  ``should_execute_build`` and returns its verdict as a ``status: success`` dict;
  a missing ``--plan-id`` surfaces a structured error.

The footprint and build_map readers are deferred-import, cross-skill helpers; the
tests redirect them on the ``extension_base`` module object so the decision logic
itself — not a live git worktree — is exercised deterministically.
"""

# ruff: noqa: I001, E402

import importlib.util
import sys
from argparse import Namespace
from pathlib import Path

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-config'
    / 'scripts'
)

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_cmd_build_map_mod = _load_module('_cmd_build_map_for_build_decision_test', '_cmd_build_map.py')

# extension_base lives in script-shared and is on PYTHONPATH (executor wires every
# skill scripts dir). The handler resolves should_execute_build from it at call
# time, so monkeypatching helpers on this same module object is what the handler
# (and the direct should_execute_build calls below) actually observe.
import extension_base  # type: ignore[import-not-found]  # noqa: E402


# =============================================================================
# should_execute_build — pure decision over build_map globs + footprint
# =============================================================================


def test_empty_build_map_is_not_necessary(monkeypatch):
    """No registered build globs -> not_necessary with a populated reason."""
    # Arrange — build_map registers nothing.
    monkeypatch.setattr(extension_base, '_read_build_map_globs', lambda _root=None: [])
    monkeypatch.setattr(extension_base, '_resolve_plan_footprint', lambda _plan: ['scripts/foo.py'])

    # Act
    verdict = extension_base.should_execute_build('quality-gate', 'my-plan')

    # Assert
    assert verdict['decision'] == 'not_necessary'
    assert verdict['reason']
    assert verdict['canonical_command'] == 'quality-gate'


def test_empty_footprint_is_not_necessary(monkeypatch):
    """A non-empty build_map but an empty footprint -> not_necessary, reason populated."""
    # Arrange — globs exist, but nothing changed.
    monkeypatch.setattr(extension_base, '_read_build_map_globs', lambda _root=None: ['scripts/*.py'])
    monkeypatch.setattr(extension_base, '_resolve_plan_footprint', lambda _plan: [])

    # Act
    verdict = extension_base.should_execute_build('verify', 'my-plan')

    # Assert
    assert verdict['decision'] == 'not_necessary'
    assert verdict['reason']
    assert verdict['canonical_command'] == 'verify'


def test_footprint_matching_no_glob_is_not_necessary(monkeypatch):
    """A footprint that intersects no build glob -> not_necessary, reason populated.

    Regression guard against a spurious build on an artifact-only footprint: a
    ``uv.lock`` / ``target/`` change that no build_map glob covers must not trigger
    a build.
    """
    # Arrange — globs cover only scripts/*.py, footprint is a lockfile.
    monkeypatch.setattr(extension_base, '_read_build_map_globs', lambda _root=None: ['scripts/*.py'])
    monkeypatch.setattr(extension_base, '_resolve_plan_footprint', lambda _plan: ['uv.lock'])

    # Act
    verdict = extension_base.should_execute_build('quality-gate', 'my-plan')

    # Assert
    assert verdict['decision'] == 'not_necessary'
    assert verdict['reason']
    assert verdict['canonical_command'] == 'quality-gate'


def test_footprint_intersecting_a_glob_is_build(monkeypatch):
    """A footprint touching a registered build glob -> build, echoing the command."""
    # Arrange — a changed production .py matches the registered glob.
    monkeypatch.setattr(extension_base, '_read_build_map_globs', lambda _root=None: ['scripts/*.py'])
    monkeypatch.setattr(
        extension_base, '_resolve_plan_footprint', lambda _plan: ['scripts/foo.py']
    )

    # Act
    verdict = extension_base.should_execute_build('quality-gate', 'my-plan')

    # Assert
    assert verdict['decision'] == 'build'
    assert verdict['canonical_command'] == 'quality-gate'
    # The build verdict carries no reason (only not_necessary does).
    assert 'reason' not in verdict


# =============================================================================
# cmd_build_decision — manage-config build-decision handler
# =============================================================================


def test_handler_returns_build_verdict(monkeypatch):
    """The handler wraps a build verdict as a status: success dict."""
    # Arrange
    monkeypatch.setattr(extension_base, '_read_build_map_globs', lambda _root=None: ['scripts/*.py'])
    monkeypatch.setattr(
        extension_base, '_resolve_plan_footprint', lambda _plan: ['scripts/foo.py']
    )

    # Act
    result = _cmd_build_map_mod.cmd_build_decision(
        Namespace(command='quality-gate', plan_id='my-plan', audit_plan_id=None)
    )

    # Assert
    assert result['status'] == 'success'
    assert result['decision'] == 'build'
    assert result['canonical_command'] == 'quality-gate'


def test_handler_returns_not_necessary_with_reason(monkeypatch):
    """The handler surfaces the not_necessary verdict and its reason."""
    # Arrange — empty footprint forces not_necessary.
    monkeypatch.setattr(extension_base, '_read_build_map_globs', lambda _root=None: ['scripts/*.py'])
    monkeypatch.setattr(extension_base, '_resolve_plan_footprint', lambda _plan: [])

    # Act
    result = _cmd_build_map_mod.cmd_build_decision(
        Namespace(command='verify', plan_id='my-plan', audit_plan_id=None)
    )

    # Assert
    assert result['status'] == 'success'
    assert result['decision'] == 'not_necessary'
    assert result['reason']


def test_handler_accepts_audit_plan_id_alias(monkeypatch):
    """--audit-plan-id is honoured as an alias when --plan-id is absent."""
    # Arrange
    monkeypatch.setattr(extension_base, '_read_build_map_globs', lambda _root=None: ['scripts/*.py'])
    monkeypatch.setattr(
        extension_base, '_resolve_plan_footprint', lambda _plan: ['scripts/foo.py']
    )

    # Act — only audit_plan_id is set.
    result = _cmd_build_map_mod.cmd_build_decision(
        Namespace(command='quality-gate', plan_id=None, audit_plan_id='my-plan')
    )

    # Assert
    assert result['status'] == 'success'
    assert result['decision'] == 'build'


def test_handler_errors_when_plan_id_missing():
    """A missing plan identifier surfaces a structured error, not a crash."""
    # Act
    result = _cmd_build_map_mod.cmd_build_decision(
        Namespace(command='quality-gate', plan_id=None, audit_plan_id=None)
    )

    # Assert
    assert result['status'] == 'error'
    assert 'plan-id' in result['error']
