# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``compile-report.py``.

Scope: when a section is dropped loudly rather than omitted benignly, observed
end-to-end through the ``run_script`` subprocess harness — plus the catch-all
that still renders an unregistered aspect.

The partition asks the render path's own question: a refused section that WOULD
have rendered a usable body is a drop; one that would not is an omission. The
in-process unit cases for that predicate live in
``test_compile_report_behavior_fragment_payload.py``; this module pins the
same rule as it reaches the returned TOON — including that a drop, and ONLY a
drop, raises the run status to ``warning``.
"""


from __future__ import annotations

from _compile_report_fixtures import (
    SCRIPT_PATH,
    _write_fragments_with_dispatch_boundaries,
    _write_fragments_with_extra,
)
from _plan_retrospective_fixtures import setup_live_plan  # noqa: E402

from conftest import run_script  # noqa: E402


def _compile(plan_id, fragments):
    """Run the compiler over ``fragments`` and return its parsed TOON."""
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
    return result.toon()


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
        data = _compile(plan_id, fragments)
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
        data = _compile(plan_id, fragments)
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
    """A refused section that WOULD have rendered a usable body is a DROP.

    A drop is content the aspect produced and the report lost, so it lands in
    ``sections_dropped`` and flips the TOON status to ``warning``. Anything else
    is a benign omission that leaves ``status: success``.
    """

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

        data = _compile(plan_id, fragments)
        assert data['status'] == 'warning'
        assert 'Script Failure Analysis' in data['sections_dropped']
        assert 'Script Failure Analysis' not in data['sections_omitted']
        assert 'Script Failure Analysis' in data['message']

    def test_non_dict_fragment_carrying_prose_is_dropped(self, tmp_path, monkeypatch):
        """⛔ The silent content loss the partition used to miss entirely.

        ``_fragment_has_payload`` is ``False`` for every non-dict, so a producer
        that wrote prose instead of a fragment landed in ``sections_omitted``
        with ``dropped == []`` — the report lost the content AND reported a
        clean run. The render path has always been able to render this value.
        """
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        fragments = _write_fragments_with_extra(
            tmp_path,
            ['script-failure-analysis: the producer wrote a sentence, not a fragment'],
            'fragments-non-dict-prose.toon',
        )

        data = _compile(plan_id, fragments)
        assert data['status'] == 'warning'
        assert 'Script Failure Analysis' in data['sections_dropped']
        assert 'Script Failure Analysis' not in data['sections_omitted']


class TestBenignOmissionStaysClean:
    """Shapes that render nothing: omitted, and the run stays ``success``."""

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

        data = _compile(plan_id, fragments)
        assert data['status'] == 'success'
        assert 'Permission Prompt Analysis' in data['sections_omitted']
        assert not data.get('sections_dropped')

    def test_dispatch_boundaries_without_present_phase_is_omitted(self, tmp_path, monkeypatch):
        """Per-phase entries exist, but none is ``present`` — so nothing renders.

        This shape was previously a DROP, because a per-phase dict is payload to
        the container predicate. It is an omission: the section's own renderer
        prints ``_No dispatch-boundary artifacts present._`` for exactly this
        input, so there is no body for the report to have lost.
        """
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

        data = _compile(plan_id, fragments)
        assert data['status'] == 'success'
        assert 'Phase Dispatch Boundaries' in data['sections_omitted']
        assert not data.get('sections_dropped')
        assert 'message' not in data

    def test_clean_run_script_failure_analysis_keeps_the_run_clean(self, tmp_path, monkeypatch):
        """⛔ The headline case: no script failures must not read as a lossy run.

        The real clean-run fragment carries provenance and zero-valued counters
        beside its empty lists, so the container predicate saw payload and every
        such plan reported ``status: warning``.
        """
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        fragments = _write_fragments_with_extra(
            tmp_path,
            [
                'script-failure-analysis:',
                '  status: success',
                '  aspect: script_failure_analysis',
                '  plan_id: demo-plan',
                '  total_failures: 0',
                '  unique_failures: 0',
                '  failures[0]:',
                '  findings[0]:',
            ],
            'fragments-clean-script-failure.toon',
        )

        data = _compile(plan_id, fragments)
        assert data['status'] == 'success'
        assert 'Script Failure Analysis' in data['sections_omitted']
        assert not data.get('sections_dropped')


class TestUnregisteredAspectCatchAll:
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

        data = _compile(plan_id, fragments)
        assert data['status'] == 'success'
        assert 'Wrapper Tangle' in data['sections_written']
        assert 'Wrapper Tangle' not in data['sections_omitted']
        assert 'Wrapper Tangle' not in (data.get('sections_dropped') or [])
        content = (plan_dir / 'quality-verification-report.md').read_text(encoding='utf-8')
        assert '## Wrapper Tangle' in content
