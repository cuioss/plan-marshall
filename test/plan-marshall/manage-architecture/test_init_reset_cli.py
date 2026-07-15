#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""CLI-level regression tests for ``architecture.py init`` flag wiring.

Drives the ``init`` subcommand through the real argparse / ``cmd_init``
dispatch at the constructed-argv subprocess boundary — the same
``architecture init --force`` invocation the marshall-steward menus run — to
pin the enrichment-wipe fix end-to-end:

* ``init --force`` preserves an existing curated ``enriched.json`` and seeds
  only the module whose stub is missing.
* ``init --force --reset`` blanks every module's ``enriched.json`` back to the
  canonical empty stub.

Regression anchor for the defect where plain ``init --force`` clobbered every
module's curated enrichment. Complements the direct ``api_init(...)`` unit
tests in ``test_cmd_manage.py`` with coverage at the command boundary.
"""

import json
import sys
import tempfile
from pathlib import Path

from conftest import get_script_path, load_script_module, run_script

sys.path.insert(0, str(Path(__file__).parent))

from _arch_fixtures import create_test_project  # noqa: E402


_architecture_core = load_script_module(
    'plan-marshall', 'manage-architecture', '_architecture_core.py', '_architecture_core'
)
get_module_enriched_path = _architecture_core.get_module_enriched_path
save_module_enriched = _architecture_core.save_module_enriched

_ARCHITECTURE_SCRIPT = get_script_path('plan-marshall', 'manage-architecture', 'architecture.py')


def _read_enriched(module_name: str, project_dir: str) -> dict:
    """Read a module's on-disk ``enriched.json`` as a dict."""
    data: dict = json.loads(get_module_enriched_path(module_name, project_dir).read_text())
    return data


def _seed_curated_and_missing(tmpdir: str) -> None:
    """Seed module-a with curated enrichment; leave module-b's stub missing."""
    create_test_project(tmpdir, shape='metadata_rich')
    save_module_enriched('module-a', {'responsibility': 'custom-cli'}, tmpdir)
    # module-b intentionally has no enriched.json — it is the missing-stub case.
    assert not get_module_enriched_path('module-b', tmpdir).exists()


def test_cli_init_force_preserves_existing_and_seeds_missing():
    """``init --force`` preserves curated enrichment and seeds only the missing stub."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_curated_and_missing(tmpdir)

        result = run_script(_ARCHITECTURE_SCRIPT, '--project-dir', tmpdir, 'init', '--force')

        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        # Only module-b (the missing stub) is seeded; module-a is preserved.
        assert int(data['modules_initialized']) == 1

        # module-a's curated content survived the forced init byte-for-byte.
        assert _read_enriched('module-a', tmpdir)['responsibility'] == 'custom-cli'
        # module-b now carries the canonical empty stub.
        assert get_module_enriched_path('module-b', tmpdir).exists()
        assert _read_enriched('module-b', tmpdir)['responsibility'] == ''


def test_cli_init_force_reset_blanks_all():
    """``init --force --reset`` blanks every module's ``enriched.json``."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_curated_and_missing(tmpdir)

        result = run_script(_ARCHITECTURE_SCRIPT, '--project-dir', tmpdir, 'init', '--force', '--reset')

        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        # Both modules are (re-)written to the empty stub.
        assert int(data['modules_initialized']) == 2

        # The curated module-a content has been blanked back to the empty stub.
        assert _read_enriched('module-a', tmpdir)['responsibility'] == ''
        assert _read_enriched('module-b', tmpdir)['responsibility'] == ''
