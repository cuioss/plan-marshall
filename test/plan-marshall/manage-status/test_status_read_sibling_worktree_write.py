# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_status_read_sibling_worktree_fixtures import (
    PLAN_ID,
    Path,
    _add_linked_worktree,
    _ns,
    _stub_locator,
    main_base,
    pytest,
    status_core,
    status_query,
)

# =============================================================================
# ⛔ The write verbs keep the strict gate
# =============================================================================


class TestWriteVerbsKeepTheStrictGate:
    def test_metadata_set_refuses_a_sibling_plan_and_writes_no_local_document(
        self, main_base: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Removing the read-only gate reddens this: require_status would hand the
        # sibling's document to the --set branch, which commits through the
        # LOCALLY resolved path and would materialize status.json in the wrong tree.
        worktree = _add_linked_worktree(tmp_path / 'main', main_base, PLAN_ID)
        sibling_status = worktree / '.plan' / 'local' / 'plans' / PLAN_ID / 'status.json'
        before = sibling_status.read_text(encoding='utf-8')
        seen = _stub_locator(monkeypatch, status_core._CheckoutLookup(True, worktree))

        result = status_query.cmd_metadata(
            _ns('metadata', '--plan-id', PLAN_ID, '--set', '--field', 'change_type', '--value', 'bug_fix')
        )

        assert result is None, 'the write verb resolved a sibling-worktree plan'
        assert seen == [], 'the write path consulted the sibling-worktree locator'
        assert not (main_base / 'plans' / PLAN_ID / 'status.json').exists()
        assert sibling_status.read_text(encoding='utf-8') == before

    def test_set_phase_refuses_a_sibling_plan_and_writes_no_local_document(
        self, main_base: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        worktree = _add_linked_worktree(tmp_path / 'main', main_base, PLAN_ID)
        seen = _stub_locator(monkeypatch, status_core._CheckoutLookup(True, worktree))

        result = status_query.cmd_set_phase(_ns('set-phase', '--plan-id', PLAN_ID, '--phase', '5-execute'))

        assert result is None
        assert seen == []
        assert not (main_base / 'plans' / PLAN_ID / 'status.json').exists()

    def test_get_worktree_path_keeps_the_strict_gate(
        self, main_base: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # This read verb is deliberately excluded: locate-plan-checkout calls back
        # into it, so opting it in would make the consult call itself.
        worktree = _add_linked_worktree(tmp_path / 'main', main_base, PLAN_ID)
        seen = _stub_locator(monkeypatch, status_core._CheckoutLookup(True, worktree))

        result = status_query.cmd_get_worktree_path(_ns('get-worktree-path', '--plan-id', PLAN_ID))

        assert result is None
        assert seen == []
