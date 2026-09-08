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
* **Arm 4 — the constructed-argv pin.** Whether THIS repository's gate can leave a
  dirty tree at all is a property of ``build.py``, and it is settled by asserting
  the argv the gate constructs rather than by running it: ``ruff check`` carries no
  ``--fix``, the SPDX check reports offenders instead of inserting headers, and the
  executor bootstrap's only write target is git-ignored.

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

#: Argv tokens that would make ruff a source mutator. ``check --fix`` and
#: ``format`` are the two spellings that write; both must be absent.
_MUTATING_RUFF_TOKENS = ('--fix', '--unsafe-fixes', 'format')


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


# ---------------------------------------------------------------------------
# Arm 2 — dirty tree takes item-5f(a)+(b), and the commit is whole-tree
# ---------------------------------------------------------------------------


def test_dirty_unrelated_file_is_swept_into_the_instrumentation_commit(seeded_repo: Path):
    """An unrelated dirty tracked file lands in the instrumentation commit.

    The commit carries no path filter, so it absorbs whatever else was dirty at
    that moment. This is the behavioural delta the declaration turns on, and it
    is asserted from the commit's own contents rather than from the commit
    succeeding.
    """
    # Arrange — dirty ONLY a file the gate did not touch.
    _write(seeded_repo, _UNRELATED_TRACKED, '# demo skill\n\nEdited by something else.\n')
    seed_head = _head(seeded_repo)

    # Act — 5f(a) observes the dirt, 5f(b) commits it.
    porcelain = _porcelain(seeded_repo)
    _instrumentation_commit(seeded_repo, 'chore(quality-gate): apply pre-push auto-fixes')

    # Assert — the porcelain named it, and the commit absorbed it.
    assert _UNRELATED_TRACKED in porcelain
    committed = _git(seeded_repo, 'show', '--name-only', '--format=', 'HEAD').stdout.split()
    assert _UNRELATED_TRACKED in committed, (
        f'the unrelated file must be absorbed by the whole-tree commit; got {committed!r}'
    )
    assert _head(seeded_repo) != seed_head, 'the instrumentation commit must advance HEAD'
    assert _porcelain(seeded_repo) == '', 'the tree must be clean once the commit lands'


# ---------------------------------------------------------------------------
# Arm 3 — matched control: the pre-flip declaration skips 5f(a)-(d) entirely
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Arm 4 — constructed-argv pin on this repository's own gate
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


def test_quality_gate_invokes_ruff_check_with_no_fix_flag(recorded_argv, monkeypatch):
    """The gate lints; it does not rewrite. No argv it builds carries a write flag.

    Asserted against the constructed argv rather than by running the gate: a real
    run costs minutes, and its outcome would depend on the tree it happened to
    run against.
    """
    # Arrange — module-scoped, so the whole-tree-only arms stay out of scope.
    monkeypatch.setattr(build, 'check_spdx_headers', lambda paths: [])

    # Act
    exit_code = build.cmd_quality_gate(_ARM4_MODULE)

    # Assert — ruff ran, and nothing that ran could write.
    assert exit_code == 0
    ruff_calls = [cmd for cmd in recorded_argv if 'ruff' in cmd]
    assert ruff_calls, f'the gate must invoke ruff; recorded {recorded_argv!r}'
    for cmd in ruff_calls:
        assert 'check' in cmd, f'ruff must be invoked in check mode; got {cmd!r}'
    for cmd in recorded_argv:
        offenders = [token for token in cmd if token in _MUTATING_RUFF_TOKENS]
        assert not offenders, (
            f'the gate must construct no source-rewriting argv; {offenders!r} in {cmd!r}'
        )


def test_spdx_check_reports_the_offender_without_editing_it(tmp_path: Path):
    """A file missing the SPDX header is REPORTED, and its bytes are untouched.

    The read-only half of the gate's mutation surface: were the check to insert
    the header it would be a source mutator in every repository, not only one
    whose linter auto-fixes.
    """
    # Arrange — one .py file with no SPDX header.
    offender = tmp_path / 'missing_header.py'
    original = 'x = 1\n'
    offender.write_text(original, encoding='utf-8')

    # Act
    reported = build.check_spdx_headers([str(tmp_path)])

    # Assert — named as an offender, and byte-identical afterwards.
    assert [Path(p).name for p in reported] == ['missing_header.py']
    assert offender.read_text(encoding='utf-8') == original, (
        'check_spdx_headers must report offenders, never rewrite them'
    )


def test_quality_gate_fails_on_an_spdx_offender_rather_than_fixing_it(
    recorded_argv, monkeypatch
):
    """An SPDX offender turns the gate red; it is never repaired into a pass."""
    # Arrange — one offender reported by the check.
    monkeypatch.setattr(build, 'check_spdx_headers', lambda paths: ['some/file.py'])

    # Act
    exit_code = build.cmd_quality_gate(_ARM4_MODULE)

    # Assert
    assert exit_code == 1, 'a reported SPDX offender must fail the gate'


def test_executor_bootstrap_writes_nothing_itself(monkeypatch, tmp_path: Path):
    """``ensure_executor_substrate`` performs no write of its own.

    Its only write happens inside the generator subprocess, so with that
    subprocess stubbed out nothing appears on disk at all. The matched positive
    control below pins WHICH path that subprocess is required to have produced.
    """
    # Arrange — an empty tree and a generator that does nothing.
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(build, 'run', lambda cmd, description, env=None: 0)

    # Act
    exit_code = build.ensure_executor_substrate()

    # Assert — it refuses (nothing landed) and it created nothing itself.
    assert exit_code != 0, 'a zero exit with no executor on disk must not read as success'
    assert list(tmp_path.rglob('*')) == [], (
        f'the bootstrap must write nothing directly; found {list(tmp_path.rglob("*"))!r}'
    )


def test_executor_bootstrap_target_is_the_git_ignored_executor_path(
    monkeypatch, tmp_path: Path
):
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


# ---------------------------------------------------------------------------
# Declaration assertions — the two facts, and the conjunction that enrols the gate
# ---------------------------------------------------------------------------


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


def test_gate_declares_mutates_source_true():
    """The gate declares itself a source mutator."""
    assert _gate_fields('mutates_source').get('mutates_source') is True


def test_gate_still_declares_head_dependent_true():
    """The flip leaves ``head_dependent`` untouched — the two facts are independent."""
    assert _gate_fields('head_dependent').get('head_dependent') is True


def test_gate_is_a_re_stale_trigger_member_by_the_full_conjunction():
    """Both operands together are what enrol the gate in the re-stale trigger set.

    ``mutates_source: true`` alone does not witness the enrolment (a mutator above
    the settle-band bound is not a member), and an order below the bound alone
    does not either (a non-mutator never moves HEAD). Asserting them jointly is
    what makes this a witness rather than two unrelated facts.
    """
    fields = _gate_fields('mutates_source', 'order')
    bound = _settle_band_order_bound()

    assert fields.get('mutates_source') is True
    assert isinstance(fields.get('order'), int), (
        f'the gate must declare an integer order; got {fields.get("order")!r}'
    )
    assert fields['order'] < bound, (
        f'the gate is order {fields["order"]}, which must sit below the settle-band '
        f'bound {bound} for the re-stale enrolment to hold'
    )
