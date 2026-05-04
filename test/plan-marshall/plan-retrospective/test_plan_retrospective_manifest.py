"""Tests for ``check-manifest-consistency.py`` and the manifest-aware
forward in ``check-artifact-consistency.py``.

The cross-check matrix being exercised is documented in
``marketplace/bundles/plan-marshall/skills/plan-retrospective/standards/manifest-crosscheck.md``.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _fixtures import build_happy_plan_dir  # noqa: E402

from conftest import MARKETPLACE_ROOT, run_script  # noqa: E402

MANIFEST_SCRIPT = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts' / 'check-manifest-consistency.py'
)

ARTIFACT_SCRIPT = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts' / 'check-artifact-consistency.py'
)


# =============================================================================
# Fixture helpers
# =============================================================================


def _write_manifest(plan_dir: Path, body: str) -> None:
    """Write a TOON manifest into the plan directory."""
    (plan_dir / 'execution.toon').write_text(body, encoding='utf-8')


def _write_diff(tmp_path: Path, files: list[str]) -> Path:
    """Write a one-path-per-line diff file and return its path."""
    diff_path = tmp_path / 'diff.txt'
    diff_path.write_text('\n'.join(files) + ('\n' if files else ''), encoding='utf-8')
    return diff_path


def _write_decision_log(plan_dir: Path, lines: list[str]) -> None:
    """Write decision-log lines including the composer caller tag where requested."""
    logs_dir = plan_dir / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / 'decision.log').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def _setup_plan_with_manifest(
    tmp_path: Path,
    monkeypatch,
    manifest_body: str,
    *,
    plan_id: str = 'manifest-plan',
    decision_lines: list[str] | None = None,
) -> tuple[str, Path]:
    """Build a happy-path plan and overlay an execution.toon manifest."""
    base = tmp_path / 'base'
    base.mkdir()
    plan_dir = base / 'plans' / plan_id
    build_happy_plan_dir(plan_dir)
    _write_manifest(plan_dir, manifest_body)
    if decision_lines is not None:
        _write_decision_log(plan_dir, decision_lines)
    monkeypatch.setenv('PLAN_BASE_DIR', str(base))
    return plan_id, plan_dir


# Manifest body templates. We round-trip through ``serialize_toon`` so the
# fixtures always match the on-disk shape produced by ``manage-execution-manifest``
# (``key[N]:`` header followed by ``  - value`` lines for simple arrays).
def _serialize_manifest(body: dict) -> str:
    from toon_parser import serialize_toon  # local import — script-test PYTHONPATH

    return serialize_toon(body) + '\n'


def _manifest_default() -> str:
    return _serialize_manifest(
        {
            'manifest_version': 1,
            'plan_id': 'manifest-plan',
            'phase_5': {
                'early_terminate': False,
                'verification_steps': ['quality-gate', 'module-tests'],
            },
            'phase_6': {
                'steps': ['commit-push', 'create-pr', 'branch-cleanup'],
            },
        }
    )


def _manifest_docs_only() -> str:
    return _serialize_manifest(
        {
            'manifest_version': 1,
            'plan_id': 'manifest-plan',
            'phase_5': {
                'early_terminate': False,
                'verification_steps': [],
            },
            'phase_6': {
                'steps': ['commit-push', 'create-pr'],
            },
        }
    )


def _manifest_early_terminate() -> str:
    return _serialize_manifest(
        {
            'manifest_version': 1,
            'plan_id': 'manifest-plan',
            'phase_5': {
                'early_terminate': True,
                'verification_steps': [],
            },
            'phase_6': {
                'steps': ['knowledge-capture', 'archive-plan'],
            },
        }
    )


def _manifest_tests_only() -> str:
    return _serialize_manifest(
        {
            'manifest_version': 1,
            'plan_id': 'manifest-plan',
            'phase_5': {
                'early_terminate': False,
                'verification_steps': ['module-tests'],
            },
            'phase_6': {
                'steps': ['commit-push', 'create-pr'],
            },
        }
    )


def _check_by_name(checks: list, name: str) -> dict | None:
    for entry in checks:
        if entry.get('name') == name:
            return entry
    return None


def _finding_by_code(findings: list, code: str) -> dict | None:
    for entry in findings:
        if entry.get('code') == code:
            return entry
    return None


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

    def test_pass_when_only_bookkeeping_changes(self, tmp_path, monkeypatch):
        plan_id, _ = _setup_plan_with_manifest(tmp_path, monkeypatch, manifest_body=_manifest_early_terminate())
        diff = _write_diff(
            tmp_path,
            [
                '.plan/local/lessons-learned/foo.md',
                '.claude/settings.local.json',
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
        # All three diff entries should be filtered out as bookkeeping.
        assert int(data['diff']['files_filtered']) == 3
        check = _check_by_name(data['checks'], 'early_terminate_diff')
        assert check is not None
        assert check['status'] == 'pass'

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

    def test_fail_when_branch_cleanup_without_changes(self, tmp_path, monkeypatch):
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
        data = result.toon()
        check = _check_by_name(data['checks'], 'branch_cleanup_changes')
        assert check is not None
        assert check['status'] == 'fail'
        finding = _finding_by_code(data['findings'], 'branch_cleanup_without_changes')
        assert finding is not None
        assert finding['severity'] == 'info'

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
# Rule M5: manifest version recognition
# =============================================================================


class TestManifestVersionRule:
    def test_pass_for_known_version(self, tmp_path, monkeypatch):
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
        check = _check_by_name(data['checks'], 'manifest_version_recognized')
        assert check is not None
        assert check['status'] == 'pass'

    def test_fail_for_unknown_version(self, tmp_path, monkeypatch):
        # Replace the version line precisely. Replacing the bare ``1`` would
        # also rewrite list counts in the surrounding TOON header.
        body = _manifest_default().replace('manifest_version: 1\n', 'manifest_version: 99\n')
        plan_id, _ = _setup_plan_with_manifest(tmp_path, monkeypatch, manifest_body=body)
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
        check = _check_by_name(data['checks'], 'manifest_version_recognized')
        assert check is not None
        assert check['status'] == 'fail'
        finding = _finding_by_code(data['findings'], 'manifest_version_unknown')
        assert finding is not None
        assert finding['severity'] == 'error'


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
# Forward in check-artifact-consistency
# =============================================================================


class TestArtifactConsistencyManifestForward:
    """When execution.toon exists, the legacy exact_match warn is downgraded
    to info and forwarded to the manifest aspect."""

    def test_warn_downgraded_when_manifest_present(self, tmp_path, monkeypatch):
        # Build a happy plan whose outline declares foo/bar/baz but whose
        # references.json only has foo, producing an exact_match warn.
        base = tmp_path / 'base'
        base.mkdir()
        plan_dir = base / 'plans' / 'forward-plan'
        build_happy_plan_dir(plan_dir)
        # Trim references.json so outline > references → warn.
        import json as _json  # local alias to avoid module-level pollution

        (plan_dir / 'references.json').write_text(
            _json.dumps({'modified_files': ['src/foo.py'], 'domains': []}),
            encoding='utf-8',
        )
        _write_manifest(plan_dir, _manifest_default())
        monkeypatch.setenv('PLAN_BASE_DIR', str(base))

        result = run_script(
            ARTIFACT_SCRIPT,
            'run',
            '--plan-id',
            'forward-plan',
            '--mode',
            'live',
        )
        assert result.success, result.stderr
        data = result.toon()
        exact = data['affected_files_exact_match']
        # Top-level payload retains the original warn status as ground truth
        # for tooling, but adds the forwarding flag.
        assert exact['status'] == 'warn'
        assert exact['manifest_present'] is True
        assert exact['forwarded_to_manifest'] is True

        # The check entry visible to the report renderer is downgraded to info.
        check = _check_by_name(data['checks'], 'affected_files_exact_match')
        assert check is not None
        assert check['status'] == 'info'
        assert 'deferred to manifest aspect' in check['message']

        # The corresponding finding is severity=info (not warning) so the
        # report renderer routes the reader to the manifest section instead
        # of double-counting the drift.
        forwarded = [f for f in data['findings'] if 'deferred to manifest aspect' in f['message']]
        assert len(forwarded) == 1
        assert forwarded[0]['severity'] == 'info'

    def test_warn_retained_when_manifest_absent(self, tmp_path, monkeypatch):
        base = tmp_path / 'base'
        base.mkdir()
        plan_dir = base / 'plans' / 'legacy-warn'
        build_happy_plan_dir(plan_dir)
        import json as _json

        (plan_dir / 'references.json').write_text(
            _json.dumps({'modified_files': ['src/foo.py'], 'domains': []}),
            encoding='utf-8',
        )
        # No execution.toon written.
        monkeypatch.setenv('PLAN_BASE_DIR', str(base))

        result = run_script(
            ARTIFACT_SCRIPT,
            'run',
            '--plan-id',
            'legacy-warn',
            '--mode',
            'live',
        )
        assert result.success, result.stderr
        data = result.toon()
        exact = data['affected_files_exact_match']
        assert exact['status'] == 'warn'
        assert exact['manifest_present'] is False
        assert exact['forwarded_to_manifest'] is False

        # Existing behavior preserved: the check entry is warn and the
        # finding severity stays warning.
        check = _check_by_name(data['checks'], 'affected_files_exact_match')
        assert check is not None
        assert check['status'] == 'warn'
        warning_findings = [f for f in data['findings'] if f.get('severity') == 'warning']
        # At least the exact_match warning is present.
        assert any('mismatch' in f['message'].lower() for f in warning_findings)
