# SPDX-License-Identifier: FSL-1.1-ALv2
"""In-process behavioral tests for ``compile-report.py``.

Scope: the drop-versus-omit partition and the predicate that decides it.

The partition is decided by ONE question, asked of the fragment the renderer
would have been handed — *is there content this section's renderer would have
shown, or content it structurally cannot show?* This module pins that question
directly and pins the container predicate (``_fragment_has_payload``) it must
NOT be confused with: the two disagree on exactly the shapes the partition used
to misfile, so a test module that exercised only the container predicate could
not witness the difference.

⛔ One question, resolved against TWO renderers, and the second half of it is
live for only one of them. A conditional row is rendered by
``render_section_body``, whose trailing JSON dump is TOTAL — every key the
fragment carries is shown whenever the section emits — so nothing it holds is
structurally unshowable and the question collapses to its reader-facing arm,
``_renders_usable_body``, alone. The Executive Summary is rendered from
``summary`` alone with no dump, so payload under any other key is unreachable by
construction and the second half survives: ``_exec_summary_is_drop``. Both
instantiations are pinned below, each against the control that bounds it.
"""


from __future__ import annotations

from argparse import Namespace
from pathlib import Path

import pytest
from _compile_report_behavior_fixtures import _cr


class TestRendersUsableBody:
    """The partition's discriminator, exercised directly.

    Grouped by the shape being judged rather than by expected answer, so each
    positive sits next to the negative that bounds it.
    """

    # -- dicts: reader-facing content is the summary prose or the findings ----

    def test_summary_prose_is_a_usable_body(self):
        assert _cr._renders_usable_body({'status': 'success', 'summary': 'Two roles drifted.'}) is True

    def test_whitespace_only_summary_is_not_a_usable_body(self):
        # A summary of blanks renders a heading over nothing.
        assert _cr._renders_usable_body({'status': 'success', 'summary': '   \n '}) is False

    def test_non_empty_findings_are_a_usable_body(self):
        fragment = {'status': 'error', 'findings': [{'severity': 'warning', 'message': 'boom'}]}
        assert _cr._renders_usable_body(fragment) is True

    def test_empty_findings_list_is_not_a_usable_body(self):
        assert _cr._renders_usable_body({'status': 'success', 'findings': []}) is False

    def test_bookkeeping_and_provenance_alone_are_not_a_usable_body(self):
        """⛔ The load-bearing case, and the reason a key blocklist is not the fix.

        This is the REAL clean-run ``script-failure-analysis`` shape: provenance
        (``plan_id``), zero-valued counters, and two empty lists. Every one of
        those is payload to ``_fragment_has_payload`` — and a numeric ``0`` is
        payload *deliberately*, so blocklisting ``plan_id`` would not change the
        verdict either. Rendering it produces a heading over a JSON block that
        states nothing, so it is an omission, not a drop.
        """
        fragment = {
            'aspect': 'script_failure_analysis',
            'status': 'success',
            'plan_id': 'demo-plan',
            'total_failures': 0,
            'unique_failures': 0,
            'failures': [],
            'findings': [],
        }
        assert _cr._renders_usable_body(fragment) is False
        # The matched control: the container predicate DOES see payload here.
        # Without this line the assertion above would read as "the fragment is
        # empty", which is the misreading the whole partition turned on.
        assert _cr._fragment_has_payload(fragment) is True

    def test_a_skipped_fragment_naming_its_reason_is_not_a_usable_body(self):
        """A self-declared skip renders nothing, whatever else it carries.

        ``skip_reason`` is non-envelope payload, which is why this shape used to
        be classified a DROP and raise a clean run to ``warning``.
        """
        fragment = {
            'status': 'skipped',
            'aspect': 'script_failure_analysis',
            'skip_reason': 'no script-execution.log for this plan',
            'findings': [],
        }
        assert _cr._renders_usable_body(fragment) is False
        assert _cr._fragment_has_payload(fragment) is True

    def test_a_skipped_fragment_carrying_findings_is_still_a_usable_body(self):
        """⛔ The carve-out control — a skip that DOES have something to say.

        ``chat-history-analysis`` emits ``status: skipped`` plus a warning
        finding the reference requires to be visible. If the skip shape alone
        decided the answer, this fragment would be silently reclassified and the
        carve-out would stop meaning anything.
        """
        fragment = {
            'status': 'skipped',
            'aspect': 'chat_history_analysis',
            'skip_reason': 'no --session-id supplied',
            'findings': [{'severity': 'warning', 'message': 'chat history unavailable'}],
        }
        assert _cr._renders_usable_body(fragment) is True

    # -- non-dicts: the value itself is the content --------------------------

    @pytest.mark.parametrize(
        'fragment',
        ['a bare line of real prose', 7, 0, [1, 2], ('x',)],
        ids=['string', 'int', 'zero', 'list', 'tuple'],
    )
    def test_non_dict_with_content_is_a_usable_body(self, fragment):
        """⛔ The silent-loss half of the defect.

        ``_fragment_has_payload`` reports ``False`` for EVERY non-dict, so a
        producer that wrote prose instead of a fragment used to land in
        ``sections_omitted`` with ``dropped == []`` — content lost with no
        signal at all. ``0`` is included deliberately: it renders a value a
        reader can act on.
        """
        assert _cr._renders_usable_body(fragment) is True
        assert _cr._fragment_has_payload(fragment) is False

    @pytest.mark.parametrize(
        'fragment',
        [None, '', '   ', [], (), False],
        ids=['none', 'empty-string', 'blank-string', 'empty-list', 'empty-tuple', 'false'],
    )
    def test_empty_non_dict_is_not_a_usable_body(self, fragment):
        assert _cr._renders_usable_body(fragment) is False


class TestPartitionOverBuildDocument:
    """The same question, observed through ``build_document``'s partition."""

    def test_clean_run_script_failure_analysis_is_omitted_not_dropped(self, tmp_path):
        """Every plan with no script failures must report a clean run."""
        fragment = {
            'aspect': 'script_failure_analysis',
            'status': 'success',
            'plan_id': 'demo-plan',
            'total_failures': 0,
            'failures': [],
            'findings': [],
        }
        _c, _w, omitted, dropped = _cr.build_document(
            'demo', 'live', tmp_path, None, {'script-failure-analysis': fragment}
        )
        assert 'Script Failure Analysis' in omitted
        assert dropped == []

    def test_a_bare_skipped_fragment_is_a_benign_omission(self, tmp_path):
        fragment = {'status': 'skipped', 'aspect': 'script_failure_analysis', 'findings': []}
        _c, _w, omitted, dropped = _cr.build_document(
            'demo', 'live', tmp_path, None, {'script-failure-analysis': fragment}
        )
        assert 'Script Failure Analysis' in omitted
        assert dropped == []

    def test_a_skipped_fragment_naming_its_reason_is_a_benign_omission(self, tmp_path):
        """Was a DROP before the partition asked the render path's question."""
        fragment = {
            'status': 'skipped',
            'aspect': 'script_failure_analysis',
            'skip_reason': 'no script-execution.log for this plan',
            'findings': [],
        }
        _c, _w, omitted, dropped = _cr.build_document(
            'demo', 'live', tmp_path, None, {'script-failure-analysis': fragment}
        )
        assert 'Script Failure Analysis' in omitted
        assert dropped == []

    def test_a_bare_string_fragment_on_a_conditional_row_is_a_loud_drop(self, tmp_path):
        _c, _w, omitted, dropped = _cr.build_document(
            'demo', 'live', tmp_path, None, {'script-failure-analysis': 'producer wrote prose'}
        )
        assert dropped == ['Script Failure Analysis']
        assert 'Script Failure Analysis' not in omitted


class TestFragmentHasPayload:
    """The CONTAINER predicate — unchanged, and deliberately not the partition.

    It still backs ``_fragment_renders_empty`` and therefore the
    *written implies non-empty* invariant on the EMIT path. These cases pin that
    it kept its meaning while the partition moved off it.
    """

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


class TestExecutiveSummaryResolvesTheQuestionAgainstItsOwnRenderer:
    """⛔ The second instantiation, and the control proving it did not leak.

    ``build_document`` renders this row from ``summary`` ALONE — no
    ``render_section_body``, no JSON dump — so a key other than ``summary`` holds
    content NO render path can show. The reader-facing arm alone would call that
    a benign omission and lose it silently, which is why this branch keeps the
    "cannot show" clause the conditional branch must never acquire.
    """

    def test_a_narrative_written_to_the_wrong_key_is_a_loud_drop(self, tmp_path):
        fragments = {'_executive-summary': {'narrative': 'written to the wrong key'}}
        content, written, omitted, dropped = _cr.build_document(
            'demo', 'live', tmp_path, None, fragments
        )
        assert '## Executive Summary' not in content
        assert 'Executive Summary' not in written
        assert 'Executive Summary' in dropped
        assert 'Executive Summary' not in omitted
        # The reader-facing arm alone says "nothing to show" — so the drop above
        # is produced by the second clause, not by an arm that would have fired
        # anyway. Without this line the test could not tell which.
        assert _cr._renders_usable_body({'narrative': 'written to the wrong key'}) is False

    def test_the_same_fragment_on_a_conditional_row_stays_a_benign_omission(self, tmp_path):
        """⛔ The load-bearing control: the payload clause must NOT have migrated.

        Identical fragment, conditional row. There the JSON dump is total, so
        nothing is structurally unshowable and the answer collapses to the
        reader-facing arm. If this went to ``dropped`` too, the clause had leaked
        back to the branch where it is the original defect — every clean-run
        ``script-failure-analysis`` would raise the run to ``warning`` again.
        """
        fragments = {'script-failure-analysis': {'narrative': 'written to the wrong key'}}
        _c, _w, omitted, dropped = _cr.build_document('demo', 'live', tmp_path, None, fragments)
        assert 'Script Failure Analysis' in omitted
        assert dropped == []

    def test_an_envelope_only_executive_summary_is_a_benign_omission(self, tmp_path):
        """The matched negative bounding the drop above: no payload, nothing lost."""
        fragments = {'_executive-summary': {'status': 'success', 'aspect': 'executive_summary'}}
        _c, written, omitted, dropped = _cr.build_document(
            'demo', 'live', tmp_path, None, fragments
        )
        assert 'Executive Summary' not in written
        assert 'Executive Summary' in omitted
        assert dropped == []

    def test_a_bare_measured_zero_summary_is_a_drop_through_the_render_arm(self, tmp_path):
        """The non-dict arm the payload clause cannot reach.

        ``_fragment_has_payload`` is ``False`` for every non-dict, so the first
        clause is what makes a bare ``0`` loud — a value a reader can act on that
        the ``summary``-only renderer will never show.
        """
        _c, _w, _omitted, dropped = _cr.build_document(
            'demo', 'live', tmp_path, None, {'_executive-summary': 0}
        )
        assert dropped == ['Executive Summary']
        assert _cr._fragment_has_payload(0) is False


class TestEmitPathStillRendersAttributedCleanRuns:
    """⛔ The regression control for scoping the new question to the NON-emit path.

    An always-emitted aspect whose clean output is a populated ``counts`` block
    beside an empty ``findings`` list carries no summary and no findings — so if
    the emit path were routed through ``_renders_usable_body`` too, these
    sections would vanish from every healthy report. They are precisely how a
    reader sees "evaluated, and found sound", which is the signal this whole
    change exists to protect.
    """

    @pytest.mark.parametrize(
        ('fragment_key', 'heading'),
        [
            ('direct-gh-glab-usage', 'Direct gh/glab Usage'),
            ('execution-context-dispatch-audit', 'Execution-Context Dispatch Audit'),
        ],
    )
    def test_clean_always_emitted_aspect_is_still_written(self, tmp_path, fragment_key, heading):
        fragment = {
            'status': 'success',
            'aspect': fragment_key.replace('-', '_'),
            'counts': {'total': 0, 'by_surface': {}},
            'findings': [],
        }
        _c, written, omitted, dropped = _cr.build_document(
            'demo', 'live', tmp_path, None, {fragment_key: fragment}
        )
        assert heading in written
        assert heading not in omitted
        assert dropped == []


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
