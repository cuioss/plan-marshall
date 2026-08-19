# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``check-manifest-consistency.py`` and the manifest-aware
forward in ``check-artifact-consistency.py``.

The cross-check matrix being exercised is documented in
``marketplace/bundles/plan-marshall/skills/plan-retrospective/standards/manifest-crosscheck.md``.
"""


from __future__ import annotations

from _plan_retrospective_fixtures import build_happy_plan_dir  # noqa: E402
from _plan_retrospective_manifest_fixtures import (
    ARTIFACT_SCRIPT,
    _check_by_name,
    _manifest_default,
    _write_manifest,
)

from conftest import run_script  # noqa: E402

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
