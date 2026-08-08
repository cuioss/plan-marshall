#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the PR-wide ``not_triggered`` observable (github_ops pull-request-runs).

The observable answers one question: does ANY workflow run triggered by the
``pull_request`` event exist for this PR's head branch? A negative means nothing
ever ran on account of the PR, so no review bot could have published — a different
condition from a bot that was asked and stayed silent, and one whose remedy is the
opposite (trigger the review vs escalate a non-participating reviewer).

Four run-list fixtures carry the core matrix, and each is a distinct *reason* the
answer could come out wrong rather than four samples of one shape:

1. **Zero runs** — the only ``not_triggered: true`` case.
2. **A run present, concluded ``skipped``** — the LOAD-BEARING negative control.
   ``skipped`` and "no run created" are two distinct states: a skipped run was
   still TRIGGERED, so the bot was asked and this is ``not_triggered: false``.
   Collapsing the two is the defect this fixture exists to keep out.
3. **A run present, concluded ``success``** — the ordinary positive.
4. **A multi-page paginated response whose only run sits on page TWO** — the
   regression guard for the unslurped-pagination false positive. Without
   ``--slurp`` the response is a stream of concatenated JSON documents rather than
   one array, so a busy PR's runs on page two would read as zero runs and be
   misreported as ``not_triggered`` exactly where a review matters most.

Alongside the matrix: the constructed-argv assertion that the pagination flags are
actually passed (the mechanism, not just the outcome), the ``mergeable_state``
prohibition asserted at BOTH the source and behaviour level, the unconfigured
fail-loud path, and the malformed-response guard that must not manufacture a
confident answer.

Only the provider surface is monkeypatched (``check_auth``, ``view_pr_data``,
``get_repo_info``, ``run_gh``); the handler, the pagination assembly, and the pure
predicate are the real ones.

Modules are imported PLAINLY (``import github_ops``) rather than through
``conftest.load_script_module``. That is load-bearing: ``load_script_module``
re-registers ``sys.modules[name]`` with a FRESH module object, so any other module
that already imported the real one ends up holding a different object — which
breaks identity assertions elsewhere and, worse, means a monkeypatch applied here
targets globals the code under test does not read. The sibling suites
(``test_github_ops_wait.py``) import these modules plainly for the same reason.
"""

import inspect
import json

import _github_checks
import github_ops
import pytest

_HEAD_BRANCH = 'feature/some-work'


def _code_without_docstring(func):
    """Return ``func``'s source with its docstring removed.

    The source-level prohibition tests below scan for names the CODE must not
    reference. Scanning the raw source would also read the PROSE, so a docstring
    that explains *why* a field is not consulted would fail the very assertion it
    documents — the assertion must be about what the code does, not about which
    words appear near it.
    """
    source = inspect.getsource(func)
    doc = func.__doc__
    return source.replace(doc, '') if doc else source


def _run(event, conclusion='success'):
    """One workflow-run record in the shape the actions/runs API returns."""
    return {'id': 12345, 'event': event, 'status': 'completed', 'conclusion': conclusion}


def _page(runs):
    """One page envelope of the actions/runs response."""
    return {'total_count': len(runs), 'workflow_runs': list(runs)}


def _patch_provider(monkeypatch, pages, *, pr_extras=None, capture=None):
    """Patch the provider surface beneath ``pull_request_runs_result``.

    ``pages`` is the decoded value ``gh api --paginate --slurp`` would emit — a
    LIST of page envelopes. It is serialized back to JSON here so the handler
    performs its own real decode and page assembly rather than being handed a
    pre-assembled run list.

    ``capture`` (a list) receives the constructed argv of every ``run_gh`` call, so
    a test can assert the pagination flags at the lowest primitive rather than
    inferring them from the outcome.
    """
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(github_ops, 'get_repo_info', lambda: ('cuioss', 'plan-marshall'))

    pr_payload = {
        'status': 'success',
        'operation': 'pr_view',
        'pr_number': 42,
        'head_branch': _HEAD_BRANCH,
    }
    pr_payload.update(pr_extras or {})
    monkeypatch.setattr(github_ops, 'view_pr_data', lambda selector=None: dict(pr_payload))

    def _run_gh(args, capture_json=False, timeout=60):
        if capture is not None:
            capture.append(list(args))
        return 0, json.dumps(pages), ''

    monkeypatch.setattr(github_ops, 'run_gh', _run_gh)


# ---------------------------------------------------------------------------
# The four-fixture matrix
# ---------------------------------------------------------------------------


def test_zero_runs_is_the_only_not_triggered_case(monkeypatch):
    """No runs at all — nothing was ever triggered by this PR."""
    _patch_provider(monkeypatch, [_page([])])

    result = github_ops.pull_request_runs_result(42)

    assert result['status'] == 'success'
    assert result['not_triggered'] is True
    assert result['has_pull_request_run'] is False
    assert result['pull_request_run_count'] == 0


def test_a_skipped_pull_request_run_is_not_not_triggered(monkeypatch):
    """The load-bearing negative control: ``skipped`` means ASKED, not un-asked.

    A ``pull_request`` run that exists and concluded ``skipped`` proves the PR
    triggered a workflow which then declined to do work. The bot WAS asked, so the
    remedy is not "trigger the review". Folding this into ``not_triggered`` would
    collapse two states whose remedies differ, and would do so silently — the
    conclusion is never consulted, which is exactly what makes it safe.
    """
    _patch_provider(monkeypatch, [_page([_run('pull_request', conclusion='skipped')])])

    result = github_ops.pull_request_runs_result(42)

    assert result['status'] == 'success'
    assert result['not_triggered'] is False
    assert result['has_pull_request_run'] is True
    assert result['pull_request_run_count'] == 1


def test_a_successful_pull_request_run_is_not_not_triggered(monkeypatch):
    """The ordinary positive: a concluded run exists, so something was triggered."""
    _patch_provider(monkeypatch, [_page([_run('pull_request', conclusion='success')])])

    result = github_ops.pull_request_runs_result(42)

    assert result['not_triggered'] is False
    assert result['has_pull_request_run'] is True


def test_a_run_on_the_second_page_is_still_found(monkeypatch):
    """The unslurped-pagination regression guard, asserted on the OUTCOME.

    Page one carries only ``push`` runs; the single ``pull_request`` run sits on
    page two. A handler that read one page — or that decoded only the first
    document of an unslurped concatenated stream — would report zero
    ``pull_request`` runs and misreport a busy PR as never having been reviewed.
    """
    pages = [
        _page([_run('push'), _run('push')]),
        _page([_run('pull_request')]),
    ]
    _patch_provider(monkeypatch, pages)

    result = github_ops.pull_request_runs_result(42)

    assert result['not_triggered'] is False
    assert result['has_pull_request_run'] is True
    # Every page's runs are assembled, not just the matching one.
    assert result['run_count'] == 3
    assert result['pull_request_run_count'] == 1


def test_the_pagination_flags_are_actually_passed(monkeypatch):
    """The MECHANISM behind the case above, asserted at the lowest primitive.

    The outcome assertion alone would pass against a single-page fetch that simply
    happened to receive both pages in one document. Asserting the constructed argv
    pins the two flags that make multi-page assembly correct: ``--paginate``
    requests every page and ``--slurp`` wraps them in one array instead of
    emitting a stream of concatenated documents.
    """
    capture: list[list[str]] = []
    _patch_provider(monkeypatch, [_page([_run('pull_request')])], capture=capture)

    github_ops.pull_request_runs_result(42)

    assert capture, 'the handler never reached the gh primitive'
    argv = capture[-1]
    assert '--paginate' in argv
    assert '--slurp' in argv
    # The endpoint targets the PR's own head branch, not the whole repo.
    assert any('actions/runs' in token for token in argv)
    assert any(_HEAD_BRANCH.replace('/', '%2F') in token or _HEAD_BRANCH in token for token in argv)


# ---------------------------------------------------------------------------
# mergeable_state is prohibited — asserted at source AND behaviour level
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    'func',
    [
        'pull_request_runs_result',
        'fetch_branch_workflow_runs',
        'cmd_checks_pull_request_runs',
    ],
)
def test_no_function_in_the_detection_path_mentions_mergeable_state(func):
    """Source-level prohibition, per function in the new detection path.

    ``mergeable_state`` is computed asynchronously by GitHub and reported as
    ``UNKNOWN`` while still computing, so a participation state keyed on it would
    depend on WHEN the question was asked rather than on what happened. The source
    assertion is what makes the prohibition durable: a behavioural test alone would
    keep passing if a future edit read the field and merely did not change the
    outcome on these fixtures.
    """
    source = _code_without_docstring(getattr(github_ops, func))

    assert 'mergeable_state' not in source
    assert 'mergeStateStatus' not in source


def test_a_poisoned_mergeable_state_does_not_move_the_verdict(monkeypatch):
    """Behavioural counterpart: the field is present and hostile, and ignored.

    ``view_pr_data`` really does return ``merge_state`` / ``mergeable``, so the
    field is genuinely reachable from this handler's inputs. Poisoning it and
    getting the fixture's normal answer proves the handler reads the run list.
    """
    _patch_provider(
        monkeypatch,
        [_page([_run('pull_request')])],
        pr_extras={'merge_state': 'dirty', 'mergeable': 'conflicting'},
    )

    result = github_ops.pull_request_runs_result(42)

    assert result['not_triggered'] is False
    # The envelope does not re-export the field either.
    assert 'merge_state' not in result
    assert 'mergeable' not in result


# ---------------------------------------------------------------------------
# Fail-loud and malformed-input guards
# ---------------------------------------------------------------------------


def test_unconfigured_provider_fails_loud_and_claims_nothing(monkeypatch):
    """An unauthenticated gh yields ``unconfigured``, never ``not_triggered: true``.

    This is the most dangerous false positive available to this verb: an
    unconfigured provider that reported "no pull_request run exists" would mark
    every PR as never having triggered a review, on evidence nobody gathered.
    """
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (False, 'Not authenticated'))

    result = github_ops.pull_request_runs_result(42)

    assert result['status'] == 'unconfigured'
    assert 'not_triggered' not in result
    assert 'has_pull_request_run' not in result


def test_an_unparseable_response_is_an_error_not_a_confident_answer(monkeypatch):
    """A response that could not be read must not resolve to ``not_triggered: true``.

    "The run list was never read" and "the run list is empty" are different facts.
    Reporting the observable from the former would assert the review was never
    triggered on the strength of a failed fetch.
    """
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(github_ops, 'get_repo_info', lambda: ('cuioss', 'plan-marshall'))
    monkeypatch.setattr(
        github_ops,
        'view_pr_data',
        lambda selector=None: {'status': 'success', 'head_branch': _HEAD_BRANCH},
    )
    monkeypatch.setattr(
        github_ops, 'run_gh', lambda args, capture_json=False, timeout=60: (0, 'not json at all', '')
    )

    result = github_ops.pull_request_runs_result(42)

    assert result['status'] == 'error'
    assert 'not_triggered' not in result


def test_a_failed_fetch_is_an_error_not_a_confident_answer(monkeypatch):
    """A non-zero gh exit is likewise an error, never a silent negative."""
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(github_ops, 'get_repo_info', lambda: ('cuioss', 'plan-marshall'))
    monkeypatch.setattr(
        github_ops,
        'view_pr_data',
        lambda selector=None: {'status': 'success', 'head_branch': _HEAD_BRANCH},
    )
    monkeypatch.setattr(
        github_ops, 'run_gh', lambda args, capture_json=False, timeout=60: (1, '', 'api rate limited')
    )

    result = github_ops.pull_request_runs_result(42)

    assert result['status'] == 'error'
    assert 'not_triggered' not in result


def test_malformed_list_elements_are_skipped_without_crashing(monkeypatch):
    """A malformed element is neither counted as evidence nor allowed to abort the scan.

    The input is a decoded API response, so per-element shape validation is what
    keeps one bad entry from discarding the well-formed entries beside it. Here the
    only well-formed ``pull_request`` run sits AFTER the malformed entries, so a
    predicate that raised — or that stopped at the first non-dict — would report
    the PR as never triggered.
    """
    pages = [
        {
            'total_count': 4,
            'workflow_runs': [
                'not-a-dict',
                42,
                {'event': None},
                {'no_event_key': True},
                _run('pull_request'),
            ],
        }
    ]
    _patch_provider(monkeypatch, pages)

    result = github_ops.pull_request_runs_result(42)

    assert result['status'] == 'success'
    assert result['not_triggered'] is False
    assert result['pull_request_run_count'] == 1


def test_malformed_elements_alone_do_not_fabricate_a_pull_request_run(monkeypatch):
    """The other direction: garbage is never READ as evidence a review ran.

    Paired with the case above so the shape validation is shown to reject as well
    as to tolerate — a validator that admitted any truthy element would turn this
    fixture into a false ``not_triggered: false``.
    """
    pages = [{'total_count': 3, 'workflow_runs': ['x', 7, {'event': ['pull_request']}]}]
    _patch_provider(monkeypatch, pages)

    result = github_ops.pull_request_runs_result(42)

    assert result['status'] == 'success'
    assert result['not_triggered'] is True
    assert result['pull_request_run_count'] == 0


# ---------------------------------------------------------------------------
# The pure predicate, driven directly
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ('label', 'runs', 'expected'),
    [
        ('empty-list', [], False),
        ('push-only', [{'event': 'push'}], False),
        ('pull-request', [{'event': 'pull_request'}], True),
        ('mixed', [{'event': 'push'}, {'event': 'pull_request'}], True),
        ('non-list', 'not-a-list', False),
        ('none', None, False),
    ],
    ids=['empty-list', 'push-only', 'pull-request', 'mixed', 'non-list', 'none'],
)
def test_has_pull_request_event_run_is_existence_only(label, runs, expected):
    """The predicate is pure existence over ``event``, and total over bad input.

    A non-list resolves ``False`` rather than raising, which is the fail-closed
    direction for the predicate itself — its CALLER is responsible for reporting a
    failed fetch as an error, which the handler cases above pin.
    """
    assert _github_checks._has_pull_request_event_run(runs) is expected


def test_the_predicate_never_consults_a_timestamp():
    """Existence only: no time comparison, so no dependence on clock skew.

    Asserted at the source level because the property is an ABSENCE — there is no
    input that demonstrates a comparison is not being made.
    """
    source = _code_without_docstring(_github_checks._has_pull_request_event_run)
    source += _code_without_docstring(_github_checks._is_pull_request_event_run)

    for forbidden in ('created_at', 'updated_at', 'run_started_at', 'datetime', 'timestamp'):
        assert forbidden not in source, f'the predicate must not reference {forbidden}'
