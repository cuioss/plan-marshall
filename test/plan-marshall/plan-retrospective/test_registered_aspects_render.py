# SPDX-License-Identifier: FSL-1.1-ALv2
"""Registered ⇒ rendered completeness guard for the retrospective report pipeline."""


from __future__ import annotations

from pathlib import Path

import retro_sections as _rs
from _registered_aspects_render_fixtures import (
    _CHAT_HISTORY_HEADING,
    _CHAT_HISTORY_KEY,
    _SKILL_MD_PATH,
    _TIER2_WARNING,
    _cf,
    _cr,
    _scan_aspect_table_keys,
    _spec_fragment_keys,
)


class TestAspectTableKeysMatchTheRegistry:
    """D3: the documentation that instructs a registration supplies the exact argument.

    The Step-3 aspect table named its aspects in PROSE while
    ``collect-fragments add`` validates ``--aspect`` against a closed registry,
    and the canonical keys appeared nowhere in the document — so a registration
    written from the table was rejected on first attempt. The table now carries a
    Key column, and these assertions are what make that column *derived* rather
    than *transcribed*: a key that drifts from ``SECTION_SPEC`` fails here.

    ⚠ The correspondence is checked in ONE direction only — ``table → registry``.
    A ``SECTION_SPEC`` row shipped with no table row is caught by nothing here,
    and deliberately so: the reverse assertion would fail today on the two rows
    that have no producer (``_executive-summary``, ``dispatch_boundaries``), and
    encoding those exemptions in a test would pin the dead rows in place rather
    than surface them. They are carried as residue in the plan's run report
    instead. Re-open the reverse direction once neither dead row remains.
    """

    def test_scan_finds_a_key_for_every_numbered_row(self):
        # Anchor: without it, a scanner returning [] would make every assertion
        # below pass vacuously.
        keys = _scan_aspect_table_keys()
        assert len(keys) >= 15, f'aspect-table key scan returned {len(keys)} rows: {keys}'
        assert all(keys), f'aspect-table row(s) with an empty Key cell: {keys}'
        # Spot-anchor the one row whose key differs from BOTH its prose name and
        # its reference-document basename (`invariant-summary`: prose slugs to
        # `invariant-outcomes`, basename is `invariant-check-summary`) plus one
        # that differs from its basename alone (`routing-decisions`, whose prose
        # DOES slug to its key). Re-derived from the table, not recalled. If the
        # scan were reading the wrong cell neither would be present.
        assert 'invariant-summary' in keys
        assert 'routing-decisions' in keys

    def test_every_table_key_is_a_real_registry_key(self):
        keys = _scan_aspect_table_keys()
        spec_keys = _spec_fragment_keys()
        unknown = sorted(set(keys) - spec_keys)
        assert not unknown, (
            f'The Step-3 aspect table declares key(s) {unknown} that are not in '
            f'retro_sections.SECTION_SPEC. A registration copied from the table '
            f'would be rejected by `collect-fragments add` — the exact defect the '
            f'Key column exists to prevent.'
        )

    def test_every_table_key_is_registerable(self):
        keys = _scan_aspect_table_keys()
        registerable = _cf._registerable_aspect_keys()
        unregisterable = sorted(set(keys) - registerable)
        assert not unregisterable, (
            f'The Step-3 aspect table declares key(s) {unregisterable} that '
            f'`collect-fragments add` would reject as unregistered.'
        )

    def test_table_keys_are_unique(self):
        keys = _scan_aspect_table_keys()
        duplicates = sorted({k for k in keys if keys.count(k) > 1})
        assert not duplicates, (
            f'The Step-3 aspect table declares the same canonical key on more than '
            f'one row: {duplicates} — two aspects registering one key means the '
            f'second overwrites the first in the bundle.'
        )

    def test_guard_bites_on_a_key_that_is_not_in_the_registry(self):
        # Runs the REAL parser over a deliberately corrupted copy of the live
        # table, then applies the same correspondence check. Set arithmetic on a
        # literal would prove nothing about either step.
        corrupted = _SKILL_MD_PATH.read_text(encoding='utf-8').replace(
            '| `invariant-summary` |', '| `invariant-check-summary` |', 1
        )
        assert corrupted != _SKILL_MD_PATH.read_text(encoding='utf-8'), (
            'the corruption did not apply — the row shape changed and this test '
            'would pass vacuously against an unmodified table'
        )

        keys = _scan_aspect_table_keys(corrupted)
        unknown = sorted(set(keys) - _spec_fragment_keys())

        assert unknown == ['invariant-check-summary'], (
            f'the correspondence check must flag the corrupted key; got {unknown}'
        )
        # And the uncorrupted table must be clean, so the assertion above is
        # discriminating rather than always-true.
        assert not sorted(set(_scan_aspect_table_keys()) - _spec_fragment_keys())


class TestConditionalFragmentActuallyRenders:
    """A SECTION_SPEC row is necessary but NOT sufficient — the fragment's shape
    must also pass ``compile-report.should_emit()``. The dispatched-vs-row guard
    above cannot see this: a listed aspect whose real fragment carries no
    ``findings``/``failures``/``prompts``/``candidates`` list (the routing-decisions
    case) still ships dead unless ``should_emit`` has a carve-out for it. These
    tests exercise the render path with the aspect's REAL fragment shape.
    """

    @staticmethod
    def _routing_decisions_fragment() -> dict:
        """The success-shape fragment ``check-routing-decisions.py`` emits (plus the
        LLM-synthesized ``posture_verdict``) — findings-less by design."""
        return {
            'status': 'success',
            'aspect': 'routing-decisions',
            'manifest_present': True,
            'posture': 'standard',
            'planning_lane': 'deep',
            'mis_prune_checks': [
                {'check': 'mis_prune:sonar-roundtrip', 'status': 'pass',
                 'predicate': 'no_code_delta', 'detail': 'step ran'},
            ],
            'cost_preview': {
                'execution_log_tokens': 123,
                'execution_log_population': '5-execute,6-finalize',
                'predicted_tokens': 100,
                'predicted_population': '5-execute,6-finalize',
                'comparison': 'computed',
                'delta_tokens': 23,
            },
            'posture_verdict': 'correct',
            'summary': {'passed': 1, 'failed': 0, 'skipped': 0},
        }

    def test_routing_decisions_should_emit_true_for_real_shape(self):
        # Direct should_emit assertion: the findings-less routing-decisions
        # fragment MUST be judged renderable. Without the carve-out this returns
        # False and the section is silently dropped despite its SECTION_SPEC row.
        fragment = self._routing_decisions_fragment()
        assert _cr.should_emit('routing-decisions', 'routing-decisions',
                               {'routing-decisions': fragment}) is True

    def test_routing_decisions_section_renders_in_document(self):
        # End-to-end: build a document from the real fragment shape and assert the
        # "Routing Decisions" section actually appears in the compiled report.
        heading = next(
            (h for h, fragment_key, _trigger in _rs.SECTION_SPEC
             if fragment_key == 'routing-decisions'),
            None,
        )
        assert heading is not None, 'routing-decisions must have a SECTION_SPEC row (D1)'

        fragments = {'_meta': {'mode': 'live'},
                     'routing-decisions': self._routing_decisions_fragment()}
        content, _written, _omitted, _dropped = _cr.build_document(
            'p', 'live', Path('/tmp/plan'), None, fragments)
        assert f'## {heading}' in content, (
            'routing-decisions has a SECTION_SPEC row but its real (findings-less) '
            'fragment shape is rejected by should_emit — the section never renders'
        )


class TestChatHistoryAnalysisRenders:
    """Explicit anchor for aspect 14, dispatched from its own reference document.

    Aspect 14's ``add --aspect chat-history-analysis`` command lives in
    ``references/chat-history-analysis.md``, not in ``SKILL.md``. The widened
    producer scan now reaches it, so these assertions are no longer the ONLY
    coverage of this aspect — they are the redundancy that proves the widened
    enumeration is doing its job, and they pin render behaviour (the Tier-2
    ``status: skipped`` case) that no key-set assertion can express.
    """

    @staticmethod
    def _tier1_fragment() -> dict:
        """Tier-1 success fragment — a real transcript was read and analyzed."""
        return {
            'status': 'success',
            'aspect': 'chat_history_analysis',
            'findings': [
                {'severity': 'info', 'message': 'operator corrected the scope once'},
            ],
        }

    @staticmethod
    def _tier2_fragment() -> dict:
        """Tier-2 graceful-skip fragment — ``status: skipped`` plus a warning.

        ``references/chat-history-analysis.md`` explicitly requires this warning
        to be visible in the compiled report, so the fragment MUST render despite
        its non-success status.
        """
        return {
            'status': 'skipped',
            'aspect': 'chat_history_analysis',
            'findings': [{'severity': 'warning', 'message': _TIER2_WARNING}],
        }

    def test_chat_history_analysis_is_registerable(self):
        assert _CHAT_HISTORY_KEY in _cf._registerable_aspect_keys(), (
            'chat-history-analysis must be registerable — without a SECTION_SPEC row '
            '`collect-fragments add --aspect chat-history-analysis` is rejected with '
            '`Unregistered aspect key` and the aspect ships dead.'
        )

    def test_chat_history_analysis_has_a_section_spec_row(self):
        assert _CHAT_HISTORY_KEY in _spec_fragment_keys()

    def test_section_sits_between_routing_decisions_and_proposed_lessons(self):
        keys = [fragment_key for _heading, fragment_key, _trigger in _rs.SECTION_SPEC]
        assert keys.index('routing-decisions') < keys.index(_CHAT_HISTORY_KEY)
        assert keys.index(_CHAT_HISTORY_KEY) < keys.index('lessons-proposal')

    def test_tier1_fragment_renders_section(self):
        fragments = {'_meta': {'mode': 'live'}, _CHAT_HISTORY_KEY: self._tier1_fragment()}
        content, _written, _omitted, _dropped = _cr.build_document(
            'p', 'live', Path('/tmp/plan'), None, fragments)
        assert f'## {_CHAT_HISTORY_HEADING}' in content

    def test_tier2_skipped_fragment_renders_section_and_warning(self):
        """Asserted on the RENDERED DOCUMENT, deliberately.

        Asserting only that a ``should_emit`` branch exists would pass against
        the dead-code placement this deliverable exists to avoid: a branch placed
        AFTER the ``status not in (None, 'success')`` guard never runs for a
        ``skipped`` fragment. Only the rendered output proves the branch sits
        before the guard.
        """
        fragments = {'_meta': {'mode': 'live'}, _CHAT_HISTORY_KEY: self._tier2_fragment()}
        content, _written, _omitted, _dropped = _cr.build_document(
            'p', 'live', Path('/tmp/plan'), None, fragments)
        assert f'## {_CHAT_HISTORY_HEADING}' in content, (
            'The Tier-2 status:skipped chat-history fragment must still render — its '
            'warning finding is required to be visible in the compiled report. A '
            'should_emit branch placed after the status guard is dead code for this case.'
        )
        assert _TIER2_WARNING in content

    def test_should_emit_true_for_skipped_fragment(self):
        """Function-level pin on the pre-guard placement."""
        fragment = self._tier2_fragment()
        assert _cr.should_emit(
            _CHAT_HISTORY_HEADING, _CHAT_HISTORY_KEY, {_CHAT_HISTORY_KEY: fragment}
        ) is True

    def test_should_emit_false_for_skipped_fragment_without_findings(self):
        """The carve-out is bounded — it does not blanket-admit every skip.

        A ``skipped`` fragment carrying no finding has nothing for the report to
        surface, so it falls through to the ordinary status guard.
        """
        fragment = {'status': 'skipped', 'aspect': 'chat_history_analysis', 'findings': []}
        assert _cr.should_emit(
            _CHAT_HISTORY_HEADING, _CHAT_HISTORY_KEY, {_CHAT_HISTORY_KEY: fragment}
        ) is False

    def test_other_sections_gating_is_unchanged(self):
        """The branch keys on its own trigger_key — no other section is affected."""
        skipped_other = {'status': 'skipped', 'findings': [{'severity': 'warning', 'message': 'x'}]}
        assert _cr.should_emit(
            'Artifact Consistency', 'artifact-consistency', {'artifact-consistency': skipped_other}
        ) is False
