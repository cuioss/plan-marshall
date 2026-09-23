#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for ``_orchestrator_ledger`` — the per-concern epic ledger layout.

Covers every module entry point: path resolution (including the refusal of a
plan id outside the grammar), the assembled view round-trip ordered by
``(seq, id)``, the atomic duplicate-id and duplicate-slug refusals of
``create_row``, per-row mutate isolation, legacy-layout detection, migration
fidelity (``seq`` follows array order), and the absent-queue versus
unreadable-row distinction.
"""

import json
import threading

import pytest

from conftest import load_script_module

_ledger = load_script_module('plan-marshall', 'manage-status', '_orchestrator_ledger.py', '_orchestrator_ledger_unit')


def _header(**overrides) -> dict:
    header = {
        'kind': 'orchestrator',
        'title': 'Unit Epic',
        'phase': 'orchestrating',
        'workstreams': ['WS-01'],
        'metadata': {'parallelization_scope': '2'},
        'created': '2020-01-01T00:00:00Z',
    }
    header.update(overrides)
    return header


def _row(plan_id: str, slug: str, **extra) -> dict:
    row = {
        'id': plan_id,
        'slug': slug,
        'workstream': 'WS-01',
        'status': 'staged',
        'plan_marshall_plan_id': '',
        'pr': '',
        'landing': '',
    }
    row.update(extra)
    return row


@pytest.fixture
def root(tmp_path):
    epic = tmp_path / 'orchestrator' / 'unit-epic'
    epic.mkdir(parents=True)
    return epic


# =============================================================================
# Path resolution
# =============================================================================


class TestPathResolution:
    def test_should_resolve_every_per_concern_path_under_the_root(self, root):
        assert _ledger.header_path(root) == root / 'status.json'
        assert _ledger.anchor_path(root) == root / 'resume_anchor.md'
        assert _ledger.queue_dir(root) == root / 'queue'
        assert _ledger.view_path(root) == root / 'queue-view.md'
        assert _ledger.row_path(root, 'PLAN-01') == root / 'queue' / 'PLAN-01.json'
        assert _ledger.row_path(root, 'PLAN-TRUTH-143') == root / 'queue' / 'PLAN-TRUTH-143.json'

    @pytest.mark.parametrize(
        'plan_id',
        ['../evil', 'PLAN-01/../x', 'PLAN-025B', 'PLAN-01\n', '', 'plan-01', 'PLAN-'],
    )
    def test_should_refuse_a_plan_id_outside_the_grammar(self, root, plan_id):
        assert _ledger.is_valid_row_id(plan_id) is False
        with pytest.raises(_ledger.LedgerPathError):
            _ledger.row_path(root, plan_id)

    def test_should_refuse_a_non_string_plan_id(self, root):
        assert _ledger.is_valid_row_id(None) is False
        assert _ledger.is_valid_row_id(7) is False


# =============================================================================
# The assembled view
# =============================================================================


class TestAssembleView:
    def test_should_round_trip_header_anchor_and_rows(self, root):
        rows = (_row('PLAN-01', 'first', seq=1), _row('PLAN-02', 'second', seq=2))
        _ledger.write_layout(root, _header(), 'await PR #9 CI', rows)

        view = _ledger.assemble_view(root)

        assert view.state == _ledger.LEDGER_OK
        assert view.queue_state == _ledger.QUEUE_PRESENT
        assert view.unreadable_rows == ()
        assert list(view.document) == list(_ledger.VIEW_FIELDS)
        assert view.document['resume_anchor'] == 'await PR #9 CI'
        assert view.document['metadata'] == {'parallelization_scope': '2'}
        assert view.document['plans'] == [dict(row) for row in rows]
        assert 'updated' not in view.document

    def test_should_order_rows_by_seq_then_id(self, root):
        rows = (
            _row('PLAN-03', 'third', seq=2),
            _row('PLAN-02', 'second', seq=1),
            _row('PLAN-01', 'first', seq=2),
        )
        _ledger.write_layout(root, _header(), '', rows)

        view = _ledger.assemble_view(root)

        assert [row['id'] for row in view.document['plans']] == ['PLAN-02', 'PLAN-01', 'PLAN-03']

    def test_should_read_an_absent_queue_as_a_measured_empty_queue(self, root):
        _ledger.create_ledger(root, 'Fresh', '2020-01-01T00:00:00Z')

        view = _ledger.assemble_view(root)

        assert view.state == _ledger.LEDGER_OK
        assert view.queue_state == _ledger.QUEUE_ABSENT
        assert view.document['plans'] == []
        assert view.document['resume_anchor'] == ''

    def test_should_report_an_unreadable_row_as_its_own_state(self, root):
        _ledger.write_layout(root, _header(), '', (_row('PLAN-01', 'first', seq=1),))
        (_ledger.queue_dir(root) / 'PLAN-02.json').write_text('<<<<<<< HEAD\n{}\n', encoding='utf-8')
        (_ledger.queue_dir(root) / 'PLAN-03.json').write_text('[1]', encoding='utf-8')

        view = _ledger.assemble_view(root)

        assert view.state == _ledger.LEDGER_OK
        assert [row['id'] for row in view.document['plans']] == ['PLAN-01']
        assert [row['file'] for row in view.unreadable_rows] == ['PLAN-02.json', 'PLAN-03.json']
        assert all(row['reason'] for row in view.unreadable_rows)

    def test_should_report_an_absent_header(self, root):
        view = _ledger.assemble_view(root)

        assert view.state == _ledger.LEDGER_ABSENT
        assert view.document == {}

    def test_should_report_an_unreadable_header_apart_from_an_absent_one(self, root):
        _ledger.header_path(root).write_text('not json', encoding='utf-8')

        view = _ledger.assemble_view(root)

        assert view.state == _ledger.LEDGER_UNREADABLE
        assert view.document == {}

    def test_should_ignore_non_row_files_in_the_queue(self, root):
        _ledger.write_layout(root, _header(), '', (_row('PLAN-01', 'first', seq=1),))
        (_ledger.queue_dir(root) / 'notes.txt').write_text('scratch', encoding='utf-8')

        view = _ledger.assemble_view(root)

        assert [row['id'] for row in view.document['plans']] == ['PLAN-01']
        assert view.unreadable_rows == ()


# =============================================================================
# create_row — atomic staging
# =============================================================================


class TestCreateRow:
    def test_should_allocate_seq_as_local_max_plus_one(self, root):
        _ledger.create_ledger(root, 'Epic', '2020-01-01T00:00:00Z')

        first = _ledger.create_row(root, _row('PLAN-02', 'second'))
        second = _ledger.create_row(root, _row('PLAN-01', 'first'))

        assert first['row']['seq'] == 1
        assert second['row']['seq'] == 2
        assert [row['id'] for row in _ledger.assemble_view(root).document['plans']] == ['PLAN-02', 'PLAN-01']
        on_disk = json.loads(_ledger.row_path(root, 'PLAN-02').read_text(encoding='utf-8'))
        assert list(on_disk) == list(_ledger.ROW_FIELDS)

    def test_should_refuse_a_duplicate_id_and_leave_the_existing_row_intact(self, root):
        _ledger.create_row(root, _row('PLAN-01', 'first'))
        path = _ledger.row_path(root, 'PLAN-01')
        before = path.read_bytes()

        outcome = _ledger.create_row(root, _row('PLAN-01', 'other-slug'))

        assert set(outcome) == {'duplicate'}
        assert outcome['duplicate']['slug'] == 'first'
        assert path.read_bytes() == before

    def test_should_refuse_a_duplicate_slug_and_write_nothing(self, root):
        _ledger.create_row(root, _row('PLAN-01', 'shared'))

        outcome = _ledger.create_row(root, _row('PLAN-02', 'shared'))

        assert set(outcome) == {'duplicate_slug'}
        assert outcome['duplicate_slug']['id'] == 'PLAN-01'
        assert not _ledger.row_path(root, 'PLAN-02').exists()

    def test_should_refuse_the_epic_slug_before_any_write(self, root):
        outcome = _ledger.create_row(root, _row('PLAN-01', 'unit-epic'), epic_slug='unit-epic')

        assert outcome == {'epic_slug': 'unit-epic'}
        assert not _ledger.queue_dir(root).exists()

    def test_should_refuse_an_id_outside_the_grammar(self, root):
        outcome = _ledger.create_row(root, _row('../escape', 'x'))

        assert outcome == {'invalid_id': '../escape'}
        assert not _ledger.queue_dir(root).exists()

    def test_should_release_the_queue_guard_after_every_outcome(self, root):
        _ledger.create_row(root, _row('PLAN-01', 'first'))
        _ledger.create_row(root, _row('PLAN-01', 'first'))

        assert not (root / _ledger.QUEUE_GUARD_FILE).exists()
        assert sorted(path.name for path in _ledger.queue_dir(root).iterdir()) == ['PLAN-01.json']

    @pytest.mark.xdist_group(name='manage_locks_contention')
    def test_should_keep_both_rows_when_two_sessions_stage_concurrently(self, root):
        barrier = threading.Barrier(2, timeout=30)
        outcomes: dict[str, dict] = {}
        errors: list[Exception] = []

        def _stage(plan_id: str, slug: str) -> None:
            try:
                barrier.wait()
                outcomes[plan_id] = _ledger.create_row(root, _row(plan_id, slug))
            except Exception as exc:  # broad on purpose: surfaced by the assertion below
                errors.append(exc)

        threads = [
            threading.Thread(target=_stage, args=('PLAN-01', 'first')),
            threading.Thread(target=_stage, args=('PLAN-02', 'second')),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)

        assert not any(thread.is_alive() for thread in threads)
        assert not errors
        assert set(outcomes) == {'PLAN-01', 'PLAN-02'}
        assert all('row' in outcome for outcome in outcomes.values())
        assert sorted(outcome['row']['seq'] for outcome in outcomes.values()) == [1, 2]
        listed = sorted(path.name for path in _ledger.queue_dir(root).iterdir())
        assert listed == ['PLAN-01.json', 'PLAN-02.json']


# =============================================================================
# mutate_row — per-row isolation
# =============================================================================


class TestMutateRow:
    def test_should_mutate_one_row_and_leave_every_other_row_byte_identical(self, root):
        _ledger.write_layout(root, _header(), '', (_row('PLAN-01', 'first', seq=1), _row('PLAN-02', 'second', seq=2)))
        other = _ledger.row_path(root, 'PLAN-02')
        other_before = other.read_bytes()
        header_before = _ledger.header_path(root).read_bytes()

        def _transition(row: dict) -> str:
            previous = str(row['status'])
            row['status'] = 'running'
            return previous

        outcome = _ledger.mutate_row(root, 'PLAN-01', _transition)

        assert outcome == {'result': 'staged'}
        assert json.loads(_ledger.row_path(root, 'PLAN-01').read_text(encoding='utf-8'))['status'] == 'running'
        assert other.read_bytes() == other_before
        assert _ledger.header_path(root).read_bytes() == header_before

    def test_should_report_available_plans_for_an_absent_row(self, root):
        _ledger.write_layout(root, _header(), '', (_row('PLAN-02', 'second', seq=1),))

        outcome = _ledger.mutate_row(root, 'PLAN-09', lambda row: None)

        assert outcome == {'available_plans': ['PLAN-02']}
        assert not _ledger.row_path(root, 'PLAN-09').exists()

    def test_should_refuse_an_unreadable_row_and_leave_it_untouched(self, root):
        _ledger.write_layout(root, _header(), '', ())
        path = _ledger.row_path(root, 'PLAN-01')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('<<<<<<< HEAD\n', encoding='utf-8')

        outcome = _ledger.mutate_row(root, 'PLAN-01', lambda row: row.update(status='running'))

        assert set(outcome) == {'unreadable'}
        assert path.read_text(encoding='utf-8') == '<<<<<<< HEAD\n'

    def test_should_refuse_an_id_outside_the_grammar(self, root):
        assert _ledger.mutate_row(root, '../x', lambda row: None) == {'invalid_id': '../x'}


# =============================================================================
# Header and anchor writes
# =============================================================================


class TestHeaderAndAnchorWrites:
    def test_should_create_a_header_without_queue_anchor_or_updated_keys(self, root):
        header = _ledger.create_ledger(root, 'Fresh', '2020-01-01T00:00:00Z')

        on_disk = json.loads(_ledger.header_path(root).read_text(encoding='utf-8'))
        assert on_disk == header
        assert list(on_disk) == list(_ledger.HEADER_FIELDS)
        assert _ledger.anchor_path(root).read_text(encoding='utf-8') == '\n'

    def test_should_write_a_header_field_without_stamping_updated(self, root):
        _ledger.create_ledger(root, 'Fresh', '2020-01-01T00:00:00Z')

        outcome = _ledger.write_header_field(root, 'phase', 'closed')

        assert outcome == {'previous': 'init'}
        on_disk = json.loads(_ledger.header_path(root).read_text(encoding='utf-8'))
        assert on_disk['phase'] == 'closed'
        assert 'updated' not in on_disk

    def test_should_set_a_metadata_entry(self, root):
        _ledger.create_ledger(root, 'Fresh', '2020-01-01T00:00:00Z')

        first = _ledger.set_metadata_field(root, 'owner', 'a')
        second = _ledger.set_metadata_field(root, 'owner', 'b')

        assert first == {'previous': None}
        assert second == {'previous': 'a'}
        assert json.loads(_ledger.header_path(root).read_text(encoding='utf-8'))['metadata'] == {'owner': 'b'}

    def test_should_report_legacy_from_inside_the_header_critical_section(self, root):
        legacy = {'kind': 'orchestrator', 'phase': 'init', 'plans': [], 'resume_anchor': ''}
        _ledger.header_path(root).write_text(json.dumps(legacy, indent=2), encoding='utf-8')

        assert _ledger.write_header_field(root, 'phase', 'closed') == {'legacy': True}
        assert _ledger.set_metadata_field(root, 'owner', 'x') == {'legacy': True}
        assert json.loads(_ledger.header_path(root).read_text(encoding='utf-8')) == legacy

    def test_should_round_trip_the_anchor_verbatim(self, root):
        _ledger.write_anchor(root, 'line one\nline two')

        text, _detail = _ledger.read_anchor(root)

        assert text == 'line one\nline two'

    def test_should_read_an_absent_anchor_as_empty(self, root):
        text, detail = _ledger.read_anchor(root)

        assert text == ''
        assert 'does not exist' in detail


# =============================================================================
# The monolithic layout
# =============================================================================


class TestLegacyLayout:
    @pytest.mark.parametrize('key', ['plans', 'resume_anchor'])
    def test_should_detect_either_legacy_key(self, key):
        assert _ledger.detect_legacy({'kind': 'orchestrator', key: []}) is True

    def test_should_not_detect_a_per_concern_header(self):
        assert _ledger.detect_legacy(_header()) is False

    def test_should_refuse_to_assemble_a_legacy_ledger(self, root):
        _ledger.header_path(root).write_text(
            json.dumps({'kind': 'orchestrator', 'plans': [], 'resume_anchor': 'x'}), encoding='utf-8'
        )

        view = _ledger.assemble_view(root)

        assert view.state == _ledger.LEDGER_LEGACY
        assert view.document == {}

    def test_should_name_migrate_layout_as_the_remedy(self):
        error = _ledger.legacy_layout_error('my-epic')

        assert error['error'] == _ledger.LEGACY_LAYOUT_ERROR
        assert error['remedy'] == 'orchestrator migrate-layout --slug my-epic'
        assert error['remedy'] in error['message']


class TestMigrateDocument:
    def _legacy(self) -> dict:
        return {
            'kind': 'orchestrator',
            'title': 'Legacy',
            'phase': 'orchestrating',
            'workstreams': ['WS-01', 'WS-02'],
            'plans': [
                _row('PLAN-03', 'third', status='shipped', pr='#12', landing='landings/PLAN-03.md'),
                _row('PLAN-01', 'first', status='running'),
                _row('PLAN-02', 'second'),
            ],
            'resume_anchor': 'await PR #12 CI',
            'metadata': {'parallelization_scope': '2'},
            'created': '2020-01-01T00:00:00Z',
            'updated': '2021-01-01T00:00:00Z',
        }

    def test_should_preserve_every_value_and_drop_updated(self):
        legacy = self._legacy()

        migrated = _ledger.migrate_document(legacy)

        assert migrated.header == {key: legacy[key] for key in _ledger.HEADER_FIELDS}
        assert 'updated' not in migrated.header
        assert migrated.anchor == 'await PR #12 CI'
        for original, converted in zip(legacy['plans'], migrated.rows, strict=True):
            assert {key: value for key, value in converted.items() if key != 'seq'} == original
        assert migrated.rejected_rows == ()

    def test_should_take_seq_from_array_order(self):
        migrated = _ledger.migrate_document(self._legacy())

        assert [(row['id'], row['seq']) for row in migrated.rows] == [('PLAN-03', 1), ('PLAN-01', 2), ('PLAN-02', 3)]

    def test_should_reproduce_the_legacy_order_after_materialising(self, root):
        legacy = self._legacy()
        migrated = _ledger.migrate_document(legacy)

        _ledger.write_layout(root, migrated.header, migrated.anchor, migrated.rows)
        view = _ledger.assemble_view(root)

        assert view.state == _ledger.LEDGER_OK
        assert [row['id'] for row in view.document['plans']] == ['PLAN-03', 'PLAN-01', 'PLAN-02']
        assert view.document['resume_anchor'] == legacy['resume_anchor']
        assert view.document['workstreams'] == legacy['workstreams']

    def test_should_report_rows_it_cannot_convert_instead_of_dropping_them(self):
        legacy = self._legacy()
        legacy['plans'].append('not-a-row')
        legacy['plans'].append(_row('PLAN-025B', 'lettered'))

        migrated = _ledger.migrate_document(legacy)

        assert len(migrated.rows) == 3
        assert [(row['index'], row['id']) for row in migrated.rejected_rows] == [('3', ''), ('4', 'PLAN-025B')]
        assert all(row['reason'] for row in migrated.rejected_rows)
