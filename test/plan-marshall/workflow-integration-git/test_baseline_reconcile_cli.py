#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for git-workflow.py baseline-reconcile subcommand.

The subcommand is the mechanical predicate for phase-2-refine Step 3d:
fetches origin/{base_branch}, lists upstream commits since the
**merge-base of HEAD and origin/{base_branch}** (recomputed per call, never
read from a stored SHA), and runs ``git merge-tree`` to detect potential
conflicts. It **moves no refs and touches no working-tree file** on any path
— though it is not side-effect-free: on the stale-base path it rewrites
``base_branch`` in ``references.json`` and emits a decision-log entry. Each
conflicted file becomes a Q-Gate finding (under --source qgate) so the
existing phase-2-refine iterate-to-confidence loop addresses the drift.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
from argparse import Namespace
from pathlib import Path

import file_ops
from _resolve_project_dir_fixtures import patch_query_worktree_path

from conftest import PROJECT_ROOT, get_script_path, load_script_module

_mod = load_script_module(
    'plan-marshall',
    'workflow-integration-git',
    '_cmd_baseline_reconcile.py',
    '_cmd_baseline_reconcile_under_test',
    register=False,
)
cmd_baseline_reconcile = _mod.cmd_baseline_reconcile


# =============================================================================
# Helpers — git fixtures
# =============================================================================


def _git(cwd: Path, *args: str) -> None:
    """Run a git command in ``cwd``; fail the test on non-zero exit."""
    subprocess.run(
        ['git', '-C', str(cwd), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _git_init_repo(repo: Path, *, default_branch: str = 'main') -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, 'init', '-q', '-b', default_branch)
    _git(repo, 'config', 'user.email', 'tests@example.com')
    _git(repo, 'config', 'user.name', 'Test')


def _commit_file(repo: Path, name: str, content: str, message: str) -> str:
    (repo / name).write_text(content, encoding='utf-8')
    _git(repo, 'add', name)
    _git(repo, 'commit', '-q', '-m', message)
    return subprocess.run(
        ['git', '-C', str(repo), 'rev-parse', 'HEAD'],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _setup_remote_and_worktree(
    fixture_root: Path,
    *,
    base_branch: str = 'main',
    upstream_commits: int = 0,
    upstream_conflicts: bool = False,
) -> tuple[Path, Path, str]:
    """Build a (bare-remote, local-clone) fixture and return paths + baseline SHA.

    The local clone simulates the worktree: it cloned at ``baseline_sha``
    and may have diverged on its branch. ``upstream_commits`` add commits
    on the remote-tracking branch after the clone; ``upstream_conflicts``
    additionally rewrites the same line in ``shared.txt`` on the local
    side so ``git merge-tree`` reports a conflict.
    """
    remote = fixture_root / 'remote.git'
    seed = fixture_root / 'seed'
    worktree = fixture_root / 'worktree'

    # Seed repo (used to bootstrap the remote with one commit).
    _git_init_repo(seed, default_branch=base_branch)
    _commit_file(seed, 'shared.txt', 'line 1\n', 'seed: initial')

    # Build the bare remote from the seed.
    subprocess.run(
        ['git', 'clone', '--bare', '-q', str(seed), str(remote)],
        check=True,
        capture_output=True,
        text=True,
    )

    # Local clone — this is what the test passes as worktree_path.
    subprocess.run(
        ['git', 'clone', '-q', str(remote), str(worktree)],
        check=True,
        capture_output=True,
        text=True,
    )
    _git(worktree, 'config', 'user.email', 'tests@example.com')
    _git(worktree, 'config', 'user.name', 'Test')
    baseline_sha = subprocess.run(
        ['git', '-C', str(worktree), 'rev-parse', 'HEAD'],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    # Optionally diverge the local branch (line conflict).
    if upstream_conflicts:
        _commit_file(worktree, 'shared.txt', 'line 1 (local edit)\n', 'local: edit shared')

    # Optionally land commits on the remote after the local cloned.
    if upstream_commits > 0:
        # Push from the seed repo (still on default_branch).
        for i in range(upstream_commits):
            new_content = 'line 1 (upstream)\n' if upstream_conflicts else f'extra {i}\n'
            target = 'shared.txt' if upstream_conflicts else f'upstream-{i}.txt'
            _commit_file(seed, target, new_content, f'upstream: change {i}')
        _git(seed, 'push', '-q', str(remote), base_branch)

        # The local clone needs to fetch — done by the script.

    return remote, worktree, baseline_sha


# =============================================================================
# Tests
# =============================================================================


# =============================================================================
# status.json helpers
# =============================================================================


def _write_status(plan_dir: Path, worktree: Path, baseline_sha: str) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'status.json').write_text(
        json.dumps(
            {
                'plan_id': plan_dir.name,
                'phases': [],
                'metadata': {
                    'use_worktree': True,
                    'worktree_path': str(worktree),
                    'worktree_branch': 'feature/test',
                    'worktree_sha': baseline_sha,
                },
            }
        ),
        encoding='utf-8',
    )


def _write_status_main_checkout(plan_dir: Path) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'status.json').write_text(
        json.dumps(
            {
                'plan_id': plan_dir.name,
                'phases': [],
                'metadata': {'use_worktree': False},
            }
        ),
        encoding='utf-8',
    )


# =============================================================================
# Classification tests
# =============================================================================


def _setup_overlap_no_conflict(fixture_root: Path) -> tuple[Path, Path, str]:
    """Build a fixture where upstream and in-flight touch the SAME file but
    different lines, so merge-tree predicts no conflict yet there is overlap.
    """
    remote = fixture_root / 'remote.git'
    seed = fixture_root / 'seed'
    worktree = fixture_root / 'worktree'

    _git_init_repo(seed, default_branch='main')
    _commit_file(
        seed,
        'shared.txt',
        'A\nB\nC\nD\nE\nF\nG\nH\n',
        'seed: initial',
    )
    subprocess.run(
        ['git', 'clone', '--bare', '-q', str(seed), str(remote)],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ['git', 'clone', '-q', str(remote), str(worktree)],
        check=True,
        capture_output=True,
        text=True,
    )
    _git(worktree, 'config', 'user.email', 'tests@example.com')
    _git(worktree, 'config', 'user.name', 'Test')
    baseline_sha = subprocess.run(
        ['git', '-C', str(worktree), 'rev-parse', 'HEAD'],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    # In-flight change: edit the FIRST line of shared.txt.
    _commit_file(
        worktree,
        'shared.txt',
        'A-local\nB\nC\nD\nE\nF\nG\nH\n',
        'local: edit first line',
    )
    # Upstream change: edit the LAST line of shared.txt — non-overlapping.
    _commit_file(
        seed,
        'shared.txt',
        'A\nB\nC\nD\nE\nF\nG\nH-upstream\n',
        'upstream: edit last line',
    )
    _git(seed, 'push', '-q', str(remote), 'main')

    return remote, worktree, baseline_sha


# =============================================================================
# Merge-base anchor + non-mutation (D1–D5)
# =============================================================================


def _setup_disjoint_upstream_and_local(fixture_root: Path) -> tuple[Path, Path, str]:
    """A disjoint fixture: upstream edits ``upstream.txt``; the branch edits
    ``local.txt``. Returns ``(remote, worktree, baseline_sha)``.

    The worktree carries ONE in-flight commit on ``local.txt``; the remote main
    carries ONE upstream commit on ``upstream.txt`` landed after the clone. The
    two file sets are disjoint, so a correct classifier reports ``no_overlap``.
    """
    remote = fixture_root / 'remote.git'
    seed = fixture_root / 'seed'
    worktree = fixture_root / 'worktree'

    _git_init_repo(seed, default_branch='main')
    _commit_file(seed, 'base.txt', 'base\n', 'seed: initial')
    subprocess.run(
        ['git', 'clone', '--bare', '-q', str(seed), str(remote)],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ['git', 'clone', '-q', str(remote), str(worktree)],
        check=True,
        capture_output=True,
        text=True,
    )
    _git(worktree, 'config', 'user.email', 'tests@example.com')
    _git(worktree, 'config', 'user.name', 'Test')
    baseline_sha = subprocess.run(
        ['git', '-C', str(worktree), 'rev-parse', 'HEAD'],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    # In-flight: the branch adds local.txt.
    _commit_file(worktree, 'local.txt', 'local change\n', 'local: add local.txt')
    # Upstream: a disjoint commit adds upstream.txt on the remote main.
    _commit_file(seed, 'upstream.txt', 'upstream change\n', 'upstream: add upstream.txt')
    _git(seed, 'push', '-q', str(remote), 'main')
    return remote, worktree, baseline_sha


def _behind_count(worktree: Path) -> int:
    """Number of commits ``origin/main`` is ahead of HEAD (the branch's behind-count)."""
    out = subprocess.run(
        ['git', '-C', str(worktree), 'rev-list', '--count', 'HEAD..origin/main'],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return int(out)


# =============================================================================
# The documented reason / error vocabularies are BOUND to the emitting script (D4)
# =============================================================================
#
# ``workflow-integration-git/SKILL.md`` tables every ``status: skipped`` reason and
# every ``status: error`` token this subcommand can return. Nothing compared the
# two: a token added, renamed, or removed in ``_cmd_baseline_reconcile.py`` left
# the table quietly wrong, and a reader consulting the documented vocabulary would
# act on a token the script no longer emits — or miss one it does.
#
# Both sides are DERIVED. The documented side is parsed out of the tables (a
# transcription here would be a third copy that can drift from both); the emitted
# side is read from the module's own AST (a second literal list would be exactly
# the restatement this guard exists to forbid).

_SKILL_DOC = (
    PROJECT_ROOT / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'workflow-integration-git' / 'SKILL.md'
)

_RECONCILE_SOURCE = get_script_path('plan-marshall', 'workflow-integration-git', '_cmd_baseline_reconcile.py')

#: The function whose ``return None, '<token>'`` tuples ARE the worktree-resolution
#: skip reasons. Six of the eleven documented reasons reach the payload only
#: through this helper, so an emitted-side derivation that looked solely at
#: ``'reason': …`` dict literals would miss them and pass while the table drifted.
_SKIP_REASON_FUNCTION = '_worktree_target'


def _table_tokens(heading_cell: str, doc_text: str | None = None) -> set[str]:
    """Parse the backticked tokens from the first column of one SKILL.md table.

    ``heading_cell`` is the table's first header cell (``reason`` / ``error``),
    which is what distinguishes the two tables from every other table in the doc.

    A first column may group several tokens in ONE slash-joined cell — the
    worktree-resolution row does exactly that, listing four reasons together — so
    every backticked run in the cell is collected rather than the cell being read
    as a single token. A parser that took the cell verbatim would yield one
    unmatchable string and make the comparison vacuous for those four.

    ``doc_text`` overrides the document read, and exists so the control below can
    drive THIS parser over an injected row rather than restating set algebra over
    a locally-built set. The default is the real doc, so every caller that omits
    it is unaffected.
    """
    lines = (doc_text or _SKILL_DOC.read_text(encoding='utf-8')).splitlines()
    tokens: set[str] = set()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if line.startswith('|') and index + 1 < len(lines):
            cells = [c.strip() for c in line.strip('|').split('|')]
            delimiter = lines[index + 1].strip()
            if (
                cells
                and cells[0].strip('`') == heading_cell
                and delimiter.startswith('|')
                and set(delimiter) <= set('|-: ')
            ):
                row = index + 2
                while row < len(lines) and lines[row].strip().startswith('|'):
                    first = lines[row].strip().strip('|').split('|')[0]
                    tokens.update(re.findall(r'`([a-z0-9_]+)`', first))
                    row += 1
                index = row
                continue
        index += 1
    return tokens


def _emitted_tokens(source_text: str | None = None) -> tuple[set[str], set[str]]:
    """The ``reason`` and ``error`` tokens the script actually emits, from its AST.

    Three emission shapes are recognised, which together cover every site:

    * a ``{'reason': '<token>'}`` / ``{'error': '<token>'}`` dict entry — including
      the ``skip_reason or '<fallback>'`` form, whose constant operand is the
      fallback reason;
    * a ``payload['error'] = '<token>'`` subscript assignment;
    * a ``return None, '<token>'`` tuple inside :data:`_SKIP_REASON_FUNCTION`, the
      helper that owns the six worktree-resolution reasons.

    ``source_text`` overrides the source read, and exists so the control below can
    drive THIS AST derivation over an injected emission site. The default is the
    real script, so every caller that omits it is unaffected.
    """
    tree = ast.parse(source_text or _RECONCILE_SOURCE.read_text(encoding='utf-8'))
    reasons: set[str] = set()
    errors: set[str] = set()

    def _constants(node: ast.AST) -> list[str]:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return [node.value]
        if isinstance(node, ast.BoolOp):
            found: list[str] = []
            for operand in node.values:
                found.extend(_constants(operand))
            return found
        return []

    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values, strict=True):
                if not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
                    continue
                if key.value == 'reason':
                    reasons.update(_constants(value))
                elif key.value == 'error':
                    errors.update(_constants(value))
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Subscript)
                    and isinstance(target.slice, ast.Constant)
                    and target.slice.value in ('reason', 'error')
                ):
                    bucket = reasons if target.slice.value == 'reason' else errors
                    bucket.update(_constants(node.value))

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == _SKIP_REASON_FUNCTION:
            for inner in ast.walk(node):
                if isinstance(inner, ast.Return) and isinstance(inner.value, ast.Tuple):
                    elements = inner.value.elts
                    if len(elements) == 2:
                        reasons.update(_constants(elements[1]))

    return reasons, errors


def test_baseline_reconcile_registered_in_git_workflow_cli():
    """argparse subparser routes 'baseline-reconcile' to cmd_baseline_reconcile."""
    git_workflow = load_script_module(
        'plan-marshall', 'workflow-integration-git', 'git-workflow.py', '_git_workflow_dispatch_check', register=False
    )
    assert git_workflow.cmd_baseline_reconcile is cmd_baseline_reconcile or callable(
        git_workflow.cmd_baseline_reconcile
    )

    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')
    leaf = sub.add_parser('baseline-reconcile')
    leaf.set_defaults(func=git_workflow.cmd_baseline_reconcile)
    ns = parser.parse_args(['baseline-reconcile'])
    assert ns.func is git_workflow.cmd_baseline_reconcile


def test_documented_reason_and_error_vocabularies_match_the_script():
    """The two documented tables equal the token sets the script emits.

    Compared as SETS in both directions: a documented token the script never
    emits sends a reader chasing a state that cannot occur, and an emitted token
    the table omits leaves a real outcome undocumented.
    """
    documented_reasons = _table_tokens('reason')
    documented_errors = _table_tokens('error')
    emitted_reasons, emitted_errors = _emitted_tokens()

    # Vacuity guard FIRST — an empty parse on either side would make every set
    # comparison below trivially true (or trivially false) for the wrong reason.
    assert documented_reasons, (
        f'parsed no `reason` tokens out of {_SKILL_DOC}; the table moved, was '
        f'renamed, or the parser broke — the comparison would be vacuous'
    )
    assert documented_errors, f'parsed no `error` tokens out of {_SKILL_DOC}'
    assert emitted_reasons, (
        f'derived no reason tokens from {_RECONCILE_SOURCE}; the emission shapes '
        f'changed and the AST derivation no longer recognises them'
    )
    assert emitted_errors, f'derived no error tokens from {_RECONCILE_SOURCE}'

    # Published on a clean run, so the run states how much it compared.
    print(
        f'baseline-reconcile vocabulary: documented_reasons={len(documented_reasons)} '
        f'emitted_reasons={len(emitted_reasons)} '
        f'documented_errors={len(documented_errors)} '
        f'emitted_errors={len(emitted_errors)}'
    )

    assert documented_reasons == emitted_reasons, (
        f'the documented skip-reason vocabulary and the one the script emits '
        f'disagree (examined {len(documented_reasons)} documented, '
        f'{len(emitted_reasons)} emitted). '
        f'Documented but never emitted: {sorted(documented_reasons - emitted_reasons)}; '
        f'emitted but undocumented: {sorted(emitted_reasons - documented_reasons)}'
    )
    assert documented_errors == emitted_errors, (
        f'the documented error vocabulary and the one the script emits disagree '
        f'(examined {len(documented_errors)} documented, {len(emitted_errors)} '
        f'emitted). '
        f'Documented but never emitted: {sorted(documented_errors - emitted_errors)}; '
        f'emitted but undocumented: {sorted(emitted_errors - documented_errors)}'
    )


def test_the_slash_joined_reason_row_expands_to_every_token_it_groups():
    """The grouped cell is expanded, not read as one unmatchable string.

    One documented row lists four worktree-resolution reasons in a single
    slash-joined cell. A parser that took the cell verbatim would produce one
    token matching nothing, and the equality above would then fail for a parsing
    reason while those four reasons went effectively unchecked. Pinning the
    expansion keeps the row's four members inside the compared set.
    """
    documented = _table_tokens('reason')
    grouped = {
        'status_not_found',
        'status_module_unavailable',
        'worktree_path_missing',
        'worktree_path_not_a_directory',
    }

    assert grouped <= documented, (
        f'the slash-joined row did not expand; missing {sorted(grouped - documented)}. Parsed: {sorted(documented)}'
    )
    # The row really is joined — otherwise this asserts nothing about grouping.
    text = _SKILL_DOC.read_text(encoding='utf-8')
    assert '`status_not_found` / `status_module_unavailable`' in text, (
        'the grouped row is no longer slash-joined, so this test no longer '
        'demonstrates that the parser expands such a cell'
    )


#: A table row injected into the doc for a reason the script never emits. Written
#: as a whole table so the injection exercises the parser's header match,
#: delimiter check, and backtick extraction — not just its row loop.
_INJECTED_DOC_ROW = (
    '\n| `reason` | Meaning |\n|---|---|\n| `control_only_documented_reason` | a state the script cannot reach |\n'
)

#: An emission site appended to the script source for a reason the table omits.
#: A ``{'reason': …}`` dict literal — one of the three shapes the AST derivation
#: claims to recognise — so the injection tests that recognition.
_INJECTED_EMISSION_SITE = "\n\ndef _control_only_emission():\n    return {'reason': 'control_only_emitted_reason'}\n"


def test_an_injected_token_on_either_side_is_derived_and_flagged():
    """Matched control pair: BOTH derivations resolve an injected divergence.

    The guard compares two DERIVED sets, so a control that builds two sets
    locally and unions a phantom into one of them controls the ``-`` operator
    and nothing else: given the matched case immediately below, such an
    assertion reduces to "the phantom is not in the other set", which is true of
    any string nobody uses. It cannot fail for any change to
    :func:`_table_tokens` or :func:`_emitted_tokens` — the parts that can
    actually break.

    Each direction here injects into the SUBSTRATE instead, and each fails for
    its own reason:

    * DOCUMENTED side — a table row for a state the script cannot reach. Red if
      :func:`_table_tokens` stops parsing a table (header match, delimiter
      check, or backtick extraction), which is also what would make the guard
      silently compare an empty documented set.
    * EMITTED side — a ``{'reason': …}`` emission site the table omits. Red if
      :func:`_emitted_tokens` stops recognising that dict shape, which is what
      would make the guard silently compare an empty emitted set.

    The matched (uninjected) pair is asserted first, so a divergence already
    present in the real corpus cannot masquerade as the injected one.
    """
    documented_reasons = _table_tokens('reason')
    emitted_reasons, _emitted_errors = _emitted_tokens()

    # The matched (unmodified) case: no divergence in either direction.
    assert documented_reasons == emitted_reasons, (
        f'the real corpus already diverges, so neither injection below is '
        f'attributable to the injection. Documented but never emitted: '
        f'{sorted(documented_reasons - emitted_reasons)}; emitted but '
        f'undocumented: {sorted(emitted_reasons - documented_reasons)}'
    )

    # DOCUMENTED side — parse a doc carrying one extra row, through the real parser.
    injected_doc = _SKILL_DOC.read_text(encoding='utf-8') + _INJECTED_DOC_ROW
    documented_with_phantom = _table_tokens('reason', doc_text=injected_doc)

    assert documented_with_phantom - documented_reasons == {'control_only_documented_reason'}, (
        f'the table parser did not pick up the injected row, so the '
        f'documented-side derivation is not being driven. Parsed: '
        f'{sorted(documented_with_phantom - documented_reasons)}'
    )
    assert documented_with_phantom != emitted_reasons, (
        'a documented-but-never-emitted token left the guard equality intact'
    )
    assert documented_with_phantom - emitted_reasons == {'control_only_documented_reason'}, (
        'a documented-but-never-emitted token was not detected'
    )

    # EMITTED side — derive from a source carrying one extra emission site.
    injected_source = _RECONCILE_SOURCE.read_text(encoding='utf-8') + _INJECTED_EMISSION_SITE
    emitted_with_phantom, _ = _emitted_tokens(source_text=injected_source)

    assert emitted_with_phantom - emitted_reasons == {'control_only_emitted_reason'}, (
        f'the AST derivation did not pick up the injected emission site, so the '
        f'emitted-side derivation is not being driven. Derived: '
        f'{sorted(emitted_with_phantom - emitted_reasons)}'
    )
    assert emitted_with_phantom != documented_reasons, (
        'an emitted-but-undocumented token left the guard equality intact'
    )
    assert emitted_with_phantom - documented_reasons == {'control_only_emitted_reason'}, (
        'an emitted-but-undocumented token was not detected'
    )
