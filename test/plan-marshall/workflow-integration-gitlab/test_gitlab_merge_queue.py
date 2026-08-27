#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the GitLab merge-train surface (deliverable 2).

Three handlers are covered, all with API-shape-faithful fixtures (no live glab):

* ``cmd_pr_merge_queue`` — reads the project's merge-train state BEFORE the
  enqueue, then performs a REAL merge-train enqueue via
  ``POST /projects/:id/merge_trains/merge_requests/:iid``, pinned by a
  constructed-argv assertion against the captured ``run_glab`` invocation. The
  pre-POST probe is what lets an off-routed dispatch refuse without a side
  effect, so the refusal cases assert on the ABSENCE of the POST, not merely on
  the returned status.
* ``cmd_repo_merge_queue_probe`` — reads ``merge_trains_enabled`` from
  ``GET /projects/:id`` and maps each state to the shared eligibility
  discriminator, including the auth-scope actionable-error path.
* ``cmd_repo_merge_queue_enable`` — idempotent no-op when already configured,
  ``PUT /projects/:id`` when unconfigured, actionable refusal when ineligible.
"""

import argparse

import gitlab_ops
import pytest
from _ci_wait_contract import _ok_auth


def _mq_ns(*, pr_number=42, head=None, strategy='merge', delete_branch=False):
    return argparse.Namespace(
        pr_number=pr_number, head=head, strategy=strategy, delete_branch=delete_branch
    )


def _install_common(monkeypatch):
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'get_project_path', lambda: 'group/repo')


def _stub_probe(monkeypatch, discriminator, *, detail='stubbed probe', error=None) -> dict:
    """Stub ``_probe_merge_train_state`` for the pre-enqueue read.

    The probe is PROJECT-scoped and takes no branch argument, so the stub's
    signature mirrors that exactly — a fixture can never drift into asserting a
    per-branch shape GitLab does not have.

    The ``cmd_repo_merge_queue_*`` scenarios deliberately do NOT use this helper:
    they drive the real probe through a stubbed ``run_api`` because the mapping
    from Projects-API response to discriminator is precisely what they assert.
    """
    captured: dict = {'calls': 0}

    def probe_stub():
        captured['calls'] += 1
        return discriminator, detail, error

    monkeypatch.setattr(gitlab_ops, '_probe_merge_train_state', probe_stub)
    return captured


def _post_calls(captured: list[list[str]]) -> list[list[str]]:
    """Every captured merge-train enqueue POST — the verb's only side effect."""
    return [c for c in captured if c[:3] == ['api', '-X', 'POST']]


# ---------------------------------------------------------------------------
# pr merge-queue — real merge-train enqueue
# ---------------------------------------------------------------------------


def test_cmd_pr_merge_queue_enqueues_via_merge_train(monkeypatch):
    # Arrange — the project actually runs a train, so the enqueue proceeds.
    _install_common(monkeypatch)
    monkeypatch.setattr(gitlab_ops, '_resolve_mr_iid', lambda args, op: ('42', None))
    _stub_probe(monkeypatch, gitlab_ops.MERGE_QUEUE_ELIGIBLE_CONFIGURED)
    captured: list[list[str]] = []

    def run_glab_stub(args):
        captured.append(list(args))
        return 0, '{"id": 7, "merge_request": {"iid": 42}}', ''

    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    # Act
    result = gitlab_ops.cmd_pr_merge_queue(_mq_ns())

    # Assert — a REAL POST to the merge-train endpoint, not a fail-loud error.
    assert result['status'] == 'success'
    assert result['operation'] == 'pr_merge_queue'
    assert result['provider'] == 'gitlab'
    assert result['enqueued'] is True
    assert result['merge_train_car_id'] == '7'
    assert captured == [
        ['api', '-X', 'POST', 'projects/group%2Frepo/merge_trains/merge_requests/42']
    ]


# --- Off-routing: the probe refuses BEFORE the POST --------------------------
#
# The enqueue endpoint answers a project with no train with a 404 that reads
# identically to a routing mistake, so a verb that learns only from the POST
# cannot tell the two apart — and has already paid the side effect by the time
# it finds out. Each case below asserts the ABSENCE of the POST, which is the
# part a status-only assertion would miss.


@pytest.mark.parametrize(
    'discriminator',
    [
        gitlab_ops.MERGE_QUEUE_ELIGIBLE_UNCONFIGURED,
        gitlab_ops.MERGE_QUEUE_INELIGIBLE,
    ],
    ids=['train_available_but_off', 'tier_does_not_offer_trains'],
)
def test_cmd_pr_merge_queue_refuses_off_routing_without_posting(monkeypatch, discriminator):
    """A project that runs no train refuses, and issues no merge-train POST.

    ``run_glab`` is stubbed to SUCCEED, so a POST that was issued would be
    reported as a successful enqueue. The refusal therefore proves the probe
    gated the side effect rather than the endpoint rejecting it.
    """
    # Arrange
    _install_common(monkeypatch)
    monkeypatch.setattr(gitlab_ops, '_resolve_mr_iid', lambda args, op: ('42', None))
    probe = _stub_probe(monkeypatch, discriminator, detail='project group/repo: merge_trains_enabled=false')
    captured: list[list[str]] = []

    def run_glab_stub(args):
        captured.append(list(args))
        return 0, '{"id": 7}', ''

    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    # Act
    result = gitlab_ops.cmd_pr_merge_queue(_mq_ns())

    # Assert
    assert result['status'] == 'error', result
    assert result['operation'] == 'pr_merge_queue'
    assert probe['calls'] == 1, probe
    assert _post_calls(captured) == [], captured
    message = ' '.join(str(v) for v in result.values()).lower()
    assert 'merge train' in message
    assert 'safe-merge' in message
    assert '/marshall-steward' in message


def test_cmd_pr_merge_queue_probe_error_refuses_without_posting(monkeypatch):
    """A probe that established nothing refuses without reaching the POST.

    An unread ``merge_trains_enabled`` is not evidence that the enqueue is the
    right call, so the scope-resolution failure fails closed here exactly as it
    does on the immediate-merge verbs.
    """
    _install_common(monkeypatch)
    monkeypatch.setattr(gitlab_ops, '_resolve_mr_iid', lambda args, op: ('42', None))
    _stub_probe(
        monkeypatch,
        gitlab_ops.MERGE_QUEUE_UNSUPPORTED,
        detail='could not resolve the GitLab project scope',
        error=gitlab_ops._MERGE_TRAIN_SCOPE_UNRESOLVED_HINT,
    )
    captured: list[list[str]] = []

    def run_glab_stub(args):
        captured.append(list(args))
        return 0, '{"id": 7}', ''

    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    result = gitlab_ops.cmd_pr_merge_queue(_mq_ns())

    assert result['status'] == 'error', result
    assert _post_calls(captured) == [], captured
    message = ' '.join(str(v) for v in result.values())
    assert 'scope could not be resolved' in message, result
    # Nothing resolved a project, so no project path may be interpolated.
    assert 'group/repo' not in message, result


# --- Endpoint-arm refusals: reached only past an eligible_configured probe ----


@pytest.mark.parametrize(
    'stderr',
    ['HTTP 403 Forbidden', 'HTTP 404 Not Found'],
    ids=['403', '404'],
)
def test_cmd_pr_merge_queue_ineligible_on_endpoint_refusal(monkeypatch, stderr):
    """Both endpoint-refusal arms name merge trains AND the alternative verb.

    The 403 and 404 arms are one branch in the handler, so they carry one
    message contract — asserting it on only one of them would leave the other
    free to drift.
    """
    # Arrange — the probe cleared, so the endpoint itself is the refusal.
    _install_common(monkeypatch)
    monkeypatch.setattr(gitlab_ops, '_resolve_mr_iid', lambda args, op: ('42', None))
    _stub_probe(monkeypatch, gitlab_ops.MERGE_QUEUE_ELIGIBLE_CONFIGURED)
    monkeypatch.setattr(gitlab_ops, 'run_glab', lambda args: (1, '', stderr))

    # Act
    result = gitlab_ops.cmd_pr_merge_queue(_mq_ns())

    # Assert — actionable ineligible error naming merge trains, never a stack trace.
    assert result['status'] == 'error'
    assert result['operation'] == 'pr_merge_queue'
    message = ' '.join(str(v) for v in result.values()).lower()
    assert 'merge train' in message
    # A boundary, not a wall: the refusal must also name the alternative routed
    # verb so a reader who cannot enable merge trains is led to the correct next
    # verb rather than left at a dead end.
    assert 'safe-merge' in message
    # The project path resolved before the POST, so the refusal names it.
    assert 'group/repo' in message


def test_cmd_pr_merge_queue_generic_error_is_not_ineligible(monkeypatch):
    # A non-403/404 failure is a plain enqueue error (not the ineligible branch).
    _install_common(monkeypatch)
    monkeypatch.setattr(gitlab_ops, '_resolve_mr_iid', lambda args, op: ('42', None))
    _stub_probe(monkeypatch, gitlab_ops.MERGE_QUEUE_ELIGIBLE_CONFIGURED)
    monkeypatch.setattr(
        gitlab_ops, 'run_glab', lambda args: (1, '', 'HTTP 500 Internal Server Error')
    )

    result = gitlab_ops.cmd_pr_merge_queue(_mq_ns())
    assert result['status'] == 'error'
    message = ' '.join(str(v) for v in result.values()).lower()
    assert 'failed to enqueue' in message
    # A known-path refusal: the project resolved, so the message names it.
    assert 'group/repo' in message


def test_cmd_pr_merge_queue_auth_failure(monkeypatch):
    monkeypatch.setattr(gitlab_ops, 'check_auth', lambda: (False, 'not authed'))
    result = gitlab_ops.cmd_pr_merge_queue(_mq_ns())
    assert result['status'] == 'error'
    assert result['operation'] == 'pr_merge_queue'


# ---------------------------------------------------------------------------
# repo merge-queue probe — merge_trains_enabled → eligibility discriminator
# ---------------------------------------------------------------------------


def test_repo_merge_queue_probe_configured(monkeypatch):
    _install_common(monkeypatch)
    monkeypatch.setattr(
        gitlab_ops, 'run_api', lambda ep: (0, {'merge_trains_enabled': True}, '')
    )

    result = gitlab_ops.cmd_repo_merge_queue_probe(argparse.Namespace())
    assert result['status'] == 'success'
    assert result['operation'] == 'repo_merge_queue_probe'
    assert result['provider'] == 'gitlab'
    assert result['eligibility'] == 'eligible_configured'


def test_repo_merge_queue_probe_unconfigured(monkeypatch):
    _install_common(monkeypatch)
    monkeypatch.setattr(
        gitlab_ops, 'run_api', lambda ep: (0, {'merge_trains_enabled': False}, '')
    )

    result = gitlab_ops.cmd_repo_merge_queue_probe(argparse.Namespace())
    assert result['eligibility'] == 'eligible_unconfigured'


def test_repo_merge_queue_probe_ineligible_when_field_absent(monkeypatch):
    # The Projects API response lacks merge_trains_enabled → tier does not expose it.
    _install_common(monkeypatch)
    monkeypatch.setattr(gitlab_ops, 'run_api', lambda ep: (0, {'id': 5}, ''))

    result = gitlab_ops.cmd_repo_merge_queue_probe(argparse.Namespace())
    assert result['eligibility'] == 'ineligible'


def test_repo_merge_queue_probe_auth_scope_error(monkeypatch):
    _install_common(monkeypatch)
    monkeypatch.setattr(gitlab_ops, 'run_api', lambda ep: (1, None, 'HTTP 403 Forbidden'))

    result = gitlab_ops.cmd_repo_merge_queue_probe(argparse.Namespace())
    # Auth-scope failure surfaces the actionable error, not a discriminator.
    assert result['status'] == 'error'
    assert result['operation'] == 'repo_merge_queue_probe'
    message = ' '.join(str(v) for v in result.values()).lower()
    assert 'scope' in message or 'permission' in message


def test_repo_merge_queue_probe_unresolvable_scope_is_error_not_ineligible(monkeypatch):
    """An unresolvable project scope establishes NOTHING — it is not ``ineligible``.

    Reporting it as ``ineligible`` would read as "this project cannot run a merge
    train": a claim about a project that was never identified, and the exact
    claim that lets ``_refuse_on_required_merge_train`` permit an immediate
    merge. It must therefore carry an actionable error instead.
    """
    monkeypatch.setattr(gitlab_ops, 'check_auth', _ok_auth)
    monkeypatch.setattr(gitlab_ops, 'get_project_path', lambda: None)

    def _boom(endpoint):
        raise AssertionError('an unresolved scope must not reach the Projects API')

    monkeypatch.setattr(gitlab_ops, 'run_api', _boom)

    result = gitlab_ops.cmd_repo_merge_queue_probe(argparse.Namespace())
    assert result['status'] == 'error'
    assert result.get('eligibility') != 'ineligible'
    message = ' '.join(str(v) for v in result.values())
    assert 'scope could not be resolved' in message, result


def test_repo_merge_queue_probe_generic_api_error_is_error_not_ineligible(monkeypatch):
    # A non-auth run_api failure (transient HTTP 500) must surface as a real
    # error result — NOT be folded into the 'ineligible' discriminator, which
    # would wrongly tell the operator the platform lacks the feature.
    _install_common(monkeypatch)
    monkeypatch.setattr(
        gitlab_ops, 'run_api', lambda ep: (1, None, 'HTTP 500 Internal Server Error')
    )

    result = gitlab_ops.cmd_repo_merge_queue_probe(argparse.Namespace())
    assert result['status'] == 'error'
    assert result['operation'] == 'repo_merge_queue_probe'
    assert result.get('eligibility') != 'ineligible'


def test_repo_merge_queue_probe_malformed_response_is_error_not_ineligible(monkeypatch):
    # A well-formed HTTP 200 whose body is not a JSON object is an unexpected API
    # shape, not a feature-availability verdict — it must surface as an error.
    _install_common(monkeypatch)
    monkeypatch.setattr(gitlab_ops, 'run_api', lambda ep: (0, ['not', 'an', 'object'], ''))

    result = gitlab_ops.cmd_repo_merge_queue_probe(argparse.Namespace())
    assert result['status'] == 'error'
    assert result.get('eligibility') != 'ineligible'


def test_repo_merge_queue_probe_auth_failure(monkeypatch):
    monkeypatch.setattr(gitlab_ops, 'check_auth', lambda: (False, 'not authed'))
    result = gitlab_ops.cmd_repo_merge_queue_probe(argparse.Namespace())
    assert result['status'] == 'error'


# --- Present-but-non-boolean merge_trains_enabled must fail CLOSED -----------
#
# `error is None` is the probe's "this verdict established the project's
# merge-train support" marker, and `_refuse_on_required_merge_train` permits an
# immediate merge on exactly that set. A present-but-non-boolean value —
# `null`, a string, a number — establishes nothing, so landing it in that set
# made the guard fail OPEN on precisely the malformed input its docstring
# promises it fails closed on. These cases pin the tuple the guard reads, and
# the one below them pins the refusal that tuple produces.


@pytest.mark.parametrize(
    'value',
    [None, 'true', 1, 0.0, [], {}],
    ids=['null', 'string', 'int', 'float', 'list', 'object'],
)
def test_probe_non_boolean_merge_trains_enabled_is_unsupported_with_error(monkeypatch, value):
    # Arrange — the field IS present, so the absent-field branch does not apply.
    _install_common(monkeypatch)
    monkeypatch.setattr(
        gitlab_ops, 'run_api', lambda ep: (0, {'merge_trains_enabled': value}, '')
    )

    # Act
    discriminator, detail, error = gitlab_ops._probe_merge_train_state()

    # Assert — outside the `error is None` set, and naming the concrete project.
    assert discriminator == gitlab_ops.MERGE_QUEUE_UNSUPPORTED
    assert error is not None
    assert 'group/repo' in detail
    assert 'not a boolean' in detail


@pytest.mark.parametrize(
    ('value', 'expected'),
    [
        (True, gitlab_ops.MERGE_QUEUE_ELIGIBLE_CONFIGURED),
        (False, gitlab_ops.MERGE_QUEUE_ELIGIBLE_UNCONFIGURED),
    ],
    ids=['true', 'false'],
)
def test_probe_boolean_merge_trains_enabled_still_establishes_support(
    monkeypatch, value, expected
):
    """Matched negative control: the two real booleans keep their error-free verdicts.

    Without this arm, a non-boolean guard that rejected everything — including
    `True` and `False` — would satisfy the cases above while destroying the
    probe.
    """
    _install_common(monkeypatch)
    monkeypatch.setattr(
        gitlab_ops, 'run_api', lambda ep: (0, {'merge_trains_enabled': value}, '')
    )

    discriminator, _detail, error = gitlab_ops._probe_merge_train_state()

    assert discriminator == expected
    assert error is None


def test_probe_absent_merge_trains_enabled_stays_ineligible_with_no_error(monkeypatch):
    """The absent-field branch is a real verdict and must NOT become UNSUPPORTED.

    An absent field means the tier does not expose merge trains — a genuine
    `ineligible` that DID read the project. The non-boolean guard is ordered
    after this branch precisely so tightening the malformed case cannot swallow
    it.
    """
    _install_common(monkeypatch)
    monkeypatch.setattr(gitlab_ops, 'run_api', lambda ep: (0, {'id': 5}, ''))

    discriminator, detail, error = gitlab_ops._probe_merge_train_state()

    assert discriminator == gitlab_ops.MERGE_QUEUE_INELIGIBLE
    assert error is None
    assert 'group/repo' in detail


@pytest.mark.parametrize(
    'value',
    [None, 'true', 1],
    ids=['null', 'string', 'int'],
)
def test_refuse_on_required_merge_train_refuses_on_non_boolean(monkeypatch, value):
    """The consequence the tuple exists for: an immediate merge is NOT permitted.

    Asserting the discriminator alone would leave the fail-open path free to
    return if the guard's arm-1 predicate ever changed, so the refusal itself is
    pinned here.
    """
    _install_common(monkeypatch)
    monkeypatch.setattr(
        gitlab_ops, 'run_api', lambda ep: (0, {'merge_trains_enabled': value}, '')
    )

    refusal = gitlab_ops._refuse_on_required_merge_train('pr_merge')

    assert refusal is not None, 'a non-boolean merge_trains_enabled must not permit a merge'
    assert refusal['status'] == 'error'
    message = ' '.join(str(v) for v in refusal.values())
    assert 'group/repo' in message


# ---------------------------------------------------------------------------
# repo merge-queue enable — idempotent / PUT / refuse
# ---------------------------------------------------------------------------


def test_repo_merge_queue_enable_idempotent_when_configured(monkeypatch):
    _install_common(monkeypatch)
    monkeypatch.setattr(
        gitlab_ops, 'run_api', lambda ep: (0, {'merge_trains_enabled': True}, '')
    )

    def _boom(args):
        raise AssertionError('enable must not mutate an already-configured project')

    monkeypatch.setattr(gitlab_ops, 'run_glab', _boom)

    result = gitlab_ops.cmd_repo_merge_queue_enable(argparse.Namespace())
    assert result['status'] == 'success'
    assert result['changed'] is False
    assert result['eligibility'] == 'eligible_configured'


def test_repo_merge_queue_enable_sets_flag_when_unconfigured(monkeypatch):
    _install_common(monkeypatch)
    monkeypatch.setattr(
        gitlab_ops, 'run_api', lambda ep: (0, {'merge_trains_enabled': False}, '')
    )
    captured: list[list[str]] = []

    def run_glab_stub(args):
        captured.append(list(args))
        return 0, '{"merge_trains_enabled": true}', ''

    monkeypatch.setattr(gitlab_ops, 'run_glab', run_glab_stub)

    result = gitlab_ops.cmd_repo_merge_queue_enable(argparse.Namespace())
    assert result['status'] == 'success'
    assert result['changed'] is True
    assert result['eligibility'] == 'eligible_configured'
    assert captured == [
        ['api', '-X', 'PUT', 'projects/group%2Frepo', '-f', 'merge_trains_enabled=true']
    ]


def test_repo_merge_queue_enable_refuses_when_ineligible(monkeypatch):
    _install_common(monkeypatch)
    monkeypatch.setattr(gitlab_ops, 'run_api', lambda ep: (0, {'id': 5}, ''))

    def _boom(args):
        raise AssertionError('enable must not mutate an ineligible project')

    monkeypatch.setattr(gitlab_ops, 'run_glab', _boom)

    result = gitlab_ops.cmd_repo_merge_queue_enable(argparse.Namespace())
    assert result['status'] == 'error'
    assert result['operation'] == 'repo_merge_queue_enable'
    message = ' '.join(str(v) for v in result.values()).lower()
    assert 'merge train' in message


def test_gitlab_ops_exposes_repo_merge_queue_handlers():
    assert callable(gitlab_ops.cmd_repo_merge_queue_probe)
    assert callable(gitlab_ops.cmd_repo_merge_queue_enable)
    assert callable(gitlab_ops.cmd_pr_merge_queue)
