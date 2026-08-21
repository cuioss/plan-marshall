#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``compact`` verb of the plan-orchestrator script.

The ledger-compaction stage regenerates every DERIVABLE surface of ``epic.md``
in place — the START-HERE resume summary and the Ordered Queue table — and
leaves every byte OUTSIDE the ``BEGIN/END GENERATED`` markers untouched. The
module is organised around the properties that make the stage safe to run
unattended:

- **Derivable is regenerated** — a stale queue row is corrected from
  ``status.json``, never preserved.
- **Narrative survives verbatim** — a retraction, an annotation, and every
  hand-authored section sit outside the markers and are byte-identical after a
  pass. This is the test that protects everything the stage is for: a compaction
  that can drop a retraction is a destructive tool wearing a tidy name.
- **Idempotent** — a second run finds every block ``unchanged`` and writes
  nothing.
- **Refuses a closed epic** — that tree is the frozen audit record; compaction
  is a live-epic operation only.
- **Reports every mutation and every abstention** — a silent compaction is
  indistinguishable from a lossy one.
- **Invariants bite** — the queue<->spec reconciliation is bidirectional, no
  terminal row leaks into the live queue, and every relocation pointer resolves.

Everything runs against a SCAFFOLDED FIXTURE EPIC under ``PLAN_BASE_DIR``
isolation — never the live ``truthful-signals`` tree.
"""

import json
from argparse import Namespace
from pathlib import Path

from conftest import get_script_path, load_script_module, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'plan-orchestrator', 'orchestrator.py')

_orch = load_script_module(
    'plan-marshall', 'plan-orchestrator', 'orchestrator.py', 'orchestrator_compact_script'
)

cmd_compact = _orch.cmd_compact
GENERATED_BLOCKS = _orch.GENERATED_BLOCKS
INBOX_SUBDIR = _orch.INBOX_SUBDIR

SLUG = 'fixture-compact-epic'
FIXED_TIMESTAMP = '2020-01-01T00:00:00Z'

#: A settled narrative statement that must survive a pass byte-identical. It is
#: exactly the anti-rework record the stage exists to protect.
RETRACTION = '- 2020-01-01 — RETRACTED: the spec-corruption claim was withdrawn; do not re-flag it.'

#: A hand annotation in the START-HERE zone, and a per-row queue caveat — both
#: OUTSIDE their block's markers, both must survive regeneration.
START_ANNOTATION = '- PLAN-01 — a hand annotation the generator does not produce.'
QUEUE_ANNOTATION = '- PLAN-01 — sequencing caveat the generator cannot derive.'
VISION_TEXT = 'A fixture epic exercising the compact stage.'
OPEN_DEFECT = '- a known defect not yet owned by a plan — source: observation'
WATCH = '- a mid-flight watch — re-check at the next landing'


# =============================================================================
# Fixture builders
# =============================================================================


def _epic_dir(plan_context) -> Path:
    return Path(plan_context.fixture_dir) / 'orchestrator' / SLUG


def _row(plan_id: str, status: str = 'staged', workstream: str = 'WS-01') -> dict:
    return {
        'id': plan_id,
        'slug': plan_id.lower(),
        'workstream': workstream,
        'status': status,
        'plan_marshall_plan_id': '',
        'pr': '',
        'landing': '',
    }


def _write_status(
    plan_context,
    rows: list,
    phase: str = 'orchestrating',
    resume_anchor: str = 'await nothing',
) -> Path:
    doc = {
        'kind': 'orchestrator',
        'title': 'Fixture Compact Epic',
        'phase': phase,
        'workstreams': ['WS-01'],
        'plans': rows,
        'resume_anchor': resume_anchor,
        'metadata': {},
        'created': FIXED_TIMESTAMP,
        'updated': FIXED_TIMESTAMP,
    }
    path = _epic_dir(plan_context) / 'status.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2), encoding='utf-8')
    return path


def _write_spec(plan_context, name: str, surface: list[str] | None = None) -> Path:
    body = '# Fixture spec\n\n## Claim Labels\n\n- OBSERVED: a claim\n'
    if surface:
        rendered = '\n'.join(f'- `{path}`' for path in surface)
        body += f'\n## Expected Surface\n\n{rendered}\n'
    path = _epic_dir(plan_context) / 'plans' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding='utf-8')
    return path


def _write_broken_spec(plan_context, name: str) -> Path:
    path = _epic_dir(plan_context) / 'plans' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'\xff\xfe not valid utf-8 \xff')
    return path


def _default_queue_body() -> str:
    return (
        '| # | Plan | Workstream | Status | Surface (expected) |\n'
        '|---|------|------------|--------|--------------------|\n'
        '| 1 | PLAN-01-alpha | WS-01 | STALE-STATUS | (stale surface) |'
    )


def _epic_md(
    *,
    resume_body: str = 'OLD RESUME BODY — pre-regeneration',
    queue_body: str | None = None,
    decisions: str = RETRACTION,
    include_queue_markers: bool = True,
    pointer_line: str = '',
) -> str:
    queue_body = _default_queue_body() if queue_body is None else queue_body
    ordered_queue_section = (
        [
            _orch._begin_marker('ordered-queue'),
            queue_body,
            _orch._end_marker('ordered-queue'),
        ]
        if include_queue_markers
        else ['| # | Plan | Workstream | Status | Surface (expected) |', queue_body]
    )
    return (
        '\n'.join(
            [
                '# Epic: Fixture Compact Epic',
                '',
                f'slug: {SLUG}',
                '',
                '## Vision',
                '',
                VISION_TEXT,
                '',
                '## START HERE',
                '',
                _orch._begin_marker('resume-summary'),
                resume_body,
                _orch._end_marker('resume-summary'),
                '',
                '### Annotations',
                '',
                START_ANNOTATION,
                '',
                '## Ordered Queue',
                '',
                *ordered_queue_section,
                '',
                '### Queue annotations',
                '',
                QUEUE_ANNOTATION,
                '',
                '## Decisions',
                '',
                decisions,
                '',
                '## Open Defects',
                '',
                OPEN_DEFECT,
                pointer_line,
                '',
                '## Watches',
                '',
                WATCH,
                '',
            ]
        )
        + '\n'
    )


def _write_epic(plan_context, **kwargs) -> Path:
    path = _epic_dir(plan_context) / 'epic.md'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_epic_md(**kwargs), encoding='utf-8')
    return path


def _live_epic(plan_context, rows: list | None = None, **epic_kwargs) -> Path:
    """Materialize a live epic: a status.json queue, one spec, and an epic.md."""
    rows = rows if rows is not None else [_row('PLAN-01')]
    _write_status(plan_context, rows)
    _write_spec(plan_context, 'PLAN-01-alpha.md', surface=['scripts/a.py'])
    return _write_epic(plan_context, **epic_kwargs)


def _run() -> dict:
    result: dict = cmd_compact(Namespace(slug=SLUG))
    return result


def _epic_text(plan_context) -> str:
    return (_epic_dir(plan_context) / 'epic.md').read_text(encoding='utf-8')


def _block_body(text: str, name: str) -> str:
    lines = text.split('\n')
    begin, end = _orch._marker_indices(lines, name)
    assert begin >= 0 and end >= 0, f'block {name!r} markers not found'
    return '\n'.join(lines[begin + 1 : end])


def _invariant(result: dict, name: str) -> dict:
    rows: list[dict] = [row for row in result['invariants'] if row['invariant'] == name]
    assert len(rows) == 1, f'expected exactly one {name!r} invariant, got {len(rows)}'
    return rows[0]


def _regenerated(result: dict, surface: str) -> dict:
    rows: list[dict] = [row for row in result['regenerated'] if row['surface'] == surface]
    assert len(rows) == 1, f'expected exactly one {surface!r} regenerated row'
    return rows[0]


def _abstained(result: dict, section: str) -> dict:
    rows: list[dict] = [row for row in result['abstained'] if row['section'] == section]
    assert len(rows) == 1, (
        f'expected exactly one {section!r} abstained row, got '
        f'{[row["section"] for row in result["abstained"]]}'
    )
    return rows[0]


# =============================================================================
# Report shape and the happy path
# =============================================================================


class TestCompactShape:
    def test_reports_operation_and_relocation_target(self, plan_context):
        _live_epic(plan_context)

        result = _run()

        assert result['status'] == 'success'
        assert result['operation'] == 'compact'
        assert result['relocation_target'] == 'settled.md'

    def test_regenerates_every_declared_block(self, plan_context):
        _live_epic(plan_context)

        result = _run()

        surfaces = {row['surface'] for row in result['regenerated']}
        assert surfaces == set(GENERATED_BLOCKS)
        for row in result['regenerated']:
            assert row['outcome'] in ('regenerated', 'unchanged', 'markers_absent')
            assert isinstance(row['lines_before'], int)
            assert isinstance(row['lines_after'], int)

    def test_carries_three_invariants_each_with_verdict_evidence_population(self, plan_context):
        _live_epic(plan_context)

        result = _run()

        assert {row['invariant'] for row in result['invariants']} == {
            'queue_spec_bidirectional',
            'no_terminal_in_live_queue',
            'relocated_pointer_reachable',
        }
        for row in result['invariants']:
            assert set(row) == {'invariant', 'verdict', 'evidence', 'population'}
            assert row['verdict'] in ('ok', 'violated', 'indeterminate')
            assert row['evidence'].strip()
            assert row['population'].strip()

    def test_abstained_names_the_narrative_sections_left_verbatim(self, plan_context):
        _live_epic(plan_context)

        result = _run()

        abstained = {row['section'] for row in result['abstained']}
        # The two sections that CONTAIN a generated block are regenerated, not abstained.
        assert 'START HERE' not in abstained
        assert 'Ordered Queue' not in abstained
        # Every hand-authored section is named as preserved.
        assert {'Vision', 'Decisions', 'Open Defects', 'Watches'} <= abstained
        assert result['abstained_count'] == len(result['abstained'])
        for row in result['abstained']:
            assert row['treatment'] == 'preserved_verbatim'


# =============================================================================
# Derivable is regenerated; narrative survives verbatim
# =============================================================================


class TestDerivableRegeneration:
    def test_a_stale_queue_row_is_corrected_from_status_json(self, plan_context):
        # status.json is authority: the row is parked; the epic.md table shows a
        # stale status. After compaction the table reflects status.json.
        _write_status(plan_context, [_row('PLAN-01', status='parked')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface=['scripts/a.py'])
        _write_epic(plan_context)

        result = _run()

        queue = _block_body(_epic_text(plan_context), 'ordered-queue')
        assert '| parked |' in queue
        assert 'STALE-STATUS' not in queue
        assert result['epic_changed'] is True
        assert _regenerated(result, 'ordered-queue')['outcome'] == 'regenerated'

    def test_the_surface_column_is_derived_from_the_spec(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface=['scripts/a.py', 'scripts/b.py'])
        _write_epic(plan_context)

        _run()

        queue = _block_body(_epic_text(plan_context), 'ordered-queue')
        assert 'scripts/a.py' in queue
        assert 'scripts/b.py' in queue

    def test_a_row_without_a_spec_renders_a_named_marker_not_a_blank(self, plan_context):
        _write_status(plan_context, [_row('PLAN-09')])
        _write_epic(plan_context)

        _run()

        queue = _block_body(_epic_text(plan_context), 'ordered-queue')
        assert '(spec missing)' in queue

    def test_the_resume_summary_block_is_regenerated_from_status_json(self, plan_context):
        _live_epic(plan_context)

        _run()

        summary = _block_body(_epic_text(plan_context), 'resume-summary')
        assert 'OLD RESUME BODY' not in summary
        assert '**Resume anchor**' in summary


class TestNarrativeSurvivesVerbatim:
    def test_a_retraction_survives_a_pass_byte_identical(self, plan_context):
        _live_epic(plan_context)

        _run()

        assert RETRACTION in _epic_text(plan_context)

    def test_every_hand_authored_section_survives_verbatim(self, plan_context):
        """Every narrative section survives a pass, and a SECOND pass is byte-identical.

        The byte-identity claim is asserted across an actually-performed second
        pass. Comparing the settled text against a read taken BEFORE the first
        ``_run()`` would compare two different documents (the first pass rewrites
        the resume body), and comparing it against a re-read of the same file
        would be true by construction because nothing wrote between the reads.
        """
        _live_epic(plan_context)
        _run()
        after_first = _epic_text(plan_context)  # the settled text, after regeneration

        _run()

        after_second = _epic_text(plan_context)
        for fragment in (VISION_TEXT, START_ANNOTATION, QUEUE_ANNOTATION, OPEN_DEFECT, WATCH):
            assert fragment in after_second
        # A second pass changes nothing at all — across a pass that was performed.
        assert after_second == after_first

    def test_content_outside_the_markers_is_untouched_when_only_the_queue_changes(
        self, plan_context
    ):
        _write_status(plan_context, [_row('PLAN-01', status='parked')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface=['scripts/a.py'])
        _write_epic(plan_context, resume_body='**Resume anchor**: kept')
        before = _epic_text(plan_context)

        _run()

        after = _epic_text(plan_context)
        # The annotation zones and every narrative section are byte-identical.
        for fragment in (START_ANNOTATION, QUEUE_ANNOTATION, RETRACTION, VISION_TEXT):
            assert before.count(fragment) == after.count(fragment) == 1


# =============================================================================
# Idempotence
# =============================================================================


class TestIdempotence:
    def test_a_second_run_is_a_no_op_on_disk(self, plan_context):
        _live_epic(plan_context)
        _run()
        after_first = (_epic_dir(plan_context) / 'epic.md').read_bytes()

        result = _run()

        after_second = (_epic_dir(plan_context) / 'epic.md').read_bytes()
        assert result['epic_changed'] is False
        assert result['regenerated_count'] == 0
        assert all(row['outcome'] == 'unchanged' for row in result['regenerated'])
        assert after_first == after_second

    def test_first_run_regenerates_then_settles(self, plan_context):
        _live_epic(plan_context)

        first = _run()

        assert first['epic_changed'] is True
        assert first['regenerated_count'] >= 1


# =============================================================================
# Refusals — the closed epic and the missing tree
# =============================================================================


class TestRefusals:
    def test_refuses_a_closed_epic_and_leaves_it_byte_identical(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')], phase='closed')
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        epic_path = _write_epic(plan_context)
        before = epic_path.read_bytes()

        result = _run()

        assert result['status'] == 'error'
        assert result['error'] == 'refused_closed'
        assert result['phase'] == 'closed'
        assert epic_path.read_bytes() == before

    def test_rejects_an_invalid_slug(self, plan_context):
        result = cmd_compact(Namespace(slug='../evil'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_slug'

    def test_errors_when_the_epic_has_no_store_tree(self, plan_context):
        result = cmd_compact(Namespace(slug='absent-compact-epic'))

        assert result['status'] == 'error'
        assert result['error'] == 'not_found'

    def test_errors_when_epic_md_is_absent(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])

        result = _run()

        assert result['status'] == 'error'
        assert result['error'] == 'file_not_found'

    def test_errors_when_status_json_is_absent(self, plan_context):
        _write_epic(plan_context)

        result = _run()

        assert result['status'] == 'error'
        assert result['error'] == 'file_not_found'


# =============================================================================
# markers_absent — reported, never fabricated
# =============================================================================


class TestMarkersAbsent:
    def test_a_missing_block_is_reported_and_skipped_not_fabricated(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _write_epic(plan_context, include_queue_markers=False)

        result = _run()

        assert result['status'] == 'success'
        assert _regenerated(result, 'ordered-queue')['outcome'] == 'markers_absent'
        # The resume-summary block IS present, so it still regenerates.
        assert _regenerated(result, 'resume-summary')['outcome'] == 'regenerated'
        # No ordered-queue markers were inserted into the hand-authored doc.
        assert _orch._begin_marker('ordered-queue') not in _epic_text(plan_context)

    def test_an_unreachable_surface_is_not_reported_as_preserved_verbatim(self, plan_context):
        """A section the stage COULD NOT reach is distinguishable from one it left alone.

        ``## Ordered Queue`` carries a derivable surface. With its marker pair
        absent the stage cannot regenerate it, so reporting it as
        ``preserved_verbatim`` — a deliberate abstention — would claim a choice
        the stage never made.
        """
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _write_epic(plan_context, include_queue_markers=False)

        result = _run()

        assert _abstained(result, 'Ordered Queue')['treatment'] == (
            'markers_absent_not_regenerated'
        )

    def test_an_unreachable_surface_is_counted_apart_from_the_abstentions(self, plan_context):
        """``abstained_count`` counts choices; ``unreachable_count`` counts blind spots."""
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _write_epic(plan_context, include_queue_markers=False)

        result = _run()

        assert result['unreachable_count'] == 1
        preserved = [
            row for row in result['abstained'] if row['treatment'] == 'preserved_verbatim'
        ]
        assert result['abstained_count'] == len(preserved)
        assert 'Ordered Queue' not in [row['section'] for row in preserved]

    def test_a_purely_narrative_section_is_still_preserved_verbatim(self, plan_context):
        """The control: a section carrying no derivable surface keeps the old treatment."""
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _write_epic(plan_context, include_queue_markers=False)

        result = _run()

        assert _abstained(result, 'Decisions')['treatment'] == 'preserved_verbatim'

    def test_a_partial_marker_pair_is_reported_unreachable(self, plan_context):
        """A BEGIN with no END is a blind spot, and must not read as nothing at all.

        ``_replace_block`` reports ``markers_absent`` for a partial pair, but the
        owning section CONTAINS a BEGIN marker — so a section scan keyed on marker
        presence alone skips it, and the blind spot is reported by neither
        ``abstained[]`` nor ``unreachable_count``. That is the exact defect this
        treatment split exists to close, one level down.
        """
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        path = _epic_dir(plan_context) / 'epic.md'
        path.parent.mkdir(parents=True, exist_ok=True)
        # A queue section carrying BEGIN and no END.
        path.write_text(
            '\n'.join(
                [
                    '# Epic: Fixture Compact Epic',
                    '',
                    f'slug: {SLUG}',
                    '',
                    '## START HERE',
                    '',
                    _orch._begin_marker('resume-summary'),
                    'body',
                    _orch._end_marker('resume-summary'),
                    '',
                    '## Ordered Queue',
                    '',
                    _orch._begin_marker('ordered-queue'),
                    '| # | Plan | Workstream | Status | Surface (expected) |',
                    '',
                    '## Decisions',
                    '',
                    RETRACTION,
                    '',
                ]
            ),
            encoding='utf-8',
        )

        result = _run()

        assert _regenerated(result, 'ordered-queue')['outcome'] == 'markers_absent'
        assert _abstained(result, 'Ordered Queue')['treatment'] == (
            'markers_absent_not_regenerated'
        )
        assert result['unreachable_count'] == 1

    def test_a_reachable_ledger_reports_no_unreachable_section(self, plan_context):
        """With both marker pairs present nothing is unreachable, and the count says so."""
        _live_epic(plan_context)

        result = _run()

        assert result['unreachable_count'] == 0
        assert all(
            row['treatment'] == 'preserved_verbatim' for row in result['abstained']
        )


# =============================================================================
# replaced_body — a regenerated block NAMES what it overwrote
# =============================================================================


class TestReplacedBody:
    def test_a_regenerated_block_names_the_content_it_overwrote(self, plan_context):
        """A regenerated block reports WHAT it replaced, not merely a line-count delta.

        A hand-written line inside a generated block is overwritten by the first
        pass — legitimately, since the region is the generator's. Reporting only
        ``lines_before``/``lines_after`` would leave the operator unable to tell
        which bytes were lost, so the pre-write text rides ``replaced_body``.
        """
        hand_written = 'HAND-WRITTEN: do not re-derive, see PLAN-04'
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _write_epic(plan_context, resume_body=hand_written)

        result = _run()

        row = _regenerated(result, 'resume-summary')
        assert row['outcome'] == 'regenerated'
        assert hand_written in row['replaced_body']

    def test_an_unchanged_block_reports_an_empty_replaced_body(self, plan_context):
        """Nothing was overwritten, so there is nothing to name."""
        _live_epic(plan_context)
        _run()

        result = _run()

        for row in result['regenerated']:
            assert row['outcome'] == 'unchanged'
            assert row['replaced_body'] == ''


# =============================================================================
# Invariant — no terminal row in the live queue
# =============================================================================


class TestNoTerminalInLiveQueue:
    def test_a_shipped_row_is_excluded_from_the_live_queue(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01', status='staged'), _row('PLAN-02', status='shipped')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface=['scripts/a.py'])
        _write_spec(plan_context, 'PLAN-02-beta.md', surface=['scripts/b.py'])
        _write_epic(plan_context)

        result = _run()

        queue = _block_body(_epic_text(plan_context), 'ordered-queue')
        assert 'PLAN-01' in queue
        assert 'PLAN-02' not in queue
        assert _invariant(result, 'no_terminal_in_live_queue')['verdict'] == 'ok'

    def test_an_all_terminal_queue_renders_empty_and_still_passes(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01', status='shipped')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _write_epic(plan_context)

        result = _run()

        queue = _block_body(_epic_text(plan_context), 'ordered-queue')
        assert '(empty)' in queue
        assert _invariant(result, 'no_terminal_in_live_queue')['verdict'] == 'ok'


# =============================================================================
# Invariant — bidirectional queue <-> spec reconciliation
# =============================================================================


class TestQueueSpecInvariant:
    def test_a_reconciled_corpus_is_ok(self, plan_context):
        _live_epic(plan_context)

        result = _run()

        assert _invariant(result, 'queue_spec_bidirectional')['verdict'] == 'ok'

    def test_a_row_without_a_spec_is_violated(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _write_epic(plan_context)

        result = _run()

        row = _invariant(result, 'queue_spec_bidirectional')
        assert row['verdict'] == 'violated'
        assert '1 row(s) without a spec' in row['evidence']

    def test_a_spec_without_a_row_is_violated(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _write_spec(plan_context, 'PLAN-07-orphan.md')
        _write_epic(plan_context)

        result = _run()

        row = _invariant(result, 'queue_spec_bidirectional')
        assert row['verdict'] == 'violated'
        assert 'spec(s) without a row' in row['evidence']

    def test_an_unreadable_spec_is_indeterminate_not_violated(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _write_broken_spec(plan_context, 'PLAN-02-broken.md')
        _write_epic(plan_context)

        result = _run()

        row = _invariant(result, 'queue_spec_bidirectional')
        assert row['verdict'] == 'indeterminate'
        assert row['verdict'] != 'violated'


# =============================================================================
# Invariant — relocation pointer reachability
# =============================================================================

_POINTER = '> Relocated to `settled.md` § "Retracted spec-corruption claim" — settled narrative'


class TestPointerReachability:
    def test_no_pointer_is_ok(self, plan_context):
        _live_epic(plan_context)

        result = _run()

        row = _invariant(result, 'relocated_pointer_reachable')
        assert row['verdict'] == 'ok'
        assert '0 relocation pointer(s)' in row['population']

    def test_a_resolved_pointer_is_ok(self, plan_context):
        _live_epic(plan_context, pointer_line=_POINTER)
        (_epic_dir(plan_context) / 'settled.md').write_text(
            '# Settled narrative\n\n## Retracted spec-corruption claim\n\n'
            'The claim was withdrawn; do not re-flag it.\n',
            encoding='utf-8',
        )

        result = _run()

        assert _invariant(result, 'relocated_pointer_reachable')['verdict'] == 'ok'

    def test_a_pointer_with_no_settled_file_is_violated(self, plan_context):
        _live_epic(plan_context, pointer_line=_POINTER)

        result = _run()

        row = _invariant(result, 'relocated_pointer_reachable')
        assert row['verdict'] == 'violated'
        assert 'settled.md is absent' in row['evidence']

    def test_a_pointer_to_a_missing_heading_is_violated(self, plan_context):
        _live_epic(plan_context, pointer_line=_POINTER)
        (_epic_dir(plan_context) / 'settled.md').write_text(
            '# Settled narrative\n\n## A different heading\n\nunrelated\n', encoding='utf-8'
        )

        result = _run()

        row = _invariant(result, 'relocated_pointer_reachable')
        assert row['verdict'] == 'violated'
        assert 'Retracted spec-corruption claim' in row['evidence']


# =============================================================================
# The template carries the markers this stage regenerates
# =============================================================================


class TestTemplateContract:
    def test_the_epic_template_carries_every_generated_block_marker_pair(self):
        # The stage regenerates a block only if its markers exist. Pinning the
        # template's markers keeps the template<->script contract from drifting:
        # a block named in GENERATED_BLOCKS with no home in the template would
        # silently report markers_absent on every real epic.
        template = SCRIPT_PATH.parent.parent / 'templates' / 'epic.md'
        text = template.read_text(encoding='utf-8')

        for name in GENERATED_BLOCKS:
            assert _orch._begin_marker(name) in text, f'{name} BEGIN marker missing from template'
            assert _orch._end_marker(name) in text, f'{name} END marker missing from template'


# =============================================================================
# CLI boundary
# =============================================================================


class TestCompactCli:
    def test_reports_through_cli(self, plan_context):
        _live_epic(plan_context)
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}

        result = run_script(SCRIPT_PATH, 'compact', '--slug', SLUG, env_overrides=env)

        assert result.returncode == 0
        assert 'status: success' in result.stdout
        assert 'operation: compact' in result.stdout
        assert 'relocation_target: settled.md' in result.stdout

    def test_refuses_a_closed_epic_through_cli(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')], phase='closed')
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _write_epic(plan_context)
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}

        result = run_script(SCRIPT_PATH, 'compact', '--slug', SLUG, env_overrides=env)

        assert 'status: error' in result.stdout
        assert 'refused_closed' in result.stdout
