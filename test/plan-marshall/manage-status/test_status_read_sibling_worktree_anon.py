# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_status_read_sibling_worktree_fixtures import (
    PLAN_ID,
    Path,
    _ns,
    _stub_locator,
    _write_local_plan,
    json,
    main_base,
    pytest,
    status_core,
    status_query,
)


class TestANonObjectMetadataFieldIsHandled:
    """Both branches normalize; neither raises. The dict cells are matched controls.

    Without the dict cells the guard is equally consistent with a normalization
    that discards every caller's real metadata, which would pass the null cells
    and silently destroy state on the ordinary path.
    """

    @pytest.mark.parametrize('metadata', [None, 'a string', 42, ['a', 'list']])
    def test_metadata_get_reports_not_found_instead_of_raising(
        self, metadata: object, main_base: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Arrange — the widened any-checkout READ branch, over a document whose
        # metadata is not an object.
        _write_local_plan(main_base, PLAN_ID, metadata)
        _stub_locator(monkeypatch, status_core._LOOKUP_UNANSWERED)

        # Act
        result = status_query.cmd_metadata(_ns('metadata', '--plan-id', PLAN_ID, '--get', '--field', 'use_worktree'))

        # Assert — a structured verdict, and an available_fields list that is
        # empty because it was DERIVED from a normalized empty mapping.
        assert result is not None
        assert result['status'] == 'not_found'
        assert result['available_fields'] == []

    def test_metadata_get_still_returns_a_real_value(self, main_base: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        # Matched control — normalization must not flatten a genuine object.
        _write_local_plan(main_base, PLAN_ID, {'use_worktree': True, 'other': 'x'})
        _stub_locator(monkeypatch, status_core._LOOKUP_UNANSWERED)

        result = status_query.cmd_metadata(_ns('metadata', '--plan-id', PLAN_ID, '--get', '--field', 'use_worktree'))

        assert result is not None
        assert result['status'] == 'success'
        assert result['value'] is True

    @pytest.mark.parametrize('metadata', [None, 'a string', 42])
    def test_metadata_set_writes_through_instead_of_raising(
        self, metadata: object, main_base: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Arrange — the sibling WRITE branch, whose ``'metadata' not in status``
        # guard an explicit null walks straight past.
        status_path = _write_local_plan(main_base, PLAN_ID, metadata)
        _stub_locator(monkeypatch, status_core._LOOKUP_UNANSWERED)

        # Act
        result = status_query.cmd_metadata(
            _ns('metadata', '--plan-id', PLAN_ID, '--set', '--field', 'change_type', '--value', 'bug_fix')
        )

        # Assert — and the correction reaches DISK, not only the in-memory view.
        assert result is not None
        assert result['status'] == 'success'
        assert result['value'] == 'bug_fix'
        assert json.loads(status_path.read_text(encoding='utf-8'))['metadata'] == {'change_type': 'bug_fix'}

    def test_metadata_set_preserves_existing_sibling_fields(
        self, main_base: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Matched control — the normalization must be a no-op on a real object, so
        # a set never becomes a wipe of everything already recorded.
        status_path = _write_local_plan(main_base, PLAN_ID, {'use_worktree': True})
        _stub_locator(monkeypatch, status_core._LOOKUP_UNANSWERED)

        result = status_query.cmd_metadata(
            _ns('metadata', '--plan-id', PLAN_ID, '--set', '--field', 'change_type', '--value', 'bug_fix')
        )

        assert result is not None
        assert result['status'] == 'success'
        persisted = json.loads(status_path.read_text(encoding='utf-8'))['metadata']
        assert persisted == {'use_worktree': True, 'change_type': 'bug_fix'}
