# SPDX-License-Identifier: FSL-1.1-ALv2
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


def test_cause_parity_rejects_a_renamed_member():
    text = _api_contract_text()
    mutated = text.replace('`no_pr_found`', '`no_pr_found_x`')
    assert mutated != text, 'the rename mutation did not apply; the control proves nothing'
    assert _documented_pr_view_causes(mutated) != set(PR_VIEW_CAUSES)


def test_cause_parity_rejects_an_extra_documented_member():
    lines = _api_contract_text().splitlines()
    header_at = next(i for i, line in enumerate(lines) if line.startswith(_CAUSE_TABLE_HEADER))
    lines.insert(header_at + 2, '| `invented_cause` | fabricated | Yes | No |')
    documented = _documented_pr_view_causes('\n'.join(lines))
    assert 'invented_cause' in documented
    assert documented != set(PR_VIEW_CAUSES)


def test_cause_parity_rejects_a_dropped_documented_member():
    kept = [line for line in _api_contract_text().splitlines() if not line.startswith('| `no_pr_found` |')]
    documented = _documented_pr_view_causes('\n'.join(kept))
    assert 'no_pr_found' not in documented
    assert documented != set(PR_VIEW_CAUSES)


def test_landing_parity_rejects_a_renamed_member():
    text = _api_contract_text()
    mutated = _LANDING_POPULATION_RE.sub(
        'own declared population (`merged`, `pr_open`, `pushed_no_pr`, `unpushed_x`)',
        text,
        count=1,
    )
    assert mutated != text, 'the rename mutation did not apply; the control proves nothing'
    assert _documented_landing_states(mutated) != set(LANDING_STATES)


def test_landing_parity_rejects_a_dropped_member():
    text = _api_contract_text()
    mutated = _LANDING_POPULATION_RE.sub('own declared population (`merged`, `pr_open`, `pushed_no_pr`)', text, count=1)
    assert mutated != text, 'the drop mutation did not apply; the control proves nothing'
    assert _documented_landing_states(mutated) != set(LANDING_STATES)
