#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Per-signal matched controls for the ``cleanup restart-check`` verb.

Each signal read from the epic tree or the repository has a ``ready`` control,
a degraded control, and (where the signal admits one) BOTH a ``not_ready`` and
an ``indeterminate`` control, asserted to be distinct outcomes. An unreadable
observation must land on ``indeterminate``; landing it on ``not_ready`` is the
confident-signal defect this verb exists to remove.

The ``worktree`` signal observes the real repository through the module's single
git seam, so every test that needs a determinate worktree verdict substitutes a
stub for that seam. Leaving it live would make the suite's verdict depend on
whether the developer's tree happened to be clean.
"""

import pytest
from _ledger_fixtures import write_legacy_status
from _restart_check_fixtures import (
    CLEAN_SHA,
    INDETERMINATE,
    NOT_READY,
    READY,
    _epic_dir,
    _git_stub,
    _make_blocked_inbox,
    _make_finished_inbox,
    _make_inbox,
    _orch,
    _ready_epic,
    _row,
    _run,
    _signal_row,
    _status_doc,
    _write_broken_spec,
    _write_spec,
    _write_status,
    install_parity_stores,
)


@pytest.fixture(autouse=True)
def parity_stores(tmp_path, monkeypatch):
    """Point the parity arm of every test at fixture stores that are in parity."""
    return install_parity_stores(tmp_path, monkeypatch)


class TestPhaseSignal:
    def test_a_readable_phase_is_ready(self, plan_context, monkeypatch):
        _ready_epic(plan_context, monkeypatch)

        row = _signal_row(_run(), 'phase')

        assert row['verdict'] == READY
        assert 'orchestrating' in row['evidence']

    def test_an_unreadable_phase_is_indeterminate_not_not_ready(self, plan_context, monkeypatch):
        # Degraded control: no status.json at all, so the phase cannot be looked
        # at. Not looking is not the same as looking and finding a problem.
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        monkeypatch.setattr(_orch, '_git_read', _git_stub())

        row = _signal_row(_run(), 'phase')

        assert row['verdict'] == INDETERMINATE
        assert row['verdict'] != NOT_READY


class TestRunningPlansSignal:
    def test_a_quiet_queue_is_ready(self, plan_context, monkeypatch):
        _ready_epic(plan_context, monkeypatch)

        row = _signal_row(_run(), 'running_plans')

        assert row['verdict'] == READY
        assert row['population'] == 'queue rows: 2 row(s) scanned and 0 unreadable'

    def test_an_in_flight_plan_is_not_ready_and_is_named(self, plan_context, monkeypatch):
        # Positive control for the DEFINITE hazard arm — a restart mid-run loses
        # the run's context, which is an observed problem, not an unknown.
        _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02', status='running')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _write_spec(plan_context, 'PLAN-02-beta.md')
        _make_inbox(plan_context)
        monkeypatch.setattr(_orch, '_git_read', _git_stub())

        row = _signal_row(_run(), 'running_plans')

        assert row['verdict'] == NOT_READY
        assert 'PLAN-02' in row['evidence']
        assert row['population'] == 'queue rows: 2 row(s) scanned and 0 unreadable'

    def test_an_unreadable_queue_is_indeterminate_not_not_ready(self, plan_context, monkeypatch):
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        monkeypatch.setattr(_orch, '_git_read', _git_stub())

        row = _signal_row(_run(), 'running_plans')

        assert row['verdict'] == INDETERMINATE
        assert row['verdict'] != NOT_READY
        assert row['population'] == 'queue rows: not readable'

    def test_a_legacy_layout_ledger_is_indeterminate_and_names_the_layout(self, plan_context, monkeypatch):
        # The monolithic layout is refused rather than read: its plans[] names a
        # running row, yet the arm may not read it as one — nor as a quiet queue.
        write_legacy_status(_epic_dir(plan_context), _status_doc([_row('PLAN-01', status='running')]))
        monkeypatch.setattr(_orch, '_git_read', _git_stub())

        result = _run()

        row = _signal_row(result, 'running_plans')
        assert row['verdict'] == INDETERMINATE
        assert 'legacy_layout' in row['evidence']
        # The phase is a header fact and stays readable on the legacy layout.
        assert _signal_row(result, 'phase')['verdict'] == READY

    def test_an_unreadable_row_with_no_readable_running_row_is_indeterminate(self, plan_context, monkeypatch):
        # Matched pair with the quiet-queue control: the unread row might be the
        # running one, so the arm may not report a confident ``ready``.
        root = _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02')])
        (root / 'queue' / 'PLAN-02.json').write_text('<<<<<<< ours\n', encoding='utf-8')
        monkeypatch.setattr(_orch, '_git_read', _git_stub())

        row = _signal_row(_run(), 'running_plans')

        assert row['verdict'] == INDETERMINATE
        assert 'PLAN-02.json' in row['evidence']
        assert row['population'] == 'queue rows: 1 row(s) scanned and 1 unreadable'


class TestCorpusSignal:
    def test_a_reconciled_corpus_is_ready(self, plan_context, monkeypatch):
        _ready_epic(plan_context, monkeypatch)

        row = _signal_row(_run(), 'corpus_reconciliation')

        assert row['verdict'] == READY
        assert row['population'] == '2 queue row(s) and 2 spec file(s)'

    def test_an_orphan_row_is_not_ready(self, plan_context, monkeypatch):
        # Observed and understood: the queue and the specs genuinely disagree.
        _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _make_inbox(plan_context)
        monkeypatch.setattr(_orch, '_git_read', _git_stub())

        row = _signal_row(_run(), 'corpus_reconciliation')

        assert row['verdict'] == NOT_READY
        assert '1 row(s) without a spec' in row['evidence']

    def test_an_unreadable_spec_is_indeterminate_and_outranks_the_orphan(self, plan_context, monkeypatch):
        # The corpus could not be read in full, so the orphan finding computed
        # over the readable part is not a verdict this signal may assert.
        _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02'), _row('PLAN-03')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _write_broken_spec(plan_context, 'PLAN-02-broken.md')
        _make_inbox(plan_context)
        monkeypatch.setattr(_orch, '_git_read', _git_stub())

        row = _signal_row(_run(), 'corpus_reconciliation')

        assert row['verdict'] == INDETERMINATE
        assert row['verdict'] != NOT_READY
        assert '1 spec file(s) could not be read' in row['evidence']
        assert row['population'] == '3 queue row(s) and 2 spec file(s)'


class TestInboxSignal:
    def test_an_empty_present_inbox_is_ready(self, plan_context, monkeypatch):
        _ready_epic(plan_context, monkeypatch)

        row = _signal_row(_run(), 'inbox')

        assert row['verdict'] == READY
        assert row['population'] == 'inbox/: 0 live of 0 total and 0 closed and 0 invalid'

    def test_a_queued_message_is_not_ready(self, plan_context, monkeypatch):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _make_inbox(plan_context, queued=2)
        monkeypatch.setattr(_orch, '_git_read', _git_stub())

        row = _signal_row(_run(), 'inbox')

        assert row['verdict'] == NOT_READY
        assert '2 message(s) still queued' in row['evidence']

    def test_a_queued_only_stream_end_marker_is_ready_with_finished_evidence(self, plan_context, monkeypatch):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _make_finished_inbox(plan_context)
        monkeypatch.setattr(_orch, '_git_read', _git_stub())

        row = _signal_row(_run(), 'inbox')

        assert row['verdict'] == READY
        assert 'FINISHED' in row['evidence']
        assert row['population'] == 'inbox/: 0 live of 1 total and 1 closed and 0 invalid'

    def test_a_malformed_only_queue_is_not_ready_with_blocked_evidence(self, plan_context, monkeypatch):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _make_blocked_inbox(plan_context, malformed=2)
        monkeypatch.setattr(_orch, '_git_read', _git_stub())

        row = _signal_row(_run(), 'inbox')

        assert row['verdict'] == NOT_READY
        assert 'BLOCKED' in row['evidence']
        assert row['population'] == 'inbox/: 0 live of 2 total and 0 closed and 2 invalid'

    def test_an_absent_inbox_is_indeterminate_never_a_confident_zero(self, plan_context, monkeypatch):
        # The two zeros are told apart by the payload: an absent inbox/ is
        # *could not look*, and reporting it as "0 queued — ready" would be the
        # confident zero this whole seam refuses to emit.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        monkeypatch.setattr(_orch, '_git_read', _git_stub())

        row = _signal_row(_run(), 'inbox')

        assert row['verdict'] == INDETERMINATE
        assert row['verdict'] != READY
        assert row['population'] == 'inbox/: missing'

    def test_an_unreadable_archive_with_no_live_is_indeterminate_never_empty(self, plan_context, monkeypatch):
        # An unreadable archive leaves closure unestablished: with no live and
        # no invalid message the queue reads EMPTY only when the archive was
        # fully checked, so a partial scan must yield indeterminate.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _make_inbox(plan_context, queued=0)
        monkeypatch.setattr(_orch, '_git_read', _git_stub())
        original_list = _orch.cmd_inbox_list

        def _partial_archive(args):
            result = original_list(args)
            assert result['live_count'] == 0, 'the arrangement queued a live message'
            assert result['invalid_count'] == 0, 'the arrangement queued an invalid message'
            result['archive_readable'] = False
            result['closed_senders'] = []
            return result

        monkeypatch.setattr(_orch, 'cmd_inbox_list', _partial_archive)

        row = _signal_row(_run(), 'inbox')

        assert row['verdict'] == INDETERMINATE
        assert row['verdict'] != READY
        assert 'closure is unobservable' in row['evidence']


class TestWorktreeSignal:
    def test_a_clean_worktree_is_ready_and_names_its_head(self, plan_context, monkeypatch):
        _ready_epic(plan_context, monkeypatch)

        row = _signal_row(_run(), 'worktree')

        assert row['verdict'] == READY
        assert CLEAN_SHA in row['evidence']

    def test_an_uncommitted_path_is_not_ready(self, plan_context, monkeypatch):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _make_inbox(plan_context)
        monkeypatch.setattr(_orch, '_git_read', _git_stub(porcelain=' M a/b.py\n?? c/d.py\n'))

        row = _signal_row(_run(), 'worktree')

        assert row['verdict'] == NOT_READY
        assert '2 uncommitted path(s)' in row['evidence']

    def test_an_unreadable_head_is_indeterminate_not_not_ready(self, plan_context, monkeypatch):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _make_inbox(plan_context)
        monkeypatch.setattr(_orch, '_git_read', _git_stub(unreadable='head-sha'))

        row = _signal_row(_run(), 'worktree')

        assert row['verdict'] == INDETERMINATE
        assert row['verdict'] != NOT_READY
        assert row['population'] == 'git: not readable'

    def test_an_unreadable_status_is_indeterminate_even_when_head_resolves(self, plan_context, monkeypatch):
        # Half an observation is not an observation: knowing the sha without
        # knowing whether the tree is clean cannot support a ready verdict.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _make_inbox(plan_context)
        monkeypatch.setattr(_orch, '_git_read', _git_stub(unreadable='worktree-status'))

        row = _signal_row(_run(), 'worktree')

        assert row['verdict'] == INDETERMINATE
