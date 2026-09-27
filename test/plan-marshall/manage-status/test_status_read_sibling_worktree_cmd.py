# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_status_read_sibling_worktree_fixtures import (
    PLAN_ID,
    Path,
    _add_linked_worktree,
    _ns,
    main_base,
    status_query,
)

# =============================================================================
# cmd_list is UNCHANGED — pinning the refuted half of the original hypothesis
# =============================================================================


class TestCmdListUnchanged:
    def test_cmd_list_still_scans_worktrees_and_publishes_scope(self, main_base: Path, tmp_path: Path) -> None:
        # The `list` half of the fold was refuted at outline time: the scan and the
        # scope field already shipped. Pinned here so a later reader cannot mistake
        # the untouched verb for an unfixed one.
        _add_linked_worktree(tmp_path / 'main', main_base, PLAN_ID)

        result = status_query.cmd_list(_ns('list'))

        assert result['scope'] == 'main'
        assert [(plan['id'], plan['location']) for plan in result['plans']] == [(PLAN_ID, 'worktree')]

    def test_cmd_list_carries_no_read_verb_provenance(self, main_base: Path, tmp_path: Path) -> None:
        # The enumeration answers a different question than a single-plan read, so
        # it gains none of the read verbs' provenance fields.
        _add_linked_worktree(tmp_path / 'main', main_base, PLAN_ID)

        result = status_query.cmd_list(_ns('list'))

        assert 'resolved_from' not in result
        assert 'plan_visibility' not in result
