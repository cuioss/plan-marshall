#!/usr/bin/env python3
"""Unit tests for execute-script.py executor (template)."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from conftest import _MARKETPLACE_SCRIPT_DIRS, PlanContext


def _subprocess_env() -> dict[str, str]:
    """Build environment with PYTHONPATH for subprocess calls."""
    env = os.environ.copy()
    pythonpath = os.pathsep.join(_MARKETPLACE_SCRIPT_DIRS)
    if 'PYTHONPATH' in env:
        pythonpath = pythonpath + os.pathsep + env['PYTHONPATH']
    env['PYTHONPATH'] = pythonpath
    return env


# Path to templates and scripts
SKILL_DIR = (
    Path(__file__).parent.parent.parent.parent / 'marketplace/bundles/plan-marshall/skills/tools-script-executor'
)
TEMPLATE_DIR = SKILL_DIR / 'templates'
SCRIPTS_DIR = SKILL_DIR / 'scripts'
LOGGING_DIR = Path(__file__).parent.parent.parent.parent / 'marketplace/bundles/plan-marshall/skills/logging/scripts'


def load_executor_module():
    """Load the execute-script module from template for testing."""
    template_path = TEMPLATE_DIR / 'execute-script.py.template'
    with open(template_path) as f:
        code = f.read()

    # Replace the placeholders with test values
    code = code.replace(
        '{{SCRIPT_MAPPINGS}}',
        """
    "plan-marshall:manage-files": "/test/path/manage-files.py",
    "pm-dev-builder:builder-maven-rules": "/test/path/maven.py",
    "test:skill": "/test/path/test-skill.py",
""",
    )
    code = code.replace('{{SUBCOMMAND_MAPPINGS}}', '')
    code = code.replace('{{LOGGING_DIR}}', str(LOGGING_DIR))
    code = code.replace('{{SHARED_MODULE_DIRS}}', '# (none in test)')
    code = code.replace('{{EXTRA_SCRIPT_DIRS}}', '')
    code = code.replace('{{PLAN_DIR_NAME}}', '.plan')
    code = code.replace('{{EXECUTOR_TARGET}}', 'claude')
    code = code.replace(
        '{{TARGET_AWARE_RESOLVER}}',
        'def _resolve_notation_by_target(notation):\n    return None\n',
    )

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
    result = executor.resolve_notation('plan-marshall:manage-files')
    assert result == '/test/path/manage-files.py', f"Expected '/test/path/manage-files.py', got {result}"


def test_resolve_partial_match():
    """Resolve partial notation match."""
    executor = load_executor_module()
    result = executor.resolve_notation('plan-marshall')
    # Should find planning:manage-files
    assert result is not None, 'Expected a result for partial match'
    assert 'manage-files' in result, f"Expected 'manage-files' in result, got {result}"


def test_resolve_unknown_notation():
    """Return None for unknown notation."""
    executor = load_executor_module()
    result = executor.resolve_notation('unknown:script')
    assert result is None, f'Expected None for unknown notation, got {result}'


def test_resolve_all_mappings():
    """All mappings are available in SCRIPTS dict."""
    executor = load_executor_module()
    assert 'plan-marshall:manage-files' in executor.SCRIPTS
    assert 'pm-dev-builder:builder-maven-rules' in executor.SCRIPTS
    assert 'test:skill' in executor.SCRIPTS


# =============================================================================
# TESTS: extract_audit_plan_id
# =============================================================================


def test_extract_audit_plan_id_space_separated():
    """Extract --audit-plan-id with space-separated value."""
    executor = load_executor_module()
    plan_id, cleaned = executor.extract_audit_plan_id(['--audit-plan-id', 'my-plan', '--include-descriptions'])
    assert plan_id == 'my-plan', f"Expected 'my-plan', got {plan_id}"
    assert cleaned == ['--include-descriptions'], f"Expected ['--include-descriptions'], got {cleaned}"


def test_extract_audit_plan_id_equals_format():
    """Extract --audit-plan-id=value format."""
    executor = load_executor_module()
    plan_id, cleaned = executor.extract_audit_plan_id(['--audit-plan-id=my-plan', '--bundles', 'planning'])
    assert plan_id == 'my-plan', f"Expected 'my-plan', got {plan_id}"
    assert cleaned == ['--bundles', 'planning'], f"Expected ['--bundles', 'planning'], got {cleaned}"


def test_extract_audit_plan_id_not_present():
    """No audit-plan-id returns None and unchanged args."""
    executor = load_executor_module()
    plan_id, cleaned = executor.extract_audit_plan_id(['--plan-id', 'my-plan', '--flag'])
    assert plan_id is None, f'Expected None, got {plan_id}'
    assert cleaned == ['--plan-id', 'my-plan', '--flag'], 'Args should be unchanged'


def test_extract_audit_plan_id_preserves_other_args():
    """audit-plan-id extraction preserves all other arguments."""
    executor = load_executor_module()
    plan_id, cleaned = executor.extract_audit_plan_id(
        ['verb', '--audit-plan-id', 'test-plan', '--flag', 'value', '--other']
    )
    assert plan_id == 'test-plan', f"Expected 'test-plan', got {plan_id}"
    assert cleaned == ['verb', '--flag', 'value', '--other'], 'Other args should be preserved'


def test_extract_audit_plan_id_at_end():
    """audit-plan-id at end of args."""
    executor = load_executor_module()
    plan_id, cleaned = executor.extract_audit_plan_id(['--bundles', 'pm-dev-java', '--audit-plan-id', 'end-plan'])
    assert plan_id == 'end-plan', f"Expected 'end-plan', got {plan_id}"
    assert cleaned == ['--bundles', 'pm-dev-java'], f"Expected ['--bundles', 'pm-dev-java'], got {cleaned}"


# =============================================================================
# TESTS: Script execution via subprocess
# =============================================================================


def test_successful_script_execution():
    """Successful script execution returns correct exit code."""
    with tempfile.TemporaryDirectory() as tmp:
        test_script = Path(tmp) / 'test-script.py'
        test_script.write_text("""#!/usr/bin/env python3
import sys
print("Hello from test script")
print(f"Args: {sys.argv[1:]}")
sys.exit(0)
""")

        # Execute directly via subprocess
        result = subprocess.run(['python3', str(test_script), 'arg1', 'arg2'], capture_output=True, text=True)

        assert result.returncode == 0, f'Expected exit code 0, got {result.returncode}'
        assert 'Hello from test script' in result.stdout


def test_failed_script_returns_exit_code():
    """Failed script execution returns script's exit code."""
    with tempfile.TemporaryDirectory() as tmp:
        test_script = Path(tmp) / 'test-script.py'
        test_script.write_text("""#!/usr/bin/env python3
import sys
print("Error occurred", file=sys.stderr)
sys.exit(42)
""")

        result = subprocess.run(['python3', str(test_script)], capture_output=True, text=True)

        assert result.returncode == 42, f'Expected exit code 42, got {result.returncode}'
        assert 'Error occurred' in result.stderr


def test_argument_forwarding():
    """Arguments are correctly forwarded to script."""
    with tempfile.TemporaryDirectory() as tmp:
        test_script = Path(tmp) / 'test-script.py'
        test_script.write_text("""#!/usr/bin/env python3
import sys
import json
print(json.dumps(sys.argv[1:]))
""")

        args = ['verb', '--plan-id', 'my-plan', '--flag', 'value']
        result = subprocess.run(['python3', str(test_script)] + args, capture_output=True, text=True)

        import json

        received_args = json.loads(result.stdout.strip())
        assert received_args == args, f'Expected {args}, got {received_args}'


# =============================================================================
# TESTS: should_skip_logging (meta-logging noise prevention)
# =============================================================================


def test_skip_logging_for_manage_log_success():
    """Skip logging for successful manage-log calls (avoids meta-logging noise)."""
    executor = load_executor_module()
    result = executor.should_skip_logging('plan-marshall:manage-logging:manage-logging', exit_code=0)
    assert result is True, 'Should skip logging for successful manage-log calls'


def test_log_manage_log_on_error():
    """Log manage-log calls when they fail (errors should be logged)."""
    executor = load_executor_module()
    result = executor.should_skip_logging('plan-marshall:manage-logging:manage-logging', exit_code=1)
    assert result is False, 'Should log manage-log calls when they fail'


def test_log_normal_scripts_success():
    """Log normal scripts even on success."""
    executor = load_executor_module()
    result = executor.should_skip_logging('plan-marshall:manage-files', exit_code=0)
    assert result is False, 'Should log normal script calls'


def test_log_normal_scripts_failure():
    """Log normal scripts on failure."""
    executor = load_executor_module()
    result = executor.should_skip_logging('plan-marshall:manage-files', exit_code=1)
    assert result is False, 'Should log normal script calls on failure'


# =============================================================================
# TESTS: generate_executor.py script
# =============================================================================


def test_generate_script_help():
    """Generate script shows help."""
    script_path = SCRIPTS_DIR / 'generate_executor.py'

    if script_path.exists():
        result = subprocess.run(
            ['python3', str(script_path), '--help'], capture_output=True, text=True, env=_subprocess_env()
        )

        assert result.returncode == 0, f'Script failed: {result.stderr}'
        assert 'generate' in result.stdout, "Missing 'generate' subcommand in help"


def test_verify_script_help():
    """Verify script shows help."""
    script_path = SCRIPTS_DIR / 'verify-executor.py'

    if script_path.exists():
        result = subprocess.run(
            ['python3', str(script_path), '--help'], capture_output=True, text=True, env=_subprocess_env()
        )

        assert result.returncode == 0, f'Script failed: {result.stderr}'
        assert 'check' in result.stdout, "Missing 'check' subcommand in help"


# =============================================================================
# TESTS: _derive_failure_detail (option-A precedence)
# =============================================================================
#
# The dispatch-boundary [ERROR] line surfaces a single-line ``detail=`` field
# describing why a dispatched script exited non-zero. plan-marshall scripts
# report structured errors on STDOUT as a ``status: error`` TOON payload while
# exiting non-zero with EMPTY stderr — so a stderr-only diagnostic would render
# the work.log entry blank and undiagnosable. ``_derive_failure_detail``
# implements option-A precedence:
#
#   1. stdout parses as a ``status: error`` TOON with a ``message`` → that message
#   2. else stdout non-empty → raw stdout
#   3. else stderr non-empty → raw stderr (last resort, real stderr-only crashes)
#
# The chosen text is truncated to ``_DISPATCH_FAILURE_DETAIL_LIMIT`` and has its
# newlines collapsed so the entry stays single-line. These tests pin each
# precedence rung; the boundary-level behaviour (recursion guard, plan-id
# fallback) lives in test_dispatch_boundary_error.py and is not duplicated here.


def test_derive_detail_precedence1_status_error_toon_message():
    """Precedence (1): a status: error TOON on stdout yields its message field.

    This is the core regression: a script that reports ``status: error`` +
    ``message: ...`` on stdout (exiting non-zero with empty stderr) must have
    that message surfaced as the detail, NOT a blank string.
    """
    executor = load_executor_module()

    stdout = 'status: error\nmessage: plan not found: ghost-plan\nerror_type: plan_not_found'
    detail = executor._derive_failure_detail(stdout, '')

    assert detail == 'plan not found: ghost-plan', (
        f'Expected the TOON message field as detail, got {detail!r}'
    )


def test_derive_detail_precedence1_prefers_stdout_message_over_stderr():
    """Precedence (1) beats stderr: even when stderr is non-empty, a parseable
    status: error TOON message on stdout wins (option-A — always prefer the
    reason the script itself reported)."""
    executor = load_executor_module()

    stdout = 'status: error\nmessage: structured reason from stdout'
    stderr = 'incidental noise on stderr'
    detail = executor._derive_failure_detail(stdout, stderr)

    assert detail == 'structured reason from stdout', (
        f'Expected stdout TOON message to take precedence over stderr, got {detail!r}'
    )


def test_derive_detail_precedence2_raw_stdout_when_not_structured():
    """Precedence (2): non-empty stdout that does NOT parse as a status: error
    TOON falls through to the raw stdout text (newlines collapsed)."""
    executor = load_executor_module()

    # A plain non-TOON traceback / free-text blob on stdout.
    stdout = 'Traceback (most recent call last):\n  File "x.py", line 1\nValueError: boom'
    detail = executor._derive_failure_detail(stdout, '')

    assert 'ValueError: boom' in detail, f'Raw stdout text missing from detail: {detail!r}'
    assert 'Traceback (most recent call last):' in detail, f'Raw stdout head missing: {detail!r}'
    assert '\n' not in detail, f'detail must be single-line (newlines collapsed): {detail!r}'


def test_derive_detail_precedence2_status_ok_toon_is_raw_stdout():
    """A TOON payload whose status is NOT 'error' does not match precedence (1) —
    it falls through to precedence (2) and is surfaced as raw stdout. This pins
    the guard on ``status == 'error'`` specifically, not on "stdout parses as
    TOON"."""
    executor = load_executor_module()

    stdout = 'status: success\nmessage: this should not be treated as an error reason'
    detail = executor._derive_failure_detail(stdout, '')

    # The whole raw stdout is surfaced (precedence 2), not just the message field.
    assert 'status: success' in detail, f'Expected raw stdout for non-error TOON, got {detail!r}'


def test_derive_detail_precedence3_stderr_only_when_stdout_empty():
    """Precedence (3): stderr is the last-resort source, used ONLY when stdout is
    empty. Covers the genuine stderr-only crash case."""
    executor = load_executor_module()

    detail = executor._derive_failure_detail('', 'segfault: core dumped')

    assert detail == 'segfault: core dumped', (
        f'Expected stderr to be used when stdout is empty, got {detail!r}'
    )


def test_derive_detail_empty_when_both_streams_empty():
    """When both stdout and stderr are empty the detail is the empty string —
    the only case where a blank diagnostic is legitimate."""
    executor = load_executor_module()

    assert executor._derive_failure_detail('', '') == '', 'Both-empty case must yield empty detail'
    # Whitespace-only streams collapse to empty too.
    assert executor._derive_failure_detail('   \n  ', '\t') == '', 'Whitespace-only streams must yield empty detail'


def test_derive_detail_truncates_oversized_chosen_stream():
    """Precedence (4): the chosen stream, when longer than the configured limit,
    is truncated with the ``...[truncated]`` sentinel. Exercised here via the
    stdout path (precedence 2) to complement the stderr-path truncation test in
    test_dispatch_boundary_error.py."""
    executor = load_executor_module()

    limit = executor._DISPATCH_FAILURE_DETAIL_LIMIT
    oversized = 'B' * (limit + 200)

    detail = executor._derive_failure_detail(oversized, '')

    assert detail.endswith('...[truncated]'), f'Truncation sentinel missing: {detail[-40:]!r}'
    # Exactly ``limit`` retained characters precede the sentinel.
    assert detail == ('B' * limit) + '...[truncated]', (
        f'Expected exactly {limit} retained chars before the sentinel'
    )


def test_derive_detail_truncated_toon_message_is_capped():
    """A status: error TOON whose message exceeds the limit is truncated too —
    the cap applies to the chosen detail text regardless of which precedence rung
    produced it."""
    executor = load_executor_module()

    limit = executor._DISPATCH_FAILURE_DETAIL_LIMIT
    long_message = 'C' * (limit + 50)
    stdout = f'status: error\nmessage: {long_message}'

    detail = executor._derive_failure_detail(stdout, '')

    assert detail.endswith('...[truncated]'), f'Truncation sentinel missing from long TOON message: {detail[-40:]!r}'
    assert detail == ('C' * limit) + '...[truncated]', (
        f'Expected the TOON message truncated to exactly {limit} chars'
    )


# =============================================================================
# TESTS: emit_dispatch_failure_work_log surfaces stdout-derived detail=
# =============================================================================
#
# These assert the BOUNDARY emits a ``detail=`` field carrying the
# stdout-derived reason — the regression being that a non-zero exit reporting
# its error on stdout (empty stderr) must NOT produce a bare ``stderr=`` field
# or a blank diagnostic. The recursion guard / plan-id fallback rungs live in
# test_dispatch_boundary_error.py and are not duplicated here.

_EMIT_TEST_NOTATION = 'plan-marshall:manage-files:manage-files'
_EMIT_TEST_PLAN_ID = 'unit-emit-plan'


def test_emit_surfaces_stdout_toon_message_as_detail():
    """A status: error TOON on stdout (empty stderr) is surfaced via the
    ``detail=`` field — the headline regression for the script_failure record."""
    executor = load_executor_module()
    mock_log_entry = MagicMock()
    executor.log_entry = mock_log_entry

    stdout = 'status: error\nmessage: plan not found: ghost-plan'

    executor.emit_dispatch_failure_work_log(
        notation=_EMIT_TEST_NOTATION,
        exit_code=1,
        stdout=stdout,
        stderr='',
        script_args=['read', '--plan-id', _EMIT_TEST_PLAN_ID],
        audit_plan_id=None,
    )

    assert mock_log_entry.call_count == 1, f'Expected one log_entry call, got {mock_log_entry.call_count}'
    message = mock_log_entry.call_args.args[3]

    # The detail= field carries the stdout-reported reason.
    assert 'detail=plan not found: ghost-plan' in message, (
        f'Expected stdout TOON message in detail= field, got {message!r}'
    )
    # And it is a detail= field — not the legacy bare stderr= token.
    assert 'detail=' in message, f'Emitted line must carry a detail= field: {message!r}'
    assert 'stderr=' not in message, (
        f'Emitted line must NOT carry a bare stderr= field (regression token): {message!r}'
    )
    assert 'script_failure' in message, f'Expected script_failure marker in: {message!r}'


def test_emit_detail_is_not_blank_for_stdout_only_failure():
    """The exact original symptom: a non-zero exit with a status: error stdout
    payload and EMPTY stderr must never render a blank diagnostic. Asserts the
    detail= field is followed by non-whitespace content."""
    executor = load_executor_module()
    mock_log_entry = MagicMock()
    executor.log_entry = mock_log_entry

    executor.emit_dispatch_failure_work_log(
        notation=_EMIT_TEST_NOTATION,
        exit_code=1,
        stdout='status: error\nmessage: something broke',
        stderr='',
        script_args=['--plan-id', _EMIT_TEST_PLAN_ID],
        audit_plan_id=None,
    )

    message = mock_log_entry.call_args.args[3]
    # Split on the detail= token and assert the tail is non-empty.
    _, _, after_detail = message.partition('detail=')
    assert after_detail.strip(), f'detail= field must not be blank for a stdout-only failure: {message!r}'
    assert 'something broke' in after_detail, f'Expected the stdout message after detail=: {message!r}'


# =============================================================================
# TESTS: end-to-end dispatch-failure work.log regression
# =============================================================================
#
# Reproduces the original symptom through the FULL executor main() path: a stub
# script that prints a ``status: error`` TOON to stdout and exits non-zero with
# EMPTY stderr is dispatched via a materialized execute-script.py. The plan is
# routed to an isolated PLAN_BASE_DIR via PlanContext, and the plan's work.log
# is read back to assert the script_failure line carries the stub message and is
# NOT a blank diagnostic. This test FAILS against the pre-fix template (which
# emitted only stderr) and PASSES after the stdout-forwarding fix.


def _materialize_executor(target_path: Path, stub_notation: str, stub_script_path: Path) -> None:
    """Render the execute-script template to ``target_path`` with a single
    stub-script notation registered, so the full main() dispatch path can run as
    a subprocess.

    The ``{{LOGGING_DIR}}`` placeholder is wired to the REAL manage-logging
    scripts dir (the in-process unit harness can rely on conftest's PYTHONPATH,
    but a subprocess needs a resolvable path). ``toon_parser`` and
    ``plan_logging`` are additionally importable via the PYTHONPATH supplied to
    the subprocess (``_subprocess_env``).
    """
    template_path = TEMPLATE_DIR / 'execute-script.py.template'
    with open(template_path) as f:
        code = f.read()

    code = code.replace(
        '{{SCRIPT_MAPPINGS}}',
        f'    "{stub_notation}": "{stub_script_path}",\n',
    )
    code = code.replace('{{SUBCOMMAND_MAPPINGS}}', '')
    code = code.replace('{{LOGGING_DIR}}', str(LOGGING_DIR))
    code = code.replace('{{SHARED_MODULE_DIRS}}', '# (none in test)')
    code = code.replace('{{EXTRA_SCRIPT_DIRS}}', '')
    code = code.replace('{{PLAN_DIR_NAME}}', '.plan')
    code = code.replace('{{EXECUTOR_TARGET}}', 'claude')
    code = code.replace(
        '{{TARGET_AWARE_RESOLVER}}',
        'def _resolve_notation_by_target(notation):\n    return None\n',
    )
    target_path.write_text(code)


def test_end_to_end_script_failure_surfaces_stdout_in_work_log():
    """Full-path regression: a non-zero dispatch whose error is reported on
    stdout (status: error TOON, empty stderr) lands a diagnosable script_failure
    line in the plan's work.log carrying the stub's message — not a blank."""
    plan_id = 'e2e-stdout-failure-surface'
    stub_message = 'plan not found: phantom-target'

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Stub script: prints a status: error TOON to stdout, NOTHING to stderr,
        # and exits non-zero — the exact original failure shape.
        stub_script = tmp_path / 'stub_failing_script.py'
        stub_script.write_text(
            '#!/usr/bin/env python3\n'
            'import sys\n'
            f'print("status: error")\n'
            f'print("message: {stub_message}")\n'
            f'print("error_type: plan_not_found")\n'
            'sys.exit(1)\n'
        )

        stub_notation = 'test:stub:stub-failing-script'
        executor_path = tmp_path / 'execute-script.py'
        _materialize_executor(executor_path, stub_notation, stub_script)

        with PlanContext(plan_id=plan_id) as ctx:
            # log_entry('work', ...) routes to the plan-scoped logs/work.log ONLY
            # when the plan dir carries a status.json sentinel; create it so the
            # boundary's work.log write is plan-scoped (not the global fallback).
            (ctx.plan_dir / 'status.json').write_text('{}')

            result = subprocess.run(
                ['python3', str(executor_path), stub_notation, '--plan-id', plan_id],
                capture_output=True,
                text=True,
                env=_subprocess_env(),
            )

            # The dispatched stub's non-zero exit is the user-visible contract.
            assert result.returncode == 1, (
                f'Expected the executor to propagate the stub exit code 1, '
                f'got {result.returncode} (stderr: {result.stderr!r})'
            )

            work_log = ctx.plan_dir / 'logs' / 'work.log'
            assert work_log.exists(), f'Plan work.log was not written at {work_log}'
            log_text = work_log.read_text()

    # The script_failure line must be present, name the stub notation, and carry
    # the stub's stdout message in the detail= field.
    assert 'script_failure' in log_text, f'No script_failure entry in work.log:\n{log_text}'
    assert f'notation={stub_notation}' in log_text, f'Failing notation missing from work.log:\n{log_text}'
    assert stub_message in log_text, (
        f'The stub stdout message was not surfaced in work.log — this is the '
        f'blank-diagnostic regression:\n{log_text}'
    )
    assert 'detail=' in log_text, f'Expected a detail= field in the script_failure line:\n{log_text}'

    # Regression assertion: the detail= field is NOT blank. Find the line and
    # assert the text after detail= is non-empty.
    failure_lines = [ln for ln in log_text.splitlines() if 'script_failure' in ln and 'detail=' in ln]
    assert failure_lines, f'No script_failure line carrying a detail= field:\n{log_text}'
    _, _, after_detail = failure_lines[0].partition('detail=')
    assert after_detail.strip(), (
        f'detail= field rendered blank — the original undiagnosable symptom:\n{failure_lines[0]!r}'
    )
