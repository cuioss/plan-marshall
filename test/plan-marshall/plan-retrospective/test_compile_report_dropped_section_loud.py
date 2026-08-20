# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``compile-report.py``."""


from __future__ import annotations

from _compile_report_fixtures import (
    SCRIPT_PATH,
    _write_fragments_with_dispatch_boundaries,
    _write_fragments_with_extra,
)
from _plan_retrospective_fixtures import setup_live_plan  # noqa: E402

from conftest import run_script  # noqa: E402


class TestPhaseDispatchBoundariesSection:
    """Rendering tests for the Phase Dispatch Boundaries section."""

    def test_section_emitted_when_fragment_has_present_phase(self, tmp_path, monkeypatch):
        """The section emits when at least one phase reports present=true."""
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        fragments = _write_fragments_with_dispatch_boundaries(
            tmp_path,
            phases={
                '5-execute': {
                    'present': True,
                    'rows': [],
                    'unknown_count': 0,
                    'clean_exit_queue_empty_count': 3,
                },
            },
        )
        result = run_script(
            SCRIPT_PATH,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--fragments-file',
            str(fragments),
        )
        assert result.success, result.stderr
        data = result.toon()
        assert 'Phase Dispatch Boundaries' in data['sections_written']
        content = (plan_dir / 'quality-verification-report.md').read_text(encoding='utf-8')
        assert '## Phase Dispatch Boundaries' in content
        # The per-phase markdown table renders with one row per recorded phase.
        # Columns: phase | rows | error_total_tokens (wasted) | retryable_total_tokens
        #          | returned_with_findings | unknown_count | clean_exit_queue_empty_count.
        # This fixture carries none of the new figures, so they default to 0.
        assert '| 5-execute | 0 | 0 | 0 | 0 | 0 | 3 |' in content

    def test_section_omitted_when_fragment_absent(self, tmp_path, monkeypatch):
        """No fragment ⇒ section is omitted (gate returns false)."""
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        fragments = _write_fragments_with_dispatch_boundaries(tmp_path, phases=None)
        result = run_script(
            SCRIPT_PATH,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--fragments-file',
            str(fragments),
        )
        assert result.success, result.stderr
        data = result.toon()
        # Absent fragment ⇒ benign omission, never a drop.
        assert data['status'] == 'success'
        assert 'Phase Dispatch Boundaries' in data['sections_omitted']
        assert not data.get('sections_dropped')
        content = (plan_dir / 'quality-verification-report.md').read_text(encoding='utf-8')
        assert '## Phase Dispatch Boundaries' not in content

    def test_per_phase_table_renders_one_row_per_recorded_phase(self, tmp_path, monkeypatch):
        """All three phases (4-plan, 5-execute, 6-finalize) appear as table rows."""
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        fragments = _write_fragments_with_dispatch_boundaries(
            tmp_path,
            phases={
                '4-plan': {
                    'present': True,
                    'rows': [],
                    'unknown_count': 0,
                    'clean_exit_queue_empty_count': 0,
                },
                '5-execute': {
                    'present': True,
                    'rows': [],
                    'unknown_count': 1,
                    'clean_exit_queue_empty_count': 2,
                },
                '6-finalize': {
                    'present': True,
                    'rows': [],
                    'unknown_count': 0,
                    'clean_exit_queue_empty_count': 0,
                    'error_total_tokens': 10000,
                    'retryable_total_tokens': 16000,
                    'returned_with_findings_count': 2,
                },
            },
        )
        result = run_script(
            SCRIPT_PATH,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--fragments-file',
            str(fragments),
        )
        assert result.success, result.stderr
        content = (plan_dir / 'quality-verification-report.md').read_text(encoding='utf-8')
        # Per-phase markdown table includes one row per recorded phase, sorted.
        # Columns: phase | rows | error_total_tokens (wasted) | retryable_total_tokens
        #          | returned_with_findings | unknown_count | clean_exit_queue_empty_count.
        assert '| 4-plan | 0 | 0 | 0 | 0 | 0 | 0 |' in content
        assert '| 5-execute | 0 | 0 | 0 | 0 | 1 | 2 |' in content
        # 6-finalize carries the genuinely-wasted vs retryable split distinctly.
        assert '| 6-finalize | 0 | 10000 | 16000 | 2 | 0 | 0 |' in content


class TestDroppedSectionIsLoud:
    """A section whose trigger fragment carries real payload is a DROP, not an omission.

    The distinction the partition exists to make: an absent or genuinely empty
    trigger fragment is a benign omission that leaves ``status: success``,
    while a trigger fragment carrying content the gate refused is content the
    report lost — it lands in ``sections_dropped`` and flips the TOON status to
    ``warning`` so the caller cannot mistake the run for clean.
    """

    def test_dispatch_boundaries_without_present_phase_is_dropped(self, tmp_path, monkeypatch):
        # Per-phase entries exist (real payload) but no phase reports
        # present: true, so should_emit refuses — that is a drop, not an omission.
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        fragments = _write_fragments_with_dispatch_boundaries(
            tmp_path,
            phases={
                '5-execute': {
                    'present': False,
                    'rows': [],
                    'unknown_count': 0,
                    'clean_exit_queue_empty_count': 0,
                },
            },
        )

        result = run_script(
            SCRIPT_PATH,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--fragments-file',
            str(fragments),
        )

        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'warning'
        assert 'Phase Dispatch Boundaries' in data['sections_dropped']
        assert 'Phase Dispatch Boundaries' not in data['sections_omitted']
        assert 'Phase Dispatch Boundaries' in data['message']

    def test_non_success_status_with_findings_is_dropped(self, tmp_path, monkeypatch):
        # A registered conditional aspect that produced findings but reports a
        # non-success status: the gate refuses it, so the findings are lost.
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        fragments = _write_fragments_with_extra(
            tmp_path,
            [
                'script-failure-analysis:',
                '  status: error',
                '  aspect: script_failure_analysis',
                '  findings[1]{severity,message}:',
                '    warning,producer blew up mid-run',
            ],
            'fragments-non-success-findings.toon',
        )

        result = run_script(
            SCRIPT_PATH,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--fragments-file',
            str(fragments),
        )

        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'warning'
        assert 'Script Failure Analysis' in data['sections_dropped']
        assert 'Script Failure Analysis' not in data['sections_omitted']

    def test_bookkeeping_only_fragment_is_a_benign_omission(self, tmp_path, monkeypatch):
        # Envelope keys plus an empty payload list carry nothing the report
        # could have rendered — a benign omission that keeps status: success.
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        fragments = _write_fragments_with_extra(
            tmp_path,
            [
                'permission-prompt-analysis:',
                '  status: success',
                '  aspect: permission_prompt_analysis',
                '  prompts[0]:',
            ],
            'fragments-bookkeeping-only.toon',
        )

        result = run_script(
            SCRIPT_PATH,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--fragments-file',
            str(fragments),
        )

        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        assert 'Permission Prompt Analysis' in data['sections_omitted']
        assert not data.get('sections_dropped')

    def test_unregistered_aspect_is_rendered_by_the_catch_all(self, tmp_path, monkeypatch):
        # Regression guard for the generic fallback: a domain-contributed key
        # with no SECTION_SPEC row is rendered under a synthesized heading and
        # is therefore neither omitted nor dropped.
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        fragments = _write_fragments_with_extra(
            tmp_path,
            [
                'wrapper-tangle:',
                '  status: success',
                '  aspect: wrapper_tangle',
                '  findings[1]{severity,message}:',
                '    info,domain aspect with no SECTION_SPEC row',
            ],
            'fragments-unregistered-aspect.toon',
        )

        result = run_script(
            SCRIPT_PATH,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--fragments-file',
            str(fragments),
        )

        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        assert 'Wrapper Tangle' in data['sections_written']
        assert 'Wrapper Tangle' not in data['sections_omitted']
        assert 'Wrapper Tangle' not in (data.get('sections_dropped') or [])
        content = (plan_dir / 'quality-verification-report.md').read_text(encoding='utf-8')
        assert '## Wrapper Tangle' in content
