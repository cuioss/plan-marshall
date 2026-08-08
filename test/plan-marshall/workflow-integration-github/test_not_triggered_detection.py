#!/usr/bin/env python3
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


#: The two modules the detection path is spread across. The entry point lives in
#: ``github_ops``; the PR-boundary predicate and its helper live in
#: ``_github_checks``, so a walk confined to one module would miss half the path.
_DETECTION_MODULES = (github_ops, _github_checks)


def _resolve_detection_func(name):
    """Return the function ``name`` refers to, searched across both path modules."""
    for module in _DETECTION_MODULES:
        candidate = getattr(module, name, None)
        if inspect.isfunction(candidate) and candidate.__module__ in {
            m.__name__ for m in _DETECTION_MODULES
        }:
            return candidate
    return None


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

    return tuple(
        sorted(name for name in reachable if callers[name] <= reachable)
    )


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


#: The functions the prohibition sweeps. DERIVED from the entry point's call
#: graph rather than named, so a helper added to the detection path inherits the
#: sweep instead of silently escaping it — the failure mode that let
#: ``_run_names_a_different_pr`` and ``_pull_request_event_runs_for_pr`` join the
#: path while a three-name literal kept reporting full coverage.
_DETECTION_PATH_FUNCS = _detection_path_functions()


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
        assert helper in _DETECTION_PATH_FUNCS, (
            f'{helper} is on the detection path but the derivation missed it'
        )


@pytest.mark.parametrize('func', _DETECTION_PATH_FUNCS)
def test_no_function_in_the_detection_path_mentions_mergeable_state(func):
    """Source-level prohibition, per function in the new detection path.

    ``mergeable_state`` is computed asynchronously by GitHub and reported as
    ``UNKNOWN`` while still computing, so a participation state keyed on it would
    depend on WHEN the question was asked rather than on what happened. The source
    assertion is what makes the prohibition durable: a behavioural test alone would
    keep passing if a future edit read the field and merely did not change the
    outcome on these fixtures.
    """
    source = _code_without_docstring(_resolve_detection_func(func))

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
# Envelope-shape validation — a malformed envelope is None, never an empty list
# ---------------------------------------------------------------------------
#
# The two guards above validate the ELEMENTS inside a well-formed page. These
# validate the ENVELOPE that carries them, which is a different failure: a page
# whose ``workflow_runs`` is absent or non-list yields no runs at all, and
# skipping it would report ``not_triggered: true`` — "no review was ever
# triggered" — on a run collection that was never validly read. That is the
# collapse ``fetch_branch_workflow_runs``'s ``None`` discriminator exists to
# prevent, so every malformed envelope must reach the caller through it.


def _patch_envelope(monkeypatch, raw_stdout):
    """Patch the provider beneath ``fetch_branch_workflow_runs`` with raw stdout.

    Narrower than ``_patch_provider``: the envelope cases drive the fetch
    primitive directly, so no PR lookup is involved and the payload is supplied
    already serialized (some shapes are not expressible as a page list).
    """
    monkeypatch.setattr(github_ops, 'get_repo_info', lambda: ('cuioss', 'plan-marshall'))
    monkeypatch.setattr(
        github_ops, 'run_gh', lambda args, capture_json=False, timeout=60: (0, raw_stdout, '')
    )


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


def test_a_well_formed_slurped_envelope_still_reads_every_page(monkeypatch):
    """The positive control: valid shapes are not caught by the validation above.

    Without this, the parametrized rejections would be equally satisfied by a
    function that returned ``None`` unconditionally.
    """
    _patch_envelope(monkeypatch, json.dumps([_page([_run('push')]), _page([_run('pull_request')])]))

    runs, error = github_ops.fetch_branch_workflow_runs(_HEAD_BRANCH)

    assert error == ''
    assert runs is not None
    assert len(runs) == 2


def test_a_well_formed_empty_envelope_is_a_real_empty_read(monkeypatch):
    """An empty ``workflow_runs`` on a valid page is data, not a malformed shape.

    The two are the states this whole file separates: "read, and empty" is the
    only legitimate ``not_triggered: true``, while "never validly read" is the
    ``None`` above. A validator that rejected both would break the observable.
    """
    _patch_envelope(monkeypatch, json.dumps([_page([])]))

    runs, error = github_ops.fetch_branch_workflow_runs(_HEAD_BRANCH)

    assert error == ''
    assert runs == []


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


# ---------------------------------------------------------------------------
# The PR boundary — the branch is how runs are FETCHED, not what they answer for
# ---------------------------------------------------------------------------
#
# The run list is fetched branch-scoped, but a branch is not a PR boundary: a
# branch a closed PR already used, or two open PRs sharing one head branch, carry
# ``pull_request`` runs belonging to another PR that would otherwise suppress
# ``not_triggered`` for a PR that never triggered anything. The exclusion is ASYMMETRIC —
# GitHub's ``pull_requests`` array is unreliable (routinely empty on fork runs),
# so it may only ever remove a false negative and must never manufacture a
# ``not_triggered: true``. Both directions are pinned below, because a filter
# tested in one direction only is the exact shape that would pass while being
# unsafe.


def _run_for_pr(event, pr_numbers, conclusion='success'):
    """A workflow run carrying an explicit ``pull_requests`` association."""
    run = _run(event, conclusion=conclusion)
    run['pull_requests'] = [{'number': number} for number in pr_numbers]
    return run


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


def test_this_prs_own_run_is_kept_when_the_branch_also_carries_another_prs(monkeypatch):
    """The complement: the exclusion removes only the foreign run, not every run.

    Without this, the case above would be equally satisfied by a filter that
    discarded every associated run.
    """
    pages = [
        _page(
            [
                _run_for_pr('pull_request', [99]),
                _run_for_pr('pull_request', [42]),
            ]
        )
    ]
    _patch_provider(monkeypatch, pages)

    result = github_ops.pull_request_runs_result(42)

    assert result['not_triggered'] is False
    assert result['has_pull_request_run'] is True
    assert result['pull_request_run_count'] == 1


def test_a_run_listing_several_prs_including_this_one_is_kept(monkeypatch):
    """A run may be associated with more than one PR — membership, not equality."""
    _patch_provider(monkeypatch, [_page([_run_for_pr('pull_request', [99, 42])])])

    result = github_ops.pull_request_runs_result(42)

    assert result['not_triggered'] is False
    assert result['pull_request_run_count'] == 1


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
def test_an_unreliable_association_never_fabricates_not_triggered(
    label, association, monkeypatch
):
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


def test_a_skipped_run_for_this_pr_still_counts_as_triggered(monkeypatch):
    """The `skipped` carve-out survives the PR-boundary filter.

    The exclusion is about ATTRIBUTION, not about outcome, so composing it with
    the event predicate must not quietly reintroduce a ``conclusion`` check.
    """
    _patch_provider(
        monkeypatch, [_page([_run_for_pr('pull_request', [42], conclusion='skipped')])]
    )

    result = github_ops.pull_request_runs_result(42)

    assert result['not_triggered'] is False
    assert result['pull_request_run_count'] == 1


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
    ('label', 'pr_number'),
    [('int', 42), ('numeric-string', '42')],
    ids=['int', 'numeric-string'],
)
def test_the_requested_pr_is_matched_across_its_argument_spellings(
    label, pr_number, monkeypatch
):
    """The verb accepts ``int | str``, so the comparison must not be identity-typed.

    A string-vs-int mismatch would silently exclude the PR's OWN run and report
    ``not_triggered: true`` — the damaging polarity — on every string-spelled call.
    """
    _patch_provider(monkeypatch, [_page([_run_for_pr('pull_request', [42])])])

    result = github_ops.pull_request_runs_result(pr_number)

    assert result['not_triggered'] is False, f'{label} spelling excluded the PR own run'


def test_an_unusable_requested_pr_number_does_not_exclude_anything():
    """A non-numeric PR identifier fails safe at the predicate itself.

    Driven directly because the handler resolves the identifier upstream; the
    predicate must still be total, and total in the keep direction.
    """
    run = _run_for_pr('pull_request', [99])

    assert _github_checks._run_names_a_different_pr(run, 'not-a-number') is False
    assert _github_checks._run_names_a_different_pr(run, None) is False


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
