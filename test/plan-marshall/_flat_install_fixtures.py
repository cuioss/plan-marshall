# SPDX-License-Identifier: FSL-1.1-ALv2
"""Build a marker-less FLAT install fixture out of the real bundle trees.

OpenCode and Antigravity deploy every skill as ``{root}/skills/{bundle}-{skill}/``
— no ``{bundle}/`` directory, no ``.claude-plugin/plugin.json``, no manifest of
any kind. A deployed tree of that shape is what a machine running either target
actually has, and it is the shape an import-time walk over the script's parents
must resolve.

This builder copies every bundle skill's ``scripts/``, ``standards/`` and
``workflow/`` trees into that layout and writes the one file the emitters
synthesize: an identity-carrying ``SKILL.md``
(:func:`deployed_layout.read_flat_skill_identity` is its reader). Nothing it
produces carries a bundle marker, which is the property under test — a
``plan-marshall/.claude-plugin/plugin.json`` anywhere in the fixture would let
the nested probes answer and the flat leg would never run.

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
from deployed_layout import flat_skill_dir_name

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
    """Return the ``SKILL.md`` a flat emitter writes: identity plus a description."""
    return (
        '---\n'
        f'name: {bundle}-{skill}\n'
        f'description: flat-install fixture skill {bundle}:{skill}\n'
        'metadata:\n'
        f'  bundle: {bundle}\n'
        f'  skill: {skill}\n'
        '---\n\n# Fixture skill\n'
    )


def build_flat_install(root: Path) -> Path:
    """Populate ``{root}/skills/{bundle}-{skill}/`` from the real bundle trees.

    Args:
        root: The deploy root to create (e.g. ``~/.config/opencode``).

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
            (target / 'SKILL.md').write_text(identity_skill_md(bundle_dir.name, skill_dir.name), encoding='utf-8')
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


def flat_env(root: Path, project_dir: Path) -> dict[str, str]:
    """Return a clean environment whose only import path is ``root``.

    ``PYTHONPATH`` is REPLACED, never extended: a test that inherited the source
    tree's script directories would import the source copies and prove nothing
    about the flat deployment.
    """
    env = {key: value for key, value in os.environ.items() if key != 'PYTHONPATH'}
    env['PYTHONPATH'] = flat_pythonpath(root)
    env['PLAN_MARSHALL_HOME'] = str(project_dir / '.machine-home')
    return env


def run_python_in_flat(
    root: Path,
    project_dir: Path,
    code: str,
    *,
    timeout: int = 300,
) -> subprocess.CompletedProcess[str]:
    """Run ``code`` with the flat fixture as the import root and ``project_dir`` as cwd."""
    return subprocess.run(
        [sys.executable, '-c', code],
        cwd=project_dir,
        env=flat_env(root, project_dir),
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
) -> subprocess.CompletedProcess[str]:
    """Run a deployed script out of the flat fixture, with no source tree on the path."""
    return subprocess.run(
        [sys.executable, str(script), *args],
        cwd=project_dir,
        env=flat_env(root, project_dir),
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
