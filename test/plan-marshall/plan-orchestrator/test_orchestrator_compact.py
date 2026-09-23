#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``compact`` verb of the plan-orchestrator script.

The ledger-compaction stage verifies the ledger invariants and then regenerates
the generated, git-tracked ``queue-view.md`` through the SAME writer
``regenerate-view`` uses. It makes NO ``epic.md`` write: ``epic.md`` is
hand-written narrative only. The module is organised around the properties that
make the stage safe to run unattended:

- **The view is regenerated from the ledger** — a queue change reaches
  ``queue-view.md``, and a stale or conflicted view is overwritten.
- **``epic.md`` is never written** — a retraction, an annotation, and every
  hand-authored section are byte-identical after a pass because nothing here
  writes that file at all.
- **Idempotent** — a second run over an unchanged ledger reports
  ``view_written: false`` and writes nothing.
- **Refuses a closed epic** — that tree is the frozen audit record; compaction
  is a live-epic operation only. Also refuses a monolithic-layout ledger and an
  unreadable row file, writing nothing.
- **Reports every abstention** — every ``##`` section of ``epic.md`` is named as
  preserved verbatim, so a silent compaction cannot pass for a lossy one.
- **Invariants bite** — the queue<->spec reconciliation is bidirectional and
  every relocation pointer resolves. The retired ``no_terminal_in_live_queue``
  invariant is gone with the pasted table it guarded; terminal-row exclusion is
  pinned on the renderer in ``test_orchestrator_queue_view.py``.

Everything runs against a SCAFFOLDED FIXTURE EPIC under ``PLAN_BASE_DIR``
isolation — never a live epic tree.
"""

import argparse
import copy
from pathlib import Path
from typing import Any

from _ledger_fixtures import write_ledger, write_legacy_status

from conftest import get_script_path, load_script_module, parse_ns, run_script

#: The orchestrator script's address, as module-level string constants so the
#: ``parse_ns`` call below stays statically resolvable.
_ORCH_BUNDLE = 'plan-marshall'
_ORCH_SKILL = 'plan-orchestrator'
_ORCH_SCRIPT = 'orchestrator.py'

SCRIPT_PATH = get_script_path(_ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT)

_orch = load_script_module(_ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT, 'orchestrator_compact_script')

cmd_compact = _orch.cmd_compact
GENERATED_BLOCKS = _orch.GENERATED_BLOCKS

SLUG = 'fixture-compact-epic'
FIXED_TIMESTAMP = '2020-01-01T00:00:00Z'

#: A settled narrative statement that must survive a pass byte-identical. It is
#: exactly the anti-rework record the stage exists to protect.
RETRACTION = '- 2020-01-01 — RETRACTED: the spec-corruption claim was withdrawn; do not re-flag it.'

#: A hand annotation and a per-row queue caveat — narrative that must survive.
START_ANNOTATION = '- PLAN-01 — a hand annotation the generator does not produce.'
QUEUE_ANNOTATION = '- PLAN-01 — sequencing caveat the generator cannot derive.'
VISION_TEXT = 'A fixture epic exercising the compact stage.'
OPEN_DEFECT = '- a known defect not yet owned by a plan — source: observation'
WATCH = '- a mid-flight watch — re-check at the next landing'


# =============================================================================
# Parser-derived argument namespaces
# =============================================================================


def _variant(base: argparse.Namespace, **overrides: Any) -> argparse.Namespace:
    """Derive a namespace from a hoisted parser-derived base."""
    derived = copy.copy(base)
    for field, value in overrides.items():
        setattr(derived, field, value)
    return derived


_COMPACT_ARGS = parse_ns(
    _ORCH_BUNDLE,
    _ORCH_SKILL,
    _ORCH_SCRIPT,
    'compact',
    '--slug',
    SLUG,
    register=False,
)


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


def _ledger_doc(rows: list, phase: str = 'orchestrating', resume_anchor: str = 'await nothing') -> dict:
    return {
        'kind': 'orchestrator',
        'title': 'Fixture Compact Epic',
        'phase': phase,
        'workstreams': ['WS-01'],
        'plans': rows,
        'resume_anchor': resume_anchor,
        'metadata': {},
        'created': FIXED_TIMESTAMP,
    }


def _write_status(plan_context, rows: list, phase: str = 'orchestrating', resume_anchor: str = 'await nothing') -> Path:
    """Seed the per-concern ledger through the production conversion; return the epic root."""
    root = _epic_dir(plan_context)
    write_ledger(root, _ledger_doc(rows, phase, resume_anchor))
    return root


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


def _epic_md(*, decisions: str = RETRACTION, pointer_line: str = '') -> str:
    """A narrative-only ``epic.md`` — the per-concern layout carries no generated block."""
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
                '### Annotations',
                '',
                START_ANNOTATION,
                '',
                '## Queue annotations',
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
    """Materialize a live epic: a per-concern queue, one spec, and an epic.md."""
    rows = rows if rows is not None else [_row('PLAN-01')]
    _write_status(plan_context, rows)
    _write_spec(plan_context, 'PLAN-01-alpha.md', surface=['scripts/a.py'])
    return _write_epic(plan_context, **epic_kwargs)


def _run() -> dict:
    result: dict = cmd_compact(_COMPACT_ARGS)
    return result


def _view_text(plan_context) -> str:
    return (_epic_dir(plan_context) / 'queue-view.md').read_text(encoding='utf-8')


def _invariant(result: dict, name: str) -> dict:
    rows: list[dict] = [row for row in result['invariants'] if row['invariant'] == name]
    assert len(rows) == 1, f'expected exactly one {name!r} invariant, got {len(rows)}'
    return rows[0]


# =============================================================================
# Report shape and the happy path
# =============================================================================


class TestCompactShape:
    def test_reports_operation_relocation_target_and_view(self, plan_context):
        _live_epic(plan_context)

        result = _run()

        assert result['status'] == 'success'
        assert result['operation'] == 'compact'
        assert result['relocation_target'] == 'settled.md'
        assert result['view'] == 'queue-view.md'
        assert result['view_written'] is True

    def test_carries_the_two_invariants_each_with_verdict_evidence_population(self, plan_context):
        _live_epic(plan_context)

        result = _run()

        assert {row['invariant'] for row in result['invariants']} == {
            'queue_spec_bidirectional',
            'relocated_pointer_reachable',
        }
        for row in result['invariants']:
            assert set(row) == {'invariant', 'verdict', 'evidence', 'population'}
            assert row['verdict'] in ('ok', 'violated', 'indeterminate')
            assert row['evidence'].strip()
            assert row['population'].strip()

    def test_the_retired_terminal_row_invariant_is_not_reported(self, plan_context):
        _live_epic(plan_context)

        result = _run()

        assert 'no_terminal_in_live_queue' not in {row['invariant'] for row in result['invariants']}

    def test_abstained_names_every_epic_md_section_as_preserved(self, plan_context):
        _live_epic(plan_context)

        result = _run()

        abstained = {row['section'] for row in result['abstained']}
        assert {'Vision', 'START HERE', 'Queue annotations', 'Decisions', 'Open Defects', 'Watches'} <= abstained
        assert result['abstained_count'] == len(result['abstained'])
        assert all(row['treatment'] == 'preserved_verbatim' for row in result['abstained'])


# =============================================================================
# The view is regenerated; epic.md is never written
# =============================================================================


class TestViewRegeneration:
    def test_a_queue_change_reaches_the_view(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01', status='parked')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface=['scripts/a.py'])
        _write_epic(plan_context)

        _run()

        assert '| 1 | PLAN-01 | WS-01 | parked |' in _view_text(plan_context)

    def test_the_surface_column_is_derived_from_the_spec(self, plan_context):
        # The declared entries are ROOTED — their first segment is a real
        # top-level repository entry — so the single reader claims them.
        declared = ['test/alpha/a.py', 'test/alpha/b.py']
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface=declared)
        _write_epic(plan_context)

        _run()

        view = _view_text(plan_context)
        for path in declared:
            assert path in view

    def test_a_row_without_a_spec_renders_a_named_marker_not_a_blank(self, plan_context):
        _write_status(plan_context, [_row('PLAN-09')])
        _write_epic(plan_context)

        _run()

        assert '(spec missing)' in _view_text(plan_context)

    def test_a_conflicted_view_is_overwritten_by_a_clean_render(self, plan_context):
        _live_epic(plan_context)
        view_path = _epic_dir(plan_context) / 'queue-view.md'
        view_path.write_text('<<<<<<< ours\nA\n=======\nB\n>>>>>>> theirs\n', encoding='utf-8')

        result = _run()

        assert result['view_written'] is True
        assert '<<<<<<<' not in _view_text(plan_context)


class TestEpicMdIsNeverWritten:
    def test_epic_md_is_byte_identical_after_a_pass(self, plan_context):
        epic_path = _live_epic(plan_context)
        before = epic_path.read_bytes()

        _run()

        assert epic_path.read_bytes() == before

    def test_a_retraction_and_every_narrative_fragment_survive(self, plan_context):
        _live_epic(plan_context)

        _run()

        text = (_epic_dir(plan_context) / 'epic.md').read_text(encoding='utf-8')
        for fragment in (RETRACTION, VISION_TEXT, START_ANNOTATION, QUEUE_ANNOTATION, OPEN_DEFECT, WATCH):
            assert text.count(fragment) == 1


# =============================================================================
# Idempotence
# =============================================================================


class TestIdempotence:
    def test_a_second_run_writes_nothing(self, plan_context):
        _live_epic(plan_context)
        first = _run()
        view_after_first = (_epic_dir(plan_context) / 'queue-view.md').read_bytes()

        second = _run()

        assert first['view_written'] is True
        assert second['view_written'] is False
        assert (_epic_dir(plan_context) / 'queue-view.md').read_bytes() == view_after_first


# =============================================================================
# Refusals
# =============================================================================


class TestRefusals:
    def test_refuses_a_closed_epic_and_writes_no_view(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')], phase='closed')
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        epic_path = _write_epic(plan_context)
        before = epic_path.read_bytes()

        result = _run()

        assert result['status'] == 'error'
        assert result['error'] == 'refused_closed'
        assert result['phase'] == 'closed'
        assert epic_path.read_bytes() == before
        assert not (_epic_dir(plan_context) / 'queue-view.md').exists()

    def test_refuses_a_legacy_layout_ledger_without_writing(self, plan_context):
        root = _epic_dir(plan_context)
        write_legacy_status(root, {**_ledger_doc([_row('PLAN-01')]), 'updated': FIXED_TIMESTAMP})
        _write_epic(plan_context)

        result = _run()

        assert result['status'] == 'error'
        assert result['error'] == 'legacy_layout'
        assert not (root / 'queue-view.md').exists()
        assert not (root / 'queue').exists()

    def test_refuses_an_unreadable_row_file_without_writing_the_view(self, plan_context):
        root = _write_status(plan_context, [_row('PLAN-01')])
        _write_epic(plan_context)
        (root / 'queue' / 'PLAN-01.json').write_text('<<<<<<< ours\n', encoding='utf-8')

        result = _run()

        assert result['status'] == 'error'
        assert result['error'] == 'row_unreadable'
        assert result['unreadable_rows'] == ['PLAN-01.json']
        assert not (root / 'queue-view.md').exists()

    def test_rejects_an_invalid_slug(self, plan_context):
        result = cmd_compact(_variant(_COMPACT_ARGS, slug='../evil'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_slug'

    def test_errors_when_the_epic_has_no_store_tree(self, plan_context):
        result = cmd_compact(_variant(_COMPACT_ARGS, slug='absent-compact-epic'))

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
        assert 'view_written: true' in result.stdout

    def test_refuses_a_closed_epic_through_cli(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')], phase='closed')
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _write_epic(plan_context)
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}

        result = run_script(SCRIPT_PATH, 'compact', '--slug', SLUG, env_overrides=env)

        assert 'status: error' in result.stdout
        assert 'refused_closed' in result.stdout


# =============================================================================
# _marker_indices returns two distinct not-fully-delimited shapes
# =============================================================================


class TestMarkerIndicesContract:
    """Pin the two shapes ``_marker_indices`` returns.

    ``migrate-layout`` locates the legacy GENERATED blocks through it: a begin
    with no following end returns ``(begin_idx, -1)`` — which the migration
    reports as ``incomplete`` and leaves untouched — and an end that precedes
    the begin is never a candidate, because the end is only searched for AFTER
    the begin index.
    """

    def test_an_absent_begin_marker_returns_the_minus_one_pair(self):
        name = GENERATED_BLOCKS[0]
        lines = ['# epic', '', 'no markers here', '']

        assert _orch._marker_indices(lines, name) == (-1, -1)

    def test_a_begin_with_no_following_end_returns_the_begin_index_and_minus_one(self):
        name = GENERATED_BLOCKS[0]
        lines = ['# epic', _orch._begin_marker(name), 'body', 'still body']

        begin_idx, end_idx = _orch._marker_indices(lines, name)

        assert begin_idx == 1
        assert end_idx == -1

    def test_an_end_before_the_begin_is_never_a_candidate(self):
        name = GENERATED_BLOCKS[0]
        lines = [_orch._end_marker(name), _orch._begin_marker(name), 'body']

        assert _orch._marker_indices(lines, name) == (1, -1)

    def test_a_fully_delimited_block_returns_both_indices(self):
        name = GENERATED_BLOCKS[0]
        lines = ['# epic', _orch._begin_marker(name), 'body', _orch._end_marker(name), 'tail']

        assert _orch._marker_indices(lines, name) == (1, 3)

    def test_a_marker_quoted_mid_sentence_is_not_matched(self):
        name = GENERATED_BLOCKS[0]
        lines = ['# epic', f'see {_orch._begin_marker(name)} for details', 'body']

        assert _orch._marker_indices(lines, name) == (-1, -1)

    def test_an_incomplete_pair_is_left_untouched_by_the_block_strip(self):
        # The migration's use of the not-fully-delimited shape: a BEGIN with no
        # END is reported and never guessed at, so no hand-written line is cut.
        name = GENERATED_BLOCKS[0]
        text = '\n'.join(['# epic', _orch._begin_marker(name), 'hand-written tail', ''])

        stripped, outcomes = _orch._strip_generated_blocks(text)

        assert stripped == text
        assert {'block': name, 'outcome': 'incomplete'} in outcomes
