#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
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
(b) The record-before-return ordering invariant is stated explicitly.
(c) Both guard error codes (``step_record_missing``,
    ``step_record_mismatched_key``) are referenced by the contract, so the
    dispatcher-side detector and the authoring-side rule stay paired.

``test_stale_instruction_patterns_detect_the_pre_fix_prose`` is the mutation
guard: it asserts the stale-form patterns actually fire on the exact pre-fix
sentence, so a typo in a regex cannot make assertion (a) vacuously green.

Scope note: this deliverable is confined to ``phase-6-finalize``. The guard
implementation under ``manage-status/scripts/`` is a read-only consulted source
and is deliberately NOT asserted against here.
"""

from __future__ import annotations

import re

from conftest import MARKETPLACE_ROOT

_SKILL_DIR = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize'
_CONTRACT_DOC = _SKILL_DIR / 'standards' / 'external-step-contract.md'
_SKILL_DOC = _SKILL_DIR / 'SKILL.md'

_TERMINATION_HEADING = '## Required termination'

#: The two error codes the dispatcher-side guard distinguishes.
_GUARD_ERROR_CODES = ('step_record_missing', 'step_record_mismatched_key')

#: Stale key-form instructions removed by this deliverable. Each pattern matched
#: the pre-fix sentence: "Must match the fully-qualified step name as listed in
#: `marshal.json` (e.g. `default:push`, ...)".
_STALE_MARSHAL_KEY_FORM = re.compile(
    r'step\s+name\s+as\s+listed\s+in\s+`?marshal\.json`?', re.IGNORECASE
)
_STALE_FULLY_QUALIFIED_MUST_MATCH = re.compile(
    r'[Mm]ust\s+match\s+the\s+fully-qualified\s+step\s+name', re.IGNORECASE
)

_STALE_PATTERNS = (
    ('stale-marshal-json-key-form', _STALE_MARSHAL_KEY_FORM),
    ('stale-fully-qualified-must-match', _STALE_FULLY_QUALIFIED_MUST_MATCH),
)


def _contract_text() -> str:
    return _CONTRACT_DOC.read_text(encoding='utf-8')


def _termination_section() -> str:
    """Return the '## Required termination' section body."""
    lines = _contract_text().splitlines()
    try:
        start = next(
            i for i, line in enumerate(lines) if line.strip() == _TERMINATION_HEADING
        )
    except StopIteration:  # pragma: no cover — guarded by its own test
        raise AssertionError(
            f'Heading not found in external-step-contract.md: '
            f'{_TERMINATION_HEADING!r}'
        ) from None
    collected: list[str] = []
    for line in lines[start + 1 :]:
        if line.startswith('## '):
            break
        collected.append(line)
    return '\n'.join(collected)


def _stale_hits(text: str) -> list[str]:
    hits: list[str] = []
    for label, pattern in _STALE_PATTERNS:
        for match in pattern.finditer(text):
            hits.append(f'{label}: {match.group(0)!r}')
    return hits


# ---------------------------------------------------------------------------
# Sanity: the section the assertions read actually exists
# ---------------------------------------------------------------------------


def test_required_termination_section_is_present_and_non_empty():
    section = _termination_section()

    assert section.strip(), (
        f'{_TERMINATION_HEADING!r} section is empty — the assertions below '
        f'would be vacuous'
    )


# ---------------------------------------------------------------------------
# (a) the stale key-form instruction is gone
# ---------------------------------------------------------------------------


def test_stale_marshal_json_key_form_instruction_is_gone():
    hits = _stale_hits(_contract_text())

    assert not hits, (
        'external-step-contract.md still instructs the stale --step key form '
        '(the authoring instruction that seeded the key-form-split cause). '
        f'Offending fragments: {hits}'
    )


def test_step_argument_names_the_composed_manifest_catalog_key():
    section = _termination_section().lower()

    assert 'composed manifest catalog key' in section, (
        'The --step contract must direct authors to the composed manifest '
        'catalog key, not a marshal.json step name'
    )


def test_step_contract_states_the_bundle_skill_verbatim_carve_out():
    section = _termination_section().lower()

    # The `default:` half is normalised on write; the `bundle:skill` half is
    # preserved verbatim and is therefore the half still able to mismatch.
    assert 'verbatim' in section
    assert 'bundle:skill' in section
    assert 'normalis' in section or 'normaliz' in section


# ---------------------------------------------------------------------------
# (b) the record-before-return ordering invariant is present
# ---------------------------------------------------------------------------


def test_ordering_invariant_is_stated_explicitly():
    section = _termination_section().lower()

    assert 'before' in section
    assert 'return toon' in section, (
        'The ordering invariant must name the return TOON as the thing the '
        'terminal mark-step-done call precedes'
    )
    assert 'never as a trailing' in section, (
        'The ordering invariant must explicitly forbid the trailing-call shape '
        '(the omitted-call cause)'
    )


def test_ordering_invariant_has_its_own_heading():
    assert '### Ordering invariant — record before returning' in _contract_text()


def test_contract_names_the_dispatcher_guard_as_a_backstop_not_the_fix():
    section = _termination_section().lower()

    assert 'backstop' in section, (
        'The contract must label the dispatcher-side guard a backstop so the '
        'authoring rule is not mistaken for redundant with the detector'
    )
    assert 'item 5d' in section


# ---------------------------------------------------------------------------
# (c) detector and authoring rule stay paired
# ---------------------------------------------------------------------------


def test_contract_references_both_guard_error_codes():
    text = _contract_text()

    missing = [code for code in _GUARD_ERROR_CODES if code not in text]

    assert not missing, (
        f'external-step-contract.md must reference both guard error codes so '
        f'the detector and the authoring rule stay paired. Missing: {missing}'
    )


def test_skill_item_5d_records_the_two_cause_taxonomy():
    text = _SKILL_DOC.read_text(encoding='utf-8')

    # The corrected taxonomy: two independent causes, each named, with the
    # absorbed half identified as absorbed.
    assert 'key-form split' in text
    assert 'omitted call' in text
    for code in _GUARD_ERROR_CODES:
        assert code in text
    assert 'standards/external-step-contract.md' in text, (
        'Item 5d must point at the authoring-side contract for both causes'
    )


# ---------------------------------------------------------------------------
# Mutation guard for the stale-form sweep
# ---------------------------------------------------------------------------


def test_stale_instruction_patterns_detect_the_pre_fix_prose():
    pre_fix = (
        '- `--step` — MANDATORY. Must match the fully-qualified step name as '
        'listed in `marshal.json` (e.g. `default:push`, `project:foo`, or '
        '`plan-marshall:some-skill:some-script`). Mismatches here create orphan '
        'status records that the renderer cannot pair with the dispatched step.'
    )

    hits = _stale_hits(pre_fix)

    assert len(hits) == len(_STALE_PATTERNS), (
        f'Stale-form sweep failed to detect the known pre-fix --step '
        f'instruction — assertion (a) would be vacuous. Hits: {hits}'
    )


# ---------------------------------------------------------------------------
# Concurrency guard: this deliverable does not own the manage-status surface
# ---------------------------------------------------------------------------


def test_guard_implementation_is_only_a_consulted_source():
    # The contract cites the guard's behaviour but the fix is confined to
    # phase-6-finalize. Pin that the contract references the guard by its
    # dispatcher-side location rather than importing or re-specifying it.
    section = _termination_section()

    assert 'assert-step-recorded' in section
    assert 'manage-status/scripts' not in section, (
        'The authoring contract must not reach into the guard implementation '
        'path — it is a read-only consulted source, not this contract surface'
    )
