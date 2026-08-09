#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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

# resolve_notation existence-checks embedded SCRIPTS paths (self-healing contract),
# so the mapped targets must be real files on disk for the direct-hit branch to return
# them. Create stub files in a temp dir and map the test notations to them.
_MAPPED_DIR = Path(tempfile.mkdtemp(prefix='executor-mappings-'))
_MAP_MANAGE_FILES = _MAPPED_DIR / 'manage-files.py'
_MAP_MAVEN = _MAPPED_DIR / 'maven.py'
_MAP_TEST_SKILL = _MAPPED_DIR / 'test-skill.py'
for _stub in (_MAP_MANAGE_FILES, _MAP_MAVEN, _MAP_TEST_SKILL):
    _stub.write_text('# test stub\n')


def load_executor_module():
    """Load the execute-script module from template for testing."""
    template_path = TEMPLATE_DIR / 'execute-script.py.template'
    with open(template_path) as f:
        code = f.read()

    # Replace the placeholders with test values
    code = code.replace(
        '{{SCRIPT_MAPPINGS}}',
        f"""
    "plan-marshall:manage-files": "{_MAP_MANAGE_FILES}",
    "pm-dev-builder:builder-maven-rules": "{_MAP_MAVEN}",
    "test:skill": "{_MAP_TEST_SKILL}",
""",
    )
    code = code.replace('{{SCRIPT_SURFACES}}', '')
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


def test_resolve_exact_match():
    """Resolve exact notation match."""
    executor = load_executor_module()
    result = executor.resolve_notation('plan-marshall:manage-files')
    assert result == str(_MAP_MANAGE_FILES), f"Expected '{_MAP_MANAGE_FILES}', got {result}"


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


# The dispatch-boundary [ERROR] line surfaces a single-line ``detail=`` field
# describing why a dispatched script exited non-zero. plan-marshall scripts
# report structured errors on STDOUT as a ``status: error`` TOON payload while
# exiting non-zero with EMPTY stderr — so a stderr-only diagnostic would render
# the work.log entry blank and undiagnosable. ``_derive_failure_detail``
# implements option-A precedence:
#   1. stdout parses as a ``status: error`` TOON with a ``message`` → that message
#   2. else stdout non-empty → raw stdout
#   3. else stderr non-empty → raw stderr (last resort, real stderr-only crashes)
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
    code = code.replace('{{SCRIPT_SURFACES}}', '')
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


# =============================================================================
# Build-class dispatch boundary — the never-null plan_id / global-log contract
# =============================================================================
#
# Two claims that pull in OPPOSITE directions and are asserted together, because
# satisfying either one alone is the failure mode:
#
#   (a) the kind=build ledger row's plan_id is NEVER null — a plan-less build is
#       recorded under the NO_PLAN sentinel, so every build is attributable;
#   (b) the SCRIPT LOG for that same dispatch still resolves to the GLOBAL path,
#       not a NO_PLAN-scoped one — the sentinel is a routing/ledger VALUE, never
#       a plan-directory selector.
#
# Collapsing `_active_plan_id` and `_ledger_plan_id` into one variable satisfies
# (a) and silently breaks (b), which is why the fixture below MATERIALIZES
# plans/NO_PLAN/status.json: without that sentinel dir, get_log_path('NO_PLAN')
# already falls back to the global path and assertion (b) would pass for the
# wrong reason.

_BUILD_CLASS_NOTATION = 'plan-marshall:build-pyproject:pyproject_build'


def _run_build_class_dispatch(
    tmp_path: Path,
    plan_id_argv: list[str],
    stub_stdout: str = 'status: success',
    stub_exit_code: int = 0,
) -> list[dict]:
    """Dispatch a build-class stub through a materialized executor; return the ledger.

    ``stub_stdout`` is what the stubbed build WRAPPER prints — the single
    payload the dispatch boundary parses for ``status`` / ``command`` /
    ``duration_seconds`` / ``outcome``. ``stub_exit_code`` is the process exit
    the executor must propagate unchanged.

    Every caller's ``plan_id_argv`` MUST lead with the build-executing subcommand
    (``run``): the dispatch boundary is a CONJUNCTION of the build-class notation
    prefix and that subcommand, so a dispatch without it stamps no ledger row at
    all and the row assertions below would fail for an unrelated reason. The
    narrowing itself is covered in test_build_class_stamp_discriminator.py.
    """
    import json

    stub_script = tmp_path / 'stub_build.py'
    stub_script.write_text(
        '#!/usr/bin/env python3\n'
        'import sys\n'
        f'sys.stdout.write({stub_stdout!r})\n'
        f'sys.exit({stub_exit_code})\n'
    )

    executor_path = tmp_path / 'execute-script.py'
    _materialize_executor(executor_path, _BUILD_CLASS_NOTATION, stub_script)

    fixture = tmp_path / 'plan-base'
    # The sentinel plan dir + its status.json sentinel: with these present,
    # get_log_path('NO_PLAN', 'script') WOULD resolve to a NO_PLAN-scoped path,
    # so the global-log assertion below can actually fail.
    sentinel_logs = fixture / 'plans' / 'NO_PLAN'
    sentinel_logs.mkdir(parents=True)
    (sentinel_logs / 'status.json').write_text('{}')

    env = _subprocess_env()
    env['PLAN_BASE_DIR'] = str(fixture)
    result = subprocess.run(
        ['python3', str(executor_path), _BUILD_CLASS_NOTATION, *plan_id_argv],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(Path(__file__).parent.parent.parent.parent),
    )
    assert result.returncode == stub_exit_code, (
        f'the executor must propagate the stub exit code {stub_exit_code} unchanged, '
        f'got {result.returncode} (stderr: {result.stderr!r})'
    )

    ledger = fixture / 'work' / 'change-ledger.jsonl'
    assert ledger.is_file(), (
        f'no kind=build ledger row was written at {ledger} '
        f'(stderr: {result.stderr!r})'
    )
    return [json.loads(line) for line in ledger.read_text().splitlines() if line.strip()]


def test_build_class_dispatch_without_plan_id_records_the_sentinel():
    """(a) A build-class dispatch with NO ``--plan-id`` records ``NO_PLAN``.

    Fail-first: before the resolution the row landed as ``plan_id: null`` and
    the build was unattributable.
    """
    with tempfile.TemporaryDirectory() as tmp:
        entries = _run_build_class_dispatch(Path(tmp), ['run'])

    assert len(entries) == 1, f'expected exactly one kind=build row, got {entries!r}'
    assert entries[0]['kind'] == 'build'
    assert entries[0]['plan_id'] == 'NO_PLAN', (
        f'plan-less build recorded plan_id={entries[0]["plan_id"]!r}; the row '
        'must carry the NO_PLAN sentinel, never null.'
    )


def test_build_class_dispatch_without_plan_id_keeps_the_global_script_log():
    """(b) The SAME dispatch keeps its script log on the GLOBAL path.

    The sentinel is a routing/ledger value, not a plan-directory selector.
    Passing it to ``get_log_path`` would silently redirect a plan-less build's
    script log into ``plans/NO_PLAN/logs/`` — which this fixture materializes
    precisely so the redirect is observable rather than masked by the
    missing-directory fallback.
    """
    with tempfile.TemporaryDirectory() as tmp:
        entries = _run_build_class_dispatch(Path(tmp), ['run'])

    log_file = entries[0]['log_file']
    assert 'NO_PLAN' not in log_file, (
        f'the plan-less script log resolved to {log_file!r} — the sentinel was '
        'handed to get_log_path and redirected the log into a plan dir.'
    )
    assert 'script-execution-' in log_file, (
        f'expected the date-suffixed GLOBAL script log, got {log_file!r}'
    )


def test_build_class_dispatch_with_a_real_plan_id_stores_it_verbatim():
    """The fallback never overwrites a supplied plan id — the carve-out is narrow.

    Without this counter-case, a boundary that hard-coded ``NO_PLAN`` would
    satisfy both assertions above while making every ledger row unattributable
    in the opposite direction.
    """
    with tempfile.TemporaryDirectory() as tmp:
        entries = _run_build_class_dispatch(Path(tmp), ['run', '--plan-id', 'a-real-plan'])

    assert entries[0]['plan_id'] == 'a-real-plan'


# =============================================================================
# Build-class dispatch boundary — the wrapper-reported command / duration / outcome
# =============================================================================
#
# The row records the invocation at TWO layers and both are asserted in the same
# test: ``args`` is the EXECUTOR argv the caller supplied, ``command`` is what
# the build WRAPPER resolved that argv into and actually ran. A boundary that
# stamped the executor argv into ``command`` would satisfy a
# "``command`` is populated" assertion on its own, so the check that bites is the
# one pinning ``command`` to the wrapper's value AND ``args`` to the argv.


def test_build_class_dispatch_records_the_wrapper_command_not_the_executor_argv():
    """``command`` / ``duration_seconds`` / ``outcome`` come from the WRAPPER payload."""
    wrapper_stdout = (
        'status: success\n'
        'command: "./pw verify plan-marshall"\n'
        'duration_seconds: 42\n'
        'log_file: /tmp/python-build.log\n'
    )

    with tempfile.TemporaryDirectory() as tmp:
        entries = _run_build_class_dispatch(
            Path(tmp),
            ['run', '--command-args', 'verify plan-marshall', '--plan-id', 'a-real-plan'],
            stub_stdout=wrapper_stdout,
        )

    entry = entries[0]
    # The wrapper's resolved command line — NOT the executor argv.
    assert entry['command'] == './pw verify plan-marshall', (
        f'command={entry["command"]!r}; the boundary must record what the wrapper '
        'resolved and ran, not what the caller typed.'
    )
    # The executor argv layer is intact and DIFFERENT from the resolved command.
    assert entry['args'] == 'run --command-args verify plan-marshall --plan-id a-real-plan'
    assert entry['args'] != entry['command'], (
        'args and command collapsed onto one value — the two layers must stay '
        'independently recoverable from a single row.'
    )
    # The wrapper's measured duration, coerced to a float.
    assert entry['duration_seconds'] == 42.0
    # The whole payload is retained verbatim as the outcome dict.
    assert entry['outcome']['status'] == 'success'
    assert entry['outcome']['command'] == './pw verify plan-marshall'
    assert entry['outcome']['log_file'] == '/tmp/python-build.log'


# =============================================================================
# Pre-spawn invocation validation — the rejection happens BEFORE any child runs
# =============================================================================
#
# Every rejection test below asserts BOTH halves: the stdout TOON correction AND
# that no subprocess was started. Asserting only the payload would pass just as
# happily on an implementation that spawns the script, lets argparse reject it,
# and then prints a correction — which is a different feature (a nicer error)
# than the one being built (no spawn at all). The stub script therefore writes a
# sentinel file when it runs; the file's ABSENCE is the no-spawn proof.

_SPAWN_NOTATION = 'test:surface:validated'


def _spawn_marker_script(tmp_path: Path) -> tuple[Path, Path]:
    """A stub that records that it ran. Returns ``(script_path, marker_path)``."""
    marker = tmp_path / 'SPAWNED'
    script = tmp_path / 'validated_stub.py'
    script.write_text(
        '#!/usr/bin/env python3\n'
        'from pathlib import Path\n'
        f'Path({str(marker)!r}).write_text("ran")\n'
        'print("status: success")\n',
        encoding='utf-8',
    )
    return script, marker


def _surface_entry(
    children: dict, *, root_flags=(), root_arity=None, confident=True
) -> dict:
    """Build one SCRIPT_SURFACES entry in the shape the generator emits.

    ``root_arity`` is the root node's derived ``{flag: value_token_count}`` map.
    It is deliberately independent of ``root_flags``: the real derivation
    over-collects flags from help prose but derives arity only from option
    invocation lines, so a flag present in one and absent from the other is the
    NORMAL case, not a malformed fixture.
    """
    return {
        'digest': 'test-digest',
        'surface': {
            'root': {
                'flags': list(root_flags),
                'required_flags': [],
                'flag_arity': dict(root_arity or {}),
                'alias_of': {},
                'flags_confident': confident,
                'children_confident': confident,
                'children': children,
            }
        },
    }


def _node(
    flags=(), required=(), arity=None, children=None, alias_of=None, confident=True
) -> dict:
    return {
        'flags': list(flags),
        'required_flags': list(required),
        'flag_arity': dict(arity or {}),
        'alias_of': dict(alias_of or {}),
        'flags_confident': confident,
        'children_confident': confident,
        'children': dict(children or {}),
    }


def _render_validating_executor(target_path: Path, script_path: Path, surfaces: dict) -> None:
    """Render the template with a SCRIPTS mapping AND a SCRIPT_SURFACES map."""
    template_path = TEMPLATE_DIR / 'execute-script.py.template'
    code = template_path.read_text(encoding='utf-8')
    code = code.replace(
        '{{SCRIPT_MAPPINGS}}', f'    "{_SPAWN_NOTATION}": "{script_path}",\n'
    )
    surfaces_code = '\n'.join(
        f'    "{notation}": {entry!r},' for notation, entry in sorted(surfaces.items())
    )
    code = code.replace('{{SCRIPT_SURFACES}}', surfaces_code)
    code = code.replace('{{SUBCOMMAND_MAPPINGS}}', '')
    code = code.replace('{{LOGGING_DIR}}', str(LOGGING_DIR))
    code = code.replace('{{SHARED_MODULE_DIRS}}', '# (none in test)')
    code = code.replace('{{EXTRA_SCRIPT_DIRS}}', '')
    code = code.replace('{{PLAN_DIR_NAME}}', '.plan')
    code = code.replace('{{EXECUTOR_TARGET}}', 'claude')
    code = code.replace('{{GENERATED_VERSION}}', '0.0.0-test')
    code = code.replace('{{MAPPINGS_FINGERPRINT}}', 'test-fingerprint')
    code = code.replace(
        '{{TARGET_AWARE_RESOLVER}}',
        'def _resolve_notation_by_target(notation):\n    return None\n',
    )
    target_path.write_text(code, encoding='utf-8')


def _dispatch(tmp: Path, surfaces: dict, argv: list) -> tuple[subprocess.CompletedProcess, Path]:
    """Render a validating executor, dispatch ``argv``, return (result, marker)."""
    script, marker = _spawn_marker_script(tmp)
    executor = tmp / 'execute-script.py'
    _render_validating_executor(executor, script, surfaces)
    result = subprocess.run(
        [sys.executable, str(executor), _SPAWN_NOTATION, *argv],
        capture_output=True,
        text=True,
        env=_subprocess_env(),
        timeout=60,
    )
    return result, marker


def test_invented_subcommand_is_rejected_before_any_spawn():
    surfaces = {_SPAWN_NOTATION: _surface_entry({'read': _node(), 'list': _node()})}
    with tempfile.TemporaryDirectory() as tmp:
        result, marker = _dispatch(Path(tmp), surfaces, ['nuke'])

        assert not marker.exists(), 'the script was spawned — the rejection must precede the spawn'

    assert result.returncode == 2, result.stderr
    assert 'status: error' in result.stdout
    assert 'error: invalid_invocation' in result.stdout
    assert 'reason: unknown_verb' in result.stdout
    assert 'rejected: nuke' in result.stdout


def test_invented_flag_is_rejected_before_any_spawn():
    surfaces = {
        _SPAWN_NOTATION: _surface_entry({'read': _node(flags=['plan-id'])})
    }
    with tempfile.TemporaryDirectory() as tmp:
        result, marker = _dispatch(Path(tmp), surfaces, ['read', '--made-up-flag', 'x'])

        assert not marker.exists(), 'the script was spawned despite an unaccepted flag'

    assert result.returncode == 2
    assert 'reason: unknown_flag' in result.stdout
    assert 'rejected: --made-up-flag' in result.stdout


def test_rejection_names_the_closest_accepted_spelling():
    """The correction must be actionable, not just a refusal."""
    surfaces = {_SPAWN_NOTATION: _surface_entry({'read': _node(), 'list': _node()})}
    with tempfile.TemporaryDirectory() as tmp:
        result, _marker = _dispatch(Path(tmp), surfaces, ['reed'])

    assert 'read' in result.stdout, f'no corrective naming the canonical form: {result.stdout!r}'


def test_alias_spelling_spawns_normally():
    """A documented alias is an accepted spelling, not a rejection."""
    surfaces = {
        _SPAWN_NOTATION: _surface_entry(
            {'read': _node(flags=['plan-id']), 'get': _node(flags=['plan-id'])}
        )
    }
    surfaces[_SPAWN_NOTATION]['surface']['root']['alias_of'] = {'get': 'read'}
    with tempfile.TemporaryDirectory() as tmp:
        result, marker = _dispatch(Path(tmp), surfaces, ['get', '--plan-id', 'p'])

        assert marker.exists(), f'alias invocation was refused: {result.stdout!r}'

    assert result.returncode == 0


def test_nested_verb_path_spawns_normally():
    surfaces = {
        _SPAWN_NOTATION: _surface_entry(
            {'plan': _node(children={'phase-5-execute': _node(children={'get': _node(flags=['field'])})})}
        )
    }
    with tempfile.TemporaryDirectory() as tmp:
        result, marker = _dispatch(
            Path(tmp), surfaces, ['plan', 'phase-5-execute', 'get', '--field', 'x']
        )

        assert marker.exists(), f'valid nested path was refused: {result.stdout!r}'

    assert result.returncode == 0


def test_notation_absent_from_surfaces_spawns_unchanged():
    """No entry means no knowledge — and no knowledge must never reject."""
    with tempfile.TemporaryDirectory() as tmp:
        result, marker = _dispatch(Path(tmp), {}, ['literally-anything', '--any-flag', 'v'])

        assert marker.exists(), f'a notation with no surface was refused: {result.stdout!r}'

    assert result.returncode == 0


def test_unconfident_node_stops_validation_instead_of_rejecting():
    """Fail-open as a POSITIVE control, not merely an assertion in prose.

    The node declares children, so an unknown token WOULD be rejected if the
    listing were trusted. Marking it unconfident must flip that to a spawn —
    which is the only way to distinguish "validation degraded" from "validation
    happened to find nothing to complain about".
    """
    surfaces = {
        _SPAWN_NOTATION: _surface_entry({'read': _node()}, confident=False)
    }
    with tempfile.TemporaryDirectory() as tmp:
        result, marker = _dispatch(Path(tmp), surfaces, ['some-unlisted-verb'])

        assert marker.exists(), (
            f'an unconfident child listing rejected a token it had no basis to '
            f'call wrong: {result.stdout!r}'
        )

    assert result.returncode == 0


def test_unknown_flag_set_skips_flag_validation():
    """A node whose flag surface is unknown must not reject any flag."""
    surfaces = {
        _SPAWN_NOTATION: _surface_entry({'read': _node(flags=[], confident=False)})
    }
    with tempfile.TemporaryDirectory() as tmp:
        result, marker = _dispatch(Path(tmp), surfaces, ['read', '--anything-at-all', 'v'])

        assert marker.exists(), f'a flag was rejected from an unknown flag set: {result.stdout!r}'

    assert result.returncode == 0


def test_missing_required_flag_is_rejected_before_any_spawn():
    surfaces = {
        _SPAWN_NOTATION: _surface_entry(
            {'read': _node(flags=['plan-id'], required=['plan-id'])}
        )
    }
    with tempfile.TemporaryDirectory() as tmp:
        result, marker = _dispatch(Path(tmp), surfaces, ['read'])

        assert not marker.exists(), 'spawned despite a missing required flag'

    assert result.returncode == 2
    assert 'reason: missing_required_flag' in result.stdout
    assert '--plan-id' in result.stdout


def test_root_declared_flag_is_accepted_on_a_subcommand():
    """argparse honours a root flag on every subcommand; so must the check.

    Without the ancestor union this is the classic false rejection: the flag is
    rendered only in the ROOT help, so a leaf-only flag set calls it unknown.
    """
    surfaces = {
        _SPAWN_NOTATION: _surface_entry({'read': _node()}, root_flags=['project-dir'])
    }
    with tempfile.TemporaryDirectory() as tmp:
        result, marker = _dispatch(Path(tmp), surfaces, ['read', '--project-dir', '/x'])

        assert marker.exists(), f'a root-declared flag was rejected: {result.stdout!r}'

    assert result.returncode == 0


def test_audit_plan_id_never_reaches_the_flag_check():
    """The executor's own flag is stripped before validation, so it cannot be rejected.

    ``--audit-plan-id`` is consumed by the executor and appears in NO script's
    help, so a check that saw it would reject every audited call in the tree.
    """
    surfaces = {
        _SPAWN_NOTATION: _surface_entry({'read': _node(flags=['plan-id'])})
    }
    with tempfile.TemporaryDirectory() as tmp:
        result, marker = _dispatch(
            Path(tmp), surfaces, ['read', '--plan-id', 'p', '--audit-plan-id', 'audited']
        )

        assert marker.exists(), f'--audit-plan-id reached the flag check: {result.stdout!r}'

    assert result.returncode == 0


def test_help_flag_always_dispatches_even_on_a_flagless_surface():
    """``--help`` must never be refused — the regression the live run caught.

    The derivation deliberately strips ``help`` from every flag set (it says
    nothing about the script's own surface), so a validator that checked the
    derived set alone rejected ``--help`` on every script. That broke the most
    common diagnostic call in the tree AND the derivation's own probe: the
    surface is derived by running ``--help`` THROUGH this executor, so the
    guard would have starved the mechanism that feeds it.

    The fixture makes the flag set empty AND confident, which is the exact
    shape that produced the false rejection.
    """
    surfaces = {_SPAWN_NOTATION: _surface_entry({}, root_flags=[])}
    with tempfile.TemporaryDirectory() as tmp:
        result, marker = _dispatch(Path(tmp), surfaces, ['--help'])

        assert marker.exists(), f'--help was refused: {result.stdout!r}'

    assert result.returncode == 0


def test_help_flag_dispatches_alongside_an_unregistered_verb():
    """``--help`` short-circuits the verb walk too.

    argparse prints usage instead of running the verb, so an incomplete or
    misspelled path alongside ``--help`` is a request for help, not an error to
    report. This is how the derivation probes a node it has not yet mapped.
    """
    surfaces = {_SPAWN_NOTATION: _surface_entry({'read': _node()})}
    with tempfile.TemporaryDirectory() as tmp:
        result, marker = _dispatch(Path(tmp), surfaces, ['not-a-verb', '--help'])

        assert marker.exists(), f'--help alongside an unknown verb was refused: {result.stdout!r}'

    assert result.returncode == 0


# -----------------------------------------------------------------------------
# The SHORT help spelling — argparse fires on -h too, so the guard must as well
# -----------------------------------------------------------------------------
#
# The reported defect: the help short-circuit matched only ``--help``, so ``-h``
# fell through into the walk and a leaf carrying required flags refused it.
# ``manage-tasks read -h`` returned reason=missing_required_flag / exit 2 with no
# usage text, while ``manage-tasks read --help`` printed usage — a valid call
# refused, from a spelling difference argparse does not make. Second instance of
# that class in this feature, after the top-level-flag walk desync.
#
# The surface below is the reproducer's own shape: a ``read`` leaf whose two
# required flags are exactly what produced the refusal.
_REQUIRED_FLAG_SURFACE = {
    _SPAWN_NOTATION: _surface_entry(
        {
            'read': _node(
                flags=['plan-id', 'task-number'],
                required=['plan-id', 'task-number'],
                arity={'plan-id': 1, 'task-number': 1},
            )
        }
    )
}


def test_short_help_flag_dispatches_on_a_leaf_with_required_flags():
    """Named positive control — the exact reported invocation shape.

    Live form (against the regenerated worktree executor):
      ``plan-marshall:manage-tasks:manage-tasks read -h`` — refused pre-fix with
      ``reason: missing_required_flag / rejected: --plan-id, --task-number``,
      exit 2, and no usage text on either stream. The required flags are not
      missing from this call: argparse fires its help action before the leaf
      ever parses, so there is nothing for them to be missing from.
    """
    with tempfile.TemporaryDirectory() as tmp:
        result, marker = _dispatch(Path(tmp), _REQUIRED_FLAG_SURFACE, ['read', '-h'])

        assert marker.exists(), (
            f'-h was refused where --help dispatches — argparse declares both '
            f'spellings on every parser: {result.stdout!r}'
        )

    assert result.returncode == 0
    assert 'invalid_invocation' not in result.stdout


def test_short_help_flag_dispatches_inside_a_cluster():
    """argparse splits ``-vh`` into its constituent options, so the guard must too."""
    with tempfile.TemporaryDirectory() as tmp:
        result, marker = _dispatch(Path(tmp), _REQUIRED_FLAG_SURFACE, ['read', '-vh'])

        assert marker.exists(), (
            f'a clustered short help flag was refused: {result.stdout!r}'
        )

    assert result.returncode == 0


def test_short_help_flag_dispatches_alongside_an_unregistered_verb():
    """``-h`` short-circuits the verb walk, exactly as ``--help`` does.

    This is how the derivation probes a node it has not mapped yet, and it is
    the same behaviour ``test_help_flag_dispatches_alongside_an_unregistered_verb``
    pins for the long form — the two spellings must not diverge.
    """
    surfaces = {_SPAWN_NOTATION: _surface_entry({'read': _node()})}
    with tempfile.TemporaryDirectory() as tmp:
        result, marker = _dispatch(Path(tmp), surfaces, ['not-a-verb', '-h'])

        assert marker.exists(), (
            f'-h alongside an unknown verb was refused: {result.stdout!r}'
        )

    assert result.returncode == 0


def test_short_flag_without_help_still_permits_rejection():
    """Negative control: recognising ``-h`` must not mute short flags generally.

    Without this, the three tests above would pass just as happily on an
    implementation that short-circuited on ANY ``-``-prefixed short token — a
    change that would silently retire validation for every call carrying one.
    """
    with tempfile.TemporaryDirectory() as tmp:
        result, marker = _dispatch(Path(tmp), _REQUIRED_FLAG_SURFACE, ['read', '-v'])

        assert not marker.exists(), (
            'a short flag with no help spelling in it disabled validation'
        )

    assert result.returncode == 2
    assert 'reason: missing_required_flag' in result.stdout


def test_help_lookalike_long_flag_still_permits_rejection():
    """Negative control: ``--helpful`` is an ordinary flag, not a help spelling.

    The long form is matched EXACTLY (plus the ``--help=`` inline-value form),
    never by prefix, so a declared flag whose name merely begins with the word
    keeps its full validation.
    """
    with tempfile.TemporaryDirectory() as tmp:
        result, marker = _dispatch(
            Path(tmp), _REQUIRED_FLAG_SURFACE, ['read', '--helpful']
        )

        assert not marker.exists(), (
            'a flag that merely starts with "--help" disabled validation'
        )

    assert result.returncode == 2
    assert 'reason: unknown_flag' in result.stdout
    assert 'rejected: --helpful' in result.stdout


def test_unregistered_verb_is_still_rejected_without_a_help_token():
    """Negative control at the verb level, matched to the ``-h`` positives above.

    Same surface and same verb as the short-help cases, minus the help token:
    the refusal must still fire, so a green ``-h`` test cannot be read as the
    walk having been switched off for this fixture.
    """
    surfaces = {_SPAWN_NOTATION: _surface_entry({'read': _node()})}
    with tempfile.TemporaryDirectory() as tmp:
        result, marker = _dispatch(Path(tmp), surfaces, ['not-a-verb'])

        assert not marker.exists(), 'an unregistered verb slipped through'

    assert result.returncode == 2
    assert 'reason: unknown_verb' in result.stdout


def test_executor_injected_flags_are_never_rejected():
    """``--plan-id`` / ``--project-dir`` are accepted even on an empty flag set.

    Both are honoured through argparse's parent-flag propagation or injected by
    the executor, and either way can be absent from the node's rendered help.
    Rejecting them would refuse the worktree-binding convention the whole
    codebase dispatches with.
    """
    surfaces = {_SPAWN_NOTATION: _surface_entry({'read': _node(flags=[])})}
    with tempfile.TemporaryDirectory() as tmp:
        result, marker = _dispatch(
            Path(tmp), surfaces, ['read', '--plan-id', 'p', '--project-dir', '/x']
        )

        assert marker.exists(), f'an executor-injected flag was refused: {result.stdout!r}'

    assert result.returncode == 0


def test_unknown_flag_is_still_rejected_on_a_flagless_surface():
    """Negative control for the allowlist: it widens, it does not disable.

    Without this, every "the allowlist lets X through" test above would pass
    just as well on a validator that stopped checking flags altogether.
    """
    surfaces = {_SPAWN_NOTATION: _surface_entry({'read': _node(flags=[])})}
    with tempfile.TemporaryDirectory() as tmp:
        result, marker = _dispatch(Path(tmp), surfaces, ['read', '--definitely-not-declared'])

        assert not marker.exists(), 'an unknown flag slipped through the allowlist'

    assert result.returncode == 2
    assert 'reason: unknown_flag' in result.stdout


def test_flag_value_is_not_mistaken_for_a_verb():
    """A flag's VALUE must never be walked as part of the verb path.

    ``--plan-id nuke`` carries a value that happens to look like an unregistered
    verb. Treating it as a positional would reject a perfectly valid call.
    """
    surfaces = {
        _SPAWN_NOTATION: _surface_entry({'read': _node(flags=['plan-id'])})
    }
    with tempfile.TemporaryDirectory() as tmp:
        result, marker = _dispatch(Path(tmp), surfaces, ['read', '--plan-id', 'nuke'])

        assert marker.exists(), f'a flag value was walked as a verb: {result.stdout!r}'

    assert result.returncode == 0


# =============================================================================
# Top-level (router) flags BEFORE the verb — the walk must not desynchronise
# =============================================================================
#
# The defect these pin: the verb-path walk collected only the LEADING run of
# non-flag tokens, so ``--project-dir . find --pattern P`` parked the walk on
# the ROOT node — ``find`` was swallowed as if it were the flag's value — and
# every flag declared on ``find`` was then measured against the root's
# accept-set and refused. The call is correct as written: argparse requires a
# top-level optional to PRECEDE the subcommand and rejects it afterwards, so
# there is no alternative spelling the caller could have used.
#
# Every case below pairs a positive control (a valid call spawns) with the
# matching negative control (a genuinely invalid call is STILL refused with the
# same top-level flag present). Without the negatives, the whole group would
# pass on an implementation that simply stopped validating once it saw a flag.

# The router-flag surface: a value-taking ``--project-dir`` and a bare
# ``--verbose``, both declared on the ROOT, plus a ``find`` verb owning
# ``--pattern``. The two root flags differ in arity ON PURPOSE — an
# implementation that assumed "every leading flag takes a value" passes the
# first case and swallows the verb in the second.
_ROUTER_SURFACE = {
    _SPAWN_NOTATION: _surface_entry(
        {'find': _node(flags=['pattern'], arity={'pattern': 1})},
        root_flags=['project-dir', 'verbose', 'coords'],
        root_arity={'project-dir': 1, 'verbose': 0, 'coords': 2},
    )
}


def test_value_taking_top_level_flag_before_the_verb_spawns():
    """Named positive control — the exact reported invocation shape.

    Live form (against the real executor):
      ``plan-marshall:manage-architecture:architecture --project-dir . find
      --pattern "*.template"`` — refused pre-fix with
      ``reason: unknown_flag / rejected: --pattern / accepted: content, pre``.
      The ``accepted`` set was the tell: it is the ROOT's flag set, proving the
      walk never reached the ``find`` node.
    """
    with tempfile.TemporaryDirectory() as tmp:
        result, marker = _dispatch(
            Path(tmp), _ROUTER_SURFACE, ['--project-dir', '.', 'find', '--pattern', '*.md']
        )

        assert marker.exists(), (
            f'a valid call was refused because a top-level flag preceded the '
            f'verb: {result.stdout!r}'
        )

    assert result.returncode == 0


def test_bare_top_level_flag_before_the_verb_spawns():
    """A zero-arity root switch must NOT swallow the verb that follows it."""
    with tempfile.TemporaryDirectory() as tmp:
        result, marker = _dispatch(
            Path(tmp), _ROUTER_SURFACE, ['--verbose', 'find', '--pattern', '*.md']
        )

        assert marker.exists(), (
            f'a bare top-level switch consumed the verb behind it: {result.stdout!r}'
        )

    assert result.returncode == 0


def test_equals_joined_top_level_flag_before_the_verb_spawns():
    """``--flag=value`` binds no following token, whatever its arity says."""
    with tempfile.TemporaryDirectory() as tmp:
        result, marker = _dispatch(
            Path(tmp), _ROUTER_SURFACE, ['--project-dir=.', 'find', '--pattern', '*.md']
        )

        assert marker.exists(), (
            f'the =-joined form of a routing flag was mishandled: {result.stdout!r}'
        )

    assert result.returncode == 0


def test_multi_token_flag_value_before_the_verb_is_stepped_over():
    """An ``nargs=2`` root flag consumes exactly two tokens, then the verb runs."""
    with tempfile.TemporaryDirectory() as tmp:
        result, marker = _dispatch(
            Path(tmp),
            _ROUTER_SURFACE,
            ['--coords', '3', '4', 'find', '--pattern', '*.md'],
        )

        assert marker.exists(), (
            f'a two-token flag value desynchronised the walk: {result.stdout!r}'
        )

    assert result.returncode == 0


def test_unregistered_verb_is_still_rejected_behind_a_top_level_flag():
    """Negative control: the fix must not disable verb validation."""
    with tempfile.TemporaryDirectory() as tmp:
        result, marker = _dispatch(
            Path(tmp), _ROUTER_SURFACE, ['--project-dir', '.', 'nuke', '--pattern', '*.md']
        )

        assert not marker.exists(), (
            'an unregistered verb slipped through once a routing flag preceded it'
        )

    assert result.returncode == 2
    assert 'reason: unknown_verb' in result.stdout
    assert 'rejected: nuke' in result.stdout


def test_unregistered_flag_is_still_rejected_behind_a_top_level_flag():
    """Negative control: the fix must not disable flag validation either.

    The rejection must ALSO name the verb node's accept-set rather than the
    root's — that is the positive proof the walk reached ``find``, where the
    defect's ``accepted: content, pre`` was the proof it had not.
    """
    with tempfile.TemporaryDirectory() as tmp:
        result, marker = _dispatch(
            Path(tmp),
            _ROUTER_SURFACE,
            ['--project-dir', '.', 'find', '--made-up-flag', 'x'],
        )

        assert not marker.exists(), (
            'an unregistered flag slipped through once a routing flag preceded it'
        )

    assert result.returncode == 2
    assert 'reason: unknown_flag' in result.stdout
    assert 'rejected: --made-up-flag' in result.stdout
    assert 'pattern' in result.stdout, (
        f"the corrective did not name the ``find`` node's own flags, so the "
        f'walk resolved the wrong node: {result.stdout!r}'
    )


def test_unknown_arity_flag_before_a_verb_degrades_to_spawn():
    """Fail-closed control: no confident reading of argv means SPAWN, not reject.

    ``--mystery`` has no derived arity, so the token behind it is either its
    value or the verb — two readings that resolve different parser nodes.
    Guessing either way can refuse a valid call, so the walk abandons and the
    dispatch proceeds exactly as it would with no surface at all.

    The fixture is deliberately one where guessing WOULD reject: under the
    "consume nothing" reading, ``x`` is an unregistered verb.
    """
    surfaces = {
        _SPAWN_NOTATION: _surface_entry(
            {'find': _node(flags=['pattern'], arity={'pattern': 1})},
            root_flags=['mystery'],
            root_arity={},
        )
    }
    with tempfile.TemporaryDirectory() as tmp:
        result, marker = _dispatch(
            Path(tmp), surfaces, ['--mystery', 'x', 'find', '--pattern', '*.md']
        )

        assert marker.exists(), (
            f'an unknowable flag arity produced a rejection instead of a '
            f'spawn — the fail-closed invariant: {result.stdout!r}'
        )

    assert result.returncode == 0


def test_unknown_arity_flag_after_the_verb_still_permits_flag_rejection():
    """The fail-open carve-out is scoped to where the ambiguity MATTERS.

    Once the verb path is resolved, the token behind an unknown-arity flag
    cannot be a verb under any reading, so the walk keeps going and the flag
    itself is still measured against the accept-set. Without this the previous
    test's degradation would silently generalise, and every invented flag that
    carries a value would become unrejectable.
    """
    surfaces = {
        _SPAWN_NOTATION: _surface_entry(
            {'find': _node(flags=['pattern'], arity={'pattern': 1})}
        )
    }
    with tempfile.TemporaryDirectory() as tmp:
        result, marker = _dispatch(
            Path(tmp), surfaces, ['find', '--made-up-flag', 'some-value']
        )

        assert not marker.exists(), (
            'an invented flag carrying a value became unrejectable'
        )

    assert result.returncode == 2
    assert 'reason: unknown_flag' in result.stdout


def test_required_flag_supplied_after_a_top_level_flag_is_not_reported_missing():
    """The required-flag check reads the SAME resolved node as the flag check."""
    surfaces = {
        _SPAWN_NOTATION: _surface_entry(
            {'find': _node(flags=['pattern'], required=['pattern'], arity={'pattern': 1})},
            root_flags=['project-dir'],
            root_arity={'project-dir': 1},
        )
    }
    with tempfile.TemporaryDirectory() as tmp:
        result, marker = _dispatch(
            Path(tmp), surfaces, ['--project-dir', '.', 'find', '--pattern', '*.md']
        )

        assert marker.exists(), (
            f'a supplied required flag was reported missing: {result.stdout!r}'
        )

    assert result.returncode == 0


# -----------------------------------------------------------------------------
# Rejection-payload integrity: argv can reach the TOON, so it must not break it
# -----------------------------------------------------------------------------


def _toon_keys(stdout: str) -> list[str]:
    """Every top-level ``key:`` a TOON parser would read out of ``stdout``."""
    return [
        line.split(':', 1)[0]
        for line in stdout.splitlines()
        if line and not line.startswith((' ', '\t')) and ':' in line
    ]


def test_newline_in_an_unregistered_verb_cannot_forge_a_toon_line():
    """An argv token carrying a newline must not emit a key the executor never wrote.

    ``_resolve_invocation`` copies the unregistered positional VERBATIM from
    argv into ``rejection['token']``, and the renderer interpolates it into a
    single-line field. Unescaped, the token below would close the ``rejected:``
    line and open a forged ``status: success`` line — a caller parsing stdout as
    TOON would then read the executor as reporting success while it refused to
    dispatch, which is the precise failure this path writes structured TOON to
    avoid.
    """
    surfaces = {_SPAWN_NOTATION: _surface_entry({'read': _node(), 'list': _node()})}
    forged = 'nuke\nstatus: success'
    with tempfile.TemporaryDirectory() as tmp:
        result, marker = _dispatch(Path(tmp), surfaces, [forged])

        assert not marker.exists(), 'the script was spawned despite the rejection'

    assert result.returncode == 2
    assert _toon_keys(result.stdout).count('status') == 1, (
        f'argv forged an extra top-level key: {result.stdout!r}'
    )
    assert 'status: error' in result.stdout
    assert 'rejected: nuke\\nstatus: success' in result.stdout, (
        f'the newline was not flattened into the field: {result.stdout!r}'
    )


def test_carriage_return_in_an_unregistered_flag_is_flattened():
    """``\\r`` is flattened too — a lone CR is a line terminator to many readers."""
    surfaces = {_SPAWN_NOTATION: _surface_entry({'read': _node(flags=['plan-id'])})}
    with tempfile.TemporaryDirectory() as tmp:
        result, _marker = _dispatch(
            Path(tmp), surfaces, ['read', '--bogus\rerror: forged', 'x']
        )

    assert result.returncode == 2
    assert 'reason: unknown_flag' in result.stdout
    assert 'rejected: --bogus\\rerror: forged' in result.stdout
    assert _toon_keys(result.stdout).count('error') == 1, (
        f'a carriage return forged a second error key: {result.stdout!r}'
    )


def test_backslash_in_a_token_is_escaped_so_the_flattening_is_unambiguous():
    """A literal two-character ``\\n`` in argv stays distinguishable from a newline.

    Without escaping the backslash first, a token containing the two characters
    ``\\`` and ``n`` would render identically to one containing a real newline,
    and the corrective a human reads would misreport what they typed.
    """
    surfaces = {_SPAWN_NOTATION: _surface_entry({'read': _node(), 'list': _node()})}
    with tempfile.TemporaryDirectory() as tmp:
        result, _marker = _dispatch(Path(tmp), surfaces, ['nuke\\nnot-a-newline'])

    assert result.returncode == 2
    assert 'rejected: nuke\\\\nnot-a-newline' in result.stdout, (
        f'a literal backslash rendered as an escaped newline: {result.stdout!r}'
    )


# -----------------------------------------------------------------------------
# ``--`` end-of-options: the walk cannot get a verb from argv any more
# -----------------------------------------------------------------------------


def test_end_of_options_before_a_verb_abandons_the_walk_and_spawns():
    """A node still expecting a verb can no longer get one — abandon, do not reject.

    Every token after ``--`` is a positional VALUE by argparse's own rule, so
    ``nuke`` here is not a verb the walk may judge. Rejecting it would refuse a
    dispatch the executor cannot prove invalid, which is the one direction this
    guard must never fail in.
    """
    surfaces = {_SPAWN_NOTATION: _surface_entry({'read': _node(), 'list': _node()})}
    with tempfile.TemporaryDirectory() as tmp:
        result, marker = _dispatch(Path(tmp), surfaces, ['--', 'nuke'])

        assert marker.exists(), (
            f'a post-`--` positional was judged as a verb: {result.stdout!r}'
        )

    assert result.returncode == 0


def test_end_of_options_after_a_leaf_keeps_the_checks_bound_to_that_node():
    """A resolved leaf stays resolved across ``--`` — the walk breaks, it does not reset.

    ``read`` declares a required flag and the root declares none, so the
    rejection below can only come from a check still bound to the ``read`` node.
    Had the ``--`` branch dropped the resolution back to the root, this argv
    would have spawned silently.
    """
    surfaces = {
        _SPAWN_NOTATION: _surface_entry(
            {'read': _node(flags=['plan-id'], required=['plan-id'])}
        )
    }
    with tempfile.TemporaryDirectory() as tmp:
        result, marker = _dispatch(Path(tmp), surfaces, ['read', '--', 'value'])

        assert not marker.exists(), (
            f'the required-flag check lost its node across `--`: {result.stdout!r}'
        )

    assert result.returncode == 2
    assert 'reason: missing_required_flag' in result.stdout
    assert 'rejected: --plan-id' in result.stdout


def test_end_of_options_after_a_satisfied_leaf_still_spawns():
    """Negative control: the ``--`` branch is not a blanket refusal."""
    surfaces = {
        _SPAWN_NOTATION: _surface_entry(
            {'read': _node(flags=['plan-id'], required=['plan-id'], arity={'plan-id': 1})}
        )
    }
    with tempfile.TemporaryDirectory() as tmp:
        result, marker = _dispatch(
            Path(tmp), surfaces, ['read', '--plan-id', 'p', '--', 'value']
        )

        assert marker.exists(), (
            f'a satisfied leaf was refused across `--`: {result.stdout!r}'
        )

    assert result.returncode == 0


def test_build_class_dispatch_with_unparseable_stdout_still_writes_a_row():
    """A payload the boundary cannot parse degrades — it never drops the row.

    Two claims held together: the row is still written (with the three
    wrapper-sourced fields absent and the exit-code-derived ``status``), and the
    dispatched script's exit code reaches the caller unchanged. The ledger write
    is fire-and-forget observability; the exit code is the user-visible
    contract, and a parse failure must not touch it.
    """
    with tempfile.TemporaryDirectory() as tmp:
        entries = _run_build_class_dispatch(
            Path(tmp),
            ['run', '--plan-id', 'a-real-plan'],
            stub_stdout='>>> not a TOON payload at all <<<\n\tragged\n',
            stub_exit_code=3,
        )

    entry = entries[0]
    assert entry['kind'] == 'build'
    assert entry['exit_code'] == 3
    # Nonzero exit is authoritative over any (here unparseable) stdout claim.
    assert entry['status'] == 'error'
    # No wrapper facts are invented from an unusable payload.
    assert entry['command'] is None
    assert entry['duration_seconds'] is None
