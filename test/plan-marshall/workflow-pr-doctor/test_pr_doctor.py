# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for pr_doctor.py - PR Doctor handoff parsing and validation.

Tier 2 (direct import) tests with 3 subprocess tests for CLI plumbing.
"""

import io
import json
import sys
from contextlib import redirect_stdout
from unittest.mock import MagicMock, patch

import pytest

from conftest import get_script_path, run_script

# Import toon_parser - conftest sets up PYTHONPATH

# Script under test (for subprocess CLI plumbing tests)
SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-pr-doctor', 'pr_doctor.py')

# Tier 2 direct imports — conftest sets up PYTHONPATH for cross-skill imports
import pr_doctor  # type: ignore[import-not-found]  # noqa: E402
from pr_doctor import (  # type: ignore[import-not-found]  # noqa: E402
    check_attempt,
    diagnose_pr,
    forward_project_dir,
    merge_handoff_with_params,
    run_child_cmd,
    set_project_dir,
    validate_handoff,
)
from triage_helpers import make_error, parse_json_arg  # type: ignore[import-not-found]  # noqa: E402


def _parse_and_merge(handoff_json, pr=None, checks=None, auto_fix=None, max_fix_attempts=None, wait=None):
    """Helper to parse JSON handoff and merge with params, returning result dict."""
    handoff, rc = parse_json_arg(handoff_json, '--handoff')
    if rc:
        return rc
    if not isinstance(handoff, dict):
        return make_error('Handoff must be a JSON object')
    warnings = validate_handoff(handoff)

    merged = merge_handoff_with_params(
        handoff,
        pr=pr,
        checks=checks,
        auto_fix=auto_fix,
        max_fix_attempts=max_fix_attempts,
        wait=wait,
    )

    return {
        'merged': merged,
        'validation': {
            'valid': len(warnings) == 0,
            'warnings': warnings,
        },
        'status': 'success',
    }


# =============================================================================
# parse-handoff (direct import)
# =============================================================================


def test_full_handoff():
    """Test parsing a complete handoff structure."""
    handoff = {
        'artifacts': {
            'pr_number': 123,
            'branch': 'feature/my-feature',
            'commit_hash': 'abc123',
            'plan_id': 'my-plan',
        },
        'decisions': {
            'auto_fix': True,
            'checks': 'all',
            'skip_sonar': False,
        },
        'constraints': {
            'max_fix_attempts': 3,
            'protected_files': ['README.md'],
        },
    }

    result = _parse_and_merge(json.dumps(handoff))

    assert result['status'] == 'success'
    merged = result['merged']
    assert merged['pr_number'] == 123
    assert merged['branch'] == 'feature/my-feature'
    assert merged['checks'] == 'all'
    assert merged['auto_fix']
    assert merged['max_fix_attempts'] == 3
    assert result['validation']['valid']
    assert len(result['validation']['warnings']) == 0


def test_minimal_handoff():
    """Test parsing a minimal handoff with defaults."""
    handoff = {'artifacts': {'pr_number': 42}}

    result = _parse_and_merge(json.dumps(handoff))

    merged = result['merged']
    assert merged['pr_number'] == 42
    assert merged['checks'] == 'all'
    assert merged['auto_fix'] is False
    assert merged['max_fix_attempts'] == 3


def test_explicit_params_override_handoff():
    """Test that explicit params override handoff values."""
    handoff = {
        'artifacts': {'pr_number': 100},
        'decisions': {'checks': 'all', 'auto_fix': False},
    }

    result = _parse_and_merge(json.dumps(handoff), pr=456, checks='build', auto_fix=True)

    merged = result['merged']
    assert merged['pr_number'] == 456
    assert merged['checks'] == 'build'
    assert merged['auto_fix']


def test_empty_handoff():
    """Test parsing empty handoff uses defaults."""
    result = _parse_and_merge('{}')

    merged = result['merged']
    assert merged['pr_number'] is None
    assert merged['checks'] == 'all'
    assert merged['auto_fix'] is False


def test_invalid_json():
    """Test error on invalid JSON."""
    result = _parse_and_merge('not-json')

    assert result['status'] == 'error'
    assert 'Invalid' in result['error']
    assert 'JSON' in result['error']


def test_handoff_not_dict():
    """Test error when handoff is not a dict."""
    result = _parse_and_merge('[1,2,3]')

    assert result['status'] == 'error'
    assert 'object' in result['error']


def test_validation_warns_on_bad_pr_number():
    """Test validation warns on invalid PR number."""
    handoff = {'artifacts': {'pr_number': -1}}

    result = _parse_and_merge(json.dumps(handoff))

    assert result['validation']['valid'] is False
    assert any('pr_number' in w for w in result['validation']['warnings'])


def test_validation_warns_on_bad_checks():
    """Test validation warns on invalid checks value."""
    handoff = {'decisions': {'checks': 'invalid'}}

    result = _parse_and_merge(json.dumps(handoff))

    assert result['validation']['valid'] is False
    assert any('checks' in w for w in result['validation']['warnings'])


def test_validation_warns_on_unknown_keys():
    """Test validation warns on unknown top-level keys."""
    handoff = {'artifacts': {}, 'extra_key': 'value'}

    result = _parse_and_merge(json.dumps(handoff))

    assert any('Unknown' in w for w in result['validation']['warnings'])


def test_validation_warns_on_bad_auto_fix_type():
    """Test validation warns when auto_fix is not a bool."""
    handoff = {'decisions': {'auto_fix': 'yes'}}

    result = _parse_and_merge(json.dumps(handoff))

    assert any('auto_fix' in w for w in result['validation']['warnings'])


def test_validation_warns_on_bad_max_fix_attempts():
    """Test validation warns when max_fix_attempts is not a positive int."""
    handoff = {'constraints': {'max_fix_attempts': 0}}

    result = _parse_and_merge(json.dumps(handoff))

    assert any('max_fix_attempts' in w for w in result['validation']['warnings'])


def test_validation_warns_on_bad_protected_files():
    """Test validation warns when protected_files contains non-strings."""
    handoff = {'constraints': {'protected_files': [1, 2]}}

    result = _parse_and_merge(json.dumps(handoff))

    assert any('protected_files' in w for w in result['validation']['warnings'])


def test_max_fix_attempts_override():
    """Test that max_fix_attempts param overrides handoff."""
    handoff = {'constraints': {'max_fix_attempts': 5}}

    result = _parse_and_merge(json.dumps(handoff), max_fix_attempts=10)

    assert result['merged']['max_fix_attempts'] == 10


def test_auto_fix_not_provided_uses_handoff():
    """Test that omitting auto_fix defers to handoff value."""
    handoff = {'decisions': {'auto_fix': False}}

    result = _parse_and_merge(json.dumps(handoff))

    assert result['merged']['auto_fix'] is False


def test_auto_fix_not_provided_defaults_false():
    """Test that omitting auto_fix without handoff defaults to False."""
    handoff = {'artifacts': {'pr_number': 1}}

    result = _parse_and_merge(json.dumps(handoff))

    assert result['merged']['auto_fix'] is False


def test_no_wait_overrides_handoff():
    """Test that wait=False overrides handoff wait=true."""
    handoff = {'decisions': {'wait': True}}

    result = _parse_and_merge(json.dumps(handoff), wait=False)

    assert result['merged']['wait'] is False


def test_wait_defaults_true():
    """Test that wait defaults to True without flags."""
    handoff = {'artifacts': {'pr_number': 1}}

    result = _parse_and_merge(json.dumps(handoff))

    assert result['merged']['wait']


def test_wait_override_true():
    """Test that wait=True overrides handoff wait=false."""
    handoff = {'decisions': {'wait': False}}

    result = _parse_and_merge(json.dumps(handoff), wait=True)

    assert result['merged']['wait']


# =============================================================================
# track-attempt (direct import)
# =============================================================================


def test_first_attempt_proceeds():
    """Test that the first attempt (current=0) should proceed."""
    result = check_attempt('build', 0, 3)

    assert result['status'] == 'success'
    assert result['proceed']
    assert result['attempt'] == 1
    assert result['remaining'] == 2
    assert result['category'] == 'build'


def test_last_attempt_proceeds():
    """Test that the last attempt (current=2 with max=3) proceeds."""
    result = check_attempt('sonar', 2, 3)

    assert result['proceed']
    assert result['attempt'] == 3
    assert result['remaining'] == 0


def test_exceeds_max_stops():
    """Test that exceeding max attempts stops."""
    result = check_attempt('reviews', 3, 3)

    assert result['proceed'] is False
    assert result['attempt'] == 4
    assert result['remaining'] == 0
    assert 'reached max' in result['reason']


def test_custom_max_attempts():
    """Test with custom max-attempts value."""
    result = check_attempt('build', 4, 5)

    assert result['proceed']
    assert result['attempt'] == 5
    assert result['remaining'] == 0


def test_default_max_attempts():
    """Test that default max-attempts is 3."""
    result = check_attempt('build', 0, 3)

    assert result['max_attempts'] == 3


# =============================================================================
# diagnose (direct import)
# =============================================================================


def test_all_pass():
    """Test diagnosis with no issues."""
    result = diagnose_pr(build_status='success')

    assert result['status'] == 'success'
    assert result['overall'] == 'pass'
    assert result['build_status'] == 'PASS'
    assert result['review_comments'] == 0
    assert result['sonar_issues'] == 0
    assert len(result['issues']) == 0


def test_build_failure():
    """Test diagnosis with build failure."""
    result = diagnose_pr(
        build_status='failure',
        build_failures=[{'step': 'test', 'message': '3 tests failed'}],
    )

    assert result['overall'] == 'fail'
    assert result['build_status'] == 'FAIL'
    assert any(i['category'] == 'build' for i in result['issues'])
    assert any('build' in a.lower() for a in result['recommended_actions'])


def test_review_comments():
    """Test diagnosis with unresolved review comments."""
    result = diagnose_pr(
        review_comments=[
            {'priority': 'high', 'body': 'Fix this'},
            {'priority': 'low', 'body': 'Nit'},
        ]
    )

    assert result['overall'] == 'fail'
    assert result['review_comments'] == 2
    review_issue = next(i for i in result['issues'] if i['category'] == 'reviews')
    assert review_issue['severity'] == 'high'


def test_sonar_issues():
    """Test diagnosis with Sonar issues."""
    result = diagnose_pr(
        sonar_issues=[
            {'severity': 'BLOCKER', 'rule': 'java:S1234'},
            {'severity': 'MAJOR', 'rule': 'java:S5678'},
            {'severity': 'MINOR', 'rule': 'java:S9012'},
        ]
    )

    assert result['sonar_issues'] == 3
    sonar_issue = next(i for i in result['issues'] if i['category'] == 'sonar')
    assert sonar_issue['severity'] == 'high'


def test_combined_diagnosis():
    """Test diagnosis with all three categories."""
    result = diagnose_pr(
        build_status='failure',
        build_failures=[{'step': 'compile', 'message': 'error'}],
        review_comments=[{'priority': 'medium'}],
        sonar_issues=[{'severity': 'MAJOR'}],
    )

    assert result['overall'] == 'fail'
    categories = {i['category'] for i in result['issues']}
    assert categories == {'build', 'reviews', 'sonar'}
    assert len(result['recommended_actions']) == 3


def test_build_pass_with_review_issues():
    """Test diagnosis with passing build but unresolved review comments (#52)."""
    result = diagnose_pr(
        build_status='success',
        review_comments=[{'priority': 'high', 'body': 'Fix this'}],
    )

    assert result['overall'] == 'fail'
    assert result['build_status'] == 'PASS'
    assert result['review_comments'] == 1
    categories = {i['category'] for i in result['issues']}
    assert 'reviews' in categories
    assert 'build' not in categories


def test_no_inputs_is_pass():
    """Test that diagnose with no inputs reports pass."""
    result = diagnose_pr()

    assert result['overall'] == 'pass'
    assert result['build_status'] == 'UNKNOWN'


def test_sonar_severity_breakdown():
    """Test that Sonar diagnosis includes severity breakdown."""
    result = diagnose_pr(
        sonar_issues=[
            {'severity': 'CRITICAL'},
            {'severity': 'CRITICAL'},
            {'severity': 'MAJOR'},
        ]
    )

    sonar_issue = next(i for i in result['issues'] if i['category'] == 'sonar')
    assert sonar_issue['breakdown']['CRITICAL'] == 2
    assert sonar_issue['breakdown']['MAJOR'] == 1


# =============================================================================
# diagnose build severity (#46)
# =============================================================================


def test_lint_failure_is_medium():
    """Lint failure should be medium severity, not high."""
    result = diagnose_pr(
        build_status='failure',
        build_failures=[{'step': 'lint', 'message': 'ESLint errors'}],
    )

    build_issue = next(i for i in result['issues'] if i['category'] == 'build')
    assert build_issue['severity'] == 'medium'


def test_compile_failure_is_high():
    """Compile failure should be high severity."""
    result = diagnose_pr(
        build_status='failure',
        build_failures=[{'step': 'compile', 'message': 'Compilation error'}],
    )

    build_issue = next(i for i in result['issues'] if i['category'] == 'build')
    assert build_issue['severity'] == 'high'


def test_unknown_step_defaults_to_high():
    """Unknown step type should default to high severity."""
    result = diagnose_pr(
        build_status='failure',
        build_failures=[{'step': 'unknown', 'message': 'Something failed'}],
    )

    build_issue = next(i for i in result['issues'] if i['category'] == 'build')
    assert build_issue['severity'] == 'high'


# =============================================================================
# diagnose edge cases
# =============================================================================


def test_build_status_none_with_failures_skips_build():
    """When build_status is None, build failures are ignored."""
    result = diagnose_pr(
        build_failures=[{'step': 'test', 'message': 'fails'}],
    )

    assert result['build_status'] == 'UNKNOWN'
    build_issues = [i for i in result['issues'] if i['category'] == 'build']
    assert len(build_issues) == 0


# =============================================================================
# diagnose input validation for malformed data
# =============================================================================


def test_diagnose_build_failures_missing_keys():
    """Test diagnose handles build failures without expected keys."""
    result = diagnose_pr(
        build_status='failure',
        build_failures=[{'unexpected_key': 'value'}],
    )

    assert result['status'] == 'success'
    build_issue = next(i for i in result['issues'] if i['category'] == 'build')
    assert build_issue['step'] == 'unknown'
    assert build_issue['detail'] == 'Build failure'


def test_diagnose_review_comments_non_dict_entries():
    """Test diagnose handles non-dict entries in review comments array."""
    result = diagnose_pr(
        review_comments=[
            {'priority': 'high'},
            'not-a-dict',
            42,
        ]
    )

    assert result['status'] == 'success'
    assert result['review_comments'] == 3


def test_diagnose_sonar_issues_non_dict_entries():
    """Test diagnose handles non-dict entries in sonar issues array."""
    result = diagnose_pr(
        sonar_issues=[
            {'severity': 'MAJOR'},
            'invalid-entry',
        ]
    )

    assert result['status'] == 'success'
    assert result['sonar_issues'] == 2


def test_diagnose_build_failures_non_dict_entries():
    """Test diagnose handles non-dict entries in build failures array."""
    result = diagnose_pr(
        build_status='failure',
        build_failures=['not-a-dict', 42],
    )

    assert result['status'] == 'success'
    for issue in result['issues']:
        if issue['category'] == 'build':
            assert issue['step'] == 'unknown'


# =============================================================================
# parse-handoff skip_sonar field (#31)
# =============================================================================


def test_skip_sonar_true():
    """Test that skip_sonar is extracted from handoff decisions."""
    handoff = {'decisions': {'skip_sonar': True}}

    result = _parse_and_merge(json.dumps(handoff))

    assert result['merged']['skip_sonar']


def test_skip_sonar_defaults_false():
    """Test that skip_sonar defaults to False when not in handoff."""
    handoff = {'artifacts': {'pr_number': 1}}

    result = _parse_and_merge(json.dumps(handoff))

    assert result['merged']['skip_sonar'] is False


# =============================================================================
# parse-handoff automated_review field (#32)
# =============================================================================


def test_automated_review_true():
    """Test that automated_review is extracted from handoff decisions."""
    handoff = {'decisions': {'automated_review': True}}

    result = _parse_and_merge(json.dumps(handoff))

    assert result['merged']['automated_review']


def test_automated_review_defaults_false():
    """Test that automated_review defaults to False when not in handoff."""
    handoff = {'artifacts': {'pr_number': 1}}

    result = _parse_and_merge(json.dumps(handoff))

    assert result['merged']['automated_review'] is False


# =============================================================================
# parse-handoff semantic validation (#41)
# =============================================================================


def test_checks_sonar_with_skip_sonar_warns():
    """checks=sonar + skip_sonar=true is contradictory — should warn."""
    handoff = {'decisions': {'checks': 'sonar', 'skip_sonar': True}}

    result = _parse_and_merge(json.dumps(handoff))

    warnings = result['validation']['warnings']
    assert any('sonar' in w.lower() and ('skip' in w.lower() or 'contradict' in w.lower()) for w in warnings), (
        f'Expected contradiction warning about sonar, got: {warnings}'
    )


# =============================================================================
# Subprocess (Tier 3) tests — CLI plumbing only
# =============================================================================


def run_doctor_script(args: list) -> tuple:
    """Run pr_doctor.py with args and return (stdout, stderr, returncode)."""
    result = run_script(SCRIPT_PATH, *args)
    return result.stdout, result.stderr, result.returncode


def test_no_subcommand():
    """Test error when no subcommand provided."""
    _, stderr, code = run_doctor_script([])

    assert code != 0


def test_help():
    """Test help output."""
    stdout, _, code = run_doctor_script(['--help'])

    assert code == 0
    assert 'parse-handoff' in stdout
    assert 'track-attempt' in stdout
    assert 'diagnose' in stdout


def test_invalid_category():
    """Test that invalid category is rejected by argparse."""
    _, stderr, code = run_doctor_script(
        [
            'track-attempt',
            '--category',
            'invalid',
            '--current',
            '0',
        ]
    )

    assert code != 0
    assert 'invalid' in stderr


# =============================================================================
# --project-dir forwarding tests (TASK-7/8)
#
# The contract is:
#   - main() pre-parses --project-dir via ci_base.extract_project_dir,
#     strips it from argv, and stores the value in _PROJECT_DIR.
#   - forward_project_dir(cmd) appends --project-dir <value> when set,
#     and is a no-op when _PROJECT_DIR is None (default inherited cwd).
#   - run_child_cmd(cmd, **kwargs) routes every subprocess invocation
#     through forward_project_dir — this is the monkey-patch target.
# =============================================================================


@pytest.fixture
def clean_project_dir():
    """Reset module project-dir state before and after each test."""
    set_project_dir(None)
    yield
    set_project_dir(None)


@pytest.fixture
def capture_run():
    """Patch pr_doctor.subprocess.run with a MagicMock for the test duration."""
    mock = MagicMock(return_value=MagicMock(returncode=0, stdout='', stderr=''))
    with patch.object(pr_doctor.subprocess, 'run', mock):
        yield mock


# -- forward_project_dir unit-level behaviour --------------------------


def test_forward_noop_when_unset(clean_project_dir):
    """Absent --project-dir, forward_project_dir must not mutate cmd."""
    set_project_dir(None)
    cmd = ['ci', 'pr', 'checks', '--pr', '123']

    forwarded = forward_project_dir(cmd)

    assert forwarded == cmd
    assert '--project-dir' not in forwarded


def test_forward_appends_when_set(clean_project_dir):
    """When set, forward appends --project-dir <value> at the tail."""
    set_project_dir('/tmp/worktree')
    cmd = ['ci', 'pr', 'checks', '--pr', '123']

    forwarded = forward_project_dir(cmd)

    assert forwarded[-2:] == ['--project-dir', '/tmp/worktree']
    assert '--project-dir' not in cmd


def test_forward_preserves_list_identity(clean_project_dir):
    """forward_project_dir returns a new list, never mutates input."""
    set_project_dir('/tmp/worktree')
    cmd = ['build', 'run']

    forwarded = forward_project_dir(cmd)

    assert forwarded is not cmd
    assert cmd == ['build', 'run']


# -- run_child_cmd: subprocess.run monkey-patch ------------------------


def test_run_child_cmd_forwards_when_set(clean_project_dir, capture_run):
    """Every child script invocation must receive --project-dir."""
    set_project_dir('/tmp/worktree')
    child_cmds = [
        ['ci', 'pr', 'checks', '--pr', '123'],
        ['build', 'run', '--command-args', 'verify'],
        ['sonar', 'issues', 'list'],
        ['github', 'pr', 'review'],
        ['gitlab', 'mr', 'discussions'],
        ['architecture', 'resolve', '--command', 'compile'],
    ]

    for cmd in child_cmds:
        run_child_cmd(cmd)

    assert capture_run.call_count == len(child_cmds)
    for call in capture_run.call_args_list:
        forwarded = call.args[0]
        assert '--project-dir' in forwarded, f'missing flag in {forwarded}'
        idx = forwarded.index('--project-dir')
        assert forwarded[idx + 1] == '/tmp/worktree'


def test_run_child_cmd_noop_when_unset(clean_project_dir, capture_run):
    """Default (no --project-dir) must not append the flag."""
    set_project_dir(None)
    child_cmds = [
        ['ci', 'pr', 'checks', '--pr', '123'],
        ['build', 'run', '--command-args', 'verify'],
        ['sonar', 'issues', 'list'],
        ['github', 'pr', 'review'],
        ['gitlab', 'mr', 'discussions'],
        ['architecture', 'resolve', '--command', 'compile'],
    ]

    for cmd in child_cmds:
        run_child_cmd(cmd)

    assert capture_run.call_count == len(child_cmds)
    for call in capture_run.call_args_list:
        forwarded = call.args[0]
        assert '--project-dir' not in forwarded, f'unexpected flag in {forwarded}'


def test_run_child_cmd_passes_kwargs(clean_project_dir, capture_run):
    """run_child_cmd must transparently forward subprocess.run kwargs."""
    set_project_dir('/tmp/worktree')

    run_child_cmd(['ci', 'pr'], capture_output=True, text=True, check=False)

    assert capture_run.call_count == 1
    kwargs = capture_run.call_args.kwargs
    assert kwargs.get('capture_output')
    assert kwargs.get('text')
    assert kwargs.get('check') is False


# -- main() argv pre-parsing: space and equals forms -------------------


def _run_main_with_argv(argv):
    """Run pr_doctor.main() under patched argv with diagnose stubbed out."""
    # Stub cmd_diagnose to return quickly without doing real work — we only
    # care about what main() does to argv and _PROJECT_DIR before dispatch.
    stub = MagicMock(return_value={'status': 'success', 'overall': 'pass'})
    with patch.object(pr_doctor, 'cmd_diagnose', stub), patch.object(sys, 'argv', argv):
        pr_doctor.main()
    return stub


def test_main_strips_project_dir_space_form(clean_project_dir, capture_run):
    """main() must pre-parse --project-dir PATH and store it."""
    argv = ['pr_doctor.py', '--project-dir', '/tmp/worktree', 'diagnose', '--build-status', 'success']

    _run_main_with_argv(argv)

    assert pr_doctor.get_project_dir() == '/tmp/worktree'
    assert '--project-dir' not in sys.argv
    assert '/tmp/worktree' not in sys.argv


def test_main_strips_project_dir_equals_form(clean_project_dir, capture_run):
    """main() must also accept --project-dir=PATH."""
    argv = ['pr_doctor.py', '--project-dir=/tmp/worktree', 'diagnose', '--build-status', 'success']

    _run_main_with_argv(argv)

    assert pr_doctor.get_project_dir() == '/tmp/worktree'
    assert '--project-dir' not in sys.argv
    assert not any(a.startswith('--project-dir') for a in sys.argv)


def test_main_without_project_dir_leaves_unset(clean_project_dir, capture_run):
    """Absent the flag, _PROJECT_DIR must remain None."""
    argv = ['pr_doctor.py', 'diagnose', '--build-status', 'success']

    _run_main_with_argv(argv)

    assert pr_doctor.get_project_dir() is None


# -- Two-state ``--plan-id`` / ``--project-dir`` routing contract ----


def test_main_plan_id_resolves_via_manage_status(clean_project_dir, capture_run):
    """Router-level --plan-id auto-resolves to the persisted worktree path."""
    import resolve_project_dir as _routing  # type: ignore[import-not-found]

    argv = [
        'pr_doctor.py',
        '--plan-id',
        'task-routing-canonical',
        'diagnose',
        '--build-status',
        'success',
    ]

    with patch.object(
        _routing,
        '_query_worktree_path',
        return_value=(True, '/tmp/wt-pr-doctor'),
    ):
        _run_main_with_argv(argv)

    assert pr_doctor.get_project_dir() == '/tmp/wt-pr-doctor'


def test_main_emits_mutually_exclusive_error_on_both_flags(clean_project_dir):
    """Both router-level --plan-id and --project-dir → mutually_exclusive_args."""
    argv = [
        'pr_doctor.py',
        '--plan-id',
        'task-routing-canonical',
        '--project-dir',
        '/tmp/explicit',
        'diagnose',
        '--build-status',
        'success',
    ]

    # main() may or may not propagate the SystemExit depending on how
    # extract_routing_args handles the error — it calls sys.exit(2) directly.
    buf = io.StringIO()
    with patch.object(sys, 'argv', argv):
        with pytest.raises(SystemExit) as ctx:
            with redirect_stdout(buf):
                pr_doctor.main()

    assert ctx.value.code == 2
    assert 'mutually_exclusive_args' in buf.getvalue()


def test_main_plan_id_use_worktree_false_falls_back_to_main_checkout(clean_project_dir, capture_run):
    """``use_worktree=false`` resolution surfaces the main checkout root."""
    import resolve_project_dir as _routing  # type: ignore[import-not-found]

    argv = [
        'pr_doctor.py',
        '--plan-id',
        'task-routing-canonical',
        'diagnose',
        '--build-status',
        'success',
    ]

    with (
        patch.object(_routing, '_query_worktree_path', return_value=(False, '')),
        patch.object(_routing, '_main_checkout_root', return_value='/tmp/main-stub'),
    ):
        _run_main_with_argv(argv)

    assert pr_doctor.get_project_dir() == '/tmp/main-stub'
