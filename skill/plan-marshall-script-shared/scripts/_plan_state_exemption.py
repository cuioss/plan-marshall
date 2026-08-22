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

This module does I/O (one ``git ls-files`` per partition) and is stdlib-only. It
lives at the ``script-shared/scripts/`` top level so every consuming bundle imports
it by bare name (``from _plan_state_exemption import partition_plan_state_exemption``).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

#: Path prefix whose entries MAY be plan-state bookkeeping. A path under it is
#: exempt only when it is additionally NOT git-tracked (see module docstring); the
#: prefix alone is not sufficient, which is the defect this module corrects.
_PLAN_STATE_PREFIX: str = '.plan/'

#: Seconds allowed for the single ``git ls-files`` trackedness observation.
_GIT_TIMEOUT_SECONDS: int = 60


def is_plan_state_path(path: str) -> bool:
    """Whether ``path`` lies under the ``.plan/`` state prefix.

    Prefix membership only — it says nothing about trackedness, which
    :func:`partition_plan_state_exemption` resolves against a real tree.
    """
    return path.startswith(_PLAN_STATE_PREFIX)


def tracked_plan_paths(tree: str | Path) -> set[str] | None:
    """Return the set of git-tracked paths under ``.plan/`` in ``tree``.

    Runs one ``git ls-files -z -- .plan/`` against ``tree`` (which must be the
    repository root the dirty paths were observed against, so its output is
    root-relative and directly comparable to the porcelain paths). Returns the
    tracked ``.plan/`` path set on success, or ``None`` when the observation could
    not run (not a git repository, git unavailable, non-zero exit) — the caller
    treats ``None`` as "trackedness unknown" and fails closed by retaining.

    Args:
        tree: Working-tree / repository root to observe.

    Returns:
        The tracked ``.plan/`` path set, or ``None`` on an unusable observation.
    """
    try:
        completed = subprocess.run(
            ['git', '-C', str(tree), 'ls-files', '-z', '--', _PLAN_STATE_PREFIX],
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return {entry for entry in completed.stdout.split('\0') if entry}


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
