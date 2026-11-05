# SPDX-License-Identifier: FSL-1.1-ALv2
"""The lessons Signal-3 scanner counts genuine stalls only.

What it pins:

* a plan whose only phase-5 boundary rows are prescribed build hand-backs
  yields ``signal_3_count == 0``;
* a plan with one genuine B7 no-progress reclassification yields ``1``;
* the marker B7 writes is the marker the scanner matches — asserted against the
  single constant, with the writer's prose required to carry that exact string;
* the `[FAILED]` / `[ERROR] ... script_failure` work-log classes still count, and
  two classes on one notation count once.
"""

from __future__ import annotations

from pathlib import Path

from conftest import load_script_module, run_script

_manage_logging = load_script_module('plan-marshall', 'manage-logging', 'manage-logging.py', 'manage_logging_scan')
_scan = load_script_module('plan-marshall', 'manage-logging', '_signal_scan.py', 'signal_scan_module')

SCRIPT_PATH = Path(_manage_logging.__file__)
REPO_ROOT = Path(__file__).resolve().parents[3]
EXECUTION_MD = (
    REPO_ROOT / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'plan-marshall' / 'workflow' / 'execution.md'
)
FINALIZE_SKILL_MD = REPO_ROOT / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'SKILL.md'
LESSONS_CAPTURE_MD = (
    REPO_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'phase-6-finalize'
    / 'workflow'
    / 'lessons-capture.md'
)

_BOUNDARY_HEADER = 'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms}:\n'


def _seed_plan(
    plan_context, plan_id: str, *, work_lines: list[str], decision_lines: list[str], boundary_rows: list[str]
):
    plan_dir = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'logs').mkdir(parents=True, exist_ok=True)
    (plan_dir / 'work').mkdir(parents=True, exist_ok=True)
    (plan_dir / 'logs' / 'work.log').write_text('\n'.join(work_lines) + ('\n' if work_lines else ''), encoding='utf-8')
    (plan_dir / 'logs' / 'decision.log').write_text(
        '\n'.join(decision_lines) + ('\n' if decision_lines else ''), encoding='utf-8'
    )
    (plan_dir / 'work' / 'metrics-dispatch-boundaries-5-execute.toon').write_text(
        f'plan_id: {plan_id}\nphase: 5-execute\n' + _BOUNDARY_HEADER + ''.join(boundary_rows),
        encoding='utf-8',
    )
    return plan_dir


class TestSignal3CountsGenuineStallsOnly:
    def test_a_plan_of_only_handback_rows_yields_zero(self, plan_context):
        """Two hand-back rows (a re-attach) are the prescribed yield, not a stall."""
        _seed_plan(
            plan_context,
            'scan-handbacks-only',
            work_lines=[],
            decision_lines=[],
            boundary_rows=[
                '2026-05-08T14:00:00Z,verification_handback,100,2,1000\n',
                '2026-05-08T14:01:00Z,verification_handback,150,3,1500\n',
            ],
        )

        result = _scan.scan_signal_3('scan-handbacks-only')

        assert result['signal_3_count'] == 0
        assert result['verification_handback_rows'] == 2
        assert result['notations'] == []

    def test_one_genuine_b7_reclassification_yields_one(self, plan_context):
        """The reclassification is scanned in the DECISION log, where B7 writes it."""
        _seed_plan(
            plan_context,
            'scan-one-reclassification',
            work_lines=[],
            decision_lines=[
                '2026-05-08T14:00:00Z [INFO] (plan-marshall:phase-5-execute:no-progress) '
                'reclassified voluntary_checkpoint as error — in_progress=1, completed_delta=0, tokens=536031',
            ],
            boundary_rows=['2026-05-08T14:00:01Z,error,536031,2,1000\n'],
        )

        result = _scan.scan_signal_3('scan-one-reclassification')

        assert result['signal_3_count'] == 1
        assert result['notations'] == [_scan.NO_PROGRESS_SCOPE]
        assert result['by_class']['no_progress_reclassification'] == 1

    def test_the_work_log_classes_still_count_and_dedupe_by_notation(self, plan_context):
        """A notation failing under two classes counts once — the union rule."""
        _seed_plan(
            plan_context,
            'scan-work-classes',
            work_lines=[
                '2026-05-08T14:00:00Z [ERROR] (plan-marshall:phase-5-execute) '
                '[FAILED] plan-marshall:manage-tasks:manage-tasks failed',
                '2026-05-08T14:00:01Z [ERROR] (plan-marshall:execute-script:2) script_failure '
                'notation=plan-marshall:manage-tasks:manage-tasks exit_code=2 args=--bad',
                '2026-05-08T14:00:02Z [ERROR] (plan-marshall:execute-script:1) script_failure '
                'notation=plan-marshall:manage-metrics:manage-metrics exit_code=1 args=run',
            ],
            decision_lines=[],
            boundary_rows=[],
        )

        result = _scan.scan_signal_3('scan-work-classes')

        assert result['by_class']['failed'] == 1
        assert result['by_class']['script_failure'] == 2
        assert result['signal_3_count'] == 2
        assert result['notations'] == [
            'plan-marshall:manage-metrics:manage-metrics',
            'plan-marshall:manage-tasks:manage-tasks',
        ]

    def test_an_empty_plan_scan_returns_zero_without_error(self, plan_context):
        """No logs at all is a measured zero, not a failure."""
        plan_context.plan_dir_for('scan-empty').mkdir(parents=True, exist_ok=True)

        result = _scan.scan_signal_3('scan-empty')

        assert result['signal_3_count'] == 0
        assert result['verification_handback_rows'] == 0

    def test_cli_signal_scan_is_registered_and_answers(self, plan_context):
        plan_context.plan_dir_for('scan-cli').mkdir(parents=True, exist_ok=True)

        result = run_script(str(SCRIPT_PATH), 'signal-scan', '--plan-id', 'scan-cli')

        assert result.returncode == 0
        assert 'signal_3_count: 0' in result.stdout


class TestTheWriterAndTheScannerShareOneMarker:
    """A doc test that the marker B7 writes is the marker Signal 3 scans for."""

    def test_execution_md_carries_the_scanner_marker_verbatim(self):
        text = EXECUTION_MD.read_text(encoding='utf-8')

        assert _scan.NO_PROGRESS_MARKER in text, (
            'the B7 writer prose in execution.md must carry the exact marker string '
            'manage-logging _signal_scan matches — one string, one log type'
        )
        assert 'decision --plan-id {plan_id}' in text
        assert _scan.NO_PROGRESS_SCOPE in text

    def test_the_dispatcher_scans_with_the_verb_and_names_the_marker(self):
        text = FINALIZE_SKILL_MD.read_text(encoding='utf-8')

        assert 'signal-scan' in text and 'manage-logging' in text, (
            'Signal 3 must be computed by manage-logging signal-scan, not re-derived from a work-log read'
        )
        assert '_signal_scan.py' in text, 'the marker string must be cited from its single source'
        assert 'verification_handback' in text, 'a prescribed hand-back must be named as not lesson-bearing'

    def test_the_workflow_body_cites_the_same_scanner(self):
        text = LESSONS_CAPTURE_MD.read_text(encoding='utf-8')

        assert 'signal-scan' in text, 'lessons-capture.md must cite the scanner that produces its input field'
        assert 'verification_handback' in text, 'the field description must name the excluded hand-back'

    def test_the_dispatcher_names_the_log_its_marker_is_scanned_in(self):
        """Signal 3's marker is scoped to the log it is written to, and to no other consumer."""
        text = FINALIZE_SKILL_MD.read_text(encoding='utf-8')

        assert 'the WORK log carries no copy of it' in text, (
            'the dispatcher must state which log class 3 is read from, as current behaviour'
        )
        assert 'so the two read one string from one writer' not in text, (
            'the retrospective does not read this marker: its script-failure analysis reads '
            'script-execution.log, so no cross-surface marker set exists to align'
        )
        assert 'script-execution.log' in text
