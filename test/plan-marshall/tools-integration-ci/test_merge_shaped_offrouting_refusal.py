#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Population-complete BEHAVIOURAL guard for the merge-shaped off-routing refusal.

This is the deliverable of plan
``060-a-prose-routing-table-is-not-an-enforcement-boundary``. It generalises the
shipped one-site fix — the base-branch/project queue preflight every merge-shaped
verb now carries — into a guard bound to the DERIVED population rather than to a
hand-listed set of verbs.

**Why a new test when per-verb behavioural tests already exist.** The provider
suites already prove each merge-shaped verb's refusal one hand-written test
function at a time (``test_pr_merge_refuses_when_base_merge_queue_required`` and
its siblings). A hand-list is a *sample*: it says nothing about a NEW merge-shaped
verb added to a registry without a guard, which is exactly the shape that
under-counted this population twice. This module instead DERIVES the population
from both providers' ``handlers: HandlerMap`` registry literals (via the shared
:mod:`_merge_shaped_roster`, the single-source pattern :mod:`_dispatch_roster`
established) and asserts the off-routing behaviour of EVERY derived member. A
merge-shaped verb added to a registry without an off-routing scenario fails
``test_every_derived_member_has_an_offrouting_scenario``; one added without a
working guard fails the behavioural parametrization.

**The population is 8** — ``{merge, auto-merge, safe-merge, merge-queue}`` × two
providers. The size is asserted (and published in the failure message) so a run
that derived an empty or half-read population is self-evident from its own output
rather than reporting a vacuous green — the empty-population trap this epic has
been bitten by repeatedly.

**The off-routing scenarios, and the ONE sanctioned exception.** The documented
route (``branch-cleanup.md`` § "Merge routing (``use_merge_queue``)") dispatches
only ``safe-merge`` / ``merge-queue`` and declares ``merge`` / ``auto-merge``
unreachable from it. The callee-side handling of an off-routing dispatch is:

* ``merge`` / ``safe-merge`` — an IMMEDIATE merge against a base that REQUIRES a
  platform queue/train is the close-unmerged signature; the callee REFUSES
  (``status: error``).
* ``merge-queue`` — an enqueue against a base with NO queue/train configured
  would silently degrade to plain auto-merge; the callee REFUSES.
* ``auto-merge`` — the **sanctioned exception**. ``gh pr merge --auto`` /
  ``glab mr merge --when-pipeline-succeeds`` self-routes: on a queued base it
  ENQUEUES (the safe outcome), on an unqueued base it enables plain auto-merge.
  It is therefore never in the close-unmerged unsafe state, and a blanket refusal
  would break the legitimate enqueue-via-auto-merge path. The callee-side handling
  that prevents the incident here is PROBE-AND-REPORT: it reports the
  ``disposition`` it actually produced and NEVER a bare/false ``merged: true``.
  This module asserts that sanctioned handling (success + ``disposition:
  enqueued`` + no ``merged`` key), not a refusal.

**Falsifiability, measured by mutation.** The behavioural arms are proven to fail
against a mutant — deleting a handler's guard call (e.g. dropping the
``_refuse_on_required_merge_queue`` preflight from ``cmd_pr_merge``) makes that
member's off-routing dispatch merge blind, so the refusal assertion goes red for
it while the live tree stays green. The plan's run report records the mutation
run. The population arm's falsifiability is structural: shrink the derived
population and the size assertion fails; add an unclassified verb and the scenario
arm fails.
"""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path

import pytest

from conftest import MARKETPLACE_ROOT
from _merge_shaped_roster import MERGE_SHAPED_VERBS, merge_shaped_members

# ---------------------------------------------------------------------------
# Derived population — the single source of truth for what this suite covers
# ---------------------------------------------------------------------------

_SKILLS: Path = Path(MARKETPLACE_ROOT) / 'plan-marshall' / 'skills'
_PROVIDER_PATHS: dict[str, Path] = {
    'github': _SKILLS / 'workflow-integration-github' / 'scripts' / 'github_ops.py',
    'gitlab': _SKILLS / 'workflow-integration-gitlab' / 'scripts' / 'gitlab_ops.py',
}
_PROVIDER_TEXTS: dict[str, str] = {
    provider: path.read_text(encoding='utf-8') for provider, path in _PROVIDER_PATHS.items()
}

#: ``(provider, verb, handler_name)`` for every merge-shaped registry member.
_MEMBERS: list[tuple[str, str, str]] = merge_shaped_members(_PROVIDER_TEXTS)

#: The provider handler modules, imported for dispatch. Both live on the
#: conftest-configured marketplace ``sys.path`` and carry distinct module names,
#: so importing both in one process is collision-free.
_PROVIDER_MODULES = {
    'github': importlib.import_module('github_ops'),
    'gitlab': importlib.import_module('gitlab_ops'),
}

# ---------------------------------------------------------------------------
# Off-routing scenario classification (keyed by verb; both providers share it)
# ---------------------------------------------------------------------------

#: An immediate-merge verb refuses when the base REQUIRES a platform queue/train.
_REFUSE_IMMEDIATE = 'refuse_immediate'
#: The enqueue verb refuses when the base has NO queue/train configured.
_REFUSE_UNCONFIGURED = 'refuse_unconfigured'
#: The sanctioned exception: auto-merge self-routes and reports its disposition.
_REPORT_DISPOSITION = 'report_disposition'

_SCENARIOS: dict[str, str] = {
    'merge': _REFUSE_IMMEDIATE,
    'safe-merge': _REFUSE_IMMEDIATE,
    'merge-queue': _REFUSE_UNCONFIGURED,
    'auto-merge': _REPORT_DISPOSITION,
}

_IDS = [f'{provider}:{verb}' for provider, verb, _handler in _MEMBERS]


def _ok_auth() -> tuple[bool, str]:
    """Stub ``check_auth`` — always authenticated, so no verb short-circuits on auth."""
    return True, ''


# Minimal provider ``view_pr_data`` payloads. ``base_branch`` feeds the GitHub
# base-branch preflight; ``merge_state`` feeds the safe-merge readiness poll
# (``clean`` / ``can_be_merged`` are ready on the first poll, so no sleep runs).
# The GitLab payload carries ``state: merged`` because the same view feeds the
# GitLab post-merge corroboration re-read.
_GH_VIEW_PAYLOAD = {
    'status': 'success', 'operation': 'pr_view', 'pr_number': 42,
    'pr_url': 'https://github.com/octo/repo/pull/42', 'state': 'open', 'title': 'T',
    'head_branch': 'feature/x', 'base_branch': 'main', 'is_draft': 'false',
    'mergeable': 'mergeable', 'merge_state': 'clean',
}
_GL_VIEW_PAYLOAD = {
    'status': 'success', 'operation': 'pr_view', 'pr_number': 42,
    'pr_url': 'https://gitlab.com/octo/repo/-/merge_requests/42', 'state': 'merged', 'title': 'T',
    'head_branch': 'feature/x', 'base_branch': 'main', 'is_draft': 'false',
    'mergeable': 'mergeable', 'merge_state': 'can_be_merged',
}
# The post-merge re-read GitHub corroborates a landed merge from.
_GH_MERGED_PAYLOAD = {
    'state': 'MERGED', 'mergedAt': '2026-01-01T00:00:00Z',
    'baseRefName': 'main', 'headRefOid': 'abc123',
}


def _gh_run_stub(captured: list[list[str]]):
    """A ``run_gh`` stub: merge/auto-merge accepted, post-merge re-read = MERGED."""
    def stub(args, capture_json=False, timeout=60):
        captured.append(list(args))
        if args[:2] == ['pr', 'view']:
            return 0, json.dumps(_GH_MERGED_PAYLOAD), ''
        return 0, '', ''

    return stub


def _gl_run_stub(captured: list[list[str]], *, mt_post_ok: bool):
    """A ``run_glab`` stub: ``mr merge`` accepted; the merge-train POST gated by ``mt_post_ok``.

    ``mt_post_ok`` is what makes the GitLab ``merge-queue`` off-routing case a
    genuine refusal: GitLab's ``cmd_pr_merge_queue`` does not probe first, it POSTs
    to the merge-train endpoint and reads an HTTP 404 as the ineligible refusal.
    """
    def stub(args, capture_json=False, timeout=60):
        captured.append(list(args))
        if args[:3] == ['api', '-X', 'POST']:
            return (0, '{"id": 7}', '') if mt_post_ok else (1, '', 'HTTP 404: not found')
        return 0, '', ''

    return stub


def _discriminator_for(mod, verb: str, mode: str) -> str:
    """The queue/train state the base is in for this member under this mode.

    Off-routing means the base is in the state the verb must NOT be dispatched
    against; compliant means the state it may. The one exception where the
    discriminator does not decide the outcome is GitLab ``merge-queue`` (its
    handler POSTs rather than reading the probe) — the run stub's ``mt_post_ok``
    carries that case.
    """
    configured = str(mod.MERGE_QUEUE_ELIGIBLE_CONFIGURED)
    unconfigured = str(mod.MERGE_QUEUE_ELIGIBLE_UNCONFIGURED)
    if verb == 'merge-queue':
        # off-routing = NO queue configured; compliant = queue configured.
        return unconfigured if mode == 'off_routing' else configured
    # merge / safe-merge / auto-merge: off-routing = base REQUIRES the queue.
    return configured if mode == 'off_routing' else unconfigured


def _namespace_for(verb: str) -> argparse.Namespace:
    """The argparse.Namespace each merge-shaped handler reads, by verb."""
    if verb == 'safe-merge':
        return argparse.Namespace(
            pr_number=42, head=None, strategy='merge', delete_branch=False,
            poll_timeout=30, poll_interval=1, admin_merge_on_stuck_state=False,
        )
    if verb == 'merge-queue':
        return argparse.Namespace(pr_number=42, head=None)
    if verb == 'auto-merge':
        return argparse.Namespace(pr_number=42, head=None, strategy='merge')
    return argparse.Namespace(pr_number=42, head=None, strategy='merge', delete_branch=False)


def _dispatch(monkeypatch, provider: str, verb: str, handler: str, mode: str) -> tuple[dict, list]:
    """Install provider-appropriate stubs for ``mode`` and dispatch ``handler``.

    Returns ``(result_dict, captured_cli_calls)``. Every external seam the handler
    reaches (auth, repo/project resolution, PR view, the queue/train probe, and
    the ``gh``/``glab`` runner) is stubbed, so the dispatch is pure and exercises
    only the handler's own routing/guard logic.
    """
    mod = _PROVIDER_MODULES[provider]
    captured: list[list[str]] = []
    discriminator = _discriminator_for(mod, verb, mode)

    monkeypatch.setattr(mod, 'check_auth', _ok_auth)
    if provider == 'github':
        monkeypatch.setattr(mod, 'get_repo_info', lambda: ('octo', 'repo'))
        monkeypatch.setattr(mod, 'view_pr_data', lambda head=None: dict(_GH_VIEW_PAYLOAD))
        monkeypatch.setattr(
            mod, '_probe_merge_queue_state',
            lambda owner, repo, branch: (discriminator, 'probe detail', None, None),
        )
        monkeypatch.setattr(mod, 'run_gh', _gh_run_stub(captured))
    else:
        monkeypatch.setattr(mod, 'get_project_path', lambda: 'octo/repo')
        monkeypatch.setattr(mod, 'view_pr_data', lambda head=None: dict(_GL_VIEW_PAYLOAD))
        monkeypatch.setattr(
            mod, '_probe_merge_train_state',
            lambda: (discriminator, 'probe detail', None),
        )
        mt_post_ok = not (verb == 'merge-queue' and mode == 'off_routing')
        monkeypatch.setattr(mod, 'run_glab', _gl_run_stub(captured, mt_post_ok=mt_post_ok))

    result = getattr(mod, handler)(_namespace_for(verb))
    return result, captured


# ---------------------------------------------------------------------------
# Population derivation — asserted FIRST, non-emptiness before anything else
# ---------------------------------------------------------------------------


def test_merge_shaped_population_is_derived_nonempty_and_sized():
    """The derived population is non-empty, exactly 8, and 4-per-provider.

    Asserted first and on its own: every behavioural parametrization below iterates
    ``_MEMBERS``, so a derivation that silently collapsed to an empty set would make
    those checks pass vacuously. The size is published in every failure message so
    an under-read population is self-evident from the test output — the trap this
    epic has repeatedly hit (a hand-list of two routed verbs understated the real
    population fourfold).
    """
    assert _MEMBERS, (
        'The derived merge-shaped population is EMPTY. The registry HandlerMap literal '
        'stopped matching, so every behavioural assertion below would pass vacuously.'
    )
    size = len(_MEMBERS)
    assert size == 8, (
        f'Derived merge-shaped population size = {size}, expected 8 (4 verbs x 2 providers). '
        f'Members: {_MEMBERS}. A smaller set means a verb is registered under a name this '
        'derivation does not see — exactly how cmd_pr_auto_merge was missed twice.'
    )
    verbs_by_provider: dict[str, set[str]] = {}
    for provider, verb, _handler in _MEMBERS:
        verbs_by_provider.setdefault(provider, set()).add(verb)
    for provider in ('github', 'gitlab'):
        assert verbs_by_provider.get(provider) == set(MERGE_SHAPED_VERBS), (
            f'{provider} merge-shaped verbs = {sorted(verbs_by_provider.get(provider) or set())}, '
            f'expected {sorted(MERGE_SHAPED_VERBS)}. A missing verb is an under-enumeration; an '
            'extra one is a vocabulary drift.'
        )


def test_every_derived_member_has_an_offrouting_scenario():
    """Every derived member is classified, so a new merge-shaped verb cannot slip through.

    The behavioural arms below look each member's verb up in ``_SCENARIOS``. A verb
    added to a provider registry but not to that map would raise ``KeyError`` in the
    parametrized arms; this test names it directly instead, with the population size
    for context, so the failure points at the missing classification rather than at
    a distant KeyError.
    """
    unclassified = [(p, v, h) for (p, v, h) in _MEMBERS if v not in _SCENARIOS]
    assert not unclassified, (
        f'{len(_MEMBERS)} derived merge-shaped members; these have NO off-routing scenario: '
        f'{unclassified}. A newly registered merge-shaped verb must gain both a callee-side '
        'guard and an off-routing scenario here, or this population-complete check silently '
        'skips it.'
    )


# ---------------------------------------------------------------------------
# Behavioural arm (a): an off-routing dispatch is refused at the callee
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('provider,verb,handler', _MEMBERS, ids=_IDS)
def test_offrouting_dispatch_is_refused_at_the_callee(monkeypatch, provider, verb, handler):
    """Every derived member refuses (or safely self-routes) an off-routing dispatch.

    For the immediate-merge and enqueue verbs the callee returns ``status: error``
    on the unsafe base state, so the incident (a merge-shaped verb reporting a false
    ``merged: true`` off-routing) cannot recur through them. For ``auto-merge`` — the
    sanctioned exception — the callee self-routes to the ENQUEUE and reports that
    disposition, and critically NEVER emits ``merged``, so it too cannot report a
    false merge.
    """
    result, _captured = _dispatch(monkeypatch, provider, verb, handler, 'off_routing')
    scenario = _SCENARIOS[verb]

    if scenario == _REPORT_DISPOSITION:
        assert result.get('status') == 'success', result
        assert result.get('disposition') == 'enqueued', (
            f'{provider}:{verb} did not self-route to the queue on an off-routing dispatch. '
            f'The sanctioned handling is enqueue-and-report, not a silent enable. Result: {result}'
        )
        assert 'merged' not in result, (
            f'{provider}:{verb} reported a merge verdict on a scheduling verb. auto-merge '
            f'schedules; it must never claim merged. Result: {result}'
        )
    else:
        assert result.get('status') == 'error', (
            f'{provider}:{verb} did NOT refuse an off-routing dispatch at the callee. This is the '
            f'incident shape: a merge-shaped verb reached off-routing without a guard. Result: {result}'
        )


# ---------------------------------------------------------------------------
# Behavioural arm (b): the compliant route still succeeds unchanged
# ---------------------------------------------------------------------------


@pytest.mark.parametrize('provider,verb,handler', _MEMBERS, ids=_IDS)
def test_compliant_route_succeeds(monkeypatch, provider, verb, handler):
    """The compliant dispatch of every member still succeeds — the guard is not a wall.

    A refusal that also blocked the compliant route would trade the defect for an
    outage. Each member is dispatched against the base state its verb is FOR:
    immediate-merge against an unqueued base (merges, ``merged: true``), enqueue
    against a queued base (``enqueued: true``), and auto-merge against an unqueued
    base (``disposition: enabled``).
    """
    result, _captured = _dispatch(monkeypatch, provider, verb, handler, 'compliant')
    assert result.get('status') == 'success', (
        f'{provider}:{verb} compliant route did not succeed — the guard blocks a sanctioned '
        f'dispatch. Result: {result}'
    )
    scenario = _SCENARIOS[verb]
    if scenario == _REFUSE_IMMEDIATE:
        assert result.get('merged') is True, result
    elif scenario == _REFUSE_UNCONFIGURED:
        assert result.get('enqueued') is True, result
    else:
        assert result.get('disposition') == 'enabled', result
