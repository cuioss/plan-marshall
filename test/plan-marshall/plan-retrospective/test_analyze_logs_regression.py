# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``analyze-logs.py``."""


from __future__ import annotations

import json

from _analyze_logs_fixtures import SCRIPT_PATH, _analyze_logs, read_log
from _plan_retrospective_fixtures import setup_archived_plan, setup_broken_plan, setup_live_plan  # noqa: E402

from conftest import run_script  # noqa: E402


class TestHappyPath:
    def test_counts_log_entries_by_level(self, tmp_path, monkeypatch):
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        assert data['status'] == 'success'
        assert data['aspect'] == 'log_analysis'
        counts = data['counts']
        assert int(counts['work_entries']) == 3
        assert int(counts['warnings_work']) == 1
        assert int(counts['script_entries']) == 3
        assert int(counts['errors_script']) == 1

    def test_phases_seen_extracted_from_logs(self, tmp_path, monkeypatch):
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        data = result.toon()
        phases = data['phases_seen']
        assert '1-init' in phases
        assert '3-outline' in phases
        assert '5-execute' in phases

    def test_script_durations_percentiles(self, tmp_path, monkeypatch):
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        data = result.toon()
        assert float(data['script_duration_max_ms']) >= 2500.0

    def test_slowest_scripts_ordered_desc(self, tmp_path, monkeypatch):
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        data = result.toon()
        slowest = data['slowest_scripts']
        assert slowest[0]['notation'] == 'plan-marshall:manage-status:manage-status'


class TestFaultPaths:
    def test_missing_logs_dir_returns_zero_counts(self, tmp_path, monkeypatch):
        plan_id, _ = setup_broken_plan(tmp_path, monkeypatch)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        counts = data['counts']
        assert int(counts['work_entries']) == 0
        assert int(counts['script_entries']) == 0


class TestArchivedMode:
    def test_archived_plan_path_reads_logs(self, tmp_path):
        archived = setup_archived_plan(tmp_path)
        result = run_script(SCRIPT_PATH, 'run', '--archived-plan-path', str(archived), '--mode', 'archived')
        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        assert int(data['counts']['work_entries']) == 3


class TestRegression:
    """Lock in the production-shape reading contracts.

    Two of them carry the whole class: ``analyze-logs`` MUST read the
    script-execution log under its real filename, or ``errors_script`` comes
    back zero even when that log holds ERROR entries; and ``read_log`` MUST
    distinguish a missing log file from an empty one, or log-source drift is
    invisible to the retrospective. The rest pin the tag, level and artifact
    readers those two feed.
    """

    def test_errors_script_counts_three_error_entries(self, tmp_path, monkeypatch):
        """A ``script-execution.log`` with 3 ERROR lines must produce
        ``counts.errors_script == 3``. Before the fix, analyze-logs read
        from ``script.log`` and this counter was always 0.
        """
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch, plan_id='retro-errors-script')
        logs_dir = plan_dir / 'logs'
        logs_dir.mkdir(exist_ok=True)
        # Overwrite the happy-path fixture (1 ERROR) with a 3-ERROR log to
        # exercise the counter exactly. Filename MUST match what
        # ``analyze-logs`` reads — ``script-execution.log`` per the fix.
        (logs_dir / 'script-execution.log').write_text(
            '[2026-04-17T10:00:01Z] [ERROR] [aaaaaa] '
            'plan-marshall:manage-tasks:manage-tasks add (0.12s)\n'
            '[2026-04-17T10:00:02Z] [ERROR] [bbbbbb] '
            'plan-marshall:manage-status:manage-status read (2.5s)\n'
            '[2026-04-17T10:00:10Z] [ERROR] [cccccc] '
            'plan-marshall:manage-files:manage-files add (0.05s)\n',
            encoding='utf-8',
        )
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        assert int(data['counts']['errors_script']) == 3, (
            f'Expected errors_script == 3 on a 3-ERROR script-execution.log, '
            f'got {data["counts"]["errors_script"]}. This regression means '
            f'analyze-logs is reading the wrong filename again.'
        )

    def test_artifact_entries_always_present_in_counts(self, tmp_path, monkeypatch):
        """``counts.artifact_entries`` MUST appear on every run regardless of
        modified_files / log state. Operators rely on its presence as a
        boolean signal that the counter is wired up.
        """
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch, plan_id='retro-artifact-present')
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        assert 'artifact_entries' in data['counts'], (
            'counts.artifact_entries missing — regression in analyze-logs output shape'
        )

    def test_modified_files_with_artifacts_produces_no_finding(self, tmp_path, monkeypatch):
        """Case (a): modified_files non-empty AND artifact_entries > 0 →
        no error finding. The happy-path fixture already satisfies this.
        """
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch, plan_id='retro-artifact-happy')
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        assert int(data['counts']['artifact_entries']) >= 1
        findings = data.get('findings') or []
        assert not any(f.get('severity') == 'error' and 'ARTIFACT' in f.get('message', '') for f in findings), (
            f'Did not expect ARTIFACT-missing finding when work.log has ARTIFACT entries; got findings: {findings}'
        )

    def test_modified_files_without_artifacts_emits_error_finding(self, tmp_path, monkeypatch):
        """Case (b): modified_files non-empty AND artifact_entries == 0 →
        an error finding MUST be produced so the retrospective surfaces
        the gap between declared artifacts and log evidence.
        """
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch, plan_id='retro-artifact-missing')
        # Overwrite work.log with entries that contain NO ARTIFACT tag,
        # using the production ``[ts] [LEVEL] [hash] [CATEGORY] ...`` shape.
        work_log = plan_dir / 'logs' / 'work.log'
        work_log.write_text(
            '[2026-04-17T10:00:00Z] [INFO] [aaaaaa] [STATUS] '
            '(plan-marshall:phase-1-init) Starting\n'
            '[2026-04-17T10:02:00Z] [WARNING] [bbbbbb] [STATUS] '
            '(plan-marshall:phase-5-execute) slow\n',
            encoding='utf-8',
        )

        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        assert int(data['counts']['artifact_entries']) == 0
        findings = data.get('findings') or []
        assert any(f.get('severity') == 'error' and 'ARTIFACT' in f.get('message', '') for f in findings), (
            f'Expected an ARTIFACT-missing error finding when modified_files '
            f'is non-empty and artifact_entries == 0; got findings: {findings}'
        )

    def test_empty_modified_files_produces_no_finding(self, tmp_path, monkeypatch):
        """Case (c): modified_files empty AND artifact_entries == 0 →
        no finding. Nothing was declared, so there is nothing to flag.
        """
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch, plan_id='retro-artifact-nothing-declared')
        # Clear modified_files and strip ARTIFACT entries from work.log.
        references_path = plan_dir / 'references.json'
        references = json.loads(references_path.read_text(encoding='utf-8'))
        references['modified_files'] = []
        references_path.write_text(json.dumps(references), encoding='utf-8')

        work_log = plan_dir / 'logs' / 'work.log'
        work_log.write_text(
            '[2026-04-17T10:00:00Z] [INFO] [aaaaaa] [STATUS] (plan-marshall:phase-1-init) Starting\n',
            encoding='utf-8',
        )

        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        assert int(data['counts']['artifact_entries']) == 0
        findings = data.get('findings') or []
        assert not any(f.get('severity') == 'error' and 'ARTIFACT' in f.get('message', '') for f in findings), (
            f'Did not expect ARTIFACT-missing finding when modified_files is empty; got findings: {findings}'
        )

    def test_extract_tags_captures_category_behind_level_bracket(self):
        """Production lines carry multiple bracketed uppercase tokens
        (``[LEVEL]`` precedes ``[CATEGORY]``). A plain ``re.search`` would
        return only ``[LEVEL]`` and never surface ``[ARTIFACT]``, silently
        defeating the artifact_entries counter. Guards that regression.
        """
        lines = [
            '[2026-04-18T12:00:00Z] [INFO] [abc123] [ARTIFACT] (plan-marshall:phase-5-execute:3) Wrote foo.py',
            '[2026-04-18T12:00:05Z] [INFO] [def456] [STATUS] (plan-marshall:phase-5-execute) task 3 complete',
            '[2026-04-18T12:00:10Z] [WARNING] [789aaa] [ARTIFACT] (plan-marshall:phase-5-execute:4) Deleted bar.py',
        ]
        tags = _analyze_logs.extract_tags(lines)
        assert 'ARTIFACT' in tags, (
            f'extract_tags must surface [ARTIFACT] even when [INFO] or '
            f'[WARNING] precedes it in the same line; got tags: {tags}'
        )
        assert tags.count('ARTIFACT') == 2, (
            f'extract_tags must count every [ARTIFACT] occurrence, not just one per line; got tags: {tags}'
        )
        assert tags.count('STATUS') == 1
        # Level tokens must NOT leak into the category stream.
        assert 'INFO' not in tags
        assert 'WARNING' not in tags
        assert 'ERROR' not in tags

    def test_count_levels_matches_bracketed_production_shape(self):
        """``count_levels`` must recognize ``[INFO]``/``[WARNING]``/``[ERROR]``
        bracketed tokens as emitted by ``manage-logging``. The earlier
        space-delimited match failed to see levels in the production
        shape, leaving ``counts.*`` stuck at zero for real plans.
        """
        lines = [
            '[2026-04-18T12:00:00Z] [INFO] [abc] [STATUS] msg one',
            '[2026-04-18T12:00:01Z] [WARNING] [def] [STATUS] msg two',
            '[2026-04-18T12:00:02Z] [ERROR] [ghi] [STATUS] msg three',
            '[2026-04-18T12:00:03Z] [INFO] [jkl] [STATUS] msg four',
        ]
        counts = _analyze_logs.count_levels(lines)
        assert counts['INFO'] == 2
        assert counts['WARNING'] == 1
        assert counts['ERROR'] == 1

    def test_read_log_missing_path_emits_stderr_warn(self, tmp_path, capsys):
        """``read_log`` must surface a stderr WARN line (not silently
        return []) when the target file is missing. Silent-swallowing
        hides log-source drift from the retrospective reader.
        """
        missing_path = tmp_path / 'definitely-not-a-real-log.log'
        assert not missing_path.exists()

        # call read_log directly so we get clean stderr capture.
        result = read_log(missing_path)

        # empty list for missing file is still the contract, but
        # the stderr WARN line MUST be present so operators notice.
        assert result == []
        captured = capsys.readouterr()
        assert 'WARN' in captured.err, f'read_log on missing path must emit stderr WARN; got stderr: {captured.err!r}'
        assert str(missing_path) in captured.err, 'WARN line must include the missing path for operator debugging'
