#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the shared plan-footprint resolver (``_footprint_resolver``).

Pins the D4 tiers that let an ARCHIVED plan — whose worktree branch-cleanup
removed — resolve a footprint instead of falling to UNRESOLVED:

* Tier 2 — the ``references.realized_footprint`` capture (the capture-while-true
  side effect), and its precedence over the legacy key.
* Tier 3 — the merge-commit fallback (``git diff {sha}^1 {sha}``), for BOTH a
  linear/squash landing and a true merge commit, and its fall-through on a bad SHA.
* Tier 4 — the PR-landing fallback: ``references.pr_number`` resolved through the CI
  abstraction to THIS PR's own landing SHA, then diffed by the same first-parent range.
  Covers the positive fire, the three-outcome read (present / reported-absent /
  could-not-read), every unresolvable branch, and its strict subordination to tier 3.
* Tier 5 — the legacy ``references.modified_files`` key.
* Tier 6 — the negative control: nothing resolvable yields FOOTPRINT_UNRESOLVED, a
  present-but-empty capture is a resolved-empty set (never the sentinel).

Also pins the doc-vs-body agreement the tier chain rests on: the module docstring's
enumerated tier count equals the number of tiers ``resolve_footprint`` actually consults,
so a docstring promising a tier the body does not wire cannot ship.
"""

from __future__ import annotations

import inspect
import json
import re
import subprocess
from pathlib import Path

from conftest import load_script_module

_fr = load_script_module('plan-marshall', 'plan-retrospective', '_footprint_resolver.py')


# =============================================================================
# Git fixture helpers
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


# =============================================================================
# _coerce_path_set — the shared tier-value decoder
# =============================================================================


def test_coerce_path_set_missing_key_is_none():
    assert _fr._coerce_path_set(None) is None


def test_coerce_path_set_bare_string_is_one_element():
    assert _fr._coerce_path_set('a.py') == {'a.py'}


def test_coerce_path_set_empty_list_is_resolved_empty():
    # A present-but-empty list is a resolved, genuinely-empty footprint — NOT None.
    assert _fr._coerce_path_set([]) == set()


def test_coerce_path_set_non_list_is_none():
    assert _fr._coerce_path_set(42) is None


# =============================================================================
# Tier 2 — realized-footprint capture (and its precedence)
# =============================================================================


def test_tier2_realized_footprint_capture(tmp_path):
    """An archived plan (no worktree) resolves via references.realized_footprint."""
    plan_dir = tmp_path / 'plan'
    _write_refs(plan_dir, {'realized_footprint': ['src/a.py', 'src/b.py']})

    resolved = _fr.resolve_footprint(plan_dir, None)
    assert _fr.footprint_resolved(resolved)
    assert resolved == {'src/a.py', 'src/b.py'}


def test_tier2_preferred_over_legacy_key(tmp_path):
    """The capture is PREFERRED over the legacy modified_files key."""
    plan_dir = tmp_path / 'plan'
    _write_refs(
        plan_dir,
        {'realized_footprint': ['captured.py'], 'modified_files': ['legacy.py']},
    )

    resolved = _fr.resolve_footprint(plan_dir, None)
    assert resolved == {'captured.py'}


def test_tier2_present_but_empty_is_resolved_empty(tmp_path):
    """A present-but-empty capture is a resolved-empty set, never the sentinel."""
    plan_dir = tmp_path / 'plan'
    _write_refs(plan_dir, {'realized_footprint': []})

    resolved = _fr.resolve_footprint(plan_dir, None)
    assert _fr.footprint_resolved(resolved)
    assert resolved == set()


# =============================================================================
# Tier 3 — merge-commit fallback (squash AND true-merge shapes)
# =============================================================================


def test_tier3_merge_commit_linear_squash_shape(tmp_path):
    """A linear landing commit (one parent) resolves via git diff {sha}^1 {sha}.

    This is the squash shape: the landing commit's single parent is the base, so
    the first-parent range names exactly the paths the landing introduced.
    """
    repo = tmp_path / 'repo'
    _init_repo(repo)
    _commit(repo, 'base', {'base.txt': 'base\n'})
    landing = _commit(repo, 'squash landing', {'feat/a.py': 'a\n', 'feat/b.py': 'b\n'})
    _write_refs(repo, {'merge_commit_sha': landing})

    resolved = _fr.resolve_footprint(repo, None)
    assert _fr.footprint_resolved(resolved)
    assert resolved == {'feat/a.py', 'feat/b.py'}


def test_tier3_merge_commit_true_merge_shape(tmp_path):
    """A true merge commit (two parents) resolves the merged-in side via {sha}^1.

    The first parent of a merge commit is the base branch, so {sha}^1..{sha} names
    the feature's changes — exact, and free of sibling contamination.
    """
    repo = tmp_path / 'repo'
    _init_repo(repo)
    _commit(repo, 'base', {'base.txt': 'base\n'})
    _git(repo, 'checkout', '-b', 'feature')
    _commit(repo, 'feature change', {'feat/only.py': 'x\n'})
    _git(repo, 'checkout', 'main')
    # Advance main with a sibling file the merge must NOT attribute to the feature.
    _commit(repo, 'sibling on main', {'sibling.py': 's\n'})
    _git(repo, 'merge', '--no-ff', 'feature', '-m', 'merge feature')
    merge_sha = _git(repo, 'rev-parse', 'HEAD').strip()
    _write_refs(repo, {'merge_commit_sha': merge_sha})

    resolved = _fr.resolve_footprint(repo, None)
    assert _fr.footprint_resolved(resolved)
    # Only the feature's file — the sibling that landed on main independently is
    # excluded because {sha}^1 is main's tip at merge time.
    assert resolved == {'feat/only.py'}


def test_tier3_bad_sha_falls_through_to_legacy(tmp_path):
    """A recorded SHA that git cannot resolve falls through, never fabricating a set."""
    repo = tmp_path / 'repo'
    _init_repo(repo)
    _commit(repo, 'base', {'base.txt': 'base\n'})
    _write_refs(
        repo,
        {'merge_commit_sha': '0' * 40, 'modified_files': ['legacy.py']},
    )

    resolved = _fr.resolve_footprint(repo, None)
    assert resolved == {'legacy.py'}


def test_resolve_merge_commit_absent_sha_is_none(tmp_path):
    """No merge_commit_sha → the tier answers None (skip)."""
    assert _fr.resolve_merge_commit_footprint(tmp_path, {}) is None
    assert _fr.resolve_merge_commit_footprint(tmp_path, {'merge_commit_sha': '  '}) is None


# =============================================================================
# Tier 4 / Tier 5 — legacy key and the unresolvable negative control
# =============================================================================


def test_tier4_legacy_modified_files(tmp_path):
    plan_dir = tmp_path / 'plan'
    _write_refs(plan_dir, {'modified_files': ['legacy/a.py', 'legacy/b.py']})

    resolved = _fr.resolve_footprint(plan_dir, None)
    assert resolved == {'legacy/a.py', 'legacy/b.py'}


def test_tier5_unresolvable_negative_control(tmp_path):
    """Nothing resolvable → FOOTPRINT_UNRESOLVED, never a graded empty set.

    The D4 negative control: an unresolvable footprint must stay unresolvable so
    the consumer reports `inconclusive`, not a confident zero.
    """
    plan_dir = tmp_path / 'plan'
    _write_refs(plan_dir, {'base_branch': 'main'})

    resolved = _fr.resolve_footprint(plan_dir, None)
    assert resolved is _fr.FOOTPRINT_UNRESOLVED
    assert not _fr.footprint_resolved(resolved)


def test_missing_references_file_is_unresolvable(tmp_path):
    """No references.json at all → unresolvable (the resolver reads {} defensively)."""
    plan_dir = tmp_path / 'plan'
    plan_dir.mkdir()
    resolved = _fr.resolve_footprint(plan_dir, None)
    assert resolved is _fr.FOOTPRINT_UNRESOLVED


# =============================================================================
# Tier 4 — the PR-landing fallback: stubbing ONLY the CI abstraction
# =============================================================================

#: Captured before any patching so the dispatcher below can delegate to the genuine
#: implementation. Looked up as a module attribute at call time everywhere else, which
#: is what makes the monkeypatch visible to the code under test.
_REAL_SUBPROCESS_RUN = subprocess.run


def _stub_ci(monkeypatch, handler) -> list[list[str]]:
    """Route ONLY the executor's ``ci pr view`` call to *handler*.

    Every other subprocess call — notably the REAL ``git diff`` the tier runs once it has
    a SHA — is delegated to the genuine ``subprocess.run``. Blanket-stubbing
    ``subprocess.run`` would also capture the git fixture helpers in this module, and the
    positive-fire test below would then assert against a diff that nothing computed —
    a test that passes while measuring its own stub.

    Returns the list each intercepted argv is appended to, so a test can assert the
    provider was NOT consulted at all (the precedence case).
    """
    calls: list[list[str]] = []

    def dispatching_run(cmd, **kwargs):
        if isinstance(cmd, (list, tuple)) and _fr._CI_NOTATION in cmd:
            calls.append(list(cmd))
            return handler(list(cmd))
        return _REAL_SUBPROCESS_RUN(cmd, **kwargs)

    monkeypatch.setattr(_fr.subprocess, 'run', dispatching_run)
    monkeypatch.setattr(_fr, 'get_executor_path', lambda: Path('/nonexistent/execute-script.py'))
    return calls


def _ci_returns(stdout: str, returncode: int = 0):
    """A handler that answers the stubbed CI call with *stdout* / *returncode*."""

    def handler(cmd):
        return subprocess.CompletedProcess(cmd, returncode, stdout, '')

    return handler


def _ci_raises(exc: BaseException):
    """A handler that makes the stubbed CI call raise — the transport-failure shape."""

    def handler(cmd):
        raise exc

    return handler


def _pr_view_toon(**fields) -> str:
    """Render a minimal ``ci pr view`` TOON payload.

    Written as literal TOON rather than through ``serialize_toon`` so the wire format the
    tier parses is pinned by this test, not co-derived with the serializer.
    """
    lines = [f'{key}: {"null" if value is None else value}' for key, value in fields.items()]
    return '\n'.join(lines) + '\n'


def _merged_payload(pr_number: int, sha: str) -> str:
    return _pr_view_toon(
        status='success', operation='pr_view', pr_number=pr_number, state='merged', merge_commit_sha=sha
    )


# ---------------------------------------------------------------------------
# coerce_pr_number — what may key the tier at all
# ---------------------------------------------------------------------------


def test_coerce_pr_number_accepts_int_and_digit_string():
    # `manage-references set` stores every value as a STRING, so the digit-string form
    # is the one production actually writes.
    assert _fr.coerce_pr_number(456) == 456
    assert _fr.coerce_pr_number('456') == 456
    assert _fr.coerce_pr_number('  456  ') == 456


def test_coerce_pr_number_rejects_the_unknown_sentinel():
    """`pr create` emits 'unknown' when it could not parse the number out of the URL."""
    assert _fr.coerce_pr_number('unknown') is None


def test_coerce_pr_number_rejects_unusable_values():
    assert _fr.coerce_pr_number(None) is None
    assert _fr.coerce_pr_number(0) is None
    assert _fr.coerce_pr_number(-1) is None
    assert _fr.coerce_pr_number('') is None
    assert _fr.coerce_pr_number('12a') is None
    assert _fr.coerce_pr_number(1.5) is None


def test_coerce_pr_number_rejects_bool():
    """bool is an int subclass; True must not coerce to PR #1."""
    assert _fr.coerce_pr_number(True) is None
    assert _fr.coerce_pr_number(False) is None


# ---------------------------------------------------------------------------
# read_pr_landing_sha — THREE inputs, THREE outcomes, asserted separately
# ---------------------------------------------------------------------------


def test_read_outcome_present(monkeypatch):
    _stub_ci(monkeypatch, _ci_returns(_merged_payload(456, 'deadbeef')))
    assert _fr.read_pr_landing_sha(456) == (_fr.PR_SHA_PRESENT, 'deadbeef')


def test_read_outcome_reported_absent_open_pr(monkeypatch):
    """An OPEN PR is a read ANSWER — there is no landing commit — not a failure."""
    payload = _pr_view_toon(status='success', pr_number=456, state='open', merge_commit_sha=None)
    _stub_ci(monkeypatch, _ci_returns(payload))
    assert _fr.read_pr_landing_sha(456) == (_fr.PR_SHA_REPORTED_ABSENT, None)


def test_read_outcome_reported_absent_merged_without_sha(monkeypatch):
    """Merged, but the provider reported no merge commit — an absence it STATED."""
    payload = _pr_view_toon(status='success', pr_number=456, state='merged', merge_commit_sha=None)
    _stub_ci(monkeypatch, _ci_returns(payload))
    assert _fr.read_pr_landing_sha(456) == (_fr.PR_SHA_REPORTED_ABSENT, None)


def test_read_outcome_unreadable_on_provider_error(monkeypatch):
    """A provider outage is UNREADABLE — never reported as an absent SHA.

    This is the pair the tri-state exists for: collapsing this onto `reported_absent`
    would make an outage indistinguishable from an open PR.
    """
    payload = _pr_view_toon(status='error', operation='pr_view', error='No PR found')
    _stub_ci(monkeypatch, _ci_returns(payload, returncode=1))
    assert _fr.read_pr_landing_sha(456) == (_fr.PR_SHA_UNREADABLE, None)


def test_read_outcome_unreadable_distinct_from_reported_absent(monkeypatch):
    """The matched control for the pair above: same PR, two inputs, two DIFFERENT outcomes."""
    open_payload = _pr_view_toon(status='success', pr_number=456, state='open')
    _stub_ci(monkeypatch, _ci_returns(open_payload))
    absent = _fr.read_pr_landing_sha(456)

    monkeypatch.undo()
    _stub_ci(monkeypatch, _ci_returns(_pr_view_toon(status='error', error='boom'), returncode=1))
    unreadable = _fr.read_pr_landing_sha(456)

    assert absent[0] != unreadable[0]
    assert {absent[0], unreadable[0]} == {_fr.PR_SHA_REPORTED_ABSENT, _fr.PR_SHA_UNREADABLE}


def test_read_outcome_unreadable_on_empty_output(monkeypatch):
    _stub_ci(monkeypatch, _ci_returns('   '))
    assert _fr.read_pr_landing_sha(456) == (_fr.PR_SHA_UNREADABLE, None)


def test_read_outcome_unreadable_on_subprocess_failure(monkeypatch):
    _stub_ci(monkeypatch, _ci_raises(OSError('no such executable')))
    assert _fr.read_pr_landing_sha(456) == (_fr.PR_SHA_UNREADABLE, None)


def test_read_outcome_unreadable_when_executor_unresolvable(monkeypatch):
    """Nothing was asked of the provider, so nothing is known — never 'reported_absent'."""

    def _boom():
        raise RuntimeError('no executor')

    monkeypatch.setattr(_fr, 'get_executor_path', _boom)
    assert _fr.read_pr_landing_sha(456) == (_fr.PR_SHA_UNREADABLE, None)


def test_read_outcome_unreadable_when_payload_names_a_DIFFERENT_pr(monkeypatch):
    """Corroboration is against THIS PR: a payload about another PR proves nothing here."""
    _stub_ci(monkeypatch, _ci_returns(_merged_payload(999, 'deadbeef')))
    assert _fr.read_pr_landing_sha(456) == (_fr.PR_SHA_UNREADABLE, None)


def test_read_outcomes_population_is_exactly_the_declared_three():
    assert set(_fr.PR_SHA_READ_OUTCOMES) == {
        _fr.PR_SHA_PRESENT,
        _fr.PR_SHA_REPORTED_ABSENT,
        _fr.PR_SHA_UNREADABLE,
    }
    assert len(_fr.PR_SHA_READ_OUTCOMES) == 3


# ---------------------------------------------------------------------------
# Tier 4 positive fire — the squash landing tiers 2 and 3 cannot see
# ---------------------------------------------------------------------------


def test_tier4_positive_fire_resolves_a_squash_landing(tmp_path, monkeypatch):
    """pr_number and NO merge_commit_sha: the PR's own landing SHA resolves the diff.

    This is the merge-queue shape verbatim — `branch-cleanup` wrote neither
    `realized_footprint` nor `merge_commit_sha`, so tiers 2 and 3 fail together.
    """
    repo = tmp_path / 'repo'
    _init_repo(repo)
    _commit(repo, 'base', {'base.txt': 'base\n'})
    landing = _commit(repo, 'squash landing', {'feat/a.py': 'a\n', 'feat/b.py': 'b\n'})
    _write_refs(repo, {'pr_number': '456'})

    _stub_ci(monkeypatch, _ci_returns(_merged_payload(456, landing)))

    resolved = _fr.resolve_footprint(repo, None)
    assert _fr.footprint_resolved(resolved)
    assert resolved == {'feat/a.py', 'feat/b.py'}


def test_tier4_is_strictly_below_tier3_and_does_not_consult_the_provider(tmp_path, monkeypatch):
    """A recorded merge_commit_sha DECIDES; the tier never overrides a resolved answer.

    The provider must not even be consulted — asserting the call list is empty is what
    makes 'strictly below' a structural claim rather than an incidental one.
    """
    repo = tmp_path / 'repo'
    _init_repo(repo)
    _commit(repo, 'base', {'base.txt': 'base\n'})
    recorded = _commit(repo, 'recorded landing', {'recorded.py': 'r\n'})
    other = _commit(repo, 'other landing', {'other.py': 'o\n'})
    _write_refs(repo, {'merge_commit_sha': recorded, 'pr_number': '456'})

    calls = _stub_ci(monkeypatch, _ci_returns(_merged_payload(456, other)))

    resolved = _fr.resolve_footprint(repo, None)
    assert resolved == {'recorded.py'}
    assert calls == []


def test_tier4_absent_pr_number_never_consults_the_provider(tmp_path, monkeypatch):
    """The branch every pre-create-pr plan takes; it must cost no provider round-trip."""
    plan_dir = tmp_path / 'plan'
    _write_refs(plan_dir, {'base_branch': 'main'})
    calls = _stub_ci(monkeypatch, _ci_returns(_merged_payload(456, 'deadbeef')))

    assert _fr.resolve_pr_landing_footprint(plan_dir, {'base_branch': 'main'}) is None
    assert calls == []


# ---------------------------------------------------------------------------
# Tier 4 — EVERY unresolvable branch is the sentinel, never an empty set
# ---------------------------------------------------------------------------


def test_tier4_unresolvable_branches_return_the_sentinel_never_an_empty_set(tmp_path, monkeypatch):
    """An empty set is a resolved, genuinely-empty footprint — a wrong answer here."""
    repo = tmp_path / 'repo'
    _init_repo(repo)
    _commit(repo, 'base', {'base.txt': 'base\n'})
    refs = {'pr_number': '456'}

    branches = {
        'no_pr_number': (_ci_returns(_merged_payload(456, 'x')), {}),
        'open_pr': (_ci_returns(_pr_view_toon(status='success', pr_number=456, state='open')), refs),
        'merged_no_sha': (
            _ci_returns(_pr_view_toon(status='success', pr_number=456, state='merged', merge_commit_sha=None)),
            refs,
        ),
        'provider_error': (_ci_returns(_pr_view_toon(status='error', error='boom'), returncode=1), refs),
        'malformed_payload': (_ci_returns('not: a pr_view payload'), refs),
        'transport_failure': (_ci_raises(OSError('gone')), refs),
        'foreign_pr_payload': (_ci_returns(_merged_payload(999, 'x')), refs),
        'bad_sha_git_failure': (_ci_returns(_merged_payload(456, '0' * 40)), refs),
    }

    for name, (handler, branch_refs) in branches.items():
        monkeypatch.undo()
        _stub_ci(monkeypatch, handler)
        result = _fr.resolve_pr_landing_footprint(repo, branch_refs)
        assert result is _fr.FOOTPRINT_UNRESOLVED, f'{name} did not return the sentinel'
        assert result != set(), f'{name} returned a resolved-empty set'


def test_tier4_falls_through_to_the_legacy_key_when_unresolvable(tmp_path, monkeypatch):
    """Fall-through, not short-circuit: a lower tier still gets its turn."""
    plan_dir = tmp_path / 'plan'
    _write_refs(plan_dir, {'pr_number': '456', 'modified_files': ['legacy.py']})
    _stub_ci(monkeypatch, _ci_returns(_pr_view_toon(status='error', error='boom'), returncode=1))

    assert _fr.resolve_footprint(plan_dir, None) == {'legacy.py'}


def test_tier4_unresolvable_leaves_the_whole_chain_unresolved(tmp_path, monkeypatch):
    """With no lower tier to catch it, the chain reports UNRESOLVED — not empty."""
    plan_dir = tmp_path / 'plan'
    _write_refs(plan_dir, {'pr_number': '456'})
    _stub_ci(monkeypatch, _ci_returns(_pr_view_toon(status='error', error='boom'), returncode=1))

    resolved = _fr.resolve_footprint(plan_dir, None)
    assert resolved is _fr.FOOTPRINT_UNRESOLVED
    assert not _fr.footprint_resolved(resolved)


def test_tier4_reads_through_the_ci_abstraction_not_gh(tmp_path, monkeypatch):
    """ADR-018: the provider is reached via the abstraction, never by invoking gh."""
    plan_dir = tmp_path / 'plan'
    _write_refs(plan_dir, {'pr_number': '456'})
    calls = _stub_ci(monkeypatch, _ci_returns(_pr_view_toon(status='error', error='boom'), returncode=1))

    _fr.resolve_pr_landing_footprint(plan_dir, {'pr_number': '456'})

    assert len(calls) == 1
    argv = calls[0]
    assert _fr._CI_NOTATION in argv
    assert argv[argv.index('pr') + 1] == 'view'
    assert '--pr-number' in argv
    assert argv[argv.index('--pr-number') + 1] == '456'
    assert 'gh' not in argv


# =============================================================================
# Doc-vs-body agreement — the docstring cannot promise a tier the body omits
# =============================================================================

#: Numbered entries of the module docstring's tier list, with their bold titles.
_DOCSTRING_TIER_RE = re.compile(r'^(\d+)\. \*\*([^*]+)\*\*', re.MULTILINE)

#: The call marker that proves ``resolve_footprint`` consults each declared tier. Keyed
#: by the resolver's OWN declared population so a tier added to `RESOLVING_TIERS` without
#: a marker here fails the coverage test below rather than silently shrinking the count.
_TIER_CALL_MARKERS = {
    'live_diff': 'compute_plan_branch_diff',
    'realized_capture': 'read_captured_footprint',
    'merge_commit': 'resolve_merge_commit_footprint',
    'pr_landing': 'resolve_pr_landing_footprint',
    'legacy_key': 'read_legacy_footprint',
}


def test_tier_marker_map_covers_the_declared_population():
    """The marker map is derived from RESOLVING_TIERS, not a hand-copied parallel list."""
    assert set(_TIER_CALL_MARKERS) == set(_fr.RESOLVING_TIERS)


def test_docstring_tier_list_is_contiguous_and_ends_at_the_sentinel():
    entries = _DOCSTRING_TIER_RE.findall(_fr.__doc__)
    numbers = [int(number) for number, _title in entries]
    assert numbers == list(range(1, len(numbers) + 1)), 'docstring tier numbering has a gap'
    # Substantiates the "minus one" in the count test below rather than assuming it.
    assert entries[-1][1].strip() == 'Unresolvable'


def test_docstring_tier_count_equals_the_tiers_resolve_footprint_consults():
    """The constraint: a docstring promising five resolving tiers while the body wires
    four is the doc-vs-body divergence that hides a missing guard."""
    entries = _DOCSTRING_TIER_RE.findall(_fr.__doc__)
    documented_resolving = len(entries) - 1  # the final entry is the sentinel, not a tier
    assert documented_resolving == len(_fr.RESOLVING_TIERS)

    source = inspect.getsource(_fr.resolve_footprint)
    consulted = [tier for tier, marker in _TIER_CALL_MARKERS.items() if marker in source]
    assert sorted(consulted) == sorted(_fr.RESOLVING_TIERS)
    assert len(consulted) == documented_resolving
