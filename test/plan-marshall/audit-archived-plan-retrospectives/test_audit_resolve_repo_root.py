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
from _audit_fixtures import _line, _write_log, audit, minimal_corpus


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


class TestRunChecksTwoRootBinding:
    """``run_checks`` binds the two roots SEPARATELY — the default is not a coercion.

    ``run_checks(all_inputs, selected, repo_root, main_root=None)`` defaults
    ``main_root`` to ``repo_root``, which is what a caller staging both populations
    inside ONE sandbox wants — and that is every other test in this suite. That
    uniformity is precisely why the defaulting line was never exercised: with
    ``main_root == repo_root`` at every call site, a fallback that fired
    unconditionally and one that fired only on ``None`` are indistinguishable.

    These three drive the two states apart, over ONE observable — the
    ``global-log-analysis`` summary metric, which is computed from
    ``{main_root}/.plan/local/logs/`` and is withheld entirely when no log was
    read. A single log file is staged under exactly one root per test, so the
    metric's presence and value say WHICH root the main-anchored reads used.
    """

    #: One genuine failure line: elevated level plus real failure markers, the
    #: shape ``cross_global_log_analysis`` counts as an error (a bare probe or a
    #: DEBUG diagnostic would not).
    _ERROR_LINE = ('2026-06-01T10:10:00Z', 'ERROR', 'pm:x:x run -> status: error exit_code=1')

    @staticmethod
    def _persisted_metrics(repo_root: Path) -> dict:
        """Parse the summary-metric header of the report ``run_checks`` just wrote."""
        reports = sorted((repo_root / audit.AUDIT_REPORTS_REL).glob('*.toon'))
        assert reports, 'precondition: run_checks must have persisted a report'
        return audit._parse_report_summary_metrics(reports[-1])

    @staticmethod
    def _two_roots(tmp_path: Path) -> tuple[Path, Path]:
        repo_root = tmp_path / 'repo'
        main_root = tmp_path / 'main'
        repo_root.mkdir()
        main_root.mkdir()
        return repo_root, main_root

    def test_an_explicit_main_root_is_not_overwritten_by_the_repo_root(
        self, tmp_path: Path
    ):
        """A supplied ``main_root`` must SURVIVE — the default fires only on ``None``.

        This is the branch every other caller in the suite leaves untouched, and it
        is the one ``main()`` actually takes: it is the only caller that can run
        from a linked worktree, where the two roots genuinely differ. A fallback
        that assigned ``repo_root`` unconditionally would silently discard the main
        checkout and read the machine-singular corpora out of the worktree's own
        partial ``.plan/`` — the exact collapse ``_resolve_main_root`` exists to
        prevent, re-introduced one layer up at the consumer.
        """
        repo_root, main_root = self._two_roots(tmp_path)
        inputs = minimal_corpus(repo_root)
        _write_log(main_root, 'work-2026-06-01.log', [_line(*self._ERROR_LINE)])
        assert not (repo_root / '.plan' / 'local' / 'logs').exists(), (
            'precondition: the ONLY log corpus on disk is under main_root, so a '
            'measured result can have come from nowhere else'
        )

        audit.run_checks(inputs, ['global-log-analysis'], repo_root, main_root)

        metrics = self._persisted_metrics(repo_root)
        assert metrics['global-log-analysis_errors'] == 1, (
            'the main-anchored read must use the supplied main_root; a 1 here is '
            'only reachable by reading the log staged under it'
        )

    def test_the_same_corpus_is_invisible_when_main_root_is_omitted(
        self, tmp_path: Path
    ):
        """The matched negative control for the guard above.

        Byte-identical fixture — the same single log under the same ``main_root``
        — with the argument simply not passed. The metric is WITHHELD, because the
        main-anchored reads fall back to ``repo_root``, which holds no logs.

        Without this control the assertion above would be equally satisfied by a
        function that read every root it could find, and ``== 1`` would prove
        nothing about which root was bound.
        """
        repo_root, main_root = self._two_roots(tmp_path)
        inputs = minimal_corpus(repo_root)
        _write_log(main_root, 'work-2026-06-01.log', [_line(*self._ERROR_LINE)])

        audit.run_checks(inputs, ['global-log-analysis'], repo_root)

        metrics = self._persisted_metrics(repo_root)
        assert 'global-log-analysis_errors' not in metrics

    def test_an_omitted_main_root_reads_the_repo_root_corpus(self, tmp_path: Path):
        """The default itself: with no ``main_root``, the main-anchored reads use ``repo_root``.

        The third leg of the partition — the same single log, now staged under
        ``repo_root``, IS read when the argument is omitted. Together with the
        control above this pins the default as a default: it supplies ``repo_root``
        when nothing was given, and supplies nothing when something was.
        """
        repo_root, _main_root = self._two_roots(tmp_path)
        inputs = minimal_corpus(repo_root)
        _write_log(repo_root, 'work-2026-06-01.log', [_line(*self._ERROR_LINE)])

        audit.run_checks(inputs, ['global-log-analysis'], repo_root)

        metrics = self._persisted_metrics(repo_root)
        assert metrics['global-log-analysis_errors'] == 1
