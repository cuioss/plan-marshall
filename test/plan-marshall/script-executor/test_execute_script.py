#!/usr/bin/env python3
"""Unit tests for execute-script.py executor (template)."""

import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

# Import shared infrastructure (conftest.py sets up PYTHONPATH)

# Path to templates and scripts
SKILL_DIR = Path(__file__).parent.parent.parent.parent / "marketplace/bundles/plan-marshall/skills/script-executor"
TEMPLATE_DIR = SKILL_DIR / "templates"
SCRIPTS_DIR = SKILL_DIR / "scripts"
LOGGING_DIR = Path(__file__).parent.parent.parent.parent / "marketplace/bundles/plan-marshall/skills/logging/scripts"


def load_executor_module():
    """Load the execute-script module from template for testing."""
    template_path = TEMPLATE_DIR / "execute-script.py.template"
    with open(template_path) as f:
        code = f.read()

    # Replace the placeholders with test values
    code = code.replace(
        '{{SCRIPT_MAPPINGS}}',
        '''
    "pm-workflow:manage-files": "/test/path/manage-files.py",
    "pm-dev-builder:builder-maven-rules": "/test/path/maven.py",
    "test:skill": "/test/path/test-skill.py",
'''
    )
    code = code.replace('{{LOGGING_DIR}}', str(LOGGING_DIR))

    # Add logging dir to path so plan_logging can be imported
    sys.path.insert(0, str(LOGGING_DIR))

    # Create a module and provide __file__
    import types
    module = types.ModuleType('execute_script')
    module.__dict__['__file__'] = str(template_path)

    exec(code, module.__dict__)
    return module


# =============================================================================
# TESTS: resolve_notation
# =============================================================================

def test_resolve_exact_match():
    """Resolve exact notation match."""
    executor = load_executor_module()
    result = executor.resolve_notation('pm-workflow:manage-files')
    assert result == '/test/path/manage-files.py', f"Expected '/test/path/manage-files.py', got {result}"


def test_resolve_partial_match():
    """Resolve partial notation match."""
    executor = load_executor_module()
    result = executor.resolve_notation('pm-workflow')
    # Should find planning:manage-files
    assert result is not None, "Expected a result for partial match"
    assert 'manage-files' in result, f"Expected 'manage-files' in result, got {result}"


def test_resolve_unknown_notation():
    """Return None for unknown notation."""
    executor = load_executor_module()
    result = executor.resolve_notation('unknown:script')
    assert result is None, f"Expected None for unknown notation, got {result}"


def test_resolve_all_mappings():
    """All mappings are available in SCRIPTS dict."""
    executor = load_executor_module()
    assert 'pm-workflow:manage-files' in executor.SCRIPTS
    assert 'pm-dev-builder:builder-maven-rules' in executor.SCRIPTS
    assert 'test:skill' in executor.SCRIPTS


# =============================================================================
# TESTS: extract_trace_plan_id
# =============================================================================

def test_extract_trace_plan_id_space_separated():
    """Extract --trace-plan-id with space-separated value."""
    executor = load_executor_module()
    plan_id, cleaned = executor.extract_trace_plan_id(
        ['--trace-plan-id', 'my-plan', '--include-descriptions']
    )
    assert plan_id == 'my-plan', f"Expected 'my-plan', got {plan_id}"
    assert cleaned == ['--include-descriptions'], f"Expected ['--include-descriptions'], got {cleaned}"


def test_extract_trace_plan_id_equals_format():
    """Extract --trace-plan-id=value format."""
    executor = load_executor_module()
    plan_id, cleaned = executor.extract_trace_plan_id(
        ['--trace-plan-id=my-plan', '--bundles', 'planning']
    )
    assert plan_id == 'my-plan', f"Expected 'my-plan', got {plan_id}"
    assert cleaned == ['--bundles', 'planning'], f"Expected ['--bundles', 'planning'], got {cleaned}"


def test_extract_trace_plan_id_not_present():
    """No trace-plan-id returns None and unchanged args."""
    executor = load_executor_module()
    plan_id, cleaned = executor.extract_trace_plan_id(
        ['--plan-id', 'my-plan', '--flag']
    )
    assert plan_id is None, f"Expected None, got {plan_id}"
    assert cleaned == ['--plan-id', 'my-plan', '--flag'], "Args should be unchanged"


def test_extract_trace_plan_id_preserves_other_args():
    """trace-plan-id extraction preserves all other arguments."""
    executor = load_executor_module()
    plan_id, cleaned = executor.extract_trace_plan_id(
        ['verb', '--trace-plan-id', 'test-plan', '--flag', 'value', '--other']
    )
    assert plan_id == 'test-plan', f"Expected 'test-plan', got {plan_id}"
    assert cleaned == ['verb', '--flag', 'value', '--other'], "Other args should be preserved"


def test_extract_trace_plan_id_at_end():
    """trace-plan-id at end of args."""
    executor = load_executor_module()
    plan_id, cleaned = executor.extract_trace_plan_id(
        ['--bundles', 'pm-dev-java', '--trace-plan-id', 'end-plan']
    )
    assert plan_id == 'end-plan', f"Expected 'end-plan', got {plan_id}"
    assert cleaned == ['--bundles', 'pm-dev-java'], f"Expected ['--bundles', 'pm-dev-java'], got {cleaned}"


# =============================================================================
# TESTS: Script execution via subprocess
# =============================================================================

def test_successful_script_execution():
    """Successful script execution returns correct exit code."""
    with tempfile.TemporaryDirectory() as tmp:
        test_script = Path(tmp) / 'test-script.py'
        test_script.write_text('''#!/usr/bin/env python3
import sys
print("Hello from test script")
print(f"Args: {sys.argv[1:]}")
sys.exit(0)
''')

        # Execute directly via subprocess
        result = subprocess.run(
            ['python3', str(test_script), 'arg1', 'arg2'],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"Expected exit code 0, got {result.returncode}"
        assert 'Hello from test script' in result.stdout


def test_failed_script_returns_exit_code():
    """Failed script execution returns script's exit code."""
    with tempfile.TemporaryDirectory() as tmp:
        test_script = Path(tmp) / 'test-script.py'
        test_script.write_text('''#!/usr/bin/env python3
import sys
print("Error occurred", file=sys.stderr)
sys.exit(42)
''')

        result = subprocess.run(
            ['python3', str(test_script)],
            capture_output=True,
            text=True
        )

        assert result.returncode == 42, f"Expected exit code 42, got {result.returncode}"
        assert 'Error occurred' in result.stderr


def test_argument_forwarding():
    """Arguments are correctly forwarded to script."""
    with tempfile.TemporaryDirectory() as tmp:
        test_script = Path(tmp) / 'test-script.py'
        test_script.write_text('''#!/usr/bin/env python3
import sys
import json
print(json.dumps(sys.argv[1:]))
''')

        args = ['verb', '--plan-id', 'my-plan', '--flag', 'value']
        result = subprocess.run(
            ['python3', str(test_script)] + args,
            capture_output=True,
            text=True
        )

        import json
        received_args = json.loads(result.stdout.strip())
        assert received_args == args, f"Expected {args}, got {received_args}"


# =============================================================================
# TESTS: should_skip_logging (meta-logging noise prevention)
# =============================================================================

def test_skip_logging_for_manage_log_success():
    """Skip logging for successful manage-log calls (avoids meta-logging noise)."""
    executor = load_executor_module()
    result = executor.should_skip_logging('plan-marshall:logging:manage-log', exit_code=0)
    assert result is True, "Should skip logging for successful manage-log calls"


def test_log_manage_log_on_error():
    """Log manage-log calls when they fail (errors should be logged)."""
    executor = load_executor_module()
    result = executor.should_skip_logging('plan-marshall:logging:manage-log', exit_code=1)
    assert result is False, "Should log manage-log calls when they fail"


def test_log_normal_scripts_success():
    """Log normal scripts even on success."""
    executor = load_executor_module()
    result = executor.should_skip_logging('pm-workflow:manage-files', exit_code=0)
    assert result is False, "Should log normal script calls"


def test_log_normal_scripts_failure():
    """Log normal scripts on failure."""
    executor = load_executor_module()
    result = executor.should_skip_logging('pm-workflow:manage-files', exit_code=1)
    assert result is False, "Should log normal script calls on failure"


# =============================================================================
# TESTS: generate-executor.py script
# =============================================================================

def test_generate_script_help():
    """Generate script shows help."""
    script_path = SCRIPTS_DIR / "generate-executor.py"

    if script_path.exists():
        result = subprocess.run(
            ['python3', str(script_path), '--help'],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"Script failed: {result.stderr}"
        assert 'generate' in result.stdout, "Missing 'generate' subcommand in help"


def test_verify_script_help():
    """Verify script shows help."""
    script_path = SCRIPTS_DIR / "verify-executor.py"

    if script_path.exists():
        result = subprocess.run(
            ['python3', str(script_path), '--help'],
            capture_output=True,
            text=True
        )

        assert result.returncode == 0, f"Script failed: {result.stderr}"
        assert 'check' in result.stdout, "Missing 'check' subcommand in help"
