"""Tests for ``analyze-logs.py``."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from _plan_retrospective_fixtures import setup_archived_plan, setup_broken_plan, setup_live_plan  # noqa: E402

from conftest import MARKETPLACE_ROOT, run_script  # noqa: E402

SCRIPT_PATH = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts' / 'analyze-logs.py'


# Direct import of analyze-logs.py (hyphenated filename → importlib). Used by
# the regression tests below that call ``read_log`` in-process so they can
# capture stderr WARN lines reliably without shell-level quoting noise.
_spec = importlib.util.spec_from_file_location('analyze_logs', str(SCRIPT_PATH))
assert _spec is not None and _spec.loader is not None
_analyze_logs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_analyze_logs)
read_log = _analyze_logs.read_log


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
    """Regression tests that lock in the production-shape bug fixes.

    The parent plan was triggered by four concrete defects: among them,
    ``analyze-logs`` was reading the wrong filename so ``errors_script``
    came back zero even when the script-execution log had ERROR entries,
    and ``read_log`` silently returned [] for missing log files which hid
    log-source drift from the retrospective. These tests fail whenever
    either regression reappears.
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

        # Act: call read_log directly so we get clean stderr capture.
        result = read_log(missing_path)

        # Assert: empty list for missing file is still the contract, but
        # the stderr WARN line MUST be present so operators notice.
        assert result == []
        captured = capsys.readouterr()
        assert 'WARN' in captured.err, f'read_log on missing path must emit stderr WARN; got stderr: {captured.err!r}'
        assert str(missing_path) in captured.err, 'WARN line must include the missing path for operator debugging'


# =============================================================================
# Phase-5 logging-gap fact extractors (lesson 2026-05-08-14-001)
# =============================================================================


class TestPhase5LoggingGapExtractors:
    """Pin down the four phase-5-execute fact extractors.

    The extractors are pure counting/pairing — never judging. These tests
    therefore assert the shape of the returned dicts on (a) clean fixtures
    and (b) regression fixtures that mirror the cluster-02 gap pattern that
    motivated lesson 2026-05-08-14-001 (missing OUTCOME, ghost dispatches,
    no dispatch-boundary file).
    """

    # ------------------------------------------------------------------
    # pair_outcome_emissions
    # ------------------------------------------------------------------

    def test_pair_outcome_emissions_clean(self):
        """Clean fixture: every Completed has a paired [OUTCOME]."""
        lines = [
            '[2026-05-08T14:00:00Z] [INFO] [abc] [MANAGE-TASKS] Completed TASK-001',
            '[2026-05-08T14:00:01Z] [INFO] [def] [OUTCOME] (plan-marshall:phase-5-execute) '
            'Completed TASK-001: Title (3 steps)',
            '[2026-05-08T14:01:00Z] [INFO] [ghi] [MANAGE-TASKS] Completed TASK-002',
            '[2026-05-08T14:01:01Z] [INFO] [jkl] [OUTCOME] (plan-marshall:phase-5-execute) '
            'Completed TASK-002: Other (1 steps)',
        ]
        result = _analyze_logs.pair_outcome_emissions(lines)
        assert result['paired'] == 2
        assert result['unpaired_completed'] == []
        assert result['unpaired_outcome'] == []

    def test_pair_outcome_emissions_regression_missing_outcome(self):
        """Regression fixture: TASK-002 closed but [OUTCOME] line lost on re-dispatch."""
        lines = [
            '[2026-05-08T14:00:00Z] [INFO] [abc] [MANAGE-TASKS] Completed TASK-001',
            '[2026-05-08T14:00:01Z] [INFO] [def] [OUTCOME] (plan-marshall:phase-5-execute) '
            'Completed TASK-001: Title (3 steps)',
            '[2026-05-08T14:01:00Z] [INFO] [ghi] [MANAGE-TASKS] Completed TASK-002',
            # No [OUTCOME] line for TASK-002 — the lesson-2026-05-08-14-001 gap pattern.
        ]
        result = _analyze_logs.pair_outcome_emissions(lines)
        assert result['paired'] == 1
        assert result['unpaired_completed'] == ['TASK-002']
        assert result['unpaired_outcome'] == []

    # ------------------------------------------------------------------
    # cluster_dispatches
    # ------------------------------------------------------------------

    def test_cluster_dispatches_single_cluster(self):
        """All phase-5-execute lines within `gap_threshold_s` form one cluster."""
        work = [
            '[2026-05-08T14:00:00Z] [INFO] [abc] '
            '[STATUS] (plan-marshall:phase-5-execute) Starting execute phase — 3 tasks pending',
            '[2026-05-08T14:00:10Z] [INFO] [def] '
            '[OUTCOME] (plan-marshall:phase-5-execute) Completed TASK-001: x (1 steps)',
            '[2026-05-08T14:00:20Z] [INFO] [ghi] '
            '[OUTCOME] (plan-marshall:phase-5-execute) Completed TASK-002: y (1 steps)',
        ]
        script: list[str] = []
        result = _analyze_logs.cluster_dispatches(work, script, gap_threshold_s=30.0)
        assert result['inferred_dispatches'] == 1
        assert result['starting_markers'] == 1
        assert result['re_entering_markers'] == 0

    def test_cluster_dispatches_regression_ghost_re_entry(self):
        """Two clusters with a gap > 30s but only one Re-entering marker — the
        cluster-02 ghost-re-entry pattern."""
        work = [
            '[2026-05-08T14:00:00Z] [INFO] [abc] '
            '[STATUS] (plan-marshall:phase-5-execute) Starting execute phase — 3 tasks pending',
            '[2026-05-08T14:00:10Z] [INFO] [def] '
            '[OUTCOME] (plan-marshall:phase-5-execute) Completed TASK-001: x (1 steps)',
            # 5-minute gap → second dispatch cluster.
            '[2026-05-08T14:05:10Z] [INFO] [ghi] '
            '[OUTCOME] (plan-marshall:phase-5-execute) Completed TASK-002: y (1 steps)',
        ]
        script: list[str] = []
        result = _analyze_logs.cluster_dispatches(work, script, gap_threshold_s=30.0)
        assert result['inferred_dispatches'] == 2
        assert result['starting_markers'] == 1
        # No "Re-entering" line was emitted for the second cluster — the
        # symptom the LLM rule is meant to flag.
        assert result['re_entering_markers'] == 0

    # ------------------------------------------------------------------
    # detect_outcome_for_diffed_tasks
    # ------------------------------------------------------------------

    def test_detect_outcome_for_diffed_tasks_clean(self, tmp_path):
        """Every done task has a matching [OUTCOME] — no missing entries."""
        plan_dir = tmp_path / 'plans' / 'clean'
        (plan_dir / 'tasks').mkdir(parents=True)
        (plan_dir / 'tasks' / 'TASK-001.json').write_text(
            json.dumps({'number': 1, 'title': 'A', 'status': 'done'}),
            encoding='utf-8',
        )
        (plan_dir / 'tasks' / 'TASK-002.json').write_text(
            json.dumps({'number': 2, 'title': 'B', 'status': 'done'}),
            encoding='utf-8',
        )

        lines = [
            '[2026-05-08T14:00:01Z] [INFO] [abc] [OUTCOME] (plan-marshall:phase-5-execute) '
            'Completed TASK-001: A (1 steps)',
            '[2026-05-08T14:00:02Z] [INFO] [def] [OUTCOME] (plan-marshall:phase-5-execute) '
            'Completed TASK-002: B (1 steps)',
        ]
        result = _analyze_logs.detect_outcome_for_diffed_tasks(lines, plan_dir)
        assert result['tasks_with_diff_no_outcome'] == []

    def test_detect_outcome_for_diffed_tasks_regression(self, tmp_path):
        """Done task with no [OUTCOME] line — the lesson 2026-05-08-14-001 gap."""
        plan_dir = tmp_path / 'plans' / 'gap'
        (plan_dir / 'tasks').mkdir(parents=True)
        (plan_dir / 'tasks' / 'TASK-001.json').write_text(
            json.dumps({'number': 1, 'title': 'A', 'status': 'done'}),
            encoding='utf-8',
        )
        (plan_dir / 'tasks' / 'TASK-002.json').write_text(
            json.dumps({'number': 2, 'title': 'B', 'status': 'done'}),
            encoding='utf-8',
        )
        # Task pending — never closed; should NOT be flagged as missing-outcome.
        (plan_dir / 'tasks' / 'TASK-003.json').write_text(
            json.dumps({'number': 3, 'title': 'C', 'status': 'pending'}),
            encoding='utf-8',
        )

        lines = [
            '[2026-05-08T14:00:01Z] [INFO] [abc] [OUTCOME] (plan-marshall:phase-5-execute) '
            'Completed TASK-001: A (1 steps)',
            # No [OUTCOME] for TASK-002 → flagged.
        ]
        result = _analyze_logs.detect_outcome_for_diffed_tasks(lines, plan_dir)
        assert result['tasks_with_diff_no_outcome'] == ['TASK-002']

    # ------------------------------------------------------------------
    # read_dispatch_boundaries_per_phase
    # ------------------------------------------------------------------

    def test_read_dispatch_boundaries_per_phase_absent(self, tmp_path):
        """Plans with no boundary artifacts return an empty per-phase dict."""
        plan_dir = tmp_path / 'plans' / 'no-boundary'
        plan_dir.mkdir(parents=True)
        result = _analyze_logs.read_dispatch_boundaries_per_phase(plan_dir)
        assert result == {}

    def test_read_dispatch_boundaries_per_phase_present(self, tmp_path):
        """Glob discovers every per-phase artifact and keys the result by phase name.

        Lesson 2026-05-20-12-002 generalised the prior phase-5-only reader to
        cover phase-4-plan and phase-6-finalize boundary artifacts. The
        per-file shape (``present``, ``rows``, ``unknown_count``,
        ``clean_exit_queue_empty_count``) is unchanged.
        """
        plan_dir = tmp_path / 'plans' / 'with-boundary'
        (plan_dir / 'work').mkdir(parents=True)
        # Phase-5-execute artifact — preserves the legacy single-phase shape.
        (plan_dir / 'work' / 'metrics-dispatch-boundaries-5-execute.toon').write_text(
            'plan_id: with-boundary\n'
            'phase: 5-execute\n'
            'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms}:\n'
            '2026-05-08T14:00:00Z,voluntary_checkpoint,100,2,1000\n'
            '2026-05-08T14:01:00Z,unknown,200,4,2000\n'
            '2026-05-08T14:02:00Z,clean_exit_queue_empty,300,6,3000\n',
            encoding='utf-8',
        )
        # Phase-4-plan artifact — new dispatch surface in this lesson.
        (plan_dir / 'work' / 'metrics-dispatch-boundaries-4-plan.toon').write_text(
            'plan_id: with-boundary\n'
            'phase: 4-plan\n'
            'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms}:\n'
            '2026-05-08T14:00:00Z,task_batch_complete,500,10,5000\n',
            encoding='utf-8',
        )
        # Phase-6-finalize artifact — per-step recorder.
        (plan_dir / 'work' / 'metrics-dispatch-boundaries-6-finalize.toon').write_text(
            'plan_id: with-boundary\n'
            'phase: 6-finalize\n'
            'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms}:\n'
            '2026-05-08T14:00:00Z,step_complete,600,12,6000\n'
            '2026-05-08T14:01:00Z,step_complete,700,14,7000\n',
            encoding='utf-8',
        )

        result = _analyze_logs.read_dispatch_boundaries_per_phase(plan_dir)
        # All three phases surface as top-level keys.
        assert set(result.keys()) == {'4-plan', '5-execute', '6-finalize'}

        # Phase-5-execute counters carry through verbatim from the legacy parser.
        p5 = result['5-execute']
        assert p5['present'] is True
        assert len(p5['rows']) == 3
        assert p5['rows'][0]['termination_cause'] == 'voluntary_checkpoint'
        assert p5['unknown_count'] == 1
        assert p5['clean_exit_queue_empty_count'] == 1

        # Phase-4-plan boundary row.
        p4 = result['4-plan']
        assert p4['present'] is True
        assert len(p4['rows']) == 1
        assert p4['rows'][0]['termination_cause'] == 'task_batch_complete'

        # Phase-6-finalize per-step rows.
        p6 = result['6-finalize']
        assert p6['present'] is True
        assert len(p6['rows']) == 2
        assert all(r['termination_cause'] == 'step_complete' for r in p6['rows'])

    # ------------------------------------------------------------------
    # Integration: cmd_run end-to-end
    # ------------------------------------------------------------------

    def test_cmd_run_surfaces_phase5_logging_gaps_and_top_level_dispatch_boundaries(
        self, tmp_path, monkeypatch
    ):
        """End-to-end: cmd_run emits phase5_logging_gaps (three extractors) and
        a top-level dispatch_boundaries per-phase dict.

        Lesson 2026-05-20-12-002 restructured ``dispatch_boundaries`` from a
        sub-key of ``phase5_logging_gaps`` to a top-level fragment so the
        compile-report renderer can emit a dedicated section keyed by phase.
        """
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)

        # Add a tasks/ dir + boundary artifacts for all three phases.
        (plan_dir / 'tasks').mkdir(parents=True, exist_ok=True)
        (plan_dir / 'tasks' / 'TASK-001.json').write_text(
            json.dumps({'number': 1, 'title': 'A', 'status': 'done'}),
            encoding='utf-8',
        )
        (plan_dir / 'work').mkdir(parents=True, exist_ok=True)
        (plan_dir / 'work' / 'metrics-dispatch-boundaries-5-execute.toon').write_text(
            'plan_id: ' + plan_id + '\n'
            'phase: 5-execute\n'
            'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms}:\n'
            '2026-05-08T14:00:00Z,unknown,100,2,1000\n',
            encoding='utf-8',
        )
        (plan_dir / 'work' / 'metrics-dispatch-boundaries-4-plan.toon').write_text(
            'plan_id: ' + plan_id + '\n'
            'phase: 4-plan\n'
            'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms}:\n'
            '2026-05-08T14:00:00Z,task_batch_complete,500,10,5000\n',
            encoding='utf-8',
        )
        (plan_dir / 'work' / 'metrics-dispatch-boundaries-6-finalize.toon').write_text(
            'plan_id: ' + plan_id + '\n'
            'phase: 6-finalize\n'
            'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms}:\n'
            '2026-05-08T14:00:00Z,step_complete,600,12,6000\n',
            encoding='utf-8',
        )

        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()

        # phase5_logging_gaps keeps the three extractor sub-keys (the prior
        # ``dispatch_boundaries`` sub-key has been hoisted out — see below).
        gaps = data['phase5_logging_gaps']
        assert 'outcome_pairing' in gaps
        assert 'dispatch_clustering' in gaps
        assert 'outcome_for_diffed_tasks' in gaps
        assert 'dispatch_boundaries' not in gaps

        # Top-level dispatch_boundaries surfaces every phase artifact discovered
        # by the glob.
        boundaries = data['dispatch_boundaries']
        for phase in ('4-plan', '5-execute', '6-finalize'):
            assert phase in boundaries, f'expected {phase} key in dispatch_boundaries'

    def test_cmd_run_dispatch_boundaries_empty_when_no_artifacts(self, tmp_path, monkeypatch):
        """When no boundary artifacts exist the top-level key is an empty dict
        (vs. absent) — the compile-report renderer's gate distinguishes the
        two states.
        """
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')
        assert result.success, result.stderr
        data = result.toon()
        # Key is present and empty (per the generalised reader contract).
        assert 'dispatch_boundaries' in data
        # The TOON parser may render an empty dict as an empty-string-like or
        # empty-iterable value — accept any falsy representation.
        boundaries = data['dispatch_boundaries']
        if isinstance(boundaries, dict):
            assert boundaries == {}
        else:
            assert not boundaries


# =============================================================================
# Folded-in global-log per-plan signals
# =============================================================================
#
# Under the move-based finalize model the plan's OWN global logs
# (``{prefix}-YYYY-MM-DD.log``) are folded into ``<plan_dir>/logs/``. The
# ``analyze_folded_global_logs`` helper parses those folded-in copies for
# per-plan operational signals (error/non-INFO lines, slow calls, fixture
# leaks) — the per-plan replacement for the retired cross-plan
# ``global-log-analysis`` audit check.


def _line(ts: str, level: str, rest: str, *, hash_: str = '3befe7') -> str:
    """Build one folded-in global-log line in the bracketed grammar."""
    return f'[{ts}] [{level}] [{hash_}] {rest}'


def _write_folded_log(logs_dir: Path, name: str, lines: list[str]) -> None:
    """Write a folded-in global-log file under ``logs_dir/{name}``."""
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / name).write_text('\n'.join(lines) + '\n', encoding='utf-8')


class TestAnalyzeFoldedGlobalLogs:
    def test_no_logs_dir_yields_all_zero_signals(self, tmp_path):
        # Arrange — logs_dir does not exist
        logs_dir = tmp_path / 'logs'

        # Act
        result = _analyze_logs.analyze_folded_global_logs(logs_dir)

        # Assert
        assert result['logs_present'] is False
        assert result['folded_log_files'] == 0
        assert result['total_lines'] == 0
        assert result['error_count'] == 0
        assert result['slow_call_count'] == 0
        assert result['fixture_leak_count'] == 0

    def test_only_canonical_logs_no_folded_globals_yields_no_signals(self, tmp_path):
        # Arrange — canonical per-plan logs only; no date-stamped folded copies
        logs_dir = tmp_path / 'logs'
        _write_folded_log(
            logs_dir,
            'work.log',
            [_line('2026-06-01T10:00:00Z', 'ERROR', '[STATUS] (x) boom')],
        )

        # Act
        result = _analyze_logs.analyze_folded_global_logs(logs_dir)

        # Assert — work.log is NOT a folded ``work-*.log`` glob match
        assert result['logs_present'] is False
        assert result['folded_log_files'] == 0
        assert result['error_count'] == 0

    def test_well_formed_lines_counted_and_error_flagged(self, tmp_path):
        # Arrange — one INFO + one ERROR line in a folded global log
        logs_dir = tmp_path / 'logs'
        _write_folded_log(
            logs_dir,
            'work-2026-06-01.log',
            [
                _line('2026-06-01T10:00:00Z', 'INFO', '[STATUS] (x) ok'),
                _line('2026-06-01T10:00:01Z', 'ERROR', '[STATUS] (x) off'),
            ],
        )

        # Act
        result = _analyze_logs.analyze_folded_global_logs(logs_dir)

        # Assert — both parsed; the ERROR line surfaces in error_count
        assert result['logs_present'] is True
        assert result['folded_log_files'] == 1
        assert result['total_lines'] == 2
        assert result['error_count'] == 1

    def test_info_line_with_failure_marker_flagged(self, tmp_path):
        # Arrange — INFO level but the body carries a fail marker (status: error)
        logs_dir = tmp_path / 'logs'
        _write_folded_log(
            logs_dir,
            'script-execution-2026-06-01.log',
            [_line('2026-06-01T10:00:00Z', 'INFO', 'pm:x:x run -> status: error exit_code: 1')],
        )

        # Act
        result = _analyze_logs.analyze_folded_global_logs(logs_dir)

        # Assert
        assert result['error_count'] == 1

    def test_slow_call_flagged_at_ceiling(self, tmp_path):
        # Arrange — a call at the slow ceiling (30.0s) and a fast call
        logs_dir = tmp_path / 'logs'
        _write_folded_log(
            logs_dir,
            'script-execution-2026-06-01.log',
            [
                _line('2026-06-01T10:00:00Z', 'INFO', 'pm:a:a run (30.0s)'),
                _line('2026-06-01T10:00:01Z', 'INFO', 'pm:b:b run (1.0s)'),
            ],
        )

        # Act
        result = _analyze_logs.analyze_folded_global_logs(logs_dir)

        # Assert — only the >=ceiling call is slow
        assert result['slow_call_count'] == 1

    def test_fixture_leak_signature_flagged(self, tmp_path):
        # Arrange — a synthetic test-fixture id leaked into the folded log
        logs_dir = tmp_path / 'logs'
        _write_folded_log(
            logs_dir,
            'decision-2026-06-01.log',
            [_line('2026-06-01T10:00:00Z', 'INFO', '(x) plan orphan-md-xyz123 resolved')],
        )

        # Act
        result = _analyze_logs.analyze_folded_global_logs(logs_dir)

        # Assert
        assert result['fixture_leak_count'] == 1
        assert 'orphan-md-xyz123' in result['fixture_leak_signatures']

    def test_malformed_lines_skipped(self, tmp_path):
        # Arrange — only the first line matches the bracketed grammar
        logs_dir = tmp_path / 'logs'
        _write_folded_log(
            logs_dir,
            'work-2026-06-01.log',
            [
                _line('2026-06-01T10:00:00Z', 'INFO', '[STATUS] (x) ok'),
                'no bracketed prefix here',
            ],
        )

        # Act
        result = _analyze_logs.analyze_folded_global_logs(logs_dir)

        # Assert — only the well-formed line counted
        assert result['total_lines'] == 1

    def test_cmd_run_surfaces_global_log_signals_and_fixture_leak_finding(self, tmp_path, monkeypatch):
        # Arrange — a live plan whose folded-in global log carries a fixture leak
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch, plan_id='retro-folded-leak')
        _write_folded_log(
            plan_dir / 'logs',
            'work-2026-06-01.log',
            [_line('2026-06-01T10:00:00Z', 'INFO', '[STATUS] fake-test-bundle leaked')],
        )

        # Act
        result = run_script(SCRIPT_PATH, 'run', '--plan-id', plan_id, '--mode', 'live')

        # Assert — the global_log_signals key is present and a leak finding fired
        assert result.success, result.stderr
        data = result.toon()
        assert 'global_log_signals' in data
        signals = data['global_log_signals']
        assert int(signals['fixture_leak_count']) == 1


def _git(repo: Path, *args: str) -> None:
    subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True, text=True)


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, 'init', '-b', 'main')
    _git(repo, 'config', 'user.email', 'test@example.com')
    _git(repo, 'config', 'user.name', 'Test')


class TestResolveFootprintTiers:
    """``resolve_footprint`` resolves live diff, then the legacy key, then empty."""

    def test_tier1_live_diff_when_worktree_resolves(self, tmp_path):
        """A resolvable git worktree yields the live ``{base}...HEAD`` ∪ porcelain set."""
        repo = tmp_path / 'wt'
        _init_repo(repo)
        (repo / 'base.txt').write_text('base\n')
        _git(repo, 'add', '-A')
        _git(repo, 'commit', '-m', 'base')
        _git(repo, 'checkout', '-b', 'feature')
        (repo / 'committed.py').write_text('print("x")\n')
        _git(repo, 'add', '-A')
        _git(repo, 'commit', '-m', 'plan change')
        (repo / 'uncommitted.py').write_text('print("y")\n')

        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        (plan_dir / 'references.json').write_text(json.dumps({'base_branch': 'main'}))
        (plan_dir / 'status.json').write_text(
            json.dumps({'metadata': {'worktree_path': str(repo)}})
        )

        footprint = _analyze_logs.resolve_footprint(plan_dir)
        assert 'committed.py' in footprint
        assert 'uncommitted.py' in footprint
        assert 'base.txt' not in footprint

    def test_tier2_legacy_key_when_no_worktree(self, tmp_path):
        """No worktree → fall back to the legacy ``modified_files`` key."""
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        (plan_dir / 'references.json').write_text(
            json.dumps({'modified_files': ['legacy/a.py', 'legacy/b.py']})
        )

        footprint = _analyze_logs.resolve_footprint(plan_dir)
        assert sorted(footprint) == ['legacy/a.py', 'legacy/b.py']

    def test_tier3_empty_when_neither_resolves(self, tmp_path):
        """No worktree and no legacy key → empty footprint."""
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        (plan_dir / 'references.json').write_text(json.dumps({'domains': []}))

        footprint = _analyze_logs.resolve_footprint(plan_dir)
        assert footprint == []

    def test_tier2_fallback_when_worktree_not_a_git_dir(self, tmp_path):
        """A worktree_path that is not a git tree falls through to the legacy key."""
        plain = tmp_path / 'plain'
        plain.mkdir()

        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        (plan_dir / 'references.json').write_text(
            json.dumps({'modified_files': ['legacy/a.py']})
        )
        (plan_dir / 'status.json').write_text(
            json.dumps({'metadata': {'worktree_path': str(plain)}})
        )

        footprint = _analyze_logs.resolve_footprint(plan_dir)
        assert footprint == ['legacy/a.py']


# =============================================================================
# Voluntary-checkpoint polling detector (tightened)
# =============================================================================
#
# ``detect_voluntary_checkpoint_polling`` was tightened to fire a candidate pair
# ONLY when the 5-line window after an ``[ATTEMPT]`` line carries a GENUINE
# background-poll signal — a ``run_in_background=true`` marker, OR an
# ``until ... sleep ... done`` shell-loop shape. Bare polling-language keywords
# (``wait``, ``background``, ``sleep``) no longer trigger a candidate: those
# produced the false-positive class this detector was tightened to eliminate.
# CI-wait line shapes (``ci checks wait``, ``ci_complete_precondition``) are
# exempt — they contain a generic ``wait`` token but are legitimate synchronous
# CI waits, not voluntary-checkpoint polling.


def _attempt(rest: str = 'dispatch subagent') -> str:
    """Build one ``[ATTEMPT]`` work-log line in the bracketed grammar."""
    return f'[2026-06-13T10:00:00Z] [INFO] [abc123] [ATTEMPT] (plan-marshall:execute-task) {rest}'


def _plain(rest: str) -> str:
    """Build one non-ATTEMPT work-log line carrying arbitrary body text."""
    return f'[2026-06-13T10:00:01Z] [INFO] [def456] [STATUS] (plan-marshall:phase-5-execute) {rest}'


class TestDetectVoluntaryCheckpointPolling:
    """Unit + regression tests for the tightened voluntary-checkpoint detector."""

    # ------------------------------------------------------------------
    # Precondition gate
    # ------------------------------------------------------------------

    def test_precondition_not_met_without_attempt_line(self):
        """No ``[ATTEMPT]`` line → precondition not met, zero candidates."""
        lines = [
            _plain('run_in_background=true'),
            _plain('until x; do sleep 1; done'),
        ]
        result = _analyze_logs.detect_voluntary_checkpoint_polling(lines)
        assert result['precondition_met'] is False
        assert result['polling_pairs_count'] == 0
        assert result['candidate_line_numbers'] == []

    def test_precondition_met_but_no_signal_fires_no_candidate(self):
        """An ``[ATTEMPT]`` line with a benign window → precondition met but
        no candidate. This is the load-bearing false-positive fix: the mere
        presence of an ATTEMPT line is not enough to flag a pair.
        """
        lines = [
            _attempt(),
            _plain('Wrote foo.py'),
            _plain('verification passed'),
        ]
        result = _analyze_logs.detect_voluntary_checkpoint_polling(lines)
        assert result['precondition_met'] is True
        assert result['polling_pairs_count'] == 0
        assert result['candidate_line_numbers'] == []

    # ------------------------------------------------------------------
    # Genuine background-poll signals
    # ------------------------------------------------------------------

    @pytest.mark.parametrize('window_text', [
        'launched Bash with run_in_background=true',
        'config has run_in_background: TRUE here',
    ])
    def test_run_in_background_marker_fires_candidate(self, window_text):
        """``run_in_background=true`` or ``run_in_background: TRUE`` in the
        window fires a candidate — the marker tolerates ``=`` or ``:`` and is
        matched case-insensitively.
        """
        lines = [
            _attempt(),
            _plain(window_text),
        ]
        result = _analyze_logs.detect_voluntary_checkpoint_polling(lines)
        assert result['precondition_met'] is True
        assert result['polling_pairs_count'] == 1
        # ATTEMPT line is index 0 → 1-based line number 1.
        assert result['candidate_line_numbers'] == [1]

    def test_until_sleep_done_shape_spanning_window_fires_candidate(self):
        """An ``until ... sleep ... done`` shape spanning several window lines
        fires a candidate (the hand-rolled poll loop the rule catches).
        """
        lines = [
            _attempt(),
            _plain('until [ -f marker ]; do'),
            _plain('  sleep 5'),
            _plain('done'),
        ]
        result = _analyze_logs.detect_voluntary_checkpoint_polling(lines)
        assert result['polling_pairs_count'] == 1
        assert result['candidate_line_numbers'] == [1]

    # ------------------------------------------------------------------
    # Regression: bare keywords no longer trigger (false-positive class)
    # ------------------------------------------------------------------

    def test_bare_wait_keyword_does_not_fire(self):
        """A bare ``wait`` keyword with no genuine poll signal → no candidate.
        Before the tightening this was a false positive.
        """
        lines = [
            _attempt(),
            _plain('please wait for the build to settle'),
        ]
        result = _analyze_logs.detect_voluntary_checkpoint_polling(lines)
        assert result['precondition_met'] is True
        assert result['polling_pairs_count'] == 0

    def test_bare_background_and_sleep_keywords_do_not_fire(self):
        """Bare ``background`` / ``sleep`` keywords without the
        ``until ... done`` shape or a ``run_in_background=true`` marker →
        no candidate. Guards the false-positive regression.
        """
        lines = [
            _attempt(),
            _plain('moved the task to the background queue'),
            _plain('sleep until the next dispatch'),
        ]
        result = _analyze_logs.detect_voluntary_checkpoint_polling(lines)
        assert result['polling_pairs_count'] == 0

    # ------------------------------------------------------------------
    # CI-wait exemptions
    # ------------------------------------------------------------------

    def test_ci_checks_wait_line_is_exempt(self):
        """A ``ci checks wait`` line in the window is a legitimate synchronous
        CI wait → exempt, never flagged as polling.
        """
        lines = [
            _attempt(),
            _plain('invoking ci checks wait for PR #123'),
        ]
        result = _analyze_logs.detect_voluntary_checkpoint_polling(lines)
        assert result['precondition_met'] is True
        assert result['polling_pairs_count'] == 0

    def test_ci_complete_precondition_marker_is_exempt(self):
        """The ``ci_complete_precondition`` work-log marker is a synchronous
        CI-completion gate → exempt.
        """
        lines = [
            _attempt(),
            _plain('ci_complete_precondition satisfied; continuing'),
        ]
        result = _analyze_logs.detect_voluntary_checkpoint_polling(lines)
        assert result['polling_pairs_count'] == 0

    def test_ci_wait_line_does_not_complete_until_sleep_done_span(self):
        """A CI-wait line is dropped BEFORE the ``until ... sleep ... done``
        scan, so it cannot bridge an otherwise-incomplete poll-loop span.
        Here ``done`` lives only on the exempt CI-wait line, so no candidate.
        """
        lines = [
            _attempt(),
            _plain('until [ -f marker ]; do'),
            _plain('  sleep 5'),
            # The only 'done' token is on the exempt CI-wait line, which is
            # stripped before the span scan → span never completes.
            _plain('ci checks wait done waiting'),
        ]
        result = _analyze_logs.detect_voluntary_checkpoint_polling(lines)
        assert result['polling_pairs_count'] == 0

    def test_ci_wait_does_not_suppress_genuine_signal_on_other_line(self):
        """An exempt CI-wait line in the window must not suppress a genuine
        ``run_in_background=true`` signal sitting on a different window line.
        """
        lines = [
            _attempt(),
            _plain('ci checks wait for PR #123'),
            _plain('also launched run_in_background=true'),
        ]
        result = _analyze_logs.detect_voluntary_checkpoint_polling(lines)
        assert result['polling_pairs_count'] == 1
        assert result['candidate_line_numbers'] == [1]

    # ------------------------------------------------------------------
    # Window boundary + multi-attempt counting
    # ------------------------------------------------------------------

    def test_signal_outside_five_line_window_does_not_fire(self):
        """A genuine signal beyond the 5-line window (lines idx+1..idx+5) is
        out of range → no candidate.
        """
        lines = [
            _attempt(),
            _plain('filler 1'),
            _plain('filler 2'),
            _plain('filler 3'),
            _plain('filler 4'),
            _plain('filler 5'),
            # 6th line after ATTEMPT — outside the window.
            _plain('run_in_background=true'),
        ]
        result = _analyze_logs.detect_voluntary_checkpoint_polling(lines)
        assert result['polling_pairs_count'] == 0

    def test_signal_on_last_window_line_fires(self):
        """A genuine signal on the 5th line after ATTEMPT (last in-window line)
        still fires — boundary inclusive.
        """
        lines = [
            _attempt(),
            _plain('filler 1'),
            _plain('filler 2'),
            _plain('filler 3'),
            _plain('filler 4'),
            _plain('run_in_background=true'),
        ]
        result = _analyze_logs.detect_voluntary_checkpoint_polling(lines)
        assert result['polling_pairs_count'] == 1
        assert result['candidate_line_numbers'] == [1]

    def test_multiple_attempts_count_each_candidate_with_line_numbers(self):
        """Each ATTEMPT line with a genuine signal in its window contributes a
        distinct 1-based candidate line number.
        """
        lines = [
            _attempt('first dispatch'),           # index 0 → line 1 (candidate)
            _plain('run_in_background=true'),      # index 1
            _plain('benign filler'),               # index 2
            _attempt('second dispatch'),           # index 3 → line 4 (candidate)
            _plain('until x; do sleep 1; done'),   # index 4
            _attempt('third dispatch'),            # index 5 → line 6 (no signal)
            _plain('verification passed'),          # index 6
        ]
        result = _analyze_logs.detect_voluntary_checkpoint_polling(lines)
        assert result['precondition_met'] is True
        assert result['polling_pairs_count'] == 2
        assert result['candidate_line_numbers'] == [1, 4]
