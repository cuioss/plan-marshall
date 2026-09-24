#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the generated ``queue-view.md`` — its renderer and the view verbs.

START HERE and the Ordered Queue are rendered by ONE pure function,
``render_queue_view``, into the generated, git-tracked ``queue-view.md``, written
by ONE writer that ``regenerate-view`` (and ``compact``) call. ``resume-summary``
is a read that writes nothing and reports whether the committed view is current.

- **Determinism** — two renders of the same ledger state are byte-identical, and
  the text carries no timestamp.
- **Live rows only** — a row at a terminal status is absent from the Ordered
  Queue BY CONSTRUCTION; this replaces the retired ``no_terminal_in_live_queue``
  compact invariant, and a live row beside it is the positive control.
- **``regenerate-view`` writes** — it writes ``queue-view.md`` and returns
  ``written: false`` on a second run with nothing changed.
- **Conflict-marker overwrite** — a view holding git conflict markers is replaced
  by a clean render, because the verb never reads the view as an input.
- **Refusal on an unreadable source** — a row file holding conflict markers makes
  the verb return the unreadable state, name the file, and leave the view
  untouched, so a genuine source conflict is never papered over.
- **Read-only summary** — ``resume-summary`` writes no file, and reports
  ``view_current: true`` after a regeneration and ``false`` after a queue change
  or when the file is absent.

Everything runs under ``PLAN_BASE_DIR`` isolation (``plan_context``).
"""

import argparse
import copy
import re
from pathlib import Path
from typing import Any

from _ledger_fixtures import ledger, write_ledger

from conftest import get_script_path, load_script_module, parse_ns, run_script

_ORCH_BUNDLE = 'plan-marshall'
_ORCH_SKILL = 'plan-orchestrator'
_ORCH_SCRIPT = 'orchestrator.py'

SCRIPT_PATH = get_script_path(_ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT)

_orch = load_script_module(_ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT, 'orchestrator_queue_view_script')

render_queue_view = _orch.render_queue_view
cmd_regenerate_view = _orch.cmd_regenerate_view
cmd_resume_summary = _orch.cmd_resume_summary
cmd_queue = _orch.cmd_queue
LIVE_PLAN_STATUSES = _orch.LIVE_PLAN_STATUSES
TERMINAL_PLAN_STATUSES = _orch.TERMINAL_PLAN_STATUSES

SLUG = 'view-epic'
FIXED_TIMESTAMP = '2020-01-01T00:00:00Z'

#: Any ISO-8601-looking instant. The rendered view must carry none: a timestamp
#: would make two renders of the same ledger state differ, which is exactly the
#: false merge conflict the deterministic render exists to prevent.
_TIMESTAMP_RE = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}')


def _variant(base: argparse.Namespace, **overrides: Any) -> argparse.Namespace:
    derived = copy.copy(base)
    for field, value in overrides.items():
        setattr(derived, field, value)
    return derived


_REGENERATE_ARGS = parse_ns(_ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT, 'regenerate-view', '--slug', SLUG, register=False)
_RESUME_ARGS = parse_ns(_ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT, 'resume-summary', '--slug', SLUG, register=False)
_QUEUE_ARGS = parse_ns(_ORCH_BUNDLE, _ORCH_SKILL, _ORCH_SCRIPT, 'queue', '--slug', SLUG, register=False)


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


def _seed(plan_context, rows: list[dict], anchor: str = 'resume at PLAN-01') -> Path:
    root = _epic_dir(plan_context)
    write_ledger(
        root,
        {
            'kind': 'orchestrator',
            'title': 'View Epic',
            'phase': 'orchestrating',
            'workstreams': ['WS-01'],
            'plans': rows,
            'resume_anchor': anchor,
            'metadata': {},
            'created': FIXED_TIMESTAMP,
        },
    )
    return root


def _view(root: Path) -> Path:
    return root / 'queue-view.md'


def _render(root: Path) -> str:
    """A fresh render of the ledger at ``root`` through the production path."""
    view = ledger.assemble_view(root).document
    rendered: str = render_queue_view(view, _orch._resolve_row_surfaces(view, root), slug=SLUG)
    return rendered


def _files(root: Path) -> dict[str, bytes]:
    return {str(path.relative_to(root)): path.read_bytes() for path in sorted(root.rglob('*')) if path.is_file()}


# =============================================================================
# The renderer
# =============================================================================


class TestRendererDeterminism:
    def test_two_renders_of_the_same_state_are_byte_identical(self, plan_context):
        root = _seed(plan_context, [_row('PLAN-01'), _row('PLAN-02', status='running')])

        assert _render(root) == _render(root)

    def test_the_render_carries_no_timestamp(self, plan_context):
        root = _seed(plan_context, [_row('PLAN-01')])

        rendered = _render(root)

        assert not _TIMESTAMP_RE.search(rendered), 'the rendered view carries a timestamp'

    def test_the_render_carries_the_regenerate_on_conflict_header(self, plan_context):
        root = _seed(plan_context, [_row('PLAN-01')])

        first_line = _render(root).split('\n', 1)[0]

        assert first_line.startswith('<!-- GENERATED FILE')
        assert f'orchestrator regenerate-view --slug {SLUG}' in first_line
        assert 'git add' in first_line

    def test_the_render_orders_rows_by_seq_then_id(self):
        # Pure: a view handed over in the wrong order still renders in queue order.
        view = {
            'phase': 'orchestrating',
            'resume_anchor': '',
            'plans': [{**_row('PLAN-01'), 'seq': 2}, {**_row('PLAN-02'), 'seq': 1}],
        }

        rendered = render_queue_view(view, {}, slug=SLUG)

        assert rendered.index('| 1 | PLAN-02 |') < rendered.index('| 2 | PLAN-01 |')


class TestLiveRowsOnly:
    """A terminal row is absent from the Ordered Queue by construction."""

    def test_the_status_populations_are_non_empty(self):
        assert LIVE_PLAN_STATUSES, 'LIVE_PLAN_STATUSES is empty (population 0)'
        assert TERMINAL_PLAN_STATUSES, 'TERMINAL_PLAN_STATUSES is empty (population 0)'

    def test_every_terminal_row_is_excluded_and_every_live_row_rendered(self):
        rows = [
            {**_row(f'PLAN-{index:02d}', status=status), 'seq': index}
            for index, status in enumerate((*LIVE_PLAN_STATUSES, *TERMINAL_PLAN_STATUSES), start=1)
        ]
        view = {'phase': 'orchestrating', 'resume_anchor': '', 'plans': rows}

        queue = render_queue_view(view, {}, slug=SLUG).split('## Ordered Queue', 1)[1]

        rendered_statuses = {cells[4] for cells in _table_rows(queue)}
        assert rendered_statuses == set(LIVE_PLAN_STATUSES)
        assert not rendered_statuses & set(TERMINAL_PLAN_STATUSES)

    def test_an_all_terminal_queue_renders_the_empty_marker(self):
        view = {'phase': 'orchestrating', 'resume_anchor': '', 'plans': [{**_row('PLAN-01', 'shipped'), 'seq': 1}]}

        assert '| — | (empty) | — | — | — |' in render_queue_view(view, {}, slug=SLUG)


def _table_rows(text: str) -> list[list[str]]:
    """The Ordered Queue data rows (first cell a position integer), split into cells."""
    rows: list[list[str]] = []
    for line in text.split('\n'):
        cells = [cell.strip() for cell in line.split('|')]
        if len(cells) >= 7 and cells[1].isdigit():
            rows.append(cells)
    return rows


# =============================================================================
# regenerate-view
# =============================================================================


class TestRegenerateView:
    def test_writes_the_view_and_reports_written(self, plan_context):
        root = _seed(plan_context, [_row('PLAN-01')])

        result = cmd_regenerate_view(_REGENERATE_ARGS)

        assert result['status'] == 'success'
        assert result['operation'] == 'regenerate-view'
        assert result['written'] is True
        assert _view(root).read_text(encoding='utf-8') == _render(root)

    def test_a_second_run_with_nothing_changed_writes_nothing(self, plan_context):
        root = _seed(plan_context, [_row('PLAN-01')])
        cmd_regenerate_view(_REGENERATE_ARGS)
        before = _view(root).read_bytes()

        second = cmd_regenerate_view(_REGENERATE_ARGS)

        assert second['written'] is False
        assert _view(root).read_bytes() == before

    def test_a_view_holding_conflict_markers_is_replaced_by_a_clean_render(self, plan_context):
        root = _seed(plan_context, [_row('PLAN-01'), _row('PLAN-02')])
        conflicted = '<<<<<<< ours\n| 1 | PLAN-01 |\n=======\n| 1 | PLAN-02 |\n>>>>>>> theirs\n'
        _view(root).write_text(conflicted, encoding='utf-8')

        result = cmd_regenerate_view(_REGENERATE_ARGS)

        assert result['written'] is True
        text = _view(root).read_text(encoding='utf-8')
        assert '<<<<<<<' not in text and '>>>>>>>' not in text
        assert text == _render(root)

    def test_an_unreadable_row_file_is_named_and_the_view_left_untouched(self, plan_context):
        root = _seed(plan_context, [_row('PLAN-01'), _row('PLAN-02')])
        cmd_regenerate_view(_REGENERATE_ARGS)
        view_before = _view(root).read_bytes()
        (root / 'queue' / 'PLAN-02.json').write_text(
            '<<<<<<< ours\n{"id": "PLAN-02"}\n=======\n{"id": "PLAN-02"}\n>>>>>>> theirs\n', encoding='utf-8'
        )

        result = cmd_regenerate_view(_REGENERATE_ARGS)

        assert result['status'] == 'error'
        assert result['error'] == 'row_unreadable'
        assert result['unreadable_rows'] == ['PLAN-02.json']
        assert 'PLAN-02.json' in result['message']
        assert _view(root).read_bytes() == view_before

    def test_an_unreadable_header_refuses_without_writing(self, plan_context):
        root = _seed(plan_context, [_row('PLAN-01')])
        (root / 'status.json').write_text('{"kind": ', encoding='utf-8')

        result = cmd_regenerate_view(_REGENERATE_ARGS)

        assert result['status'] == 'error'
        assert result['error'] == 'ledger_unreadable'
        assert not _view(root).exists()

    def test_an_unsafe_slug_and_an_absent_tree_are_refused(self, plan_context):
        unsafe = cmd_regenerate_view(_variant(_REGENERATE_ARGS, slug='../evil'))
        absent = cmd_regenerate_view(_variant(_REGENERATE_ARGS, slug='ghost-epic'))

        assert unsafe['error'] == 'invalid_slug'
        assert absent['error'] == 'not_found'

    def test_regenerates_through_the_cli(self, plan_context):
        root = _seed(plan_context, [_row('PLAN-01')])
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}

        result = run_script(SCRIPT_PATH, 'regenerate-view', '--slug', SLUG, env_overrides=env)

        assert result.returncode == 0
        assert 'written: true' in result.stdout
        assert _view(root).is_file()


# =============================================================================
# resume-summary — a read that writes nothing
# =============================================================================


class TestResumeSummaryIsReadOnly:
    def test_resume_summary_writes_no_file(self, plan_context):
        root = _seed(plan_context, [_row('PLAN-01')])
        before = _files(root)

        result = cmd_resume_summary(_RESUME_ARGS)

        assert result['status'] == 'success'
        assert _files(root) == before

    def test_view_current_is_false_when_the_view_is_absent(self, plan_context):
        _seed(plan_context, [_row('PLAN-01')])

        assert cmd_resume_summary(_RESUME_ARGS)['view_current'] is False

    def test_view_current_is_true_after_a_regeneration(self, plan_context):
        _seed(plan_context, [_row('PLAN-01')])
        cmd_regenerate_view(_REGENERATE_ARGS)

        assert cmd_resume_summary(_RESUME_ARGS)['view_current'] is True

    def test_view_current_turns_false_after_a_queue_change(self, plan_context):
        _seed(plan_context, [_row('PLAN-01')])
        cmd_regenerate_view(_REGENERATE_ARGS)

        cmd_queue(_variant(_QUEUE_ARGS, transition='PLAN-01', status='running'))

        assert cmd_resume_summary(_RESUME_ARGS)['view_current'] is False

    def test_the_summary_and_queue_blocks_match_the_rendered_view(self, plan_context):
        # One renderer: the blocks resume-summary returns are the blocks the
        # committed view carries (the view omits only the live inbox line).
        root = _seed(plan_context, [_row('PLAN-01'), _row('PLAN-02', status='running')])
        cmd_regenerate_view(_REGENERATE_ARGS)

        result = cmd_resume_summary(_RESUME_ARGS)

        view = _view(root).read_text(encoding='utf-8')
        assert result['ordered_queue'] in view
        for line in result['summary'].split('\n'):
            if not line.startswith('**Inbox (derived)**'):
                assert line in view
