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
    _manifest_docs_only,
    _manifest_early_terminate,
    _manifest_tests_only,
    _setup_plan_with_manifest,
    _write_diff,
)

from conftest import run_script  # noqa: E402

# =============================================================================
# Skipped path: no manifest present
# =============================================================================


class TestNoManifest:
    """Without execution.toon the script emits a skipped fragment."""

    def test_legacy_plan_emits_skipped_fragment(self, tmp_path, monkeypatch):
        plan_id, _ = _setup_plan_with_manifest(tmp_path, monkeypatch, manifest_body='', plan_id='legacy-plan')
        # Remove the manifest written by the helper to simulate legacy plans.
        (tmp_path / 'base' / 'plans' / plan_id / 'execution.toon').unlink()
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
        assert data['status'] == 'skipped'
        assert data['manifest_present'] is False
        assert data['checks'] == []
        assert data['findings'] == []


# =============================================================================
# Rule M1: docs-only manifest
# =============================================================================


class TestDocsOnlyRule:
    def test_pass_when_diff_is_pure_docs(self, tmp_path, monkeypatch):
        plan_id, _ = _setup_plan_with_manifest(tmp_path, monkeypatch, manifest_body=_manifest_docs_only())
        diff = _write_diff(
            tmp_path,
            [
                'docs/intro.md',
                'docs/usage.adoc',
                'src/skills/foo/references/bar.md',
                'src/skills/foo/templates/baz.md',
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
        assert result.success, result.stderr
        data = result.toon()
        check = _check_by_name(data['checks'], 'docs_only_diff')
        assert check is not None
        assert check['status'] == 'pass'
        # No violation finding emitted.
        assert _finding_by_code(data['findings'], 'docs_only_diff_violation') is None

    def test_fail_when_diff_contains_python_source(self, tmp_path, monkeypatch):
        plan_id, _ = _setup_plan_with_manifest(tmp_path, monkeypatch, manifest_body=_manifest_docs_only())
        diff = _write_diff(
            tmp_path,
            ['docs/intro.md', 'src/foo/bar.py'],
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
        assert result.success, result.stderr
        data = result.toon()
        check = _check_by_name(data['checks'], 'docs_only_diff')
        assert check is not None
        assert check['status'] == 'fail'
        finding = _finding_by_code(data['findings'], 'docs_only_diff_violation')
        assert finding is not None
        assert finding['severity'] == 'warning'
        assert 'src/foo/bar.py' in finding['culprits']

    def test_skip_when_manifest_has_verification_steps(self, tmp_path, monkeypatch):
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
        check = _check_by_name(data['checks'], 'docs_only_diff')
        assert check is not None
        assert check['status'] == 'skip'


# =============================================================================
# Rule M2: early_terminate
# =============================================================================


class TestEarlyTerminateRule:
    def test_pass_when_diff_is_empty(self, tmp_path, monkeypatch):
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
        check = _check_by_name(data['checks'], 'early_terminate_diff')
        assert check is not None
        assert check['status'] == 'pass'

    def test_verdict_withheld_when_only_bookkeeping_changes(self, tmp_path, monkeypatch):
        plan_id, _ = _setup_plan_with_manifest(tmp_path, monkeypatch, manifest_body=_manifest_early_terminate())
        diff = _write_diff(
            tmp_path,
            [
                '.plan/local/lessons-learned/foo.md',
                'docs/quality-verification-report.md',
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
        # Both entries are bookkeeping the filter can substantiate: the
        # genuinely-runtime ``.plan/`` state directory (in no build map, so
        # hardcoded) and the plan's own quality-verification report.
        assert int(data['diff']['files_filtered']) == 2
        check = _check_by_name(data['checks'], 'early_terminate_diff')
        assert check is not None
        # Every supplied path was filtered, so the rule saw nothing: its clean
        # pass is withheld rather than emitted bare (D2).
        assert check['status'] == 'indeterminate'
        assert 'VERDICT WITHHELD' in check['message']

    def test_unrouted_dotfile_path_is_retained_not_assumed_bookkeeping(self, tmp_path, monkeypatch):
        """A ``.claude/`` path the build map does not route is RETAINED.

        The filter used to drop the whole ``.claude/`` tree on a private prefix
        tuple, which discarded this project's own production source (``build.map``
        routes ``.claude/skills/*.py`` as ``production``). The corrected filter
        drops only what it can substantiate, so a path the oracle has no opinion
        about is kept and counted rather than silently assumed unimportant.
        """
        plan_id, _ = _setup_plan_with_manifest(tmp_path, monkeypatch, manifest_body=_manifest_early_terminate())
        diff = _write_diff(tmp_path, ['.plan/local/lessons-learned/foo.md', '.claude/settings.local.json'])
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
        assert int(data['diff']['files_kept']) == 1
        assert int(data['diff']['filtered_by_category']['unclassified']) == 1

    def test_fail_when_implementation_files_present(self, tmp_path, monkeypatch):
        plan_id, _ = _setup_plan_with_manifest(tmp_path, monkeypatch, manifest_body=_manifest_early_terminate())
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
        check = _check_by_name(data['checks'], 'early_terminate_diff')
        assert check is not None
        assert check['status'] == 'fail'
        finding = _finding_by_code(data['findings'], 'early_terminate_diff_nonempty')
        assert finding is not None


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
