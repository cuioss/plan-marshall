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
    """Stub the six seams the decision reads, leaving the decision itself real."""
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


# =============================================================================
# PLAN-LB-172 D2 — the carry-forward binds itself, and the decision verb's edges
# =============================================================================
_CARRIED_REASON = (
    'carried_forward_unbuilt_delta: analysed bbbb != head aaaa; the delta since the analysed head is empty'
)


def test_a_carried_forward_read_reason_without_the_marker_is_refused() -> None:
    """The read's own output names the carry-forward; a bare figure must not pass."""
    verdict = cmd_sonar_gate(_gate_args(open_count='0', count_status_reason=_CARRIED_REASON))

    assert verdict['status'] == 'error', verdict
    assert verdict['error'] == 'carried_forward_unmarked', verdict


def test_a_carried_forward_gate_keeps_the_read_own_delta_reason() -> None:
    verdict = cmd_sonar_gate(
        _gate_args(
            open_count='0',
            carried_forward=True,
            carried_forward_analysis_revision=_ANALYSED,
            carried_forward_head_revision=_HEAD,
            count_status_reason=_CARRIED_REASON,
        )
    )

    assert verdict['merge_allowed'] is True, verdict
    assert 'empty' in verdict['reason'], verdict


def test_a_short_and_a_full_sha_of_one_commit_are_one_revision() -> None:
    """A prefix and its full object name describe one commit, never a carry-forward pair."""
    full = 'abcdef1' + '0' * 33

    verdict = cmd_sonar_gate(
        _gate_args(
            open_count='0',
            carried_forward=True,
            carried_forward_analysis_revision='abcdef1',
            carried_forward_head_revision=full,
        )
    )

    assert verdict['status'] == 'error', verdict
    assert verdict['error'] == 'carried_forward_revisions_equal', verdict


def test_a_revision_that_is_not_a_hex_object_name_is_refused() -> None:
    verdict = cmd_sonar_gate(
        _gate_args(
            open_count='0',
            carried_forward=True,
            carried_forward_analysis_revision='HEAD~1',
            carried_forward_head_revision=_HEAD,
        )
    )

    assert verdict['status'] == 'error', verdict
    assert verdict['error'] == 'revision_format_invalid', verdict


def _real_repo(tmp_path: Path) -> Path:
    """A one-commit repository, so the git-backed guards read real state."""
    import subprocess

    repo = tmp_path / 'repo'
    repo.mkdir()
    for args in (
        ('init', '-b', 'main'),
        ('config', 'user.email', 'lane@example.com'),
        ('config', 'user.name', 'lane'),
    ):
        subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True)
    (repo / 'a.txt').write_text('a\n', encoding='utf-8')
    for args in (('add', '.'), ('commit', '-m', 'base')):
        subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True)
    return repo


def test_the_dirty_guard_sees_an_assume_unchanged_edit(tmp_path: Path) -> None:
    """`git status` hides an assume-unchanged edit, and the rule it would supply is not the head's."""
    import subprocess

    repo = _real_repo(tmp_path)
    subprocess.run(
        ['git', '-C', str(repo), 'update-index', '--assume-unchanged', 'a.txt'], check=True, capture_output=True
    )
    (repo / 'a.txt').write_text('changed\n', encoding='utf-8')

    assert lane._worktree_is_clean(repo) is False


def test_the_dirty_guard_sees_an_untracked_file_hidden_by_config(tmp_path: Path) -> None:
    """`status.showUntrackedFiles=no` must not make an untracked rule file invisible."""
    import subprocess

    repo = _real_repo(tmp_path)
    subprocess.run(
        ['git', '-C', str(repo), 'config', 'status.showUntrackedFiles', 'no'], check=True, capture_output=True
    )
    (repo / 'new.yml').write_text('x\n', encoding='utf-8')

    assert lane._worktree_is_clean(repo) is False


def test_the_ignored_input_guard_covers_the_whole_ci_tree(tmp_path: Path) -> None:
    """An ignored file under `.github/` can carry the rule as surely as one under workflows."""
    repo = _real_repo(tmp_path)
    (repo / '.gitignore').write_text('.github/secret.yml\n', encoding='utf-8')
    (repo / '.github').mkdir()
    (repo / '.github' / 'secret.yml').write_text('skip-on-docs-only: true\n', encoding='utf-8')

    assert lane._ignored_workflow_inputs(repo)


def test_a_head_that_widens_its_own_paths_ignore_is_not_carried_forward(monkeypatch) -> None:
    """A delta carrying the CI rule itself is never a delta the rule can excuse."""
    _patch_delta(
        monkeypatch,
        paths=('.github/workflows/ci.yml', 'doc/one.adoc'),
        rows=[
            {'path': '.github/workflows/ci.yml', 'kind': 'docs-only'},
            {'path': 'doc/one.adoc', 'kind': 'docs-only'},
        ],
    )

    verdict = lane.cmd_sonar_stale_delta(_stale_args())

    assert verdict['carry_forward'] is False, verdict
    assert verdict['detail'].startswith('rule_changed'), verdict


def test_a_workflow_symlink_out_of_the_checkout_is_not_followed(tmp_path: Path) -> None:
    """A tracked symlink is not the checkout's own rule."""
    outside = tmp_path / 'outside.yml'
    outside.write_text('skip-on-docs-only: true\n', encoding='utf-8')
    repo = tmp_path / 'repo'
    (repo / '.github' / 'workflows').mkdir(parents=True)
    (repo / '.github' / 'workflows' / 'ci.yml').symlink_to(outside)

    assert lane._iter_workflow_files(repo) == []


def test_a_delegating_consumers_delta_is_not_carried_forward(tmp_path: Path) -> None:
    """The CI's rule lives in a reusable workflow this checkout does not hold.

    Substituting the architecture's documentation surfaces would decide the delta by
    a rule the CI never applied, so the delta stays undecidable: the delegation is
    named instead of a skip being guessed.
    """
    repo = tmp_path / 'repo'
    (repo / '.github' / 'workflows').mkdir(parents=True)
    (repo / '.github' / 'workflows' / 'ci.yml').write_text(
        'name: CI\nskip-on-docs-only: true\njobs:\n  verify:\n    uses: example/reusable.yml@0123456789abcdef\n',
        encoding='utf-8',
    )
    (repo / 'doc').mkdir()
    (repo / 'doc' / 'one.adoc').write_text('one\n', encoding='utf-8')
    _git_init(repo)
    analysed = _commit(repo, 'doc/two.adoc')
    head = _commit(repo, 'doc/three.adoc')

    verdict = lane.cmd_sonar_stale_delta(
        _stale_args(analysis_revision=analysed, head_revision=head, worktree=str(repo))
    )

    assert verdict['carry_forward'] is False, verdict
    assert verdict['reason'] == 'undecidable_read', verdict
    assert verdict['detail'].startswith('rule_unreadable'), verdict
    assert 'delegates' in verdict['detail'], verdict


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


def test_the_lane_text_states_the_carry_forward_rule() -> None:
    section = _section('## 6. Pull request and reviews')

    assert 'sonar-stale-delta' in section, '§ 6 must name the decision verb'
    assert 'carried_forward_unbuilt_delta' in section, '§ 6 must name the distinct reason'
    assert '--analysed-revision' in section, '§ 6 must name the read licence'
    assert 'retry the read, and if it stays undecidable' in section, '§ 6 must keep the general stop'
    assert 'NOT in that retry class' in section, '§ 6 must exempt a refused stale read from the retry'


# The delegated branch (a consumer whose CI delegates its build to a reusable
# workflow) is decided here: the rule the CI applied is not in this checkout, so the
# delta stays undecidable and the delegation is named. No architecture substitute.


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
