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

import pytest

from conftest import (
    EXECUTOR_GENERATION_ERROR_TOKEN,
    ExecutorBootstrapError,
    _ensure_executor_present,
    get_scripts_dir,
)

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


# =============================================================================
# conftest executor bootstrap — failure detection across the subprocess boundary
# =============================================================================
#
# ``_ensure_executor_present`` shells out to the generator, whose ``main()`` ends
# ``print(serialize_toon(result)); return 0`` with no branch on
# ``result['status']``. The retired ``check=True`` therefore could not fire on
# ANY expected generation error, so the bootstrap returned having written
# nothing and raised nothing — a fresh CI checkout then ran the whole suite
# against an absent executor with no diagnostic naming the cause.
#
# Detection is now fail-CLOSED: each reading raises ``ExecutorBootstrapError``
# at conftest-import time, which aborts the run. A warning would have left the
# run going over a broken substrate and reporting green on a smaller suite, so
# the assertions below are on the raised message rather than on stderr.
#
# The pair below is taken THROUGH THE SUBPROCESS BOUNDARY, deliberately: the
# bootstrap's detection lives on the far side of ``subprocess.run``, so an
# in-process stub (a monkeypatched function, a fake return value) is invisible
# to it and would exercise nothing. Each stub is a real script, run by a real
# interpreter, whose observable is exactly what a real generator emits.

_ERROR_STUB = (
    'import sys\nprint("status: error")\nprint("error: Fail-open regeneration refused: stub refusal")\nsys.exit(0)\n'
)


def _success_stub(executor_target: Path) -> str:
    """A stub that behaves like a real successful generation: writes, then reports."""
    return (
        'import sys\n'
        'from pathlib import Path\n'
        f'target = Path({str(executor_target)!r})\n'
        'target.parent.mkdir(parents=True, exist_ok=True)\n'
        'target.write_text("# generated\\n", encoding="utf-8")\n'
        'print("status: success")\n'
        'sys.exit(0)\n'
    )


def _write_stub(tmp_path: Path, source: str) -> Path:
    stub = tmp_path / 'stub_generator.py'
    stub.write_text(source, encoding='utf-8')
    return stub


class TestBootstrapFailureDetection:
    """A generation that reports ``status: error`` at exit 0 must abort the run."""

    def test_error_payload_at_exit_zero_raises(self, tmp_path):
        """The stub exits 0 and writes nothing — the payload is the only signal.

        ``check=True`` cannot raise here, so a bootstrap that trusted the exit
        code alone would detect nothing at all. The raised message must name the
        generator's own stdout so the cause is legible in the CI log rather than
        left to be inferred from a later cascade of unrelated failures.
        """
        project_root = tmp_path / 'project'
        project_root.mkdir()
        stub = _write_stub(tmp_path, _ERROR_STUB)

        with pytest.raises(ExecutorBootstrapError) as excinfo:
            _ensure_executor_present(project_root=project_root, generator=stub)

        message = str(excinfo.value)
        assert 'executor bootstrap failed' in message.lower(), message
        assert EXECUTOR_GENERATION_ERROR_TOKEN in message, message
        assert 'stub refusal' in message, message
        assert not (project_root / '.plan' / 'execute-script.py').exists()

    def test_successful_generation_returns(self, tmp_path):
        """Discriminating half — the raise is a verdict, not an unconditional abort.

        Same boundary, same exit code, and the stub differs only in writing the
        executor and reporting success. Without this case the assertion above
        would also pass on a bootstrap that raised after every run.
        """
        project_root = tmp_path / 'project'
        project_root.mkdir()
        executor = project_root / '.plan' / 'execute-script.py'
        stub = _write_stub(tmp_path, _success_stub(executor))

        _ensure_executor_present(project_root=project_root, generator=stub)

        assert executor.exists()

    def test_silent_no_write_at_exit_zero_raises(self, tmp_path):
        """A generation claiming success while writing nothing is still a failure.

        The third reading — the executor is simply absent afterwards — is what
        covers a future refusal path that forgets to say ``status: error``. The
        stub reports success and writes nothing, which neither the exit code nor
        the payload can catch.
        """
        project_root = tmp_path / 'project'
        project_root.mkdir()
        stub = _write_stub(tmp_path, 'import sys\nprint("status: success")\nsys.exit(0)\n')

        with pytest.raises(ExecutorBootstrapError) as excinfo:
            _ensure_executor_present(project_root=project_root, generator=stub)

        assert 'executor_written=False' in str(excinfo.value), str(excinfo.value)

    def test_missing_generator_raises_without_running_anything(self, tmp_path):
        """A generator that is not on disk is a broken environment, not a skip.

        The earliest reading, and the only one that never reaches
        ``subprocess.run`` — the message names the path it looked for.
        """
        project_root = tmp_path / 'project'
        project_root.mkdir()
        absent = tmp_path / 'no_such_generator.py'

        with pytest.raises(ExecutorBootstrapError) as excinfo:
            _ensure_executor_present(project_root=project_root, generator=absent)

        assert str(absent) in str(excinfo.value), str(excinfo.value)

    def test_present_executor_short_circuits_without_running_the_generator(self, tmp_path):
        """Idempotence: an existing executor returns before any subprocess runs.

        Pinned with a stub that would RAISE if it ran, so the short-circuit is
        proven by the absence of that failure rather than merely assumed.
        """
        project_root = tmp_path / 'project'
        (project_root / '.plan').mkdir(parents=True)
        (project_root / '.plan' / 'execute-script.py').write_text('# existing\n', encoding='utf-8')
        stub = _write_stub(tmp_path, _ERROR_STUB)

        _ensure_executor_present(project_root=project_root, generator=stub)

        assert (project_root / '.plan' / 'execute-script.py').read_text(encoding='utf-8') == '# existing\n'


def _skills_dir() -> Path:
    """Absolute path to the marketplace ``…/plan-marshall/skills`` directory."""
    tse_scripts: Path = get_scripts_dir('plan-marshall', 'tools-script-executor').resolve()
    return tse_scripts.parent.parent


def _template_path() -> Path:
    """Absolute path to the executor template."""
    tse_scripts: Path = get_scripts_dir('plan-marshall', 'tools-script-executor').resolve()
    return tse_scripts.parent / 'templates' / 'execute-script.py.template'


def _render_executor(pruned_base: Path, home: Path) -> str:
    """Render the executor template with every bootstrap dir PINNED at a pruned path.

    The shared-module and logging bootstrap dirs are pointed at
    ``{pruned_base}/skills/{skill}/scripts`` — directories that do NOT exist,
    mirroring a GC-pruned embedded MARSHALL_VERSION cache path. The cache-recovery
    roots are injected at the fake home's plugin-cache root — the same
    generation-time injection the real generator performs, with the same
    ``HOME`` the executor is invoked under. Every other substitution token is
    filled with a minimal valid value so the rendered file is importable and its
    module-level shared imports (``plan_logging``, ``toon_parser``,
    ``_ledger_core``, ``worktree_sha``) must resolve exclusively through the
    template's newest-cache self-heal.
    """
    template = _template_path().read_text(encoding='utf-8')

    def pinned(skill: str) -> str:
        return str(pruned_base / 'skills' / skill / 'scripts')

    shared_pairs = '\n'.join(f'    ({skill!r}, {pinned(skill)!r}),' for skill in _BOOTSTRAP_SHARED_SKILLS)

    content = template.replace('{{SCRIPT_MAPPINGS}}', '')
    content = content.replace('{{SCRIPT_SURFACES}}', '')
    content = content.replace('{{LOGGING_DIR}}', pinned(_BOOTSTRAP_LOGGING_SKILL))
    content = content.replace('{{SHARED_MODULE_DIRS}}', shared_pairs)
    recovery_root = home / '.claude' / 'plugins' / 'cache' / 'plan-marshall'
    content = content.replace('{{CACHE_RECOVERY_ROOTS}}', f"    '{recovery_root}',")
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
        home = tmp_path / 'fakehome'
        executor.write_text(_render_executor(pruned_base, home), encoding='utf-8')
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
        home = tmp_path / 'emptyhome'
        executor.write_text(_render_executor(pruned_base, home), encoding='utf-8')
        home.mkdir()

        # Act
        result = _run_executor(executor, home)

        # Assert: with both the pinned dir and the cache absent, the module-level
        # import of plan_logging fails loudly.
        assert result.returncode != 0
        assert 'plan_logging' in result.stderr
