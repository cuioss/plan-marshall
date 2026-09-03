#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Every invocation the deploy-target skill prescribes can actually be run.

The skill body is an executable playbook: an agent follows its command lines
literally. Two of them could not succeed as written — a generator line that
exits 127 because ``uv`` is not on ``PATH``, and an executor notation the
resolver rejects as ``Unknown notation`` while suggesting the typo be appended
as a subcommand. Both failures pointed the caller at something already correct.

These tests read the document by EXPLICIT PATH. ``.claude/**`` lies outside the
architecture inventory, so an inventory-driven sweep returns a structurally
blind ``count: 0`` for this tree — a zero that means "not searched", not "not
found". The same substrate discipline the enumeration gate applied is applied
here.

Every assertion publishes the population it examined, and the population is
asserted non-zero on its own. A scan whose extractor stops matching the document
finds no prescriptions, and "none of them is broken" over an empty set is not a
clean result.
"""

from __future__ import annotations

import re

from _documented_example_scan import DEFECTIVE_GENERATOR_CALL, scan_shell_prescriptions
from conftest import MARKETPLACE_ROOT, PROJECT_ROOT, load_script_module

#: ``discover_scripts`` is taken from the executor GENERATOR itself, so the
#: notation table these tests check against is the one the installed resolver is
#: built from rather than a second derivation of the ``{bundle}:{skill}:{script}``
#: path rule. A second derivation could accept a notation the real resolver
#: rejects, which is the failure mode under test.
#:
#: It is reached through the shared loader with ``register=False`` rather than by
#: a plain ``from generate_executor import ...``. A plain import publishes the
#: stem in ``sys.modules``, where it collides with the file-load of that same name
#: elsewhere in the tree: one copy displaces the other and only collection order
#: decides whether that is observable. Only the returned module is needed here,
#: which is exactly the case the opt-out exists for — the growth guard in
#: ``test/plan-marshall/script-shared/test_conftest_loader_contract.py`` names this
#: escape and forbids clearing the collision by pinning the name instead.
discover_scripts = load_script_module(
    'plan-marshall', 'tools-script-executor', 'generate_executor.py', register=False
).discover_scripts

_SKILL_MD = PROJECT_ROOT / '.claude' / 'skills' / 'finalize-step-deploy-target' / 'SKILL.md'

#: The executor invocation, with the notation that follows it captured. The
#: notation is the token the resolver looks up, so it is what must be present in
#: the resolver's own table.
_EXECUTOR_CALL = re.compile(r'\.plan/execute-script\.py\s+(?P<notation>[A-Za-z0-9_.:-]+)')

def _skill_text() -> str:
    return _SKILL_MD.read_text(encoding='utf-8')


def test_skill_document_yields_a_non_empty_prescription_population():
    """The scan resolves prescriptions from the live document, not from nothing."""
    prescriptions, fenced_lines = scan_shell_prescriptions(_skill_text())

    assert fenced_lines > 0, f'no fenced lines resolved in {_SKILL_MD} — the scan is unresolved'
    assert prescriptions, (
        f'no prescribed command lines resolved from {fenced_lines} fenced lines in {_SKILL_MD} — '
        f'the extractor no longer matches the document, so a broken prescription would pass unseen'
    )


def test_every_prescribed_executor_notation_resolves():
    """Each ``.plan/execute-script.py`` notation exists in the executor's own table.

    The table is derived by the executor GENERATOR — the same discovery that
    builds the installed resolver — rather than by re-deriving the
    ``{bundle}:{skill}:{script}`` path rule here. A second derivation could
    accept a notation the real resolver rejects, which is precisely the failure
    mode under test.
    """
    prescriptions, _ = scan_shell_prescriptions(_skill_text())
    notations = [
        match.group('notation')
        for line in prescriptions
        for match in _EXECUTOR_CALL.finditer(line)
    ]

    assert notations, (
        f'no executor notations found among {len(prescriptions)} prescribed command line(s) in '
        f'{_SKILL_MD} — nothing was resolved'
    )

    table = discover_scripts(MARKETPLACE_ROOT)
    assert table, 'the executor notation table resolved empty; nothing could be checked against it'

    unresolved = sorted({notation for notation in notations if notation not in table})
    assert not unresolved, (
        f'{len(unresolved)} of {len(notations)} prescribed notation(s) in {_SKILL_MD} do not '
        f'resolve against the executor table ({len(table)} notations): {", ".join(unresolved)}'
    )


def test_no_prescription_uses_the_bare_generator_invocation():
    """The generator is prescribed through the wrapper, never bare.

    ``uv`` is installed only into the project-local ``.pyprojectx/`` tree, so the
    bare form exits 127 from a normal shell; a bare ``python3`` form fails
    earlier still, on the project's ``PyYAML`` dependency. Matched as the command
    literal rather than as the bare words ``uv run``, because the body
    legitimately NAMES that form while explaining why it is wrong.
    """
    prescriptions, _ = scan_shell_prescriptions(_skill_text())
    offenders = [line for line in prescriptions if DEFECTIVE_GENERATOR_CALL in line]

    assert not offenders, (
        f'{len(offenders)} of {len(prescriptions)} prescribed command line(s) in {_SKILL_MD} '
        f'use the bare generator invocation:\n  ' + '\n  '.join(offenders)
    )


def test_an_unresolvable_notation_would_be_detected():
    """The matched negative control for the resolution check.

    Without it, a table that happened to contain every string — or a check that
    never consulted one — would satisfy the positive test above. The underscore
    spelling is the exact defect this document once carried.
    """
    table = discover_scripts(MARKETPLACE_ROOT)

    assert 'plan-marshall:manage-status:manage-status' in table
    assert 'plan-marshall:manage-status:manage_status' not in table


def test_prescription_scan_reports_zero_for_a_document_holding_no_fences():
    """The scan publishes an empty population rather than inventing one."""
    prescriptions, fenced_lines = scan_shell_prescriptions('# Heading\n\nProse only.\n')

    assert fenced_lines == 0
    assert prescriptions == []
