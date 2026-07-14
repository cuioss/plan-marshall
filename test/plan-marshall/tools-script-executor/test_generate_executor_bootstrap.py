# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the generate_executor.py sys.path bootstrap guard.

The bootstrap guard at the top of ``generate_executor.py`` must UNCONDITIONALLY
front-load the generator's own (script-relative) shared-lib paths, so an
inherited PYTHONPATH carrying an OLDER-version ``script-shared`` dir cannot
shadow the generator's own imports. The regression these tests guard against is
the "insert only when absent" form, which left the generator's own path stranded
behind an older-version entry when that path was already present on ``sys.path``.

The guard runs at module import time, so it is exercised via a clean-environment
subprocess that pre-seeds ``sys.path`` and then imports the real generator by
file path — asserting on the resulting ``sys.path`` ordering.
"""

import os
import subprocess
import sys
import textwrap
from pathlib import Path

from conftest import get_scripts_dir

# The shared-module skills the executor template bootstraps onto sys.path before
# its own top-level imports (plan_logging, toon_parser, _ledger_core,
# worktree_sha, input_validation). Mirrors get_shared_module_dirs' shared_skills
# plus the separately-handled logging skill.
_BOOTSTRAP_SHARED_SKILLS = (
    'tools-file-ops',
    'tools-input-validation',
    'ref-toon-format',
    'script-shared',
    'manage-change-ledger',
)
_BOOTSTRAP_LOGGING_SKILL = 'manage-logging'


def _run_bootstrap_probe(seed_lines: str) -> tuple[int, int, int, str]:
    """Import generate_executor in a clean subprocess after seeding sys.path.

    ``seed_lines`` is Python source (executed before the import) that arranges
    ``sys.path`` — it may reference the ``real`` and ``injected`` names bound in
    the driver preamble. Returns ``(returncode, real_index, injected_index,
    stderr)``; the indices are ``-1`` when the probe did not emit them.
    """
    gen_path = (get_scripts_dir('plan-marshall', 'tools-script-executor') / 'generate_executor.py').resolve()
    scripts_dir = gen_path.parent
    skills_dir = scripts_dir.parent.parent
    # Match the guard's own computation exactly (str(_SKILLS_DIR / 'script-shared' / 'scripts')).
    real = str(skills_dir / 'script-shared' / 'scripts')
    injected = '/nonexistent-plan-marshall-oldver/script-shared/scripts'

    driver = textwrap.dedent(
        """
        import importlib.util
        import sys

        real = {real!r}
        injected = {injected!r}
        {seed_lines}
        spec = importlib.util.spec_from_file_location('generate_executor_under_test', {gen_path!r})
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        print(sys.path.index(real) if real in sys.path else -1)
        print(sys.path.index(injected) if injected in sys.path else -1)
        """
    ).format(real=real, injected=injected, seed_lines=seed_lines, gen_path=str(gen_path))

    # Clean environment: drop PYTHONPATH so the subprocess sys.path starts minimal
    # and the seed lines are the only script-dir entries. The generator resolves
    # its own imports via the bootstrap guard, so no inherited PYTHONPATH is needed.
    import os

    env = {k: v for k, v in os.environ.items() if k != 'PYTHONPATH'}
    result = subprocess.run(
        [sys.executable, '-c', driver],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )
    lines = result.stdout.strip().splitlines()
    real_idx = int(lines[0]) if len(lines) >= 1 else -1
    injected_idx = int(lines[1]) if len(lines) >= 2 else -1
    return result.returncode, real_idx, injected_idx, result.stderr


class TestBootstrapGuard:
    def test_front_loads_own_path_ahead_of_injected_older_path(self):
        # Arrange: an inherited PYTHONPATH where an OLDER-version script-shared dir
        # sits FIRST and the generator's OWN path is already present but LATER — the
        # exact shape a plain "insert only when absent" guard would leave shadowed.
        seed = textwrap.dedent(
            """
            sys.path.insert(0, real)      # own path present but about to be pushed back
            sys.path.insert(0, injected)  # older-version dir now ahead of it
            """
        )

        # Act
        returncode, real_idx, injected_idx, stderr = _run_bootstrap_probe(seed)

        # Assert: the generator imported cleanly and its own path is now AHEAD of
        # the injected older path (a non-unconditional guard would leave real behind).
        assert returncode == 0, stderr
        assert real_idx != -1, 'generator own script-shared path missing from sys.path'
        assert injected_idx != -1, 'injected older path missing from sys.path'
        assert real_idx < injected_idx

    def test_front_loads_own_path_when_absent(self):
        # Arrange: only the older-version dir is inherited; the generator's own path
        # is not yet on sys.path.
        seed = 'sys.path.insert(0, injected)'

        # Act
        returncode, real_idx, injected_idx, stderr = _run_bootstrap_probe(seed)

        # Assert: the guard still front-loads its own path ahead of the older dir.
        assert returncode == 0, stderr
        assert real_idx != -1
        assert injected_idx != -1
        assert real_idx < injected_idx


def _skills_dir() -> Path:
    """Absolute path to the marketplace ``…/plan-marshall/skills`` directory."""
    tse_scripts: Path = get_scripts_dir('plan-marshall', 'tools-script-executor').resolve()
    return tse_scripts.parent.parent


def _template_path() -> Path:
    """Absolute path to the executor template."""
    tse_scripts: Path = get_scripts_dir('plan-marshall', 'tools-script-executor').resolve()
    return tse_scripts.parent / 'templates' / 'execute-script.py.template'


def _render_executor(pruned_base: Path) -> str:
    """Render the executor template with every bootstrap dir PINNED at a pruned path.

    The shared-module and logging bootstrap dirs are pointed at
    ``{pruned_base}/skills/{skill}/scripts`` — directories that do NOT exist,
    mirroring a GC-pruned embedded MARSHALL_VERSION cache path. Every other
    substitution token is filled with a minimal valid value so the rendered file
    is importable and its module-level shared imports (``plan_logging``,
    ``toon_parser``, ``_ledger_core``, ``worktree_sha``) must resolve exclusively
    through the template's newest-cache self-heal.
    """
    template = _template_path().read_text(encoding='utf-8')

    def pinned(skill: str) -> str:
        return str(pruned_base / 'skills' / skill / 'scripts')

    shared_pairs = '\n'.join(f'    ({skill!r}, {pinned(skill)!r}),' for skill in _BOOTSTRAP_SHARED_SKILLS)

    content = template.replace('{{SCRIPT_MAPPINGS}}', '')
    content = content.replace('{{LOGGING_DIR}}', pinned(_BOOTSTRAP_LOGGING_SKILL))
    content = content.replace('{{SHARED_MODULE_DIRS}}', shared_pairs)
    content = content.replace('{{EXTRA_SCRIPT_DIRS}}', '')
    content = content.replace('{{PLAN_DIR_NAME}}', '.plan')
    content = content.replace(
        '{{TARGET_AWARE_RESOLVER}}',
        'def _resolve_notation_by_target(notation):\n    return None',
    )
    content = content.replace('{{EXECUTOR_TARGET}}', 'claude')
    content = content.replace('{{GENERATED_VERSION}}', '')
    content = content.replace('{{MAPPINGS_FINGERPRINT}}', '')
    return content


def _stand_up_fake_cache(home: Path, skills: tuple[str, ...]) -> None:
    """Create a plugin cache under ``home`` whose ONLY (newer) version dir carries the skills.

    Lays out ``{home}/.claude/plugins/cache/plan-marshall/9.9.9999/skills/{skill}/scripts``
    as a symlink to each real marketplace skill's ``scripts`` dir, so the template's
    ``_newest_cache_scripts_dir`` self-heal resolves the real modules. No older/pinned
    version dir is created — that is the GC-pruned shape.
    """
    skills_dir = _skills_dir()
    cache_ver = home / '.claude' / 'plugins' / 'cache' / 'plan-marshall' / '9.9.9999' / 'skills'
    for skill in skills:
        skill_dir = cache_ver / skill
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / 'scripts').symlink_to(skills_dir / skill / 'scripts', target_is_directory=True)


def _run_executor(executor: Path, home: Path) -> subprocess.CompletedProcess:
    """Invoke the rendered executor with ``--list`` under a clean env + fake HOME.

    ``PYTHONPATH`` is dropped so the ONLY way the module-level shared imports resolve
    is the template's newest-cache self-heal (the pinned dirs are pruned). ``--list``
    exits right after the module-load bootstrap, so a self-heal failure surfaces as a
    non-zero exit with a ``ModuleNotFoundError`` before ``main`` runs.
    """
    env = {k: v for k, v in os.environ.items() if k != 'PYTHONPATH'}
    env['HOME'] = str(home)
    return subprocess.run(
        [sys.executable, str(executor), '--list'],
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )


class TestTemplateBootstrapSelfHeal:
    """The executor template self-heals a GC-pruned pinned cache version dir."""

    _ALL_BOOTSTRAP_SKILLS = (*_BOOTSTRAP_SHARED_SKILLS, _BOOTSTRAP_LOGGING_SKILL)

    def test_pruned_pinned_version_self_heals_to_newest_cache_dir(self, tmp_path):
        # Arrange: render an executor whose bootstrap dirs are all pinned at a pruned
        # (nonexistent) path, and stand up a fake cache whose ONLY version dir (newer)
        # carries the real shared modules — the exact GC-pruned-pinned-version shape.
        pruned_base = tmp_path / 'pruned-cache'
        executor = tmp_path / 'execute-script.py'
        executor.write_text(_render_executor(pruned_base), encoding='utf-8')
        home = tmp_path / 'fakehome'
        _stand_up_fake_cache(home, self._ALL_BOOTSTRAP_SKILLS)

        # Act
        result = _run_executor(executor, home)

        # Assert: the bootstrap re-resolved to the newest surviving cache version dir,
        # so plan_logging (and the other shared imports) loaded cleanly.
        assert result.returncode == 0, result.stderr
        assert 'ModuleNotFoundError' not in result.stderr
        assert 'plan_logging' not in result.stderr

    def test_pruned_pinned_version_without_cache_fails_to_import(self, tmp_path):
        # Arrange: same pruned-pinned render, but NO surviving cache version dir — the
        # self-heal has nothing to resolve to. This proves the pruned-pinned setup
        # genuinely breaks the imports, so the positive test above exercises the heal.
        pruned_base = tmp_path / 'pruned-cache'
        executor = tmp_path / 'execute-script.py'
        executor.write_text(_render_executor(pruned_base), encoding='utf-8')
        home = tmp_path / 'emptyhome'
        home.mkdir()

        # Act
        result = _run_executor(executor, home)

        # Assert: with both the pinned dir and the cache absent, the module-level
        # import of plan_logging fails loudly.
        assert result.returncode != 0
        assert 'plan_logging' in result.stderr
