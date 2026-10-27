# SPDX-License-Identifier: FSL-1.1-ALv2
"""Build a marker-less FLAT install fixture out of the real bundle trees.

OpenCode and Antigravity deploy every skill as ``{root}/skills/{bundle}-{skill}/``
— no ``{bundle}/`` directory, no ``.claude-plugin/plugin.json``, no bundle marker
of any kind. A deployed tree of that shape is what a machine running either target
actually has, and it is the shape an import-time walk over the script's parents
must resolve.

What this builder reproduces is the LAYOUT plus each skill's ``scripts/``,
``standards/`` and ``workflow/`` trees. Two deliberate limits: the ``SKILL.md`` it
writes is a minimal identity-carrying manifest of its own, not an emitter's
output, and root-level skill files (``extension.py`` above all) are not copied.
Those two limits are why the emitter-facing D4 tests build their fixtures by
running the real emitters instead (:mod:`test_flat_extension_discovery`); this
fixture exists for the import-time and registry readers, which only need the
layout, the identity and the code.

Nothing it produces carries a bundle marker, which is the property under test — a
``plan-marshall/.claude-plugin/plugin.json`` anywhere in the fixture would let
the nested probes answer and the flat leg would never run. It does write the
TARGET manifest at the deploy root, because a real install has one (see
:data:`TARGET_MANIFEST_NAME`).

Usage (``test/plan-marshall/`` is on ``sys.path`` via the root conftest)::

    from _flat_install_fixtures import build_flat_install, flat_pythonpath

    root = build_flat_install(tmp_path / 'opencode')
    env = {'PYTHONPATH': flat_pythonpath(root)}
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from deployed_layout import (
    IDENTITY_BUNDLE_KEY,
    IDENTITY_METADATA_KEY,
    IDENTITY_SKILL_KEY,
    flat_skill_dir_name,
)

#: The marketplace source tree this repository authors, resolved from this file
#: rather than from an env var or the cwd.
MARKETPLACE_ROOT = Path(__file__).resolve().parents[2] / 'marketplace' / 'bundles'

#: The skill-relative trees a deployed flat skill carries that this fixture
#: reproduces. ``scripts/`` is what imports resolve against; ``standards/`` and
#: ``workflow/`` are the body docs a runtime reader (the runbook lane's bot
#: registry, the phase-6 body docs) opens by path.
COPIED_SUBTREES = ('scripts', 'standards', 'workflow')

#: The target manifest the OpenCode install writes at the deploy root. It is NOT a
#: bundle marker — ``resolve_bundles_root``'s nested probes look for
#: ``plan-marshall/.claude-plugin/plugin.json``, which no flat install carries — but
#: a real deployed tree does hold it, and ``resolve_skills_root`` anchors on it
#: exactly as it does on a source checkout's ``plugin.json``. Leaving it out would
#: make this fixture less like the tree that ships, not more rigorous.
TARGET_MANIFEST_NAME = 'opencode.json'


def identity_skill_md(bundle: str, skill: str) -> str:
    """Return a minimal identity-carrying ``SKILL.md`` for the fixture.

    Deliberately NOT an emitter's output: it carries only what the flat readers in
    this fixture need (the ``metadata`` identity block
    ``deployed_layout.read_flat_skill_identity`` reads). A test that needs the
    deployed frontmatter as an emitter writes it runs the real emitter instead.
    """
    return (
        '---\n'
        f'name: {bundle}-{skill}\n'
        f'description: flat-install fixture skill {bundle}:{skill}\n'
        'metadata:\n'
        f'  bundle: {bundle}\n'
        f'  skill: {skill}\n'
        '---\n\n# Fixture skill\n'
    )


def deployed_skill_md(bundle: str, skill: str) -> str:
    """Return a flat ``SKILL.md`` carrying the SOURCE frontmatter plus the identity block.

    The default :func:`identity_skill_md` is enough for the layout and registry
    readers, but a reader that parses a skill's own ``configurable`` declaration
    (``configurable_contract``) or its bot roster needs the REAL frontmatter. A
    deployed tree carries the source frontmatter verbatim — the emitter copies it
    and adds only the ``metadata`` identity block this function appends — so
    reproducing that pair is enough for such a reader, and it stays decoupled from
    the emitter's own target-specific rewrites.

    Args:
        bundle: Bundle name, e.g. ``plan-marshall``.
        skill: Skill name, e.g. ``automatic-review``.

    Returns:
        The markdown text a flat install holds at
        ``{root}/skills/{bundle}-{skill}/SKILL.md``.
    """
    source = MARKETPLACE_ROOT / bundle / 'skills' / skill / 'SKILL.md'
    text = source.read_text(encoding='utf-8')
    lines = text.splitlines()
    if not lines or lines[0].strip() != '---':
        return identity_skill_md(bundle, skill)
    closing = next((index for index, line in enumerate(lines[1:], start=1) if line.strip() == '---'), None)
    if closing is None:
        return identity_skill_md(bundle, skill)
    frontmatter = lines[1:closing]
    body = lines[closing + 1 :]
    identity = [f'  {IDENTITY_BUNDLE_KEY}: {bundle}', f'  {IDENTITY_SKILL_KEY}: {skill}']
    metadata_key = f'{IDENTITY_METADATA_KEY}:'
    if metadata_key in frontmatter:
        # Four shipped skills already declare a top-level ``metadata:`` map (a
        # ``verification_profile``). Appending a second one would give the manifest a
        # duplicate key, and which half a parser keeps is implementation-defined — so
        # the identity is merged INTO the existing block instead.
        index = frontmatter.index(metadata_key)
        merged = [*frontmatter[: index + 1], *identity, *frontmatter[index + 1 :]]
        assembled = ['---', *merged, '---', *body]
    else:
        assembled = ['---', *frontmatter, metadata_key, *identity, '---', *body]
    return '\n'.join(assembled) + '\n'


def build_flat_install(root: Path, *, real_frontmatter: bool = False) -> Path:
    """Populate ``{root}/skills/{bundle}-{skill}/`` from the real bundle trees.

    Args:
        root: The deploy root to create (e.g. ``~/.config/opencode``).
        real_frontmatter: Write each skill's SOURCE frontmatter plus the identity
            block (:func:`deployed_skill_md`) instead of the minimal fixture
            manifest. Needed by a reader that parses a skill's own declaration —
            the step-doc ``configurable`` blocks and the ``automatic-review`` bot
            roster — and still cheap enough to build per session.

    Returns:
        ``root``, so a caller can chain the build and the env construction.
    """
    skills_root = root / 'skills'
    skills_root.mkdir(parents=True, exist_ok=True)
    (root / TARGET_MANIFEST_NAME).write_text('{"$schema": "https://opencode.ai/config.json"}\n', encoding='utf-8')
    for bundle_dir in sorted(MARKETPLACE_ROOT.iterdir()):
        bundle_skills = bundle_dir / 'skills'
        if not bundle_dir.is_dir() or not bundle_skills.is_dir():
            continue
        for skill_dir in sorted(bundle_skills.iterdir()):
            if not skill_dir.is_dir():
                continue
            target = skills_root / flat_skill_dir_name(bundle_dir.name, skill_dir.name)
            target.mkdir()
            manifest = (
                deployed_skill_md(bundle_dir.name, skill_dir.name)
                if real_frontmatter
                else identity_skill_md(bundle_dir.name, skill_dir.name)
            )
            (target / 'SKILL.md').write_text(manifest, encoding='utf-8')
            for subtree in COPIED_SUBTREES:
                source = skill_dir / subtree
                if source.is_dir():
                    shutil.copytree(
                        source,
                        target / subtree,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'),
                    )
    return root


def flat_pythonpath(root: Path) -> str:
    """Return the ``PYTHONPATH`` the executor builds for a flat install.

    Read from the production rule (``marketplace_bundles.collect_script_dirs``) so
    the fixture's import environment cannot drift from the executor's: every flat
    skill's ``scripts/`` directory plus its immediate sub-directories.
    """
    from marketplace_bundles import collect_script_dirs

    return os.pathsep.join(collect_script_dirs(root))


#: Location variables that would let a flat run read a REAL tree instead of the
#: fixture. Each is scrubbed rather than merely left unset by the caller: an
#: ambient ``PM_MARKETPLACE_ROOT`` (the documented operator workaround for a flat
#: install) is read FIRST by ``find_marketplace_root``, so carrying it through
#: would decide the "no marketplace tree" assertions from the developer's machine.
LOCATION_ENV_VARS = (
    'PYTHONPATH',
    'PM_MARKETPLACE_ROOT',
    'PLAN_BASE_DIR',
    'PLAN_DIR_NAME',
    'PM_DIST_MANIFEST',
)


def flat_env(root: Path, project_dir: Path) -> dict[str, str]:
    """Return a clean environment whose only import path and location is ``root``.

    ``PYTHONPATH`` is REPLACED, never extended: a test that inherited the source
    tree's script directories would import the source copies and prove nothing
    about the flat deployment. Every variable in :data:`LOCATION_ENV_VARS` is
    dropped for the same reason.
    """
    env = {key: value for key, value in os.environ.items() if key not in LOCATION_ENV_VARS}
    env['PYTHONPATH'] = flat_pythonpath(root)
    env['PLAN_MARSHALL_HOME'] = str(project_dir / '.machine-home')
    return env


def run_python_in_flat(
    root: Path,
    project_dir: Path,
    code: str,
    *,
    timeout: int = 300,
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run ``code`` with the flat fixture as the import root and ``project_dir`` as cwd.

    ``env_overrides`` is applied after the scrub, so a caller can PIN a location
    (or an empty ``PYTHONPATH``) the fixture otherwise decides for it.
    """
    env = flat_env(root, project_dir)
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        [sys.executable, '-c', code],
        cwd=project_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def run_script_in_flat(
    root: Path,
    project_dir: Path,
    script: Path,
    *args: str,
    timeout: int = 300,
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a deployed script out of the flat fixture, with no source tree on the path.

    ``env_overrides`` is applied AFTER the scrub, for a caller that must PIN a
    location :data:`LOCATION_ENV_VARS` deliberately clears — a verb that resolves
    its own plan root has to be told which project it is operating on, or it walks
    up into the repository that hosts the pytest basetemp.
    """
    env = flat_env(root, project_dir)
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=project_dir,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


@pytest.fixture(scope='session')
def flat_install_tree(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One marker-less flat deployment for the whole session.

    Session-scoped because populating it copies every bundle skill's script tree;
    the tree is read-only for every consumer, each of which brings its own
    isolated project directory.
    """
    return build_flat_install(tmp_path_factory.mktemp('flat-install'))


@pytest.fixture(scope='session')
def flat_install_tree_with_frontmatter(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """One marker-less flat deployment whose ``SKILL.md`` files carry the real frontmatter.

    The twin of :func:`flat_install_tree` for readers that parse a skill's own
    declaration rather than only its identity: the step-doc ``configurable`` blocks
    (``manage-config``'s backend) and the ``automatic-review`` bot roster. Same
    layout, same copied trees, real manifests.
    """
    return build_flat_install(tmp_path_factory.mktemp('flat-install-frontmatter'), real_frontmatter=True)
