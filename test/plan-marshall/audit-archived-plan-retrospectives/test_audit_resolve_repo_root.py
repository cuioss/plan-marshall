#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Root resolution — the TWO resolvers and the partition between them.

``_resolve_repo_root`` is the CWD-SCOPED walk-up: it finds the project root from a
nested working directory and fails closed when no root is reachable. It owns the
plan scan roots, the persisted report and the dormation moves.

``_resolve_main_root`` is the MAIN-ANCHORED resolver: it answers with the main
checkout even when asked from a linked worktree, and owns every machine-singular
``.plan/`` store (the lessons corpus, the global logs, the lock logs, the
change-ledger, the project config).

Collapsing the two is the defect these tests exist to prevent, and it is a defect
in BOTH directions — a walk-up serving a corpus read publishes a worktree's
sliver as the corpus, while a main-anchored answer serving the report write puts
the report somewhere the caller never asked for.
"""

import subprocess
import tempfile
from pathlib import Path

import pytest
from _audit_fixtures import audit


class TestResolveRepoRoot:
    """``_resolve_repo_root`` walks up to the nearest ancestor carrying ``.plan/local``.

    Every repo-root-anchored read and write in ``audit.py`` — the corpus scan
    roots, the lessons-corpus read, the global-log read, the retire-on-quiet run
    history, and the persisted report — hangs off this resolver, so the branch
    that matters is (b): invoked from a subdirectory, the resolver must return
    the project root rather than the working directory.

    All three branches drive the REAL resolver through ``monkeypatch.chdir``
    into a constructed sandbox. ``Path.cwd`` itself is never stubbed or
    monkeypatched, which is what makes branch (b) fail against a revert to
    ``repo_root = Path.cwd()`` instead of passing against a mock.
    """

    def test_cwd_is_the_marker_bearing_root_returns_cwd(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        # branch (a): cwd IS the root
        (tmp_path / '.plan' / 'local').mkdir(parents=True)
        monkeypatch.chdir(tmp_path)

        resolved = audit._resolve_repo_root()

        assert resolved == Path.cwd()
        assert (resolved / '.plan' / 'local').is_dir()

    def test_nested_cwd_walks_up_to_the_marker_bearing_ancestor(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        # branch (b): cwd is BELOW the root — the branch a Path.cwd() derivation fails
        (tmp_path / '.plan' / 'local').mkdir(parents=True)
        nested = tmp_path / 'marketplace' / 'bundles' / 'plan-marshall'
        nested.mkdir(parents=True)
        monkeypatch.chdir(nested)

        resolved = audit._resolve_repo_root()

        assert resolved == tmp_path.resolve()
        assert resolved != Path.cwd()

    def test_no_marker_bearing_ancestor_falls_back_to_cwd(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        # branch (c): nothing qualifies — stay anchored where we were invoked, which
        # is what keeps an out-of-project invocation inside its own sandbox.
        #
        # Deliberately NOT `tmp_path`: pytest's basetemp is configured under this
        # project's own `.plan/temp/`, so every `tmp_path` HAS a `.plan/local`-bearing
        # ancestor (the repo root) and the no-marker branch is unconstructible there.
        # The system temp dir is the nearest thing to a genuinely out-of-project cwd;
        # the precondition below fails loudly rather than silently passing vacuously
        # if that ever stops holding.
        with tempfile.TemporaryDirectory() as raw:
            bare = Path(raw).resolve() / 'outside-any-project'
            bare.mkdir()
            assert not any(
                (ancestor / '.plan' / 'local').is_dir()
                for ancestor in (bare, *bare.parents)
            ), 'system temp dir sits inside a .plan/local tree — branch (c) unconstructible'
            monkeypatch.chdir(bare)

            resolved = audit._resolve_repo_root()

            assert resolved == Path.cwd()


def _git(cwd: Path, *args: str) -> None:
    """Run one git command in ``cwd``, failing the test loudly on a non-zero exit."""
    subprocess.run(
        ['git', '-C', str(cwd), *args],
        check=True,
        capture_output=True,
        text=True,
    )


class TestResolveMainRoot:
    """``_resolve_main_root`` answers with the MAIN checkout, from either tree.

    Driven against a REAL git repository with a REAL linked worktree rather than a
    stub, because the whole mechanism under test is git's own
    ``rev-parse --git-common-dir`` answer. A stubbed resolver would assert only
    that the code calls the function the test told it to call.
    """

    @staticmethod
    def _repo_with_worktree(tmp_path: Path) -> tuple[Path, Path]:
        """Build ``(main, worktree)`` — a real repo and a real linked worktree.

        BOTH trees are given a ``.plan/local`` marker. That is the load-bearing
        part of the fixture: it is what a plan's pinned worktree actually looks
        like under ADR-002, and it is what makes the cwd walk-up answer with the
        WORKTREE. Without the worktree's own marker the walk-up would climb to
        main anyway and both resolvers would agree by accident — the test would
        pass against the very collapse it exists to catch.
        """
        main = tmp_path / 'main'
        main.mkdir()
        _git(main, 'init', '--initial-branch', 'main')
        _git(main, 'config', 'user.email', 'test@example.com')
        _git(main, 'config', 'user.name', 'test')
        _git(main, 'commit', '--allow-empty', '-m', 'root')

        worktree = tmp_path / 'linked-worktree'
        _git(main, 'worktree', 'add', str(worktree), '-b', 'feature/x')

        (main / '.plan' / 'local').mkdir(parents=True)
        (worktree / '.plan' / 'local').mkdir(parents=True)
        return main.resolve(), worktree.resolve()

    def test_from_a_linked_worktree_resolves_the_main_checkout(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        # THE criterion: from a cwd inside a linked worktree, the resolved corpus
        # root is main's — not the worktree's partial `.plan/local`.
        main, worktree = self._repo_with_worktree(tmp_path)
        monkeypatch.chdir(worktree)

        assert audit._resolve_main_root() == main

    def test_the_two_resolvers_disagree_inside_a_linked_worktree(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """The partition, asserted as a partition.

        This is the discriminating assertion: inside a linked worktree the
        cwd-scoped resolver MUST still answer the worktree while the main-anchored
        one answers main. A regression that collapsed either resolver into the
        other would make these two equal, and no single-resolver assertion above
        would notice.
        """
        main, worktree = self._repo_with_worktree(tmp_path)
        monkeypatch.chdir(worktree)

        assert audit._resolve_repo_root() == worktree
        assert audit._resolve_main_root() == main
        assert audit._resolve_repo_root() != audit._resolve_main_root()

    def test_from_the_main_checkout_both_resolvers_agree(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        # The positive control: the partition must not invent a difference where
        # there is none. Asked from main, both answer main.
        main, _worktree = self._repo_with_worktree(tmp_path)
        monkeypatch.chdir(main)

        assert audit._resolve_main_root() == main
        assert audit._resolve_repo_root() == main

    def test_outside_any_repository_falls_back_to_the_cwd_walk_up(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """`None` from git means "no repository answered", never "use main anyway".

        Deliberately NOT `tmp_path`: pytest's basetemp sits inside this project, so
        every `tmp_path` IS in a repository and the no-repo branch is
        unconstructible there. The precondition below fails loudly rather than
        passing vacuously if that ever stops holding.
        """
        with tempfile.TemporaryDirectory() as raw:
            bare = Path(raw).resolve() / 'outside-any-project'
            bare.mkdir()
            probe = subprocess.run(
                ['git', '-C', str(bare), 'rev-parse', '--git-common-dir'],
                capture_output=True,
                text=True,
                check=False,
            )
            assert probe.returncode != 0, (
                'system temp dir is inside a git repository — the no-repo branch '
                'is unconstructible here'
            )
            monkeypatch.chdir(bare)

            assert audit._resolve_main_checkout(Path.cwd()) is None
            assert audit._resolve_main_root() == Path.cwd()
