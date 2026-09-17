"""Tests for the PR-wide ``not_triggered`` observable (github_ops pull-request-runs).

The observable answers one question: does ANY workflow run triggered by the
``pull_request`` event exist FOR THIS PR? A negative means nothing ever ran on
account of the PR, so no review bot could have published — a different condition
from a bot that was asked and stayed silent, and one whose remedy is the opposite
(trigger the review vs escalate a non-participating reviewer). The head branch is
how the runs are fetched, not what the answer is scoped to.

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
fail-loud path, the malformed-response guard that must not manufacture a confident
answer, the ENVELOPE-shape validation (every invalid page envelope resolves to the
``None`` discriminator rather than to an empty run list), and the PR-BOUNDARY
filter — asserted in both directions, since a filter that only ever excludes is as
wrong as one that never does.

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
import re

import _github_checks
import github_ops
import pytest

_HEAD_BRANCH = 'feature/some-work'
_DETECTION_MODULES = (github_ops, _github_checks)
def _module_level_functions():
    """Every function defined in either path module, keyed by name."""
    own = {m.__name__ for m in _DETECTION_MODULES}
    found = {}
    for module in _DETECTION_MODULES:
        for name, obj in vars(module).items():
            if inspect.isfunction(obj) and obj.__module__ in own:
                found.setdefault(name, obj)
    return found
def _calls_in(func):
    """The identifiers ``func`` calls, as a set."""
    return set(re.findall(r'\b([A-Za-z_][A-Za-z0-9_]*)\s*\(', inspect.getsource(func)))
def _detection_path_functions():
    """Derive the detection-path function set by walking the entry point's calls.

    Naming the set as a literal is what let the PR-boundary fix add two helpers to
    the path while the sweep below kept reporting full coverage over the three
    names it happened to know. The population is therefore derived: start at the
    handler, follow every call to a function defined in either path module, then
    keep only the functions PRIVATE to that path.

    The privacy filter is what makes the derivation usable rather than merely
    wide. A transitive walk also reaches shared provider primitives — a generic
    PR-data read, the ``gh`` wrapper — which many unrelated handlers call and
    which legitimately surface ``mergeable_state`` for their own callers. The
    prohibition governs code authored FOR this observable, so a reachable
    function stays in the population only when every module-level caller of it is
    itself on the path. A helper added to the path tomorrow is private to it and
    is swept; a shared primitive the path merely consumes is not.
    """
    module_funcs = _module_level_functions()

    reachable: set[str] = set()
    frontier = ['cmd_checks_pull_request_runs']
    while frontier:
        name = frontier.pop()
        if name in reachable or name not in module_funcs:
            continue
        reachable.add(name)
        frontier.extend(ident for ident in _calls_in(module_funcs[name]) if ident not in reachable)

    callers: dict[str, set[str]] = {name: set() for name in module_funcs}
    for caller, func in module_funcs.items():
        for callee in _calls_in(func):
            if callee in callers and callee != caller:
                callers[callee].add(caller)

    return tuple(sorted(name for name in reachable if callers[name] <= reachable))
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
_DETECTION_PATH_FUNCS = _detection_path_functions()
def _run_for_pr(event, pr_numbers, conclusion='success'):
    """A workflow run carrying an explicit ``pull_requests`` association."""
    run = _run(event, conclusion=conclusion)
    run['pull_requests'] = [{'number': number} for number in pr_numbers]
    return run


def test_the_detection_path_derivation_is_not_vacuous():
    """The derived population must be non-empty and reach past the entry point.

    A derivation that resolved to nothing — or to the entry point alone — would
    make the prohibition sweep below pass over an empty set while still reporting
    a healthy per-function result, which is the exact shape the derivation
    replaced.
    """
    assert 'cmd_checks_pull_request_runs' in _DETECTION_PATH_FUNCS
    assert len(_DETECTION_PATH_FUNCS) > 1, (
        f'the call-graph walk reached only {_DETECTION_PATH_FUNCS} — it never left the '
        f'entry point, so the sweep would be vacuous'
    )
    # The two helpers the PR-boundary fix introduced must be reachable, or the
    # walk is not actually following the path it claims to follow.
    for helper in ('_pull_request_event_runs_for_pr', '_run_names_a_different_pr'):
        assert helper in _DETECTION_PATH_FUNCS, f'{helper} is on the detection path but the derivation missed it'
def test_a_failed_fetch_is_an_error_not_a_confident_answer(monkeypatch):
    """A non-zero gh exit is likewise an error, never a silent negative."""
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(github_ops, 'get_repo_info', lambda: ('cuioss', 'plan-marshall'))
    monkeypatch.setattr(
        github_ops,
        'view_pr_data',
        lambda selector=None: {'status': 'success', 'head_branch': _HEAD_BRANCH},
    )
    monkeypatch.setattr(github_ops, 'run_gh', lambda args, capture_json=False, timeout=60: (1, '', 'api rate limited'))

    result = github_ops.pull_request_runs_result(42)

    assert result['status'] == 'error'
    assert 'not_triggered' not in result
def test_another_prs_run_on_the_same_branch_does_not_suppress_not_triggered(monkeypatch):
    """Two PRs, one branch: PR 42 never triggered, so the remedy must stay reachable.

    The only ``pull_request`` run on the branch belongs to PR 99. Answering from
    the branch alone would report ``not_triggered: false`` for PR 42 and silently
    withdraw the "trigger the review" remedy from a PR that was never asked.
    """
    _patch_provider(monkeypatch, [_page([_run_for_pr('pull_request', [99])])])

    result = github_ops.pull_request_runs_result(42)

    assert result['status'] == 'success'
    assert result['not_triggered'] is True
    assert result['has_pull_request_run'] is False
    assert result['pull_request_run_count'] == 0
    # The run was still READ — only its attribution excluded it.
    assert result['run_count'] == 1
@pytest.mark.parametrize(
    ('label', 'association'),
    [
        ('absent', None),
        ('empty-list', []),
        ('not-a-list', {'number': 99}),
        ('elements-not-dicts', ['99']),
        ('number-missing', [{'id': 7}]),
        ('number-not-an-int', [{'number': '99'}]),
    ],
    ids=[
        'absent',
        'empty-list',
        'not-a-list',
        'elements-not-dicts',
        'number-missing',
        'number-not-an-int',
    ],
)
def test_an_unreliable_association_never_fabricates_not_triggered(label, association, monkeypatch):
    """The safety direction: no usable association means KEEP the run.

    Each shape is one way GitHub's ``pull_requests`` array actually arrives
    unusable — most importantly ``empty-list``, which is routine for
    fork-originated runs. A strict filter would resolve every one of these to
    ``not_triggered: true``, asserting "the reviewers were never asked" on a PR
    that plainly triggered a run, and blocking its merge on that fiction. Keeping
    the run means the exclusion can only ever remove a false negative.
    """
    run = _run('pull_request')
    if association is not None:
        run['pull_requests'] = association
    _patch_provider(monkeypatch, [_page([run])])

    result = github_ops.pull_request_runs_result(42)

    assert result['status'] == 'success'
    assert result['not_triggered'] is False, f'{label} fabricated a not_triggered verdict'
    assert result['has_pull_request_run'] is True
def test_a_push_run_attributed_to_this_pr_is_still_not_a_pull_request_run(monkeypatch):
    """The event predicate is not weakened by the boundary filter.

    An association naming this PR does not make a ``push`` run evidence the PR
    triggered a review — the two conditions are conjoined, not alternative.
    """
    _patch_provider(monkeypatch, [_page([_run_for_pr('push', [42])])])

    result = github_ops.pull_request_runs_result(42)

    assert result['not_triggered'] is True
    assert result['pull_request_run_count'] == 0
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
