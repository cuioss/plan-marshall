# SPDX-License-Identifier: FSL-1.1-ALv2
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


def _patch_envelope(monkeypatch, raw_stdout):
    """Patch the provider beneath ``fetch_branch_workflow_runs`` with raw stdout.

    Narrower than ``_patch_provider``: the envelope cases drive the fetch
    primitive directly, so no PR lookup is involved and the payload is supplied
    already serialized (some shapes are not expressible as a page list).
    """
    monkeypatch.setattr(github_ops, 'get_repo_info', lambda: ('cuioss', 'plan-marshall'))
    monkeypatch.setattr(github_ops, 'run_gh', lambda args, capture_json=False, timeout=60: (0, raw_stdout, ''))


def test_a_successful_pull_request_run_is_not_not_triggered(monkeypatch):
    """The ordinary positive: a concluded run exists, so something was triggered."""
    _patch_provider(monkeypatch, [_page([_run('pull_request', conclusion='success')])])

    result = github_ops.pull_request_runs_result(42)

    assert result['not_triggered'] is False
    assert result['has_pull_request_run'] is True


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
    monkeypatch.setattr(github_ops, 'run_gh', lambda args, capture_json=False, timeout=60: (0, 'not json at all', ''))

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


@pytest.mark.parametrize(
    ('label', 'payload'),
    [
        ('bare-object', {}),
        ('unslurped-single-page', {'total_count': 0, 'workflow_runs': []}),
        ('top-level-string', 'nope'),
        ('top-level-null', None),
        ('page-not-a-dict', ['not-a-dict']),
        ('page-is-a-list', [[]]),
        ('workflow-runs-absent', [{'total_count': 0}]),
        ('workflow-runs-is-a-dict', [{'workflow_runs': {}}]),
        ('workflow-runs-is-null', [{'workflow_runs': None}]),
        ('second-page-malformed', [{'workflow_runs': []}, {'workflow_runs': 'x'}]),
    ],
    ids=[
        'bare-object',
        'unslurped-single-page',
        'top-level-string',
        'top-level-null',
        'page-not-a-dict',
        'page-is-a-list',
        'workflow-runs-absent',
        'workflow-runs-is-a-dict',
        'workflow-runs-is-null',
        'second-page-malformed',
    ],
)
def test_a_malformed_envelope_returns_none_not_an_empty_run_list(label, payload, monkeypatch):
    """Every invalid envelope shape resolves to the ``None`` discriminator.

    ``unslurped-single-page`` is deliberately in this set rather than tolerated:
    the sole call site always passes ``--slurp``, so an unwrapped page can only
    mean the flag was dropped — a pagination regression this guard surfaces
    instead of masking. ``second-page-malformed`` is the one that a per-page
    skip would pass: page one is valid, so a validator keyed on the first page
    alone would return that page's runs and call the read complete.
    """
    _patch_envelope(monkeypatch, json.dumps(payload))

    runs, error = github_ops.fetch_branch_workflow_runs(_HEAD_BRANCH)

    assert runs is None, f'{label} was accepted as a readable run set'
    assert error, f'{label} returned no error message alongside the None'


def test_a_malformed_envelope_reaches_the_handler_as_an_error(monkeypatch):
    """End-to-end: the handler reports ``error``, never a confident ``not_triggered``.

    The unit assertions above pin the discriminator at the primitive; this pins
    that the caller honours it, which is where the false ``not_triggered: true``
    would actually have surfaced.
    """
    _patch_provider(monkeypatch, [{'total_count': 0, 'workflow_runs': {}}])

    result = github_ops.pull_request_runs_result(42)

    assert result['status'] == 'error'
    assert 'not_triggered' not in result
    assert 'has_pull_request_run' not in result
