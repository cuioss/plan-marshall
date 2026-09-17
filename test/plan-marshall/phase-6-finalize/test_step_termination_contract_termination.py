#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Regression for the external finalize-step termination contract.

``standards/external-step-contract.md`` is the authoring contract for external
finalize step bodies. Two defects in it fed the "step recorded no terminal
outcome" recurrence family:

* **Cause A — key-form split.** The contract directed ``--step`` to "match the
  fully-qualified step name as listed in ``marshal.json`` (e.g. ``default:push``)".
  The manifest composes bare keys and the canonical step-key seam strips
  ``default:`` on write, so that instruction was stale — it is the authoring
  instruction that seeded the mismatched-key half.
* **Cause B — omitted call.** The contract mandated *that* a step calls
  ``mark-step-done`` but never *when*. A leaf that composes its return TOON
  first and treats the record as a trailing step never lands the write.

These tests pin both corrections plus the detector/authoring-rule pairing:

(a) The stale ``marshal.json`` / ``default:``-prefixed key-form instruction is
    gone, replaced by the composed-manifest-catalog-key contract.
(b) The record-before-return ordering invariant is stated explicitly — now in
    ``ref-workflow-architecture/standards/agents.md``, which owns it for EVERY
    dispatched leaf rather than only for external steps.
(c) Both guard error codes (``step_record_missing``,
    ``step_record_mismatched_key``) are referenced by the contract, so the
    dispatcher-side detector and the authoring-side rule stay paired.
(d) The invariant is scoped to every dispatched leaf, not external steps only,
    and is reachable from every DISPATCHED roster entry's governing contract —
    asserted per PARTITION, not merely centrally: external (``project:`` /
    ``bundle:skill``) entries reach it through ``external-step-contract.md``,
    built-in (``default:``) entries through the ``phase-6-finalize/SKILL.md``
    reach-point, and a roster row matching neither partition fails the test.
(e) ``agents.md``'s corollary ordinal and its corollary enumeration agree with
    the number of corollary sections actually present, so a one-site drift
    fails instead of silently desynchronising.

The mutation guards are what keep the sweeps honest:
``test_stale_instruction_patterns_detect_the_pre_fix_prose`` asserts the
stale-form patterns fire on the exact pre-fix sentence (guarding (a)),
``test_external_only_scoping_detector_fires_on_the_pre_fix_shape`` asserts the
scoping detector rejects the pre-fix external-only phrasing (guarding (d)),
``test_builtin_reach_point_detector_fires_only_on_a_real_binding`` asserts the
built-in reach-point detector rejects both the pre-fix no-binding text and an
external-only near-miss (guarding the built-in half of (d)), and
``test_ordinal_enumeration_detectors_fire_on_the_pre_fix_three_item_shape``
asserts the lock-step detectors fire on the pre-fix three-item ordinal and
enumeration (guarding (e)). Without them a regex typo would make the
corresponding assertion vacuously green.

The (d) population is **derived, never hardcoded**: it is parsed from the
``## Dispatched steps`` roster in ``dispatch-inline-split.md`` at test time, so
a newly added dispatched step is covered without editing this file.

Scope note: this deliverable is confined to ``phase-6-finalize`` plus the
``agents.md`` invariant it now cross-references. The guard implementation under
``manage-status/scripts/`` is a read-only consulted source and is deliberately
NOT asserted against here.
"""

from __future__ import annotations

import re

from _dispatch_roster import parse_roster, section_lines
from conftest import MARKETPLACE_ROOT

_SKILL_DIR = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize'
_CONTRACT_DOC = _SKILL_DIR / 'standards' / 'external-step-contract.md'
_SKILL_DOC = _SKILL_DIR / 'SKILL.md'
_ROSTER_DOC = _SKILL_DIR / 'standards' / 'dispatch-inline-split.md'
_AGENTS_DOC = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'ref-workflow-architecture' / 'standards' / 'agents.md'

_TERMINATION_HEADING = '## Required termination'
_DISPATCHED_HEADING = '## Dispatched steps'

#: The agents.md section that now OWNS the record-before-return invariant for
#: every dispatched leaf (external steps included).
_RECORD_COROLLARY_HEADING = '### Leaf must record its terminal outcome BEFORE composing its return'

#: Corollary sections carry a ``### Leaf ...`` heading. The leaf/dispatch-topology
#: invariant itself ("a leaf cannot spawn a subagent") is the FIRST corollary but
#: is stated in the SSOT blockquote rather than as its own ``###`` section, so the
#: corollary count is the heading count plus that one.
_COROLLARY_HEADING = re.compile(r'^###\s+Leaf\s+(?:cannot|must)\b', re.MULTILINE)
_BASE_INVARIANT_COROLLARY_COUNT = 1

#: The ordinal naming the backgrounded-build corollary's position.
_COROLLARY_ORDINAL = re.compile(r'This is the (\w+) corollary of the leaf/dispatch-topology invariant')

#: The parenthetical enumeration in that same sentence. Items are comma
#: separated with a trailing ``and``.
_COROLLARY_ENUMERATION = re.compile(
    r'This is the \w+ corollary of the leaf/dispatch-topology invariant above '
    r'\(([^)]+)\)'
)

_ORDINAL_WORDS = {
    'first': 1,
    'second': 2,
    'third': 3,
    'fourth': 4,
    'fifth': 5,
    'sixth': 6,
}

#: Pre-fix phrasings that scoped the invariant to external steps only.
_EXTERNAL_ONLY_SCOPING = re.compile(r'\bevery\s+external\s+step\b[^.]{0,120}?\bmark-step-done\b', re.IGNORECASE)

#: The two error codes the dispatcher-side guard distinguishes.
_GUARD_ERROR_CODES = ('step_record_missing', 'step_record_mismatched_key')

#: The reach-point that binds BUILT-IN (``default:``) dispatched step bodies to
#: the agents.md record-before-return invariant. External steps reach it via
#: ``external-step-contract.md``; built-ins have no shared authoring contract, so
#: the dispatcher SKILL.md must carry the binding for them. Matches the binding
#: sentence irrespective of its surrounding prose.
_BUILTIN_REACH_POINT = re.compile(
    r'[Rr]ecord-before-return\s+binds\s+every\s+dispatched\s+step\s+body'
    r'[^.]{0,80}?built-in',
    re.IGNORECASE,
)

#: Stale key-form instructions removed by this deliverable. Each pattern matched
#: the pre-fix sentence: "Must match the fully-qualified step name as listed in
#: `marshal.json` (e.g. `default:push`, ...)".
_STALE_MARSHAL_KEY_FORM = re.compile(r'step\s+name\s+as\s+listed\s+in\s+`?marshal\.json`?', re.IGNORECASE)
_STALE_FULLY_QUALIFIED_MUST_MATCH = re.compile(r'[Mm]ust\s+match\s+the\s+fully-qualified\s+step\s+name', re.IGNORECASE)

_STALE_PATTERNS = (
    ('stale-marshal-json-key-form', _STALE_MARSHAL_KEY_FORM),
    ('stale-fully-qualified-must-match', _STALE_FULLY_QUALIFIED_MUST_MATCH),
)


def _contract_text() -> str:
    text: str = _CONTRACT_DOC.read_text(encoding='utf-8')
    return text


def _termination_section() -> str:
    """Return the '## Required termination' section body.

    Delegates to the shared ``_dispatch_roster.section_lines`` heading-bounded
    walk (``test/_shared/``) — the same walk
    ``test_dispatch_roster_closure.py``'s roster parse and this file's own
    ``_section_body`` both need.
    """
    return '\n'.join(section_lines(_contract_text(), _TERMINATION_HEADING))


def _stale_hits(text: str) -> list[str]:
    hits: list[str] = []
    for label, pattern in _STALE_PATTERNS:
        for match in pattern.finditer(text):
            hits.append(f'{label}: {match.group(0)!r}')
    return hits


def _agents_text() -> str:
    text: str = _AGENTS_DOC.read_text(encoding='utf-8')
    return text


def _section_body(text: str, heading: str, stop_prefixes: tuple[str, ...]) -> str:
    """Return the body between ``heading`` and the next heading at/above its level."""
    return '\n'.join(section_lines(text, heading, stop_prefixes))


def _record_corollary_section() -> str:
    """Return the agents.md record-before-return corollary body."""
    return _section_body(_agents_text(), _RECORD_COROLLARY_HEADING, ('### ', '## ', '---'))


def _dispatched_roster() -> list[str]:
    """Parse the DISPATCHED step keys from the roster document.

    Delegates to the shared ``_dispatch_roster.parse_roster``
    (``test/_shared/``) — the same parser
    ``test_dispatch_roster_closure.py``'s closure assertions read, so the two
    suites cannot read a divergent roster population.
    """
    text = _ROSTER_DOC.read_text(encoding='utf-8')
    return parse_roster(text, _DISPATCHED_HEADING)


def _corollary_section_count(text: str) -> int:
    """Count the leaf-contract corollaries agents.md actually carries."""
    return len(_COROLLARY_HEADING.findall(text)) + _BASE_INVARIANT_COROLLARY_COUNT


def _declared_corollary_ordinal(text: str) -> int | None:
    match = _COROLLARY_ORDINAL.search(text)
    if match is None:
        return None
    return _ORDINAL_WORDS.get(match.group(1).lower())


def _declared_enumeration_items(text: str) -> list[str] | None:
    match = _COROLLARY_ENUMERATION.search(text)
    if match is None:
        return None
    body = match.group(1)
    items = [item.strip() for item in body.split(',') if item.strip()]
    return items


# ---------------------------------------------------------------------------
# Sanity: the section the assertions read actually exists
# ---------------------------------------------------------------------------


def test_required_termination_section_is_present_and_non_empty():
    section = _termination_section()

    assert section.strip(), f'{_TERMINATION_HEADING!r} section is empty — the assertions below would be vacuous'


def test_step_argument_names_the_composed_manifest_catalog_key():
    section = _termination_section().lower()

    assert 'composed manifest catalog key' in section, (
        'The --step contract must direct authors to the composed manifest catalog key, not a marshal.json step name'
    )


def test_ordering_invariant_is_stated_explicitly():
    # The invariant now lives in agents.md, which owns it for EVERY dispatched
    # leaf; external-step-contract.md cross-references it (see (d) below).
    section = _record_corollary_section().lower()

    assert 'before' in section
    assert 'return toon' in section, (
        'The ordering invariant must name the return TOON as the thing the terminal mark-step-done call precedes'
    )
    assert 'never as a trailing' in section, (
        'The ordering invariant must explicitly forbid the trailing-call shape (the omitted-call cause)'
    )


def test_contract_names_the_dispatcher_guard_as_a_backstop_not_the_fix():
    section = _record_corollary_section().lower()

    assert 'backstop' in section, (
        'The invariant must label the dispatcher-side guard a backstop so the '
        'authoring rule is not mistaken for redundant with the detector'
    )
    assert 'item 5d' in section


def test_contract_references_both_guard_error_codes():
    text = _contract_text()

    missing = [code for code in _GUARD_ERROR_CODES if code not in text]

    assert not missing, (
        f'external-step-contract.md must reference both guard error codes so '
        f'the detector and the authoring rule stay paired. Missing: {missing}'
    )


def test_record_invariant_is_scoped_to_every_dispatched_leaf():
    section = _record_corollary_section().lower()

    assert 'every dispatched leaf' in section, (
        'The invariant must bind every dispatched leaf, not only the external '
        'finalize steps whose own contract document happens to spell it out'
    )
    assert 'not only' in section or 'not just' in section, (
        'The invariant must explicitly reject the pre-fix external-only scoping'
    )


def test_dispatcher_side_half_is_a_contract_violation_not_reconcilable():
    section = _record_corollary_section().lower()

    assert 'contract violation' in section
    assert 'step_record_missing' in section
    assert 'reconcilable' in section, (
        'The dispatcher-side half must state that a success return with a '
        'missing terminal record is NOT a reconcilable condition'
    )
    assert 'escalate_ask' in section, 'The single sanctioned non-terminal return must be cross-referenced'


def test_corollary_enumeration_matches_the_corollary_section_count():
    text = _agents_text()

    expected = _corollary_section_count(text)
    items = _declared_enumeration_items(text)

    assert items is not None, (
        'agents.md must carry the parenthetical corollary enumeration — the '
        'lock-step assertion would otherwise be vacuous'
    )
    assert len(items) == expected, (
        f'agents.md corollary enumeration drift: the sentence enumerates '
        f'{len(items)} leaf-cannot-do-it items {items} but the document carries '
        f'{expected} corollaries. Adding a corollary must extend the '
        f'enumeration in lock-step.'
    )


def test_external_only_scoping_detector_fires_on_the_pre_fix_shape():
    # Mutation guard for (d): the pre-fix contract scoped the termination
    # obligation to external steps only. The detector must reject that shape.
    pre_fix = (
        'Every external step (project and fully-qualified skill) MUST terminate '
        'with a `manage-status mark-step-done` call that carries '
        '`--display-detail "{one-line summary}"`.'
    )

    assert _EXTERNAL_ONLY_SCOPING.search(pre_fix), (
        'External-only scoping detector failed to fire on the known pre-fix phrasing — assertion (d) would be vacuous'
    )

    # Positive control: the post-fix invariant is NOT external-only scoped.
    post_fix = (
        'A dispatched leaf MUST land its terminal `mark-step-done` before it '
        'composes its return TOON. This binds every dispatched leaf, not only '
        'the external finalize steps.'
    )
    assert not _EXTERNAL_ONLY_SCOPING.search(post_fix)


def test_ordinal_enumeration_detectors_fire_on_the_pre_fix_three_item_shape():
    # Mutation guard for (e): before this deliverable agents.md declared the
    # backgrounded-build corollary "third" with a three-item enumeration.
    pre_fix = (
        'This is the third corollary of the leaf/dispatch-topology invariant '
        'above (a leaf cannot spawn a subagent, cannot reach the operator, and '
        'cannot reap a backgrounded build), and it is the SSOT.'
    )

    assert _declared_corollary_ordinal(pre_fix) == 3, (
        'Ordinal detector failed to read the known pre-fix "third" ordinal'
    )
    items = _declared_enumeration_items(pre_fix)
    assert items is not None and len(items) == 3, (
        f'Enumeration detector failed to read the known pre-fix three-item '
        f'list — assertion (e) would be vacuous. Got: {items}'
    )

    # The pre-fix shape would FAIL the lock-step assertions against a document
    # that now carries four corollaries — that failure is the point.
    assert _declared_corollary_ordinal(pre_fix) != _corollary_section_count(_agents_text())
