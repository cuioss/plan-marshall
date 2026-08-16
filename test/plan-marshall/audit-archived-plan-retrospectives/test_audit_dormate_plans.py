#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``dormate_plans`` batch dormation and its ``plan_id`` path-traversal guard —
multi-id and ``--dormate-all`` success, inert-without-confirmed, all-or-nothing
refuse-on-clash, silent dedup, and refusal of ``../``, absolute, and embedded
path-separator ids before any move.
"""

from pathlib import Path

from _audit_fixtures import audit


def _archived_plan_dir(repo_root: Path, plan_id: str) -> Path:
    """Create and return an archived-plan source dir with a marker file."""
    plan_dir = repo_root / '.plan' / 'local' / 'archived-plans' / plan_id
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'status.json').write_text('{}', encoding='utf-8')
    return plan_dir


def _dormated_plan_dir(repo_root: Path, plan_id: str) -> Path:
    """Path to the dormation destination for a single plan id."""
    return repo_root / '.plan' / 'temp' / 'dormated-plans' / plan_id


class TestDormatePlanIdHardening:
    """The path-traversal guard fires identically under the batch function:
    each hostile id is driven through ``dormate_plans`` as a one-element list.
    """

    def test_parent_traversal_plan_id_refused(self, tmp_path: Path):
        result = audit.dormate_plans(tmp_path, ['../escape'], confirmed=True)

        # refused on grammar before any move
        assert result['status'] == 'refused'
        assert 'invalid plan_id' in result['reason']
        assert result['moved'] == []

    def test_absolute_path_plan_id_refused(self, tmp_path: Path):
        result = audit.dormate_plans(tmp_path, ['/etc/passwd'], confirmed=True)

        assert result['status'] == 'refused'
        assert 'invalid plan_id' in result['reason']
        assert result['moved'] == []

    def test_embedded_separator_plan_id_refused(self, tmp_path: Path):
        result = audit.dormate_plans(tmp_path, ['a/b'], confirmed=True)

        assert result['status'] == 'refused'
        assert 'invalid plan_id' in result['reason']
        assert result['moved'] == []

    def test_well_formed_plan_id_passes_grammar_then_source_not_found(self, tmp_path: Path):
        # a canonical kebab/date plan_id with no archived dir on disk
        plan_id = '2026-05-29-some-valid-plan'

        result = audit.dormate_plans(tmp_path, [plan_id], confirmed=True)

        # passes grammar (NOT the grammar refusal); fails source-not-found
        assert result['status'] == 'error'
        assert 'source not found' in result['reason']
        assert 'invalid plan_id' not in result['reason']
        assert result['moved'] == []

    def test_inert_without_confirmed(self, tmp_path: Path):
        result = audit.dormate_plans(tmp_path, ['../escape'], confirmed=False)

        # the inert path fires before grammar validation
        assert result['status'] == 'refused'
        assert 'requires --confirmed' in result['reason']
        assert result['moved'] == []


class TestDormatePlans:
    """Batch-specific behaviours of ``dormate_plans`` / ``dormate_all_plans``."""

    def test_multi_id_success_relocates_every_plan(self, tmp_path: Path):
        # two valid archived plans on disk
        _archived_plan_dir(tmp_path, '2026-06-01-plan-a')
        _archived_plan_dir(tmp_path, '2026-06-02-plan-b')

        result = audit.dormate_plans(
            tmp_path, ['2026-06-01-plan-a', '2026-06-02-plan-b'], confirmed=True
        )

        # both moved, sources gone, destinations present
        assert result['status'] == 'success'
        assert result['moved'] == ['2026-06-01-plan-a', '2026-06-02-plan-b']
        archived = tmp_path / '.plan' / 'local' / 'archived-plans'
        assert not (archived / '2026-06-01-plan-a').exists()
        assert not (archived / '2026-06-02-plan-b').exists()
        assert _dormated_plan_dir(tmp_path, '2026-06-01-plan-a').is_dir()
        assert _dormated_plan_dir(tmp_path, '2026-06-02-plan-b').is_dir()

    def test_dormate_all_relocates_every_archived_plan(self, tmp_path: Path):
        # three archived plans; dormate_all_plans enumerates them all
        _archived_plan_dir(tmp_path, '2026-06-01-plan-a')
        _archived_plan_dir(tmp_path, '2026-06-02-plan-b')
        _archived_plan_dir(tmp_path, '2026-06-03-plan-c')

        result = audit.dormate_all_plans(tmp_path, confirmed=True)

        # all three relocated (sorted) via the dormate_plans delegate
        assert result['status'] == 'success'
        assert result['moved'] == [
            '2026-06-01-plan-a',
            '2026-06-02-plan-b',
            '2026-06-03-plan-c',
        ]
        archived = tmp_path / '.plan' / 'local' / 'archived-plans'
        assert list(archived.iterdir()) == []
        assert _dormated_plan_dir(tmp_path, '2026-06-01-plan-a').is_dir()
        assert _dormated_plan_dir(tmp_path, '2026-06-02-plan-b').is_dir()
        assert _dormated_plan_dir(tmp_path, '2026-06-03-plan-c').is_dir()

    def test_dormate_all_absent_archive_dir_is_noop_success(self, tmp_path: Path):
        # no archived-plans directory exists at all
        result = audit.dormate_all_plans(tmp_path, confirmed=True)

        # empty no-op success
        assert result['status'] == 'success'
        assert result['moved'] == []

    def test_inert_without_confirmed_leaves_sources_untouched(self, tmp_path: Path):
        # a valid archived plan that must NOT move
        _archived_plan_dir(tmp_path, '2026-06-01-plan-a')

        result = audit.dormate_plans(
            tmp_path, ['2026-06-01-plan-a'], confirmed=False
        )

        # refused, nothing moved, source still on disk
        assert result['status'] == 'refused'
        assert result['moved'] == []
        archived = tmp_path / '.plan' / 'local' / 'archived-plans'
        assert (archived / '2026-06-01-plan-a').is_dir()
        assert not _dormated_plan_dir(tmp_path, '2026-06-01-plan-a').exists()

    def test_all_or_nothing_refuse_on_clash_moves_nothing(self, tmp_path: Path):
        # two valid sources, but a pre-existing destination for the
        # SECOND plan. The all-or-nothing pre-check must refuse the WHOLE batch
        # before relocating the first (clean) plan.
        _archived_plan_dir(tmp_path, '2026-06-01-plan-a')
        _archived_plan_dir(tmp_path, '2026-06-02-plan-b')
        clash = _dormated_plan_dir(tmp_path, '2026-06-02-plan-b')
        clash.mkdir(parents=True, exist_ok=True)

        result = audit.dormate_plans(
            tmp_path, ['2026-06-01-plan-a', '2026-06-02-plan-b'], confirmed=True
        )

        # error, nothing moved, BOTH sources still present
        assert result['status'] == 'error'
        assert result['moved'] == []
        assert 'already exists' in result['reason']
        archived = tmp_path / '.plan' / 'local' / 'archived-plans'
        assert (archived / '2026-06-01-plan-a').is_dir()
        assert (archived / '2026-06-02-plan-b').is_dir()
        # The first (clean) plan was NOT relocated despite being clash-free.
        assert not _dormated_plan_dir(tmp_path, '2026-06-01-plan-a').exists()

    def test_silent_dedup_collapses_duplicate_ids(self, tmp_path: Path):
        # one archived plan, supplied id listed three times
        _archived_plan_dir(tmp_path, '2026-06-01-plan-a')

        # duplicates must collapse silently (no double-move error)
        result = audit.dormate_plans(
            tmp_path,
            ['2026-06-01-plan-a', '2026-06-01-plan-a', '2026-06-01-plan-a'],
            confirmed=True,
        )

        # moved exactly once, no error
        assert result['status'] == 'success'
        assert result['moved'] == ['2026-06-01-plan-a']
        assert _dormated_plan_dir(tmp_path, '2026-06-01-plan-a').is_dir()
