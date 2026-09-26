# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_orchestrator_ledger_fixtures import (
    _ledger,
    _row,
    json,
    pytest,
    root,
    threading,
)

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
