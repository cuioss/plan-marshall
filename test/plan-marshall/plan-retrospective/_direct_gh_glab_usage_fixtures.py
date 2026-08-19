# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``direct gh glab usage`` test modules.

Holds the module-level loads, constants and helpers those modules
share, so each of them carries the import and not the preamble.
"""


from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

from conftest import MARKETPLACE_ROOT  # noqa: E402

sys.path.insert(0, str(Path(__file__).parent))


SCRIPT_PATH = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts' / 'direct-gh-glab-usage.py'
)


EXT_DISCOVERY_PATH = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'extension-api' / 'scripts' / 'extension_discovery.py'
)


_PLUGIN_DEV_EXT_PATH = (
    MARKETPLACE_ROOT / 'pm-plugin-development' / 'skills' / 'plan-marshall-plugin' / 'extension.py'
)


# Domain key gating the wrapper-tangle aspect. A plan of any other domain must
# not pick it up.
_PLUGIN_DEV_DOMAIN = 'plan-marshall-plugin-dev'


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _init_git_repo(repo_dir: Path) -> None:
    """Initialise a minimal git repo with a ``main`` branch and one commit.

    The diff scanner (surface B) calls ``git diff {base}...HEAD`` against
    the given ``--project-root``. We need a real repo with a ``main``
    branch so the three-dot syntax resolves cleanly. The initial commit
    is empty so subsequent per-test commits become the HEAD diff.
    """
    env = {
        'GIT_AUTHOR_NAME': 'Test',
        'GIT_AUTHOR_EMAIL': 'test@example.com',
        'GIT_COMMITTER_NAME': 'Test',
        'GIT_COMMITTER_EMAIL': 'test@example.com',
    }
    subprocess.run(
        ['git', 'init', '-q', '-b', 'main', str(repo_dir)],
        check=True,
        capture_output=True,
        env={**env},
    )
    subprocess.run(
        ['git', '-C', str(repo_dir), 'commit', '--allow-empty', '-q', '-m', 'init'],
        check=True,
        capture_output=True,
        env={**env},
    )


def _commit_file(repo_dir: Path, rel_path: str, content: str) -> None:
    """Create ``rel_path`` under ``repo_dir`` with ``content`` and commit it.

    The commit lands on HEAD so ``main...HEAD`` exposes the file as an
    all-added diff.
    """
    env = {
        'GIT_AUTHOR_NAME': 'Test',
        'GIT_AUTHOR_EMAIL': 'test@example.com',
        'GIT_COMMITTER_NAME': 'Test',
        'GIT_COMMITTER_EMAIL': 'test@example.com',
    }
    file_path = repo_dir / rel_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding='utf-8')
    subprocess.run(
        ['git', '-C', str(repo_dir), 'checkout', '-q', '-b', 'feature'],
        check=False,
        capture_output=True,
        env={**env},
    )
    subprocess.run(
        ['git', '-C', str(repo_dir), 'add', rel_path],
        check=True,
        capture_output=True,
        env={**env},
    )
    subprocess.run(
        ['git', '-C', str(repo_dir), 'commit', '-q', '-m', f'add {rel_path}'],
        check=True,
        capture_output=True,
        env={**env},
    )


def _load_extension_module(ext_path: Path, module_name: str):
    """Load an ``extension.py`` and return its ``Extension`` instance."""
    spec = importlib.util.spec_from_file_location(module_name, ext_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.Extension()
