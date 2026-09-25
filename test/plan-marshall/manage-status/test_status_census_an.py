# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_status_census_fixtures import (
    _UNEXAMINABLE,
    Any,
    Path,
    _census,
    _cohort,
    _write_plan,
    pytest,
    store,
)


class TestAnUnexaminableEntryIsCredited:
    """An entry the probe cannot complete degrades its cohort instead of vanishing.

    Both positives and the control run under the SAME injected denial, so the only
    thing that differs between them is whether the tree holds the unexaminable entry.
    """

    @pytest.fixture
    def deny_probe(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Deny ``stat`` for the single entry named ``_UNEXAMINABLE``, Python-3.14 style.

        The production condition is a search-bit denial on the containing directory:
        ``iterdir`` still lists the names (that needs read) while stat-ing each child
        fails with ``EACCES`` (that needs search). Staging it with ``chmod`` would make
        the verdict depend on the uid running the suite — root bypasses the permission
        check outright and the entry would probe cleanly — so the denial is injected at
        the syscall, narrowed by name. Every other entry keeps the real ``stat``.

        ⛔ The injection sits at ``Path.stat`` AND the two predicates are pinned to
        ``False`` for the same entry, which is exactly the Python 3.14 contract: from
        3.14 ``is_dir`` / ``is_file`` return ``False`` for an operating-system error,
        permission denials included, instead of raising. Under that runtime a
        predicate-based membership probe reads a denied entry as a plain "not a
        directory", skips it, and lets the cohort publish ``coverage: complete`` over an
        entry nobody looked at. Emulating both halves here makes these cells pass only
        against a scan that consults ``stat`` — on every supported Python, rather than
        only on the interpreter the suite happens to run under.
        """
        real_stat = Path.stat

        def denying_stat(path: Path, *args: Any, **kwargs: Any) -> Any:
            if path.name == _UNEXAMINABLE:
                raise PermissionError(13, 'Permission denied')
            return real_stat(path, *args, **kwargs)

        real_is_dir = Path.is_dir
        real_is_file = Path.is_file

        def py314_is_dir(path: Path, *args: Any, **kwargs: Any) -> bool:
            if path.name == _UNEXAMINABLE:
                return False
            return bool(real_is_dir(path, *args, **kwargs))

        def py314_is_file(path: Path, *args: Any, **kwargs: Any) -> bool:
            if path.name == _UNEXAMINABLE:
                return False
            return bool(real_is_file(path, *args, **kwargs))

        monkeypatch.setattr(Path, 'stat', denying_stat)
        monkeypatch.setattr(Path, 'is_dir', py314_is_dir)
        monkeypatch.setattr(Path, 'is_file', py314_is_file)

    def test_an_unexaminable_cohort_entry_degrades_the_cohort(self, store: Path, deny_probe: None) -> None:
        """``partial`` plus a non-zero ``unreadable_count``, with the entry named.

        The entry is NOT added to ``population``: nothing established it is a plan, so
        counting it as one would be a second false claim. It is the ``unreadable_count``
        and the ``reason`` that carry it — a silent ``continue`` here is what would let
        this cohort publish ``complete`` over an entry it never looked at.
        """
        del deny_probe
        _write_plan(store / 'plans' / 'readable-plan', {'1-init': 'done', '5-execute': 'in_progress'})
        (store / 'plans' / _UNEXAMINABLE).mkdir(parents=True)

        result = _census()

        live = _cohort(result, 'live')
        assert live['coverage'] == 'partial', live
        assert live['unreadable_count'] == 1, f'The unexaminable entry must be credited; got {live!r}.'
        assert live['population'] == 1, f'Only the established member counts as a member; got {live!r}.'
        assert live['open_phase_count'] == 1, live
        assert _UNEXAMINABLE in live['reason'], live

    def test_an_unexaminable_worktree_entry_degrades_the_worktree_cohort(self, store: Path, deny_probe: None) -> None:
        """The same credit one level up, where the unknown is a whole plan store.

        A worktree entry that cannot be examined may hold any number of plans, none of
        them seen, so it counts as one unreadable unit. This is the second discard site
        and it needs its own cell: a fix applied to the inner loop alone leaves this one
        reporting ``complete``.
        """
        del deny_probe
        _write_plan(store / 'worktrees' / 'wt-0' / '.plan' / 'local' / 'plans' / 'wt-plan-0', {'1-init': 'done'})
        (store / 'worktrees' / _UNEXAMINABLE).mkdir(parents=True)

        result = _census()

        worktree = _cohort(result, 'worktree')
        assert worktree['coverage'] == 'partial', worktree
        assert worktree['unreadable_count'] == 1, worktree
        assert worktree['population'] == 1, f'The readable store still contributes its member; got {worktree!r}.'
        assert _UNEXAMINABLE in worktree['reason'], worktree

    def test_a_fully_examinable_cohort_still_reports_complete(self, store: Path, deny_probe: None) -> None:
        """Matched control: the identical tree MINUS the unexaminable entry.

        The load-bearing half. The denial is still installed, so what differs is only
        that no entry triggers it. Without this cell both positives are equally
        consistent with a verb that reports ``partial`` for everything — which would
        make the tri-state worthless in the opposite direction.
        """
        del deny_probe
        _write_plan(store / 'plans' / 'readable-plan', {'1-init': 'done', '5-execute': 'in_progress'})

        result = _census()

        live = _cohort(result, 'live')
        assert live['coverage'] == 'complete', live
        assert live['unreadable_count'] == 0, live
        assert live['population'] == 1, live
        assert 'reason' not in live, f'A complete cohort has no shortfall to name; got {live!r}.'
