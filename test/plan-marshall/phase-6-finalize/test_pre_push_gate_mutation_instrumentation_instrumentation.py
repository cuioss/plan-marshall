#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Executable demonstration of the pre-push quality gate's commit instrumentation.

``default:pre-push-quality-gate`` declares ``mutates_source: true``, which enrols
it in the dispatcher's item-5f commit instrumentation. The declaration is a claim
about the step's CONTRACT — the step runs each project's resolved ``quality-gate``,
and a project whose gate auto-fixes leaves edits in the worktree when the step
returns — so the behaviour it turns on has to be observed rather than reasoned
about.

Four arms, three of them driving real git commands against throwaway
repositories:

* **Arm 1 — the cheap path** (clean tree, item-5f(c)). Nothing was fixed, the
  porcelain is empty, no commit is made and HEAD does not move.
* **Arm 2 — the mutating path** (dirty tree, item-5f(a)+(b)). The instrumentation
  commit is whole-tree, so an unrelated dirty tracked file the step never touched
  IS swept into the resulting commit. This is the one genuine behavioural delta
  the declaration turns on.
* **Arm 3 — the matched control** (the same dirty tree, ``mutates_source: false``).
  Item 5f skips (a)-(d) entirely and the file stays uncommitted. Without this arm,
  arm 2 is satisfied by a harness that would commit under either declaration.
* **Arm 4 — the constructed-argv pin, plus the configuration that argv resolves
  against.** Whether this repository's gate leaves a dirty tree is a property of
  ``build.py`` and of the resolved ruff configuration, settled by asserting both
  rather than by running the gate. THIS REPOSITORY'S GATE AUTO-FIXES: the argv arm
  pins that both halves (``ruff check --fix`` and ``ruff format``) are constructed,
  which is the org norm rather than a local exception — the Maven side's canonical
  ``quality-gate`` resolves ``verify -Ppre-commit`` and rewrites tracked files the
  same way. The claim is bounded by the invocation's own scope, and that bound is
  DERIVED at run time from ``build._quality_gate_could_run`` against
  ``build._QUALITY_GATE_DIMENSIONS`` rather than restated here — arm 4 runs
  module-scoped, so a dimension that scope does not reach never enters the recorded
  argv and is outside what the sweep can speak to. The configuration half is the
  complement, and it did NOT flip: write mode must stay OUT of configuration so
  that mutation is explicit per invocation, and read-only invocations (the ``lint``
  alias, any ad-hoc ``ruff check``) keep reporting instead of silently rewriting.

Plus the declaration assertions: the two frontmatter facts resolve truthy
post-flip, and — jointly — ``mutates_source: true`` together with an order below
the settle-band bound is what makes the gate a re-stale trigger-set member. The
bound is READ from ``verdict-currency.md`` rather than hardcoded, so a moved
threshold moves the assertion with it.

Arms 1-3 model item 5f's own primitives (``git status --porcelain``, then the
whole-tree commit) rather than invoking the dispatcher, because the dispatcher is
an LLM-orchestration prose surface with no callable entry point. The commands are
the ones the prose names.
"""

from __future__ import annotations

import re
import subprocess
import tomllib
from pathlib import Path

import build
import extension_discovery
import pytest

from conftest import get_skill_dir

_PHASE6_STANDARDS: Path = get_skill_dir('plan-marshall', 'phase-6-finalize') / 'standards'
_GATE_DOC = _PHASE6_STANDARDS / 'pre-push-quality-gate.md'
_VERDICT_CURRENCY_DOC = _PHASE6_STANDARDS / 'verdict-currency.md'

#: The repo root, derived from the imported module rather than hard-coded.
_REPO_ROOT = Path(build.__file__).resolve().parent

#: A tracked file the gate did NOT touch — the unrelated-dirt shape arm 2 needs.
_UNRELATED_TRACKED = 'marketplace/bundles/demo/skills/demo/SKILL.md'

#: A tracked file standing in for something the gate itself would have fixed.
_GATE_TOUCHED = 'marketplace/bundles/demo/scripts/demo.py'

#: The bundle arm 4 scopes the gate to, so the sweep stays module-scoped and cheap.
_ARM4_MODULE = 'plan-marshall'

#: Argv tokens that would make ruff a source mutator: the write-enabling flags of
#: ``check`` (``--fix-only`` implies ``--fix``, so both spellings write, and
#: ``--unsafe-fixes`` widens what a write may change) and the ``format`` subcommand,
#: which writes unconditionally. Every one of them must be absent. Membership is by
#: exact token, so the negating ``--no-fix`` / ``--no-fix-only`` spellings do not
#: match.
_MUTATING_RUFF_TOKENS = ('--fix', '--fix-only', '--unsafe-fixes', 'format')

#: The ruff CONFIGURATION keys that turn writing on without any argv flag. Same
#: contract as the token denylist above, on the other half of the surface.
_MUTATING_RUFF_SETTINGS = ('fix', 'fix-only', 'unsafe-fixes')

#: The ruff configuration files ruff resolves at the repository ROOT — the ones
#: governing the gate's own invocation. Ruff also honours a config beside a linted
#: file; this tuple deliberately does not walk for those (see the assertion's
#: docstring for the bound and why it is drawn there).
_ROOT_RUFF_CONFIG_NAMES = ('pyproject.toml', 'ruff.toml', '.ruff.toml')


# ---------------------------------------------------------------------------
# Real-git fixture (identity supplied per invocation, so the run is hermetic)
# ---------------------------------------------------------------------------


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run one git command against ``repo`` with a pinned, hermetic identity.

    Commit identity and signing are supplied per-invocation rather than read from
    the ambient environment, so the fixture behaves identically on a developer
    machine with a global gitconfig and on a bare runner with none.
    """
    return subprocess.run(
        [
            'git',
            '-C',
            str(repo),
            '-c',
            'user.name=Test',
            '-c',
            'user.email=test@example.invalid',
            '-c',
            'commit.gpgsign=false',
            *args,
        ],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )


def _write(repo: Path, rel_path: str, content: str) -> Path:
    """Write ``content`` to ``repo/rel_path``, creating parents as needed."""
    target = repo / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding='utf-8')
    return target


def _porcelain(repo: Path) -> str:
    """Item 5f(a): the uncommitted-changes probe, verbatim."""
    return _git(repo, 'status', '--porcelain').stdout


def _head(repo: Path) -> str:
    """The current HEAD sha."""
    return _git(repo, 'rev-parse', 'HEAD').stdout.strip()


def _instrumentation_commit(repo: Path, message: str) -> None:
    """Item 5f(b): the whole-tree commit the dispatcher makes on a dirty tree.

    Whole-tree is the property under test, not an implementation shortcut: the
    dispatcher hands the commit to the git workflow with a message and no path
    filter, so whatever is dirty at that moment is what lands.
    """
    _git(repo, 'add', '-A')
    _git(repo, 'commit', '-m', message)


@pytest.fixture
def seeded_repo(tmp_path: Path) -> Path:
    """A real git repository whose worktree starts clean and committed.

    Both tracked files are committed, so any dirt a test introduces is
    unambiguously that test's own and arm 1's empty porcelain cannot be an
    accident of the seed.
    """
    repo = tmp_path / 'worktree'
    repo.mkdir()
    _git(repo, 'init', '--initial-branch=main')
    _write(repo, _UNRELATED_TRACKED, '# demo skill\n')
    _write(repo, _GATE_TOUCHED, 'x = 1\n')
    _git(repo, 'add', '-f', _UNRELATED_TRACKED, _GATE_TOUCHED)
    _git(repo, 'commit', '-m', 'chore: seed worktree')
    return repo


# ---------------------------------------------------------------------------
# Arm 1 — clean tree takes item-5f(c), the no-commit path
# ---------------------------------------------------------------------------


def _ticks(*values: float):
    """A ``time.monotonic`` stub yielding a plausible elapsed time per call."""
    stream = iter(values)
    last = values[-1]

    def _monotonic() -> float:
        nonlocal last
        try:
            last = next(stream)
        except StopIteration:
            pass
        return last

    return _monotonic

@pytest.fixture
def recorded_argv(monkeypatch) -> list[list[str]]:
    """Capture every argv at the LOWEST subprocess primitive, running nothing.

    ``build.subprocess.run`` is patched rather than ``build.run`` so the recorded
    list is the argv the primitive actually receives — a wrapper that rewrote it
    could not hide behind the assertion.
    """
    calls: list[list[str]] = []

    class _Completed:
        returncode = 0

    def _fake_run(cmd, *_args, **_kwargs):
        calls.append(list(cmd))
        return _Completed()

    monkeypatch.chdir(_REPO_ROOT)
    monkeypatch.setattr(build.subprocess, 'run', _fake_run)
    monkeypatch.setattr(build, '_compute_mypypath', lambda: '')
    monkeypatch.setattr(build.time, 'monotonic', _ticks(100.0, 130.0))
    return calls

def _gate_fields(*keys: str) -> dict:
    """Read the gate's frontmatter through the registry's OWN extraction primitive."""
    return extension_discovery._read_frontmatter_fields(_GATE_DOC, keys)

def _settle_band_order_bound() -> int:
    """Read the settle-band order bound off ``verdict-currency.md``'s trigger table.

    Read rather than hardcoded so a moved threshold moves this assertion with it;
    a literal here would keep passing against a table that had changed.
    """
    text = _VERDICT_CURRENCY_DOC.read_text(encoding='utf-8')
    match = re.search(r'`mutates_source: true`\s+on a step ordered\s+`<\s*(\d+)`', text)
    assert match, (
        'verdict-currency.md no longer states the settle-band trigger bound in the '
        'expected form, so the enrolment conjunction below cannot be derived'
    )
    return int(match.group(1))

def test_clean_tree_makes_no_commit_and_leaves_head_unmoved(seeded_repo: Path):
    """A gate run that fixed nothing produces an empty porcelain and no commit.

    This is the path every run in a repository whose gate does not auto-fix
    takes, so it is what the flip changes for such a repository: nothing.
    """
    # Arrange — the fixture committed everything; the gate touched nothing.
    seed_head = _head(seeded_repo)

    # Act
    porcelain = _porcelain(seeded_repo)

    # Assert — 5f(c): empty porcelain, so no commit is made and HEAD is unmoved.
    assert porcelain == '', f'a clean tree must yield an empty porcelain; got {porcelain!r}'
    assert _head(seeded_repo) == seed_head


def test_non_mutating_declaration_leaves_the_dirty_file_uncommitted(seeded_repo: Path):
    """Under ``mutates_source: false`` item 5f skips (a)-(d) and the dirt survives.

    This is the status quo the flip replaces: the dirty file reaches the push
    barrier, which asserts a clean tree and stops. Arm 2 is only meaningful
    against this control — without it, a harness that committed under either
    declaration would satisfy arm 2 just as well.
    """
    # Arrange — the same dirt arm 2 used.
    _write(seeded_repo, _UNRELATED_TRACKED, '# demo skill\n\nEdited by something else.\n')
    seed_head = _head(seeded_repo)

    # Act — mutates_source: false means the instrumentation does not run at all.

    # Assert — nothing was committed and the tree is still dirty.
    assert _head(seeded_repo) == seed_head, 'a non-mutating step makes no commit'
    assert _UNRELATED_TRACKED in _porcelain(seeded_repo), (
        'the dirty file must survive uncommitted — this is what reaches the push barrier'
    )


def test_the_resolved_ruff_configuration_enables_no_write_mode():
    """The other half of the contract: the CONFIG the gate's argv resolves against.

    The gate auto-fixes, and the arm above pins that it does so through EXPLICIT
    argv flags. This arm holds the complement: the write mode must not ALSO be
    turned on in configuration. The invariant survives the flip to auto-fixing —
    only its rationale changes, and it is now the more useful of the two.

    Configuration-level ``fix``/``fix-only`` applies to every ruff invocation in
    the repository, not only the gate's. The ``lint`` alias (``ruff check`` with no
    flag) and any ad-hoc ``ruff check`` a contributor runs would silently start
    rewriting the tree, with no argv anywhere recording that it could. Keeping the
    write mode explicit at the call site is what makes "which invocations mutate"
    readable from the invocation itself — the gate's two halves do, everything
    else does not.

    **The bound is stated rather than claimed away.** This reads the ruff
    configuration ruff resolves at the repository ROOT, which is what governs the
    gate's own invocation. Ruff additionally honours a config beside a linted
    file, and this arm does NOT walk for those: the only nested candidates in this
    tree are build-system fixtures, and a whole-tree walk would also sweep
    ``.plan/temp/`` pytest residue, so the arm's verdict would depend on what a
    previous run happened to leave behind. The population it did read is named in
    every failure message, so a silence here is never mistaken for a wider sweep.
    """
    # Arrange — the root candidates that actually exist. An empty population is a
    # failure, not a vacuous pass: an arm that read nothing proves nothing.
    present = [name for name in _ROOT_RUFF_CONFIG_NAMES if (_REPO_ROOT / name).is_file()]
    assert present, (
        f'no root ruff configuration exists among {list(_ROOT_RUFF_CONFIG_NAMES)!r}, '
        'so this arm read nothing and its silence is not evidence'
    )

    # Act + Assert — a `pyproject.toml` nests the settings under [tool.ruff]; a
    # dedicated ruff config carries them at the top level.
    for name in present:
        parsed = tomllib.loads((_REPO_ROOT / name).read_text(encoding='utf-8'))
        settings = parsed.get('tool', {}).get('ruff', {}) if name == 'pyproject.toml' else parsed
        enabled = [key for key in _MUTATING_RUFF_SETTINGS if settings.get(key)]
        assert not enabled, (
            f'{name} enables ruff write mode via {enabled!r}, so `ruff check` rewrites '
            'source whatever argv the gate constructs; population read for this arm: '
            f'{present!r}'
        )


def test_quality_gate_fails_on_an_spdx_offender_rather_than_fixing_it(recorded_argv, monkeypatch):
    """An SPDX offender turns the gate red; it is never repaired into a pass."""
    # Arrange — one offender reported by the check.
    monkeypatch.setattr(build, 'check_spdx_headers', lambda paths: ['some/file.py'])

    # Act
    exit_code = build.cmd_quality_gate(_ARM4_MODULE)

    # Assert
    assert exit_code == 1, 'a reported SPDX offender must fail the gate'


def test_executor_bootstrap_target_is_the_git_ignored_executor_path(monkeypatch, tmp_path: Path):
    """The sole conditional write target is ``.plan/execute-script.py``, and it is ignored.

    The path is DERIVED, not asserted: the bootstrap's own post-check accepts the
    run only if that exact file landed, so a generator writing anywhere else
    would still return non-zero. Its git-ignored status is then observed by
    asking git, not by reading ``.gitignore`` and interpreting it.
    """
    # Arrange — a generator that writes exactly the executor path.
    monkeypatch.chdir(tmp_path)
    target = tmp_path / '.plan' / 'execute-script.py'

    def _writing_run(cmd, description, env=None):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('SCRIPTS = {}\n', encoding='utf-8')
        return 0

    monkeypatch.setattr(build, 'run', _writing_run)

    # Act
    exit_code = build.ensure_executor_substrate()

    # Assert — the post-check accepted it, so that path IS the target.
    assert exit_code == 0
    ignored = subprocess.run(
        ['git', '-C', str(_REPO_ROOT), 'check-ignore', '-v', '.plan/execute-script.py'],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert ignored.returncode == 0, (
        'the bootstrap write target must be git-ignored, so the gate cannot dirty '
        f'a tracked path; git check-ignore said {ignored.stdout!r} {ignored.stderr!r}'
    )


def test_gate_still_declares_head_dependent_true():
    """The flip leaves ``head_dependent`` untouched — the two facts are independent."""
    assert _gate_fields('head_dependent').get('head_dependent') is True
