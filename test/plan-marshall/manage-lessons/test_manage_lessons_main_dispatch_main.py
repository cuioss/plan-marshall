#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""In-process ``main()`` dispatch tests for manage-lessons.py.

The existing per-subcommand suites drive the ``cmd_*`` handlers directly and
pin the CLI plumbing via ``run_script`` subprocesses. Subprocess execution
does NOT contribute to in-process coverage, so the ~210-line argparse
``main()`` body (subparser wiring, flag declarations, ``func`` dispatch,
``output_toon`` emission, and the ``parse_args_with_toon_errors`` integration)
was structurally uncovered.

These tests close that gap by invoking the real ``main()`` IN PROCESS with a
patched ``sys.argv`` so coverage counts the argparse construction and every
``set_defaults(func=...)`` dispatch edge. ``main()`` is wrapped by
``file_ops.safe_main`` — it calls ``sys.exit(rc)`` rather than returning — so
every invocation is asserted inside ``pytest.raises(SystemExit)``. The emitted
TOON (captured via ``capsys``) is parsed and asserted on real return fields,
not merely on exit code.

Lesson-ids use the canonical ``YYYY-MM-DD-HH-NNN`` shape (hyphenated, so
``parse_toon`` never int-coerces them) and assertions target round-tripped
titles / status fields rather than coerced numeric values.
"""


import sys
from pathlib import Path
import pytest
from conftest import load_script_module
from _manage_lessons_main_dispatch_fixtures import _mod, _run_main, _seed_lesson


@pytest.fixture
def corpus(tmp_path, monkeypatch):
    """Point the main-anchored corpus at ``tmp_path`` and create the dir.

    ``resolve_main_anchored_path`` honours ``PLAN_BASE_DIR`` first, so setting
    it to ``tmp_path`` lands the lessons corpus, plans dir, tombstones, and log
    files inside the per-test sandbox (overriding the autouse sandbox default).
    """
    monkeypatch.setenv('PLAN_BASE_DIR', str(tmp_path))
    (tmp_path / 'lessons-learned').mkdir(parents=True, exist_ok=True)
    return tmp_path


def test_restore_from_plan_help_names_every_restore_action(monkeypatch, capsys):
    """The published help must name every ``RESTORE_ACTIONS`` member.

    The subcommand help is where a CLI caller learns the closed ``action``
    vocabulary, and nothing else reads the help string and the frozenset
    together — so a value added to (or renamed in) ``RESTORE_ACTIONS`` without a
    matching help edit leaves the published contract stale and silently wrong.

    Population-derived: the expected members are read from the module rather
    than re-listed here, so the guard cannot pass by agreeing with a stale copy
    of the vocabulary.

    Scope, stated plainly: argparse renders a subcommand's ``help=`` string only
    in the PARENT parser's listing, so the assertion ranges over the whole
    rendered help rather than the ``restore-from-plan`` entry alone. Two members
    (``restore_incomplete``, ``plan_dir_unresolved``) are named nowhere else, so
    a dropped restore help string still fails here — but a member that another
    subcommand's help happens to mention would not be caught by this guard.
    """
    lessons_query = load_script_module(
        'plan-marshall', 'manage-lessons', '_lessons_query.py', '_dispatch_lessons_query'
    )
    actions = lessons_query.RESTORE_ACTIONS
    assert actions, 'RESTORE_ACTIONS is empty — the check below would be vacuous.'

    monkeypatch.setattr(sys, 'argv', ['manage-lessons.py', '--help'])
    with pytest.raises(SystemExit) as exc:
        _mod.main()
    assert exc.value.code == 0
    help_text = capsys.readouterr().out

    missing = sorted(action for action in actions if action not in help_text)
    assert not missing, (
        f'The manage-lessons help does not name {missing} from RESTORE_ACTIONS '
        f'({sorted(actions)}) — the restore-from-plan help string and the closed '
        f'vocabulary have drifted apart.'
    )


class TestMainCreationVerbs:
    """``add`` / ``from-error`` dispatch through main() and emit a fresh path."""

    def test_main_add_emits_success_with_absolute_path(self, corpus, monkeypatch, capsys):
        code, toon = _run_main(
            monkeypatch,
            capsys,
            ['add', '--component', 'svc:x', '--category', 'bug', '--title', 'Mainline Add'],
        )
        assert code == 0
        assert toon['status'] == 'success'
        assert toon['component'] == 'svc:x'
        assert toon['category'] == 'bug'
        # The returned path is absolute and the file was actually written.
        created = Path(toon['path'])
        assert created.is_absolute()
        assert created.exists()
        assert '# Mainline Add' in created.read_text(encoding='utf-8')

    def test_main_add_with_bundle_persists_bundle_field(self, corpus, monkeypatch, capsys):
        code, toon = _run_main(
            monkeypatch,
            capsys,
            [
                'add', '--component', 'svc:x', '--category', 'improvement',
                '--title', 'With Bundle', '--bundle', 'pm-dev-java',
            ],
        )
        assert code == 0
        assert toon['status'] == 'success'
        assert 'bundle=pm-dev-java' in Path(toon['path']).read_text(encoding='utf-8')

    def test_main_from_error_creates_from_error_context(self, corpus, monkeypatch, capsys):
        code, toon = _run_main(
            monkeypatch,
            capsys,
            ['from-error', '--context', '{"component": "build", "error": "boom", "solution": "fix"}'],
        )
        assert code == 0
        assert toon['status'] == 'success'
        assert toon['created_from'] == 'error_context'

    def test_main_from_error_invalid_json_reports_error(self, corpus, monkeypatch, capsys):
        code, toon = _run_main(monkeypatch, capsys, ['from-error', '--context', 'not-json'])
        assert code == 0
        assert toon['status'] == 'error'
        assert toon['error'] == 'invalid_json'


class TestMainReadVerbs:
    """``get`` (+ ``read`` alias) and ``list`` dispatch and surface lesson data."""

    def test_main_get_returns_seeded_lesson_fields(self, corpus, monkeypatch, capsys):
        _seed_lesson(corpus, '2025-01-01-01-001', title='Readable Lesson', component='svc:y')
        code, toon = _run_main(monkeypatch, capsys, ['get', '--lesson-id', '2025-01-01-01-001'])
        assert code == 0
        assert toon['status'] == 'success'
        assert toon['title'] == 'Readable Lesson'
        assert toon['component'] == 'svc:y'

    def test_main_read_alias_dispatches_to_get(self, corpus, monkeypatch, capsys):
        _seed_lesson(corpus, '2025-01-01-01-002', title='Alias Target')
        code, toon = _run_main(monkeypatch, capsys, ['read', '--lesson-id', '2025-01-01-01-002'])
        assert code == 0
        assert toon['status'] == 'success'
        assert toon['title'] == 'Alias Target'

    def test_main_get_missing_lesson_reports_not_found(self, corpus, monkeypatch, capsys):
        code, toon = _run_main(monkeypatch, capsys, ['get', '--lesson-id', '2099-01-01-01-001'])
        assert code == 0
        assert toon['status'] == 'error'
        assert toon['error'] == 'not_found'

    def test_main_list_counts_active_lessons(self, corpus, monkeypatch, capsys):
        _seed_lesson(corpus, '2025-01-01-01-010', title='Active One')
        _seed_lesson(corpus, '2025-01-01-01-011', title='Superseded One', status='superseded')
        # Default status filter is "active" → only one of the two is listed.
        code, toon = _run_main(monkeypatch, capsys, ['list'])
        assert code == 0
        assert toon['status'] == 'success'
        assert toon['total'] == 2
        assert toon['filtered'] == 1

    def test_main_list_all_status_includes_superseded(self, corpus, monkeypatch, capsys):
        _seed_lesson(corpus, '2025-01-01-01-020', title='Active Two')
        _seed_lesson(corpus, '2025-01-01-01-021', title='Superseded Two', status='superseded')
        code, toon = _run_main(monkeypatch, capsys, ['list', '--status', 'all', '--full'])
        assert code == 0
        assert toon['status'] == 'success'
        assert toon['filtered'] == 2

    def test_main_list_stalled_absent_plans_root_reports_could_not_look(
        self, corpus, monkeypatch, capsys
    ):
        """Through main(), an absent plans root reports WHICH kind of zero it is.

        The corpus fixture seeds no ``plans/`` directory, so the scan could not
        look. The verb stays non-faulting (a sweep is never aborted by it), but
        the payload must carry ``plans_root_state: missing`` — a bare
        ``stalled_count: 0`` here is indistinguishable from a clean corpus.
        """
        code, toon = _run_main(monkeypatch, capsys, ['list-stalled'])
        assert code == 0
        assert toon['status'] == 'success'
        assert toon['plans_root_state'] == 'missing'
        assert toon['stalled_count'] == 0
        assert toon['scanned_plan_count'] == 0
