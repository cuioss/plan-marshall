#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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

import pytest

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import _MARKETPLACE_SCRIPT_DIRS, MARKETPLACE_ROOT

SKILL_DIR = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'tools-script-executor'
SCRIPTS_DIR = SKILL_DIR / 'scripts'
TEMPLATES_DIR = SKILL_DIR / 'templates'
EXECUTOR_TEMPLATE = TEMPLATES_DIR / 'execute-script.py.template'
LOGGING_DIR = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'logging' / 'scripts'

# A simple script that we know exists for testing
TEST_SCRIPT_BUNDLE = 'plan-marshall'
TEST_SCRIPT_SKILL = 'manage-references'
TEST_SCRIPT_PATH = (
    MARKETPLACE_ROOT / TEST_SCRIPT_BUNDLE / 'skills' / TEST_SCRIPT_SKILL / 'scripts' / 'manage-references.py'
)


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
        self._monkeypatch = None

    def setup(self):
        """Create temp environment and generate executor."""
        # Create temp directory
        self.temp_dir = Path(tempfile.mkdtemp(prefix='executor_test_'))
        self.plan_dir = self.temp_dir / '.plan'
        self.plan_dir.mkdir()
        self.logs_dir = self.plan_dir / 'logs'
        self.logs_dir.mkdir()

        # Set PLAN_BASE_DIR for test isolation (execution_log.py reads this).
        # A manually instantiated MonkeyPatch is used because the built-in
        # monkeypatch fixture is function-scoped and cannot be requested from
        # the module-scoped fixture that owns this environment (ScopeMismatch).
        self._monkeypatch = pytest.MonkeyPatch()
        self._monkeypatch.setenv('PLAN_BASE_DIR', str(self.plan_dir))

        # Generate executor with test mappings
        self._generate_test_executor()

        return self

    def _generate_test_executor(self):
        """Generate executor with embedded mappings for testing."""
        template_content = EXECUTOR_TEMPLATE.read_text()

        # Build mappings for a few real scripts
        mappings = self._discover_test_scripts()
        mappings_code = self._format_mappings(mappings)

        # Replace placeholders
        executor_content = template_content.replace('{{SCRIPT_MAPPINGS}}', mappings_code)
        # Pre-flight validator placeholder — tests render with empty subcommand
        # surface; the validator is exercised in dedicated tests.
        executor_content = executor_content.replace('{{SUBCOMMAND_MAPPINGS}}', '')
        # Point to real plan_logging.py location (isolation via PLAN_BASE_DIR env var)
        executor_content = executor_content.replace(
            '{{LOGGING_DIR}}',
            str(LOGGING_DIR),  # Real marketplace location for plan_logging module
        )
        # Shared module directories (input_validation etc.) — emitted as
        # (skill, pinned_dir) tuple entries per the _BOOTSTRAP_SKILL_DIRS
        # contract (see generate_executor.get_shared_module_dirs()).
        input_validation_dir = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'tools-input-validation' / 'scripts'
        executor_content = executor_content.replace(
            '{{SHARED_MODULE_DIRS}}',
            f"    ('tools-input-validation', '{input_validation_dir}'),"
            if input_validation_dir.is_dir()
            else '    # (none in test)',
        )
        executor_content = executor_content.replace('{{EXTRA_SCRIPT_DIRS}}', '')
        executor_content = executor_content.replace('{{PLAN_DIR_NAME}}', '.plan')
        executor_content = executor_content.replace('{{EXECUTOR_TARGET}}', 'claude')
        executor_content = executor_content.replace(
            '{{TARGET_AWARE_RESOLVER}}',
            'def _resolve_notation_by_target(notation):\n    return None\n',
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
            ('plan-marshall', 'manage-references', 'manage-references.py'),
            ('plan-marshall', 'manage-status', 'manage-status.py'),
            ('plan-marshall', 'toon-usage', 'toon_parser.py'),
        ]

        for bundle, skill, script in test_scripts:
            script_path = MARKETPLACE_ROOT / bundle / 'skills' / skill / 'scripts' / script
            if script_path.exists():
                notation = f'{bundle}:{skill}'
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
        if self._monkeypatch is not None:
            self._monkeypatch.undo()
            self._monkeypatch = None

        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def run_executor(self, *args, timeout: int = 30) -> subprocess.CompletedProcess:
        """Run the generated executor with arguments."""
        # Pass PLAN_BASE_DIR and PYTHONPATH to subprocess for test isolation
        env = os.environ.copy()
        env['PLAN_BASE_DIR'] = str(self.plan_dir)
        # Include full marketplace PYTHONPATH for cross-skill imports
        pythonpath = os.pathsep.join(_MARKETPLACE_SCRIPT_DIRS)
        if 'PYTHONPATH' in env:
            pythonpath = pythonpath + os.pathsep + env['PYTHONPATH']
        env['PYTHONPATH'] = pythonpath
        return subprocess.run(
            [sys.executable, str(self.executor_path)] + list(args),
            capture_output=True,
            text=True,
            cwd=self.temp_dir,
            timeout=timeout,
            env=env,
        )

    def get_log_content(self) -> str:
        """Get content of today's execution log."""
        today = datetime.now().strftime('%Y-%m-%d')
        log_file = self.logs_dir / f'script-execution-{today}.log'
        if log_file.exists():
            content: str = log_file.read_text()
            return content
        return ''

    def clear_logs(self):
        """Clear all log files."""
        for log_file in self.logs_dir.glob('*.log'):
            log_file.unlink()


@pytest.fixture(scope='module')
def env():
    """One executor test environment per module, torn down after the module."""
    test_env = ExecutorTestEnvironment()
    test_env.setup()
    try:
        yield test_env
    finally:
        test_env.teardown()


def test_executor_generated_successfully(env):
    """Executor is generated and is valid Python."""
    assert env.executor_path.exists(), f'Executor not found at {env.executor_path}'

    # Verify it's valid Python
    result = subprocess.run(
        [sys.executable, '-m', 'py_compile', str(env.executor_path)], capture_output=True, text=True
    )
    assert result.returncode == 0, f'Executor syntax error: {result.stderr}'


def test_executor_contains_mappings(env):
    """Executor contains expected script mappings."""
    content = env.executor_path.read_text()

    # Check for expected notations
    assert 'plan-marshall:manage-references' in content, 'Missing plan-marshall:manage-references mapping'
    assert 'SCRIPTS = {' in content, 'Missing SCRIPTS dict'


def test_executor_list_command(env):
    """Executor --list shows all registered scripts."""
    result = env.run_executor('--list')

    assert result.returncode == 0, f'--list failed: {result.stderr}'

    # Should list our test scripts
    output = result.stdout
    assert 'plan-marshall:manage-references' in output, f'Missing plan-marshall:manage-references in list: {output}'


def test_execute_script_help(env):
    """Execute a script with --help (should succeed)."""
    env.clear_logs()

    result = env.run_executor('plan-marshall:manage-references', '--help')

    # --help typically exits with 0
    assert result.returncode == 0, f'Script --help failed: {result.stderr}'
    assert 'usage' in result.stdout.lower() or 'help' in result.stdout.lower(), (
        f'Expected help output, got: {result.stdout}'
    )


def test_execute_script_with_subcommand(env):
    """Execute a script with a valid subcommand."""
    env.clear_logs()

    # manage-references has a --help that works without a real plan
    result = env.run_executor('plan-marshall:manage-references', '--help')

    assert result.returncode == 0, f'Script failed: {result.stderr}'


def test_successful_execution_logged(env):
    """Successful execution creates a log entry."""
    env.clear_logs()

    # Execute something that succeeds
    result = env.run_executor('plan-marshall:manage-references', '--help')
    assert result.returncode == 0, f'Script failed: {result.stderr}'

    # Check log was created
    log_content = env.get_log_content()
    assert 'plan-marshall:manage-references' in log_content, f'Missing log entry. Log content: {log_content}'
    assert '[INFO]' in log_content, f'Expected INFO marker in log: {log_content}'


def test_log_format_success_compact(env):
    """Success log entries are compact (single line)."""
    env.clear_logs()

    env.run_executor('plan-marshall:manage-references', '--help')

    log_content = env.get_log_content()

    # Success entries should be single line with bracket format
    # Format: [timestamp] [INFO] notation subcommand (duration)
    lines = [line for line in log_content.strip().split('\n') if 'plan-marshall:manage-references' in line]
    assert len(lines) >= 1, 'No log entry found for plan-marshall:manage-references'

    entry = lines[0]
    # Check bracket format
    assert '[INFO]' in entry, f'Expected [INFO] marker, got: {entry}'
    assert entry.startswith('['), f'Entry should start with timestamp bracket: {entry}'

    # Should NOT contain ERROR marker for success
    assert '[ERROR]' not in entry, f'Success entry should not contain [ERROR]: {entry}'


def test_execute_nonexistent_script(env):
    """Executing nonexistent script returns error."""
    result = env.run_executor('test:nonexistent', 'subcommand')

    assert result.returncode != 0, 'Expected non-zero exit for nonexistent script'
    assert 'SCRIPT_ERROR' in result.stderr or 'not found' in result.stderr.lower(), (
        f'Expected error message, got: {result.stderr}'
    )


def test_execute_unknown_notation(env):
    """Executing unknown notation returns error."""
    result = env.run_executor('unknown:notation', 'subcommand')

    assert result.returncode != 0, 'Expected non-zero exit for unknown notation'
    assert 'SCRIPT_ERROR' in result.stderr or 'Unknown notation' in result.stderr, (
        f'Expected unknown notation error, got: {result.stderr}'
    )


def test_execute_script_that_fails(env):
    """Execute a script that exits with non-zero code."""
    env.clear_logs()

    # manage-references 'get' without required --plan-id should fail
    result = env.run_executor('plan-marshall:manage-references', 'get')

    # This should fail because no --plan-id provided
    assert result.returncode != 0, 'Expected non-zero exit for missing required args'

    # Verify error was logged
    log_content = env.get_log_content()
    assert 'plan-marshall:manage-references' in log_content, f'Missing log entry for failed execution: {log_content}'
    # Error entries have [ERROR] marker, not [SUCCESS]
    assert '[ERROR]' in log_content, f'Expected [ERROR] marker in log: {log_content}'


def test_error_execution_logged_with_details(env):
    """Error execution creates detailed log entry with args."""
    env.clear_logs()

    # Execute something that fails - use a command that definitely fails
    result = env.run_executor('plan-marshall:manage-references', 'get', '--plan-id', 'nonexistent-plan-xyz')

    # This should fail (plan doesn't exist)
    assert result.returncode != 0, 'Expected non-zero exit for nonexistent plan'

    log_content = env.get_log_content()
    assert 'plan-marshall:manage-references' in log_content, f'Missing log entry: {log_content}'

    # Error entries should contain [ERROR] marker and args detail
    assert '[ERROR]' in log_content, f'Expected [ERROR] marker in log: {log_content}'
    assert 'args:' in log_content, f'Error entry missing args detail: {log_content}'
    assert 'nonexistent-plan-xyz' in log_content, f'Args should include plan-id: {log_content}'


def test_log_format_error_multi_line(env):
    """Error log entries are multi-line with detailed info."""
    env.clear_logs()

    # Execute with invalid arguments to force error
    result = env.run_executor('plan-marshall:manage-references', 'get', '--plan-id', 'test-error-format')
    assert result.returncode != 0, 'Expected failure'

    log_content = env.get_log_content()

    # Error entries should span multiple lines
    lines = log_content.strip().split('\n')
    error_lines = [line for line in lines if 'plan-marshall:manage-references' in line or line.startswith('  ')]

    # Should have at least the main entry line + args line
    assert len(error_lines) >= 2, f'Expected multi-line error entry, got: {error_lines}'

    # First line should have [ERROR] marker
    assert '[ERROR]' in error_lines[0], f'First line should have [ERROR]: {error_lines[0]}'

    # Should have indented detail lines
    indented_lines = [line for line in error_lines if line.startswith('  ')]
    assert len(indented_lines) >= 1, f'Expected indented detail lines: {error_lines}'


def test_arguments_forwarded_correctly(env):
    """Arguments are correctly forwarded to the script."""
    # Use --help which should be forwarded
    result = env.run_executor('plan-marshall:manage-references', '--help')

    assert result.returncode == 0
    assert '--help' not in result.stderr, 'Help flag should be consumed by target script'


def test_subcommand_forwarded(env):
    """Subcommand is correctly forwarded."""
    # The subcommand 'get' should be forwarded to manage-references
    result = env.run_executor('plan-marshall:manage-references', 'get', '--help')

    # Should get help for the 'get' subcommand
    assert result.returncode == 0


def test_complex_arguments_forwarded(env):
    """Complex arguments with values are forwarded to script."""
    env.clear_logs()

    # Test with multiple argument types (use correct arg name --field)
    result = env.run_executor(
        'plan-marshall:manage-references', 'get', '--plan-id', 'test-arg-forward', '--field', 'some.nested.field'
    )

    # Script exits 0 with TOON error for nonexistent plan (expected condition)
    # Args were forwarded because the script received them and produced a meaningful error
    assert result.returncode == 0, 'Should exit 0 with TOON error output'
    assert 'status: error' in result.stdout, 'Should contain TOON error for missing references'

    # Verify executor logged the invocation
    log_content = env.get_log_content()
    assert 'plan-marshall:manage-references' in log_content, f'Script notation not logged: {log_content}'


def test_no_arguments_shows_usage(env):
    """Running executor without arguments shows usage."""
    result = env.run_executor()

    assert result.returncode != 0, 'Should fail without arguments'
    assert 'Usage' in result.stderr or 'usage' in result.stderr, f'Expected usage message, got: {result.stderr}'


def test_partial_notation_resolution(env):
    """Partial notation resolves to first matching script."""
    # The executor has fuzzy matching - 'plan-marshall' should match 'planning:*'
    result = env.run_executor('plan-marshall', '--help')

    # Should resolve to first planning:* script and succeed with --help
    assert result.returncode == 0, f'Partial notation resolution failed: {result.stderr}'

    # Output should be help from one of the planning scripts
    assert 'usage' in result.stdout.lower() or len(result.stdout) > 0, (
        f'Expected help output from resolved script: {result.stdout}'
    )


def test_partial_notation_matches_substring(env):
    """Partial notation matches substring in script notation."""
    # 'manage-references' should match 'plan-marshall:manage-references'
    result = env.run_executor('manage-references', '--help')

    # Should resolve and show help
    assert result.returncode == 0, f'Substring notation resolution failed: {result.stderr}'


def test_multiple_executions_append_to_log(env):
    """Multiple executions append to the same log file."""
    env.clear_logs()

    # Execute multiple times
    env.run_executor('plan-marshall:manage-references', '--help')
    env.run_executor('plan-marshall:manage-references', '--help')
    env.run_executor('plan-marshall:manage-references', '--help')

    log_content = env.get_log_content()

    # Count occurrences
    count = log_content.count('plan-marshall:manage-references')
    assert count >= 3, f'Expected at least 3 log entries, found {count}'


def test_global_log_used_without_plan_id(env):
    """Global log is used when no --plan-id provided."""
    env.clear_logs()

    result = env.run_executor('plan-marshall:manage-references', '--help')
    assert result.returncode == 0

    # Check global log exists
    today = datetime.now().strftime('%Y-%m-%d')
    global_log = env.logs_dir / f'script-execution-{today}.log'
    assert global_log.exists(), f'Global log not created at {global_log}'


def test_plan_scoped_log_when_plan_exists(env):
    """Plan-scoped log is used when --plan-id provided and plan exists."""
    # Create a fake plan directory with status.json sentinel so
    # get_log_path() treats it as an initialized plan (not a bare orphan).
    plan_id = 'test-integration-plan'
    plan_dir = env.plan_dir / 'plans' / plan_id
    plan_dir.mkdir(parents=True)
    (plan_dir / 'status.json').write_text('{}', encoding='utf-8')

    try:
        env.clear_logs()

        env.run_executor('plan-marshall:manage-references', 'get', '--plan-id', plan_id, '--field', 'branch')

        # Check if plan-scoped log was created (now in logs/ subdirectory)
        plan_log = plan_dir / 'logs' / 'script-execution.log'
        assert plan_log.exists(), f'Plan-scoped log not created at {plan_log}'

        log_content = plan_log.read_text()
        assert 'plan-marshall:manage-references' in log_content, f'Plan log missing entry: {log_content}'

    finally:
        # Cleanup
        shutil.rmtree(plan_dir, ignore_errors=True)
