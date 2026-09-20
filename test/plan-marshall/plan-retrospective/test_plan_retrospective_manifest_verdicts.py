# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``check-manifest-consistency.py`` and the manifest-aware
forward in ``check-artifact-consistency.py``.

Its sections, in order:

* Skipped path: no manifest present
* Rule M5: manifest version recognition
* Rule M1: docs-only manifest
* Rule M2: early_terminate
* Rule M4 + footprint degradation: no tier resolved
* Rule M6: the forwarded declared-vs-realized set comparison is RECEIVED
"""

from __future__ import annotations

import json
from pathlib import Path

from _plan_retrospective_manifest_fixtures import (
    MANIFEST_SCRIPT,
    _check_by_name,
    _finding_by_code,
    _manifest_default,
    _manifest_docs_only,
    _manifest_early_terminate,
    _setup_plan_with_manifest,
    _write_diff,
    _write_status_metadata,
)

from conftest import run_script


def _strand_every_footprint_tier(plan_dir: Path) -> None:
    """Leave the plan with NO resolvable footprint tier.

    Every tier of the shared chain is starved deliberately and by NAME, so the
    degradation cases below exercise the unresolvable sentinel rather than
    happening to reach it: no worktree is recorded (tier 1), and
    ``references.json`` carries none of ``realized_footprint`` (tier 2),
    ``merge_commit_sha`` / ``merge_commit_shas`` (tier 3), ``pr_number``
    (tier 4) or ``modified_files`` (tier 5).
    """
    _write_status_metadata(plan_dir, {})
    (plan_dir / 'references.json').write_text(json.dumps({'base_branch': 'main'}), encoding='utf-8')


def _write_artifact_consistency_fragment(plan_dir: Path, exact_match: dict) -> None:
    """Write the upstream fragment rule M6 receives its comparison from."""
    from toon_parser import serialize_toon  # local import — script-test PYTHONPATH

    work = plan_dir / 'work'
    work.mkdir(parents=True, exist_ok=True)
    body = {
        'aspect': 'artifact_consistency',
        'status': 'success',
        'plan_id': plan_dir.name,
        'affected_files_exact_match': exact_match,
    }
    (work / 'fragment-artifact-consistency.toon').write_text(serialize_toon(body) + '\n', encoding='utf-8')


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
# Rule M4 + footprint degradation: no tier resolved
# =============================================================================


class TestFootprintDegradation:
    """An unresolvable footprint degrades; it never reads as an empty one.

    This is the defect the aspect was repaired for. The script used to take its
    own ``git diff {base}...HEAD``, which is structurally empty at finalize
    ``order: 995`` (``branch-cleanup`` has already merged): the call succeeded,
    named no path, and rule M4 concluded "no implementation file changed" for
    plans that had shipped a real footprint.

    The pair below is MATCHED, and both halves are needed. The negative half
    alone would pass against a script that degraded unconditionally — including
    one that had simply stopped working — so the positive half pins that a
    RESOLVED footprint still produces a measured verdict.
    """

    def test_unresolved_footprint_yields_the_degradation_verdict(self, tmp_path, monkeypatch):
        plan_id, plan_dir = _setup_plan_with_manifest(tmp_path, monkeypatch, manifest_body=_manifest_default())
        _strand_every_footprint_tier(plan_dir)

        # No --diff-file: the footprint must come from the shared chain, which
        # has nothing to resolve from.
        result = run_script(MANIFEST_SCRIPT, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        assert data['footprint_resolution']['status'] == 'inconclusive'
        assert data['footprint_resolution']['tier'] == 'unresolved'

        check = _check_by_name(data['checks'], 'branch_cleanup_changes')
        assert check is not None
        # ``inconclusive``, NOT ``indeterminate``: only the former is a member of
        # retro_sections.FOOTPRINT_DEGRADED_TOKENS, and compile-report matches it
        # by equality against a verdict field. Emitting ``indeterminate`` here
        # would read as RESOLVED to the plan-level footprint aggregate.
        assert check['status'] == 'inconclusive'
        # ⛔ The confident wording must be absent — this is the exact claim the
        # repair removes, so it is asserted against rather than merely not
        # asserted for.
        assert 'no implementation file changed' not in check['message']
        assert 'the observed diff is empty' not in check['message']

        finding = _finding_by_code(data['findings'], 'branch_cleanup_footprint_unresolved')
        assert finding is not None
        assert finding['severity'] == 'warning'
        # The inverse finding must NOT have been raised.
        assert _finding_by_code(data['findings'], 'branch_cleanup_without_changes') is None

    def test_resolved_footprint_still_yields_a_measured_verdict(self, tmp_path, monkeypatch):
        """The matched POSITIVE control: a readable footprint still reports.

        Without this, a script that degraded on every run — or one whose
        resolver had broken outright — would satisfy the negative case above.
        """
        plan_id, plan_dir = _setup_plan_with_manifest(tmp_path, monkeypatch, manifest_body=_manifest_default())
        _strand_every_footprint_tier(plan_dir)
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
        assert result.success, result.stderr
        data = result.toon()

        assert data['footprint_resolution']['status'] == 'resolved'
        assert data['footprint_resolution']['tier'] == 'diff_file'

        check = _check_by_name(data['checks'], 'branch_cleanup_changes')
        assert check is not None
        assert check['status'] == 'pass'
        assert _finding_by_code(data['findings'], 'branch_cleanup_footprint_unresolved') is None


# =============================================================================
# Rule M6: the forwarded declared-vs-realized set comparison is RECEIVED
# =============================================================================


class TestDeclaredVsRealizedSetRule:
    """``check-artifact-consistency`` forwards; this rule is the receiver.

    The flag previously had no reader at all, so the downgraded upstream finding
    was DROPPED on every manifest-bearing plan rather than re-routed.
    """

    def _run(self, tmp_path, monkeypatch, exact_match: dict | None):
        plan_id, plan_dir = _setup_plan_with_manifest(tmp_path, monkeypatch, manifest_body=_manifest_default())
        if exact_match is not None:
            _write_artifact_consistency_fragment(plan_dir, exact_match)
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
        assert result.success, result.stderr
        return result.toon()

    def test_agreeing_sets_pass_and_publish_both_sizes(self, tmp_path, monkeypatch):
        data = self._run(
            tmp_path,
            monkeypatch,
            {
                'status': 'pass',
                'outline_only': [],
                'references_only': [],
                'manifest_present': True,
                'forwarded_to_manifest': False,
            },
        )
        check = _check_by_name(data['checks'], 'declared_vs_realized_set')
        assert check is not None
        assert check['status'] == 'pass'

        received = data['declared_vs_realized']
        assert received['received'] is True
        assert int(received['outline_only_count']) == 0
        assert int(received['references_only_count']) == 0

    def test_outline_only_drift_is_graded_warning(self, tmp_path, monkeypatch):
        data = self._run(
            tmp_path,
            monkeypatch,
            {
                'status': 'warn',
                'outline_only': ['src/declared_but_unbuilt.py'],
                'references_only': [],
                'manifest_present': True,
                'forwarded_to_manifest': True,
            },
        )
        check = _check_by_name(data['checks'], 'declared_vs_realized_set')
        assert check is not None
        assert check['status'] == 'fail'

        finding = _finding_by_code(data['findings'], 'declared_vs_realized_set_mismatch')
        assert finding is not None
        # A declaration the run did not honour is the stronger signal.
        assert finding['severity'] == 'warning'
        assert 'src/declared_but_unbuilt.py' in finding['culprits']
        assert int(data['declared_vs_realized']['outline_only_count']) == 1
        assert data['declared_vs_realized']['forwarded_to_manifest'] is True

    def test_references_only_drift_alone_is_graded_info(self, tmp_path, monkeypatch):
        """The severity DISCRIMINATOR: realized-but-undeclared is ordinary discovery."""
        data = self._run(
            tmp_path,
            monkeypatch,
            {
                'status': 'warn',
                'outline_only': [],
                'references_only': ['src/discovered.py'],
                'manifest_present': True,
                'forwarded_to_manifest': True,
            },
        )
        finding = _finding_by_code(data['findings'], 'declared_vs_realized_set_mismatch')
        assert finding is not None
        assert finding['severity'] == 'info'
        assert int(data['declared_vs_realized']['references_only_count']) == 1

    def test_unread_fragment_is_inconclusive_and_publishes_no_counts(self, tmp_path, monkeypatch):
        """⛔ An unreceived comparison must not read as two agreeing empty sets."""
        data = self._run(tmp_path, monkeypatch, None)

        check = _check_by_name(data['checks'], 'declared_vs_realized_set')
        assert check is not None
        assert check['status'] == 'inconclusive'

        received = data['declared_vs_realized']
        assert received['received'] is False
        # The count keys are OMITTED, never zeroed — a caller gating on them
        # finds no key instead of a measured-looking zero.
        assert 'outline_only_count' not in received
        assert 'references_only_count' not in received
        assert received['reason']
