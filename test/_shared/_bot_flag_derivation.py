#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared parser-derived flag populations for an argparse subcommand.

Two entry points read the SAME live ``--help`` rendering and differ only in how
wide a population they derive:

* :func:`derive_bot_flags` — the ``--*-bots`` list-flag FAMILY, each flag paired
  with its argparse ``dest``.
* :func:`derive_declared_flags` — every long option the subcommand declares, so a
  flag of ANY shape is a population member by construction. A valueless
  ``store_true`` such as ``--not-triggered`` carries no value and therefore cannot
  match the family pattern, so the narrow derivation can never surface it: a
  consumer sweeping only the family reports clean while covering none of the
  non-list flags at all.

Three regression suites need the FAMILY — the set of ``--*-bots`` flags a given
argparse subcommand actually declares — and each needs it derived from the live
parser rather than restated as a literal:

* ``automatic-review/test_bot_participation_contract.py`` sweeps every
  documented invocation for unquoted placeholders, and builds its scan regex
  from the flag set. It additionally consumes the WIDER population to assert that
  its own coverage is total over the declared surface rather than over the family
  alone.
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

#: Any long option, as argparse renders it in a usage line. Lowercase-anchored, so
#: a metavar (``PLAN_ID``, ``[REQUIRED_BOTS]``) is never mistaken for a flag.
_LONG_OPTION = re.compile(r'--[a-z][a-z0-9]*(?:-[a-z0-9]+)*')

#: The ``usage:`` block of a ``--help`` rendering: from the ``usage:`` keyword up
#: to the first blank line, wrapped continuation lines included. The full declared
#: option list appears there and only there, which is why the wider derivation
#: reads the usage block rather than the whole page — a flag NAMED inside another
#: flag's help text is prose, not a declaration, and would inflate the population
#: with flags this subcommand does not declare.
_USAGE_BLOCK = re.compile(r'^usage:(?P<usage>.*?)(?:\n[ \t]*\n|\Z)', re.DOTALL | re.MULTILINE)


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


def derive_declared_flags(script_path: str | Path, subcommand: str) -> tuple[str, ...]:
    """Return EVERY long option the LIVE parser declares for ``subcommand``.

    The wider counterpart to :func:`derive_bot_flags`. That one derives one
    FAMILY; this one derives the whole declared optional surface, so a flag of any
    shape is a population member BY CONSTRUCTION rather than by a literal someone
    must remember to append. ``--not-triggered`` is the case that motivated it: a
    ``store_true`` bool has no value, so it cannot match the ``--*-bots`` family
    pattern, and a consumer whose population came from that pattern alone could
    report a clean sweep while the boolean was covered by nothing.

    Derived from the ``usage:`` block rather than the whole ``--help`` page,
    because argparse lists the declared options there and nowhere else — a flag
    mentioned inside another flag's help PROSE is not a declaration of this
    subcommand and must not join the population.

    ``-h`` / ``--help`` is absent by construction rather than by a filter:
    argparse renders each optional in the usage line under its FIRST option
    string, and its own help action declares ``-h`` first, so the builtin appears
    only in a short form this long-option pattern does not match. Should a parser
    ever declare the long form alone, it joins the population and the consuming
    totality assertion fails loudly — which is the correct outcome for an
    unclassified flag, and the reason no exclusion list is kept here.

    Args:
        script_path: The script whose parser is interrogated.
        subcommand: The subcommand whose ``--help`` declares the flags.

    Returns:
        Long-option flags in parser declaration order, deduped on first appearance.
        Callers assert their coverage EQUALS this population and report its
        ``len`` in the failure message, so a population that silently shrank
        surfaces as a number rather than as a clean sweep over a smaller set.

    Raises:
        AssertionError: if the parser could not be interrogated, if the ``usage:``
            block could not be located, or if the derivation matched no flag at
            all. An empty derivation is the vacuity this guard exists to catch:
            every consuming population would sweep an empty set and pass without
            checking anything. The message publishes the derived size alongside
            the usage text it was derived from.
    """
    result = run_script(script_path, subcommand, '--help')
    assert result.success, result.stderr

    block = _USAGE_BLOCK.search(result.stdout)
    assert block, (
        f'no usage: block was found in the live {subcommand} --help at {script_path}, '
        f'so the declared-flag population could not be derived at all. help was: '
        f'{result.stdout}'
    )

    flags: tuple[str, ...] = tuple(dict.fromkeys(_LONG_OPTION.findall(block.group('usage'))))
    assert flags, (
        f'derived population size 0: no long option was found in the live '
        f'{subcommand} usage block at {script_path} — the derivation is vacuous and '
        f'every population that consumes it would pass over an empty set. usage was: '
        f'{block.group("usage")}'
    )
    return flags
