#!/usr/bin/env python3
"""Tests for extension_base.py module (public API)."""

import sys

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
# Import modules under test (PYTHONPATH set by conftest)
from extension_base import (
    ALL_CANONICAL_COMMANDS,
    CANONICAL_COMMANDS,
    CMD_BENCHMARK,
    CMD_CLEAN,
    CMD_CLEAN_INSTALL,
    CMD_COMPILE,
    CMD_COVERAGE,
    CMD_INSTALL,
    CMD_INTEGRATION_TESTS,
    CMD_MODULE_TESTS,
    CMD_PACKAGE,
    CMD_QUALITY_GATE,
    CMD_TEST_COMPILE,
    CMD_VERIFY,
    PROFILE_PATTERNS,
    ExtensionBase,
)

# =============================================================================
# Tests for CMD_* Constants
# =============================================================================

def test_cmd_constants_values():
    """CMD_* constants have expected string values."""
    assert CMD_CLEAN == "clean"
    assert CMD_COMPILE == "compile"
    assert CMD_TEST_COMPILE == "test-compile"
    assert CMD_MODULE_TESTS == "module-tests"
    assert CMD_INTEGRATION_TESTS == "integration-tests"
    assert CMD_COVERAGE == "coverage"
    assert CMD_BENCHMARK == "benchmark"
    assert CMD_QUALITY_GATE == "quality-gate"
    assert CMD_VERIFY == "verify"
    assert CMD_INSTALL == "install"
    assert CMD_CLEAN_INSTALL == "clean-install"
    assert CMD_PACKAGE == "package"


def test_all_canonical_commands_contains_all():
    """ALL_CANONICAL_COMMANDS contains all CMD_* constants."""
    expected = [
        CMD_CLEAN, CMD_COMPILE, CMD_TEST_COMPILE, CMD_MODULE_TESTS, CMD_INTEGRATION_TESTS,
        CMD_COVERAGE, CMD_BENCHMARK, CMD_QUALITY_GATE, CMD_VERIFY,
        CMD_INSTALL, CMD_CLEAN_INSTALL, CMD_PACKAGE
    ]
    assert ALL_CANONICAL_COMMANDS == expected


# =============================================================================
# Tests for CANONICAL_COMMANDS Metadata
# =============================================================================

def test_canonical_commands_structure():
    """CANONICAL_COMMANDS has expected structure for each command."""
    for cmd_name, meta in CANONICAL_COMMANDS.items():
        assert "phase" in meta, f"{cmd_name} missing 'phase'"
        assert "description" in meta, f"{cmd_name} missing 'description'"
        assert "required" in meta, f"{cmd_name} missing 'required'"
        assert isinstance(meta["required"], bool), f"{cmd_name} 'required' should be bool"


def test_canonical_commands_required():
    """Required commands are marked correctly."""
    required_commands = [CMD_MODULE_TESTS, CMD_QUALITY_GATE, CMD_VERIFY]
    for cmd in required_commands:
        assert CANONICAL_COMMANDS[cmd]["required"], f"{cmd} should be required"


def test_canonical_commands_phases():
    """Commands are assigned to expected phases."""
    phase_mapping = {
        "clean": [CMD_CLEAN],
        "build": [CMD_COMPILE, CMD_TEST_COMPILE],
        "test": [CMD_MODULE_TESTS, CMD_INTEGRATION_TESTS, CMD_COVERAGE, CMD_BENCHMARK],
        "quality": [CMD_QUALITY_GATE],
        "verify": [CMD_VERIFY],
        "deploy": [CMD_INSTALL, CMD_CLEAN_INSTALL, CMD_PACKAGE],
    }
    for phase, commands in phase_mapping.items():
        for cmd in commands:
            assert CANONICAL_COMMANDS[cmd]["phase"] == phase, f"{cmd} should be in {phase} phase"


# =============================================================================
# Tests for PROFILE_PATTERNS
# =============================================================================

def test_profile_patterns_integration_tests():
    """Integration test aliases map to CMD_INTEGRATION_TESTS."""
    aliases = ["integration-tests", "integration-test", "it", "e2e", "acceptance"]
    for alias in aliases:
        assert alias in PROFILE_PATTERNS, f"'{alias}' should be in PROFILE_PATTERNS"
        assert PROFILE_PATTERNS[alias] == CMD_INTEGRATION_TESTS


def test_profile_patterns_quality_gate():
    """Quality gate aliases map to CMD_QUALITY_GATE."""
    aliases = ["pre-commit", "precommit", "sonar", "lint", "check", "quality"]
    for alias in aliases:
        assert alias in PROFILE_PATTERNS, f"'{alias}' should be in PROFILE_PATTERNS"
        assert PROFILE_PATTERNS[alias] == CMD_QUALITY_GATE


def test_profile_patterns_coverage():
    """Coverage aliases map to CMD_COVERAGE."""
    aliases = ["coverage", "jacoco"]
    for alias in aliases:
        assert alias in PROFILE_PATTERNS, f"'{alias}' should be in PROFILE_PATTERNS"
        assert PROFILE_PATTERNS[alias] == CMD_COVERAGE


def test_profile_patterns_benchmark():
    """Benchmark aliases map to CMD_BENCHMARK."""
    aliases = ["performance", "jmh", "perf", "benchmarks", "stress", "load"]
    for alias in aliases:
        assert alias in PROFILE_PATTERNS, f"'{alias}' should be in PROFILE_PATTERNS"
        assert PROFILE_PATTERNS[alias] == CMD_BENCHMARK


# =============================================================================
# Tests for ExtensionBase Class
# =============================================================================

class ConcreteExtension(ExtensionBase):
    """Concrete implementation for testing."""

    def get_skill_domains(self) -> dict:
        return {"domain": {"key": "test"}, "profiles": {}}


def test_extension_base_abstract_methods():
    """ExtensionBase requires get_skill_domains."""
    ext = ConcreteExtension()
    assert ext.get_skill_domains()["domain"]["key"] == "test"


def test_extension_base_default_discover_modules():
    """Default discover_modules returns empty list."""
    ext = ConcreteExtension()
    assert ext.discover_modules("/some/path") == []


def test_extension_base_default_triage():
    """Default provides_triage returns None."""
    ext = ConcreteExtension()
    assert ext.provides_triage() is None


def test_extension_base_default_outline():
    """Default provides_outline returns None."""
    ext = ConcreteExtension()
    assert ext.provides_outline() is None


if __name__ == "__main__":
    import traceback

    tests = [
        test_cmd_constants_values,
        test_all_canonical_commands_contains_all,
        test_canonical_commands_structure,
        test_canonical_commands_required,
        test_canonical_commands_phases,
        test_profile_patterns_integration_tests,
        test_profile_patterns_quality_gate,
        test_profile_patterns_coverage,
        test_profile_patterns_benchmark,
        test_extension_base_abstract_methods,
        test_extension_base_default_discover_modules,
        test_extension_base_default_triage,
        test_extension_base_default_outline,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception:
            failed += 1
            print(f"FAILED: {test.__name__}")
            traceback.print_exc()
            print()

    print(f"\nResults: {passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
