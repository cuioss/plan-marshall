# SPDX-License-Identifier: FSL-1.1-ALv2
"""Registered ⇒ rendered completeness guard for the retrospective report pipeline.

An aspect key travels through three registries that MUST agree, or the aspect
ships dead (a producer emits a fragment that is silently dropped at render time):

1. ``retro_sections.SECTION_SPEC`` — the static section registry ``compile-report``
   iterates. A ``fragment_key`` with a row here is rendered.
2. ``collect-fragments._registerable_aspect_keys()`` — the closed set
   ``collect-fragments add`` accepts (``valid_aspect_keys()`` ∪
   ``_domain_aspect_keys()``). A domain-contributed key is accepted here but is
   NOT in ``SECTION_SPEC``.
3. The Step-3 dispatch list in the plan-retrospective ``SKILL.md`` — the concrete
   ``collect-fragments add --aspect <key>`` commands the workflow runs.

This guard asserts both directions of the completeness contract:

- **(a) registerable ⇒ renderable**: every member of
  ``_registerable_aspect_keys()`` either has a ``SECTION_SPEC`` row OR is emitted
  by ``compile-report.build_document()``'s generic fallback. The fallback is
  proven by building a document from a synthetic bundle carrying an unlisted
  aspect and asserting its section appears — this is the D2 fallback that closes
  the domain-contributed silent-drop (e.g. ``wrapper-tangle``).
- **(b) dispatched ⇒ has a static row**: every aspect the ``SKILL.md`` dispatches
  via a literal ``add --aspect <key>`` command has a ``SECTION_SPEC`` render row.
  The dispatch list is enumerated INDEPENDENTLY of ``SECTION_SPEC`` (scanned from
  ``SKILL.md``), so the guard fails on a dispatched-but-unlisted aspect like
  ``routing-decisions`` and passes only once D1's row is in place.

The scripts are loaded by explicit importlib path via ``conftest.load_script_module``
(the sibling pattern in ``test_compile_report_behavior.py``) so the test does not
depend on conftest import-name discovery order.
"""

from __future__ import annotations

import re
from pathlib import Path

import retro_sections as _rs

from conftest import MARKETPLACE_ROOT, load_script_module

_cr = load_script_module('plan-marshall', 'plan-retrospective', 'compile-report.py', 'cr_render_guard_mod')
_cf = load_script_module('plan-marshall', 'plan-retrospective', 'collect-fragments.py', 'cf_render_guard_mod')

_SKILL_MD_PATH = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'SKILL.md'

# Matches ``--aspect <key>`` where <key> is a concrete hyphenated aspect
# identifier. The leading ``[a-z]`` anchor excludes ``{name}`` / ``{aspect}``
# placeholder templates (they begin with ``{``), so only literal dispatched
# aspect keys are captured.
_ASPECT_DISPATCH_RE = re.compile(r'--aspect\s+([a-z][a-z0-9-]*)')


def _spec_fragment_keys() -> set[str]:
    """Return the set of every ``fragment_key`` declared in ``SECTION_SPEC``."""
    return {fragment_key for _heading, fragment_key, _trigger in _rs.SECTION_SPEC}


def _build_doc_with_aspect(aspect_key: str) -> str:
    """Build a retrospective document from a synthetic single-aspect bundle.

    The bundle carries only ``_meta`` and the one ``aspect_key``, so the section
    (when it appears) can only have come from either a ``SECTION_SPEC`` row or the
    generic fallback in ``build_document()``.
    """
    fragments = {
        '_meta': {'mode': 'live'},
        aspect_key: {'status': 'success', 'summary': f'synthetic body for {aspect_key}'},
    }
    content, _written, _omitted, _dropped = _cr.build_document('p', 'live', Path('/tmp/plan'), None, fragments)
    return content


def _scan_dispatched_aspects() -> set[str]:
    """Enumerate the literal aspect keys the plan-retrospective SKILL.md dispatches.

    Source-independent of ``SECTION_SPEC`` — reads the ``SKILL.md`` text and
    extracts every literal ``add --aspect <key>`` command. Placeholder templates
    (``{name}`` / ``{aspect}``) are excluded by the regex anchor.

    **Known blind spot — file scope, not regex scope.** This scanner reads ONLY
    ``SKILL.md``. An aspect whose ``add --aspect <key>`` command lives in its
    aspect REFERENCE doc rather than in ``SKILL.md`` is therefore invisible to
    direction (b) of the completeness guard, even though the regex would match
    the command fine. ``chat-history-analysis`` is exactly that shape —
    ``SKILL.md``'s aspect-14 block dispatches only the ``extract-chat-signal``
    pre-pass and delegates fragment synthesis and registration to
    ``references/chat-history-analysis.md`` — which is why it needs the explicit
    anchor in ``TestChatHistoryAnalysisRenders`` below. Direction (a) misses it
    too: an unregisterable key is not in ``_registerable_aspect_keys()`` and so is
    never iterated.

    **Explicitly-unresolved out-of-scope gap.** An outline-time trial of the
    obvious "scan ``references/*.md`` too" widening surfaced two FURTHER
    dispatched-but-unlisted keys — ``direct-gh-glab-usage``
    (``references/direct-gh-glab-usage.md``) and
    ``execution-context-dispatch-audit``
    (``standards/execution-context-dispatch-audit.md``). Those two may be
    legitimately domain-contributed (registerable via ``_domain_aspect_keys()``
    rather than ``SECTION_SPEC``), or they may be the same defect a second and
    third time — that was NOT resolved. Widening the scanner's file set here
    would turn the guard red for aspects outside the owning plan's scope, so the
    widening is deliberately deferred and the two keys are recorded here so the
    next reader inherits the finding rather than rediscovering it.
    """
    skill_text = _SKILL_MD_PATH.read_text(encoding='utf-8')
    return set(_ASPECT_DISPATCH_RE.findall(skill_text))


class TestRegisterableAspectsRenderable:
    """(a) Every ``_registerable_aspect_keys()`` member has a render path."""

    def test_every_registerable_aspect_has_a_render_path(self):
        registerable = _cf._registerable_aspect_keys()
        spec_keys = _spec_fragment_keys()

        unrenderable: list[str] = []
        for key in sorted(registerable):
            if key in spec_keys:
                # Static SECTION_SPEC row renders it.
                continue
            # No static row — must be emitted by the generic fallback.
            content = _build_doc_with_aspect(key)
            heading = _cr._heading_from_aspect_key(key)
            if f'## {heading}' not in content:
                unrenderable.append(key)

        assert not unrenderable, (
            f'Registerable aspects with no render path (neither a SECTION_SPEC row '
            f'nor a build_document fallback section): {unrenderable}'
        )

    def test_fallback_renders_an_unlisted_aspect(self):
        # Prove the generic fallback mechanism directly with a synthetic key that
        # is guaranteed NOT to be in SECTION_SPEC. Without the fallback this
        # section would be silently dropped.
        synthetic = 'synthetic-unlisted-aspect'
        assert synthetic not in _spec_fragment_keys()

        content = _build_doc_with_aspect(synthetic)
        heading = _cr._heading_from_aspect_key(synthetic)
        assert f'## {heading}' in content

    def test_fallback_skips_reserved_and_listed_keys(self):
        # The fallback must NOT double-emit a listed aspect and must NOT surface
        # reserved underscore-prefixed meta keys as their own sections.
        fragments = {
            '_meta': {'mode': 'live'},
            '_executive-summary': {'summary': 'exec'},
            'artifact-consistency': {'status': 'success', 'summary': 'listed aspect'},
        }
        content, written, _omitted, _dropped = _cr.build_document('p', 'live', Path('/tmp/plan'), None, fragments)

        # No section is derived from a reserved meta key.
        assert '## Meta' not in content
        assert '## Executive-Summary' not in content
        # artifact-consistency is emitted exactly once (by its SECTION_SPEC row,
        # not duplicated by the fallback).
        assert written.count('Artifact Consistency') == 1


class TestDispatchedAspectsHaveStaticRow:
    """(b) Every SKILL.md-dispatched aspect has a ``SECTION_SPEC`` render row."""

    def test_scanner_finds_the_routing_decisions_dispatch(self):
        # Anchor: if the scanner returns an empty/degenerate set the completeness
        # assertion below would silently pass. routing-decisions is a known
        # literal dispatch in SKILL.md and MUST be found.
        dispatched = _scan_dispatched_aspects()
        assert 'routing-decisions' in dispatched
        assert 'manifest-decisions' in dispatched

    def test_every_dispatched_aspect_has_a_section_spec_row(self):
        dispatched = _scan_dispatched_aspects()
        spec_keys = _spec_fragment_keys()

        missing = sorted(dispatched - spec_keys)
        assert not missing, (
            f'SKILL.md dispatches `collect-fragments add --aspect` for {missing} but no '
            f'SECTION_SPEC render row exists — those aspects ship dead (silent drop at '
            f'compile-report render time).'
        )

    def test_guard_bites_when_a_dispatched_aspect_lacks_a_row(self):
        # Demonstrate the guard's completeness logic FAILS when a dispatched
        # aspect has no SECTION_SPEC row — the exact defect D1 fixed for
        # routing-decisions. Recompute spec_keys with routing-decisions removed
        # and assert the dispatched-vs-spec difference flags it.
        dispatched = _scan_dispatched_aspects()
        assert 'routing-decisions' in dispatched

        spec_keys_without_routing = {k for k in _spec_fragment_keys() if k != 'routing-decisions'}
        missing = dispatched - spec_keys_without_routing
        assert 'routing-decisions' in missing, (
            'The completeness guard must flag routing-decisions as dispatched-but-unlisted '
            'when its SECTION_SPEC row is absent — proving the guard bites.'
        )


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
            'posture': 'auto',
            'planning_lane': 'deep',
            'mis_prune_checks': [
                {'check': 'mis_prune:sonar-roundtrip', 'status': 'pass',
                 'predicate': 'no_code_delta', 'detail': 'step ran'},
            ],
            'cost_preview': {'actual_tokens': 123, 'predicted_tokens': 100, 'delta_tokens': 23},
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


_CHAT_HISTORY_KEY = 'chat-history-analysis'
_CHAT_HISTORY_HEADING = 'Chat History Analysis'
_TIER2_WARNING = 'transcript unavailable — chat-history analysis skipped'


class TestChatHistoryAnalysisRenders:
    """Explicit anchor for aspect 14, which the SKILL.md scanner cannot see.

    ``_scan_dispatched_aspects()`` reads only ``SKILL.md`` and aspect 14's
    ``add --aspect chat-history-analysis`` command lives in
    ``references/chat-history-analysis.md`` (see the scanner's docstring for the
    full blind-spot note and the two unresolved out-of-scope keys), so neither
    direction of the completeness guard covers this aspect. These assertions are
    that missing coverage, made explicitly.
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
