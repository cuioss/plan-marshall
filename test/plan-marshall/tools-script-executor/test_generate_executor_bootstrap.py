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

import subprocess
import sys
import textwrap

from conftest import get_scripts_dir


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
