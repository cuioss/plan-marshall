# SPDX-License-Identifier: FSL-1.1-ALv2
"""In-process behavioral tests for ``compile-report.py``.

Scope: which sections are written and which are omitted — a placeholder summary, an
empty bundle, an empty or payload-free fragment, and the registry rows that always
emit — with written implying payload throughout.
"""


from __future__ import annotations

from pathlib import Path

import pytest
import retro_sections as _rs
from _compile_report_behavior_fixtures import _cr


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

    def test_no_section_is_written_from_an_empty_bundle(self, tmp_path):
        # The CLASS, not the instance. `render_section_body(None)` returns the
        # literal `_No data provided._`, and every `conditional_trigger = None`
        # row used to append its heading to `written` regardless — so an empty
        # bundle produced a report claiming ten written sections whose every body
        # was a placeholder. Quantified over the whole registry rather than a
        # name list, so a row added later is covered without an edit here.
        content, written, omitted, dropped = _cr.build_document('demo', 'live', tmp_path, None, {})
        assert written == [], f'sections written from an empty bundle: {written}'
        assert '_No data provided._' not in content
        assert dropped == []
        assert len(omitted) == len(_rs.SECTION_SPEC)

    @pytest.mark.parametrize('empty', ['', '   ', {}, [], ()], ids=['blank', 'whitespace', 'dict', 'list', 'tuple'])
    def test_an_empty_fragment_is_not_written(self, tmp_path, empty):
        # REGRESSION. The first two attempts at this invariant guarded on
        # `fragment is None`, which closes only the ABSENT-key case. The real
        # pipeline does not produce None: `parse_toon` returns `''` for a
        # valueless key (only the literal `null` yields None), and
        # `collect-fragments._read_fragment` accepts any file that is not
        # whitespace-only. A producer that wrote prose instead of a fragment
        # therefore registered successfully and was emitted as a heading over an
        # empty fenced block, counted as written, with `dropped` empty.
        fragments = {'artifact-consistency': empty}
        content, written, omitted, dropped = _cr.build_document(
            'demo', 'live', tmp_path, None, fragments
        )
        assert 'Artifact Consistency' not in written
        assert 'Artifact Consistency' in omitted
        assert '## Artifact Consistency' not in content
        assert dropped == []

    @pytest.mark.parametrize('scalar', [0, 0.0], ids=['zero', 'zero-float'])
    def test_a_measured_zero_fragment_is_content(self, tmp_path, scalar):
        # CHARACTERIZATION of pre-existing behaviour — it passes against
        # `origin/main` too. It pins the half of the falsy-versus-empty split
        # that must NOT move: collapsing this into "falsy means empty" would
        # discard a measured zero, the defect the identity checks elsewhere in
        # this module exist to prevent.
        fragments = {'artifact-consistency': scalar}
        _content, written, omitted, _dropped = _cr.build_document(
            'demo', 'live', tmp_path, None, fragments
        )
        assert 'Artifact Consistency' in written
        assert 'Artifact Consistency' not in omitted

    @pytest.mark.parametrize(
        'fragment',
        [
            {'summary': ''},
            {'findings': []},
            {'status': 'success', 'aspect': 'artifact_consistency'},
            {'summary': '', 'findings': []},
            {'summary': None},
        ],
        ids=['blank-summary', 'empty-findings', 'envelope-only', 'both-empty', 'null-summary'],
    )
    def test_a_dict_with_no_payload_is_not_written(self, tmp_path, fragment):
        # REGRESSION. Earlier attempts at this invariant closed narrower cases:
        # the first changed only the `_executive-summary` branch, the second
        # asked whether the fragment was ABSENT, and the third asked whether its
        # CONTAINER was empty. Every shape here is a non-empty dict that renders
        # a JSON block stating nothing — and `{'findings': []}` is the literal
        # shape an LLM aspect with nothing to report writes. The compiler's own
        # payload discriminator already called all of them empty while the
        # partition counted them written.
        assert _cr._fragment_has_payload(fragment) is False, 'precondition'
        content, written, omitted, dropped = _cr.build_document(
            'demo', 'live', tmp_path, None, {'artifact-consistency': fragment}
        )
        assert 'Artifact Consistency' not in written
        assert 'Artifact Consistency' in omitted
        assert '## Artifact Consistency' not in content
        assert dropped == []

    def test_written_implies_payload_holds_for_every_registry_row(self, tmp_path):
        # The invariant stated as one property over the whole registry rather
        # than as a list of cases: nothing reaches `written` that the payload
        # discriminator calls empty.
        fragments = {
            key: {'status': 'success', 'aspect': key, 'findings': []}
            for _h, key, _t in _rs.SECTION_SPEC
            if not key.startswith('_')
        }
        _content, written, _omitted, _dropped = _cr.build_document(
            'demo', 'live', tmp_path, None, fragments
        )
        assert written == [], f'sections written from payload-less fragments: {written}'

    def test_a_bare_false_fragment_is_empty(self, tmp_path):
        # Matches the identity skip `_fragment_has_payload` applies to a `False`
        # VALUE, so the two discriminators agree rather than merely being
        # described as agreeing.
        _content, written, omitted, _dropped = _cr.build_document(
            'demo', 'live', tmp_path, None, {'artifact-consistency': False}
        )
        assert 'Artifact Consistency' not in written
        assert 'Artifact Consistency' in omitted

    def test_an_empty_registry_fragment_is_omitted_exactly_once(self, tmp_path):
        # The fallback loop's emptiness check must sit AFTER the `spec_keys`
        # skip. Above it, a registry key with an empty value was recorded twice —
        # once by the static loop under its real heading, and again by the
        # fallback under a heading SYNTHESIZED from the key, naming a section no
        # registry row declares.
        fragments = {'artifact-consistency': ''}
        _content, _written, omitted, _dropped = _cr.build_document(
            'demo', 'live', tmp_path, None, fragments
        )
        assert omitted.count('Artifact Consistency') == 1
        assert len(omitted) == len(_rs.SECTION_SPEC)
        spec_headings = {heading for heading, _k, _t in _rs.SECTION_SPEC}
        phantom = [h for h in omitted if h not in spec_headings]
        assert phantom == [], f'omitted names sections declared by no registry row: {phantom}'

    @pytest.mark.parametrize(
        'heading,fragment_key',
        [(h, k) for h, k, trigger in _rs.SECTION_SPEC if trigger is None and not k.startswith('_')],
    )
    def test_an_always_emit_row_with_no_fragment_is_omitted_not_written(
        self, tmp_path, heading, fragment_key
    ):
        # There are 11 `trigger=None` rows; this parametrization covers the 10
        # that are not `_executive-summary` (that row has its own branch and
        # its own test above). Driven from the registry so the population
        # cannot silently shrink.
        _content, written, omitted, _dropped = _cr.build_document('demo', 'live', tmp_path, None, {})
        assert heading not in written
        assert heading in omitted

    def test_a_row_with_a_real_fragment_is_still_written(self, tmp_path):
        # The guard must not swallow a section that HAS content — the fix is
        # "no fragment ⇒ not written", never "write less".
        fragments = {'artifact-consistency': {'status': 'success', 'summary': 'all checks passed'}}
        content, written, omitted, _dropped = _cr.build_document(
            'demo', 'live', tmp_path, None, fragments
        )
        assert 'Artifact Consistency' in written
        assert 'Artifact Consistency' not in omitted
        assert 'all checks passed' in content

    def test_a_fallback_aspect_mapped_to_none_is_omitted_not_written(self, tmp_path):
        # The invariant is a property of the partition, not of one render path.
        fragments = {'wrapper-tangle': None}
        content, written, omitted, _dropped = _cr.build_document(
            'demo', 'live', tmp_path, None, fragments
        )
        assert 'Wrapper Tangle' not in written
        assert 'Wrapper Tangle' in omitted
        assert '## Wrapper Tangle' not in content


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
        # `plan_id` is PAYLOAD (so the section is written) but is not an
        # attribution field (so the zero stays unqualified) — the shape every
        # real producer emits. Without a payload key the section would be
        # omitted, and the probe would pass for the wrong reason: it would be
        # asserting on a section the report does not carry.
        fragments = {'direct-gh-glab-usage': {'status': 'success', 'plan_id': 'p', 'findings': []}}
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
        fragments = {'direct-gh-glab-usage': {'status': 'success', 'plan_id': 'p', 'findings': []}}
        written, flagged = self._doc(fragments)
        assert 'Script Failure Analysis' not in written
        assert flagged == ['Direct gh/glab Usage']

    def test_a_fallback_rendered_aspect_is_probed_too(self):
        # A domain-contributed aspect has no SECTION_SPEC row — build_document
        # renders it through the generic fallback. Probing only the registry rows
        # would exclude every such aspect, and those are the newest and least
        # conventional producers, so they are the population MOST likely to
        # report a bare zero.
        fragments = {'_meta': {'mode': 'live'},
                     'wrapper-tangle': {'status': 'success', 'plan_id': 'p', 'findings': []}}
        written, flagged = self._doc(fragments)
        assert 'Wrapper Tangle' in written, 'precondition: the fallback must render it'
        assert 'Wrapper Tangle' in flagged

    def test_a_fallback_rendered_aspect_clears_the_flag_when_attributed(self):
        fragments = {
            '_meta': {'mode': 'live'},
            'wrapper-tangle': {'status': 'success', 'findings': [], 'evaluated_population': 12},
        }
        written, flagged = self._doc(fragments)
        assert 'Wrapper Tangle' in written
        assert 'Wrapper Tangle' not in flagged

    def test_a_spec_row_wins_over_a_fallback_key_synthesizing_the_same_heading(self):
        # `_heading_to_fragment_key` mirrors build_document, whose fallback loop
        # skips keys that already carry a static row. Pinning the precedence so a
        # later edit cannot silently repoint a heading at the wrong fragment.
        mapping = _cr._heading_to_fragment_key({'artifact-consistency': {}, 'wrapper-tangle': {}})
        assert mapping['Artifact Consistency'] == 'artifact-consistency'
        assert mapping['Wrapper Tangle'] == 'wrapper-tangle'

    def test_a_population_published_one_level_down_counts_as_attribution(self):
        # This is where the real producers put it: `evaluated_population` lives
        # inside `shape_violation` / `dispatch_coverage` in check-dispatch-audit,
        # and `population` inside `script_cost_rollup` in analyze-logs. A
        # top-level-only probe would flag a fragment that DOES name what it
        # checked, one level down.
        fragments = {
            'execution-context-dispatch-audit': {
                'status': 'success',
                'findings': [],
                'shape_violation': {'status': 'evaluated', 'evaluated_population': 7},
            },
        }
        _written, flagged = self._doc(fragments)
        assert 'Execution-Context Dispatch Audit' not in flagged

    def test_nesting_search_stops_at_one_level(self):
        # Two levels down is NOT attribution: the population belongs to a named
        # fact block, and an unbounded walk would let any incidental key deep in
        # a payload clear the flag.
        fragments = {
            'direct-gh-glab-usage': {
                'status': 'success',
                'findings': [],
                'outer': {'inner': {'evaluated_population': 7}},
            },
        }
        _written, flagged = self._doc(fragments)
        assert 'Direct gh/glab Usage' in flagged

    def test_the_real_dispatch_audit_clean_shape_is_attributed(self):
        # The shape check-dispatch-audit actually returns on a clean trail
        # (top-level `counts`, nested `evaluated_population`).
        fragments = {
            'execution-context-dispatch-audit': {
                'status': 'success',
                'aspect': 'execution-context-dispatch-audit',
                'shape_violation': {'status': 'not_evaluated', 'evaluated_population': 0},
                'dispatch_coverage': {'evaluated_population': 3},
                'findings': [],
                'counts': {'findings_total': 0},
            },
        }
        _written, flagged = self._doc(fragments)
        assert flagged == []

    @pytest.mark.parametrize(
        'aspect_key,fragment',
        [
            (
                'artifact-consistency',
                {'status': 'success', 'aspect': 'artifact_consistency', 'findings': [],
                 'checks': [{'name': 'metrics_generated', 'status': 'pass', 'message': 'ok'}]},
            ),
            (
                'invariant-summary',
                {'status': 'success', 'aspect': 'invariant_summary', 'findings': [],
                 'phases': [], 'drift': {}, 'expected_invariants': ['handshake', 'blocking']},
            ),
        ],
        ids=['artifact-consistency-checks', 'summarize-invariants-expected'],
    )
    def test_a_producer_naming_its_checked_set_by_roster_is_not_flagged(self, aspect_key, fragment):
        # Both name what they checked WITHOUT publishing a size — one lists its
        # checks by name, the other its invariant roster — and the probe flagged
        # both on every clean run until the vocabulary covered them. They are not
        # the only such producers: `check-manifest-consistency` publishes `checks`
        # too, on a plan that has an `execution.toon` and a clean cross-check.
        #
        # The fixtures are hand-written rather than derived from the producers, so
        # a producer RENAMING its roster field would leave this green. The
        # producer-side correspondence is covered by the sweep recorded in the run
        # report, not here.
        written, flagged = self._doc({aspect_key: fragment})
        assert written, 'precondition: the section must render'
        assert flagged == []

    def test_an_all_unmeasured_counts_block_does_not_name_a_checked_set(self):
        """A fully-populated, entirely self-declared-unmeasured ``counts`` is not attribution.

        ⛔ D2's own headline scenario. ``counts`` is in the attribution vocabulary
        because a populated count block usually names what was counted — but a
        fragment that evaluated NOTHING publishes a fully-populated all-zero block
        too, and its envelope is still ``status: success``, so route 1 of
        ``_names_checked_set`` does not fire either. The log-less
        ``check-dispatch-audit`` fragment is exactly this shape: every category
        present, every count ``0``, every status ``not_evaluated``, nothing named.
        It cleared the probe on the strength of a block that names nothing, which
        is precisely the ambiguity the probe exists to report.

        Asserted at BOTH levels — the narrowing predicate itself and the section
        partition it decides — because a reader consults the section list, not the
        helper.
        """
        counts = {
            'total': 0,
            'by_category': {
                'shape_violation': {'count': 0, 'status': 'not_evaluated'},
                'missing_dispatch_emission': {'count': 0, 'status': 'not_evaluated'},
                'envelope_violation': {'count': 0, 'status': 'not_evaluated'},
                'generic_subagent_violation': {'count': 0, 'status': 'not_evaluated'},
            },
        }
        assert _cr._counts_names_population(counts) is False

        fragments = {
            'direct-gh-glab-usage': {
                'status': 'success',
                'plan_id': 'p',
                'findings': [],
                'counts': counts,
            },
        }
        written, flagged = self._doc(fragments)
        assert 'Direct gh/glab Usage' in written, 'precondition: the section must render'
        assert 'Direct gh/glab Usage' in flagged

    def test_a_counts_block_of_bare_integers_still_names_a_checked_set(self):
        """The matched negative control — the narrowing is a READ, not a new rule.

        The ``direct-gh-glab-usage`` shape: a ``counts`` block whose entries are
        BARE integers declares nothing either way, and its producer really did
        examine the population it counted over. Reading that silence as "named
        nothing" would flag it on every healthy run — the cry-wolf failure
        ``ZERO_ATTRIBUTION_FIELDS`` warns this probe against.

        Without this control the guard above would be equally satisfied by a
        narrowing that rejected every ``counts`` block, and the flag would carry no
        information at all.
        """
        counts = {'total': 0, 'by_surface': {'log_leak': 0, 'diff_leak': 0}}
        assert _cr._counts_names_population(counts) is True

        fragments = {
            'direct-gh-glab-usage': {
                'status': 'success',
                'plan_id': 'p',
                'findings': [],
                'counts': counts,
            },
        }
        written, flagged = self._doc(fragments)
        assert 'Direct gh/glab Usage' in written
        assert 'Direct gh/glab Usage' not in flagged

    def test_probe_bites_only_on_the_defect_it_names(self):
        # Mutation check: the SAME fragment with its attribution restored must
        # stop being flagged. A probe that flagged both (or neither) would be
        # asserting something other than the property it is named for.
        defective = {'direct-gh-glab-usage': {'status': 'success', 'plan_id': 'p', 'findings': []}}
        attributed = {
            'direct-gh-glab-usage': {
                'status': 'success',
                'plan_id': 'p',
                'findings': [],
                'counts': {'total': 0, 'by_surface': {'log_leak': 0, 'diff_leak': 0}},
            },
        }
        assert self._doc(defective)[1] == ['Direct gh/glab Usage']
        assert self._doc(attributed)[1] == []
