#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The re-fire waiver key has one definition, one writer and one script reader.

``manage-status/SKILL.md`` § "Re-fire waiver" states which readers honour a
``refire_waiver``. That is a fact about the code, so it is enumerated here rather
than left to prose: every script under the bundles that names the waiver key is
classified below, and a new mention fails until the classification — and the
sentence in the skill — is updated with it.
"""

from __future__ import annotations

from conftest import MARKETPLACE_ROOT

#: Script path (relative to the bundles root) → its role in the waiver's lifecycle.
#: The phase-6-finalize dispatcher's re-entry table is prose an agent applies, not a
#: script, so it is named in the skill's sentence and does not appear here. Paths
#: rather than basenames: a nested helper that merely shares a basename with a
#: classified script must not slip through as classified.
_SCRIPT_ROLES: dict[str, str] = {
    'plan-marshall/skills/manage-status/scripts/_cmd_mark_step.py': 'defines the key; writes it via write_refire_waiver',
    'plan-marshall/skills/manage-status/scripts/_cmd_loop_back.py': 'writes it (loop-back close --waive-refire)',
    'plan-marshall/skills/phase-6-finalize/scripts/pre_merge_gate.py': 'reads it (the merge head binding)',
    'plan-marshall/skills/manage-status/scripts/manage-status.py': 'names it in the verb help text only',
}

#: Every script under the bundles, as ``(path, text)``. Read once per test so a
#: guard over the whole tree stays one pass.
_SCRIPT_SUFFIX = '.py'


def _bundle_scripts() -> list[tuple[str, str]]:
    """Every Python file under the bundles, as ``(path relative to the root, text)``.

    The sweep is the whole bundle tree, not one skill's ``scripts/`` directory:
    the sentence it guards says "every script under the bundles that names it",
    so a nested helper directory must not be able to hide a new reader. The
    identity is the path, not the basename — a share of a name is not a share of
    a role.
    """
    return [
        (path.relative_to(MARKETPLACE_ROOT).as_posix(), path.read_text(encoding='utf-8'))
        for path in MARKETPLACE_ROOT.glob('**/*.py')
        if path.suffix == _SCRIPT_SUFFIX
    ]


def _scripts_naming_the_waiver() -> set[str]:
    return {name for name, text in _bundle_scripts() if 'refire_waiver' in text or 'REFIRE_WAIVER_KEY' in text}


def test_every_script_naming_the_waiver_is_classified():
    """A new mention fails here until its role is recorded."""
    naming = _scripts_naming_the_waiver()

    assert naming, 'the sweep found no script naming the waiver — it would pass vacuously'
    assert naming == set(_SCRIPT_ROLES), (
        f'unclassified: {sorted(naming - set(_SCRIPT_ROLES))}; '
        f'stale: {sorted(set(_SCRIPT_ROLES) - naming)}. '
        'Classify the new mention and update manage-status/SKILL.md § "Re-fire waiver" '
        'with it before relying on that sentence.'
    )


def test_the_waiver_key_has_one_definition():
    """One key literal, spelled once; every other site imports it."""
    definitions = [name for name, text in _bundle_scripts() if "REFIRE_WAIVER_KEY = 'refire_waiver'" in text]

    assert definitions == ['plan-marshall/skills/manage-status/scripts/_cmd_mark_step.py'], definitions
