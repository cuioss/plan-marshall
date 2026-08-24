#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Census of which registered plugin-doctor rules read a substrate a clone lacks.

``analyze_argument_naming`` resolves ``.plan/execute-script.py`` — a git-ignored
path — and an unreadable executor collapses into an empty finding list that the
gate cannot distinguish from a clean run. This module sizes that exposure across
the WHOLE registered rule set rather than asserting it about the one rule already
known to carry it.

The census is REPORT-ONLY. It publishes ``rules_examined`` and
``rules_with_absent_substrate`` for every registered rule; naming a member is an
observation for the owning epic to schedule, not a trigger to fix anything here.

Derivation, in three steps:

* **Population** — every descriptor ``_rule_registry.get_registry()`` collects,
  attributed back to its declaring module through the registry's own
  per-module collector. No rule name is hand-listed, so a rule added to the
  registry enters the census with no edit here.
* **Substrate** — each analyzer's source is parsed and the ``Path`` joins that
  escape upward out of ``marketplace_root`` are collected as repo-relative
  substrate paths. Detection is deliberately narrow: a join qualifies only when
  it is a SINGLE expression whose base is exactly ``<name>.parent`` — one hop off
  a bare name — and every segment after it is a string literal.
* **Absence** — a substrate is absent from a fresh clone exactly when git does
  not track it. That is asked of git rather than assumed from a path shape, so
  the verdict holds for whatever the ignore rules happen to say.

⛔ ``rules_with_absent_substrate`` is a LOWER BOUND, not an exhaustive count.
Three shapes are invisible to the substrate step, by construction rather than by
oversight:

* a MULTI-HOP base — ``root.parent.parent / 'x'``, whose base ``.value`` is an
  ``ast.Attribute`` rather than an ``ast.Name``;
* a path assembled ACROSS statements — only the join expression itself is read,
  so a base bound on an earlier line is never followed;
* a join carrying a NON-LITERAL segment, which disqualifies the whole join.

A rule that reaches a git-ignored substrate by any of those routes is absent from
the figure. Read a published member as confirmed exposure and a published count
as "at least this many" — never as "these are all of them". Widening the detected
shape raises the bound; it does not turn the bound into a total.

The population is asserted non-empty before anything ranges over it: a census
reporting zero members out of zero rules examined is the very defect this file
exists to measure.
"""

from __future__ import annotations

import ast
import subprocess
from functools import cache, lru_cache
from pathlib import Path
from typing import Any

from conftest import PROJECT_ROOT, get_scripts_dir, load_script_module

#: The analyzer sources the census parses.
SCRIPTS_DIR: Path = get_scripts_dir('pm-plugin-development', 'plugin-doctor')

#: The tree git is asked about, and the anchor every substrate path is relative to.
REPO_ROOT: Path = PROJECT_ROOT

#: The attribute hop that takes a path OUT of ``marketplace_root``. A join rooted
#: at ``marketplace_root`` itself stays inside the marketplace tree and therefore
#: ships in every clone; a join rooted at its ``.parent`` does not.
ROOT_ESCAPE_ATTR = 'parent'

#: Control anchor. The rule whose absent-substrate exposure is already confirmed,
#: asserted as a MEMBER so a derivation that stopped detecting anything fails
#: loudly instead of publishing a reassuring zero. It is not part of the
#: population derivation.
CONFIRMED_MEMBER_MODULE = '_analyze_argument_naming'


@lru_cache(maxsize=1)
def _registry() -> Any:
    """Load ``_rule_registry.py`` under its canonical name.

    Registering under ``_rule_registry`` (not an alias) is what makes the
    analyzer modules the collector imports resolve their own ``from
    _rule_registry import RuleDescriptor`` against this instance.
    """
    return load_script_module(
        'pm-plugin-development', 'plugin-doctor', '_rule_registry.py', '_rule_registry'
    )


@lru_cache(maxsize=1)
def _rule_modules() -> tuple[tuple[str, str], ...]:
    """Return ``(rule_id, declaring_module)`` for every registered descriptor."""
    registry = _registry()
    pairs: list[tuple[str, str]] = []
    for module_name in registry._DESCRIPTOR_MODULES:
        for descriptor in registry._descriptors_for_module(module_name):
            pairs.append((str(descriptor.rule_id), str(module_name)))
    return tuple(sorted(pairs))


def _join_segments(node: ast.expr) -> tuple[ast.expr, list[str | None]]:
    """Flatten a ``Path`` ``/`` chain into its base and its right-hand segments.

    A segment that is not a string literal yields ``None``, which marks the whole
    chain unresolvable rather than silently dropping a path component.
    """
    segments: list[str | None] = []
    current = node
    while isinstance(current, ast.BinOp) and isinstance(current.op, ast.Div):
        right = current.right
        if isinstance(right, ast.Constant) and isinstance(right.value, str):
            segments.append(right.value)
        else:
            segments.append(None)
        current = current.left
    segments.reverse()
    return current, segments


def _escaping_substrates(source: str) -> tuple[str, ...]:
    """Return repo-relative paths ``source`` resolves outside ``marketplace_root``.

    A LOWER BOUND over the detected shape, not an enumeration: the join must be a
    single expression rooted at ``<name>.parent`` with literal segments. See the
    module docstring for the three shapes this deliberately does not reach.
    """
    tree = ast.parse(source)
    joins = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)
    ]
    # Only the OUTERMOST join of a chain describes the whole path; an inner one
    # would additionally report every truncated prefix of it.
    nested = {id(node.left) for node in joins}
    found: set[str] = set()
    for node in joins:
        if id(node) in nested:
            continue
        base, segments = _join_segments(node)
        if not isinstance(base, ast.Attribute) or base.attr != ROOT_ESCAPE_ATTR:
            continue
        if not isinstance(base.value, ast.Name):
            continue
        if not segments or any(segment is None for segment in segments):
            continue
        found.add('/'.join(segment for segment in segments if segment is not None))
    return tuple(sorted(found))


@cache
def _ships_in_a_clone(rel_path: str) -> bool:
    """True when git tracks ``rel_path`` — i.e. a fresh clone materialises it."""
    result = subprocess.run(
        ['git', 'ls-files', '--error-unmatch', '--', rel_path],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise AssertionError(
            f'git could not decide whether {rel_path!r} ships in a clone '
            f'(exit {result.returncode}): {result.stderr.strip()}'
        )
    return result.returncode == 0


@lru_cache(maxsize=1)
def _census() -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    """Return ``(rule_id, module, absent_substrates)`` for every registered rule."""
    rows: list[tuple[str, str, tuple[str, ...]]] = []
    for rule_id, module_name in _rule_modules():
        path = SCRIPTS_DIR / f'{module_name}.py'
        try:
            source = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            # An unreadable analyzer is a coverage gap, not an absence — fail
            # loudly rather than silently shrinking the examined population.
            raise AssertionError(f'Could not read registered analyzer: {path}') from None
        absent = tuple(
            substrate
            for substrate in _escaping_substrates(source)
            if not _ships_in_a_clone(substrate)
        )
        rows.append((rule_id, module_name, absent))
    return tuple(rows)


def _members() -> tuple[tuple[str, str, tuple[str, ...]], ...]:
    """Return only the census rows that carry at least one absent substrate."""
    return tuple(row for row in _census() if row[2])


def census_report() -> str:
    """Render the census as the two published figures plus one line per member."""
    rows = _census()
    members = _members()
    lines = [
        f'rules_examined: {len(rows)}',
        f'rules_with_absent_substrate: {len(members)}',
        '  (a LOWER BOUND: detects single-expression joins rooted at <name>.parent '
        'with literal segments; multi-hop bases and cross-statement assembly are '
        'not reached)',
    ]
    lines.extend(f'  {rule_id} ({module}): {", ".join(absent)}' for rule_id, module, absent in members)
    return '\n'.join(lines)


def test_registered_population_is_non_empty():
    """The derived population is non-empty, so nothing below ranges over zero rules.

    A census over an empty registry publishes ``rules_with_absent_substrate: 0``
    while having examined nothing — a clean-looking figure derived from no
    observation, which is the archetype this file measures.
    """
    population = _rule_modules()
    assert population, (
        'The rule population derived from _rule_registry is EMPTY, so every count '
        'this module publishes would be a zero over nothing.'
    )


def test_module_attribution_covers_the_whole_registry():
    """Every descriptor ``get_registry`` collects is attributed to a declaring module.

    The census walks per-module to learn which analyzer to parse; this pins that
    walk to the registry itself, so a rule reachable through ``get_registry`` but
    not through the per-module collector cannot drop out of the examined set.
    """
    registry = _registry()
    collected = {str(descriptor.rule_id) for descriptor in registry.get_registry()}
    attributed = {rule_id for rule_id, _module in _rule_modules()}
    assert attributed == collected, (
        f'attribution covers {len(attributed)} rule(s) but the registry collects '
        f'{len(collected)}; unattributed: {sorted(collected - attributed)}, '
        f'unregistered: {sorted(attributed - collected)}'
    )


def test_census_publishes_both_counts():
    """Both figures are published, and the examined count matches the population."""
    report = census_report()
    print(report)

    rows = _census()
    assert f'rules_examined: {len(rows)}' in report, report
    assert f'rules_with_absent_substrate: {len(_members())}' in report, report
    assert len(rows) == len(_rule_modules()), (
        f'census examined {len(rows)} rule(s) out of a population of '
        f'{len(_rule_modules())} — the walk dropped members.\n{report}'
    )


def test_the_confirmed_member_is_derived_not_assumed():
    """``analyze_argument_naming`` is a member, derived by the census itself.

    The control that keeps the published zero honest: this rule demonstrably
    reads ``.plan/execute-script.py``, so a derivation that reports it clean has
    stopped detecting the exposure rather than found the tree free of it.
    """
    member_modules = {module for _rule_id, module, _absent in _members()}
    assert CONFIRMED_MEMBER_MODULE in member_modules, (
        f'{CONFIRMED_MEMBER_MODULE} is absent from the {len(member_modules)} member '
        f'module(s) the census derived: {sorted(member_modules)}.\n{census_report()}'
    )


def test_every_reported_substrate_is_really_untracked():
    """Each reported substrate is one git does not track, checked path by path.

    Membership is the census's whole output, so the predicate behind it is
    asserted directly rather than trusted: a substrate that ships in a clone
    reported as absent would inflate the published figure.
    """
    reported = sorted({substrate for _rule, _module, absent in _members() for substrate in absent})
    assert reported, f'no absent substrate was derived at all:\n{census_report()}'
    shipping = [substrate for substrate in reported if _ships_in_a_clone(substrate)]
    assert not shipping, (
        f'{len(shipping)} reported substrate(s) are tracked by git and therefore '
        f'present in a fresh clone: {shipping}'
    )
