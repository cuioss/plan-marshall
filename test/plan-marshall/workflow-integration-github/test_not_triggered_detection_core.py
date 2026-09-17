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
_DETECTION_MODULES = (github_ops, _github_checks)
def _resolve_detection_func(name):
    """Return the function ``name`` refers to, searched across both path modules."""
    for module in _DETECTION_MODULES:
        candidate = getattr(module, name, None)
        if inspect.isfunction(candidate) and candidate.__module__ in {m.__name__ for m in _DETECTION_MODULES}:
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
def _run_for_pr(event, pr_numbers, conclusion='success'):
    """A workflow run carrying an explicit ``pull_requests`` association."""
    run = _run(event, conclusion=conclusion)
    run['pull_requests'] = [{'number': number} for number in pr_numbers]
    return run


def test_zero_runs_is_the_only_not_triggered_case(monkeypatch):
    """No runs at all — nothing was ever triggered by this PR."""
    _patch_provider(monkeypatch, [_page([])])

    result = github_ops.pull_request_runs_result(42)

    assert result['status'] == 'success'
    assert result['not_triggered'] is True
    assert result['has_pull_request_run'] is False
    assert result['pull_request_run_count'] == 0
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
    ('label', 'pr_number'),
    [('int', 42), ('numeric-string', '42')],
    ids=['int', 'numeric-string'],
)
def test_the_requested_pr_is_matched_across_its_argument_spellings(label, pr_number, monkeypatch):
    """The verb accepts ``int | str``, so the comparison must not be identity-typed.

    A string-vs-int mismatch would silently exclude the PR's OWN run and report
    ``not_triggered: true`` — the damaging polarity — on every string-spelled call.
    """
    _patch_provider(monkeypatch, [_page([_run_for_pr('pull_request', [42])])])

    result = github_ops.pull_request_runs_result(pr_number)

    assert result['not_triggered'] is False, f'{label} spelling excluded the PR own run'
def test_the_predicate_never_consults_a_timestamp():
    """Existence only: no time comparison, so no dependence on clock skew.

    Asserted at the source level because the property is an ABSENCE — there is no
    input that demonstrates a comparison is not being made.
    """
    source = _code_without_docstring(_github_checks._has_pull_request_event_run)
    source += _code_without_docstring(_github_checks._is_pull_request_event_run)

    for forbidden in ('created_at', 'updated_at', 'run_started_at', 'datetime', 'timestamp'):
        assert forbidden not in source, f'the predicate must not reference {forbidden}'
