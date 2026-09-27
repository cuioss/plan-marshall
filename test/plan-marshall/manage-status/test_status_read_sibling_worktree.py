# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests carved from test_status_read_sibling_worktree.py: sibling."""

from _manage_status_status_read_sibling_worktree_fixtures import (
    PLAN_ID,
    Path,
    _add_linked_worktree,
    _assert_worktree_root_honours_override,
    _ns,
    _status_document,
    _stub_locator,
    json,
    main_base,
    pytest,
    status_core,
    status_query,
)

# =============================================================================
# The read verbs resolve a plan that lives in a sibling worktree
# =============================================================================


class TestSiblingWorktreeRead:
    def test_read_from_another_tree_returns_the_worktree_resident_plan(
        self, main_base: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A real linked worktree holds the plan; the resolver is anchored at the
        # MAIN checkout, so this read runs from a different tree than the one the
        # plan lives in — the exact shape that used to answer file_not_found.
        worktree = _add_linked_worktree(tmp_path / 'main', main_base, PLAN_ID)
        _assert_worktree_root_honours_override(main_base)
        assert not (main_base / 'plans' / PLAN_ID / 'status.json').exists()
        _stub_locator(monkeypatch, status_core._CheckoutLookup(True, worktree))

        result = status_query.cmd_read(_ns('read', '--plan-id', PLAN_ID))

        assert result is not None, 'the read refused a plan that is alive in a sibling worktree'
        assert result['status'] == 'success'
        assert result['plan']['current_phase'] == '5-execute'
        assert result['plan']['title'] == 'A plan that moved into its worktree'

    def test_read_names_the_checkout_that_answered(
        self, main_base: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The provenance is what lets a caller tell a local read from a foreign one.
        worktree = _add_linked_worktree(tmp_path / 'main', main_base, PLAN_ID)
        _stub_locator(monkeypatch, status_core._CheckoutLookup(True, worktree))

        result = status_query.cmd_read(_ns('read', '--plan-id', PLAN_ID))

        assert result is not None
        assert result['resolved_from'] == 'worktree'
        assert result['resolved_checkout'] == str(worktree)

    def test_a_locally_resolved_read_is_labelled_current_and_names_no_checkout(
        self, main_base: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Provenance rides EVERY read, so the local case is positively labelled
        # rather than being the absence of a field.
        plan_dir = main_base / 'plans' / PLAN_ID
        plan_dir.mkdir(parents=True)
        (plan_dir / 'status.json').write_text(json.dumps(_status_document('2-refine')), encoding='utf-8')
        seen = _stub_locator(monkeypatch, status_core._LOOKUP_UNANSWERED)

        result = status_query.cmd_read(_ns('read', '--plan-id', PLAN_ID))

        assert result is not None
        assert result['resolved_from'] == 'current'
        assert 'resolved_checkout' not in result
        assert seen == [], 'a local hit must not pay for the locator consult'

    @pytest.mark.parametrize('verb', ['progress', 'get-context'])
    def test_the_other_read_verbs_resolve_the_sibling_plan_too(
        self, verb: str, main_base: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # progress and get-context share the widened gate with read; a verb that
        # kept the strict one would refuse and return None here.
        worktree = _add_linked_worktree(tmp_path / 'main', main_base, PLAN_ID)
        _stub_locator(monkeypatch, status_core._CheckoutLookup(True, worktree))
        handler = {'progress': status_query.cmd_progress, 'get-context': status_query.cmd_get_context}[verb]

        result = handler(_ns(verb, '--plan-id', PLAN_ID))

        assert result is not None
        assert result['status'] == 'success'
        assert result['resolved_from'] == 'worktree'

    def test_metadata_get_resolves_the_sibling_plan(
        self, main_base: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        worktree = _add_linked_worktree(tmp_path / 'main', main_base, PLAN_ID)
        _stub_locator(monkeypatch, status_core._CheckoutLookup(True, worktree))

        result = status_query.cmd_metadata(_ns('metadata', '--plan-id', PLAN_ID, '--get', '--field', 'use_worktree'))

        assert result is not None
        assert result['status'] == 'success'
        assert result['value'] is True
        assert result['resolved_from'] == 'worktree'
