# SPDX-License-Identifier: FSL-1.1-ALv2
"""Single-source decoder for ``git status --porcelain -z`` output.

Two guards observe working-tree dirtiness and then compare what they observed
against a git-tracked path set:

- the post-run source guard (``phase-6-finalize/scripts/post_run_source_guard.py``), and
- the layer-D main-checkout drift capture (via
  ``plan-marshall/scripts/_git_helpers.py``'s ``git_dirty_files``, consumed by
  ``plan-marshall/scripts/_invariants.py``).

Both must speak ONE path encoding, because both compare their observation against
the tracked set from
:func:`_plan_state_exemption.tracked_plan_paths`, which reads NUL-delimited git
output. The default (un-``-z``) porcelain line form does not qualify: git *quotes
and C-escapes* a path containing a space-adjacent special character, a double
quote, a backslash, a control character, or a non-ASCII byte. Stripping the
surrounding quotes without unescaping — the previous behaviour on the drift side —
yields a spelling that never string-matches the tracked set, so a tracked
``.plan/`` file git chose to quote slipped the comparison entirely.

``-z`` removes the question rather than configuring it away: in NUL-delimited mode
git emits every path verbatim, with no quoting and no escaping, for every byte
sequence a path can contain. That is strictly stronger than
``-c core.quotePath=false``, which only suppresses the ``\\NNN`` escaping of
non-ASCII bytes and still quotes a path containing a double quote, a backslash, or
a control character. ``-z`` also disambiguates renames structurally — the original
path is its own NUL-terminated field rather than an ``orig -> dest`` infix that a
path containing the literal ``" -> "`` would corrupt.

The decoder lives here, at the ``script-shared/scripts/`` top level, so both
consuming bundles import it by bare name
(``from _porcelain import parse_porcelain_z``) and there is ONE implementation
rather than two copies — the same "one predicate, not two copies" rule that put
the ``.plan/`` exemption in :mod:`_plan_state_exemption`.

Pure and stdlib-only: this module decodes a payload and does no I/O.
"""

from __future__ import annotations

#: Porcelain status letters that introduce a second (original) path field in
#: ``-z`` output: rename and copy. Both sides are reported, because either one
#: being a tracked source path means tracked source moved.
_TWO_PATH_STATUSES: frozenset[str] = frozenset({'R', 'C'})


def parse_porcelain_z(payload: str) -> list[str]:
    """Extract the dirty paths from ``git status --porcelain -z`` output.

    Args:
        payload: Raw stdout of ``git status --porcelain -z …``. Each record is
            ``XY<space><path>\\0``; a rename/copy record is followed by one
            additional ``<original-path>\\0`` field.

    Returns:
        Every path named by the payload, in payload order, with both sides of a
        rename/copy record included. Deduplication and prefix filtering are the
        caller's concern — this function only decodes.
    """
    fields = [field for field in payload.split('\0') if field]
    paths: list[str] = []
    index = 0
    while index < len(fields):
        record = fields[index]
        index += 1
        if len(record) < 4:
            # Not a well-formed ``XY<space><path>`` record — skip it rather
            # than guessing at a path that would become a phantom offender.
            continue
        status, path = record[:2], record[3:]
        paths.append(path)
        if _TWO_PATH_STATUSES & set(status):
            if index < len(fields):
                paths.append(fields[index])
                index += 1
    return paths


__all__ = ['parse_porcelain_z']
