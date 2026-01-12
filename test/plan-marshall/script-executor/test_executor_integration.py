#!/usr/bin/env python3
"""
Integration tests for generated execute-script.py executor.

Tests the full lifecycle:
1. Generate executor to a temp location
2. Execute scripts with various parameters
3. Verify log output for success and error cases
4. Clean up on teardown
"""

import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import TestRunner, MARKETPLACE_ROOT

# ============================================================================
# PATHS
# ============================================================================

SKILL_DIR = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'script-executor'
SCRIPTS_DIR = SKILL_DIR / 'scripts'
TEMPLATES_DIR = SKILL_DIR / 'templates'
EXECUTOR_TEMPLATE = TEMPLATES_DIR / 'execute-script.py.template'
LOGGING_DIR = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'logging' / 'scripts'

# A simple script that we know exists for testing
TEST_SCRIPT_BUNDLE = 'pm-workflow'
TEST_SCRIPT_SKILL = 'manage-config'
TEST_SCRIPT_PATH = MARKETPLACE_ROOT / TEST_SCRIPT_BUNDLE / 'skills' / TEST_SCRIPT_SKILL / 'scripts' / 'manage-config.py'


# ============================================================================
# TEST FIXTURES
# ============================================================================

class ExecutorTestEnvironment:
    """
    Manages a temporary test environment for executor integration tests.

    Creates an isolated .plan directory structure with:
    - Generated execute-script.py
    - logs/ directory for execution logs
    - PLAN_BASE_DIR environment variable set for isolation
    """

    def __init__(self):
        self.temp_dir = None
        self.plan_dir = None
        self.executor_path = None
        self.logs_dir = None
        self._original_cwd = None
        self._original_plan_base_dir = None

    def setup(self):
        """Create temp environment and generate executor."""
        # Create temp directory
        self.temp_dir = Path(tempfile.mkdtemp(prefix='executor_test_'))
        self.plan_dir = self.temp_dir / '.plan'
        self.plan_dir.mkdir()
        self.logs_dir = self.plan_dir / 'logs'
        self.logs_dir.mkdir()

        # Set PLAN_BASE_DIR for test isolation (execution_log.py reads this)
        self._original_plan_base_dir = os.environ.get('PLAN_BASE_DIR')
        os.environ['PLAN_BASE_DIR'] = str(self.plan_dir)

        # Generate executor with test mappings
        self._generate_test_executor()

        # Save original cwd and change to temp dir
        self._original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

        return self

    def _generate_test_executor(self):
        """Generate executor with embedded mappings for testing."""
        template_content = EXECUTOR_TEMPLATE.read_text()

        # Build mappings for a few real scripts
        mappings = self._discover_test_scripts()
        mappings_code = self._format_mappings(mappings)

        # Replace placeholders
        executor_content = template_content.replace(
            '{{SCRIPT_MAPPINGS}}',
            mappings_code
        )
        # Point to real plan_logging.py location (isolation via PLAN_BASE_DIR env var)
        executor_content = executor_content.replace(
            '{{LOGGING_DIR}}',
            str(LOGGING_DIR)  # Real marketplace location for plan_logging module
        )

        self.executor_path = self.plan_dir / 'execute-script.py'
        self.executor_path.write_text(executor_content)

        # Store mappings for verification
        self.script_mappings = mappings

    def _discover_test_scripts(self) -> dict:
        """Discover a subset of scripts for testing."""
        mappings = {}

        # Add specific scripts we want to test
        test_scripts = [
            ('pm-workflow', 'manage-config', 'manage-config.py'),
            ('pm-workflow', 'manage-lifecycle', 'manage-lifecycle.py'),
            ('plan-marshall', 'toon-usage', 'toon_parser.py'),
        ]

        for bundle, skill, script in test_scripts:
            script_path = MARKETPLACE_ROOT / bundle / 'skills' / skill / 'scripts' / script
            if script_path.exists():
                notation = f"{bundle}:{skill}"
                mappings[notation] = str(script_path.resolve())

        # Add a fake script for error testing
        mappings['test:nonexistent'] = '/nonexistent/path/script.py'

        return mappings

    def _format_mappings(self, mappings: dict) -> str:
        """Format mappings as Python dict entries."""
        lines = []
        for notation, path in sorted(mappings.items()):
            lines.append(f'    "{notation}": "{path}",')
        return '\n'.join(lines)

    def teardown(self):
        """Clean up temp environment."""
        if self._original_cwd:
            os.chdir(self._original_cwd)

        # Restore original PLAN_BASE_DIR
        if self._original_plan_base_dir is not None:
            os.environ['PLAN_BASE_DIR'] = self._original_plan_base_dir
        elif 'PLAN_BASE_DIR' in os.environ:
            del os.environ['PLAN_BASE_DIR']

        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def run_executor(self, *args, timeout: int = 30) -> subprocess.CompletedProcess:
        """Run the generated executor with arguments."""
        # Pass PLAN_BASE_DIR to subprocess for test isolation
        env = os.environ.copy()
        env['PLAN_BASE_DIR'] = str(self.plan_dir)
        return subprocess.run(
            [sys.executable, str(self.executor_path)] + list(args),
            capture_output=True,
            text=True,
            cwd=self.temp_dir,
            timeout=timeout,
            env=env
        )

    def get_log_content(self) -> str:
        """Get content of today's execution log."""
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = self.logs_dir / f'script-execution-{today}.log'
        if log_file.exists():
            return log_file.read_text()
        return ''

    def clear_logs(self):
        """Clear all log files."""
        for log_file in self.logs_dir.glob('*.log'):
            log_file.unlink()


# Global test environment (created once per test run)
_test_env = None


def get_test_env() -> ExecutorTestEnvironment:
    """Get or create the test environment."""
    global _test_env
    if _test_env is None:
        _test_env = ExecutorTestEnvironment()
        _test_env.setup()
    return _test_env


def cleanup_test_env():
    """Clean up test environment at end of test run."""
    global _test_env
    if _test_env is not None:
        _test_env.teardown()
        _test_env = None


# ============================================================================
# TESTS: Executor Generation
# ============================================================================

def test_executor_generated_successfully():
    """Executor is generated and is valid Python."""
    env = get_test_env()

    assert env.executor_path.exists(), f"Executor not found at {env.executor_path}"

    # Verify it's valid Python
    result = subprocess.run(
        [sys.executable, '-m', 'py_compile', str(env.executor_path)],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0, f"Executor syntax error: {result.stderr}"


def test_executor_contains_mappings():
    """Executor contains expected script mappings."""
    env = get_test_env()

    content = env.executor_path.read_text()

    # Check for expected notations
    assert 'pm-workflow:manage-config' in content, "Missing pm-workflow:manage-config mapping"
    assert 'SCRIPTS = {' in content, "Missing SCRIPTS dict"


def test_executor_list_command():
    """Executor --list shows all registered scripts."""
    env = get_test_env()

    result = env.run_executor('--list')

    assert result.returncode == 0, f"--list failed: {result.stderr}"

    # Should list our test scripts
    output = result.stdout
    assert 'pm-workflow:manage-config' in output, f"Missing pm-workflow:manage-config in list: {output}"


# ============================================================================
# TESTS: Successful Execution
# ============================================================================

def test_execute_script_help():
    """Execute a script with --help (should succeed)."""
    env = get_test_env()
    env.clear_logs()

    result = env.run_executor('pm-workflow:manage-config', '--help')

    # --help typically exits with 0
    assert result.returncode == 0, f"Script --help failed: {result.stderr}"
    assert 'usage' in result.stdout.lower() or 'help' in result.stdout.lower(), \
        f"Expected help output, got: {result.stdout}"


def test_execute_script_with_subcommand():
    """Execute a script with a valid subcommand."""
    env = get_test_env()
    env.clear_logs()

    # manage-lifecycle has a 'status' subcommand that should work without a real plan
    result = env.run_executor('pm-workflow:manage-lifecycle', '--help')

    assert result.returncode == 0, f"Script failed: {result.stderr}"


def test_successful_execution_logged():
    """Successful execution creates a log entry."""
    env = get_test_env()
    env.clear_logs()

    # Execute something that succeeds
    result = env.run_executor('pm-workflow:manage-config', '--help')
    assert result.returncode == 0, f"Script failed: {result.stderr}"

    # Check log was created
    log_content = env.get_log_content()
    assert 'pm-workflow:manage-config' in log_content, f"Missing log entry. Log content: {log_content}"
    assert '[INFO]' in log_content, f"Expected INFO marker in log: {log_content}"


def test_log_format_success_compact():
    """Success log entries are compact (single line)."""
    env = get_test_env()
    env.clear_logs()

    env.run_executor('pm-workflow:manage-config', '--help')

    log_content = env.get_log_content()

    # Success entries should be single line with bracket format
    # Format: [timestamp] [INFO] notation subcommand (duration)
    lines = [line for line in log_content.strip().split('\n') if 'pm-workflow:manage-config' in line]
    assert len(lines) >= 1, "No log entry found for pm-workflow:manage-config"

    entry = lines[0]
    # Check bracket format
    assert '[INFO]' in entry, f"Expected [INFO] marker, got: {entry}"
    assert entry.startswith('['), f"Entry should start with timestamp bracket: {entry}"

    # Should NOT contain ERROR marker for success
    assert '[ERROR]' not in entry, f"Success entry should not contain [ERROR]: {entry}"


# ============================================================================
# TESTS: Error Execution
# ============================================================================

def test_execute_nonexistent_script():
    """Executing nonexistent script returns error."""
    env = get_test_env()

    result = env.run_executor('test:nonexistent', 'subcommand')

    assert result.returncode != 0, "Expected non-zero exit for nonexistent script"
    assert 'SCRIPT_ERROR' in result.stderr or 'not found' in result.stderr.lower(), \
        f"Expected error message, got: {result.stderr}"


def test_execute_unknown_notation():
    """Executing unknown notation returns error."""
    env = get_test_env()

    result = env.run_executor('unknown:notation', 'subcommand')

    assert result.returncode != 0, "Expected non-zero exit for unknown notation"
    assert 'SCRIPT_ERROR' in result.stderr or 'Unknown notation' in result.stderr, \
        f"Expected unknown notation error, got: {result.stderr}"


def test_execute_script_that_fails():
    """Execute a script that exits with non-zero code."""
    env = get_test_env()
    env.clear_logs()

    # manage-config 'get' without required --plan-id should fail
    result = env.run_executor('pm-workflow:manage-config', 'get')

    # This should fail because no --plan-id provided
    assert result.returncode != 0, "Expected non-zero exit for missing required args"

    # Verify error was logged
    log_content = env.get_log_content()
    assert 'pm-workflow:manage-config' in log_content, f"Missing log entry for failed execution: {log_content}"
    # Error entries have [ERROR] marker, not [SUCCESS]
    assert '[ERROR]' in log_content, f"Expected [ERROR] marker in log: {log_content}"


def test_error_execution_logged_with_details():
    """Error execution creates detailed log entry with args."""
    env = get_test_env()
    env.clear_logs()

    # Execute something that fails - use a command that definitely fails
    result = env.run_executor('pm-workflow:manage-config', 'get', '--plan-id', 'nonexistent-plan-xyz')

    # This should fail (plan doesn't exist)
    assert result.returncode != 0, "Expected non-zero exit for nonexistent plan"

    log_content = env.get_log_content()
    assert 'pm-workflow:manage-config' in log_content, f"Missing log entry: {log_content}"

    # Error entries should contain [ERROR] marker and args detail
    assert '[ERROR]' in log_content, f"Expected [ERROR] marker in log: {log_content}"
    assert 'args:' in log_content, f"Error entry missing args detail: {log_content}"
    assert 'nonexistent-plan-xyz' in log_content, f"Args should include plan-id: {log_content}"


def test_log_format_error_multi_line():
    """Error log entries are multi-line with detailed info."""
    env = get_test_env()
    env.clear_logs()

    # Execute with invalid arguments to force error
    result = env.run_executor('pm-workflow:manage-config', 'get', '--plan-id', 'test-error-format')
    assert result.returncode != 0, "Expected failure"

    log_content = env.get_log_content()

    # Error entries should span multiple lines
    lines = log_content.strip().split('\n')
    error_lines = [l for l in lines if 'pm-workflow:manage-config' in l or l.startswith('  ')]

    # Should have at least the main entry line + args line
    assert len(error_lines) >= 2, f"Expected multi-line error entry, got: {error_lines}"

    # First line should have [ERROR] marker
    assert '[ERROR]' in error_lines[0], f"First line should have [ERROR]: {error_lines[0]}"

    # Should have indented detail lines
    indented_lines = [l for l in error_lines if l.startswith('  ')]
    assert len(indented_lines) >= 1, f"Expected indented detail lines: {error_lines}"


# ============================================================================
# TESTS: Argument Forwarding
# ============================================================================

def test_arguments_forwarded_correctly():
    """Arguments are correctly forwarded to the script."""
    env = get_test_env()

    # Use --help which should be forwarded
    result = env.run_executor('pm-workflow:manage-config', '--help')

    assert result.returncode == 0
    assert '--help' not in result.stderr, "Help flag should be consumed by target script"


def test_subcommand_forwarded():
    """Subcommand is correctly forwarded."""
    env = get_test_env()

    # The subcommand 'get' should be forwarded to manage-config
    result = env.run_executor('pm-workflow:manage-config', 'get', '--help')

    # Should get help for the 'get' subcommand
    assert result.returncode == 0


def test_complex_arguments_forwarded():
    """Complex arguments with values are forwarded to script."""
    env = get_test_env()
    env.clear_logs()

    # Test with multiple argument types (use correct arg name --field)
    result = env.run_executor(
        'pm-workflow:manage-config',
        'get',
        '--plan-id', 'test-arg-forward',
        '--field', 'some.nested.field'
    )

    # Will fail because plan doesn't exist, but args should be forwarded
    # We verify by checking the log contains our specific args
    log_content = env.get_log_content()
    assert 'test-arg-forward' in log_content, f"plan-id arg not forwarded: {log_content}"
    assert 'some.nested.field' in log_content, f"field arg not forwarded: {log_content}"

    # Also verify script received the args (it will fail for nonexistent plan)
    assert result.returncode != 0, "Should fail for nonexistent plan"
    # The error should be about the plan not existing, not about missing args
    assert 'required' not in result.stderr.lower() or 'test-arg-forward' in result.stderr, \
        f"All required args should have been provided: {result.stderr}"


# ============================================================================
# TESTS: Edge Cases
# ============================================================================

def test_no_arguments_shows_usage():
    """Running executor without arguments shows usage."""
    env = get_test_env()

    result = env.run_executor()

    assert result.returncode != 0, "Should fail without arguments"
    assert 'Usage' in result.stderr or 'usage' in result.stderr, \
        f"Expected usage message, got: {result.stderr}"


def test_partial_notation_resolution():
    """Partial notation resolves to first matching script."""
    env = get_test_env()

    # The executor has fuzzy matching - 'pm-workflow' should match 'planning:*'
    result = env.run_executor('pm-workflow', '--help')

    # Should resolve to first planning:* script and succeed with --help
    assert result.returncode == 0, f"Partial notation resolution failed: {result.stderr}"

    # Output should be help from one of the planning scripts
    assert 'usage' in result.stdout.lower() or len(result.stdout) > 0, \
        f"Expected help output from resolved script: {result.stdout}"


def test_partial_notation_matches_substring():
    """Partial notation matches substring in script notation."""
    env = get_test_env()

    # 'manage-config' should match 'pm-workflow:manage-config'
    result = env.run_executor('manage-config', '--help')

    # Should resolve and show help
    assert result.returncode == 0, f"Substring notation resolution failed: {result.stderr}"


def test_multiple_executions_append_to_log():
    """Multiple executions append to the same log file."""
    env = get_test_env()
    env.clear_logs()

    # Execute multiple times
    env.run_executor('pm-workflow:manage-config', '--help')
    env.run_executor('pm-workflow:manage-config', '--help')
    env.run_executor('pm-workflow:manage-config', '--help')

    log_content = env.get_log_content()

    # Count occurrences
    count = log_content.count('pm-workflow:manage-config')
    assert count >= 3, f"Expected at least 3 log entries, found {count}"


# ============================================================================
# TESTS: Log Location (Plan-Scoped vs Global)
# ============================================================================

def test_global_log_used_without_plan_id():
    """Global log is used when no --plan-id provided."""
    env = get_test_env()
    env.clear_logs()

    result = env.run_executor('pm-workflow:manage-config', '--help')
    assert result.returncode == 0

    # Check global log exists
    today = datetime.now().strftime('%Y-%m-%d')
    global_log = env.logs_dir / f'script-execution-{today}.log'
    assert global_log.exists(), f"Global log not created at {global_log}"


def test_plan_scoped_log_when_plan_exists():
    """Plan-scoped log is used when --plan-id provided and plan exists."""
    env = get_test_env()

    # Create a fake plan directory
    plan_id = 'test-integration-plan'
    plan_dir = env.plan_dir / 'plans' / plan_id
    plan_dir.mkdir(parents=True)

    try:
        env.clear_logs()

        env.run_executor(
            'pm-workflow:manage-config',
            'get',
            '--plan-id', plan_id,
            '--key', 'test'
        )

        # Check if plan-scoped log was created
        plan_log = plan_dir / 'script-execution.log'
        assert plan_log.exists(), f"Plan-scoped log not created at {plan_log}"

        log_content = plan_log.read_text()
        assert 'pm-workflow:manage-config' in log_content, \
            f"Plan log missing entry: {log_content}"

        # Verify plan-id appears in plan log, confirming it went to the right place
        assert plan_id in log_content, f"Plan-id should appear in plan-scoped log: {log_content}"

    finally:
        # Cleanup
        shutil.rmtree(plan_dir, ignore_errors=True)


# ============================================================================
# TEST RUNNER
# ============================================================================

if __name__ == '__main__':
    runner = TestRunner()
    runner.add_tests([
        # Generation tests
        test_executor_generated_successfully,
        test_executor_contains_mappings,
        test_executor_list_command,
        # Success execution tests
        test_execute_script_help,
        test_execute_script_with_subcommand,
        test_successful_execution_logged,
        test_log_format_success_compact,
        # Error execution tests
        test_execute_nonexistent_script,
        test_execute_unknown_notation,
        test_execute_script_that_fails,
        test_error_execution_logged_with_details,
        test_log_format_error_multi_line,
        # Argument forwarding tests
        test_arguments_forwarded_correctly,
        test_subcommand_forwarded,
        test_complex_arguments_forwarded,
        # Edge case tests
        test_no_arguments_shows_usage,
        test_partial_notation_resolution,
        test_partial_notation_matches_substring,
        test_multiple_executions_append_to_log,
        # Log location tests
        test_global_log_used_without_plan_id,
        test_plan_scoped_log_when_plan_exists,
    ])

    try:
        exit_code = runner.run()
    finally:
        # Always cleanup
        cleanup_test_env()

    sys.exit(exit_code)
