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
3. The Step-3 aspect roster in the plan-retrospective ``SKILL.md`` — the concrete
   ``collect-fragments add --aspect <key>`` commands the workflow runs, whether
   they sit in ``SKILL.md`` itself or in the reference/standards document the
   aspect's roster row names.

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

from pathlib import Path

from _registered_aspects_render_fixtures import (
    _ASPECT_DISPATCH_RE,
    _SKILL_MD_PATH,
    _build_doc_with_aspect,
    _cf,
    _cr,
    _scan_dispatched_aspects,
    _spec_fragment_keys,
)


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

    def test_scanner_reaches_aspects_dispatched_from_their_reference_doc(self):
        # Anchor for the WIDENED half of the enumeration: these keys have no
        # literal `--aspect` command in SKILL.md at all — each is registered from
        # the reference/standards document its aspect-order row names. A scanner
        # that silently narrowed back to SKILL.md-only (or returned an empty
        # population) would make the completeness assertions below vacuous, and
        # this anchor is what fails instead.
        dispatched = _scan_dispatched_aspects()
        skill_only = set(_ASPECT_DISPATCH_RE.findall(_SKILL_MD_PATH.read_text(encoding='utf-8')))

        for key in ('direct-gh-glab-usage', 'execution-context-dispatch-audit'):
            assert key in dispatched, (
                f'{key} is dispatched from its reference document and MUST be '
                f'enumerated by the producer scan'
            )
            assert key not in skill_only, (
                f'{key} is expected to be dispatched from its reference document, '
                f'not from SKILL.md — the anchor no longer exercises the widened '
                f'half of the scan'
            )

    def test_every_dispatched_aspect_is_registerable(self):
        # An aspect the workflow dispatches but `collect-fragments add` rejects
        # ships dead: the producer's registration call fails with `Unregistered
        # aspect key` and the report never carries its fragment. The population is
        # derived, so a newly rostered aspect with no registerable key fails here.
        dispatched = _scan_dispatched_aspects()
        assert dispatched, 'Producer scan returned an empty population — the assertion would be vacuous'

        registerable = _cf._registerable_aspect_keys()
        unregisterable = sorted(dispatched - registerable)
        assert not unregisterable, (
            f'The retrospective workflow dispatches `collect-fragments add --aspect` '
            f'for {unregisterable} but those keys are not registerable (neither a '
            f'SECTION_SPEC row nor a domain-contributed key) — `add` rejects them and '
            f'the aspects ship dead.'
        )

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
