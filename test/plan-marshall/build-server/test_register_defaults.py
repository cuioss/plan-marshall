#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for registration-scope default population and backfill-on-re-register.

Exercise ``manage_build_server.run_register``'s default-scope policy: when the
operator omits ``--container`` / ``--notation``, the scope fields are populated
from canonical defaults (the routable build notations and the canonical worktree
container) rather than stored empty — the empty-scope entry that left a
registered project inert. Re-running ``register`` is the repair path: it
backfills empty fields while preserving any non-empty stored values, with the
precedence explicit CLI value > existing non-empty stored value > computed
default.

Every test isolates the machine-global home root by pointing
``PLAN_MARSHALL_HOME`` at a per-test ``tmp_path`` so no test touches the real
``~/.plan-marshall/`` tree.
"""

from __future__ import annotations

import sys
from argparse import Namespace
from pathlib import Path

import pytest
from conftest import get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-build-server', 'manage_build_server.py')
SCRIPTS_DIR = SCRIPT_PATH.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import _build_execute_factory as factory  # noqa: E402
import _build_server_registry as registry  # noqa: E402
import manage_build_server as mbs  # noqa: E402


@pytest.fixture
def home(tmp_path, monkeypatch) -> Path:
    """Point the machine-global home root at an isolated tmp dir."""
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path))
    return Path(tmp_path)


def _expected_container(canonical_root: str) -> str:
    """Return the canonical worktree container for ``canonical_root``."""
    return str(Path(canonical_root) / '.plan' / 'local' / 'worktrees')


# =============================================================================
# (a) fresh register with no flags populates the default scope
# =============================================================================


def test_fresh_register_no_flags_populates_default_scope(home):
    root = home / 'proj'
    root.mkdir()

    result = mbs.run_register(Namespace(root=str(root), container=None, notation=None))

    canonical = registry.canonicalize_root(root)
    # The default allowlist is the routable build notations (single source of
    # truth shared with the D5 routing seam).
    assert result['notation_allowlist'] == list(factory.routable_notations())
    # The default container is the canonical worktree location every plan uses.
    assert result['worktree_containers'] == [_expected_container(canonical)]
    # Both scope fields are non-empty — the project is routable, not inert.
    assert result['notation_allowlist']
    assert result['worktree_containers']


# =============================================================================
# (b) routable_notations() is the single source of truth (drift guard)
# =============================================================================


def test_routable_notations_matches_tool_notations():
    # The registration default and the D5 routing map share one source: the
    # sorted values of the tool->notation map. A drift here means a build tool
    # is routable but not default-allowlisted (or vice versa).
    assert factory.routable_notations() == tuple(sorted(factory._TOOL_NOTATIONS.values()))


# =============================================================================
# (c) re-register of an empty entry backfills defaults and preserves registered_at
# =============================================================================


def test_reregister_empty_entry_backfills_and_preserves_registered_at(home):
    root = home / 'proj'
    root.mkdir()
    canonical = registry.canonicalize_root(root)
    # Seed an OLD-style empty-scope entry (the inert registration).
    seeded = registry.register_project(canonical, worktree_containers=[], notation_allowlist=[])
    original_registered_at = seeded['registered_at']

    # Re-register with no flags → the repair path backfills the defaults.
    result = mbs.run_register(Namespace(root=str(root), container=None, notation=None))

    assert result['notation_allowlist'] == list(factory.routable_notations())
    assert result['worktree_containers'] == [_expected_container(canonical)]
    # Re-registration preserves the original first-registration timestamp.
    assert result['registered_at'] == original_registered_at


# =============================================================================
# (d) re-register preserves non-empty stored values (no wipe)
# =============================================================================


def test_reregister_preserves_nonempty_stored_values(home):
    root = home / 'proj'
    root.mkdir()
    canonical = registry.canonicalize_root(root)
    registry.register_project(
        canonical,
        worktree_containers=[str(home / 'custom-wts')],
        notation_allowlist=['custom:only:notation'],
    )

    # Re-register with no CLI args must NOT wipe deliberately-customised values.
    result = mbs.run_register(Namespace(root=str(root), container=None, notation=None))

    assert result['worktree_containers'] == [str(home / 'custom-wts')]
    assert result['notation_allowlist'] == ['custom:only:notation']


# =============================================================================
# (e) explicit CLI flags override both the stored value and the default
# =============================================================================


def test_explicit_flags_override_stored_and_default(home):
    root = home / 'proj'
    root.mkdir()
    canonical = registry.canonicalize_root(root)
    registry.register_project(
        canonical,
        worktree_containers=[str(home / 'old-wts')],
        notation_allowlist=['old:stored:notation'],
    )

    result = mbs.run_register(
        Namespace(
            root=str(root),
            container=[str(home / 'explicit-wts')],
            notation=['explicit:cli:notation'],
        )
    )

    # Explicit CLI values win over both the stored value and the computed default.
    assert result['worktree_containers'] == [str(home / 'explicit-wts')]
    assert result['notation_allowlist'] == ['explicit:cli:notation']


# =============================================================================
# (f) a corrupted non-list stored value falls back to the computed default
# =============================================================================


def test_effective_scope_value_non_list_stored_falls_back_to_default():
    # A hand-edited / corrupted registry.json may store a bare string instead of
    # a list. list(stored) would then split it into individual characters; the
    # isinstance guard makes the corrupted value fall back to the computed default
    # rather than producing a bogus per-character list.
    default = ['a:b:c', 'd:e:f']
    existing = {'notation_allowlist': 'corrupted:string:notation'}

    result = mbs._effective_scope_value(None, existing, 'notation_allowlist', default)

    assert result == default
    # Explicitly guard against the per-character split the bug produced.
    assert result != list('corrupted:string:notation')
