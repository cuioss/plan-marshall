#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Acceptance: a project registered with default scope has its build ACCEPTED.

The positive counterpart to ``test_acceptance_fallback.py``. It asserts the
exact inverse of the inert-registration bug at the verifier boundary that gates
dispatch: a project registered via ``run_register`` with no explicit
``--container`` / ``--notation`` produces a record whose scope fields are
populated, and ``_marshalld_verifier.verify_submit`` ACCEPTS a matching submit
(build notation in the default allowlist, exec_path / project_path under the
registered root) that the old empty-scope registration would have refused.

A negative control registers the SAME root the OLD way (empty scope) and shows
the identical submit is refused with ``notation_not_allowlisted`` — isolating
the default scope population as the change that unblocks dispatch.

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
import _marshalld_verifier as verifier  # noqa: E402
import manage_build_server as mbs  # noqa: E402


@pytest.fixture
def home(tmp_path, monkeypatch) -> Path:
    """Point the machine-global home root at an isolated tmp dir."""
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path))
    return Path(tmp_path)


def _submit_spec(exec_root: str, notation: str) -> Namespace:
    """Build a job-spec whose command / paths target ``exec_root``.

    The command mirrors the executor form the daemon re-runs: interpreter,
    ``{exec_root}/.plan/execute-script.py``, the executor notation, then args.
    """
    executor = str(Path(exec_root) / '.plan' / 'execute-script.py')
    command = ['python3', executor, notation, 'run', '--command-args', 'compile']
    return Namespace(command=command, exec_path=exec_root, project_path=exec_root)


def test_registered_project_build_is_accepted(home):
    root = home / 'proj'
    root.mkdir()

    # Register with default scope — no explicit --container / --notation.
    record = mbs.run_register(Namespace(root=str(root), container=None, notation=None))
    registry_data = registry.read_registry()

    # A build whose notation is one of the populated defaults, exec_path and
    # project_path at the registered root, is accepted at the verifier boundary.
    notation = record['notation_allowlist'][0]
    outcome = verifier.verify_submit(_submit_spec(str(root), notation), registry_data)

    assert outcome.accepted is True
    assert outcome.reason == ''
    assert outcome.record is not None
    assert outcome.record['canonical_root'] == record['canonical_root']


def test_empty_scope_registration_is_refused(home):
    root = home / 'proj'
    root.mkdir()
    canonical = registry.canonicalize_root(root)

    # Register the OLD way: empty scope (the inert registration the fix repairs).
    registry.register_project(canonical, worktree_containers=[], notation_allowlist=[])
    registry_data = registry.read_registry()

    # The identical submit — a routable build notation at the registered root —
    # is refused because the empty allowlist contains no notation. This isolates
    # the default scope population as the change that unblocks dispatch.
    notation = factory.routable_notations()[0]
    outcome = verifier.verify_submit(_submit_spec(str(root), notation), registry_data)

    assert outcome.accepted is False
    assert outcome.reason == verifier.REFUSE_NOTATION_NOT_ALLOWLISTED
