#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Acceptance: the S1/S2/S3/S4 verify-not-resolve refusals.

S1/S2 — the verifier refuses an unregistered tree, an off-template argv, a
non-allowlisted notation, and an exec-path escape, and accepts a fresh
post-registration worktree. S2 — the build child's env is a clean server-side
baseline (secrets dropped). S3 — an impostor-owned socket is treated as
unreachable. S4 — register / unregister live only in the user-invocable control
skill, never on the consumption client.
"""

from __future__ import annotations

import os
import sys

from conftest import get_script_path

_DAEMON_DIR = get_script_path('plan-marshall', 'manage-build-server', 'marshalld.py').parent
_CLIENT_DIR = get_script_path('plan-marshall', 'build-server-client', 'build_server.py').parent
for _d in (_DAEMON_DIR, _CLIENT_DIR):
    if str(_d) not in sys.path:
        sys.path.insert(0, str(_d))

import _marshalld_supervisor as supervisor  # noqa: E402
import build_server as client  # noqa: E402
import manage_build_server as control  # noqa: E402
from _build_server_protocol import JobSpec  # noqa: E402
from _build_server_registry import canonicalize_root  # noqa: E402
from _marshalld_verifier import (  # noqa: E402
    REFUSE_EXECUTOR_MISMATCH,
    REFUSE_EXEC_PATH_ESCAPE,
    REFUSE_NOT_REGISTERED,
    REFUSE_NOTATION_NOT_ALLOWLISTED,
    REFUSE_PROJECT_PATH_ESCAPE,
    _exec_path_within_registration,
    verify_submit,
)

_NOTATION = 'plan-marshall:build-pyproject:pyproject_build'


def _registry(root: str, containers=None):
    return {
        'version': 1,
        'projects': {
            root: {
                'canonical_root': root,
                'notation_allowlist': [_NOTATION],
                'worktree_containers': containers or [],
            }
        },
    }


def _spec(root: str, *, notation=_NOTATION, executor=None, exec_path=None):
    exec_path = exec_path if exec_path is not None else root
    executor = executor if executor is not None else f'{exec_path}/.plan/execute-script.py'
    return JobSpec(
        command=['python3', executor, notation, 'run'],
        exec_path=exec_path, project_path=exec_path, plan_id='p', fingerprint='fp',
    )


# --- S1/S2 verifier matrix ---------------------------------------------------


def test_unregistered_tree_is_refused(tmp_path):
    root = canonicalize_root(tmp_path / 'proj')
    outcome = verify_submit(_spec('/somewhere/else'), _registry(root), baseline_interpreter='python3')
    assert not outcome.accepted
    assert outcome.reason == REFUSE_NOT_REGISTERED


def test_off_template_argv_is_refused(tmp_path):
    root = canonicalize_root(tmp_path / 'proj')
    spec = _spec(root, executor=f'{root}/evil.py')  # argv[1] is not the executor
    outcome = verify_submit(spec, _registry(root), baseline_interpreter='python3')
    assert not outcome.accepted
    assert outcome.reason == REFUSE_EXECUTOR_MISMATCH


def test_non_allowlisted_notation_is_refused(tmp_path):
    root = canonicalize_root(tmp_path / 'proj')
    spec = _spec(root, notation='nt:not:allowed')
    outcome = verify_submit(spec, _registry(root), baseline_interpreter='python3')
    assert not outcome.accepted
    assert outcome.reason == REFUSE_NOTATION_NOT_ALLOWLISTED


def test_exec_path_escape_is_refused(tmp_path):
    # The project IS registered (record present ⇒ the S1 registration wall is
    # already satisfied), yet the S2 containment guard refuses an exec_path that
    # canonicalises OUTSIDE the registered root and under no worktree container.
    # verify_submit's coarse registry lookup keys off exec_path, so a
    # fully-outside path is caught one wall earlier as not_registered; the S2
    # exec-path-escape guard is defence-in-depth and is exercised here directly
    # on the registered project's record.
    root = canonicalize_root(tmp_path / 'proj')
    escape = canonicalize_root(tmp_path / 'outside')  # under neither root nor a container
    record = {'canonical_root': root, 'notation_allowlist': [_NOTATION], 'worktree_containers': []}
    reason = _exec_path_within_registration(escape, record, None)
    assert reason == REFUSE_EXEC_PATH_ESCAPE


def test_project_path_diverging_from_exec_path_is_refused(tmp_path):
    # exec_path names the registered (legitimate) tree — S1/S2 on exec_path
    # alone would accept — but project_path (the build child's cwd) points at
    # an unrelated directory outside any registered tree. The verifier must
    # refuse: project_path is a separately client-settable job-spec field that
    # `run_job` uses verbatim as the subprocess cwd, so leaving it unverified
    # would let a submitter redirect the build's working directory anywhere the
    # daemon-owning user can access.
    root = canonicalize_root(tmp_path / 'proj')
    escape = canonicalize_root(tmp_path / 'outside')
    spec = _spec(root)
    spec.project_path = escape
    outcome = verify_submit(spec, _registry(root), baseline_interpreter='python3')
    assert not outcome.accepted
    assert outcome.reason == REFUSE_PROJECT_PATH_ESCAPE


def test_empty_project_path_is_refused(tmp_path):
    root = canonicalize_root(tmp_path / 'proj')
    spec = _spec(root)
    spec.project_path = ''
    outcome = verify_submit(spec, _registry(root), baseline_interpreter='python3')
    assert not outcome.accepted
    assert outcome.reason == REFUSE_PROJECT_PATH_ESCAPE


def test_registered_root_is_accepted(tmp_path):
    root = canonicalize_root(tmp_path / 'proj')
    outcome = verify_submit(_spec(root), _registry(root), baseline_interpreter='python3')
    assert outcome.accepted
    assert outcome.reason == ''


def test_fresh_post_registration_worktree_is_accepted(tmp_path):
    root = canonicalize_root(tmp_path / 'proj')
    container = canonicalize_root(tmp_path / 'worktrees')
    worktree = canonicalize_root(tmp_path / 'worktrees' / 'wt-1')
    spec = _spec(root, exec_path=worktree)
    # A live linked worktree whose git-common-dir resolves to the registered root.
    outcome = verify_submit(
        spec, _registry(root, containers=[container]),
        baseline_interpreter='python3', common_dir_resolver=lambda _p: root,
    )
    assert outcome.accepted


# --- S2 clean baseline env ---------------------------------------------------


def test_build_child_env_drops_secrets(tmp_path):
    env = supervisor.build_baseline_env({'PATH': '/bin', 'HOME': '/h', 'AWS_SECRET': 'leak'})
    assert env == {'PATH': '/bin', 'HOME': '/h'}
    assert 'AWS_SECRET' not in env


# --- S3 impostor socket ------------------------------------------------------


def test_impostor_owned_socket_is_untrusted(tmp_path, monkeypatch):
    sock_path = tmp_path / 'socket'
    sock_path.write_text('')  # a plain file owned by the test's own uid
    # Make the client's own uid differ from the socket owner ⇒ impostor.
    monkeypatch.setattr(os, 'getuid', lambda: os.stat(sock_path).st_uid + 1)

    reason = client._socket_owner_reason(sock_path)

    assert reason == client.REASON_IMPOSTOR_SOCKET


# --- S4 anti-laundering wall -------------------------------------------------


def test_register_unregister_live_only_on_the_control_skill():
    # The consumption client owns submit/wait/ping/preflight and NOTHING else.
    assert not hasattr(client, 'run_register')
    assert not hasattr(client, 'run_unregister')
    # Registration lives only in the user-invocable control skill.
    assert hasattr(control, 'run_register')
    assert hasattr(control, 'run_unregister')
