# SPDX-License-Identifier: FSL-1.1-ALv2
"""In-process behavioral tests for ``compile-report.py``.

The sibling ``test_compile_report.py`` exercises the full pipeline through the
``run_script`` subprocess harness plus a few in-process ``cmd_run`` cleanup
cases. This module unit-tests the assembler's pure decision/rendering helpers
IN-PROCESS — ``should_emit`` (every branch), ``_dispatch_boundaries_has_present_phase``,
the two body renderers, ``build_header``/``build_document``, ``resolve_output_path``,
``resolve_plan_dir``, and ``load_fragments`` — plus an in-process archived
``cmd_run`` that the subprocess suite reaches only out-of-process.
"""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest
import retro_sections as _rs

from conftest import load_script_module

_cr = load_script_module('plan-marshall', 'plan-retrospective', 'compile-report.py', 'cr_behavior_mod')


class TestResolvePlanDir:
    def test_live_without_plan_id_raises(self):
        with pytest.raises(ValueError, match='--plan-id is required'):
            _cr.resolve_plan_dir('live', None, None)

    def test_archived_without_path_raises(self):
        with pytest.raises(ValueError, match='--archived-plan-path is required'):
            _cr.resolve_plan_dir('archived', None, None)

    def test_unknown_mode_raises(self):
        with pytest.raises(ValueError, match='Unknown mode'):
            _cr.resolve_plan_dir('bogus', 'p', None)


class TestResolveOutputPath:
    def test_live_overwrites_canonical_filename(self, tmp_path):
        out = _cr.resolve_output_path('live', tmp_path)
        assert out == tmp_path / 'quality-verification-report.md'

    def test_archived_uses_timestamped_audit_filename(self, tmp_path):
        out = _cr.resolve_output_path('archived', tmp_path)
        assert out.parent == tmp_path
        assert out.name.startswith('quality-verification-report-audit-')
        assert out.name.endswith('.md')


class TestLoadFragments:
    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(ValueError, match='does not exist'):
            _cr.load_fragments(tmp_path / 'absent.toon')

    def test_valid_bundle_parsed_to_dict(self, tmp_path):
        bundle = tmp_path / 'fragments.toon'
        bundle.write_text(
            'artifact-consistency:\n  status: success\n  aspect: artifact_consistency\n',
            encoding='utf-8',
        )
        parsed = _cr.load_fragments(bundle)
        assert isinstance(parsed, dict)
        assert 'artifact-consistency' in parsed


class TestDispatchBoundariesHasPresentPhase:
    def test_empty_dict_is_false(self):
        assert _cr._dispatch_boundaries_has_present_phase({}) is False

    def test_non_dict_is_false(self):
        assert _cr._dispatch_boundaries_has_present_phase('nope') is False

    def test_phase_with_present_true_bool(self):
        assert _cr._dispatch_boundaries_has_present_phase({'5-execute': {'present': True}}) is True

    def test_phase_with_present_true_string(self):
        assert _cr._dispatch_boundaries_has_present_phase({'5-execute': {'present': 'true'}}) is True

    def test_no_present_phase_is_false(self):
        assert _cr._dispatch_boundaries_has_present_phase({'5-execute': {'present': False}}) is False

    def test_non_dict_phase_value_skipped(self):
        assert _cr._dispatch_boundaries_has_present_phase({'5-execute': 'x'}) is False


class TestShouldEmit:
    def test_unconditional_section_always_emits(self):
        assert _cr.should_emit('any', None, {}) is True

    def test_dispatch_boundaries_routes_to_present_check(self):
        fragments = {'dispatch_boundaries': {'5-execute': {'present': True}}}
        assert _cr.should_emit('dispatch_boundaries', 'dispatch_boundaries', fragments) is True
        assert _cr.should_emit('dispatch_boundaries', 'dispatch_boundaries', {}) is False

    def test_missing_fragment_is_false(self):
        assert _cr.should_emit('s', 'trigger', {}) is False

    def test_non_success_status_is_false(self):
        fragments = {'trigger': {'status': 'error', 'findings': [{'severity': 'x'}]}}
        assert _cr.should_emit('s', 'trigger', fragments) is False

    def test_non_empty_findings_emits(self):
        fragments = {'trigger': {'status': 'success', 'findings': [{'severity': 'info'}]}}
        assert _cr.should_emit('s', 'trigger', fragments) is True

    def test_non_empty_failures_emits(self):
        fragments = {'trigger': {'failures': [{'notation': 'x'}]}}
        assert _cr.should_emit('s', 'trigger', fragments) is True

    def test_empty_payload_lists_do_not_emit(self):
        fragments = {'trigger': {'status': 'success', 'findings': [], 'prompts': []}}
        assert _cr.should_emit('s', 'trigger', fragments) is False

    def test_manifest_decisions_emits_on_present_flag(self):
        fragments = {'manifest-decisions': {'status': 'success', 'manifest_present': True}}
        assert _cr.should_emit('s', 'manifest-decisions', fragments) is True


class TestRenderDispatchBoundariesBody:
    def test_empty_fragment_renders_placeholder(self):
        body = _cr.render_dispatch_boundaries_body({})
        assert 'No dispatch-boundary artifacts present' in body

    def test_present_phase_renders_table_row(self):
        fragment = {
            '5-execute': {
                'present': True,
                'rows': [{'x': 1}, {'x': 2}],
                'unknown_count': 1,
                'clean_exit_queue_empty_count': 3,
                'error_total_tokens': 10000,
                'retryable_total_tokens': 16000,
                'returned_with_findings_count': 2,
            },
            '4-plan': {'present': False},
        }
        body = _cr.render_dispatch_boundaries_body(fragment)
        # The present phase renders its row count, the genuinely-wasted vs
        # retryable spend split, the productive-loop-back count, and the legacy
        # cause counts; the absent phase is skipped.
        assert '| 5-execute | 2 | 10000 | 16000 | 2 | 1 | 3 |' in body
        assert '| 4-plan |' not in body

    def test_present_phase_defaults_new_figures_to_zero(self):
        """A phase entry missing the new figures renders them as 0, not a crash."""
        fragment = {
            '6-finalize': {
                'present': True,
                'rows': [{'x': 1}],
                'unknown_count': 0,
                'clean_exit_queue_empty_count': 0,
            }
        }
        body = _cr.render_dispatch_boundaries_body(fragment)
        assert '| 6-finalize | 1 | 0 | 0 | 0 | 0 | 0 |' in body


class TestRenderSectionBody:
    def test_none_fragment_placeholder(self):
        assert 'No data provided' in _cr.render_section_body(None)

    def test_non_dict_fragment_fenced(self):
        body = _cr.render_section_body('raw text')
        assert 'raw text' in body
        assert body.startswith('```')

    def test_summary_and_findings_rendered(self):
        fragment = {
            'summary': 'Two issues found.',
            'findings': [
                {'severity': 'warning', 'message': 'first'},
                'not-a-dict-skipped',
                {'severity': 'error', 'message': 'second'},
            ],
        }
        body = _cr.render_section_body(fragment)
        assert 'Two issues found.' in body
        assert '- [WARNING] first' in body
        assert '- [ERROR] second' in body
        assert '```json' in body


class TestBuildHeader:
    def test_session_id_rendered_when_provided(self, tmp_path):
        header = _cr.build_header('demo', 'live', tmp_path, 'sess-9')
        assert '# Plan Retrospective — demo' in header
        assert 'session_id: sess-9' in header
        assert 'mode: live' in header

    def test_session_id_defaults_when_absent(self, tmp_path):
        header = _cr.build_header('demo', 'archived', tmp_path, None)
        assert 'session_id: not provided' in header


class TestBuildDocument:
    def test_executive_summary_from_dict_fragment(self, tmp_path):
        fragments = {'_executive-summary': {'summary': 'All green.'}}
        content, written, _omitted, _dropped = _cr.build_document('demo', 'live', tmp_path, None, fragments)
        assert 'All green.' in content
        assert 'Executive Summary' in written

    def test_executive_summary_from_plain_string(self, tmp_path):
        fragments = {'_executive-summary': 'String summary here'}
        content, _written, _omitted, _dropped = _cr.build_document('demo', 'live', tmp_path, None, fragments)
        assert 'String summary here' in content

    def test_missing_executive_summary_emits_no_section(self, tmp_path):
        # REGRESSION (D1). The compiler used to emit a heading whose entire body
        # was the literal ``_No executive summary provided._`` placeholder. An
        # empty heading is forbidden by ``references/report-structure.md``
        # § "Conditional Rule", and counting one as written breaks the partition
        # invariant *written implies non-empty*.
        content, written, omitted, dropped = _cr.build_document('demo', 'live', tmp_path, None, {})
        assert 'No executive summary provided' not in content
        assert '## Executive Summary' not in content
        assert 'Executive Summary' not in written
        # Absent fragment ⇒ nothing was lost ⇒ benign omission, not a drop.
        assert 'Executive Summary' in omitted
        assert 'Executive Summary' not in dropped

    def test_conditional_section_omitted_when_no_data(self, tmp_path):
        # No script-failure-analysis fragment → that conditional section is omitted.
        content, _written, omitted, dropped = _cr.build_document('demo', 'live', tmp_path, None, {})
        assert 'Script Failure Analysis' in omitted
        assert '## Script Failure Analysis' not in content
        assert dropped == []

    def test_payload_bearing_trigger_fragment_is_dropped_not_omitted(self, tmp_path):
        # The trigger fragment carries findings the gate refuses (non-success
        # status), so the section is a loud drop rather than a benign omission.
        fragments = {
            'script-failure-analysis': {
                'status': 'error',
                'aspect': 'script_failure_analysis',
                'findings': [{'severity': 'warning', 'message': 'blew up'}],
            }
        }
        _content, _written, omitted, dropped = _cr.build_document('demo', 'live', tmp_path, None, fragments)
        assert 'Script Failure Analysis' in dropped
        assert 'Script Failure Analysis' not in omitted


class TestWrittenImpliesNonEmpty:
    """D1 regression: the partition invariant *written implies non-empty*.

    The compiler used to append the Executive Summary heading to ``written``
    UNCONDITIONALLY — including on the branch whose whole body is the literal
    ``_No executive summary provided._`` placeholder. A headline section with no
    content then rode the clean half of a partition whose loud half exists to
    make content loss visible.
    """

    def test_placeholder_executive_summary_is_not_listed_as_written(self, tmp_path):
        _content, written, _omitted, _dropped = _cr.build_document('demo', 'live', tmp_path, None, {})
        assert 'Executive Summary' not in written


    def test_payload_bearing_executive_summary_without_a_body_is_dropped(self, tmp_path):
        # The fragment carried content the renderer could not turn into a body
        # (no ``summary`` key). That is a LOSS, so it takes the loud half of the
        # partition rather than the benign one.
        fragments = {'_executive-summary': {'narrative': 'written to the wrong key'}}
        content, written, omitted, dropped = _cr.build_document('demo', 'live', tmp_path, None, fragments)
        assert '## Executive Summary' not in content
        assert 'Executive Summary' not in written
        assert 'Executive Summary' in dropped
        assert 'Executive Summary' not in omitted


class TestZeroReportingSectionNamesItsCheckedSet:
    """D1's second property: a section reporting zero must say what it checked.

    Every *"zero findings"* line is ambiguous between *looked and found nothing*
    and *could not look*, and the checked set is the discriminator.
    """

    @staticmethod
    def _doc(fragments):
        _content, written, _omitted, _dropped = _cr.build_document(
            'demo', 'live', Path('/tmp/plan'), None, fragments
        )
        return written, _cr.unattributed_zero_sections(written, fragments)

    def test_bare_zero_is_flagged(self):
        # The defect: an empty findings list and nothing naming the population.
        fragments = {'direct-gh-glab-usage': {'status': 'success', 'findings': []}}
        written, flagged = self._doc(fragments)
        assert 'Direct gh/glab Usage' in written, 'precondition: the section must render'
        assert 'Direct gh/glab Usage' in flagged

    @pytest.mark.parametrize('field', _rs.ZERO_ATTRIBUTION_FIELDS)
    def test_every_attribution_field_clears_the_flag(self, field):
        # Quantified over the registry, not over a hand-listed subset, so a field
        # added to ZERO_ATTRIBUTION_FIELDS later is covered without an edit here.
        fragments = {
            'direct-gh-glab-usage': {'status': 'success', 'findings': [], field: {'total': 0}},
        }
        written, flagged = self._doc(fragments)
        assert 'Direct gh/glab Usage' in written
        assert 'Direct gh/glab Usage' not in flagged

    def test_a_measured_population_of_zero_still_counts_as_attribution(self):
        # ``evaluated_population: 0`` is the honest "I looked at nothing, and
        # here is that number". ``False == 0`` in Python, so an equality-based
        # sentinel test would discard exactly this case.
        fragments = {
            'direct-gh-glab-usage': {'status': 'success', 'findings': [], 'evaluated_population': 0},
        }
        _written, flagged = self._doc(fragments)
        assert 'Direct gh/glab Usage' not in flagged

    @pytest.mark.parametrize('status', sorted(_rs.ZERO_DECLARED_UNMEASURED_STATUSES))
    def test_declared_unmeasured_status_is_not_an_unattributed_zero(self, status):
        # A fragment that DECLARES it could not look is already unambiguous.
        fragment = {'status': status, 'findings': []}
        assert _cr._names_checked_set(fragment) is True

    def test_a_section_reporting_findings_is_not_a_zero(self):
        fragments = {
            'direct-gh-glab-usage': {
                'status': 'success',
                'findings': [{'severity': 'error', 'message': 'leak'}],
            },
        }
        _written, flagged = self._doc(fragments)
        assert 'Direct gh/glab Usage' not in flagged

    def test_a_fragment_with_no_findings_key_makes_no_zero_claim(self):
        assert _cr._reports_zero({'status': 'success', 'counts': {'total': 3}}) is False

    def test_only_written_sections_are_probed(self):
        # An omitted section reported nothing at all, so it cannot be an
        # unattributed zero. Probing the whole registry instead of the written
        # set would flag every absent section on every run.
        fragments = {'direct-gh-glab-usage': {'status': 'success', 'findings': []}}
        written, flagged = self._doc(fragments)
        assert 'Script Failure Analysis' not in written
        assert flagged == ['Direct gh/glab Usage']

    def test_probe_bites_only_on_the_defect_it_names(self):
        # Mutation check: the SAME fragment with its attribution restored must
        # stop being flagged. A probe that flagged both (or neither) would be
        # asserting something other than the property it is named for.
        defective = {'direct-gh-glab-usage': {'status': 'success', 'findings': []}}
        attributed = {
            'direct-gh-glab-usage': {
                'status': 'success',
                'findings': [],
                'counts': {'total': 0, 'by_surface': {'log_leak': 0, 'diff_leak': 0}},
            },
        }
        assert self._doc(defective)[1] == ['Direct gh/glab Usage']
        assert self._doc(attributed)[1] == []


class TestFragmentHasPayload:
    def test_non_dict_is_false(self):
        assert _cr._fragment_has_payload('nope') is False
        assert _cr._fragment_has_payload(None) is False

    def test_envelope_only_fragment_is_false(self):
        assert _cr._fragment_has_payload({'status': 'success', 'aspect': 'x'}) is False

    def test_empty_payload_values_are_false(self):
        fragment = {'status': 'success', 'findings': [], 'summary': '', 'extra': None, 'flag': False}
        assert _cr._fragment_has_payload(fragment) is False

    def test_any_non_empty_non_envelope_value_is_true(self):
        assert _cr._fragment_has_payload({'status': 'error', 'findings': [{'severity': 'x'}]}) is True

    def test_numeric_zero_counts_as_payload(self):
        # ``False == 0`` and ``False == 0.0`` in Python, so an equality-based
        # sentinel tuple would misclassify a zero-valued count or ratio as
        # carrying no payload — silently dropping the very content this
        # discriminator exists to make loud.
        assert _cr._fragment_has_payload({'status': 'success', 'aspect': 'probe', 'unknown_count': 0}) is True
        assert _cr._fragment_has_payload({'status': 'success', 'aspect': 'probe', 'pass_ratio': 0.0}) is True


class TestCmdRunInProcess:
    def _write_bundle(self, path: Path) -> Path:
        path.write_text(
            '_executive-summary:\n'
            '  summary: "Probe run."\n'
            'artifact-consistency:\n'
            '  status: success\n'
            '  aspect: artifact_consistency\n',
            encoding='utf-8',
        )
        return path

    def test_archived_run_writes_audit_report_and_deletes_bundle(self, tmp_path):
        plan_dir = tmp_path / 'archived-plan'
        plan_dir.mkdir()
        bundle = self._write_bundle(tmp_path / 'fragments.toon')
        args = Namespace(
            command='run',
            plan_id=None,
            archived_plan_path=str(plan_dir),
            mode='archived',
            fragments_file=str(bundle),
            session_id=None,
        )

        result = _cr.cmd_run(args)

        assert result['status'] == 'success'
        assert result['mode'] == 'archived'
        output_path = Path(result['output_path'])
        assert output_path.exists()
        assert output_path.name.startswith('quality-verification-report-audit-')
        assert 'Executive Summary' in result['sections_written']
        # Successful compile auto-deletes the fragments bundle.
        assert not bundle.exists()

    def test_missing_plan_dir_raises(self, tmp_path):
        bundle = self._write_bundle(tmp_path / 'fragments.toon')
        args = Namespace(
            command='run',
            plan_id=None,
            archived_plan_path=str(tmp_path / 'no-such-plan'),
            mode='archived',
            fragments_file=str(bundle),
            session_id=None,
        )
        with pytest.raises(ValueError, match='Plan directory does not exist'):
            _cr.cmd_run(args)
