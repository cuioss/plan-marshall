#!/usr/bin/env python3
"""Tests for extension validation in plugin-doctor.

Tests the cmd_extension.py script that validates extension.py files.
"""

import tempfile
from argparse import Namespace
from pathlib import Path

# Import shared infrastructure
from conftest import get_script_path, run_script

# Script under test
SCRIPT_PATH = get_script_path('pm-plugin-development', 'plugin-doctor', '_validate.py')

# Tier 2 direct imports via importlib for uniform import style
import importlib.util  # noqa: E402

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace' / 'bundles' / 'pm-plugin-development' / 'skills' / 'plugin-doctor' / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_cmd_extension_mod = _load_module('_cmd_extension', '_cmd_extension.py')

cmd_extension = _cmd_extension_mod.cmd_extension


def create_valid_extension(ext_path: Path) -> None:
    """Create a valid extension.py file using class-based approach."""
    ext_path.parent.mkdir(parents=True, exist_ok=True)
    # Note: We can't import extension_base in test fixtures, so we define a minimal base
    ext_path.write_text('''#!/usr/bin/env python3
"""Test extension."""

from pathlib import Path


# Minimal base class for testing (actual extensions use ExtensionBase from extension_base)
class ExtensionBase:
    def provides_triage(self) -> str | None:
        return None
    def provides_outline_skill(self) -> str | None:
        return None


class Extension(ExtensionBase):
    """Test extension class."""

    def get_skill_domains(self) -> list[dict]:
        """Return skill domains."""
        return [{
            "domain": {"key": "test", "name": "Test Domain"},
            "profiles": {"core": {"defaults": [], "optionals": []}}
        }]
''')


def create_invalid_extension_missing_func(ext_path: Path) -> None:
    """Create extension.py missing required methods."""
    ext_path.parent.mkdir(parents=True, exist_ok=True)
    ext_path.write_text('''#!/usr/bin/env python3
"""Test extension - missing required methods."""

from pathlib import Path


class Extension:
    """Extension class missing required get_skill_domains method."""

    def provides_triage(self) -> str | None:
        """Return triage (optional method)."""
        return None

    # Missing: get_skill_domains (required method)
''')


def create_invalid_extension_syntax_error(ext_path: Path) -> None:
    """Create extension.py with syntax error."""
    ext_path.parent.mkdir(parents=True, exist_ok=True)
    ext_path.write_text('''#!/usr/bin/env python3
"""Test extension - syntax error."""

def provides_triage() -> str | None:
    return None  # missing closing

def broken(
''')


# =============================================================================
# CLI plumbing tests (Tier 3 - subprocess)
# =============================================================================


def test_extension_help():
    """Test extension subcommand shows help."""
    result = run_script(SCRIPT_PATH, 'extension', '--help')
    assert result.success
    assert '--extension' in result.stdout
    assert '--bundle' in result.stdout
    assert '--marketplace' in result.stdout


# =============================================================================
# Single Extension Validation Tests (Tier 2 - direct import)
# =============================================================================


def test_validate_valid_extension():
    """Test validating a valid extension.py file."""
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        ext_path = temp_dir / 'extension.py'
        create_valid_extension(ext_path)

        args = Namespace(extension_path=str(ext_path), bundle_path=None, marketplace_path=None)
        data = cmd_extension(args)

        assert data.get('valid') is True, f'Should be valid: {data}'
        assert len(data.get('issues', [])) == 0
        methods = data.get('methods', {})
        assert 'get_skill_domains' in methods


def test_validate_extension_missing_functions():
    """Test validating extension with missing required methods."""
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        ext_path = temp_dir / 'extension.py'
        create_invalid_extension_missing_func(ext_path)

        args = Namespace(extension_path=str(ext_path), bundle_path=None, marketplace_path=None)
        data = cmd_extension(args)

        assert data.get('valid') is False
        issues = data.get('issues', [])
        missing_methods = [i['method'] for i in issues if i['type'] == 'missing_method']
        assert 'get_skill_domains' in missing_methods, f'Should report missing get_skill_domains: {missing_methods}'


def test_validate_extension_syntax_error():
    """Test validating extension with syntax error."""
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        ext_path = temp_dir / 'extension.py'
        create_invalid_extension_syntax_error(ext_path)

        args = Namespace(extension_path=str(ext_path), bundle_path=None, marketplace_path=None)
        data = cmd_extension(args)

        assert data.get('valid') is False
        issues = data.get('issues', [])
        assert any(i['type'] == 'syntax_error' for i in issues)


def test_validate_extension_not_found():
    """Test validating non-existent extension file."""
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        ext_path = temp_dir / 'nonexistent.py'

        args = Namespace(extension_path=str(ext_path), bundle_path=None, marketplace_path=None)
        data = cmd_extension(args)

        assert data.get('valid') is False
        issues = data.get('issues', [])
        assert any(i['type'] == 'file_missing' for i in issues)


# =============================================================================
# Bundle Validation Tests (Tier 2 - direct import)
# =============================================================================


def test_validate_bundle_with_extension():
    """Test validating a bundle that has extension.py."""
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        bundle_path = temp_dir / 'test-bundle'
        ext_path = bundle_path / 'skills' / 'plan-marshall-plugin' / 'extension.py'
        create_valid_extension(ext_path)

        args = Namespace(extension_path=None, bundle_path=str(bundle_path), marketplace_path=None)
        data = cmd_extension(args)

        assert 'extension' in data
        assert data['extension'].get('valid') is True
        assert data['consistency'].get('valid') is True


def test_validate_bundle_without_extension():
    """Test validating a bundle without extension.py."""
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        bundle_path = temp_dir / 'test-bundle'
        bundle_path.mkdir(parents=True)

        args = Namespace(extension_path=None, bundle_path=str(bundle_path), marketplace_path=None)
        data = cmd_extension(args)

        assert data.get('has_extension') is False


# =============================================================================
# Marketplace Scan Tests (Tier 2 - direct import)
# =============================================================================


def test_scan_marketplace():
    """Test scanning marketplace for all extensions."""
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        marketplace = temp_dir / 'marketplace'
        bundles = marketplace / 'bundles'

        # Bundle 1: with valid extension
        ext1_path = bundles / 'bundle1' / 'skills' / 'plan-marshall-plugin' / 'extension.py'
        create_valid_extension(ext1_path)

        # Bundle 2: without extension
        (bundles / 'bundle2').mkdir(parents=True)

        # Bundle 3: with invalid extension
        ext3_path = bundles / 'bundle3' / 'skills' / 'plan-marshall-plugin' / 'extension.py'
        create_invalid_extension_missing_func(ext3_path)

        args = Namespace(extension_path=None, bundle_path=None, marketplace_path=str(marketplace))
        data = cmd_extension(args)

        assert 'summary' in data
        assert data['summary']['total_bundles'] == 3
        assert data['summary']['with_extension'] == 2
        assert data['summary']['valid'] == 1
        assert data['summary']['invalid'] == 1


def test_scan_marketplace_real():
    """Test scanning the real marketplace directory."""
    marketplace_path = Path(__file__).parent.parent.parent.parent / 'marketplace'

    if not marketplace_path.exists():
        return

    args = Namespace(extension_path=None, bundle_path=None, marketplace_path=str(marketplace_path))
    data = cmd_extension(args)

    assert 'summary' in data
    assert data['summary']['with_extension'] >= 6
    assert data['summary']['invalid'] == 0, (
        f'All should be valid, issues: {[e for e in data.get("extensions", []) if not e.get("valid")]}'
    )


# =============================================================================
# Main
# =============================================================================
