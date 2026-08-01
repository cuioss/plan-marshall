#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared parser-derived population of a subcommand's ``--*-bots`` list flags.

Three regression suites need the SAME population — the set of ``--*-bots`` flags
a given argparse subcommand actually declares — and each needs it derived from
the live parser rather than restated as a literal:

* ``automatic-review/test_bot_participation_contract.py`` sweeps every
  documented invocation for unquoted placeholders, and builds its scan regex
  from the flag set.
* ``automatic-review/test_review_completeness.py`` and
  ``workflow-integration-github/test_github_pr.py`` sweep every flag's BARE
  form against the parser that must accept it.

A literal table in each suite would leave a newly added flag covered by none of
them while all three still reported clean, so the derivation — not the flag
list — is the thing that must be shared. This module is its single
implementation; the suites differ only in which ``(script, subcommand)`` parser
they interrogate, which is exactly what the parameters carry.

This file is intentionally a sibling helper and is NOT a ``conftest.py`` —
a second ``conftest.py`` under ``test/`` would shadow the top-level
``test/conftest.py`` and disable the shared autouse isolation fixtures.
"""

from __future__ import annotations

import re
from pathlib import Path

from conftest import run_script

#: A list flag of the ``--*-bots`` family, as argparse renders it in ``--help``.
_BOT_FLAG = re.compile(r'--[a-z][a-z-]*-bots\b')


def derive_bot_flags(script_path: str | Path, subcommand: str) -> tuple[tuple[str, str], ...]:
    """Return ``(flag, dest)`` for every ``--*-bots`` flag the LIVE parser declares.

    Read off the subcommand's own ``--help`` rendering, so a flag added to the
    script inherits its consumers' coverage instead of silently escaping it.

    Declaration order is preserved (argparse renders the usage line in
    declaration order, and ``dict.fromkeys`` dedupes on first appearance), so a
    caller may rely on positional grouping — e.g. the ``fetch_findings``
    family's two classification flags remaining the leading pair of the
    ``check`` family's wider set.

    ``dest`` follows argparse's own inference rule — strip the leading ``--``
    and map ``-`` to ``_`` — so a flag that overrode ``dest`` explicitly fails
    loudly at the consuming ``getattr`` rather than passing quietly.

    Args:
        script_path: The script whose parser is interrogated.
        subcommand: The subcommand whose ``--help`` declares the flags.

    Returns:
        ``(flag, dest)`` pairs in parser declaration order.

    Raises:
        AssertionError: if the parser could not be interrogated, or if the
            derivation matched no flag at all. An empty derivation is the
            vacuity this guard exists to catch: every population consuming it
            would parametrize over an empty set and pass without checking
            anything.
    """
    result = run_script(script_path, subcommand, '--help')
    assert result.success, result.stderr

    flags = tuple(dict.fromkeys(_BOT_FLAG.findall(result.stdout)))
    assert flags, (
        f'no --*-bots flag was derived from the live {subcommand} parser at '
        f'{script_path} — the derivation is vacuous and every population that '
        f'consumes it would pass over an empty set. usage was: {result.stdout}'
    )
    return tuple((flag, flag[2:].replace('-', '_')) for flag in flags)
