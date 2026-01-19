#!/usr/bin/env python3
"""
Local conftest for verify-workflow tests.

Sets up PYTHONPATH for cross-skill imports before test collection.
"""

import importlib.util
import sys
from pathlib import Path

# =============================================================================
# PYTHONPATH Setup (must run before any test module is collected)
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.parent.parent
MARKETPLACE_ROOT = PROJECT_ROOT / 'marketplace' / 'bundles'


def _setup_marketplace_pythonpath() -> list[str]:
    """Set up sys.path for cross-skill imports, mirroring executor behavior."""
    script_dirs = set()

    # Scan marketplace for all scripts/ directories
    for bundle_dir in MARKETPLACE_ROOT.iterdir():
        if not bundle_dir.is_dir():
            continue
        skills_dir = bundle_dir / 'skills'
        if not skills_dir.exists():
            continue
        for skill_dir in skills_dir.iterdir():
            if not skill_dir.is_dir():
                continue
            scripts_dir = skill_dir / 'scripts'
            if scripts_dir.exists():
                script_dirs.add(str(scripts_dir))

    # Add to sys.path (avoid duplicates)
    added = []
    for script_dir in sorted(script_dirs):
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)
            added.append(script_dir)

    return added


# Run immediately on conftest import (before test collection)
_setup_marketplace_pythonpath()


# =============================================================================
# Shared fixtures for loading scripts
# =============================================================================

VERIFY_SCRIPT_PATH = PROJECT_ROOT / '.claude' / 'skills' / 'verify-workflow' / 'scripts' / 'verify-structure.py'
COLLECT_SCRIPT_PATH = PROJECT_ROOT / '.claude' / 'skills' / 'verify-workflow' / 'scripts' / 'collect-artifacts.py'


def _load_script_module(name: str, path: Path):
    """Load a script as a module."""
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Load scripts as modules - this happens after PYTHONPATH is set up
verify_structure = _load_script_module('verify_structure', VERIFY_SCRIPT_PATH)
collect_artifacts = _load_script_module('collect_artifacts', COLLECT_SCRIPT_PATH)
