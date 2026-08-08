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

import asyncio
import os
import sys

import pytest
from conftest import get_script_path

_DAEMON_DIR = get_script_path('plan-marshall', 'manage-build-server', 'marshalld.py').parent
_CLIENT_DIR = get_script_path('plan-marshall', 'build-server-client', 'build_server.py').parent
for _d in (_DAEMON_DIR, _CLIENT_DIR):
    if str(_d) not in sys.path:
        sys.path.insert(0, str(_d))

import _marshalld_supervisor as supervisor  # noqa: E402
import build_server as client  # noqa: E402
import manage_build_server as control  # noqa: E402
import marshalld  # noqa: E402
from _build_server_protocol import STATUS_QUEUED, STATUS_REFUSED, JobSpec  # noqa: E402
from _build_server_registry import canonicalize_root  # noqa: E402
from _marshalld_audit import InteractionAudit  # noqa: E402
from _marshalld_journal import Journal  # noqa: E402
from _marshalld_scheduler import Scheduler  # noqa: E402
from _marshalld_verifier import (  # noqa: E402
    REFUSE_EXECUTOR_MISMATCH,
    REFUSE_EXEC_PATH_ESCAPE,
    REFUSE_NOT_REGISTERED,
    REFUSE_NOTATION_NOT_ALLOWLISTED,
    REFUSE_PROJECT_PATH_ESCAPE,
    REFUSE_WRONG_INTERPRETER,
    _exec_path_within_registration,
    verify_submit,
)

_NOTATION = 'plan-marshall:build-pyproject:pyproject_build'

# --- Interpreter-contract fixture value --------------------------------------
#
# A Homebrew/framework-shaped interpreter path whose BASENAME is `Python` —
# matching neither `python3` nor `python`. It is a FIXTURE value, never the live
# `sys.executable`: the controls below monkeypatch `marshalld.sys.executable` to
# it so the test's verdict never depends on which interpreter happens to be
# running the suite (a CI runner, a venv, or a framework build all behave the
# same). Fixture-level neutralization is what makes these controls a real pin
# rather than an environment reading.
#
# THE CONTRACT, stated so a later reader does not "restore" a more literal-
# sounding wording and re-introduce the defect:
#
#     Homebrew-shaped PROCESS interpreter + UNSET baseline + literal `python3`
#     argv  =>  ACCEPT
#
# There is no Homebrew-shaped BASELINE to pin. The Homebrew shape belongs to the
# daemon's LAUNCH interpreter, and its leak into the baseline is precisely what
# the fix removes: `Daemon.__init__` no longer reads `sys.executable` at all, so
# the monkeypatch below is deliberately INERT post-fix — and that inertness IS
# the property under test. Pre-fix (`baseline_interpreter or sys.executable`)
# the same monkeypatch is exactly what makes the positive control fail.
_HOMEBREW_SHAPED_INTERPRETER = (
    '/opt/homebrew/Cellar/python@3.13/3.13.1/Frameworks/Python.framework/Versions/3.13'
    '/Resources/Python.app/Contents/MacOS/Python'
)

# --- Why 20+ pre-existing assertions never caught this defect -----------------
#
# Three distinct populations exercise the interpreter check, and before this
# deliverable only the first two were covered — neither of which can observe the
# defect, because the defect lives in how the daemon SUPPLIES the baseline, not
# in how the verifier COMPARES it:
#
#   1. verifier-called-with-an-explicit-pin — every pre-existing case passes
#      `baseline_interpreter='python3'` directly to `verify_submit`. This pins
#      `_interpreter_ok`'s pinned-baseline branch, which the fix leaves entirely
#      unmodified. No `Daemon` is constructed, so the substitution these cases
#      would need to see never runs.
#   2. verifier-called-with-the-baseline-omitted, still no `Daemon` — e.g.
#      `test_default_interpreter_names_accepted` in test_marshalld_verifier.py.
#      This pins the canonical `python3`/`python` fallback, but it hands
#      `verify_submit` a `None` the TEST chose. Production never did: the daemon
#      substituted `sys.executable` before the verifier was ever reached, so this
#      case proved a branch that production could not enter.
#   3. Daemon-constructed with BOTH sides covarying — the only population that
#      can see it. The submitted `command[0]` and the daemon's baseline both
#      derive from "whatever interpreter is around", so on a machine whose
#      `python3` resolves to a `python3`-basenamed binary the two agree and every
#      submit is accepted; on a framework/Homebrew machine they disagree and
#      every submit is refused. The verdict tracked the environment, not the
#      code — which is why it reproduced for some operators and not others.
#
# The controls below are population 3: they construct the daemon exactly as
# `build_daemon()` does and drive a real `submit` through `Daemon.handle_request`,
# holding the argv fixed while the process interpreter is pinned to a shape that
# would poison a substituted baseline.


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


# --- Interpreter contract: matched positive / negative controls ---------------


def _daemon_built_the_production_way(tmp_path, monkeypatch, registry):
    """Construct a Daemon EXACTLY as ``build_daemon()`` does, under a framework interpreter.

    Mirrors ``build_daemon()``'s call shape — scheduler / journal / interaction
    audit, and deliberately NO ``baseline_interpreter`` — so the daemon under
    test supplies its baseline the same way production does. ``max_slots=0``
    keeps an accepted job ``queued``, so no build child is ever spawned.
    """
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(tmp_path))
    monkeypatch.setattr(marshalld.sys, 'executable', _HOMEBREW_SHAPED_INTERPRETER)
    monkeypatch.setattr(marshalld, 'read_registry', lambda: registry)
    return marshalld.Daemon(
        scheduler=Scheduler(max_slots=0),
        journal=Journal(),
        interaction_audit=InteractionAudit(),
    )


def _submit_through_daemon(daemon, spec):
    """Drive one real ``submit`` through the daemon's own request dispatch."""
    return asyncio.run(daemon.handle_request({'op': 'submit', 'job': spec.to_dict()}))


def test_unset_baseline_accepts_production_argv_under_framework_interpreter(tmp_path, monkeypatch):
    """POSITIVE control — the twin of the two negative controls below.

    Homebrew-shaped process interpreter + unset baseline + the literal `python3`
    argv the routing seam actually submits => ACCEPT. Pre-fix this refused with
    ``wrong_interpreter``, because ``Daemon.__init__`` substituted the
    framework-shaped ``sys.executable`` for the absent baseline.
    """
    root = canonicalize_root(tmp_path / 'proj')
    daemon = _daemon_built_the_production_way(tmp_path, monkeypatch, _registry(root))

    response = _submit_through_daemon(daemon, _spec(root))

    assert response['status'] == STATUS_QUEUED


@pytest.mark.parametrize('wrong_interpreter', ['/usr/bin/ruby', '/bin/sh'])
def test_unset_baseline_still_refuses_a_non_python_interpreter(tmp_path, monkeypatch, wrong_interpreter):
    """NEGATIVE controls — mandatory twins of the positive control above.

    Identical fixture and identical daemon construction, with ONLY ``command[0]``
    replaced by a genuinely non-Python interpreter. Without these, the positive
    control's ACCEPT would be indistinguishable from the interpreter check having
    stopped firing altogether.
    """
    root = canonicalize_root(tmp_path / 'proj')
    daemon = _daemon_built_the_production_way(tmp_path, monkeypatch, _registry(root))
    spec = _spec(root)
    spec.command = [wrong_interpreter, *spec.command[1:]]

    response = _submit_through_daemon(daemon, spec)

    assert response['status'] == STATUS_REFUSED
    assert response['reason'] == REFUSE_WRONG_INTERPRETER


@pytest.mark.parametrize('located_interpreter', ['/tmp/x/python3', './python3', 'bin/python'])
def test_unset_baseline_refuses_a_path_qualified_python_name(tmp_path, monkeypatch, located_interpreter):
    """NEGATIVE controls for the LOCATION half of the no-pin check.

    Twins of the positive control above: each carries a canonical Python
    BASENAME but a client-supplied LOCATION. A basename-only check would accept
    every one of them, so these are what distinguish "constrains the name" from
    "constrains name and location". The no-pin branch requires a bare name so
    the daemon resolves the binary from its own server-side ``PATH``.
    """
    root = canonicalize_root(tmp_path / 'proj')
    daemon = _daemon_built_the_production_way(tmp_path, monkeypatch, _registry(root))
    spec = _spec(root)
    spec.command = [located_interpreter, *spec.command[1:]]

    response = _submit_through_daemon(daemon, spec)

    assert response['status'] == STATUS_REFUSED
    assert response['reason'] == REFUSE_WRONG_INTERPRETER


def test_pinned_baseline_still_accepts_a_path_qualified_basename_match(tmp_path):
    """The pinned branch deliberately KEEPS its basename fallback.

    The narrowing above applies only to the no-pin branch. A caller that
    supplied the pin has already named the interpreter it means, so an absolute
    path sharing the pin's basename still matches. Without this control the
    narrowing could silently spread to the pinned branch unnoticed.
    """
    root = canonicalize_root(tmp_path / 'proj')
    spec = _spec(root)
    spec.command = ['/opt/venv/bin/python3', *spec.command[1:]]

    outcome = verify_submit(spec, _registry(root), baseline_interpreter='python3')

    assert outcome.accepted


def test_explicit_pinned_baseline_still_refuses_a_mismatching_argv(tmp_path):
    """Pinned-baseline control, retained.

    ``_interpreter_ok``'s explicit-pin branch is unchanged by this deliverable —
    a caller that DOES supply a pin still gets a mismatching ``command[0]``
    refused. Only the daemon's substitution of an absent baseline was removed.
    """
    root = canonicalize_root(tmp_path / 'proj')
    spec = _spec(root)
    spec.command = ['/usr/bin/ruby', *spec.command[1:]]

    outcome = verify_submit(spec, _registry(root), baseline_interpreter='python3')

    assert not outcome.accepted
    assert outcome.reason == REFUSE_WRONG_INTERPRETER
