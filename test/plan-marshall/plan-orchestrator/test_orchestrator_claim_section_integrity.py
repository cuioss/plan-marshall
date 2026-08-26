#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""End-to-end integrity suite for the claim-section parse state and its recovery.

`test_orchestrator_corpus.py` pins the parse-state discrimination and the
section-scoped write per seam, as unit controls beside the rest of the corpus
surface. This module exercises the same public seams (`cmd_corpus_verdicts`,
`cmd_corpus_set_verdict`) from the OUTSIDE, at a scope no per-seam control
covers, and duplicates no assertion from that suite.

Three groups, all population-derived:

- **(a) The write-side journey** — one walk of read -> recover -> re-read ->
  admit against a single table-form spec, asserting the recovery actually CLEARS
  the block rather than merely writing a bullet, and that the claim prose is
  byte-identical afterwards. "Recovered without re-authoring the prose" is
  pinned on the DISK, not on the return envelope.
- **(b) The detector fixture matrix** — one payload over a published population
  of five authoring forms: the two known-blind ones (table-form, prose-only),
  a matched bullet-form positive control, and the empty/absent pair that must
  NOT be detected. The two negatives are what make "stays distinguishable from
  genuinely empty or absent" a control rather than a claim.
- **(c) The pre-fix negative control** — a fixture carrying the SUPERSEDED
  zero-state parser verbatim, asserting it classified the two blind forms
  identically to the absent one. This proves the split CHANGED the match set
  rather than merely being present, mirroring the negative-fixture practice the
  corpus suite already states for its indentation group.

Every count-bearing assertion publishes the fixture-population size it was
computed over, and each group fails loudly when its fixture epic did not
materialize on disk — a suite that silently measured nothing would report the
same green as one that measured everything.
"""

import json
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import load_script_module

_orch = load_script_module(
    'plan-marshall', 'plan-orchestrator', 'orchestrator.py', 'orchestrator_script'
)

cmd_corpus_verdicts = _orch.cmd_corpus_verdicts
cmd_corpus_set_verdict = _orch.cmd_corpus_set_verdict
parse_claim_section = _orch._parse_claim_section
fenced_mask = _orch._fenced_mask
section_span = _orch._section_span
claim_block_end = _orch._claim_block_end
BULLET_RE = _orch._BULLET_RE
CLAIM_LABELS_HEADING_RE = _orch.CLAIM_LABELS_HEADING_RE
VERDICT_KEYS = _orch.VERDICT_KEYS
VERDICT_PREFIX = _orch.VERDICT_PREFIX
CLAIM_SECTION_STATES = _orch.CLAIM_SECTION_STATES
CLAIM_SECTION_ABSENT = _orch.CLAIM_SECTION_ABSENT
CLAIM_SECTION_EMPTY = _orch.CLAIM_SECTION_EMPTY
CLAIM_SECTION_UNREADABLE = _orch.CLAIM_SECTION_UNREADABLE
CLAIM_SECTION_PARSED = _orch.CLAIM_SECTION_PARSED

SLUG = 'fixture-integrity-epic'
FIXED_TIMESTAMP = '2020-01-01T00:00:00Z'
SHA = '9f3a1c2'
PRODUCER = 'fixture-integrity-epic/cleanup'

#: The verdict bullet prefix as it appears at TOP level — the section-scoped
#: shape. Derived from the module's own prefix constant so a change to the token
#: cannot leave this suite quietly matching nothing.
_TOP_LEVEL_VERDICT_PREFIX = f'- {VERDICT_PREFIX}'


# =============================================================================
# Fixture builders
# =============================================================================


def _epic_dir(plan_context) -> Path:
    return Path(plan_context.fixture_dir) / 'orchestrator' / SLUG


def _write_status(plan_context, plan_ids: list) -> Path:
    """Write a kind=orchestrator fixture status.json into the isolated store."""
    doc = {
        'kind': 'orchestrator',
        'title': 'Fixture Integrity Epic',
        'phase': 'orchestrating',
        'workstreams': ['WS-01'],
        'plans': [
            {
                'id': plan_id,
                'slug': plan_id.lower(),
                'workstream': 'WS-01',
                'status': 'staged',
                'plan_marshall_plan_id': '',
                'pr': '',
                'landing': '',
            }
            for plan_id in plan_ids
        ],
        'resume_anchor': 'fixture',
        'metadata': {},
        'created': FIXED_TIMESTAMP,
        'updated': FIXED_TIMESTAMP,
    }
    path = _epic_dir(plan_context) / 'status.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2), encoding='utf-8')
    return path


def _spec_text(claim_lines: list | None) -> str:
    """Render a spec whose claim section carries ``claim_lines``.

    ``None`` omits the ``## Claim Labels`` heading entirely — the ``absent``
    form, which is structurally different from a heading with an empty body and
    is exactly the pair this suite exists to keep apart.
    """
    head = ['# PLAN-NN: Fixture', '', '## Objective', '', 'Fixture objective.', '']
    section = [] if claim_lines is None else ['## Claim Labels', '', *claim_lines, '']
    tail = ['## Expected Surface', '', '- OBSERVED: `a.py` — `f`']
    return '\n'.join([*head, *section, *tail]) + '\n'


def _write_spec(plan_context, name: str, claim_lines: list | None) -> Path:
    path = _epic_dir(plan_context) / 'plans' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_spec_text(claim_lines), encoding='utf-8')
    return path


def _section_scope_args(
    plan: str,
    verdict: str = 'corroborated',
    rescoped: str = 'n/a',
    evidence: str = 'the section is settled as a whole',
) -> Namespace:
    """A complete ``set-verdict`` Namespace in the ``--section-scope`` mode."""
    return Namespace(
        slug=SLUG,
        plan=plan,
        claim_index=None,
        section_scope=True,
        verdict=verdict,
        checked_at=SHA,
        by=PRODUCER,
        rescoped=rescoped,
        evidence=evidence,
    )


# =============================================================================
# The published authoring-form population
# =============================================================================
#
# Five forms, each named with the state it must resolve to. The population is a
# module constant so every count-bearing assertion below can DERIVE its expected
# figures from it rather than restating a hand-typed number that would drift the
# moment a form is added.

_TABLE_FORM = [
    '| Claim | Confirm at |',
    '|-------|------------|',
    '| the write seam is single | `a.py` § `f` |',
]

_PROSE_FORM = [
    'The write seam is single: every stamp goes through `a.py` § `f`, verify at outline.',
]

_BULLET_FORM = ['- OBSERVED: the write seam is single — read at `a.py` § `f`']

#: ``(plan_id, spec_name, claim_lines, expected_state, detected)`` per form.
#: ``detected`` is membership of ``unreadable_claim_sections[]`` — true for the
#: two blind forms only, so the matrix carries its own matched negatives.
_FIXTURE_MATRIX: tuple[tuple[str, str, list | None, str, bool], ...] = (
    ('PLAN-01', 'PLAN-01-table.md', _TABLE_FORM, CLAIM_SECTION_UNREADABLE, True),
    ('PLAN-02', 'PLAN-02-prose.md', _PROSE_FORM, CLAIM_SECTION_UNREADABLE, True),
    ('PLAN-03', 'PLAN-03-bullet.md', _BULLET_FORM, CLAIM_SECTION_PARSED, False),
    ('PLAN-04', 'PLAN-04-empty.md', [], CLAIM_SECTION_EMPTY, False),
    ('PLAN-05', 'PLAN-05-absent.md', None, CLAIM_SECTION_ABSENT, False),
)

#: The fixture-population size, published beside every count derived from it.
_FIXTURE_COUNT = len(_FIXTURE_MATRIX)

#: The forms the detector must name, derived from the matrix rather than listed.
_EXPECTED_DETECTED = sorted(name for _, name, _, _, detected in _FIXTURE_MATRIX if detected)


def _materialize_matrix(plan_context) -> None:
    """Write every fixture form into one epic, then prove they reached the disk."""
    _write_status(plan_context, [plan_id for plan_id, *_ in _FIXTURE_MATRIX])
    for _, name, claim_lines, _, _ in _FIXTURE_MATRIX:
        _write_spec(plan_context, name, claim_lines)
    on_disk = sorted(path.name for path in (_epic_dir(plan_context) / 'plans').glob('PLAN-*.md'))
    assert on_disk == sorted(name for _, name, _, _, _ in _FIXTURE_MATRIX), (
        f'the fixture epic did not materialize: {len(on_disk)} of {_FIXTURE_COUNT} spec(s) on disk'
    )


# =============================================================================
# (a) The write-side journey: read -> recover -> re-read -> admit
# =============================================================================


class TestUnreadableToStampedJourney:
    """One walk of the whole recovery, asserted at each waypoint."""

    def _spec(self, plan_context) -> Path:
        _write_status(plan_context, ['PLAN-01'])
        spec = _write_spec(plan_context, 'PLAN-01-table.md', _TABLE_FORM)
        assert spec.is_file(), 'the fixture spec did not materialize on disk'
        return spec

    def test_the_journey_reports_blocks_recovers_and_admits(self, plan_context):
        spec = self._spec(plan_context)

        before = cmd_corpus_verdicts(Namespace(slug=SLUG))

        # Waypoint 1 — REPORTED: the spec is named, with its offending line.
        assert before['specs_scanned'] == 1, 'the fixture population did not materialize'
        assert before['unreadable_claim_sections'] == [
            {
                'spec': 'PLAN-01-table.md',
                'first_line': _TABLE_FORM[0],
                'section_verdict': 'absent',
            }
        ]
        # Waypoint 2 — BLOCKED: exactly one row, and it counts into the block.
        assert before['count'] == 1
        assert before['claims'][0]['verdict'] == 'indeterminate'
        assert before['claims'][0]['admits'] is False
        assert before['blocking_count'] == 1

        stamped = cmd_corpus_set_verdict(_section_scope_args('PLAN-01'))
        after = cmd_corpus_verdicts(Namespace(slug=SLUG))

        # Waypoint 3 — RECOVERED: one call, and the section is now settled.
        assert stamped['status'] == 'success'
        assert after['unreadable_claim_sections'][0]['section_verdict'] == 'present'
        # Waypoint 4 — ADMITS: the block is CLEARED, not merely written over.
        assert after['count'] == 1
        row = after['claims'][0]
        assert row['scope'] == 'section'
        assert row['admits'] is True
        for key in VERDICT_KEYS:
            assert row[key], f'{key} did not survive the section-scoped round trip'
        assert after['blocking_count'] == before['blocking_count'] - 1
        assert spec.is_file()

    def test_the_blocking_row_carries_the_offending_line_itself(self, plan_context):
        # The shortfall reason `orchestrate.md` prescribes quotes the section's
        # first line, and that document also requires the reason to be DERIVED
        # from the blocking row rather than hand-typed. Both hold only if the
        # synthesised row carries the line itself; a blank `line` would force a
        # join against `unreadable_claim_sections[]` or an author typing the
        # value the same rule forbids.
        self._spec(plan_context)

        payload = cmd_corpus_verdicts(Namespace(slug=SLUG))

        assert payload['specs_scanned'] == 1, 'the fixture population did not materialize'
        synthesised = [row for row in payload['claims'] if row['synthesised']]
        assert len(synthesised) == 1, (
            f'{len(synthesised)} synthesised row(s) over 1 unreadable section, expected 1'
        )
        assert synthesised[0]['line'] == _TABLE_FORM[0], (
            'the blocking row does not carry the offending line, so the shortfall '
            'reason cannot be derived from it'
        )
        # Same value, both surfaces: the join is now redundant, not broken.
        assert payload['unreadable_claim_sections'][0]['first_line'] == _TABLE_FORM[0]

    def test_a_readable_section_row_still_carries_its_own_bullet_line(self, plan_context):
        # Matched negative control for the assertion above: the `line` field is
        # not unconditionally the section's first line. A section carrying a real
        # top-level verdict bullet takes the non-synthesised branch, whose `line`
        # is that bullet — so a fix that hard-wired `first_line` into every
        # section row would fail here.
        self._spec(plan_context)
        cmd_corpus_set_verdict(_section_scope_args('PLAN-01'))

        payload = cmd_corpus_verdicts(Namespace(slug=SLUG))

        rows = [row for row in payload['claims'] if row['scope'] == 'section']
        assert len(rows) == 1, f'{len(rows)} section row(s), expected 1'
        assert rows[0]['synthesised'] is False
        assert rows[0]['line'].startswith(_TOP_LEVEL_VERDICT_PREFIX), (
            'a settled section row must quote its own verdict bullet, not the '
            'section heading line'
        )

    def test_the_claim_prose_survives_the_stamp_byte_for_byte(self, plan_context):
        # The disk-level half of "recovered without re-authoring the prose": the
        # stamped file is the original file plus EXACTLY the one added bullet.
        spec = self._spec(plan_context)
        before = spec.read_text(encoding='utf-8')

        cmd_corpus_set_verdict(_section_scope_args('PLAN-01'))

        after = spec.read_text(encoding='utf-8')
        added = [
            line for line in after.splitlines() if line.startswith(_TOP_LEVEL_VERDICT_PREFIX)
        ]
        kept = [
            line
            for line in after.splitlines()
            if not line.startswith(_TOP_LEVEL_VERDICT_PREFIX)
        ]
        assert len(added) == 1, f'{len(added)} section verdict bullet(s) written, expected 1'
        assert '\n'.join(kept) + '\n' == before, (
            'the stamp rewrote the surrounding document rather than inserting one line'
        )


# =============================================================================
# (b) The detector fixture matrix
# =============================================================================


class TestDetectorFixtureMatrix:
    """One payload over five authoring forms — two blind, three that must not be."""

    def test_the_matrix_population_is_well_formed(self):
        # Non-vacuity guard on the matrix itself: it must exercise every member of
        # the vocabulary AND carry at least one negative, or the two assertions
        # below could both pass over a population that proves nothing.
        states = {state for _, _, _, state, _ in _FIXTURE_MATRIX}

        assert _FIXTURE_COUNT == 5
        assert states == set(CLAIM_SECTION_STATES), (
            f'{len(CLAIM_SECTION_STATES)} state(s) in the vocabulary, {len(states)} in the matrix'
        )
        assert len(_EXPECTED_DETECTED) == 2
        assert _FIXTURE_COUNT - len(_EXPECTED_DETECTED) == 3, 'the matched negatives are missing'

    def test_the_detector_names_exactly_the_two_blind_forms(self, plan_context):
        _materialize_matrix(plan_context)

        result = cmd_corpus_verdicts(Namespace(slug=SLUG))

        assert result['specs_scanned'] == _FIXTURE_COUNT, (
            f'{_FIXTURE_COUNT} fixture(s) written, {result["specs_scanned"]} scanned'
        )
        named = sorted(row['spec'] for row in result['unreadable_claim_sections'])
        assert named == _EXPECTED_DETECTED
        assert result['unreadable_claim_section_count'] == len(_EXPECTED_DETECTED)

    def test_the_tally_accounts_for_every_fixture_across_the_vocabulary(self, plan_context):
        _materialize_matrix(plan_context)

        result = cmd_corpus_verdicts(Namespace(slug=SLUG))

        tally = {row['state']: row['count'] for row in result['claim_section_states']}
        expected: dict = dict.fromkeys(CLAIM_SECTION_STATES, 0)
        for _, _, _, state, _ in _FIXTURE_MATRIX:
            expected[state] += 1
        assert tally == expected
        assert sum(tally.values()) == _FIXTURE_COUNT == result['specs_scanned'], (
            'the tally, the fixture population and the scanned population must agree'
        )

    def test_the_scanned_population_rides_every_count(self, plan_context):
        # A detector that can report a zero it never derived is the defect this
        # whole plan removes, so the denominator is asserted to be present and
        # non-zero on the same payload that carries the counts.
        _materialize_matrix(plan_context)

        result = cmd_corpus_verdicts(Namespace(slug=SLUG))

        assert result['specs_total'] == _FIXTURE_COUNT
        assert result['specs_scanned'] == _FIXTURE_COUNT
        assert result['unreadable_count'] == 0, 'no fixture spec should be unreadable as a FILE'


# =============================================================================
# (c) The pre-fix negative control
# =============================================================================
#
# The controls above are green by construction once the split is in place, which
# is the shape that lets a suite pass while proving nothing about what changed.
# The fixture below carries the SUPERSEDED zero-state parser VERBATIM — the body
# of the retired `_parse_claims`, whose only return value for a section it could
# not read was the same empty list it returned for a section that was not there.
# It rides the module's own unchanged primitives (`_fenced_mask`, `_section_span`,
# `_BULLET_RE`, `_claim_block_end`), because what was superseded is the RETURN
# SHAPE, not the scan.


def _pre_fix_parse_claims(lines: list) -> list:
    """The retired ``_parse_claims`` body, verbatim: a bare claim list, no state."""
    fenced = fenced_mask(lines)
    start, end = section_span(lines, CLAIM_LABELS_HEADING_RE, fenced)
    if start < 0:
        return []
    claims: list = []
    for index in range(start, end):
        if fenced[index]:
            continue
        match = BULLET_RE.match(lines[index])
        if match is None:
            continue
        indent = match.group('indent')
        text = match.group('text').strip()
        if not indent:
            claims.append(
                {
                    'index': len(claims),
                    'line': index,
                    'indent': indent,
                    'text': text,
                    'block_end': claim_block_end(lines, index, end, fenced),
                    'verdict_line': -1,
                    'verdict_text': '',
                }
            )
        elif claims and text.startswith(VERDICT_PREFIX) and claims[-1]['verdict_line'] < 0:
            claims[-1]['verdict_line'] = index
            claims[-1]['verdict_text'] = text
    return claims


#: The three forms the pre-fix parser could not tell apart — it returned the same
#: empty list for every one of them, which is what the class below pins.
_COLLAPSED_FORMS = (
    ('table', _TABLE_FORM),
    ('prose', _PROSE_FORM),
    ('absent', None),
)


class TestPreFixParserCollapsedTheThreeForms:
    def test_the_pre_fix_parser_returned_the_same_empty_list_for_all_three(self):
        outcomes = {
            name: _pre_fix_parse_claims(_spec_text(claim_lines).splitlines())
            for name, claim_lines in _COLLAPSED_FORMS
        }

        assert len(outcomes) == 3, 'the collapsed-form population did not materialize'
        assert list(outcomes.values()) == [[], [], []], (
            'the pre-fix parser is expected to be BLIND here — a non-empty list '
            'means the fixture no longer reproduces the superseded behaviour'
        )

    def test_the_split_changed_the_match_set(self):
        # The bound is proven to have CHANGED the outcome, not merely to exist:
        # the same three inputs now resolve to two DISTINCT states.
        states = {
            name: parse_claim_section(_spec_text(claim_lines).splitlines())['state']
            for name, claim_lines in _COLLAPSED_FORMS
        }

        assert states == {
            'table': CLAIM_SECTION_UNREADABLE,
            'prose': CLAIM_SECTION_UNREADABLE,
            'absent': CLAIM_SECTION_ABSENT,
        }
        assert len(set(states.values())) == 2, (
            'the three forms still collapse to one state — the split is inert'
        )

    @pytest.mark.parametrize(
        ('name', 'claim_lines'), _COLLAPSED_FORMS, ids=[form for form, _ in _COLLAPSED_FORMS]
    )
    def test_the_claim_list_itself_is_unchanged_by_the_split(self, name, claim_lines):
        # Matched control on the other direction: the split added a state, it did
        # not move any claim. Both parsers still agree there is no claim here, so
        # the only thing that changed is what that emptiness is REPORTED as.
        lines = _spec_text(claim_lines).splitlines()

        assert _pre_fix_parse_claims(lines) == parse_claim_section(lines)['claims'] == []
