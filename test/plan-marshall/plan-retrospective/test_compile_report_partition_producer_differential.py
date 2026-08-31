# SPDX-License-Identifier: FSL-1.1-ALv2
"""The drop/omit differential: every conditional row x every producer status.

The defect this closes was reproduced against ONE fragment shape at a time, and
the source audit's own review recorded that as an open question — the shapes
genuinely differ (``check-routing-decisions`` carries no ``findings`` key at
all), so no cell follows from another. This module runs the full grid and pins
every cell, so a partition change that fixes one shape while breaking a sibling
fails here rather than in a report someone reads later.

⛔ The row population is DERIVED from ``retro_sections.SECTION_SPEC``, never
listed here. A conditional row added later joins ``_aspect_shaped_rows()`` and is
therefore covered automatically by the ``test_partition_cell`` parametrization,
which is where the protection against an untested row actually lives — the
derived parametrization, not any assertion about it.
"""


from __future__ import annotations

import pytest
import retro_sections as _retro_sections
from _compile_report_behavior_fixtures import _cr

# --------------------------------------------------------------------------
# Population, derived
# --------------------------------------------------------------------------

#: ``dispatch_boundaries`` is a conditional row whose fragment is a per-phase
#: dict rather than a status-wrapped aspect fragment, so the status shapes below
#: are meaningless for it. It gets its own cells in
#: :class:`TestDispatchBoundariesDifferential`; naming it here keeps the
#: population guard honest about why it is handled elsewhere.
_NON_ASPECT_SHAPED_ROWS = frozenset({'dispatch_boundaries'})


def _conditional_rows() -> dict[str, str]:
    """Return ``{fragment_key: heading}`` for every producer-registered conditional row.

    Underscore-prefixed keys are excluded because no producer can register one —
    ``collect-fragments`` refuses the prefix structurally — so they have no
    producer output to run a differential over.
    """
    return {
        fragment_key: heading
        for heading, fragment_key, trigger in _retro_sections.SECTION_SPEC
        if trigger is not None and not fragment_key.startswith('_')
    }


def _aspect_shaped_rows() -> dict[str, str]:
    return {
        key: heading
        for key, heading in _conditional_rows().items()
        if key not in _NON_ASPECT_SHAPED_ROWS
    }


# --------------------------------------------------------------------------
# The producer status shapes, written as the producers really emit them
# --------------------------------------------------------------------------


def _shape(name: str, fragment_key: str):
    """Return the fragment a producer emits for ``name``, or the absent sentinel."""
    aspect = fragment_key.replace('-', '_')
    if name == 'absent':
        return None
    if name == 'clean_success':
        # Provenance + zero-valued counters + empty lists: the real clean-run
        # shape. Every one of these is payload to the container predicate.
        return {
            'status': 'success',
            'aspect': aspect,
            'plan_id': 'demo-plan',
            'counts': {'total': 0},
            'findings': [],
        }
    if name == 'skipped_with_reason':
        return {
            'status': 'skipped',
            'aspect': aspect,
            'skip_reason': 'input artifact absent for this plan',
            'findings': [],
        }
    if name == 'skipped_with_findings':
        return {
            'status': 'skipped',
            'aspect': aspect,
            'skip_reason': 'input artifact absent for this plan',
            'findings': [{'severity': 'warning', 'message': 'aspect could not run'}],
        }
    if name == 'error_with_findings':
        return {
            'status': 'error',
            'aspect': aspect,
            'findings': [{'severity': 'error', 'message': 'producer blew up mid-run'}],
        }
    if name == 'non_dict_prose':
        return 'the producer wrote a sentence, not a fragment'
    raise AssertionError(f'unknown shape: {name!r}')


_SHAPES = (
    'absent',
    'clean_success',
    'skipped_with_reason',
    'skipped_with_findings',
    'error_with_findings',
    'non_dict_prose',
)

#: The expected outcome per shape for a row with no carve-out of its own. Rows
#: that DO have one are corrected by :func:`_carve_out_applies` rather than by a
#: per-shape exception here — see that function for why the distinction bites.
_EXPECTED = {
    'absent': 'omitted',
    'clean_success': 'omitted',
    'skipped_with_reason': 'omitted',
    'skipped_with_findings': 'dropped',
    'error_with_findings': 'dropped',
    'non_dict_prose': 'dropped',
}

#: Rows whose own carve-out in ``should_emit`` can make a refused-by-status
#: fragment RENDER instead. ``chat-history-analysis`` is the sole documented
#: member (``references/chat-history-analysis.md`` requires its warning to be
#: visible in the compiled report).
_CARVE_OUT_ROWS = frozenset({'chat-history-analysis'})


def _carve_out_applies(fragment_key: str, fragment) -> bool:
    """Return True when this row's ``should_emit`` carve-out fires for this shape.

    ⛔ The carve-out is keyed on FINDINGS-PRESENCE, not on a status, and reading
    it as "the skipped-with-findings shape" is a real misreading rather than a
    shorthand. ``should_emit`` gates ``chat-history-analysis`` BEFORE the status
    guard and asks only whether ``findings`` is a non-empty list — so
    ``error_with_findings`` renders for exactly the same reason
    ``skipped_with_findings`` does, and a shape-name exception silently expects a
    drop there.

    That position is deliberate on the production side: an aspect that errored
    but still produced findings has something to say, and refusing it would lose
    the very findings the section exists to surface. So this derives the
    exception from the property the carve-out really tests, which also means a
    findings-bearing shape added to :data:`_SHAPES` later is handled without an
    edit here.
    """
    if fragment_key not in _CARVE_OUT_ROWS:
        return False
    if not isinstance(fragment, dict):
        return False
    findings = fragment.get('findings')
    return isinstance(findings, list) and bool(findings)


def _classify(tmp_path, fragment_key: str, fragment) -> str:
    """Compile a one-key bundle and return this row's partition membership."""
    bundle = {} if fragment is None else {fragment_key: fragment}
    _content, written, omitted, dropped = _cr.build_document(
        'demo', 'live', tmp_path, None, bundle
    )
    heading = _conditional_rows()[fragment_key]
    memberships = [
        name
        for name, bucket in (('written', written), ('omitted', omitted), ('dropped', dropped))
        if heading in bucket
    ]
    # The partition must place every section in exactly one bucket. A heading in
    # two buckets is a partition breach, and reporting it as one of them would
    # hide it.
    assert len(memberships) == 1, f'{heading} landed in {memberships}, expected exactly one'
    return memberships[0]


# --------------------------------------------------------------------------
# The grid
# --------------------------------------------------------------------------


class TestDifferentialPopulation:
    """The grid's population, and the one hygiene check that can actually fail."""

    def test_no_non_aspect_shaped_row_is_stale(self):
        """``_NON_ASPECT_SHAPED_ROWS`` names only rows the registry still declares.

        This is the guard's ONE reachable failure direction, stated as itself
        rather than dressed as a coverage check. Its predecessor compared
        ``_aspect_shaped_rows() | _NON_ASPECT_SHAPED_ROWS`` against
        ``_conditional_rows()`` and advertised an ``uncovered=`` half — but
        ``_aspect_shaped_rows()`` IS ``_conditional_rows()`` minus that same
        frozenset, so ``covered`` was always ``declared | _NON_ASPECT_SHAPED_ROWS``
        and ``declared - covered`` was empty by construction. The name that half
        promised to print could never appear.

        A conditional row added later is NOT caught here, and does not need to be:
        it joins ``_aspect_shaped_rows()`` and is covered by the
        ``test_partition_cell`` parametrization below. That derived parametrization
        is the coverage mechanism; this assertion is the carve-out's own hygiene.
        """
        declared = set(_conditional_rows())
        stale = _NON_ASPECT_SHAPED_ROWS - declared
        assert not stale, (
            '_NON_ASPECT_SHAPED_ROWS names rows SECTION_SPEC no longer declares as '
            f'conditional; stale={sorted(stale)}. Each is excluded from the grid '
            'and handled by no sibling class, so the exclusion hides nothing but '
            'itself'
        )

    def test_the_grid_is_not_empty(self):
        """A population-derived grid must publish that its population is real.

        Without this, a registry read that returned nothing would make every
        parametrized case below vanish and the module would pass green over zero
        assertions.
        """
        assert len(_aspect_shaped_rows()) >= 1


@pytest.mark.parametrize('fragment_key', sorted(_aspect_shaped_rows()))
@pytest.mark.parametrize('shape', _SHAPES)
def test_partition_cell(tmp_path, fragment_key, shape):
    """One cell of the differential: this row, this producer status."""
    fragment = _shape(shape, fragment_key)
    expected = 'written' if _carve_out_applies(fragment_key, fragment) else _EXPECTED[shape]
    actual = _classify(tmp_path, fragment_key, fragment)
    assert actual == expected, (
        f'{fragment_key} x {shape}: expected {expected}, got {actual}'
    )


class TestCarveOutsStillFire:
    """⛔ Both carve-outs the change was forbidden to narrow.

    Each is asserted with the matched negative that bounds it, so neither can
    pass by accident of a blanket rule.
    """

    def test_chat_history_skipped_with_findings_still_renders(self, tmp_path):
        fragment = _shape('skipped_with_findings', 'chat-history-analysis')
        assert _classify(tmp_path, 'chat-history-analysis', fragment) == 'written'

    def test_the_chat_history_carve_out_is_keyed_to_findings_presence_not_a_status(self, tmp_path):
        """⛔ The carve-out gates BEFORE the status guard, so it is not skip-shaped.

        Reading it as "the skipped-with-findings case" expects a DROP here, which
        is what the first cut of this module asserted. ``should_emit`` asks only
        whether ``findings`` is a non-empty list, so an errored producer that
        still has findings renders — and it must, or the report loses exactly the
        findings the error produced.
        """
        errored = _shape('error_with_findings', 'chat-history-analysis')
        assert _classify(tmp_path, 'chat-history-analysis', errored) == 'written'

    def test_the_chat_history_carve_out_needs_findings_not_just_the_row(self, tmp_path):
        """The matched negative that bounds the assertion above.

        Same row, same refused status, findings emptied. Without this the test
        above would equally pass against a carve-out keyed on the row alone, and
        would be asserting nothing about what the gate reads.
        """
        findings_less = {'status': 'error', 'aspect': 'chat_history_analysis', 'findings': []}
        assert _classify(tmp_path, 'chat-history-analysis', findings_less) == 'omitted'

    def test_the_chat_history_carve_out_is_keyed_to_that_aspect_alone(self, tmp_path):
        """The negative control: the same shape on a sibling row is NOT rendered.

        If the carve-out leaked to every row, the assertion above would prove
        nothing about the keying.
        """
        fragment = _shape('skipped_with_findings', 'script-failure-analysis')
        assert _classify(tmp_path, 'script-failure-analysis', fragment) == 'dropped'

    def test_routing_decisions_findings_less_success_still_renders(self, tmp_path):
        """The routing-decisions carve-out: a clean run has NO findings key.

        The aspect grades lane/recipe/posture routing and carries verdict facts
        instead of findings, so its healthy shape is exactly the one a
        findings-keyed gate refuses.
        """
        fragment = {
            'status': 'success',
            'aspect': 'routing_decisions',
            'manifest_present': True,
            'posture': 'standard',
        }
        assert _classify(tmp_path, 'routing-decisions', fragment) == 'written'

    def test_routing_decisions_renders_on_a_content_field_without_manifest_present(self, tmp_path):
        fragment = {
            'status': 'success',
            'aspect': 'routing_decisions',
            'posture_verdict': 'lane held',
        }
        assert _classify(tmp_path, 'routing-decisions', fragment) == 'written'

    def test_manifest_decisions_present_manifest_still_renders(self, tmp_path):
        fragment = {
            'status': 'success',
            'aspect': 'manifest_decisions',
            'manifest_present': True,
            'findings': [],
        }
        assert _classify(tmp_path, 'manifest-decisions', fragment) == 'written'


class TestDispatchBoundariesDifferential:
    """The one conditional row whose fragment is not a status-wrapped aspect."""

    def test_absent_is_omitted(self, tmp_path):
        assert _classify(tmp_path, 'dispatch_boundaries', None) == 'omitted'

    def test_no_present_phase_is_omitted(self, tmp_path):
        """Its own renderer prints a placeholder for this input, so nothing is lost."""
        fragment = {'5-execute': {'present': False, 'rows': [], 'unknown_count': 0}}
        assert _classify(tmp_path, 'dispatch_boundaries', fragment) == 'omitted'

    def test_one_present_phase_is_written(self, tmp_path):
        fragment = {'5-execute': {'present': True, 'rows': [], 'unknown_count': 0}}
        assert _classify(tmp_path, 'dispatch_boundaries', fragment) == 'written'

    def test_non_dict_prose_is_dropped(self, tmp_path):
        assert _classify(tmp_path, 'dispatch_boundaries', 'prose, not a phase map') == 'dropped'


class TestRunStatusFollowsTheDroppedBucket:
    """``status: warning`` is raised by a drop, and by nothing else.

    The differential's whole point is that a clean producer run must not raise
    the run status; this pins the coupling in both directions.
    """

    def test_a_grid_row_of_benign_shapes_keeps_every_bucket_clean(self, tmp_path):
        bundle = {
            key: _shape('clean_success', key) for key in sorted(_aspect_shaped_rows())
        }
        _content, _written, _omitted, dropped = _cr.build_document(
            'demo', 'live', tmp_path, None, bundle
        )
        assert dropped == []

    def test_a_single_prose_fragment_is_enough_to_raise_the_drop_bucket(self, tmp_path):
        bundle = {
            key: _shape('clean_success', key) for key in sorted(_aspect_shaped_rows())
        }
        bundle['script-failure-analysis'] = _shape('non_dict_prose', 'script-failure-analysis')
        _content, _written, _omitted, dropped = _cr.build_document(
            'demo', 'live', tmp_path, None, bundle
        )
        assert dropped == ['Script Failure Analysis']
