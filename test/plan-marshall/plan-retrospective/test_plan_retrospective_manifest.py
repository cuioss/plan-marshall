# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``check-manifest-consistency.py`` and the manifest-aware
forward in ``check-artifact-consistency.py``.
"""


from __future__ import annotations

from _plan_retrospective_manifest_fixtures import (
    MANIFEST_SCRIPT,
    _check_by_name,
    _finding_by_code,
    _manifest_default,
    _manifest_early_terminate,
    _manifest_tests_only,
    _setup_plan_with_manifest,
    _write_diff,
)

from conftest import run_script  # noqa: E402

# =============================================================================
# Rule M3: tests-only verification
# =============================================================================


class TestTestsOnlyRule:
    def test_pass_when_only_test_files(self, tmp_path, monkeypatch):
        plan_id, _ = _setup_plan_with_manifest(tmp_path, monkeypatch, manifest_body=_manifest_tests_only())
        diff = _write_diff(
            tmp_path,
            [
                'test/foo/test_bar.py',
                'tests/baz/baz_test.py',
                'src/main/java/FooTest.java',
                'src/web/foo.test.js',
                'src/web/bar.spec.js',
            ],
        )
        result = run_script(
            MANIFEST_SCRIPT,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--diff-file',
            str(diff),
        )
        data = result.toon()
        check = _check_by_name(data['checks'], 'tests_only_diff')
        assert check is not None
        assert check['status'] == 'pass'

    def test_fail_when_production_code_present(self, tmp_path, monkeypatch):
        plan_id, _ = _setup_plan_with_manifest(tmp_path, monkeypatch, manifest_body=_manifest_tests_only())
        diff = _write_diff(
            tmp_path,
            ['test/foo/test_bar.py', 'src/main/foo/bar.py'],
        )
        result = run_script(
            MANIFEST_SCRIPT,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--diff-file',
            str(diff),
        )
        data = result.toon()
        check = _check_by_name(data['checks'], 'tests_only_diff')
        assert check is not None
        assert check['status'] == 'fail'
        finding = _finding_by_code(data['findings'], 'tests_only_diff_violation')
        assert finding is not None
        assert 'src/main/foo/bar.py' in finding['culprits']


# =============================================================================
# Rule M4: branch-cleanup paired with changes
# =============================================================================


class TestBranchCleanupRule:
    def test_pass_when_branch_cleanup_paired_with_changes(self, tmp_path, monkeypatch):
        plan_id, _ = _setup_plan_with_manifest(tmp_path, monkeypatch, manifest_body=_manifest_default())
        diff = _write_diff(tmp_path, ['src/foo/bar.py'])
        result = run_script(
            MANIFEST_SCRIPT,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--diff-file',
            str(diff),
        )
        data = result.toon()
        check = _check_by_name(data['checks'], 'branch_cleanup_changes')
        assert check is not None
        assert check['status'] == 'pass'

    def test_fail_when_branch_cleanup_with_only_bookkeeping_changes(self, tmp_path, monkeypatch):
        # The raw diff is non-empty but every path is bookkeeping, so the rule
        # still has real diff data to evaluate and must fail on the empty
        # filtered set.
        plan_id, _ = _setup_plan_with_manifest(tmp_path, monkeypatch, manifest_body=_manifest_default())
        diff = _write_diff(tmp_path, ['.plan/local/plans/foo/status.json'])
        result = run_script(
            MANIFEST_SCRIPT,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--diff-file',
            str(diff),
        )
        data = result.toon()
        check = _check_by_name(data['checks'], 'branch_cleanup_changes')
        assert check is not None
        assert check['status'] == 'fail'
        finding = _finding_by_code(data['findings'], 'branch_cleanup_without_changes')
        assert finding is not None
        assert finding['severity'] == 'info'

    def test_skip_when_diff_base_is_unknown(self, tmp_path, monkeypatch):
        # No --diff-file and no --base-ref → load_diff_files returns base
        # label "unknown" with an empty file list. Rule M4 must skip rather
        # than emit a false-positive branch_cleanup_without_changes finding.
        plan_id, _ = _setup_plan_with_manifest(tmp_path, monkeypatch, manifest_body=_manifest_default())
        result = run_script(
            MANIFEST_SCRIPT,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
        )
        assert result.success, result.stderr
        data = result.toon()
        assert data['diff']['base'] == 'unknown'
        check = _check_by_name(data['checks'], 'branch_cleanup_changes')
        assert check is not None
        assert check['status'] == 'skip'
        assert _finding_by_code(data['findings'], 'branch_cleanup_without_changes') is None

    def test_skip_when_diff_is_empty(self, tmp_path, monkeypatch):
        # An empty diff file resolves a base label but zero raw files — still
        # "no diff data", so the rule skips instead of false-positive failing.
        plan_id, _ = _setup_plan_with_manifest(tmp_path, monkeypatch, manifest_body=_manifest_default())
        diff = _write_diff(tmp_path, [])
        result = run_script(
            MANIFEST_SCRIPT,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--diff-file',
            str(diff),
        )
        assert result.success, result.stderr
        data = result.toon()
        check = _check_by_name(data['checks'], 'branch_cleanup_changes')
        assert check is not None
        assert check['status'] == 'skip'
        assert _finding_by_code(data['findings'], 'branch_cleanup_without_changes') is None

    def test_skip_when_branch_cleanup_absent(self, tmp_path, monkeypatch):
        plan_id, _ = _setup_plan_with_manifest(tmp_path, monkeypatch, manifest_body=_manifest_early_terminate())
        diff = _write_diff(tmp_path, [])
        result = run_script(
            MANIFEST_SCRIPT,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--diff-file',
            str(diff),
        )
        data = result.toon()
        check = _check_by_name(data['checks'], 'branch_cleanup_changes')
        assert check is not None
        assert check['status'] == 'skip'


# =============================================================================
# Decision-log surfacing
# =============================================================================


class TestDecisionLogSurfacing:
    def test_composer_decision_lines_carried_into_fragment(self, tmp_path, monkeypatch):
        decision_lines = [
            '[2026-04-17T10:00:00Z] [INFO] [aaaa] '
            '(plan-marshall:manage-execution-manifest:compose) Rule default fired — early_terminate=False',
            # Unrelated decision lines must NOT be surfaced.
            '[2026-04-17T10:00:01Z] [INFO] [bbbb] (plan-marshall:phase-3-outline) picked option A',
        ]
        plan_id, _ = _setup_plan_with_manifest(
            tmp_path,
            monkeypatch,
            manifest_body=_manifest_default(),
            decision_lines=decision_lines,
        )
        diff = _write_diff(tmp_path, ['src/foo/bar.py'])
        result = run_script(
            MANIFEST_SCRIPT,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--diff-file',
            str(diff),
        )
        data = result.toon()
        entries = data['decision_log_entries']
        # Exactly one composer entry surfaces, the unrelated outline entry stays out.
        assert isinstance(entries, list)
        assert len(entries) == 1
        assert 'manage-execution-manifest:compose' in entries[0]


# =============================================================================
# Gate-verb fail-closed on I/O-boundary read failures
# =============================================================================


class TestGateVerbReadFailClosed:
    """The manifest-consistency gate verb's three live filesystem reads must
    fail closed on an OSError — a path that passes ``.exists()`` but raises on
    ``read_text()`` (permission denied, the path resolves to a directory, a
    mid-read deletion race) degrades to the documented fail-closed sentinel for
    each loader, never an uncaught exception that crashes the verdict path:

    - ``load_manifest`` → ``None`` (same skip sentinel as a missing manifest).
    - ``load_decision_log_entries`` → ``[]`` (same empty-matches value as an
      absent log).
    - ``load_diff_files`` (``--diff-file`` arm) → a ``ValueError`` carrying the
      OSError context, surfaced as a structured ``status: error`` TOON (an
      explicitly supplied diff that cannot be read is a caller error, not a
      silently-empty diff).

    OSError is injected portably by replacing the target file with a directory
    of the same name: ``Path.exists()`` returns ``True`` for a directory while
    ``Path.read_text()`` raises ``IsADirectoryError`` (an ``OSError`` subclass).
    """

    def test_unreadable_manifest_degrades_to_skip_sentinel(self, tmp_path, monkeypatch):
        plan_id, plan_dir = _setup_plan_with_manifest(tmp_path, monkeypatch, manifest_body=_manifest_default())
        # Replace the manifest file with a directory so read_text() raises an
        # OSError while .exists() still passes.
        manifest_path = plan_dir / 'execution.toon'
        manifest_path.unlink()
        manifest_path.mkdir()
        diff = _write_diff(tmp_path, ['src/foo/bar.py'])

        result = run_script(
            MANIFEST_SCRIPT,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--diff-file',
            str(diff),
        )
        # Fail closed: the unreadable manifest degrades to the same skip
        # sentinel as a missing manifest — clean exit, skipped fragment, no
        # uncaught exception.
        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'skipped'
        assert data['manifest_present'] is False
        assert data['checks'] == []
        assert data['findings'] == []
        assert data.get('error') != 'internal_error'

    def test_unreadable_decision_log_degrades_to_empty_entries(self, tmp_path, monkeypatch):
        # A composer decision line WOULD normally surface, so an empty
        # decision_log_entries proves the OSError fail-closed path took over
        # rather than the read silently succeeding.
        decision_lines = [
            '[2026-04-17T10:00:00Z] [INFO] [aaaa] '
            '(plan-marshall:manage-execution-manifest:compose) Rule default fired',
        ]
        plan_id, plan_dir = _setup_plan_with_manifest(
            tmp_path,
            monkeypatch,
            manifest_body=_manifest_default(),
            decision_lines=decision_lines,
        )
        # Replace the decision log file with a directory so read_text() raises.
        log_path = plan_dir / 'logs' / 'decision.log'
        log_path.unlink()
        log_path.mkdir()
        diff = _write_diff(tmp_path, ['src/foo/bar.py'])

        result = run_script(
            MANIFEST_SCRIPT,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--diff-file',
            str(diff),
        )
        # Fail closed: the unreadable decision log degrades to the empty-matches
        # sentinel rather than crashing the verdict path.
        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        assert data['decision_log_entries'] == []
        assert data.get('error') != 'internal_error'

    def test_unreadable_diff_file_raises_structured_error(self, tmp_path, monkeypatch):
        plan_id, _ = _setup_plan_with_manifest(tmp_path, monkeypatch, manifest_body=_manifest_default())
        # Create a DIRECTORY at the --diff-file path: .exists() passes but
        # read_text() raises an OSError, which the loader converts to a
        # ValueError surfaced as a structured error TOON.
        diff_path = tmp_path / 'diff.txt'
        diff_path.mkdir()

        result = run_script(
            MANIFEST_SCRIPT,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--diff-file',
            str(diff_path),
        )
        # An explicitly supplied diff that cannot be read is a caller error:
        # the gate fails closed with a structured status: error TOON (via
        # safe_main rendering the ValueError), never a silently-empty diff and
        # never a raw traceback.
        assert not result.success
        data = result.toon()
        assert data['status'] == 'error'
        assert 'could not be read' in data['message'].lower()
