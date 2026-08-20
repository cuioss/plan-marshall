# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``direct gh glab usage`` test modules.

Holds the module-level loads, constants and helpers those modules
share. The contract they pin, in full:

Tests for the generic ``direct-gh-glab-usage.py`` aspect (Surfaces A+B) and
the retrospective-aspect extension point that homes the former Surface C.

Covers the domain-invariant detection scenarios for the generic aspect:

(a) Fixture log files containing ``gh``/``glab`` invocations (positive
    detection) — surface ``log_leak``.
(b) Fixture diff with added ``gh``/``glab`` lines (positive detection)
    — surface ``diff_leak``.
(d) Fixture where ``gh`` appears only in a comment — negative, must NOT
    trip the diff scanner.

Plus the Surface C split contract, scoped to this file per the deliverable:

* Surfaces A+B remain in the generic, domain-invariant ``direct-gh-glab-usage``
  aspect; ``wrapper_tangle`` is no longer emitted there.
* Surface C moved to the ``plan-marshall-plugin-dev`` domain aspect
  ``pm-plugin-development:plan-marshall-plugin:wrapper-tangle-scan``,
  contributed via the ``provides_retrospective_aspects()`` extension point.
* ``extension_discovery.py`` discovers the hook and surfaces it through the
  ``list-retrospective-aspects`` CLI (the deterministic backing for
  plan-retrospective Step 3's domain-aspect merge).
* ``pm-plugin-development``'s ``extension.py`` contributes the aspect gated by
  the ``plan-marshall-plugin-dev`` domain only; ``ExtensionBase`` returns ``[]``
  by default.
* plan-retrospective Step 3 merges domain aspects per domain — modelled here as
  the deterministic ``filter list-retrospective-aspects by plan domain``
  predicate the workflow step relies on.

The wrapper-tangle DETECTION behaviour itself lives in
``test/pm-plugin-development/plan-marshall-plugin/test_wrapper_tangle_scan.py``.
"""


from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))




from conftest import MARKETPLACE_ROOT  # noqa: E402

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
