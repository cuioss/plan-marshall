"""Tests for the ``ci pr landing-state`` verb — the foreign done-ness discriminator.

Three layers:

* the pure correlation :func:`ci_base.derive_landing_state`, with ONE case per
  return value and the produced-state population asserted against the verb's OWN
  declared set (:data:`ci_base.LANDING_STATES`) rather than a hand-copied list;
* the github handler :func:`_github_pr.cmd_pr_landing_state`, driven end-to-end
  with the git / gh / auth primitives monkeypatched on ``github_ops`` so each of
  the four landing states — plus the stale-tip, truncation, malformed-entry,
  auth, and git-evidence fail-closed paths — is exercised through the real
  handler body;
* the DOC-vs-runtime parity guard at the end of this module, which holds
  ``tools-integration-ci/standards/api-contract.md`` to the two closed
  populations ``ci_base`` declares — :data:`ci_base.LANDING_STATES` and
  :data:`ci_base.PR_VIEW_CAUSES`. The runtime sides were already guarded; the
  DOCUMENTED copies were not, and that document is the surface a consumer reads
  to decide what to branch on.
"""
import argparse
import json
import re
from pathlib import Path

import _github_pr
import ci_base
import github_ops
import pytest
from ci_base import LANDING_STATES, PR_VIEW_CAUSES, derive_landing_state

from conftest import PROJECT_ROOT

_CASE_PER_STATE: dict[str, tuple[list[str], bool]] = {
    'merged': (['MERGED'], True),
    'pr_open': (['OPEN'], True),
    'pushed_no_pr': ([], True),
    'unpushed': ([], False),
}
_TIP_SHA = 'deadbeefcafebabefeedface00000000deadbeef'
def _install_primitives(
    monkeypatch,
    *,
    pr_states,
    pushed,
    auth=(True, ''),
    tip_sha=_TIP_SHA,
    head_oids=None,
    git_contain_rc=0,
):
    """Monkeypatch github_ops' auth / gh / git primitives for one handler run.

    ``pr_states`` becomes the ``gh pr list --json`` payload; each PR's
    ``headRefOid`` is ``head_oids[i]`` (default: all == ``tip_sha`` so every PR is
    tip-matching). ``pushed`` drives ``git branch -r --contains`` (non-empty ⇒
    pushed); ``git_contain_rc`` forces a containment failure when non-zero.
    """
    monkeypatch.setattr(github_ops, 'check_auth', lambda: auth)
    oids = head_oids if head_oids is not None else [tip_sha] * len(pr_states)

    def fake_run_gh(args, capture_json=False, timeout=60):
        assert args[:2] == ['pr', 'list']
        payload = [
            {
                'number': i + 1,
                'state': s,
                'url': f'https://x/pull/{i + 1}',
                'headRefName': 'feature/x',
                'headRefOid': oids[i],
            }
            for i, s in enumerate(pr_states)
        ]
        return 0, json.dumps(payload), ''

    def fake_run_git(args, timeout=60):
        if args[:2] == ['rev-parse', '--abbrev-ref']:
            return 0, 'feature/x\n', ''
        if args[:1] == ['rev-parse']:
            return 0, f'{tip_sha}\n', ''
        if args[:3] == ['branch', '-r', '--contains']:
            if git_contain_rc != 0:
                return git_contain_rc, '', 'containment error'
            return (0, '  origin/feature/x\n', '') if pushed else (0, '', '')
        return 1, '', f'unexpected git args: {args}'

    monkeypatch.setattr(github_ops, 'run_gh', fake_run_gh)
    monkeypatch.setattr(github_ops, 'run_git', fake_run_git)
_API_CONTRACT: Path = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'tools-integration-ci'
    / 'standards'
    / 'api-contract.md'
)
_CAUSE_TABLE_HEADER = '| `error_cause` |'
_LANDING_POPULATION_RE = re.compile(r'own declared population \(([^)]*)\)')
_MEMBER_RE = re.compile(r'`([a-z_]+)`')
_SEPARATOR_RE = re.compile(r'^\|[\s:|-]+$')
def _api_contract_text() -> str:
    return _API_CONTRACT.read_text(encoding='utf-8')
def _documented_pr_view_causes(text: str) -> set[str]:
    """The ``error_cause`` members the api-contract cause table names."""
    lines = text.splitlines()
    header_at = next((i for i, line in enumerate(lines) if line.startswith(_CAUSE_TABLE_HEADER)), None)
    assert header_at is not None, (
        f'{_API_CONTRACT} no longer carries the cause-table header '
        f'{_CAUSE_TABLE_HEADER!r}, so the documented population cannot be located at all. '
        f'ci_base declares {len(PR_VIEW_CAUSES)} cause(s): {sorted(PR_VIEW_CAUSES)}.'
    )
    assert _SEPARATOR_RE.match(lines[header_at + 1]), (
        f'The row after the cause-table header in {_API_CONTRACT} is not a markdown '
        f'separator, so the table shape changed and its member rows cannot be bounded.'
    )
    members: set[str] = set()
    for line in lines[header_at + 2 :]:
        if not line.startswith('|'):
            break
        cell = line.split('|')[1].strip()
        matched = _MEMBER_RE.fullmatch(cell)
        assert matched is not None, (
            f'A cause-table row in {_API_CONTRACT} has first cell {cell!r}, which is not a '
            f'single backticked member name; the extractor cannot say what it documents.'
        )
        members.add(matched.group(1))
    return members
def _documented_landing_states(text: str) -> set[str]:
    """The ``landing_state`` members the api-contract field-semantics sentence names."""
    matched = _LANDING_POPULATION_RE.search(text)
    assert matched is not None, (
        f'{_API_CONTRACT} no longer carries the "own declared population (...)" sentence, '
        f'so the documented landing-state list cannot be located at all. ci_base declares '
        f'{len(LANDING_STATES)} state(s): {sorted(LANDING_STATES)}.'
    )
    return set(_MEMBER_RE.findall(matched.group(1)))
GUARD_POPULATION_LABEL = 'api-contract parity members (pr_view_causes + landing_states)'
GUARD_POPULATION_SIZE = len(PR_VIEW_CAUSES) + len(LANDING_STATES)


def test_declared_set_is_non_empty():
    # Non-vacuity guard: a derived-population sweep over an empty set would pass
    # every "for state in LANDING_STATES" assertion while testing nothing.
    assert len(LANDING_STATES) >= 1
def test_case_table_matches_the_declared_state_set():
    # The verb's declared population is the source of truth; the case table must
    # cover exactly it, so a future state added to LANDING_STATES fails here
    # until a case is supplied rather than going silently untested.
    assert set(_CASE_PER_STATE) == set(LANDING_STATES)
@pytest.mark.parametrize('expected_state', LANDING_STATES)
def test_each_declared_state_is_produced_by_its_case(expected_state):
    pr_states, pushed = _CASE_PER_STATE[expected_state]
    assert derive_landing_state(pr_states, pushed) == expected_state
def test_produced_states_cover_exactly_the_declared_set():
    produced = {derive_landing_state(prs, pushed) for prs, pushed in _CASE_PER_STATE.values()}
    assert produced  # non-vacuity
    assert produced == set(LANDING_STATES)
def test_merged_wins_over_open_when_both_reference_the_branch():
    assert derive_landing_state(['OPEN', 'MERGED'], True) == 'merged'
def test_merged_is_authoritative_even_when_branch_looks_unpushed():
    # A merged PR whose head branch was deleted by the merge reports merged even
    # though remote containment is now False — PR state precedes push state.
    assert derive_landing_state(['MERGED'], False) == 'merged'
def test_closed_unmerged_pr_collapses_to_pushed_no_pr():
    # A closed-but-unmerged PR leaves the change stranded on a remote branch with
    # nothing carrying it to merge — the blocking state, not pr_open/merged.
    assert derive_landing_state(['CLOSED'], True) == 'pushed_no_pr'
def test_state_spelling_is_case_insensitive():
    assert derive_landing_state(['merged'], True) == 'merged'
    assert derive_landing_state(['open'], True) == 'pr_open'
@pytest.mark.parametrize('expected_state', LANDING_STATES)
def test_handler_produces_each_declared_state(monkeypatch, expected_state):
    pr_states, pushed = _CASE_PER_STATE[expected_state]
    _install_primitives(monkeypatch, pr_states=pr_states, pushed=pushed)

    result = github_ops.cmd_pr_landing_state(argparse.Namespace(branch='feature/x'))

    assert result['status'] == 'success'
    assert result['landing_state'] == expected_state
    # The verb publishes its own declared population so a consumer/test reads it
    # from the code rather than re-listing it.
    assert result['landing_states'] == list(LANDING_STATES)
    assert result['tip_sha'] == _TIP_SHA
def test_stale_merged_pr_for_an_earlier_tip_is_not_merged(monkeypatch):
    # A merged PR whose head is an OLD tip on a reused branch name must not report
    # merged for the current tip's new, unlanded commits.
    _install_primitives(
        monkeypatch,
        pr_states=['MERGED'],
        pushed=True,
        head_oids=['0000000000000000000000000000000000000000'],  # != _TIP_SHA
    )
    result = github_ops.cmd_pr_landing_state(argparse.Namespace(branch='feature/x'))
    assert result['status'] == 'success'
    assert result['pr_count'] == 0  # the stale PR is filtered out
    assert result['landing_state'] == 'pushed_no_pr'
def test_truncated_pr_list_fails_closed(monkeypatch):
    _install_primitives(monkeypatch, pr_states=['OPEN'] * _github_pr._PR_LIST_LIMIT, pushed=True)
    result = github_ops.cmd_pr_landing_state(argparse.Namespace(branch='feature/x'))
    assert result['status'] == 'error'
    assert 'truncated' in result.get('error', '').lower()
def test_git_containment_failure_fails_closed_when_verdict_depends_on_it(monkeypatch):
    # No PR carries the branch, so the verdict rests on remote containment; a git
    # failure there is unreadable evidence and must not become a clearing state.
    _install_primitives(monkeypatch, pr_states=[], pushed=True, git_contain_rc=1)
    result = github_ops.cmd_pr_landing_state(argparse.Namespace(branch='feature/x'))
    assert result['status'] == 'error'
def test_git_containment_failure_tolerated_when_a_merged_pr_exists(monkeypatch):
    # A tip-matching merged PR settles the verdict without git, so a containment
    # failure is irrelevant and must not turn a merged change into an error.
    _install_primitives(monkeypatch, pr_states=['MERGED'], pushed=True, git_contain_rc=1)
    result = github_ops.cmd_pr_landing_state(argparse.Namespace(branch='feature/x'))
    assert result['status'] == 'success'
    assert result['landing_state'] == 'merged'
def test_unresolvable_tip_fails_closed(monkeypatch):
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(github_ops, 'run_git', lambda args, timeout=60: (128, '', 'unknown revision'))
    result = github_ops.cmd_pr_landing_state(argparse.Namespace(branch='feature/x'))
    assert result['status'] == 'error'
    assert 'tip sha' in result.get('error', '').lower()
def test_malformed_pr_entry_fails_closed(monkeypatch):
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(github_ops, 'run_git', lambda args, timeout=60: (0, f'{_TIP_SHA}\n', ''))
    monkeypatch.setattr(
        github_ops, 'run_gh', lambda args, capture_json=False, timeout=60: (0, json.dumps(['not-an-object']), '')
    )
    result = github_ops.cmd_pr_landing_state(argparse.Namespace(branch='feature/x'))
    assert result['status'] == 'error'
def test_pr_entry_without_state_fails_closed(monkeypatch):
    monkeypatch.setattr(github_ops, 'check_auth', lambda: (True, ''))
    monkeypatch.setattr(github_ops, 'run_git', lambda args, timeout=60: (0, f'{_TIP_SHA}\n', ''))
    monkeypatch.setattr(
        github_ops,
        'run_gh',
        lambda args, capture_json=False, timeout=60: (0, json.dumps([{'number': 1, 'headRefOid': _TIP_SHA}]), ''),
    )
    result = github_ops.cmd_pr_landing_state(argparse.Namespace(branch='feature/x'))
    assert result['status'] == 'error'
def test_landing_states_is_the_authoritative_population_reference():
    # ci_base owns the declared population; the verb and its gate read it from
    # here. (Not a mirrored-literal assertion — it names the single source.)
    assert ci_base.LANDING_STATES is LANDING_STATES
    assert 'pushed_no_pr' in LANDING_STATES
def test_both_declared_populations_are_non_empty():
    # Non-vacuity: a set-equality guard over two empty sets passes while measuring
    # nothing, and the published total would then read as a healthy zero.
    assert len(PR_VIEW_CAUSES) >= 1
    assert len(LANDING_STATES) >= 1
    assert GUARD_POPULATION_SIZE == len(PR_VIEW_CAUSES) + len(LANDING_STATES)
def test_api_contract_names_exactly_the_declared_pr_view_causes():
    documented = _documented_pr_view_causes(_api_contract_text())
    declared = set(PR_VIEW_CAUSES)
    assert documented == declared, (
        f'api-contract.md and ci_base.PR_VIEW_CAUSES disagree: documented-only '
        f'{sorted(documented - declared)}, declared-only {sorted(declared - documented)}. '
        f'Measured sizes: doc={len(documented)}, code={len(declared)}.'
    )
def test_api_contract_names_exactly_the_declared_landing_states():
    documented = _documented_landing_states(_api_contract_text())
    declared = set(LANDING_STATES)
    assert documented == declared, (
        f'api-contract.md and ci_base.LANDING_STATES disagree: documented-only '
        f'{sorted(documented - declared)}, declared-only {sorted(declared - documented)}. '
        f'Measured sizes: doc={len(documented)}, code={len(declared)}.'
    )
