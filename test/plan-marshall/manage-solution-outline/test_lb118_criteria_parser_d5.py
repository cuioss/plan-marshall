#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""PLAN-LB-118 D5 — the parser reports what it could not read, and the documents state the
current behaviour.

An indented bold field under a criterion continues that criterion rather than ending the
block; a fenced block under a criterion stays in that criterion (so a ``- `` line inside it
is not a separate criterion, and an edit to the example is an edit to the criterion); an
unterminated fence is a named state a gate reads; the retired-parser replay matches the
retired rule on prose before the first bullet; and a continuation append to a criterion the
current parser froze is named ``rewritten``, not hidden as ``parser_extended``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import _criteria_snapshot as _snap

from conftest import get_skill_dir

PLAN_ID = 'lb118-criteria-parser-d5'


def _outline(block: str) -> str:
    return (
        '# Solution: criteria\n\n## Deliverables\n\n### 1. Deliver the change\n\n'
        '**Affected files:**\n- `src/parser.py` (write-new)\n\n'
        f'**Success Criteria:**\n{block}\n'
    )


def _plan(plan_context, block: str) -> Path:
    plan_dir = Path(plan_context.plan_dir_for(PLAN_ID))
    (plan_dir / 'status.json').write_text(
        json.dumps({'title': 'fixture', 'phases': [], 'current_phase': '6-finalize', 'metadata': {}}),
        encoding='utf-8',
    )
    (plan_dir / 'references.json').write_text(json.dumps({'base_branch': 'main'}), encoding='utf-8')
    (plan_dir / 'solution_outline.md').write_text(_outline(block), encoding='utf-8')
    return plan_dir


# --- D5 (a): an indented bold field continues its criterion -------------------------------


def test_an_indented_bold_field_under_a_criterion_keeps_the_later_criteria() -> None:
    body = '**Success Criteria:**\n- a criterion\n  **Given:** a state\n- a later criterion\n'

    criteria, unparsed = _snap.parse_success_criteria(body)

    assert criteria == ['a criterion **Given:** a state', 'a later criterion'], criteria
    assert unparsed == [], unparsed


def test_a_bullet_inside_a_fenced_block_is_not_a_criterion() -> None:
    body = '**Success Criteria:**\n- a real criterion\n```\n- not a criterion\n```\n- a second criterion\n'

    criteria, unparsed = _snap.parse_success_criteria(body)

    # The fence text STAYS in the criterion it sits under: the `- ` inside is not a
    # separate criterion, and the example is part of the criterion's frozen text.
    assert criteria == ['a real criterion ``` - not a criterion ```', 'a second criterion'], criteria
    assert unparsed == [], unparsed


def test_a_shorter_or_different_marker_does_not_close_a_fence() -> None:
    body = (
        '**Success Criteria:**\n- a real criterion\n'
        '~~~~\n```\n- not a criterion\n```\n~~~\n- still not a criterion\n~~~~\n- a second criterion\n'
    )

    criteria, unparsed = _snap.parse_success_criteria(body)

    assert criteria == [
        'a real criterion ~~~~ ``` - not a criterion ``` ~~~ - still not a criterion ~~~~',
        'a second criterion',
    ], criteria
    assert unparsed == [], unparsed


def test_a_fence_marker_with_trailing_text_does_not_close() -> None:
    body = '**Success Criteria:**\n- real\n```\n``` not a close\n- not a criterion\n```\n- second\n'

    criteria, unparsed = _snap.parse_success_criteria(body)

    assert criteria == ['real ``` ``` not a close - not a criterion ```', 'second'], criteria
    assert unparsed == [], unparsed


def test_a_four_space_indented_run_is_not_a_fence() -> None:
    """CommonMark: at most three spaces indent a fence; a backtick info string may not contain a backtick."""
    assert _snap._fence_marker('    ```') is None
    assert _snap._fence_marker('\t```') is None
    assert _snap._fence_marker('   ```') is not None
    assert _snap._fence_marker('``` a`b') is None
    assert _snap._fence_marker('~~~ a`b') is not None


def test_a_fenced_example_edited_between_freezes_is_reported(plan_context) -> None:
    """The example is part of the frozen criterion, so editing it is drift. Red at 75b5780d0."""
    plan_dir = _plan(plan_context, '- a criterion with an example\n```\nbefore\n```\n')
    assert _snap.write_snapshot(PLAN_ID)['status'] == 'success'
    (plan_dir / 'solution_outline.md').write_text(
        _outline('- a criterion with an example\n```\nafter\n```\n'), encoding='utf-8'
    )

    drift = _snap.criteria_drift(PLAN_ID)

    assert [row['kind'] for row in drift] == ['rewritten'], drift


def test_an_unterminated_fence_is_a_named_state_a_gate_reads(plan_context) -> None:
    """The unterminated fence is reported by ``criteria_drift``, not only in the freeze payload."""
    plan_dir = _plan(plan_context, '- a criterion\n```\nunclosed\n')
    criteria, unparsed = _snap.parse_success_criteria((plan_dir / 'solution_outline.md').read_text(encoding='utf-8'))
    assert criteria
    assert _snap.UNTERMINATED_FENCE in unparsed, unparsed
    assert _snap.write_snapshot(PLAN_ID)['status'] == 'success'

    drift = _snap.criteria_drift(PLAN_ID)

    assert [row['kind'] for row in drift] == ['criterion_unparsed'], drift


# --- D5 (b): the retired replay matches the retired rule before the first bullet ----------


def test_prose_before_the_first_bullet_makes_the_retired_replay_empty() -> None:
    body = '**Success Criteria:**\nprose before the bullet\n- a criterion\n'

    assert _snap._retired_criteria(body) == []


def test_a_fence_before_a_criterion_stops_the_retired_replay(plan_context) -> None:
    """An older snapshot whose live outline has a fence before the bullet is a rewrite."""
    plan_dir = _plan(plan_context, '```\ncode\n```\n- a criterion that wraps\n  onto a second line\n')
    snapshot = {
        'schema': _snap.SCHEMA,
        'plan_id': PLAN_ID,
        'deliverables': [{'number': 1, 'title': 'Deliver the change', 'criteria': ['a criterion that wraps']}],
        'request': {'done_when': [], 'source': 'absent'},
        'spec': None,
        'authorized_changes': [],
    }
    path = _snap.snapshot_path(PLAN_ID)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    assert _snap.record_snapshot_digest(PLAN_ID)
    assert (plan_dir / 'solution_outline.md').is_file()

    drift = _snap.criteria_drift(PLAN_ID)

    assert [row['kind'] for row in drift] == ['rewritten'], drift


# --- D5 (c): the snapshot carries the parser that froze it --------------------------------


def test_the_current_parser_freezes_the_parser_marker(plan_context) -> None:
    _plan(plan_context, '- the parser reads every criterion\n')

    payload = _snap.write_snapshot(PLAN_ID)

    assert payload['status'] == 'success', payload
    snapshot = _snap.read_snapshot(PLAN_ID)
    assert snapshot is not None
    assert snapshot[_snap.PARSER_KEY] == _snap.CURRENT_PARSER


def test_a_continuation_append_to_a_current_parser_snapshot_is_rewritten(plan_context) -> None:
    plan_dir = _plan(plan_context, '- the parser reads every criterion\n')
    assert _snap.write_snapshot(PLAN_ID)['status'] == 'success'
    # An author appends a continuation line after the current parser froze the snapshot.
    (plan_dir / 'solution_outline.md').write_text(
        _outline('- the parser reads every criterion\n  and more\n'), encoding='utf-8'
    )

    drift = _snap.criteria_drift(PLAN_ID)

    assert [row['kind'] for row in drift] == ['rewritten'], drift


def test_an_old_snapshot_still_migrates_as_parser_extended(plan_context) -> None:
    """A freeze with no parser marker is a migration, not an author's append."""
    plan_dir = _plan(plan_context, '- a criterion that wraps\n  onto a second line\n')
    snapshot = {
        'schema': _snap.SCHEMA,
        'plan_id': PLAN_ID,
        'deliverables': [{'number': 1, 'title': 'Deliver the change', 'criteria': ['a criterion that wraps']}],
        'request': {'done_when': [], 'source': 'absent'},
        'spec': None,
        'authorized_changes': [],
    }
    path = _snap.snapshot_path(PLAN_ID)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    assert _snap.record_snapshot_digest(PLAN_ID)
    assert (plan_dir / 'solution_outline.md').is_file()

    drift = _snap.criteria_drift(PLAN_ID)

    assert [row['kind'] for row in drift] == ['parser_extended'], drift


def test_a_future_parser_marker_is_not_treated_as_older(plan_context) -> None:
    """A marker at or above the current parser is not a migration."""
    _plan(plan_context, '- a criterion that wraps\n  onto a second line\n')
    snapshot = {
        'schema': _snap.SCHEMA,
        'plan_id': PLAN_ID,
        _snap.PARSER_KEY: _snap.CURRENT_PARSER + 1,
        'deliverables': [{'number': 1, 'title': 'Deliver the change', 'criteria': ['a criterion that wraps']}],
        'request': {'done_when': [], 'source': 'absent'},
        'spec': None,
        'authorized_changes': [],
    }
    path = _snap.snapshot_path(PLAN_ID)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    assert _snap.record_snapshot_digest(PLAN_ID)

    drift = _snap.criteria_drift(PLAN_ID)

    assert [row['kind'] for row in drift] == ['rewritten'], drift


# --- D5 (d): the cited lines state the current behaviour ----------------------------------


def test_the_cited_lines_carry_no_transitional_wording_or_plan_id() -> None:
    finalize = get_skill_dir('plan-marshall', 'phase-6-finalize')
    outline = get_skill_dir('plan-marshall', 'manage-solution-outline')
    texts = {
        'review-rubric.md': (finalize / 'standards' / 'review-rubric.md').read_text(encoding='utf-8'),
        '_criteria_snapshot.py': (outline / 'scripts' / '_criteria_snapshot.py').read_text(encoding='utf-8'),
        '_review_support_integrity.py': (finalize / 'scripts' / '_review_support_integrity.py').read_text(
            encoding='utf-8'
        ),
        '_review_support_validate.py': (finalize / 'scripts' / '_review_support_validate.py').read_text(
            encoding='utf-8'
        ),
        '_plan_parsing.py': (outline / 'scripts' / '_plan_parsing.py').read_text(encoding='utf-8'),
    }
    assert 'no longer suppressed' not in texts['_review_support_integrity.py']
    assert 'It replaces a regex' not in texts['_criteria_snapshot.py']
    for label, text in texts.items():
        # Derived from the general rule, not a hand list of plan ids.
        assert re.search(r'PLAN-[A-Z]+-\d+', text) is None, label


def test_the_count_less_rule_sits_beside_the_four_cases_sentence() -> None:
    """The count-less rule is pinned beside the four-cases sentence in all three texts."""
    finalize = get_skill_dir('plan-marshall', 'phase-6-finalize')
    texts = {
        'functional-review.md § 3e': (finalize / 'workflow' / 'functional-review.md').read_text(encoding='utf-8'),
        'review-rubric.md': (finalize / 'standards' / 'review-rubric.md').read_text(encoding='utf-8'),
        '_review_support_integrity.py': (finalize / 'scripts' / '_review_support_integrity.py').read_text(
            encoding='utf-8'
        ),
    }
    four_cases = 'A loss is reported in exactly four cases:'
    count_less = 'A declaration without a count decides a removal only, never a drop of a surviving test.'
    for label, text in texts.items():
        assert four_cases in text, label
        assert count_less in text, label
        assert text.index(count_less) > text.index(four_cases), label
