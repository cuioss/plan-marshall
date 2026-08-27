#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Matched precedence controls for the footprint resolver's PR-landing tier.

The PR-landing tier reads a landing SHA from the CI provider, so it is the one
tier in the chain that can produce an answer out of a network round-trip. Its
contract is DIRECTIONAL: it sits strictly below every tier that outranks it, so
it may only ever convert an unresolvable result into a resolved one. It must
never change an answer a higher-precedence tier already gave.

Each control here is a matched pair over that direction, not a restatement of the
positive case:

* the must-NOT-fire half establishes one higher-precedence tier — including a
  GENUINE two-parent merge commit, whose parentage is asserted rather than
  assumed — while a provider stub stands ready with a DIFFERENT path set, and
  requires both that the chain return the higher tier's answer and that the
  provider is never consulted at all;
* the must-FIRE half removes only that higher-precedence key, keeping the same
  repository and the same stub, and requires the tier to fire.

The halves share every input except the key under test, so the negative half
cannot pass for the wrong reason. A stub that stopped answering sends the fire
half red; a stub whose answer happened to coincide with a higher tier's is
rejected outright by the distinguishability assertion, which derives its verdict
from the fixtures themselves rather than trusting them.

Each control also publishes the population it exercised — how many
higher-precedence tiers were established, and how many were compared — so a
control that silently stopped examining its input fails instead of reading green
on an empty sweep.

The git and provider helpers are deliberately local rather than shared with the
resolver's main test module. A control that builds its fixtures with the helpers
of the suite it controls fails in lock-step with that suite, which is exactly
when a control is supposed to still be standing.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from conftest import load_script_module

# ``register=False``: this module only needs the returned object, and publishing a
# second ``_footprint_resolver`` entry would displace the one the resolver's main
# test module registered.
_fr = load_script_module(
    'plan-marshall', 'plan-retrospective', '_footprint_resolver.py', register=False
)

#: The tier these controls are about.
_PR_LANDING = 'pr_landing'

#: The PR number every fixture records and every stub answers about.
_PR_NUMBER = 456

#: Tiers that OUTRANK the PR-landing tier, derived from the resolver's own
#: declared precedence order rather than restated. A tier inserted above it grows
#: this tuple, and the coverage assertion below then fails until a control exists
#: for it — the population guards itself.
_TIERS_ABOVE_PR_LANDING: tuple[str, ...] = _fr.RESOLVING_TIERS[
    : _fr.RESOLVING_TIERS.index(_PR_LANDING)
]

#: The path set the provider stub attributes to the PR's landing. Held disjoint
#: from every higher-tier answer so a tier that wrongly fired is VISIBLE in the
#: result rather than hidden behind a coincidence.
_PR_ONLY_PATHS = {'pr_only.py'}

#: What each higher-precedence tier answers in its own control. Keyed by the
#: tier's declared name so the coverage assertion can compare rosters.
_ABOVE_TIER_ANSWERS: dict[str, set[str]] = {
    'live_diff': {'live_only.py'},
    'realized_capture': {'captured_only.py'},
    'merge_commit': {'feature_only.py'},
}


# =============================================================================
# Git fixture helpers (local by design — see the module docstring)
# =============================================================================


def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ['git', '-C', str(repo), '-c', 'commit.gpgsign=false', *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, 'init', '--initial-branch=main')
    _git(repo, 'config', 'user.email', 'test@example.com')
    _git(repo, 'config', 'user.name', 'Test User')


def _commit(repo: Path, message: str, files: dict[str, str]) -> str:
    for rel, content in files.items():
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    _git(repo, 'add', '-A')
    _git(repo, 'commit', '-m', message)
    return _git(repo, 'rev-parse', 'HEAD').strip()


def _write_refs(plan_dir: Path, refs: dict) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'references.json').write_text(json.dumps(refs, indent=2))


def _parent_count(repo: Path, sha: str) -> int:
    """How many parents ``sha`` has, read from git rather than assumed."""
    return len(_git(repo, 'rev-list', '--parents', '-n', '1', sha).split()) - 1


class _Landings(dict):
    """The repository plus the two landing SHAs its controls resolve against."""


def _repo_with_a_genuine_merge_and_a_separate_pr_landing(tmp_path: Path) -> _Landings:
    """Build a repo whose merge landing is a REAL two-parent merge commit.

    A linear commit would satisfy the same first-parent range while quietly
    turning the merge-commit control into a squash control, so the shape the
    control claims to exercise is built here and asserted by its own test.

    The PR landing is a SEPARATE commit touching a disjoint path, so a
    PR-landing tier that wrongly overrode the merge tier changes the observed
    answer instead of coinciding with it.
    """
    repo = tmp_path / 'repo'
    _init_repo(repo)
    _commit(repo, 'base', {'base.txt': 'base\n'})
    _git(repo, 'checkout', '-b', 'feature')
    _commit(repo, 'feature change', {'feature_only.py': 'x\n'})
    _git(repo, 'checkout', 'main')
    _commit(repo, 'sibling on main', {'sibling.py': 's\n'})
    _git(repo, 'merge', '--no-ff', 'feature', '-m', 'merge feature')
    merge_sha = _git(repo, 'rev-parse', 'HEAD').strip()
    pr_sha = _commit(repo, 'pr landing', {'pr_only.py': 'p\n'})
    return _Landings(repo=repo, merge_sha=merge_sha, pr_sha=pr_sha)


# =============================================================================
# Provider stub — ONLY the CI abstraction call is intercepted
# =============================================================================

#: Captured before any patching, so the dispatcher can delegate every non-CI call
#: (notably the real ``git diff`` the tiers run, and this module's own fixtures)
#: to the genuine implementation.
_REAL_SUBPROCESS_RUN = subprocess.run


def _stub_ci(monkeypatch, stdout: str, returncode: int = 0) -> list[list[str]]:
    """Answer the executor's ``ci pr view`` call; return the intercepted argv list.

    The returned list is what makes "the provider was never consulted" a
    structural assertion rather than an inference from the result.
    """
    calls: list[list[str]] = []

    def dispatching_run(cmd, **kwargs):
        if isinstance(cmd, (list, tuple)) and _fr._CI_NOTATION in cmd:
            calls.append(list(cmd))
            return subprocess.CompletedProcess(list(cmd), returncode, stdout, '')
        return _REAL_SUBPROCESS_RUN(cmd, **kwargs)

    monkeypatch.setattr(_fr.subprocess, 'run', dispatching_run)
    monkeypatch.setattr(_fr, 'get_executor_path', lambda: Path('/nonexistent/execute-script.py'))
    return calls


def _merged_payload(sha: str) -> str:
    """A ``ci pr view`` TOON payload reporting ``_PR_NUMBER`` merged at ``sha``."""
    return (
        'status: success\n'
        'operation: pr_view\n'
        f'pr_number: {_PR_NUMBER}\n'
        'state: merged\n'
        f'merge_commit_sha: {sha}\n'
    )


def _establish_live_diff(monkeypatch) -> None:
    """Make tier ``live_diff`` answer, the only higher tier with no on-disk key."""
    monkeypatch.setattr(_fr, 'resolve_live_worktree', lambda plan_id: Path('/live/worktree'))
    monkeypatch.setattr(_fr, 'resolve_base_ref', lambda explicit, refs: 'main')
    monkeypatch.setattr(
        _fr, 'compute_plan_branch_diff', lambda worktree, base_ref: set(_ABOVE_TIER_ANSWERS['live_diff'])
    )


def _refs_for(tier: str, landings: _Landings) -> dict:
    """The references payload that establishes ``tier`` and records the PR number."""
    payloads = {
        'live_diff': {'base_branch': 'main', 'pr_number': str(_PR_NUMBER)},
        'realized_capture': {
            'realized_footprint': sorted(_ABOVE_TIER_ANSWERS['realized_capture']),
            'pr_number': str(_PR_NUMBER),
        },
        'merge_commit': {'merge_commit_sha': landings['merge_sha'], 'pr_number': str(_PR_NUMBER)},
    }
    return payloads[tier]


def _resolve_above_tier(tier: str, landings: _Landings, monkeypatch) -> tuple[object, list]:
    """Run the whole chain with ``tier`` established and the provider ready to differ."""
    repo = landings['repo']
    _write_refs(repo, _refs_for(tier, landings))
    calls = _stub_ci(monkeypatch, _merged_payload(landings['pr_sha']))
    if tier == 'live_diff':
        _establish_live_diff(monkeypatch)
    return _fr.resolve_footprint(repo, None), calls


# =============================================================================
# The population these controls are derived from
# =============================================================================


def test_the_controlled_tier_and_the_tiers_above_it_are_read_from_the_chain():
    """The control set is derived from the resolver's declared precedence order.

    Hand-copying the roster would let a tier inserted above the PR-landing tier
    ship with no control while every assertion below still passed.
    """
    assert _PR_LANDING in _fr.RESOLVING_TIERS
    assert _TIERS_ABOVE_PR_LANDING == ('live_diff', 'realized_capture', 'merge_commit')
    # A tier BELOW is legitimately overridden, so it is not part of this claim.
    assert _fr.RESOLVING_TIERS[_fr.RESOLVING_TIERS.index(_PR_LANDING) + 1 :] == ('legacy_key',)


def test_every_tier_above_has_a_control_and_none_is_unexercised():
    """The roster of controls equals the roster of tiers they must cover."""
    assert set(_ABOVE_TIER_ANSWERS) == set(_TIERS_ABOVE_PR_LANDING)
    assert len(_ABOVE_TIER_ANSWERS) == 3


def test_the_provider_answer_is_distinguishable_from_every_higher_tier_answer():
    """The negative controls cannot pass by coincidence.

    Were the stub's path set to overlap a higher tier's, a wrongly-firing tier
    would return the expected answer and every must-not-fire assertion would read
    green while measuring nothing.
    """
    for tier, answer in _ABOVE_TIER_ANSWERS.items():
        assert _PR_ONLY_PATHS.isdisjoint(answer), f'{tier} answer is not distinguishable'


# =============================================================================
# The fixture's own shape — the merge landing is a genuine merge commit
# =============================================================================


def test_the_merge_landing_fixture_is_a_genuine_two_parent_merge_commit(tmp_path):
    """The negative control's landing is a real merge, not a linear commit.

    Asserted from git rather than assumed, because a fixture that silently
    degraded to one parent would turn this control into a duplicate of the squash
    shape while still passing.
    """
    landings = _repo_with_a_genuine_merge_and_a_separate_pr_landing(tmp_path)

    assert _parent_count(landings['repo'], landings['merge_sha']) == 2
    assert _parent_count(landings['repo'], landings['pr_sha']) == 1


# =============================================================================
# Must NOT fire — a higher-precedence tier keeps its answer
# =============================================================================


def test_a_genuine_merge_commit_landing_keeps_precedence_over_the_pr_tier(tmp_path, monkeypatch):
    """The headline negative control: a real merge landing WINS, provider unread.

    The provider stands ready to report a different landing, so the assertion
    separates "the tier did not fire" from "the tier fired and happened to agree".
    """
    landings = _repo_with_a_genuine_merge_and_a_separate_pr_landing(tmp_path)

    resolved, calls = _resolve_above_tier('merge_commit', landings, monkeypatch)

    assert resolved == _ABOVE_TIER_ANSWERS['merge_commit']
    assert resolved != _PR_ONLY_PATHS
    assert calls == []


def test_no_higher_precedence_tier_is_overridden_and_all_of_them_were_exercised(
    tmp_path, monkeypatch
):
    """The direction, swept over every tier that outranks the PR-landing tier.

    Publishes the population it compared: a sweep that established no tier would
    otherwise report an empty violation list and read as a clean pass.
    """
    violations: list[str] = []
    established: list[str] = []

    for tier in _TIERS_ABOVE_PR_LANDING:
        monkeypatch.undo()
        landings = _repo_with_a_genuine_merge_and_a_separate_pr_landing(tmp_path / tier)
        resolved, calls = _resolve_above_tier(tier, landings, monkeypatch)
        if not _fr.footprint_resolved(resolved):
            violations.append(f'{tier}: higher tier did not resolve at all')
            continue
        established.append(tier)
        if resolved != _ABOVE_TIER_ANSWERS[tier]:
            violations.append(f'{tier}: answer changed to {sorted(resolved)}')
        if calls:
            violations.append(f'{tier}: provider was consulted {len(calls)} time(s)')

    assert violations == []
    assert established == list(_TIERS_ABOVE_PR_LANDING)
    assert len(established) == 3


# =============================================================================
# Must FIRE — the matched counterpart, one key removed
# =============================================================================


def test_the_pr_tier_fires_when_no_higher_tier_resolves(tmp_path, monkeypatch):
    """The matched positive: same repo, same stub, only the higher key removed.

    This is what makes the silence above meaningful — the tier is demonstrably
    able to answer with this exact fixture and this exact provider stub.
    """
    landings = _repo_with_a_genuine_merge_and_a_separate_pr_landing(tmp_path)
    repo = landings['repo']
    _write_refs(repo, {'base_branch': 'main', 'pr_number': str(_PR_NUMBER)})
    calls = _stub_ci(monkeypatch, _merged_payload(landings['pr_sha']))

    resolved = _fr.resolve_footprint(repo, None)

    assert _fr.footprint_resolved(resolved)
    assert resolved == _PR_ONLY_PATHS
    assert len(calls) == 1


def test_the_pr_tier_only_ever_converts_unresolvable_into_resolved(tmp_path, monkeypatch):
    """Both halves in one comparison: the same repo answers differently only when
    the higher-precedence key is absent, and the conversion runs in one direction.
    """
    landings = _repo_with_a_genuine_merge_and_a_separate_pr_landing(tmp_path)
    repo = landings['repo']

    _write_refs(repo, {'base_branch': 'main', 'pr_number': str(_PR_NUMBER)})
    _stub_ci(monkeypatch, _merged_payload(landings['pr_sha']))
    without_higher_tier = _fr.resolve_footprint(repo, None)

    monkeypatch.undo()
    _write_refs(repo, _refs_for('merge_commit', landings))
    _stub_ci(monkeypatch, _merged_payload(landings['pr_sha']))
    with_higher_tier = _fr.resolve_footprint(repo, None)

    # Removing the higher-precedence key is the ONLY difference between the runs.
    assert without_higher_tier == _PR_ONLY_PATHS
    assert with_higher_tier == _ABOVE_TIER_ANSWERS['merge_commit']
    assert without_higher_tier != with_higher_tier


def test_an_unreadable_provider_leaves_the_higher_tier_answer_untouched(tmp_path, monkeypatch):
    """A provider outage is not a way to disturb a resolved higher-tier answer.

    The failing-transport counterpart of the silence control: the tier cannot
    change the verdict when it succeeds, and it cannot damage it when it fails.
    """
    landings = _repo_with_a_genuine_merge_and_a_separate_pr_landing(tmp_path)
    repo = landings['repo']
    _write_refs(repo, _refs_for('merge_commit', landings))
    calls = _stub_ci(monkeypatch, 'status: error\nerror: boom\n', returncode=1)

    resolved = _fr.resolve_footprint(repo, None)

    assert resolved == _ABOVE_TIER_ANSWERS['merge_commit']
    assert calls == []
