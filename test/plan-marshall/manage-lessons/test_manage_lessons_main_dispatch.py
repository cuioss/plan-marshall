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
from toon_parser import parse_toon

# Loaded once with a UNIQUE module name so coverage of manage-lessons.py is
# attributed to the real source file without colliding with the
# ``_lessons_helpers`` ``manage_lessons`` registration used by sibling suites.
_mod = load_script_module(
    'plan-marshall', 'manage-lessons', 'manage-lessons.py', 'manage_lessons_main_dispatch'
)


def _run_main(monkeypatch, capsys, argv: list[str]) -> tuple[int, dict]:
    """Invoke ``main()`` in-process with ``argv`` and return (exit_code, toon).

    ``main()`` reads ``sys.argv`` via ``parse_args_with_toon_errors`` and always
    terminates via ``sys.exit`` (``safe_main`` wrapper), so the call is made
    under ``pytest.raises(SystemExit)``. stdout is captured and parsed as TOON;
    an empty stdout (pure argparse-usage failure) yields an empty dict.
    """
    monkeypatch.setattr(sys, 'argv', ['manage-lessons.py', *argv])
    with pytest.raises(SystemExit) as exc:
        _mod.main()
    code = exc.value.code if isinstance(exc.value.code, int) else 1
    out = capsys.readouterr().out
    parsed = parse_toon(out) if out.strip() else {}
    return code, parsed


def _seed_lesson(
    base: Path,
    lesson_id: str,
    title: str = 'Seed Title',
    component: str = 'plan-marshall:phase-5-execute',
    category: str = 'bug',
    status: str = 'active',
    body: str = 'Seed body.\n',
) -> Path:
    """Write a canonically-shaped lesson markdown file under the corpus dir."""
    lessons_dir = base / 'lessons-learned'
    lessons_dir.mkdir(parents=True, exist_ok=True)
    path = lessons_dir / f'{lesson_id}.md'
    path.write_text(
        f'id={lesson_id}\n'
        f'component={component}\n'
        f'category={category}\n'
        f'status={status}\n'
        'created=2025-01-01\n\n'
        f'# {title}\n\n{body}',
        encoding='utf-8',
    )
    return path


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

    def test_main_list_stalled_empty_corpus_reports_zero(self, corpus, monkeypatch, capsys):
        code, toon = _run_main(monkeypatch, capsys, ['list-stalled'])
        assert code == 0
        assert toon['status'] == 'success'
        assert toon['stalled_count'] == 0


class TestMainMutationVerbs:
    """``update`` / ``set-title`` / ``set-body`` dispatch and mutate the file."""

    def test_main_update_component_reports_field_and_previous(self, corpus, monkeypatch, capsys):
        _seed_lesson(corpus, '2025-01-01-01-030', component='svc:old')
        code, toon = _run_main(
            monkeypatch, capsys,
            ['update', '--lesson-id', '2025-01-01-01-030', '--component', 'svc:new'],
        )
        assert code == 0
        assert toon['status'] == 'success'
        assert toon['field'] == 'component'
        assert toon['value'] == 'svc:new'
        assert toon['previous'] == 'svc:old'

    def test_main_update_category_validates_and_records_field(self, corpus, monkeypatch, capsys):
        _seed_lesson(corpus, '2025-01-01-01-031', category='bug')
        code, toon = _run_main(
            monkeypatch, capsys,
            ['update', '--lesson-id', '2025-01-01-01-031', '--category', 'improvement'],
        )
        assert code == 0
        assert toon['status'] == 'success'
        assert toon['field'] == 'category'
        assert toon['value'] == 'improvement'

    def test_main_set_title_rewrites_h1(self, corpus, monkeypatch, capsys):
        path = _seed_lesson(corpus, '2025-01-01-01-040', title='Old Heading')
        code, toon = _run_main(
            monkeypatch, capsys,
            ['set-title', '--lesson-id', '2025-01-01-01-040', '--title', 'New Heading'],
        )
        assert code == 0
        assert toon['status'] == 'success'
        assert toon['old_title'] == 'Old Heading'
        assert toon['new_title'] == 'New Heading'
        assert '# New Heading' in path.read_text(encoding='utf-8')

    def test_main_set_body_replaces_body_via_content_flag(self, corpus, monkeypatch, capsys):
        path = _seed_lesson(corpus, '2025-01-01-01-041', title='Body Host', body='original body.\n')
        code, toon = _run_main(
            monkeypatch, capsys,
            ['set-body', '--lesson-id', '2025-01-01-01-041', '--content', 'replacement body'],
        )
        assert code == 0
        assert toon['status'] == 'success'
        content = path.read_text(encoding='utf-8')
        assert 'replacement body' in content
        assert 'original body.' not in content
        # The H1 title is preserved by set-body.
        assert '# Body Host' in content


class TestMainLifecycleVerbs:
    """``remove`` / ``supersede`` / ``cleanup-superseded`` lifecycle dispatch."""

    def test_main_remove_force_deletes_and_tombstones(self, corpus, monkeypatch, capsys):
        path = _seed_lesson(corpus, '2025-01-01-01-050', title='Doomed')
        code, toon = _run_main(
            monkeypatch, capsys,
            ['remove', '--lesson-id', '2025-01-01-01-050', '--reason', 'dup', '--force'],
        )
        assert code == 0
        assert toon['status'] == 'success'
        assert toon['reason'] == 'dup'
        assert not path.exists()
        assert (corpus / 'lessons-learned' / '.tombstones' / '2025-01-01-01-050.json').exists()

    def test_main_supersede_redirects_source_to_canonical(self, corpus, monkeypatch, capsys):
        source = _seed_lesson(corpus, '2025-01-01-01-060', title='Source', body='src body.\n')
        _seed_lesson(corpus, '2025-01-02-01-001', title='Canonical', body='canon body.\n')
        code, toon = _run_main(
            monkeypatch, capsys,
            ['supersede', '--lesson-id', '2025-01-01-01-060',
             '--by', '2025-01-02-01-001', '--reason', 'merged'],
        )
        assert code == 0
        assert toon['status'] == 'success'
        assert toon['superseded_by'] == '2025-01-02-01-001'
        # Source body becomes a redirect stub.
        assert '[SUPERSEDED]' in source.read_text(encoding='utf-8')

    def test_main_supersede_self_rejected(self, corpus, monkeypatch, capsys):
        _seed_lesson(corpus, '2025-01-01-01-061', title='Selfie')
        code, toon = _run_main(
            monkeypatch, capsys,
            ['supersede', '--lesson-id', '2025-01-01-01-061',
             '--by', '2025-01-01-01-061', '--reason', 'self'],
        )
        assert code == 0
        assert toon['status'] == 'error'
        assert toon['error'] == 'self_supersede'

    def test_main_cleanup_superseded_dry_run_reports_candidate(self, corpus, monkeypatch, capsys):
        _seed_lesson(corpus, '2025-01-01-01-070', title='Stub', status='superseded')
        # A tombstone must exist for the stub to be eligible for cleanup.
        tomb_dir = corpus / 'lessons-learned' / '.tombstones'
        tomb_dir.mkdir(parents=True, exist_ok=True)
        (tomb_dir / '2025-01-01-01-070.json').write_text(
            '{"lesson_id": "2025-01-01-01-070", "status": "superseded"}', encoding='utf-8'
        )
        code, toon = _run_main(
            monkeypatch, capsys,
            ['cleanup-superseded', '--lesson-id', '2025-01-01-01-070', '--dry-run'],
        )
        assert code == 0
        assert toon['status'] == 'success'
        assert toon['dry_run'] is True
        # Dry-run must NOT delete the stub.
        assert (corpus / 'lessons-learned' / '2025-01-01-01-070.md').exists()


class TestMainRelocationVerbs:
    """``convert-to-plan`` and ``restore-from-plan`` round-trip via main()."""

    def test_main_convert_then_restore_round_trip(self, corpus, monkeypatch, capsys):
        _seed_lesson(corpus, '2025-01-01-01-080', title='Relocatable')
        code, toon = _run_main(
            monkeypatch, capsys,
            ['convert-to-plan', '--lesson-id', '2025-01-01-01-080', '--plan-id', 'reloc-plan'],
        )
        assert code == 0
        assert toon['status'] == 'success'
        relocated = corpus / 'plans' / 'reloc-plan' / 'lesson-2025-01-01-01-080.md'
        assert relocated.exists()
        # Source removed from the corpus by the move.
        assert not (corpus / 'lessons-learned' / '2025-01-01-01-080.md').exists()

        code2, toon2 = _run_main(
            monkeypatch, capsys, ['restore-from-plan', '--plan-id', 'reloc-plan']
        )
        assert code2 == 0
        assert toon2['status'] == 'success'
        assert toon2['restored_count'] == 1
        assert (corpus / 'lessons-learned' / '2025-01-01-01-080.md').exists()

    def test_main_restore_from_plan_no_lesson_is_idempotent(self, corpus, monkeypatch, capsys):
        code, toon = _run_main(
            monkeypatch, capsys, ['restore-from-plan', '--plan-id', 'empty-plan']
        )
        assert code == 0
        assert toon['status'] == 'success'
        assert toon['action'] == 'no_lesson_file'


class TestMainAggregateVerb:
    """``aggregate`` classifier dispatch through main()."""

    def test_main_aggregate_groups_cross_ref_pair(self, corpus, monkeypatch, capsys):
        _seed_lesson(
            corpus, '2025-03-01-01-001', title='Agg Primary',
            body='Refers to 2025-03-01-01-002 directly.\n',
        )
        _seed_lesson(corpus, '2025-03-01-01-002', title='Agg Partner', body='No back-ref.\n')
        code, toon = _run_main(monkeypatch, capsys, ['aggregate', '--top-n', '3'])
        assert code == 0
        assert toon['status'] == 'success'
        # ``top_n`` is a leading scalar the parser reads before the nested
        # groups[] table, so it is asserted without depending on nested-array
        # round-tripping of the multiline merged_body_preview field.
        assert toon['top_n'] == 3


class TestMainArgparseErrors:
    """argparse rejection paths exercised through main()."""

    def test_main_no_subcommand_exits_2(self, corpus, monkeypatch, capsys):
        # required=True subparsers → argparse error → exit code 2.
        code, _ = _run_main(monkeypatch, capsys, [])
        assert code == 2

    def test_main_unknown_subcommand_exits_2(self, corpus, monkeypatch, capsys):
        code, _ = _run_main(monkeypatch, capsys, ['frobnicate'])
        assert code == 2

    def test_main_invalid_category_choice_exits_2(self, corpus, monkeypatch, capsys):
        code, _ = _run_main(
            monkeypatch, capsys,
            ['add', '--component', 'svc:x', '--category', 'nonsense', '--title', 'T'],
        )
        assert code == 2

    def test_main_invalid_lesson_id_emits_toon_error_exit_0(self, corpus, monkeypatch, capsys):
        # ``--lesson-id`` is type-validated; a malformed value is converted to a
        # TOON error on stdout with exit 0 by parse_args_with_toon_errors.
        code, toon = _run_main(monkeypatch, capsys, ['get', '--lesson-id', 'BAD ID!'])
        assert code == 0
        assert toon['status'] == 'error'
