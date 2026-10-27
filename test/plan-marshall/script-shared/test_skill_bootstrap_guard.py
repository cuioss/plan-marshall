# SPDX-License-Identifier: FSL-1.1-ALv2
"""The shared entry-script bootstrap, and the guard that keeps it shared.

Every marketplace script that imports a shared library before the executor has
set ``PYTHONPATH`` must resolve that library itself. That resolution used to be
copied per carrier — five private copies, each re-spelling the flat
``{bundle}-{lib}`` rule, two of them disagreeing about which shapes exist — and
one of the copies (``permission_common``) probed the NESTED shape only, so
``permission_fix.py`` died in a flat install on ``ModuleNotFoundError:
platform_runtime``.

The shared form is :mod:`skill_bootstrap` plus the byte-identical stdlib-only
anchor each carrier opens with. This module is the guard:

* the carrier population is DISCOVERED by AST (a module-level ``sys.path``
  mutation), so a sixth carrier that copies the old loop cannot be added
  quietly;
* every discovered carrier must import and call ``bootstrap_skill_libraries``;
* every carrier must carry the SAME anchor block, byte for byte;
* no carrier may re-spell the private fallbacks the shared helper replaced;
* and each of the five entry scripts starts in a marker-less flat fixture with an
  EMPTY ``PYTHONPATH`` — the bootstrap is the only thing that can resolve the
  libraries there.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from _flat_install_fixtures import (
    MARKETPLACE_ROOT,
    build_flat_install,
    run_script_in_flat,
)

#: The bootstrap module every carrier must route through.
HELPER_MODULE = 'skill_bootstrap'
HELPER_CALL = 'bootstrap_skill_libraries'
ANCHOR_MARKER = '# --- plan-marshall skill bootstrap: one shared anchor'

#: The carriers at the time this guard was written. The set is the DISCOVERED
#: population (a module-level ``sys.path`` mutation in a module that names the
#: shared ``script-shared`` library), declared here so a change is a deliberate
#: one: a new carrier appears in the discovery, is absent here, and reds this
#: test until it is declared — and then has to carry the anchor.
DECLARED_CARRIERS: frozenset[str] = frozenset(
    {
        # D1: the generator whose private inline derivation LB-97 added.
        'marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py',
        # D2: the four entry scripts that carried their own copy of the fallback.
        'marketplace/bundles/plan-marshall/skills/tools-permission-fix/scripts/permission_fix.py',
        'marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/determine_mode.py',
        'marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/bootstrap_plugin.py',
        'marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/gitignore_setup.py',
        # The two modules that imported ``platform_runtime`` through a
        # nested-only probe, which is what broke ``permission_fix.py`` flat.
        'marketplace/bundles/plan-marshall/skills/tools-permission-doctor/scripts/permission_common.py',
        'marketplace/bundles/plan-marshall/skills/tools-permission-doctor/scripts/permission_doctor.py',
        # platform-runtime's Claude implementation: four sibling libraries plus
        # ``script-shared/scripts/build``, resolved by the same anchor.
        'marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_runtime.py',
    }
)

#: The library-name literal that identifies a SIBLING-skill bootstrap. A module
#: that only puts its OWN ``scripts/`` directory on ``sys.path`` (the extension
#: entry points, the extension-api consumer) is a different concern and is out of
#: this guard's population.
BOOTSTRAP_SIGNATURE = "'script-shared'"

#: The five entry scripts the Done-when names, as ``(bundle, skill, script)``.
ENTRY_SCRIPTS: tuple[tuple[str, str, str], ...] = (
    ('plan-marshall', 'tools-script-executor', 'generate_executor.py'),
    ('plan-marshall', 'tools-permission-fix', 'permission_fix.py'),
    ('plan-marshall', 'marshall-steward', 'determine_mode.py'),
    ('plan-marshall', 'marshall-steward', 'bootstrap_plugin.py'),
    ('plan-marshall', 'marshall-steward', 'gitignore_setup.py'),
)

#: Spellings the shared helper replaced. A carrier carrying one has re-derived
#: the flat rule instead of asking :mod:`deployed_layout` for it.
PRIVATE_FALLBACK_SPELLINGS = (
    'plan-marshall-{_lib}',
    "'plan-marshall-script-shared'",
    '"plan-marshall-script-shared"',
)

REPO_ROOT = MARKETPLACE_ROOT.parents[1]


def _is_sys_path_attribute(node: ast.expr) -> bool:
    """Whether ``node`` is the expression ``sys.path``."""
    return (
        isinstance(node, ast.Attribute)
        and node.attr == 'path'
        and isinstance(node.value, ast.Name)
        and node.value.id == 'sys'
    )


def _module_level_path_edits(module_path: Path) -> bool:
    """Whether ``module_path`` mutates ``sys.path`` at MODULE level.

    A mutation inside a function is a lazy import helper, not an entry-script
    bootstrap, and is out of this guard's scope. Class bodies are treated as
    nested too: no bootstrap legitimately lives there.
    """
    tree = ast.parse(module_path.read_text(encoding='utf-8'), filename=str(module_path))
    found = False

    class _Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.depth = 0

        def _descend(self, node: ast.AST) -> None:
            self.depth += 1
            self.generic_visit(node)
            self.depth -= 1

        visit_FunctionDef = _descend  # type: ignore[assignment]
        visit_AsyncFunctionDef = _descend  # type: ignore[assignment]
        visit_ClassDef = _descend  # type: ignore[assignment]

        def visit_Call(self, node: ast.Call) -> None:
            nonlocal found
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr in {'insert', 'append'}
                and _is_sys_path_attribute(func.value)
                and self.depth == 0
            ):
                found = True
            self.generic_visit(node)

    _Visitor().visit(tree)
    return found


def _discovered_carriers() -> set[str]:
    """Return every module that bootstraps a SIBLING ``script-shared`` library.

    The signature is a module-level ``sys.path`` mutation plus the shared
    library's name — a module that only adds its OWN ``scripts/`` directory is a
    different concern and is not counted.
    """
    discovered: set[str] = set()
    for module_path in sorted(MARKETPLACE_ROOT.rglob('*.py')):
        if '__pycache__' in module_path.parts:
            continue
        text = module_path.read_text(encoding='utf-8')
        if BOOTSTRAP_SIGNATURE not in text:
            continue
        if _module_level_path_edits(module_path):
            discovered.add(module_path.relative_to(REPO_ROOT).as_posix())
    return discovered


def test_the_carrier_population_is_the_declared_one() -> None:
    """A new or removed carrier is a deliberate, declared change."""
    discovered = _discovered_carriers()

    assert discovered == set(DECLARED_CARRIERS), (
        'the bootstrap carrier population changed: '
        f'undeclared={sorted(discovered - set(DECLARED_CARRIERS))}, '
        f'stale={sorted(set(DECLARED_CARRIERS) - discovered)}'
    )


def test_every_carrier_routes_through_the_shared_helper() -> None:
    """The guard the Done-when names: the four private copies and the generator use one helper."""
    offenders: list[str] = []
    for relative in sorted(DECLARED_CARRIERS):
        text = (REPO_ROOT / relative).read_text(encoding='utf-8')
        if f'from {HELPER_MODULE} import {HELPER_CALL}' not in text or f'{HELPER_CALL}(' not in text:
            offenders.append(f'{relative}: does not route through {HELPER_MODULE}.{HELPER_CALL}')

    assert not offenders, 'private bootstrap copies survive:\n  ' + '\n  '.join(offenders)


def test_every_carrier_carries_the_same_anchor_block() -> None:
    """The stdlib-only anchor is one block, byte-identical in every carrier."""
    blocks: dict[str, str] = {}
    for relative in sorted(DECLARED_CARRIERS):
        text = (REPO_ROOT / relative).read_text(encoding='utf-8')
        start = text.index(ANCHOR_MARKER)
        end = text.index(f'from {HELPER_MODULE} import {HELPER_CALL}', start)
        blocks[relative] = text[start:end]

    reference_key = next(iter(blocks))
    reference = blocks[reference_key]
    drifted = {relative: block for relative, block in blocks.items() if block != reference}

    assert not drifted, (
        'the bootstrap anchor is not byte-identical across carriers; '
        f'reference={reference_key}, drifted={sorted(drifted)}'
    )


def test_no_carrier_respells_a_private_fallback() -> None:
    """The flat naming rule is asked of the shared resolver, never re-spelled."""
    offenders: list[str] = []
    for relative in sorted(DECLARED_CARRIERS):
        text = (REPO_ROOT / relative).read_text(encoding='utf-8')
        for spelling in PRIVATE_FALLBACK_SPELLINGS:
            if spelling in text:
                offenders.append(f'{relative}: carries {spelling}')

    assert not offenders, 'a carrier re-derived the flat layout rule:\n  ' + '\n  '.join(offenders)


def _deployed_script(root: Path, bundle: str, skill: str, script: str) -> Path:
    return root / 'skills' / f'{bundle}-{skill}' / 'scripts' / script


@pytest.mark.parametrize(('bundle', 'skill', 'script'), ENTRY_SCRIPTS)
def test_each_entry_script_starts_in_a_flat_install_with_no_pythonpath(
    tmp_path: Path, bundle: str, skill: str, script: str
) -> None:
    """Each entry script reaches argparse in a marker-less flat tree, bootstrap only.

    ``PYTHONPATH`` is pinned EMPTY: on a deployed OpenCode tree every library is a
    flat sibling, and nothing but the entry script's own bootstrap can put them on
    the path. ``permission_fix.py`` is the case that failed at the base — it
    imported ``permission_common``, which imported ``platform_runtime`` from a
    nested-only probe.
    """
    root = build_flat_install(tmp_path / 'opencode')
    project_dir = tmp_path / 'project'
    project_dir.mkdir()
    deployed = _deployed_script(root, bundle, skill, script)

    completed = run_script_in_flat(root, project_dir, deployed, '--help', env_overrides={'PYTHONPATH': ''})

    assert completed.returncode == 0, completed.stderr
    assert 'usage:' in completed.stdout.lower(), completed.stdout
