# SPDX-License-Identifier: FSL-1.1-ALv2
"""Single-source ``.plan/`` dirty-source exemption predicate, keyed on git trackedness.

Two independent finalize-band guards observe working-tree dirtiness to decide
whether a step left an **unpushable tracked-source edit** behind, and each must
exempt the ordinary plan-state writes every step makes under ``.plan/``:

- the post-run source guard (``phase-6-finalize/scripts/post_run_source_guard.py``),
  consulted once per ``post_run_review`` step return, and
- the layer-D main-checkout drift capture (``plan-marshall/scripts/_invariants.py``),
  captured at every phase boundary.

Both used to exempt on a bare ``.plan/`` path prefix. That is wrong, because a
number of files under ``.plan/`` **are git-tracked** — ``marshal.json`` and every
``project-architecture/**/enriched.json`` architecture descriptor — so the prefix
drop hid exactly the paths where an unpushable tracked edit is most likely (an
architecture-enrich write at finalize). Two copies of one wrong rule is how the
second guard stayed live after the first was noticed, so the corrected rule lives
here **once** and both guards call it.

The corrected rule: a ``.plan/`` path is exempt **only when it is NOT git-tracked**
in the observed tree; a *tracked* ``.plan/`` file is retained and reported like any
other tracked source. A path outside ``.plan/`` is never exempted by this predicate
(each guard keeps its own treatment of non-``.plan/`` paths). When trackedness
cannot be determined (the tree is not a repository, git is unavailable), the
``.plan/`` candidates are **retained**, never exempted — the guards exist to surface
possibly-unpushable tracked edits, so an unusable trackedness answer must not
manufacture a silent exemption.

"Tracked" means **in the index OR at HEAD**, not in the index alone. A *staged
deletion* of a tracked ``.plan/`` file removes it from the index while it is still
committed at HEAD; an index-only oracle answers "untracked" and exempts exactly the
edit the guards exist to surface. Unioning the two observations makes the oracle
answer the question the guards ask — "is this file part of the repository?" — rather
than the narrower "is this file staged right now?".

The union is only as good as BOTH halves, so an unusable HEAD half fails closed too.
Falling back to the index answer whenever the HEAD observation fails would silently
restore the index-only oracle on exactly the staged-deletion case above. The one
legitimate exception is a repository holding NO COMMIT AT ALL, where nothing can be
committed and the index answer really is complete; :func:`tracked_plan_paths` tells
that state apart with :func:`_repository_is_unborn` rather than inferring it from the
failure. The discriminator asks about commits rather than about HEAD because whether
HEAD resolves is three-valued, and the two states it cannot separate — an unborn
repository and an orphan branch — need OPPOSITE answers.

This module does I/O (two NUL-delimited git observations per partition) and is
stdlib-only. It lives at the ``script-shared/scripts/`` top level so every consuming
bundle imports it by bare name
(``from _plan_state_exemption import partition_plan_state_exemption``).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

#: Path prefix whose entries MAY be plan-state bookkeeping. A path under it is
#: exempt only when it is additionally NOT git-tracked (see module docstring); the
#: prefix alone is not sufficient, which is the defect this module corrects.
_PLAN_STATE_PREFIX: str = '.plan/'

#: Seconds allowed for each git trackedness observation.
_GIT_TIMEOUT_SECONDS: int = 60


def is_plan_state_path(path: str) -> bool:
    """Whether ``path`` lies under the ``.plan/`` state prefix.

    Prefix membership only — it says nothing about trackedness, which
    :func:`partition_plan_state_exemption` resolves against a real tree.
    """
    return path.startswith(_PLAN_STATE_PREFIX)


def _observe_z(tree: str | Path, git_args: list[str]) -> set[str] | None:
    """Run one NUL-delimited git observation against ``tree``.

    The ``-z`` form is used by every caller so paths arrive verbatim — git applies
    no shell-style quoting or escaping there, which is what makes the returned set
    directly comparable to a ``git status --porcelain -z`` path.

    Args:
        tree: Working-tree / repository root to observe.
        git_args: The git command and its arguments, without the leading
            ``git -C <tree>``.

    Returns:
        The set of non-empty NUL-separated entries, or ``None`` when the
        observation could not run or exited non-zero.

    The decode is ``surrogateescape``, matching the porcelain observation these
    paths are compared against (``_git_helpers.git_dirty_files``,
    ``post_run_source_guard._observe_dirty_source``). It is load-bearing on both
    counts: a strict decode raises ``UnicodeDecodeError`` on a path carrying a
    byte that is not valid UTF-8 — a ``ValueError``, so outside the
    ``(OSError, SubprocessError)`` tuple below, escaping uncaught instead of
    yielding the ``None`` this function documents — and a decode that differed
    from the other side's would make the ``path in tracked`` comparison miss for
    exactly those paths, which is the failure ``-z`` was adopted to end.
    """
    try:
        completed = subprocess.run(
            ['git', '-C', str(tree), *git_args],
            capture_output=True,
            encoding='utf-8',
            errors='surrogateescape',
            timeout=_GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return {entry for entry in completed.stdout.split('\0') if entry}


def _observe_lines(tree: str | Path, git_args: list[str]) -> set[str]:
    """Run one NEWLINE-delimited git observation against ``tree``.

    Separate from :func:`_observe_z` rather than a flag on it, because the two
    answer different questions and :func:`_observe_z` documents the ``-z`` form as
    what makes its output directly comparable to a porcelain path. This helper is
    for observations whose output is a sha or ref rather than a path — nothing
    here is compared against a porcelain path, so there is no quoting hazard to
    defend against and no reason to claim the ``-z`` guarantee.

    An unusable observation returns a NON-empty sentinel set, which is the
    fail-closed direction for its only caller: :func:`_repository_is_unborn`
    treats a non-empty result as "commits exist", so an unusable probe must not
    be able to manufacture the unborn verdict.
    """
    try:
        completed = subprocess.run(
            ['git', '-C', str(tree), *git_args],
            capture_output=True,
            encoding='utf-8',
            errors='surrogateescape',
            timeout=_GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return {'<unusable-observation>'}
    if completed.returncode != 0:
        return {'<unusable-observation>'}
    return {entry for entry in completed.stdout.splitlines() if entry.strip()}


def _repository_is_unborn(tree: str | Path) -> bool:
    """Whether ``tree`` holds NO commit at all — the one legitimate no-HEAD state.

    The discriminator between the two situations a failing HEAD observation can
    mean, and it asks about COMMITS rather than about HEAD on purpose. Whether
    HEAD resolves is a three-valued observable — it resolves, it is absent
    because nothing was ever committed, or it is readable but points nowhere —
    and ``git rev-parse --verify --quiet HEAD`` collapses the last two into one
    non-zero exit. ``git checkout --orphan`` produces exactly that third state on
    an everyday branch: the repository HAS commits, so an index-only answer is
    NOT complete, yet a HEAD-resolution probe reports the same non-zero as a
    fresh ``git init``. Reading that binary as "unborn" resolves an orphan branch
    fail-OPEN and exempts the staged deletion this module exists to retain.

    ``git rev-list -n 1 --all`` answers the question actually needed: it prints a
    sha when any ref reaches any commit and prints nothing in a genuinely unborn
    repository, so an empty result is the only state in which the index answer is
    the complete one.

    A probe that cannot run at all reads as NOT unborn — the fail-closed
    direction. That case never reaches a decision anyway:
    :func:`tracked_plan_paths` only probes after ``ls-files`` has already
    succeeded against the same tree, so git is present and the tree is a
    repository by the time this is called.
    """
    return not _observe_lines(tree, ['rev-list', '-n', '1', '--all'])


def tracked_plan_paths(tree: str | Path) -> set[str] | None:
    """Return the set of git-tracked paths under ``.plan/`` in ``tree``.

    "Tracked" is the UNION of two observations against ``tree`` (which must be the
    repository root the dirty paths were observed against, so both outputs are
    root-relative and directly comparable to the porcelain paths):

    - ``git ls-files -z -- .plan/`` — what the INDEX holds, and
    - ``git ls-tree -r -z --name-only HEAD -- .plan/`` — what HEAD holds.

    The union is load-bearing. A *staged deletion* of a tracked ``.plan/`` file
    leaves the index without it while HEAD still carries it; an index-only answer
    would report it untracked and :func:`partition_plan_state_exemption` would
    exempt it — silently hiding the very edit the guards exist to surface. Reading
    HEAD as well makes the oracle answer "is this file part of the repository?".

    ``None`` — "trackedness unknown", which the caller resolves by retaining — is
    returned on an unusable observation of EITHER half:

    - ``ls-files`` fails (not a git repository, git unavailable, non-zero exit); or
    - ``ls-tree`` fails in a repository that HOLDS ANY COMMIT.

    The second condition is why the HEAD half needs the
    :func:`_repository_is_unborn` probe. ``_observe_z`` returns ``None`` for more
    than one situation, and the branch cannot tell them apart from that value
    alone. Only ONE of them makes the index answer complete — a repository with no
    commit anywhere — and every other, including an orphan branch whose HEAD points
    at nothing while commits exist, leaves the index answer narrower than the truth.
    Substituting it there resolves the failure in the fail-OPEN direction:
    concretely, a *staged deletion* of a committed ``.plan/`` file is absent from
    the index, so an index-only answer classifies it untracked and
    :func:`partition_plan_state_exemption` exempts it — hiding exactly the edit the
    guards exist to surface, which is the failure this module was written to end.
    Probing for commits rather than for HEAD is what makes the carve-out cover the
    legitimate case ONLY.

    Args:
        tree: Working-tree / repository root to observe.

    Returns:
        The tracked ``.plan/`` path set, or ``None`` on an unusable observation.
    """
    index = _observe_z(tree, ['ls-files', '-z', '--', _PLAN_STATE_PREFIX])
    if index is None:
        return None
    head = _observe_z(
        tree, ['ls-tree', '-r', '-z', '--name-only', 'HEAD', '--', _PLAN_STATE_PREFIX]
    )
    if head is None:
        if not _repository_is_unborn(tree):
            # The repository HOLDS commits, so the index answer is not complete —
            # whether HEAD failed to resolve (an orphan branch) or the read itself
            # failed. Either way the answer is unusable, not absent. Fail closed
            # rather than silently narrowing trackedness to the index.
            return None
        # No commit anywhere (a genuinely unborn repository): nothing is committed,
        # so the index answer is the complete one and remains usable.
        return index
    return index | head


def partition_plan_state_exemption(
    paths: list[str], tree: str | Path
) -> tuple[list[str], list[str]]:
    """Split observed dirty ``paths`` into ``(retained, exempted)`` against ``tree``.

    A path is **exempted** (dropped) only when it is a ``.plan/`` path CONFIRMED
    NOT git-tracked in ``tree``. Everything else is **retained**: a path outside
    ``.plan/``, and — the correction this module exists for — a ``.plan/`` path
    that IS git-tracked. When the trackedness observation is unusable
    (:func:`tracked_plan_paths` returns ``None``), every ``.plan/`` candidate is
    retained (fail closed — never hide a possibly-tracked edit behind a silent
    exemption).

    Args:
        paths: Repo-relative dirty paths observed against ``tree``.
        tree: The repository root ``paths`` were observed against.

    Returns:
        ``(retained, exempted)``, each sorted and de-duplicated. ``retained`` is
        the dirty-source set the guard acts on; ``exempted`` is the population the
        guard dropped as untracked plan state, published so a clean verdict names
        what it declined to count.
    """
    plan_candidates = [p for p in paths if p and is_plan_state_path(p)]
    tracked = tracked_plan_paths(tree) if plan_candidates else set()

    retained: list[str] = []
    exempted: list[str] = []
    for path in paths:
        if not path:
            continue
        if not is_plan_state_path(path):
            retained.append(path)
        elif tracked is None or path in tracked:
            # Tracked .plan/ source, or an unusable trackedness answer: retain.
            retained.append(path)
        else:
            # Confirmed-untracked .plan/ bookkeeping: exempt.
            exempted.append(path)
    return sorted(set(retained)), sorted(set(exempted))


__all__ = [
    'is_plan_state_path',
    'partition_plan_state_exemption',
    'tracked_plan_paths',
]
