#!/usr/bin/env python3
"""Unit tests for await-until.py synchronous polling utility."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import _MARKETPLACE_SCRIPT_DIRS, get_script_path, run_script

# Path to the script
SCRIPT_PATH = get_script_path('plan-marshall', 'script-executor', 'await-until.py')


# =============================================================================
# Helper Functions
# =============================================================================

def run_with_pythonpath(args, cwd=None, env=None, timeout=30):
    """Run subprocess with marketplace PYTHONPATH set."""
    run_env = (env or os.environ).copy()
    pythonpath = os.pathsep.join(_MARKETPLACE_SCRIPT_DIRS)
    if 'PYTHONPATH' in run_env:
        pythonpath = pythonpath + os.pathsep + run_env['PYTHONPATH']
    run_env['PYTHONPATH'] = pythonpath
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        cwd=cwd,
        env=run_env,
        timeout=timeout
    )


def parse_toon_result(stdout: str) -> dict:
    """Parse TOON output (key: value format) into dict."""
    result = {}
    for line in stdout.strip().split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            value = value.strip()
            # Strip quotes if present
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            result[key.strip()] = value
    return result


# =============================================================================
# TESTS: Help output
# =============================================================================

def test_help_output():
    """Script shows help with all options."""
    result = run_script(SCRIPT_PATH, '--help')
    assert result.success, f"Script failed: {result.stderr}"
    assert '--check-cmd' in result.stdout, "Help should mention --check-cmd"
    assert '--success-field' in result.stdout, "Help should mention --success-field"
    assert '--command-key' in result.stdout, "Help should mention --command-key"


# =============================================================================
# TESTS: Immediate success
# =============================================================================

def test_immediate_success():
    """Poll returns success on first check if condition satisfied."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create run-configuration.json
        config_path = Path(tmpdir) / '.plan' / 'run-configuration.json'
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps({"version": 1, "commands": {}}))

        result = run_with_pythonpath(
            [sys.executable, str(SCRIPT_PATH),
             '--check-cmd', "printf 'status: success\\n'",
             '--success-field', 'status=success',
             '--command-key', 'test:immediate',
             '--interval', '1'],
            cwd=tmpdir
        )
        assert result.returncode == 0, f"Script failed: {result.stderr}"

        parsed = parse_toon_result(result.stdout)
        assert parsed.get('status') == 'success', f"Expected status=success, got {parsed.get('status')}"
        assert parsed.get('polls') == '1', f"Expected 1 poll, got {parsed.get('polls')}"
        assert 'duration_seconds' in parsed, "Missing duration_seconds"


def test_success_with_different_field():
    """Poll checks custom success field."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / '.plan' / 'run-configuration.json'
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps({"version": 1, "commands": {}}))

        result = run_with_pythonpath(
            [sys.executable, str(SCRIPT_PATH),
             '--check-cmd', "printf 'state: completed\\nresult: passed\\n'",
             '--success-field', 'state=completed',
             '--command-key', 'test:custom',
             '--interval', '1'],
            cwd=tmpdir
        )
        assert result.returncode == 0, f"Script failed: {result.stderr}"

        parsed = parse_toon_result(result.stdout)
        assert parsed.get('status') == 'success'


# =============================================================================
# TESTS: Failure detection
# =============================================================================

def test_failure_detection():
    """Poll returns failure when failure condition matches."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / '.plan' / 'run-configuration.json'
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps({"version": 1, "commands": {}}))

        result = run_with_pythonpath(
            [sys.executable, str(SCRIPT_PATH),
             '--check-cmd', "printf 'status: failure\\nerror: Build failed\\n'",
             '--success-field', 'status=success',
             '--failure-field', 'status=failure',
             '--command-key', 'test:failure',
             '--interval', '1'],
            cwd=tmpdir
        )
        assert result.returncode != 0, "Should fail on failure condition"

        parsed = parse_toon_result(result.stdout)
        assert parsed.get('status') == 'failure', f"Expected status=failure, got {parsed.get('status')}"
        assert parsed.get('polls') == '1', "Should detect failure on first poll"


# =============================================================================
# TESTS: Multiple polls
# =============================================================================

def test_multiple_polls_before_success():
    """Poll continues until condition is satisfied."""
    # Create a script that returns pending first, then success
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('''#!/usr/bin/env python3
import os
import sys

state_file = sys.argv[1] if len(sys.argv) > 1 else '/tmp/poll_state.txt'

try:
    with open(state_file) as f:
        count = int(f.read().strip())
except:
    count = 0

count += 1
with open(state_file, 'w') as f:
    f.write(str(count))

if count >= 2:
    print("status: success")
else:
    print("status: pending")
''')
        temp_script = f.name

    state_file = tempfile.mktemp()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / '.plan' / 'run-configuration.json'
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(json.dumps({"version": 1, "commands": {}}))

            result = run_with_pythonpath(
                [sys.executable, str(SCRIPT_PATH),
                 '--check-cmd', f"python3 {temp_script} {state_file}",
                 '--success-field', 'status=success',
                 '--command-key', 'test:multipoll',
                 '--interval', '1'],
                cwd=tmpdir
            )
            assert result.returncode == 0, f"Script failed: {result.stderr}"

            parsed = parse_toon_result(result.stdout)
            polls = int(parsed.get('polls', 0))
            assert polls >= 2, f"Expected at least 2 polls, got {polls}"
    finally:
        os.unlink(temp_script)
        if os.path.exists(state_file):
            os.unlink(state_file)


# =============================================================================
# TESTS: Adaptive timeout with run-config
# =============================================================================

def test_adaptive_timeout_from_run_config():
    """Adaptive timeout uses run-config history."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create run-configuration.json with timeout_seconds
        run_config = {
            "version": 1,
            "commands": {
                "test:operation": {
                    "timeout_seconds": 100  # Will be multiplied by safety margin
                }
            }
        }
        config_path = Path(tmpdir) / '.plan' / 'run-configuration.json'
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(run_config))

        result = run_with_pythonpath(
            [sys.executable, str(SCRIPT_PATH),
             '--check-cmd', "printf 'status: success\\n'",
             '--success-field', 'status=success',
             '--command-key', 'test:operation',
             '--interval', '1'],
            cwd=tmpdir
        )
        assert result.returncode == 0, f"Script failed: {result.stderr}"

        parsed = parse_toon_result(result.stdout)
        assert parsed.get('status') == 'success'
        assert parsed.get('command_key') == 'test:operation'


def test_default_timeout_without_history():
    """Default timeout used when no run-config history."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create empty run-configuration.json
        run_config = {"version": 1, "commands": {}}
        config_path = Path(tmpdir) / '.plan' / 'run-configuration.json'
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(run_config))

        result = run_with_pythonpath(
            [sys.executable, str(SCRIPT_PATH),
             '--check-cmd', "printf 'status: success\\n'",
             '--success-field', 'status=success',
             '--command-key', 'unknown:operation',
             '--interval', '1'],
            cwd=tmpdir
        )
        assert result.returncode == 0, f"Script failed: {result.stderr}"

        parsed = parse_toon_result(result.stdout)
        assert parsed.get('status') == 'success'


def test_execution_history_updated():
    """Execution history is updated after successful poll."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create empty run-configuration.json
        run_config = {"version": 1, "commands": {}}
        config_path = Path(tmpdir) / '.plan' / 'run-configuration.json'
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(run_config))

        # Set PLAN_BASE_DIR so script writes to tmpdir
        env = os.environ.copy()
        env['PLAN_BASE_DIR'] = tmpdir

        result = run_with_pythonpath(
            [sys.executable, str(SCRIPT_PATH),
             '--check-cmd', "printf 'status: success\\n'",
             '--success-field', 'status=success',
             '--command-key', 'new:operation',
             '--interval', '1'],
            env=env
        )
        assert result.returncode == 0, f"Script failed: {result.stderr}"

        # Check run-config was updated with timeout_seconds
        updated_config = json.loads(config_path.read_text())
        assert 'new:operation' in updated_config.get('commands', {}), "Command entry should be created"
        cmd_entry = updated_config['commands']['new:operation']
        assert 'timeout_seconds' in cmd_entry, "timeout_seconds should be recorded"


# =============================================================================
# TESTS: Error handling
# =============================================================================

def test_missing_required_args():
    """Missing required arguments cause error."""
    result = run_script(SCRIPT_PATH, '--check-cmd', 'echo test')
    assert not result.success, "Should fail without --success-field and --command-key"
    assert 'required' in result.stderr.lower()


# =============================================================================
# TESTS: Case insensitive matching
# =============================================================================

def test_case_insensitive_matching():
    """Success/failure field matching is case insensitive."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / '.plan' / 'run-configuration.json'
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps({"version": 1, "commands": {}}))

        result = run_with_pythonpath(
            [sys.executable, str(SCRIPT_PATH),
             '--check-cmd', "printf 'status: SUCCESS\\n'",
             '--success-field', 'status=success',
             '--command-key', 'test:case',
             '--interval', '1'],
            cwd=tmpdir
        )
        assert result.returncode == 0, f"Should match SUCCESS to success: {result.stderr}"


# =============================================================================
# Main
# =============================================================================
