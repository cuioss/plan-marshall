#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the lane's Sonar state and the merge condition it gates on.

The lane's job here is the half the merge gate was missing: a pull request whose
Sonar analysis still carries open findings is not ready, even when the SonarCloud
gate passes (that gate judges thresholds on new code, so it passes with findings
open). ``resolve`` reports the project's Sonar state beside its reviewers, the
lane reads the pull request's open findings through the provider's plan-less read,
and the merge is admitted only when the read is a confirmed zero or every
remaining finding is one the OPERATOR selected for dismissal. The lane never
records a dismissal itself: a gate that accepted the lane's own list would let the
run dismiss its own findings.

Two failure modes are pinned here because each looks clean and is not:

* a Sonar block the resolve cannot read must fail closed, never drain as "this
  project does not use Sonar";
* an ``undecidable`` read must block the merge. It is the state that reads like
  zero, and the lane's merge text binds the merge to the gate's verdict rather
  than to a reader's judgement.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from test_runbook_lane import (
    _PYPROJECT_EXEC,
    _claude_env,
    _run_resolve,
    _section,
    _seed_fixture,
    _skill_text,
)

from conftest import get_scripts_dir, load_script_module, parse_ns, run_script

lane = load_script_module('plan-marshall', 'runbook-lane', 'runbook_lane.py', 'runbook_lane_sonar_mod')

#: The unpatched delegation probe, captured once so a helper that stubs it can be undone.
_REAL_DELEGATED_SPEC = lane._delegated_workflow_spec
_REAL_READ_DELEGATED_WORKFLOW = lane._read_delegated_workflow
_REAL_READ_PR_CHECKS = lane._read_pr_checks

cmd_sonar_gate = lane.cmd_sonar_gate

_PROJECT_KEY = 'com.example:proj'
_SONAR_BLOCK = {'workflow-integration-sonar': {'organization': 'example', 'project_key': _PROJECT_KEY}}

_SCRIPT = get_scripts_dir('plan-marshall', 'runbook-lane') / 'runbook_lane.py'


# =============================================================================
# resolve — the Sonar state
# =============================================================================
def test_resolve_reports_configured_with_the_project_key(tmp_path: Path) -> None:
    spec = _seed_fixture(
        tmp_path,
        executable=_PYPROJECT_EXEC,
        required_bots='x',
        credentials_config=_SONAR_BLOCK,
    )

    data = _run_resolve(spec, tmp_path)

    assert data['sonar'] == 'configured'
    assert data['sonar_project_key'] == _PROJECT_KEY


def test_resolve_reports_not_configured_without_a_sonar_block(tmp_path: Path) -> None:
    spec = _seed_fixture(tmp_path, executable=_PYPROJECT_EXEC, required_bots='x')

    data = _run_resolve(spec, tmp_path)

    assert data['sonar'] == 'not_configured'
    assert 'sonar_project_key' not in data


def test_resolve_fails_closed_on_a_sonar_block_without_a_project_key(tmp_path: Path) -> None:
    """A block with no project key is a half-written Sonar config, not "no Sonar".

    The block's presence says the project intends to analyse with Sonar, so
    skipping the read on it would silently disable the merge gate on exactly the
    project that asked for it.
    """
    spec = _seed_fixture(
        tmp_path,
        executable=_PYPROJECT_EXEC,
        required_bots='x',
        credentials_config={'workflow-integration-sonar': {'organization': 'example'}},
    )

    data = _run_resolve(spec, tmp_path)

    assert data['status'] == 'error'
    assert data['error'] == 'sonar_config_incomplete'
    assert 'sonar' not in data


@pytest.mark.parametrize('block', ['not-an-object', ['not', 'an', 'object']])
def test_resolve_fails_closed_on_an_unreadable_sonar_block(tmp_path: Path, block) -> None:
    spec = _seed_fixture(
        tmp_path,
        executable=_PYPROJECT_EXEC,
        required_bots='x',
        credentials_config={'workflow-integration-sonar': block},
    )

    data = _run_resolve(spec, tmp_path)

    assert data['status'] == 'error'
    assert data['error'] == 'sonar_config_unreadable'


# =============================================================================
# the gate — an undecidable read never reaches the merge
# =============================================================================
def _gate_args(state: str = 'configured', count_status: str | None = 'confirmed', **flags: Any) -> object:
    """Build the namespace through the verb's own parser.

    A ``True`` value is a bare switch, so a flag the verb declares as
    ``store_true`` is passed the way the lane passes it.
    """
    argv = ['sonar-gate', '--state', state]
    if count_status is not None:
        argv += ['--count-status', count_status]
    for name, value in flags.items():
        flag = f'--{name.replace("_", "-")}'
        if isinstance(value, bool):
            if value:
                argv.append(flag)
            continue
        argv.extend([flag, value])
    return parse_ns('plan-marshall', 'runbook-lane', 'runbook_lane.py', *argv)


def test_an_undecidable_read_does_not_admit_the_merge() -> None:
    verdict = cmd_sonar_gate(_gate_args(count_status='undecidable'))

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'undecidable_read'
    assert verdict['open_issue_count'] is None


def test_an_unconfigured_read_does_not_admit_the_merge() -> None:
    """resolve said the project uses Sonar, so a read that cannot authenticate blocks."""
    verdict = cmd_sonar_gate(_gate_args(count_status='unconfigured'))

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'unconfigured_read'


def test_a_project_without_sonar_admits_the_merge() -> None:
    verdict = cmd_sonar_gate(_gate_args(state='not_configured', count_status=None))

    assert verdict['merge_allowed'] is True
    assert verdict['reason'] == 'not_configured'


def test_a_confirmed_zero_admits_the_merge() -> None:
    verdict = cmd_sonar_gate(_gate_args(open_count='0'))

    assert verdict['merge_allowed'] is True
    assert verdict['reason'] == 'no_open_issues'


def test_every_open_finding_the_operator_selected_admits_the_merge(tmp_path: Path) -> None:
    verdict = cmd_sonar_gate(
        _gate_with_progress(
            _progress_file(tmp_path, 'K1', 'K2'),
            open_count='2',
            open_keys='K1,K2',
            operator_selected_keys='K1,K2',
            hotspot_keys='',
        )
    )

    assert verdict['merge_allowed'] is True
    assert verdict['reason'] == 'all_open_issues_operator_selected'


def test_an_open_finding_the_operator_did_not_select_blocks_the_merge(tmp_path: Path) -> None:
    verdict = cmd_sonar_gate(
        _gate_with_progress(
            _progress_file(tmp_path, 'K1'),
            open_count='2',
            open_keys='K1,K2',
            operator_selected_keys='K1',
            hotspot_keys='',
        )
    )

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'open_issues_not_operator_selected'
    assert verdict['unselected_keys'] == ['K2']


def test_a_selection_without_a_progress_file_is_refused() -> None:
    """The flag alone is the lane's word, and the word is what this gate stopped taking."""
    verdict = cmd_sonar_gate(_gate_args(open_count='1', open_keys='K1', operator_selected_keys='K1'))

    assert verdict['status'] == 'error'
    assert verdict['error'] == 'progress_file_required'


def test_the_gate_refuses_a_dismissal_the_lane_recorded_itself() -> None:
    """The retired surface: a lane-recorded dismissal is not an input at all.

    The lane dismissing its own findings is the whole defect this closes, so the
    old flag is a tombstone that refuses BY NAME rather than an argparse
    rejection an operator would have to read as a typo.
    """
    verdict = cmd_sonar_gate(_gate_args(open_count='2', open_keys='K1,K2', dismissed_keys='K1,K2'))

    assert verdict['status'] == 'error'
    assert verdict['error'] == 'lane_dismissal_not_accepted'
    assert '--operator-selected-keys' in verdict['message']


def test_a_count_with_no_enumerated_keys_cannot_be_verified() -> None:
    """A count alone is not a per-finding disposition, so it is refused rather than passed."""
    verdict = cmd_sonar_gate(_gate_args(open_count='3'))

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'open_issue_keys_missing'


def test_a_repeated_key_cannot_stand_in_for_two_findings(tmp_path: Path) -> None:
    """Distinct keys, not list length: K1,K1 enumerates one finding, not two."""
    verdict = cmd_sonar_gate(
        _gate_with_progress(
            _progress_file(tmp_path, 'K1'),
            open_count='2',
            open_keys='K1,K1',
            operator_selected_keys='K1',
            hotspot_keys='',
        )
    )

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'open_issue_keys_missing'


def test_a_measured_zero_refuses_enumerated_keys() -> None:
    """A zero enumerates no key, so keys beside it describe a different read."""
    verdict = cmd_sonar_gate(_gate_args(open_count='0', open_keys='K1'))

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'confirmed_zero_with_open_keys'


def test_a_confirmed_read_without_a_count_blocks_the_merge() -> None:
    verdict = cmd_sonar_gate(_gate_args())

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'confirmed_read_without_count'


def test_the_gate_reads_both_states_from_a_resolve_result(tmp_path: Path) -> None:
    """Both resolve states drive the gate — not a literal passed by the test."""
    configured_root = tmp_path / 'configured'
    plain_root = tmp_path / 'plain'
    configured = _run_resolve(
        _seed_fixture(configured_root, executable=_PYPROJECT_EXEC, required_bots='x', credentials_config=_SONAR_BLOCK),
        configured_root,
    )
    plain = _run_resolve(
        _seed_fixture(plain_root, executable=_PYPROJECT_EXEC, required_bots='x'),
        plain_root,
    )

    assert configured['sonar'] == 'configured'
    assert cmd_sonar_gate(_gate_args(state=configured['sonar'], open_count='0'))['merge_allowed'] is True

    assert plain['sonar'] == 'not_configured'
    verdict = cmd_sonar_gate(_gate_args(state=plain['sonar'], count_status=None))
    assert verdict['merge_allowed'] is True
    assert verdict['reason'] == 'not_configured'


def test_a_not_configured_state_refuses_a_read_supplied_beside_it() -> None:
    """A count beside `not_configured` is a contradiction, not a licence to merge."""
    verdict = cmd_sonar_gate(_gate_args(state='not_configured', count_status=None, open_count='5'))

    assert verdict['status'] == 'error'
    assert verdict['error'] == 'state_contradicts_read'


@pytest.mark.parametrize(
    'flags',
    [
        {'count_status': 'confirmed'},
        {'open_keys': 'K1'},
        {'operator_selected_keys': 'K1'},
    ],
    ids=['count-status', 'open-keys', 'operator-selected-keys'],
)
def test_every_read_flag_beside_not_configured_is_refused(flags) -> None:
    """Every read flag is one read: dropping one silently would let it drain as allowed."""
    verdict = cmd_sonar_gate(_gate_args(state='not_configured', **flags))

    assert verdict['status'] == 'error'
    assert verdict['error'] == 'state_contradicts_read'
    assert '--operator-selected-keys' in verdict['message']


def _progress_file(tmp_path: Path, *keys: str) -> Path:
    path = tmp_path / 'progress.md'
    path.write_text(
        '\n'.join(f'operator-selected: {key}: the operator selected it' for key in keys) + '\n',
        encoding='utf-8',
    )
    return path


def _gate_with_progress(progress: Path, **flags: Any) -> Any:
    """Build the namespace, then attach the progress file the flag parser would set."""
    args: Any = _gate_args(**flags)
    args.progress_file = str(progress)
    return args


def test_a_selection_the_progress_file_records_admits_the_merge(tmp_path: Path) -> None:
    progress = _progress_file(tmp_path, 'K1', 'K2')

    verdict = cmd_sonar_gate(
        _gate_with_progress(
            progress, open_count='2', open_keys='K1,K2', operator_selected_keys='K1,K2', hotspot_keys=''
        )
    )

    assert verdict['merge_allowed'] is True
    assert verdict['reason'] == 'all_open_issues_operator_selected'


def test_a_selection_the_progress_file_does_not_record_is_refused(tmp_path: Path) -> None:
    """The flag alone is the lane's word; the record is what the gate believes."""
    progress = _progress_file(tmp_path, 'K1')

    verdict = cmd_sonar_gate(
        _gate_with_progress(
            progress, open_count='2', open_keys='K1,K2', operator_selected_keys='K1,K2', hotspot_keys=''
        )
    )

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'selection_not_recorded'
    assert verdict['unrecorded_keys'] == ['K2']


def test_an_unreadable_progress_file_refuses_every_selection(tmp_path: Path) -> None:
    verdict = cmd_sonar_gate(
        _gate_with_progress(
            tmp_path / 'absent.md',
            open_count='1',
            open_keys='K1',
            operator_selected_keys='K1',
            hotspot_keys='',
        )
    )

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'selection_not_recorded'


def test_a_selection_without_the_hotspot_set_is_refused(tmp_path: Path) -> None:
    """Omitting the hotspot set would let a selected hotspot pass as an issue."""
    verdict = cmd_sonar_gate(
        _gate_with_progress(
            _progress_file(tmp_path, 'K1'),
            open_count='1',
            open_keys='K1',
            operator_selected_keys='K1',
        )
    )

    assert verdict['status'] == 'error'
    assert verdict['error'] == 'hotspot_keys_required'


def test_a_selected_hotspot_key_is_refused(tmp_path: Path) -> None:
    """A hotspot has no transition verb, so a recorded dismissal of one is a fiction."""
    verdict = cmd_sonar_gate(
        _gate_with_progress(
            _progress_file(tmp_path, 'H1'),
            open_count='1',
            open_keys='H1',
            operator_selected_keys='H1',
            hotspot_keys='H1',
        )
    )

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'hotspot_not_dismissable'
    assert verdict['hotspot_keys'] == ['H1']


def test_the_gate_rejects_a_state_outside_the_closed_set() -> None:
    verdict = cmd_sonar_gate(_gate_args(state='maybe'))

    assert verdict['status'] == 'error'
    assert verdict['error'] == 'invalid_sonar_state'


def test_the_gate_rejects_a_missing_count_status_for_a_configured_project() -> None:
    verdict = cmd_sonar_gate(_gate_args(count_status=None))

    assert verdict['status'] == 'error'
    assert verdict['error'] == 'invalid_count_status'


def test_the_gate_verb_is_reachable_through_its_cli_surface() -> None:
    result = run_script(_SCRIPT, 'sonar-gate', '--state', 'configured', '--count-status', 'undecidable')

    assert result.success, result.stderr
    assert result.toon()['merge_allowed'] is False


# =============================================================================
# the lane text binds § 6's read to § 7's condition
# =============================================================================
def test_the_read_step_names_the_provider_read_and_the_gate() -> None:
    section = _section('## 6. Pull request and reviews')

    assert 'read_open_issues' in section, '§ 6 must name the plan-less provider read'
    assert 'sonar-gate' in section, '§ 6 must bind the read to the gate verdict'


def test_the_merge_condition_binds_the_merge_to_the_gate_verdict() -> None:
    section = _section('## 7. Merge gate')

    assert 'sonar-gate' in section, '§ 7 must carry the Sonar merge condition'
    assert 'merge_allowed' in section, '§ 7 must name the verdict it merges on'
    assert 'undecidable' in section, '§ 7 must state that an undecidable read blocks'


def test_the_lane_text_states_the_not_configured_skip() -> None:
    assert 'not_configured' in _skill_text()


def test_the_lane_text_binds_a_dismissal_to_the_operator_selection() -> None:
    """The lane may not dismiss its own findings; the gate admits only the operator's keys."""
    section = _section('## 6. Pull request and reviews')

    assert 'operator' in section.lower(), '§ 6 never mentions the operator in the dismissal rule'
    assert 'question tool' in section, '§ 6 does not name the selection surface'
    assert '--operator-selected-keys' in section, '§ 6 does not name the gate flag the selection feeds'


def test_the_merge_gate_never_offers_merging_on_recorded_evidence() -> None:
    section = _section('## 7. Merge gate')

    assert 'operator' in section.lower()
    assert 'recorded evidence' in section, '§ 7 does not forbid merging on the lane-recorded evidence'


def test_the_merge_gate_names_the_review_gate_as_a_condition() -> None:
    """The verb the review half decides on is a gate condition, not prose judgement."""
    section = _section('## 7. Merge gate')

    assert 'review-gate' in section
    assert 'merge_allowed' in section
    assert 'never overrides' in section, '§ 7 does not say the standing authorization cannot override a false'


# =============================================================================
# the CE-readiness budget — below the harness ceiling, so the read returns a state
# =============================================================================
class _FakeRuntime:
    """A platform runtime whose ceiling op answers a fixed TOON payload."""

    def __init__(self, payload: str | Exception) -> None:
        self._payload = payload

    def harness_bash_timeout_ceiling(self) -> str:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def _patch_ceiling(monkeypatch, payload: str | Exception) -> None:
    import platform_runtime

    monkeypatch.setattr(platform_runtime, '_runtime_for_target', lambda project_dir=None: _FakeRuntime(payload))


def test_the_ce_budget_keeps_a_margin_below_the_harness_ceiling(monkeypatch) -> None:
    _patch_ceiling(monkeypatch, 'status: success\nceiling_seconds: 600\n')

    assert lane._resolve_sonar_ce_wait(Path('.')) == 540


def test_a_target_without_a_ceiling_uses_the_provider_default(monkeypatch) -> None:
    _patch_ceiling(monkeypatch, 'status: no-op\n')

    assert lane._resolve_sonar_ce_wait(Path('.')) == 600


def test_an_unreadable_ceiling_fails_closed(monkeypatch) -> None:
    """A ceiling that could not be read must not fall back to a budget it might exceed."""
    _patch_ceiling(monkeypatch, RuntimeError('seam unavailable'))

    with pytest.raises(ValueError, match='sonar_ce_ceiling_unreadable'):
        lane._resolve_sonar_ce_wait(Path('.'))


def test_an_unparseable_ceiling_payload_fails_closed(monkeypatch) -> None:
    _patch_ceiling(monkeypatch, 'status: success\n')

    with pytest.raises(ValueError, match='sonar_ce_ceiling_unreadable'):
        lane._resolve_sonar_ce_wait(Path('.'))


def test_resolve_reports_the_ce_budget(tmp_path: Path) -> None:
    """On a target whose ceiling is 600s the budget is 540s, not a range that fits any."""
    spec = _seed_fixture(
        tmp_path,
        executable=_PYPROJECT_EXEC,
        required_bots='x',
        credentials_config=_SONAR_BLOCK,
    )

    data = _run_resolve(spec, tmp_path, env_overrides=_claude_env())

    assert int(data['sonar_ce_wait_timeout_seconds']) == 540


def test_resolve_omits_the_ce_budget_without_sonar(tmp_path: Path) -> None:
    """No read will be made, so no budget is resolved (and no broken seam can block)."""
    spec = _seed_fixture(tmp_path, executable=_PYPROJECT_EXEC, required_bots='x')

    data = _run_resolve(spec, tmp_path)

    assert data['sonar'] == 'not_configured'
    assert 'sonar_ce_wait_timeout_seconds' not in data


# =============================================================================
# sonar-stale-delta — the carry-forward decision, and the gate that names it
# =============================================================================
_ANALYSED = 'b' * 40
_HEAD = 'a' * 40


def _stale_args(**overrides: str | None) -> object:
    flags: dict[str, str | None] = {
        'state': 'configured',
        'count_status': 'undecidable',
        'analysis_revision': _ANALYSED,
        'head_revision': _HEAD,
        'worktree': '.',
    }
    flags.update(overrides)
    argv = ['sonar-stale-delta']
    for name, value in flags.items():
        if value is None:
            continue
        argv += [f'--{name.replace("_", "-")}', value]
    return parse_ns('plan-marshall', 'runbook-lane', 'runbook_lane.py', *argv)


def _patch_delta(
    monkeypatch,
    *,
    analysed=_ANALYSED,
    head=_HEAD,
    checkout=None,
    clean=True,
    ignored=(),
    paths=('doc/adr/001.adoc',),
    rows=None,
    reason='',
):
    """Stub the six seams the decision reads, leaving the decision itself real.

    These are the LOCAL-rule controls: the checkout is declared to carry no
    delegation, so the branch under test is the project's own rule.
    """
    monkeypatch.setattr(lane, '_delegated_workflow_spec', lambda project_dir: (None, ''))
    monkeypatch.setattr(lane, '_resolve_commit', lambda worktree, revision: analysed if revision == _ANALYSED else head)
    monkeypatch.setattr(lane, '_checkout_revision', lambda worktree: head if checkout is None else checkout)
    monkeypatch.setattr(lane, '_worktree_is_clean', lambda worktree: clean)
    monkeypatch.setattr(lane, '_ignored_workflow_inputs', lambda worktree: ignored)
    monkeypatch.setattr(lane, '_delta_paths', lambda worktree, base, tip: None if paths is None else list(paths))
    if rows is None:
        rows = [{'path': path, 'kind': 'docs-only'} for path in paths or ()]
    monkeypatch.setattr(lane, '_classify_paths', lambda project_dir, classified: (list(rows), 'ci-workflow', reason))


def _repo_with_a_footprint_rule(root: Path) -> None:
    """Build a real repository whose own CI rule classifies ``doc/**`` as not built."""
    import subprocess

    workflows = root / '.github' / 'workflows'
    workflows.mkdir(parents=True)
    (workflows / 'ci.yml').write_text(
        "name: CI\non:\n  pull_request:\n    paths-ignore:\n      - 'doc/**'\nskip-on-docs-only: true\n",
        encoding='utf-8',
    )
    (root / 'doc').mkdir()
    (root / 'doc' / 'one.adoc').write_text('one\n', encoding='utf-8')
    (root / 'src').mkdir()
    (root / 'src' / 'Main.java').write_text('class Main {}\n', encoding='utf-8')
    for args in (
        ('init', '-b', 'main'),
        ('config', 'user.email', 'lane@example.com'),
        ('config', 'user.name', 'lane'),
        ('add', '.'),
        ('commit', '-m', 'base'),
    ):
        subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True)


def _commit(root: Path, relative: str) -> str:
    """Write *relative*, commit it, and return the commit sha."""
    import subprocess

    (root / relative).write_text('changed\n', encoding='utf-8')
    for args in (('add', relative), ('commit', '-m', relative)):
        subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True)
    return subprocess.run(
        ['git', '-C', str(root), 'rev-parse', 'HEAD'], check=True, capture_output=True, text=True
    ).stdout.strip()


def test_the_project_own_rule_decides_a_real_docs_only_delta(tmp_path: Path) -> None:
    """End to end: the revision pair, the diff and the footprint rule are all real."""
    repo = tmp_path / 'repo'
    _repo_with_a_footprint_rule(repo)
    analysed = _commit(repo, 'doc/two.adoc')
    head = _commit(repo, 'doc/three.adoc')

    verdict = lane.cmd_sonar_stale_delta(
        _stale_args(analysis_revision=analysed, head_revision=head, worktree=str(repo))
    )

    assert verdict['carry_forward'] is True
    assert verdict['source'] == 'ci-workflow'
    assert verdict['changed_paths'] == ['doc/three.adoc']
    assert verdict['reason'].startswith('carried_forward_unbuilt_delta')


def test_a_modified_workflow_file_stays_undecidable(tmp_path: Path) -> None:
    """The regression the reviewer named: an uncommitted rule rewrite must not carry."""
    repo = tmp_path / 'repo'
    _repo_with_a_footprint_rule(repo)
    analysed = _commit(repo, 'doc/two.adoc')
    head = _commit(repo, 'doc/three.adoc')
    (repo / '.github' / 'workflows' / 'ci.yml').write_text(
        "name: CI\non:\n  pull_request:\n    paths-ignore:\n      - 'src/**'\nskip-on-docs-only: true\n",
        encoding='utf-8',
    )

    verdict = lane.cmd_sonar_stale_delta(
        _stale_args(analysis_revision=analysed, head_revision=head, worktree=str(repo))
    )

    assert verdict['carry_forward'] is False
    assert verdict['detail'].startswith('worktree_dirty')


def test_an_ignored_workflow_file_stays_undecidable(tmp_path: Path) -> None:
    """The regression the reviewer named: an ignored workflow must not supply the rule."""
    repo = tmp_path / 'repo'
    _repo_with_a_footprint_rule(repo)
    analysed = _commit(repo, 'doc/two.adoc')
    head = _commit(repo, 'doc/three.adoc')
    (repo / '.git' / 'info' / 'exclude').write_text('/.github/workflows/00-ignored.yml\n', encoding='utf-8')
    (repo / '.github' / 'workflows' / '00-ignored.yml').write_text(
        "skip-on-docs-only: true\npaths-ignore:\n  - 'src/**'\n", encoding='utf-8'
    )

    verdict = lane.cmd_sonar_stale_delta(
        _stale_args(analysis_revision=analysed, head_revision=head, worktree=str(repo))
    )

    assert verdict['carry_forward'] is False
    assert verdict['detail'].startswith('worktree_ignored_inputs')


def test_the_project_own_rule_refuses_a_real_buildable_delta(tmp_path: Path) -> None:
    repo = tmp_path / 'repo'
    _repo_with_a_footprint_rule(repo)
    analysed = _commit(repo, 'doc/two.adoc')
    head = _commit(repo, 'src/Other.java')

    verdict = lane.cmd_sonar_stale_delta(
        _stale_args(analysis_revision=analysed, head_revision=head, worktree=str(repo))
    )

    assert verdict['carry_forward'] is False
    assert verdict['reason'] == 'undecidable_read'
    assert verdict['buildable_paths'] == ['src/Other.java']


def test_a_revision_the_checkout_does_not_hold_stays_undecidable(tmp_path: Path) -> None:
    repo = tmp_path / 'repo'
    _repo_with_a_footprint_rule(repo)
    head = _commit(repo, 'doc/two.adoc')

    verdict = lane.cmd_sonar_stale_delta(
        _stale_args(analysis_revision='0' * 40, head_revision=head, worktree=str(repo))
    )

    assert verdict['carry_forward'] is False
    assert verdict['detail'].startswith('revision_unresolvable')


def test_a_docs_only_delta_is_carried_forward_from_the_analysed_head(monkeypatch) -> None:
    _patch_delta(monkeypatch)

    verdict = lane.cmd_sonar_stale_delta(_stale_args(worktree='.'))

    assert verdict['carry_forward'] is True
    assert verdict['reason'].startswith('carried_forward_unbuilt_delta')
    assert _ANALYSED in verdict['reason'] and _HEAD in verdict['reason']
    assert verdict['changed_paths'] == ['doc/adr/001.adoc']


def test_a_delta_carrying_one_buildable_path_stays_undecidable(monkeypatch) -> None:
    _patch_delta(
        monkeypatch,
        paths=('doc/adr/001.adoc', 'src/main/java/A.java'),
        rows=[
            {'path': 'doc/adr/001.adoc', 'kind': 'docs-only'},
            {'path': 'src/main/java/A.java', 'kind': 'buildable'},
        ],
    )

    verdict = lane.cmd_sonar_stale_delta(_stale_args())

    assert verdict['carry_forward'] is False
    assert verdict['reason'] == 'undecidable_read'
    assert verdict['buildable_paths'] == ['src/main/java/A.java']


def test_an_unresolvable_analysed_revision_stays_undecidable(monkeypatch) -> None:
    monkeypatch.setattr(lane, '_resolve_commit', lambda worktree, revision: '')
    monkeypatch.setattr(lane, '_delta_paths', lambda *a: pytest.fail('an unresolvable revision must not be diffed'))

    verdict = lane.cmd_sonar_stale_delta(_stale_args())

    assert verdict['carry_forward'] is False
    assert verdict['reason'] == 'undecidable_read'
    assert verdict['detail'].startswith('revision_unresolvable')


def test_an_unresolvable_head_revision_stays_undecidable(monkeypatch) -> None:
    monkeypatch.setattr(lane, '_resolve_commit', lambda worktree, revision: '' if revision == _HEAD else _ANALYSED)
    monkeypatch.setattr(lane, '_delta_paths', lambda *a: pytest.fail('an unresolvable revision must not be diffed'))

    verdict = lane.cmd_sonar_stale_delta(_stale_args())

    assert verdict['carry_forward'] is False
    assert verdict['reason'] == 'undecidable_read'
    assert verdict['detail'].startswith('revision_unresolvable')


def test_a_failed_diff_stays_undecidable(monkeypatch) -> None:
    """A diff that could not be listed is never read as an empty change."""
    _patch_delta(monkeypatch, paths=None)

    verdict = lane.cmd_sonar_stale_delta(_stale_args())

    assert verdict['carry_forward'] is False
    assert verdict['reason'] == 'undecidable_read'
    assert verdict['detail'].startswith('diff_failed')


def test_an_unreadable_footprint_rule_stays_undecidable(monkeypatch) -> None:
    _patch_delta(monkeypatch, reason='ci.yml: UnicodeDecodeError')

    verdict = lane.cmd_sonar_stale_delta(_stale_args())

    assert verdict['carry_forward'] is False
    assert verdict['reason'] == 'undecidable_read'
    assert verdict['detail'].startswith('rule_unreadable')


def test_an_unplaceable_path_stays_undecidable(monkeypatch) -> None:
    """The classifier cannot place it, so it answers buildable: fail closed."""
    _patch_delta(monkeypatch, paths=('mystery/file.xyz',), rows=[{'path': 'mystery/file.xyz', 'kind': 'buildable'}])

    verdict = lane.cmd_sonar_stale_delta(_stale_args())

    assert verdict['carry_forward'] is False
    assert verdict['reason'] == 'undecidable_read'
    assert verdict['buildable_paths'] == ['mystery/file.xyz']


def test_a_missing_revision_pair_stays_undecidable(monkeypatch) -> None:
    _patch_delta(monkeypatch)

    verdict = lane.cmd_sonar_stale_delta(_stale_args(head_revision=''))

    assert verdict['carry_forward'] is False
    assert verdict['detail'].startswith('revision_missing')


def test_an_empty_delta_is_carried_forward(monkeypatch) -> None:
    _patch_delta(monkeypatch, paths=())

    verdict = lane.cmd_sonar_stale_delta(_stale_args())

    assert verdict['carry_forward'] is True
    assert verdict['reason'].startswith('carried_forward_unbuilt_delta')
    assert verdict['changed_paths'] == []


def test_a_missing_worktree_stays_undecidable(tmp_path: Path, monkeypatch) -> None:
    _patch_delta(monkeypatch)

    verdict = lane.cmd_sonar_stale_delta(_stale_args(worktree=str(tmp_path / 'absent-tree')))

    assert verdict['carry_forward'] is False
    assert verdict['detail'].startswith('worktree_unreadable')


def test_a_project_without_sonar_has_nothing_to_carry(monkeypatch) -> None:
    _patch_delta(monkeypatch)

    verdict = lane.cmd_sonar_stale_delta(
        _stale_args(state='not_configured', count_status=None, analysis_revision=None, head_revision=None)
    )

    assert verdict['carry_forward'] is False
    assert verdict['reason'] == 'not_configured'


def test_a_not_configured_state_refuses_the_revision_pair(monkeypatch) -> None:
    """A project with no Sonar has no read, so revisions beside it are a contradiction."""
    _patch_delta(monkeypatch)

    verdict = lane.cmd_sonar_stale_delta(_stale_args(state='not_configured', count_status=None))

    assert verdict['status'] == 'error'
    assert verdict['error'] == 'state_contradicts_read'


def test_an_equal_revision_pair_stays_undecidable(tmp_path: Path, monkeypatch) -> None:
    """Two equal revisions describe a settled read, so the sentence would be false."""
    monkeypatch.setattr(lane, '_resolve_commit', lambda worktree, revision: _ANALYSED)
    monkeypatch.setattr(lane, '_delta_paths', lambda *a: pytest.fail('an equal pair is not a delta'))

    verdict = lane.cmd_sonar_stale_delta(_stale_args(head_revision=_ANALYSED))

    assert verdict['carry_forward'] is False
    assert verdict['detail'].startswith('revisions_equal')


def test_a_settled_read_is_not_the_case_this_decides(monkeypatch) -> None:
    _patch_delta(monkeypatch)

    verdict = lane.cmd_sonar_stale_delta(_stale_args(count_status='confirmed'))

    assert verdict['carry_forward'] is False
    assert verdict['reason'] == 'count_status_not_stale'


def test_a_worktree_on_another_commit_stays_undecidable(monkeypatch) -> None:
    """The rule is read from the worktree's files, so the worktree must BE the head."""
    _patch_delta(monkeypatch, checkout='c' * 40)

    verdict = lane.cmd_sonar_stale_delta(_stale_args())

    assert verdict['carry_forward'] is False
    assert verdict['detail'].startswith('worktree_not_at_head')


def test_a_dirty_worktree_stays_undecidable(monkeypatch) -> None:
    """A modified or untracked workflow file is a rule the head does not carry."""
    _patch_delta(monkeypatch, clean=False)

    verdict = lane.cmd_sonar_stale_delta(_stale_args())

    assert verdict['carry_forward'] is False
    assert verdict['detail'].startswith('worktree_dirty')


def test_an_unreadable_worktree_status_stays_undecidable(monkeypatch) -> None:
    _patch_delta(monkeypatch, clean=None)

    verdict = lane.cmd_sonar_stale_delta(_stale_args())

    assert verdict['carry_forward'] is False
    assert verdict['detail'].startswith('worktree_unreadable')


def test_ignored_workflow_inputs_stay_undecidable(monkeypatch) -> None:
    """An ignored workflow file is a rule the head does not carry, and git status hides it."""
    _patch_delta(monkeypatch, ignored=['.github/workflows/00-ignored.yml'])

    verdict = lane.cmd_sonar_stale_delta(_stale_args())

    assert verdict['carry_forward'] is False
    assert verdict['detail'].startswith('worktree_ignored_inputs')
    assert '00-ignored.yml' in verdict['detail']


def test_the_stale_delta_verb_is_reachable_through_its_cli_surface() -> None:
    result = run_script(_SCRIPT, 'sonar-stale-delta', '--state', 'configured', '--count-status', 'undecidable')

    assert result.success, result.stderr
    assert result.toon()['carry_forward'] is False


def test_a_carried_forward_zero_admits_the_merge_under_its_own_reason() -> None:
    """The figure is a measurement of the analysed head, so the verdict says which."""
    verdict = cmd_sonar_gate(
        _gate_args(
            open_count='0',
            carried_forward=True,
            carried_forward_analysis_revision=_ANALYSED,
            carried_forward_head_revision=_HEAD,
        )
    )

    assert verdict['merge_allowed'] is True
    assert verdict['reason'].startswith('carried_forward_unbuilt_delta')
    assert _ANALYSED in verdict['reason'] and _HEAD in verdict['reason']
    assert verdict['carried_forward'] is True


def test_a_carried_forward_pair_without_the_marker_is_refused() -> None:
    """The read's own ``carried_forward`` marker is what makes the pair a claim.

    Without it the pair is a caller's assertion tied to no read, which is the
    opt-in marking PLAN-LB-167's D3 refused: a carried-forward figure could read
    like a measurement of the head.
    """
    verdict = cmd_sonar_gate(
        _gate_args(
            open_count='0',
            carried_forward_analysis_revision=_ANALYSED,
            carried_forward_head_revision=_HEAD,
        )
    )

    assert verdict['status'] == 'error'
    assert verdict['error'] == 'carried_forward_unmarked'


def test_the_marker_without_the_revision_pair_is_refused() -> None:
    """A marker with no revisions asserts a carry-forward it cannot name."""
    verdict = cmd_sonar_gate(_gate_args(open_count='0', carried_forward=True))

    assert verdict['status'] == 'error'
    assert verdict['error'] == 'carried_forward_incomplete'


def test_a_carried_forward_pair_with_one_revision_is_refused() -> None:
    verdict = cmd_sonar_gate(
        _gate_args(open_count='0', carried_forward=True, carried_forward_analysis_revision=_ANALYSED)
    )

    assert verdict['status'] == 'error'
    assert verdict['error'] == 'carried_forward_incomplete'


def test_a_carried_forward_pair_with_equal_revisions_is_refused() -> None:
    """Two equal revisions assert a difference that does not exist."""
    verdict = cmd_sonar_gate(
        _gate_args(
            open_count='0',
            carried_forward=True,
            carried_forward_analysis_revision=_ANALYSED,
            carried_forward_head_revision=_ANALYSED,
        )
    )

    assert verdict['status'] == 'error'
    assert verdict['error'] == 'carried_forward_revisions_equal'


def test_a_carried_forward_pair_on_a_failed_read_is_refused() -> None:
    """The carry-forward renames a measured figure, never a failed one."""
    verdict = cmd_sonar_gate(
        _gate_args(
            count_status='undecidable',
            carried_forward=True,
            carried_forward_analysis_revision=_ANALYSED,
            carried_forward_head_revision=_HEAD,
        )
    )

    assert verdict['status'] == 'error'
    assert verdict['error'] == 'carried_forward_requires_confirmed'


def test_a_carried_forward_read_still_needs_its_findings_disposed(tmp_path: Path) -> None:
    verdict = cmd_sonar_gate(
        _gate_with_progress(
            _progress_file(tmp_path),
            open_count='2',
            open_keys='K1,K2',
            carried_forward=True,
            carried_forward_analysis_revision=_ANALYSED,
            carried_forward_head_revision=_HEAD,
        )
    )

    assert verdict['merge_allowed'] is False
    assert verdict['reason'] == 'open_issues_not_operator_selected'


def test_a_delegated_read_refuses_a_shape_it_cannot_trust(tmp_path: Path, monkeypatch) -> None:
    """The read is list-argv; its values are still shape-checked before they steer it."""
    repo = tmp_path / 'repo'
    _repo_with_a_delegation(repo)
    _patch_delegated(monkeypatch, rows=_checks())
    monkeypatch.setattr(
        lane,
        '_read_delegated_workflow',
        lambda project_dir, repo_ref, path, ref: _REAL_READ_DELEGATED_WORKFLOW(
            project_dir, 'owner/repo/../evil', path, ref
        ),
    )

    verdict = lane.cmd_sonar_stale_delta(_stale_args(pr_number='7', worktree=str(repo)))

    assert verdict['carry_forward'] is False
    assert verdict['detail'].startswith('delegated_rule_unreachable')
    assert 'owner/name' in verdict['detail']


def test_a_check_read_refuses_a_pull_request_that_is_not_a_number(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / 'repo'
    _repo_with_a_delegation(repo)
    _patch_delegated(monkeypatch, rows=_checks())
    monkeypatch.setattr(
        lane, '_read_pr_checks', lambda project_dir, pr: _REAL_READ_PR_CHECKS(project_dir, '7; rm -rf /')
    )

    verdict = lane.cmd_sonar_stale_delta(_stale_args(pr_number='7', worktree=str(repo)))

    assert verdict['carry_forward'] is False
    assert verdict['detail'].startswith('delegated_check_evidence_unreadable')
    assert 'not a number' in verdict['detail']


def test_the_lane_text_states_the_carry_forward_rule() -> None:
    section = _section('## 6. Pull request and reviews')

    assert 'sonar-stale-delta' in section, '§ 6 must name the decision verb'
    assert 'carried_forward_unbuilt_delta' in section, '§ 6 must name the distinct reason'
    assert '--analysed-revision' in section, '§ 6 must name the read licence'
    assert 'retry the read, and if it stays undecidable' in section, '§ 6 must keep the general stop'
    assert 'NOT in that retry class' in section, '§ 6 must exempt a refused stale read from the retry'


# =============================================================================
# a consumer that delegates its build to a reusable workflow
# =============================================================================
_DELEGATED_REF = '9f8e7d6c5b4a39281706f5e4d3c2b1a09f8e7d6c'

_DELEGATION_WORKFLOW = (
    'name: Maven Build\n'
    'on:\n'
    '  pull_request:\n'
    '    branches: [main]\n'
    'jobs:\n'
    '  build:\n'
    f'    uses: cuioss/cuioss-organization/.github/workflows/reusable-maven-build.yml@{_DELEGATED_REF}\n'
)

_CALLED_WORKFLOW = (
    'name: Maven Build (Reusable)\n'
    'on:\n'
    '  workflow_call:\n'
    '    inputs:\n'
    '      skip-on-docs-only:\n'
    '        default: true\n'
    'jobs:\n'
    '  config:\n'
    '    runs-on: ubuntu-latest\n'
    '  check-changes:\n'
    '    needs: config\n'
    '    outputs:\n'
    '      should-build: ${{ steps.decide.outputs.should-build }}\n'
    '  build:\n'
    '    needs: [config, check-changes]\n'
    "    if: always() && needs.check-changes.outputs.should-build != 'false'\n"
    '  sonar-build:\n'
    '    needs: [config, check-changes]\n'
    "    if: always() && needs.check-changes.outputs.should-build != 'false' && github.actor != 'dependabot[bot]'\n"
)


def _checks(*, build: str = 'skipping', sonar: str = 'skipping', decider: str = 'pass', extra: tuple = ()):
    """The head's check rows, in the shape ``ci checks status`` reports."""
    rows = [
        {'name': 'build / config', 'result': 'pass'},
        {'name': 'build / check-changes', 'result': decider},
        {'name': 'build / build (21)', 'result': build},
        {'name': 'build / build (25)', 'result': build},
        {'name': 'build / sonar-build', 'result': sonar},
        # A review bot's row, which is on EVERY pull request of this repository: it
        # belongs to no job of the called workflow, so it cannot decide the verdict.
        {'name': 'CodeRabbit', 'result': 'pending'},
    ]
    rows.extend(extra)
    return rows


def _repo_with_a_delegation(root: Path, workflow_text: str = _DELEGATION_WORKFLOW) -> None:
    workflows = root / '.github' / 'workflows'
    workflows.mkdir(parents=True)
    (workflows / 'maven.yml').write_text(workflow_text, encoding='utf-8')


def _patch_delegated(
    monkeypatch,
    *,
    called=_CALLED_WORKFLOW,
    rows=None,
    read_reason='',
    paths=('doc/adr/001.adoc',),
):
    """Stub the local git seams and the two remote reads, leaving the decision real."""
    _patch_delta(monkeypatch, paths=paths)
    monkeypatch.setattr(lane, '_delegated_workflow_spec', _REAL_DELEGATED_SPEC)
    monkeypatch.setattr(lane, '_read_delegated_workflow', lambda project_dir, repo, path, ref: (called, read_reason))
    monkeypatch.setattr(lane, '_read_pr_checks', lambda project_dir, pr: (rows, ''))


def test_a_delegating_consumer_decides_its_docs_delta_from_the_head_check_runs(tmp_path: Path, monkeypatch) -> None:
    """The PLAN-LB-167 case: a checkout holding only a `uses:` delegation."""
    repo = tmp_path / 'repo'
    _repo_with_a_delegation(repo)
    _patch_delegated(monkeypatch, rows=_checks())

    verdict = lane.cmd_sonar_stale_delta(_stale_args(pr_number='7', worktree=str(repo)))

    assert verdict['carry_forward'] is True
    assert verdict['source'] == 'delegated-check-runs'
    assert verdict['decider_jobs'] == ['check-changes']
    assert verdict['gated_jobs'] == ['build', 'sonar-build']
    assert verdict['reason'].startswith('carried_forward_unbuilt_delta')


def test_a_delegating_head_the_ci_built_stays_undecidable(tmp_path: Path, monkeypatch) -> None:
    """A head whose build jobs RAN is not a carried-forward delta, whatever the delta looks like."""
    repo = tmp_path / 'repo'
    _repo_with_a_delegation(repo)
    _patch_delegated(monkeypatch, rows=_checks(build='pass'), paths=('src/main/java/A.java',))

    verdict = lane.cmd_sonar_stale_delta(_stale_args(pr_number='7', worktree=str(repo)))

    assert verdict['carry_forward'] is False
    assert verdict['reason'] == 'undecidable_read'
    assert verdict['detail'].startswith('delegated_gated_job_ran')


def test_a_failed_check_on_a_delegating_head_stays_undecidable(tmp_path: Path, monkeypatch) -> None:
    """A skip beside a failed job of the called workflow is not the footprint gate's skip."""
    repo = tmp_path / 'repo'
    _repo_with_a_delegation(repo)
    _patch_delegated(monkeypatch, rows=_checks(sonar='fail'))

    verdict = lane.cmd_sonar_stale_delta(_stale_args(pr_number='7', worktree=str(repo)))

    assert verdict['carry_forward'] is False
    assert verdict['reason'] == 'undecidable_read'
    assert verdict['detail'].startswith('delegated_check_not_green')


def test_a_dependabot_skip_on_a_delegating_head_stays_undecidable(tmp_path: Path, monkeypatch) -> None:
    """The Dependabot shape: a docs-only delta, and ``build`` ran while ``sonar-build`` skipped.

    The delta alone would look carryable. The evidence refuses it because a job the
    footprint decision gates actually ran, so the skip cannot be attributed to that
    decision.
    """
    repo = tmp_path / 'repo'
    _repo_with_a_delegation(repo)
    _patch_delegated(monkeypatch, rows=_checks(build='pass', sonar='skipping'))

    verdict = lane.cmd_sonar_stale_delta(_stale_args(pr_number='7', worktree=str(repo)))

    assert verdict['carry_forward'] is False
    assert verdict['detail'].startswith('delegated_gated_job_ran')


def test_a_decider_that_did_not_run_stays_undecidable(tmp_path: Path, monkeypatch) -> None:
    """With the opt-in off the deciding job is skipped, so nothing suppressed the build."""
    repo = tmp_path / 'repo'
    _repo_with_a_delegation(repo)
    _patch_delegated(monkeypatch, rows=_checks(decider='skipping'))

    verdict = lane.cmd_sonar_stale_delta(_stale_args(pr_number='7', worktree=str(repo)))

    assert verdict['carry_forward'] is False
    assert verdict['detail'].startswith('delegated_decider_not_success')


@pytest.mark.parametrize(
    ('prefixes', 'path'),
    [
        (['src/main/java/'], 'src/main/java/A.java'),
        ([''], 'pom.xml'),
    ],
)
def test_a_path_the_project_architecture_builds_vetoes_the_skip(tmp_path, monkeypatch, prefixes, path) -> None:
    """A PLACED path contradicts the skip, so the CI's decision does not stand."""
    repo = tmp_path / 'repo'
    _repo_with_a_delegation(repo)
    _patch_delegated(monkeypatch, rows=_checks(), paths=(path,))
    monkeypatch.setattr(lane, '_architecture_module_prefixes', lambda project_dir: prefixes)

    verdict = lane.cmd_sonar_stale_delta(_stale_args(pr_number='7', worktree=str(repo)))

    assert verdict['carry_forward'] is False
    assert verdict['detail'].startswith('delegated_paths_buildable')


def test_an_unreadable_architecture_vetoes_the_skip(tmp_path: Path, monkeypatch) -> None:
    """A checkout whose architecture could not be read carries no delta forward."""
    repo = tmp_path / 'repo'
    _repo_with_a_delegation(repo)
    _patch_delegated(monkeypatch, rows=_checks())
    monkeypatch.setattr(lane, '_architecture_module_prefixes', lambda project_dir: None)

    verdict = lane.cmd_sonar_stale_delta(_stale_args(pr_number='7', worktree=str(repo)))

    assert verdict['carry_forward'] is False
    assert verdict['detail'].startswith('delegated_architecture_unreadable')


def test_a_checkout_with_no_module_vetoes_nothing(tmp_path: Path, monkeypatch) -> None:
    """The motivating consumer: no module places anything, so the CI's decision stands."""
    repo = tmp_path / 'repo'
    _repo_with_a_delegation(repo)
    _patch_delegated(monkeypatch, rows=_checks())
    monkeypatch.setattr(lane, '_architecture_module_prefixes', lambda project_dir: [])

    verdict = lane.cmd_sonar_stale_delta(_stale_args(pr_number='7', worktree=str(repo)))

    assert verdict['carry_forward'] is True


def test_a_root_level_build_file_is_decided_by_the_evidence(tmp_path: Path, monkeypatch) -> None:
    """No module places a root build file; the CI's own skip/ran evidence decides it."""
    repo = tmp_path / 'repo'
    _repo_with_a_delegation(repo)
    _patch_delegated(monkeypatch, rows=_checks(), paths=('pom.xml',))
    monkeypatch.setattr(lane, '_architecture_module_prefixes', lambda project_dir: ['client/'])

    carried = lane.cmd_sonar_stale_delta(_stale_args(pr_number='7', worktree=str(repo)))

    assert carried['carry_forward'] is True

    _patch_delegated(monkeypatch, rows=_checks(build='pass'), paths=('pom.xml',))

    refused = lane.cmd_sonar_stale_delta(_stale_args(pr_number='7', worktree=str(repo)))

    assert refused['carry_forward'] is False
    assert refused['detail'].startswith('delegated_gated_job_ran')


def test_another_callers_row_does_not_satisfy_a_job(tmp_path: Path, monkeypatch) -> None:
    """A second workflow may call the same reusable workflow with a job of the same id."""
    repo = tmp_path / 'repo'
    _repo_with_a_delegation(repo)
    rows = [row for row in _checks() if not row['name'].startswith('build / build')]
    rows.append({'name': 'other / build', 'result': 'skipping'})
    _patch_delegated(monkeypatch, rows=rows)

    verdict = lane.cmd_sonar_stale_delta(_stale_args(pr_number='7', worktree=str(repo)))

    assert verdict['carry_forward'] is False
    assert verdict['detail'].startswith('delegated_check_evidence_incomplete')


#: The shape the consumer in the plan's objective actually pins (cuioss-organization
#: ``reusable-maven-build.yml``): a push-deduplication ``gate``, a
#: ``covering-run-check`` (skipped on pull requests), a ``config`` job publishing the
#: resolved settings, the ``check-changes`` footprint decision, and the jobs it gates.
_REAL_CALLED_WORKFLOW = (
    'name: Maven Build (Reusable)\n'
    'on:\n'
    '  workflow_call:\n'
    '    inputs:\n'
    '      skip-on-docs-only:\n'
    '        default: true\n'
    'jobs:\n'
    '  gate:\n'
    '    runs-on: ubuntu-latest\n'
    '    outputs:\n'
    '      run: ${{ steps.decide.outputs.run }}\n'
    '  covering-run-check:\n'
    '    needs: gate\n'
    "    if: github.event_name == 'push' && needs.gate.outputs.run == 'false'\n"
    '    runs-on: ubuntu-latest\n'
    '    outputs:\n'
    '      rescue: ${{ steps.check.outputs.rescue }}\n'
    '  config:\n'
    '    needs: [gate, covering-run-check]\n'
    "    if: always() && (needs.gate.outputs.run == 'true' || needs.covering-run-check.outputs.rescue == 'true')\n"
    '    runs-on: ubuntu-latest\n'
    '    outputs:\n'
    '      skip-on-docs-only: ${{ steps.config.outputs.skip-on-docs-only }}\n'
    '  check-changes:\n'
    '    needs: config\n'
    "    if: always() && needs.config.outputs.skip-on-docs-only == 'true'\n"
    '    runs-on: ubuntu-latest\n'
    '    outputs:\n'
    '      should-build: ${{ steps.decide.outputs.should-build }}\n'
    '  build:\n'
    '    needs: [config, check-changes]\n'
    "    if: always() && needs.check-changes.outputs.should-build != 'false' && needs.config.result == 'success'\n"
    '    runs-on: ubuntu-latest\n'
    '  sonar-build:\n'
    '    needs: [config, check-changes]\n'
    "    if: always() && needs.check-changes.outputs.should-build != 'false' && needs.config.outputs.sonar-enabled == 'true'\n"
    '    runs-on: ubuntu-latest\n'
    '  conclusion:\n'
    '    if: always()\n'
    '    needs: [gate, config, check-changes, build, sonar-build]\n'
    '    runs-on: ubuntu-latest\n'
)


def _real_checks(**overrides: str) -> list[dict[str, str]]:
    results = {
        'build / gate': 'pass',
        'build / covering-run-check': 'skipping',
        'build / config': 'pass',
        'build / check-changes': 'pass',
        'build / build (21)': 'skipping',
        'build / build (25)': 'skipping',
        'build / sonar-build': 'skipping',
        'build / conclusion': 'pass',
    }
    for name, result in overrides.items():
        results[name.replace('__', ' / ').replace('_', '-')] = result
    return [{'name': name, 'result': result} for name, result in results.items()]


def test_the_real_reusable_workflow_shape_decides_a_docs_only_head(tmp_path: Path, monkeypatch) -> None:
    """The plumbing jobs publish outputs and skip on a PR; they must not refuse the decision.

    ``gate``/``covering-run-check``/``config`` declare outputs and are read by other
    jobs; ``config`` and ``check-changes`` also RUN on a docs-only head because the
    decision itself depends on them. Only the leaf jobs the footprint decision gates
    must be skipped.
    """
    repo = tmp_path / 'repo'
    _repo_with_a_delegation(repo)
    _patch_delegated(monkeypatch, called=_REAL_CALLED_WORKFLOW, rows=_real_checks())

    verdict = lane.cmd_sonar_stale_delta(_stale_args(pr_number='7', worktree=str(repo)))

    assert verdict['carry_forward'] is True
    assert verdict['decider_jobs'] == ['check-changes', 'config']
    assert verdict['gated_jobs'] == ['build', 'sonar-build']


def test_the_real_reusable_workflow_refuses_a_head_it_built(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / 'repo'
    _repo_with_a_delegation(repo)
    rows = _real_checks()
    for row in rows:
        if row['name'].startswith('build / build'):
            row['result'] = 'pass'
    _patch_delegated(monkeypatch, called=_REAL_CALLED_WORKFLOW, rows=rows)

    verdict = lane.cmd_sonar_stale_delta(_stale_args(pr_number='7', worktree=str(repo)))

    assert verdict['carry_forward'] is False
    assert verdict['detail'].startswith('delegated_gated_job_ran')


def test_a_condition_folded_over_lines_stays_undecidable(tmp_path: Path, monkeypatch) -> None:
    """The continuation may carry the gate's reference, so it is refused, not truncated."""
    called = _CALLED_WORKFLOW.replace(
        "    if: always() && needs.check-changes.outputs.should-build != 'false'\n",
        "    if: always() &&\n      needs.check-changes.outputs.should-build != 'false'\n",
    )
    repo = tmp_path / 'repo'
    _repo_with_a_delegation(repo)
    _patch_delegated(monkeypatch, called=called, rows=_checks())

    verdict = lane.cmd_sonar_stale_delta(_stale_args(pr_number='7', worktree=str(repo)))

    assert verdict['carry_forward'] is False
    assert verdict['detail'].startswith('delegated_rule_unreadable')
    assert 'more than one line' in verdict['detail']


def test_a_delegation_with_no_readable_caller_job_stays_undecidable(tmp_path: Path, monkeypatch) -> None:
    """A quoted job key is a job id this reader cannot place."""
    repo = tmp_path / 'repo'
    _repo_with_a_delegation(
        repo,
        'name: Maven Build\non:\n  pull_request:\njobs:\n  "build":\n'
        f'    uses: cuioss/cuioss-organization/.github/workflows/reusable-maven-build.yml@{_DELEGATED_REF}\n',
    )
    _patch_delegated(monkeypatch, rows=_checks())

    verdict = lane.cmd_sonar_stale_delta(_stale_args(pr_number='7', worktree=str(repo)))

    assert verdict['carry_forward'] is False
    assert verdict['detail'].startswith('delegated_rule_unreadable')


def test_an_unrelated_check_row_cannot_freeze_the_delegated_decision(tmp_path: Path, monkeypatch) -> None:
    """A review bot's pending row belongs to no job of the called workflow."""
    repo = tmp_path / 'repo'
    _repo_with_a_delegation(repo)
    _patch_delegated(monkeypatch, rows=_checks(extra=({'name': 'Sourcery review', 'result': 'pending'},)))

    verdict = lane.cmd_sonar_stale_delta(_stale_args(pr_number='7', worktree=str(repo)))

    assert verdict['carry_forward'] is True


def test_an_unpinned_delegation_stays_undecidable(tmp_path: Path, monkeypatch) -> None:
    """A moving ref is not the rule the CI applied to this head."""
    repo = tmp_path / 'repo'
    _repo_with_a_delegation(
        repo,
        'name: Maven Build\non:\n  pull_request:\njobs:\n  build:\n'
        '    uses: cuioss/cuioss-organization/.github/workflows/reusable-maven-build.yml@main\n',
    )
    _patch_delegated(monkeypatch, rows=_checks())

    verdict = lane.cmd_sonar_stale_delta(_stale_args(pr_number='7', worktree=str(repo)))

    assert verdict['carry_forward'] is False
    assert verdict['detail'].startswith('delegated_ref_unpinned')


def test_an_unreachable_delegated_workflow_stays_undecidable(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / 'repo'
    _repo_with_a_delegation(repo)
    _patch_delegated(monkeypatch, called=None, read_reason='repository_not_accessible', rows=_checks())

    verdict = lane.cmd_sonar_stale_delta(_stale_args(pr_number='7', worktree=str(repo)))

    assert verdict['carry_forward'] is False
    assert verdict['detail'].startswith('delegated_rule_unreachable')


def test_a_delegated_workflow_with_no_footprint_gate_stays_undecidable(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / 'repo'
    _repo_with_a_delegation(repo)
    _patch_delegated(monkeypatch, called='jobs:\n  build:\n    runs-on: ubuntu-latest\n', rows=_checks())

    verdict = lane.cmd_sonar_stale_delta(_stale_args(pr_number='7', worktree=str(repo)))

    assert verdict['carry_forward'] is False
    assert verdict['detail'].startswith('delegated_rule_unreadable')


def test_an_unreadable_check_run_list_stays_undecidable(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / 'repo'
    _repo_with_a_delegation(repo)
    _patch_delegated(monkeypatch, rows=None)

    verdict = lane.cmd_sonar_stale_delta(_stale_args(pr_number='7', worktree=str(repo)))

    assert verdict['carry_forward'] is False
    assert verdict['detail'].startswith('delegated_check_evidence_unreadable')


def test_a_delegating_shape_without_a_pull_request_number_stays_undecidable(tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / 'repo'
    _repo_with_a_delegation(repo)
    _patch_delegated(monkeypatch, rows=_checks())

    verdict = lane.cmd_sonar_stale_delta(_stale_args(worktree=str(repo)))

    assert verdict['carry_forward'] is False
    assert verdict['detail'].startswith('delegated_check_evidence_missing')


def test_a_workflow_holding_its_own_rule_still_decides_locally(tmp_path: Path) -> None:
    """The delegation branch never shadows a rule the checkout holds, even beside one."""
    import subprocess

    repo = tmp_path / 'repo'
    _repo_with_a_footprint_rule(repo)
    (repo / '.github' / 'workflows' / 'delegating.yml').write_text(_DELEGATION_WORKFLOW, encoding='utf-8')
    for args in (('add', '.'), ('commit', '-m', 'delegation'), ('rev-parse', 'HEAD')):
        completed = subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True, text=True)
    analysed = completed.stdout.strip()
    head = _commit(repo, 'doc/three.adoc')

    verdict = lane.cmd_sonar_stale_delta(
        _stale_args(analysis_revision=analysed, head_revision=head, worktree=str(repo))
    )

    assert verdict['carry_forward'] is True
    assert verdict['source'] == 'ci-workflow'


# =============================================================================
# the real-classifier twins of the two stubbed controls
# =============================================================================


def _git_init(root: Path) -> None:
    import subprocess

    for args in (
        ('init', '-b', 'main'),
        ('config', 'user.email', 'lane@example.com'),
        ('config', 'user.name', 'lane'),
        ('add', '.'),
        ('commit', '-m', 'base'),
    ):
        subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True)


def test_an_unreadable_footprint_rule_stays_undecidable_with_the_real_reader(tmp_path: Path) -> None:
    """The real workflow reader, not a stubbed classifier, answers `rule_unreadable`."""
    repo = tmp_path / 'repo'
    workflows = repo / '.github' / 'workflows'
    workflows.mkdir(parents=True)
    (workflows / 'broken.yml').write_bytes(b'\xff\xfe this is not utf-8\n')
    (repo / 'doc').mkdir()
    (repo / 'doc' / 'one.adoc').write_text('one\n', encoding='utf-8')
    _git_init(repo)
    analysed = _commit(repo, 'doc/two.adoc')
    head = _commit(repo, 'doc/three.adoc')

    verdict = lane.cmd_sonar_stale_delta(
        _stale_args(analysis_revision=analysed, head_revision=head, worktree=str(repo))
    )

    assert verdict['carry_forward'] is False
    assert verdict['reason'] == 'undecidable_read'
    assert verdict['detail'].startswith('rule_unreadable')


def test_an_unplaceable_path_stays_undecidable_with_the_real_classifier(tmp_path: Path) -> None:
    """The real classifier, not a stubbed row set, answers `buildable` for it."""
    repo = tmp_path / 'repo'
    _repo_with_a_footprint_rule(repo)
    analysed = _commit(repo, 'doc/two.adoc')
    (repo / 'mystery').mkdir()
    head = _commit(repo, 'mystery/file.xyz')

    verdict = lane.cmd_sonar_stale_delta(
        _stale_args(analysis_revision=analysed, head_revision=head, worktree=str(repo))
    )

    assert verdict['carry_forward'] is False
    assert verdict['reason'] == 'undecidable_read'
    assert verdict['buildable_paths'] == ['mystery/file.xyz']
