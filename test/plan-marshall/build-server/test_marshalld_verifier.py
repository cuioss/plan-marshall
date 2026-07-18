#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for _marshalld_verifier (S1/S2 accept/refuse matrix).

Drives the pure verifier against hand-built registry dicts and JobSpecs, with an
injected common-dir resolver so the git-common-dir worktree probe is
deterministic.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from conftest import get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-build-server', 'marshalld.py')
SCRIPTS_DIR = SCRIPT_PATH.parent

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import _build_server_protocol as proto  # noqa: E402
import _marshalld_verifier as verifier  # noqa: E402


def _registry(root: str, *, containers: list[str] | None = None, allowlist: list[str] | None = None) -> dict:
    canonical = verifier.canonicalize_root(root)
    return {
        'version': 1,
        'projects': {
            canonical: {
                'canonical_root': canonical,
                'worktree_containers': containers or [],
                'notation_allowlist': allowlist if allowlist is not None else ['a:b:c'],
            }
        },
    }


def _spec(exec_path: str, *, command: list[str] | None = None, notation: str = 'a:b:c') -> proto.JobSpec:
    executor = str(Path(exec_path) / '.plan' / 'execute-script.py')
    cmd = command if command is not None else ['python3', executor, notation, 'run']
    return proto.make_job_spec(cmd, exec_path, exec_path, 'p1')


def test_accept_registered_root(tmp_path):
    root = str(tmp_path / 'proj')
    os.mkdir(root)
    registry = _registry(root)

    outcome = verifier.verify_submit(_spec(root), registry, baseline_interpreter='python3')

    assert outcome.accepted
    assert outcome.record is not None


def test_refuse_not_registered(tmp_path):
    root = str(tmp_path / 'proj')
    os.mkdir(root)
    other = str(tmp_path / 'other')
    os.mkdir(other)
    registry = _registry(root)

    outcome = verifier.verify_submit(_spec(other), registry, baseline_interpreter='python3')

    assert not outcome.accepted
    assert outcome.reason == verifier.REFUSE_NOT_REGISTERED


def test_refuse_wrong_interpreter(tmp_path):
    root = str(tmp_path / 'proj')
    os.mkdir(root)
    registry = _registry(root)
    executor = str(Path(root) / '.plan' / 'execute-script.py')
    spec = _spec(root, command=['/usr/bin/ruby', executor, 'a:b:c'])

    outcome = verifier.verify_submit(spec, registry, baseline_interpreter='python3')

    assert outcome.reason == verifier.REFUSE_WRONG_INTERPRETER


def test_refuse_executor_mismatch(tmp_path):
    root = str(tmp_path / 'proj')
    os.mkdir(root)
    registry = _registry(root)
    spec = _spec(root, command=['python3', '/tmp/evil.py', 'a:b:c'])

    outcome = verifier.verify_submit(spec, registry, baseline_interpreter='python3')

    assert outcome.reason == verifier.REFUSE_EXECUTOR_MISMATCH


def test_refuse_notation_not_allowlisted(tmp_path):
    root = str(tmp_path / 'proj')
    os.mkdir(root)
    registry = _registry(root, allowlist=['only:this:one'])

    outcome = verifier.verify_submit(_spec(root, notation='x:y:z'), registry, baseline_interpreter='python3')

    assert outcome.reason == verifier.REFUSE_NOTATION_NOT_ALLOWLISTED


def test_refuse_invalid_args_with_nul(tmp_path):
    root = str(tmp_path / 'proj')
    os.mkdir(root)
    registry = _registry(root)
    executor = str(Path(root) / '.plan' / 'execute-script.py')
    spec = _spec(root, command=['python3', executor, 'a:b:c', 'bad\x00arg'])

    outcome = verifier.verify_submit(spec, registry, baseline_interpreter='python3')

    assert outcome.reason == verifier.REFUSE_INVALID_ARGS


def test_refuse_empty_command(tmp_path):
    root = str(tmp_path / 'proj')
    os.mkdir(root)
    registry = _registry(root)
    spec = _spec(root, command=['python3'])

    outcome = verifier.verify_submit(spec, registry, baseline_interpreter='python3')

    assert outcome.reason == verifier.REFUSE_EMPTY_COMMAND


def test_refuse_exec_path_escape(tmp_path):
    root = str(tmp_path / 'proj')
    os.mkdir(root)
    registry = _registry(root, containers=[str(tmp_path / 'worktrees')])
    outside = str(tmp_path / 'elsewhere')
    os.mkdir(outside)

    outcome = verifier.verify_submit(_spec(outside), registry, baseline_interpreter='python3')

    # 'outside' is neither the root nor under a container -> not registered by
    # the coarse lookup.
    assert outcome.reason == verifier.REFUSE_NOT_REGISTERED


def test_accept_fresh_worktree_under_container(tmp_path):
    root = str(tmp_path / 'proj')
    os.mkdir(root)
    container = tmp_path / 'worktrees'
    container.mkdir()
    worktree = container / 'feature-x'
    worktree.mkdir()
    registry = _registry(root, containers=[str(container)])

    outcome = verifier.verify_submit(
        _spec(str(worktree)),
        registry,
        baseline_interpreter='python3',
        common_dir_resolver=lambda _p: root,
    )

    assert outcome.accepted


def test_refuse_worktree_not_live_when_resolver_returns_none(tmp_path):
    root = str(tmp_path / 'proj')
    os.mkdir(root)
    container = tmp_path / 'worktrees'
    container.mkdir()
    worktree = container / 'feature-x'
    worktree.mkdir()
    registry = _registry(root, containers=[str(container)])

    outcome = verifier.verify_submit(
        _spec(str(worktree)),
        registry,
        baseline_interpreter='python3',
        common_dir_resolver=lambda _p: None,
    )

    assert outcome.reason == verifier.REFUSE_WORKTREE_NOT_LIVE


def test_refuse_worktree_common_dir_mismatch(tmp_path):
    root = str(tmp_path / 'proj')
    os.mkdir(root)
    container = tmp_path / 'worktrees'
    container.mkdir()
    worktree = container / 'feature-x'
    worktree.mkdir()
    registry = _registry(root, containers=[str(container)])

    outcome = verifier.verify_submit(
        _spec(str(worktree)),
        registry,
        baseline_interpreter='python3',
        common_dir_resolver=lambda _p: str(tmp_path / 'some-other-root'),
    )

    assert outcome.reason == verifier.REFUSE_WORKTREE_NOT_LIVE


def test_symlink_escape_canonicalizes_outside_registration(tmp_path):
    root = tmp_path / 'proj'
    root.mkdir()
    outside = tmp_path / 'outside'
    outside.mkdir()
    link = tmp_path / 'proj' / 'link'
    os.symlink(outside, link)
    registry = _registry(str(root))

    # A submit whose exec_path is the symlink resolves (canonicalizes) to
    # 'outside', which is not the registered root -> not registered.
    outcome = verifier.verify_submit(_spec(str(link)), registry, baseline_interpreter='python3')

    assert not outcome.accepted


def test_default_interpreter_names_accepted(tmp_path):
    root = str(tmp_path / 'proj')
    os.mkdir(root)
    registry = _registry(root)

    # No baseline_interpreter -> the default python3/python basenames are OK.
    outcome = verifier.verify_submit(_spec(root), registry)

    assert outcome.accepted
