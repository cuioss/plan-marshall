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
def _run_for_pr(event, pr_numbers, conclusion='success'):
    """A workflow run carrying an explicit ``pull_requests`` association."""
    run = _run(event, conclusion=conclusion)
    run['pull_requests'] = [{'number': number} for number in pr_numbers]
    return run


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
def test_a_skipped_run_for_this_pr_still_counts_as_triggered(monkeypatch):
    """The `skipped` carve-out survives the PR-boundary filter.

    The exclusion is about ATTRIBUTION, not about outcome, so composing it with
    the event predicate must not quietly reintroduce a ``conclusion`` check.
    """
    _patch_provider(monkeypatch, [_page([_run_for_pr('pull_request', [42], conclusion='skipped')])])

    result = github_ops.pull_request_runs_result(42)

    assert result['not_triggered'] is False
    assert result['pull_request_run_count'] == 1
def test_an_unusable_requested_pr_number_does_not_exclude_anything():
    """A non-numeric PR identifier fails safe at the predicate itself.

    Driven directly because the handler resolves the identifier upstream; the
    predicate must still be total, and total in the keep direction.
    """
    run = _run_for_pr('pull_request', [99])

    assert _github_checks._run_names_a_different_pr(run, 'not-a-number') is False
    assert _github_checks._run_names_a_different_pr(run, None) is False
