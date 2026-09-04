# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for permission_web.py - WebFetch domain categorization.

Tier 2 (direct import) tests with subprocess tests for CLI plumbing.
"""

from argparse import Namespace

from conftest import get_script_path, run_script

# Script under test (for subprocess CLI plumbing tests)
SCRIPT_PATH = get_script_path('plan-marshall', 'workflow-permission-web', 'permission_web.py')

# Tier 2 direct imports — conftest sets up PYTHONPATH for cross-skill imports
from permission_web import (  # noqa: E402
    categorize_domains,
    check_red_flags,
    cmd_categorize,
)

# =============================================================================
# categorize_domains (direct import)
# =============================================================================


def test_categorize_major_domain():
    """Test that known major domains are correctly categorized."""
    categories = categorize_domains(['docs.oracle.com', 'maven.apache.org', 'junit.org'])

    assert len(categories['major']) == 3


def test_categorize_high_reach_domain():
    """Test that high-reach platforms are correctly categorized."""
    categories = categorize_domains(['github.com', 'stackoverflow.com'])

    assert len(categories['high_reach']) == 2


def test_categorize_unknown_domain():
    """Test that unknown domains are categorized as unknown."""
    categories = categorize_domains(['my-internal-tool.example.com'])

    assert len(categories['unknown']) == 1


def test_categorize_suspicious_domain():
    """Test that domains with red flags are flagged as suspicious."""
    categories = categorize_domains(['free-downloads-keygen.tk'])

    assert len(categories['suspicious']) == 1
    flags = check_red_flags('free-downloads-keygen.tk')
    assert len(flags) > 0


def test_categorize_universal_wildcard():
    """Test that wildcard is categorized as universal."""
    categories = categorize_domains(['*'])

    assert len(categories['universal']) == 1


def test_categorize_subdomain_of_known():
    """Test that subdomains of known domains inherit parent category."""
    categories = categorize_domains(['api.github.com', 'javadoc.docs.oracle.com'])

    # api.github.com -> high_reach (parent: github.com)
    # javadoc.docs.oracle.com -> major (parent: docs.oracle.com)
    assert len(categories['high_reach']) == 1
    assert len(categories['major']) == 1


def test_categorize_mixed_domains():
    """Test categorization of a mixed set of domains."""
    categories = categorize_domains(['docs.oracle.com', 'github.com', 'unknown.example.com', '*'])

    assert len(categories['major']) == 1
    assert len(categories['high_reach']) == 1
    assert len(categories['unknown']) == 1
    assert len(categories['universal']) == 1


def test_categorize_empty_list():
    """Test categorization of empty domain list."""
    categories = categorize_domains([])

    total = sum(len(v) for v in categories.values())
    assert total == 0


# =============================================================================
# cmd_categorize (direct import)
# =============================================================================


def test_categorize_invalid_json():
    """Test error on invalid JSON input."""
    result = cmd_categorize(Namespace(domains='not-json'))

    assert result['status'] == 'error'


def test_categorize_not_array():
    """Test error when input is not an array."""
    result = cmd_categorize(Namespace(domains='"single-string"'))

    assert result['status'] == 'error'
    assert 'array' in result['error']


# =============================================================================
# categorize edge cases (#42)
# =============================================================================


def test_categorize_domain_star_prefix():
    """Test that 'domain:*' is NOT treated as universal (vestigial format)."""
    categories = categorize_domains(['domain:*'])

    # domain:* is not a valid format — should be classified as unknown, not universal
    assert len(categories['unknown']) == 1
    assert len(categories['universal']) == 0


# =============================================================================
# categorize with protocol-prefixed domains (#35)
# =============================================================================


def test_protocol_prefix_stripped():
    """Domains with https:// prefix are normalized — protocol is stripped."""
    categories = categorize_domains(['https://github.com'])

    # https://github.com is recognized as github.com after protocol stripping
    assert len(categories['high_reach']) == 1


# =============================================================================
# Subprocess (Tier 3) tests — CLI plumbing only
# =============================================================================


def run_pw_script(args: list) -> tuple:
    """Run permission_web.py with args and return (stdout, stderr, returncode)."""
    result = run_script(SCRIPT_PATH, *args)
    return result.stdout, result.stderr, result.returncode


def test_no_subcommand():
    """Test error when no subcommand provided."""
    _, stderr, code = run_pw_script([])

    assert code != 0


def test_help():
    """Test help output."""
    stdout, _, code = run_pw_script(['--help'])

    assert code == 0
    assert 'categorize' in stdout


# =============================================================================
# No-Claude-write pin (D1)
# =============================================================================


def test_script_performs_no_settings_io():
    """Verify the script has no settings I/O capability (D1 routing).

    This script performs only domain categorization. Settings reading,
    writing, and WebFetch grammar rendering are handled by the
    platform-runtime. Driving this script must never create a
    .claude/settings*.json file.
    """
    import inspect

    import permission_web as mod

    source = inspect.getsource(mod)
    # The script must not import settings I/O helpers or render WebFetch strings
    assert 'json.loads' not in source, 'script still parses JSON settings directly'
    assert 'json.dumps' not in source, 'script still serializes JSON settings'
    assert 'WebFetch(' not in source, 'script still renders WebFetch grammar'
    assert 'read_text' not in source, 'script still reads files directly'
    assert 'write_text' not in source, 'script still writes files directly'
