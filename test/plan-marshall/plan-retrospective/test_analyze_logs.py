"""Tests for ``analyze-logs.py``."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _fixtures import setup_archived_plan, setup_broken_plan, setup_live_plan  # noqa: E402

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
