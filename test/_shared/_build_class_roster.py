#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Argparse-derived roster of the build-class operation population.

Every check that reasons about "the build-class subcommands" needs the same
population: which subcommands each build wrapper registers, and whether each one
declares the canonical ``--plan-id`` / ``--project-dir`` routing pair. Restating
that population as a literal list is the failure mode this module exists to
remove — a hand-list silently under-reports the moment a wrapper gains or loses a
subcommand, so a universality assertion written against it passes while covering
less than it claims.

The derivation is therefore argparse introspection end to end, with **no literal
subcommand name anywhere in this module**:

1. **Wrapper discovery** — walk ``marketplace/bundles/*/skills/*/scripts/*.py``
   and keep the non-underscore scripts that route their CLI through
   ``_build_cli.build_main``. That structural marker (not a directory-name
   convention, and not a hand-list of four paths) is what makes a script a build
   wrapper.
2. **Parser capture** — call each wrapper's real ``main()`` with its
   ``build_main`` binding swapped for a capture stub. The wrapper's own
   ``register_standard_subparsers(...)`` configuration runs for real, so the
   captured parser carries EVERY registered subcommand — including the ones
   contributed through ``extra_register_fns`` (which is where the wrapper-local
   subparsers live, outside the shared helper entirely).
3. **Flag-pair introspection** — read each subparser's declared option strings
   and record whether both routing flags are present.

Consumers get ``{notation: {subcommand: declares_flag_pair}}`` from
:func:`build_class_roster`. :func:`build_class_prefixes` is the SEPARATE,
independently-sourced read of the executor template's ``_BUILD_CLASS_PREFIXES``
— the NOTATION half of the executor's definition of which dispatches are
build-class. The two derivations deliberately share no input, so cross-checking
one against the other is a real check rather than a restatement.

**Build-class-ness is a conjunction, and this module supplies only one conjunct
directly.** The executor stamps a ``kind=build`` ledger row only when the
notation matches ``_BUILD_CLASS_PREFIXES`` AND the dispatched subcommand is a
member of the template's ``_BUILD_EXECUTING_SUBCOMMANDS`` allow-list. A prefix
match alone is NOT sufficient: every wrapper also registers pure query verbs,
and a bare ``--help`` dispatch carries no subcommand at all. The subcommand
conjunct is testable from here without any literal name — the roster's
per-wrapper subcommand sets ARE the population a consumer partitions against the
executor's allow-list, which is exactly what the discriminator regression suite
does.

This file is intentionally a sibling helper (``_name.py`` style) and is NOT a
``conftest.py``: a ``conftest.py`` under ``test/_shared/`` would shadow the
top-level ``test/conftest.py`` and disable the shared fixtures.
"""

from __future__ import annotations

import argparse
import ast
import importlib.util
import re
from pathlib import Path

from conftest import MARKETPLACE_ROOT

# =============================================================================
# Canonical routing-flag names
# =============================================================================

PLAN_ID_FLAG = '--plan-id'
"""Plan-binding half of the canonical two-state routing pair."""

PROJECT_DIR_FLAG = '--project-dir'
"""Explicit-override half of the canonical two-state routing pair."""

#: The attribute a build wrapper imports from ``_build_cli`` to drive its CLI.
#: Presence of this binding — confirmed after import, not merely matched in the
#: source text — is what identifies a script as a build wrapper.
_BUILD_MAIN_ATTR = 'build_main'

#: Source-text pre-filter, so only genuine candidates are imported. Both tokens
#: must appear for a script to be worth loading; the post-import check below is
#: the authoritative test.
_CANDIDATE_TOKENS = (_BUILD_MAIN_ATTR, '_build_cli')

#: The executor template — the source of truth for ``_BUILD_CLASS_PREFIXES``.
#: The generated ``.plan/execute-script.py`` is a build artifact, so the template
#: is what a test may read.
_EXECUTOR_TEMPLATE = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'tools-script-executor'
    / 'templates'
    / 'execute-script.py.template'
)

#: The template carries ``{{PLACEHOLDER}}`` tokens, so it is not parseable as a
#: whole module. The frozenset literal itself is, hence the extract-then-
#: ``literal_eval`` shape rather than a full ``ast.parse``.
_PREFIXES_LITERAL = re.compile(
    r'_BUILD_CLASS_PREFIXES\s*=\s*frozenset\(\s*(\[.*?\])\s*\)',
    re.DOTALL,
)


# =============================================================================
# Wrapper discovery
# =============================================================================


def _iter_wrapper_scripts() -> list[tuple[str, str, Path]]:
    """Return ``(bundle, skill, script_path)`` for every build wrapper in the tree.

    Walks the whole marketplace rather than a ``build-*`` subset: the wrapper
    property is "routes its CLI through ``_build_cli.build_main``", so a build
    wrapper introduced under a differently-named skill is still discovered — and
    then shows up as a roster notation the executor's build-class prefixes do not
    cover, which is exactly the drift a cross-check should surface.

    Returns:
        The discovered wrappers, sorted by bundle then skill then filename.
    """
    found: list[tuple[str, str, Path]] = []
    for bundle_dir in sorted(MARKETPLACE_ROOT.iterdir()):
        skills_dir = bundle_dir / 'skills'
        if not skills_dir.is_dir():
            continue
        for skill_dir in sorted(skills_dir.iterdir()):
            scripts_dir = skill_dir / 'scripts'
            if not scripts_dir.is_dir():
                continue
            for script_path in sorted(scripts_dir.glob('*.py')):
                if script_path.name.startswith('_'):
                    continue
                source = script_path.read_text(encoding='utf-8')
                if all(token in source for token in _CANDIDATE_TOKENS):
                    found.append((bundle_dir.name, skill_dir.name, script_path))
    return found


def _load_wrapper_module(script_path: Path):
    """Import ``script_path`` under a private module name.

    The private name keeps the wrapper out of ``sys.modules`` under its own stem,
    so loading it here cannot shadow a module another suite imports by that name.
    Wrapper scripts reference their siblings by bare name through ``sys.path``
    (configured by the root conftest), never through their own registration, so
    the private name costs nothing.
    """
    spec = importlib.util.spec_from_file_location(f'_roster_{script_path.stem}', script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f'Could not create import spec for {script_path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# =============================================================================
# Parser capture and introspection
# =============================================================================


def _capture_parser(module) -> argparse.ArgumentParser:
    """Build the wrapper's parser by running its real ``main()`` against a stub.

    ``build_main`` normally builds the parser AND consumes ``sys.argv``. Swapping
    the wrapper's own binding for a stub keeps the first half and drops the
    second, so the wrapper's genuine ``register_standard_subparsers(...)``
    configuration — ``extra_register_fns`` included — populates a real parser
    with no argv parsing and no handler dispatch.

    Args:
        module: An imported build wrapper module.

    Returns:
        The fully-registered :class:`argparse.ArgumentParser`.

    Raises:
        AssertionError: when the wrapper's ``main()`` never reached ``build_main``.
    """
    captured: dict[str, argparse.ArgumentParser] = {}

    def _stub_build_main(description: str, subparser_fns: list) -> int:
        parser = argparse.ArgumentParser(description=description, allow_abbrev=False)
        subparsers = parser.add_subparsers(dest='command', required=True)
        for register_fn in subparser_fns:
            register_fn(subparsers)
        captured['parser'] = parser
        return 0

    original = getattr(module, _BUILD_MAIN_ATTR)
    setattr(module, _BUILD_MAIN_ATTR, _stub_build_main)
    try:
        module.main()
    finally:
        setattr(module, _BUILD_MAIN_ATTR, original)

    if 'parser' not in captured:
        raise AssertionError(
            f'{module.__name__} main() completed without reaching build_main — '
            'the parser could not be captured, so its subcommand population is unknown.'
        )
    return captured['parser']


def _declared_option_strings(parser: argparse.ArgumentParser) -> set[str]:
    """Return every option string the parser declares."""
    return {option for action in parser._actions for option in action.option_strings}


def _subcommand_flag_pairs(parser: argparse.ArgumentParser) -> dict[str, bool]:
    """Map each registered subcommand to whether it declares the routing pair."""
    pairs: dict[str, bool] = {}
    for action in parser._actions:
        if not isinstance(action, argparse._SubParsersAction):
            continue
        for name, subparser in action.choices.items():
            options = _declared_option_strings(subparser)
            pairs[name] = PLAN_ID_FLAG in options and PROJECT_DIR_FLAG in options
    return pairs


# =============================================================================
# Public API
# =============================================================================

_ROSTER_CACHE: dict[str, dict[str, bool]] | None = None


def build_class_roster() -> dict[str, dict[str, bool]]:
    """Return ``{notation: {subcommand: declares_flag_pair}}`` for every build wrapper.

    The population is derived, never declared: discovery is structural (§1 of the
    module docstring), and each wrapper's subcommand set comes from the parser its
    own ``main()`` builds. A subcommand added to any wrapper — through the shared
    ``register_standard_subparsers`` helper or through ``extra_register_fns`` —
    joins the roster with no edit here.

    Returns:
        Notation (``{bundle}:{skill}:{script}``) to that wrapper's subcommand map.
        The inner value is ``True`` when the subcommand declares BOTH
        :data:`PLAN_ID_FLAG` and :data:`PROJECT_DIR_FLAG`.
    """
    global _ROSTER_CACHE
    if _ROSTER_CACHE is not None:
        return _ROSTER_CACHE

    roster: dict[str, dict[str, bool]] = {}
    for bundle, skill, script_path in _iter_wrapper_scripts():
        module = _load_wrapper_module(script_path)
        if not hasattr(module, _BUILD_MAIN_ATTR) or not callable(getattr(module, 'main', None)):
            continue
        notation = f'{bundle}:{skill}:{script_path.stem}'
        roster[notation] = _subcommand_flag_pairs(_capture_parser(module))

    _ROSTER_CACHE = roster
    return roster


def build_class_prefixes() -> frozenset[str]:
    """Return the executor template's ``_BUILD_CLASS_PREFIXES`` set.

    Read straight out of the template source — the executor's own declaration of
    which notations are build-class dispatches. This is the second, independent
    derivation the roster is cross-checked against; it shares no input with
    :func:`build_class_roster`.

    Raises:
        AssertionError: when the constant cannot be located in the template.
    """
    source = _EXECUTOR_TEMPLATE.read_text(encoding='utf-8')
    match = _PREFIXES_LITERAL.search(source)
    if match is None:
        raise AssertionError(
            f'_BUILD_CLASS_PREFIXES not found in {_EXECUTOR_TEMPLATE} — the '
            'build-class definition moved and this reader must follow it.'
        )
    return frozenset(ast.literal_eval(match.group(1)))
