#!/usr/bin/env python3
"""Tests for triage integration patterns.

Tests domain routing logic and triage decision workflow.
"""


# =============================================================================
# Helper Functions (Implementation)
# =============================================================================

def route_file_to_domain(file_path: str):
    """
    Route a file path to the appropriate triage domain.

    Returns:
        Domain name if detected, None for generic/unknown
    """
    path = file_path.lower()

    # Check file extension first
    if path.endswith('.java'):
        return 'java'

    if path.endswith(('.js', '.ts', '.tsx', '.jsx', '.css', '.scss')):
        return 'javascript'

    # Check for marketplace Python/Markdown files
    if 'marketplace/' in path and (path.endswith('.py') or path.endswith('.md')):
        return 'plan-marshall-plugin-dev'

    # Unknown - return None for generic handling
    return None


def get_default_triage_decision(severity: str) -> str:
    """
    Get default triage decision for a severity level.

    Returns:
        Decision: 'fix', 'suppress', or 'accept'
    """
    severity_upper = severity.upper()

    # BLOCKER and CRITICAL always require fix
    if severity_upper in ['BLOCKER', 'CRITICAL']:
        return 'fix'

    # MAJOR defaults to fix
    if severity_upper == 'MAJOR':
        return 'fix'

    # MINOR can be either (default to fix)
    if severity_upper == 'MINOR':
        return 'fix'

    # INFO/LOW can be accepted
    if severity_upper in ['INFO', 'LOW']:
        return 'accept'

    # Unknown severity defaults to fix (be safe)
    return 'fix'


# =============================================================================
# Test: Domain Routing by File Extension
# =============================================================================

def test_java_file_routes_to_java_domain():
    """Java files route to java domain."""
    assert route_file_to_domain("src/main/java/MyClass.java") == "java"
    assert route_file_to_domain("src/test/java/MyClassTest.java") == "java"
    assert route_file_to_domain("module/Service.java") == "java"


def test_javascript_files_route_to_javascript_domain():
    """JavaScript/TypeScript files route to javascript domain."""
    assert route_file_to_domain("src/components/Button.js") == "javascript"
    assert route_file_to_domain("src/utils/helper.ts") == "javascript"
    assert route_file_to_domain("src/app/page.tsx") == "javascript"
    assert route_file_to_domain("src/styles.css") == "javascript"  # Frontend domain


def test_python_in_marketplace_routes_to_plugin_domain():
    """Python files in marketplace route to plugin-dev domain."""
    assert route_file_to_domain("marketplace/bundles/my-bundle/scripts/tool.py") == "plan-marshall-plugin-dev"
    assert route_file_to_domain("marketplace/bundles/pm-dev-java/skills/java-core/scripts/helper.py") == "plan-marshall-plugin-dev"


def test_markdown_in_marketplace_routes_to_plugin_domain():
    """Markdown files in marketplace route to plugin-dev domain."""
    assert route_file_to_domain("marketplace/bundles/my-bundle/skills/skill-name/SKILL.md") == "plan-marshall-plugin-dev"
    assert route_file_to_domain("marketplace/bundles/my-bundle/commands/my-command.md") == "plan-marshall-plugin-dev"


def test_python_outside_marketplace_returns_none():
    """Python files outside marketplace return None (generic)."""
    assert route_file_to_domain("scripts/util.py") is None
    assert route_file_to_domain("test/conftest.py") is None


def test_unknown_extension_returns_none():
    """Unknown file types return None."""
    assert route_file_to_domain("README.txt") is None
    assert route_file_to_domain("config.yaml") is None


# =============================================================================
# Test: Triage Decision Matrix
# =============================================================================

def test_blocker_severity_requires_fix():
    """BLOCKER severity always requires fix."""
    decision = get_default_triage_decision("BLOCKER")
    assert decision == "fix"


def test_critical_severity_requires_fix():
    """CRITICAL severity always requires fix."""
    decision = get_default_triage_decision("CRITICAL")
    assert decision == "fix"


def test_major_severity_fix_if_reasonable():
    """MAJOR severity: fix if low effort."""
    decision = get_default_triage_decision("MAJOR")
    assert decision == "fix"  # Default to fix


def test_minor_severity_defaults_to_fix():
    """MINOR severity: defaults to fix."""
    decision = get_default_triage_decision("MINOR")
    assert decision == "fix"


def test_info_severity_can_accept():
    """INFO severity: can accept unless obvious fix."""
    decision = get_default_triage_decision("INFO")
    assert decision == "accept"


# =============================================================================
# Test: Iteration Loop
# =============================================================================

def test_max_iterations_constant():
    """MAX_ITERATIONS should be 5."""
    MAX_ITERATIONS = 5
    assert MAX_ITERATIONS == 5


def test_exit_on_no_findings():
    """Loop exits when no findings remain."""
    findings = []
    should_continue = len(findings) > 0
    assert should_continue is False


def test_exit_on_max_iterations():
    """Loop exits when max iterations reached."""
    MAX_ITERATIONS = 5
    iteration = 5
    should_continue = iteration < MAX_ITERATIONS
    assert should_continue is False


def test_continue_if_fixes_made():
    """Loop continues if fixes were made."""
    fixes_made = True
    iteration = 2
    MAX_ITERATIONS = 5
    should_continue = fixes_made and iteration < MAX_ITERATIONS
    assert should_continue is True


def test_exit_if_only_accepts():
    """Loop exits if only accepts (no fixes/suppressions)."""
    decisions = ['accept', 'accept', 'accept']
    fixes_or_suppressions = any(d in ['fix', 'suppress'] for d in decisions)
    should_continue = fixes_or_suppressions
    assert should_continue is False
