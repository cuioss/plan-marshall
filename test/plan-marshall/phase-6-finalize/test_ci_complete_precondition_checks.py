#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: E402
"""Unit tests for the phase-6-finalize CI-completion precondition resolver.

The helper at ``scripts/ci_complete_precondition.py`` is the dispatcher-side
implementation of the ``requires: [ci-complete]`` frontmatter declaration on
consumer finalize steps. These tests pin the four contracts documented in
the deliverable's Success Criteria:

1. Cache miss → inline ``ci wait`` → cache populated → a second call at the
   same HEAD returns ``satisfied`` without re-polling.
2. HEAD advance between calls → second call re-invokes ``ci wait`` (the
   cache entry is implicitly invalidated by SHA mismatch).
3. ``ci wait`` returns ``final_status: failure`` → helper returns
   ``wait_failed`` with ``ci_final_status: failure``; no cache entry is
   written.
4. ``ci wait`` returns ``status: timeout`` → helper returns ``wait_failed``
   with ``ci_final_status: timeout``; no cache entry is written.
5. The consumed inner ceiling is clamped so ``inner +
   CI_WAIT_OUTER_BUFFER_SECONDS`` stays STRICTLY below
   ``HARNESS_BASH_CEILING_SECONDS`` for every origin (explicit ``--timeout``,
   the persisted ``ci:wait`` learned value, and the module default), while the
   upward ratchet keeps recording the TRUE observed / provider duration.

The tests use the injectable seams (``ci_wait_runner`` / ``git_head_resolver``)
to avoid spawning real subprocesses or hitting live CI. Each test uses a
unique ``plan_id`` to prevent cross-test cache contamination (per
MEMORY.md "Test Isolation Pattern").
"""

from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

# Python 3.14's argparse colorizes ``--help`` output when the environment
# advertises color support (FORCE_COLOR / PYTHON_COLORS), injecting ANSI SGR
# escapes into the usage banner even under captured (non-TTY) stdout. Strip
# them so substring assertions on the banner are robust to color state.
_ANSI_SGR_RE = re.compile(r'\x1b\[[0-9;]*m')


def _strip_ansi(text: str) -> str:
    """Remove ANSI SGR color escapes from ``text``."""
    return _ANSI_SGR_RE.sub('', text)


# PlanContext fixture is provided automatically by conftest.py as `plan_context`.

# ---------------------------------------------------------------------------
# Module loading — the helper is registered in the executor mapping under
# the notation ``plan-marshall:phase-6-finalize:ci_complete_precondition``,
# but the unit tests still load it via importlib from the source path so
# the test seams (``ci_wait_runner`` / ``git_head_resolver``) can be
# injected at the Python-call level without spawning a subprocess. The
# executor-level invocation is exercised separately in
# :func:`test_executor_invocation_with_scrubbed_pythonpath` below.
# ---------------------------------------------------------------------------

from conftest import PROJECT_ROOT, get_scripts_dir, load_script_module

_SCRIPTS_DIR = get_scripts_dir('plan-marshall', 'phase-6-finalize')


def _load_module(name: str, filename: str):
    return load_script_module('plan-marshall', 'phase-6-finalize', filename, name)


_resolver_mod = _load_module(
    'ci_complete_precondition',
    'ci_complete_precondition.py',
)
resolve = _resolver_mod.resolve
DEFAULT_CI_WAIT_TIMEOUT_SECONDS = _resolver_mod.DEFAULT_CI_WAIT_TIMEOUT_SECONDS
CI_WAIT_OUTER_BUFFER_SECONDS = _resolver_mod.CI_WAIT_OUTER_BUFFER_SECONDS
HARNESS_BASH_CEILING_SECONDS = _resolver_mod.HARNESS_BASH_CEILING_SECONDS
_MAX_INNER_WAIT_SECONDS = _resolver_mod._MAX_INNER_WAIT_SECONDS
_cache_path = _resolver_mod._cache_path
_read_cache = _resolver_mod._read_cache

# ---------------------------------------------------------------------------
# Repo root anchor — the executor lives at ``<repo>/.plan/execute-script.py``
# and the renamed source script at the bundled path under
# ``marketplace/bundles/...``. The tests below subprocess the executor with
# a deliberately scrubbed environment, so we need an absolute anchor that
# does NOT depend on the parent process's cwd or PYTHONPATH.
# ---------------------------------------------------------------------------

_EXECUTOR_PATH = PROJECT_ROOT / '.plan' / 'execute-script.py'
_SOURCE_SCRIPT_PATH = _SCRIPTS_DIR / 'ci_complete_precondition.py'


# ---------------------------------------------------------------------------
# Test seams: deterministic stand-ins for git and the ci wait subprocess.
# ---------------------------------------------------------------------------


class _StubGitHead:
    """Deterministic ``git rev-parse HEAD`` substitute."""

    def __init__(self, sha: str) -> None:
        self.sha = sha
        self.calls: list[str] = []

    def __call__(self, worktree_path: str) -> str:
        self.calls.append(worktree_path)
        return self.sha


class _StubCiWait:
    """Records call count and returns canned envelopes per invocation."""

    def __init__(self, envelopes: list[dict]) -> None:
        self.envelopes = envelopes
        self.calls: list[tuple] = []

    def __call__(
        self,
        plan_id: str,
        pr_number: int,
        timeout_seconds: int,
        worktree_path: str,
    ) -> dict:
        self.calls.append((plan_id, pr_number, timeout_seconds, worktree_path))
        # Pop the next envelope; fail loudly if exhausted (test bug).
        if not self.envelopes:
            raise AssertionError('Stub ci_wait_runner exhausted — test scheduled more calls than expected')
        return self.envelopes.pop(0)


class _StubTimeoutSet:
    """Record every observed CI duration passed to the timeout_set seam.

    Exposes the recorded durations under BOTH ``recorded`` (the D3
    elapsed-at-deadline ratchet tests) and ``durations`` (the run-config
    write-back tests) so a single stub serves every assertion style. The
    two names alias the same append log.
    """

    def __init__(self) -> None:
        self.recorded: list[int] = []
        self.durations: list[int] = self.recorded

    def __call__(self, duration_seconds: int) -> None:
        self.recorded.append(duration_seconds)


class _StubTimeoutGet:
    """Return canned ci:wait ceilings per successive resolve call."""

    def __init__(self, ceilings: list[int]) -> None:
        self.ceilings = ceilings
        self.calls: list[int] = []

    def __call__(self, default_seconds: int) -> int:
        self.calls.append(default_seconds)
        if not self.ceilings:
            return default_seconds
        return self.ceilings.pop(0)


class _StubClock:
    """Deterministic monotonic-clock stub returning successive tick values.

    ``resolve`` calls the clock exactly twice per invocation (immediately
    before and after the ``ci wait`` subprocess), so a list of ``[start, end]``
    ticks yields a measured elapsed of ``end - start``.
    """

    def __init__(self, ticks: list[float]) -> None:
        self.ticks = ticks
        self.calls = 0

    def __call__(self) -> float:
        value = self.ticks[self.calls]
        self.calls += 1
        return value


_SHA_A = 'a' * 40
_SHA_B = 'b' * 40
_PR = 123
_WORKTREE = '/nonexistent/worktree/path'  # Never read — git stub overrides.


# ---------------------------------------------------------------------------
# Test 1 — cache miss → ci wait succeeds → cache populated → second call
# returns ``satisfied`` without re-polling.
# ---------------------------------------------------------------------------


class _CapturingSubprocessRun:
    """Records the ``cmd`` list passed to ``subprocess.run`` and returns a
    canned ``CompletedProcess`` carrying a parseable TOON envelope.
    """

    def __init__(self, stdout: str) -> None:
        self.stdout = stdout
        self.captured_cmd: list[str] | None = None
        self.captured_kwargs: dict | None = None

    def __call__(
        self, cmd, *args, **kwargs
    ):  # deliberately unannotated: it accepts whatever subprocess.run is called with
        self.captured_cmd = list(cmd)
        self.captured_kwargs = dict(kwargs)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=self.stdout, stderr='')


def _raise_timeout_expired(
    cmd, *args, **kwargs
):  # deliberately unannotated: it accepts whatever subprocess.run is called with
    """subprocess.run stand-in that always raises TimeoutExpired.

    Mirrors the real signature: subprocess.run forwards its ``timeout``
    kwarg into the exception so the message can name the breached ceiling.
    """
    raise subprocess.TimeoutExpired(cmd=cmd, timeout=kwargs.get('timeout'))


class _StubTimeoutGetSeeded:
    """Deterministic ``run_config timeout get`` substitute.

    Returns a fixed seeded value, ignoring the requested default — this
    models a run-configuration.json that already carries a ci:wait entry.
    """

    def __init__(self, seeded_value: int) -> None:
        self.seeded_value = seeded_value
        self.calls: list[int] = []

    def __call__(self, default_seconds: int) -> int:
        self.calls.append(default_seconds)
        return self.seeded_value


class _StubTimeoutGetMissing:
    """Models a run-configuration.json with no ci:wait entry — the helper
    echoes the supplied default straight back.
    """

    def __init__(self) -> None:
        self.calls: list[int] = []

    def __call__(self, default_seconds: int) -> int:
        self.calls.append(default_seconds)
        return default_seconds


_FIXTURE_DIR = PROJECT_ROOT / 'test' / 'plan-marshall' / 'phase-6-finalize' / 'fixtures' / 'ci-wait'


def _load_parse_toon():
    """Import parse_toon from the ref-toon-format skill.

    Deliberately UNREGISTERED: ``toon_parser`` is imported plainly across the
    test tree, so publishing this copy under that name would displace the module
    those imports already hold.
    """
    return load_script_module('plan-marshall', 'ref-toon-format', 'toon_parser.py', register=False).parse_toon


_parse_toon = _load_parse_toon()


def _make_fixture_wait_runner(parsed: dict):
    """Build a ci_wait_runner stub that returns the parsed-fixture dict."""

    def _runner(
        plan_id, pr_number, timeout_seconds, worktree_path
    ):  # the parameters are unused: the stub exists to match the real runner's signature
        return parsed

    return _runner


def _run_fixture_through_resolver(fixture_path, plan_id):
    """Parse a fixture file and feed the parsed dict through resolve()."""
    raw = fixture_path.read_text()
    parsed = _parse_toon(raw)
    runner = _make_fixture_wait_runner(parsed)
    git_stub = _StubGitHead(_SHA_A)
    # Isolate the timeout-path ratchet write: a fixture carrying a
    # deadline_exceeded envelope with a duration_sec would otherwise call the
    # real run-config timeout-set subprocess. The no-op stub keeps the fixture
    # tests hermetic.
    return resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=runner,
        git_head_resolver=git_stub,
        timeout_set_runner=_StubTimeoutSet(),
    )


def _sonar_red_ci_envelope() -> dict:
    """A terminal CI envelope that is red ONLY via the Sonar check.

    This is the TokenSheriff-572 scenario: the global CI gate is red, but the
    single failing check is the Sonar analysis. Under the retired global-CI
    gate this blackout-skipped BOTH producer FINDs.
    """
    return {
        'status': 'success',
        'final_status': 'failure',
        'failing_checks': [
            {'name': 'SonarCloud Code Analysis', 'conclusion': 'FAILURE'},
        ],
        'wait_outcome': 'completed',
    }


def test_cache_miss_then_hit_does_not_repoll(plan_context):
    plan_id = 'ci-precond-cache-miss-then-hit'
    git_stub = _StubGitHead(_SHA_A)
    # Only one envelope provided — a second call would raise.
    wait_stub = _StubCiWait([{'status': 'success', 'final_status': 'success'}])

    first = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=git_stub,
    )

    assert first['status'] == 'wait_succeeded'
    assert first['head_sha'] == _SHA_A
    assert first['ci_final_status'] == 'success'
    assert len(wait_stub.calls) == 1
    # Cache file written with the success outcome.
    cache_after = _read_cache(plan_id)
    assert cache_after is not None
    assert cache_after['head_sha'] == _SHA_A
    assert cache_after['ci_final_status'] == 'success'

    # Second call at the same HEAD with NO new ci wait envelopes.
    second = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=git_stub,
    )
    assert second['status'] == 'satisfied'
    assert second['head_sha'] == _SHA_A
    assert second['ci_final_status'] == 'success'
    # Critically: ci wait was NOT invoked a second time.
    assert len(wait_stub.calls) == 1, 'satisfied must short-circuit without re-invoking ci wait'


def test_ci_timeout_returns_wait_failed_with_timeout_reason(plan_context):
    plan_id = 'ci-precond-timeout'
    git_stub = _StubGitHead(_SHA_A)
    timeout_set_stub = _StubTimeoutSet()
    wait_stub = _StubCiWait(
        [
            {
                'status': 'error',
                'operation': 'ci_wait',
                'error': 'Timeout waiting for CI',
                'pr_number': _PR,
                'duration_sec': 600,
                'wait_outcome': 'deadline_exceeded',
                'last_status': 'pending',
            }
        ]
    )

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=git_stub,
        timeout_set_runner=timeout_set_stub,
    )

    assert result['status'] == 'wait_failed'
    assert result['head_sha'] == _SHA_A
    assert result['ci_final_status'] == 'timeout', (
        'Timeout envelope must surface ci_final_status=timeout so the '
        'dispatcher can include the reason in the consumer step display'
    )
    cache_path = _cache_path(plan_id)
    assert not cache_path.exists(), 'Timeout outcomes must not be cached; re-entry must re-poll'
    # The deadline path records the provider's true duration so the ci:wait
    # ceiling ratchets upward — the starved-ratchet fix.
    assert timeout_set_stub.recorded == [600], (
        'A deadline_exceeded envelope carrying duration_sec must record it '
        'via timeout_set so the ci:wait ceiling can ratchet upward'
    )


def test_sub_ceiling_non_success_does_not_record(plan_context):
    """An immediate non-success envelope that did NOT consume the full wait
    (elapsed << ceiling, no duration_sec) MUST NOT record — a sub-ceiling
    observation would pull the ratchet DOWN via compute_weighted_timeout.
    """
    plan_id = 'ci-precond-sub-ceiling'
    git_stub = _StubGitHead(_SHA_A)
    timeout_set_stub = _StubTimeoutSet()
    # Executor-crash-style error envelope, no duration_sec.
    wait_stub = _StubCiWait([{'status': 'error', 'error': 'executor crashed immediately'}])
    # clock ticks [0, 3] → measured elapsed 3s, well below the 600s ceiling.
    clock = _StubClock([0.0, 3.0])

    resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        timeout_seconds=600,
        ci_wait_runner=wait_stub,
        git_head_resolver=git_stub,
        timeout_set_runner=timeout_set_stub,
        monotonic_clock=clock,
    )

    assert timeout_set_stub.recorded == [], 'A sub-ceiling elapsed with no provider duration must not be recorded'


def test_executor_invocation_with_scrubbed_pythonpath():
    """Spawn the executor proxy with PYTHONPATH scrubbed and confirm the
    renamed helper still resolves cross-skill imports via the executor's
    injected paths.
    """
    # The executor must be present before the subprocess runs. The
    # session-level conftest bootstrap ensures this for fresh checkouts;
    # local dev environments and CI both pass through that path.
    assert _EXECUTOR_PATH.is_file(), (
        f'Executor missing at {_EXECUTOR_PATH} — conftest session bootstrap should have generated it'
    )

    # Build a deliberately scrubbed environment: drop PYTHONPATH and
    # PYTHONHOME entirely so the subprocess CANNOT inherit any path
    # injection from the calling pytest session. Keep PATH / HOME /
    # encoding vars so subprocess startup itself remains viable.
    scrubbed_env = {k: v for k, v in os.environ.items() if k not in {'PYTHONPATH', 'PYTHONHOME'}}
    # Belt-and-braces: even an inherited '' value would break our intent.
    assert 'PYTHONPATH' not in scrubbed_env
    assert 'PYTHONHOME' not in scrubbed_env

    completed = subprocess.run(
        [
            sys.executable,
            str(_EXECUTOR_PATH),
            'plan-marshall:phase-6-finalize:ci_complete_precondition',
            '--help',
        ],
        capture_output=True,
        text=True,
        env=scrubbed_env,
        cwd=str(PROJECT_ROOT),
        timeout=30,
        check=False,
    )

    # The subprocess MUST exit cleanly. A non-zero exit here means the
    # renamed script failed to import its cross-skill dependencies under
    # the executor's PYTHONPATH injection — the exact failure mode the
    # lesson is meant to prevent.
    assert completed.returncode == 0, (
        f'Executor invocation failed (exit={completed.returncode}): '
        f'stdout={completed.stdout!r}, stderr={completed.stderr!r}'
    )

    # The argparse help banner MUST appear on stdout. We pin the script
    # filename (``ci_complete_precondition.py``) and the documented
    # ``resolve`` subcommand to guard against accidental rename drift in
    # the future. Strip ANSI color escapes first so the substring checks
    # hold whether or not Python 3.14's argparse colorized the banner.
    plain_stdout = _strip_ansi(completed.stdout)
    assert 'usage: ci_complete_precondition.py' in plain_stdout, (
        f'Argparse usage banner missing from stdout: {completed.stdout!r}'
    )
    assert 'resolve' in plain_stdout, f'``resolve`` subcommand missing from help output: {completed.stdout!r}'


def test_no_checks_returns_distinct_ci_final_status(plan_context):
    """``final_status: none`` from ``ci wait`` MUST surface as
    ``ci_final_status: no_checks`` so the dispatcher can distinguish
    "CI never ran" from a real failure and route to the
    ``ci-verify-missing`` producer.
    """
    plan_id = 'ci-precond-no-checks'
    git_stub = _StubGitHead(_SHA_A)
    wait_stub = _StubCiWait(
        [
            {
                'status': 'success',
                'final_status': 'none',
                'failing_checks': [],
                'wait_outcome': 'completed',
            }
        ]
    )

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=git_stub,
    )

    assert result['status'] == 'wait_failed'
    assert result['ci_final_status'] == 'no_checks', (
        'no_checks must be distinct from failure so the dispatcher can '
        'route to ci-verify-missing instead of ci-verify-build'
    )
    assert result['failing_checks'] == []
    # Cache MUST remain absent — no_checks is a non-cacheable verdict.
    assert not _cache_path(plan_id).exists()


def test_wait_succeeded_does_not_carry_failing_checks_field(plan_context):
    """``wait_succeeded`` (fresh poll succeeded) MUST NOT include
    failing_checks / wait_outcome — same rationale as satisfied above.
    """
    plan_id = 'ci-precond-wait-succeeded-no-failing-checks'
    git_stub = _StubGitHead(_SHA_A)
    wait_stub = _StubCiWait([{'status': 'success', 'final_status': 'success'}])

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=git_stub,
    )

    assert result['status'] == 'wait_succeeded'
    assert 'failing_checks' not in result
    assert 'wait_outcome' not in result


def test_run_ci_wait_returns_timeout_envelope_on_subprocess_timeout(monkeypatch):
    """``_run_ci_wait`` MUST catch ``subprocess.TimeoutExpired`` and return a
    timeout-like envelope instead of propagating the exception.
    """
    monkeypatch.setattr(_resolver_mod.subprocess, 'run', _raise_timeout_expired)

    result = _resolver_mod._run_ci_wait(
        plan_id='ci-precond-subprocess-timeout',
        pr_number=_PR,
        timeout_seconds=DEFAULT_CI_WAIT_TIMEOUT_SECONDS,
        worktree_path=str(PROJECT_ROOT),
    )

    # The envelope is a dict (no exception escaped) with the timeout markers.
    assert isinstance(result, dict)
    assert result['status'] == 'timeout', (
        f'A wedged ci wait subprocess must surface a timeout-like envelope, not {result.get("status")!r}'
    )
    assert result['wait_outcome'] == 'deadline_exceeded', (
        'The deadline_exceeded marker lets downstream consumers classify '
        'the precondition decision into the timeout triage producer'
    )
    # The error message names the breached host ceiling (timeout_seconds + 30).
    assert 'error' in result
    assert str(DEFAULT_CI_WAIT_TIMEOUT_SECONDS + 30) in result['error']


def test_resolve_uses_default_timeout_when_no_run_config_entry(plan_context):
    """(b) With no ci:wait entry, the run-config helper echoes the supplied
    default, so resolve() falls back to DEFAULT_CI_WAIT_TIMEOUT_SECONDS —
    which the harness-ceiling clamp then reduces to _MAX_INNER_WAIT_SECONDS,
    because the raw 600s default plus the outer buffer would reach the
    harness's per-call Bash ceiling.
    """
    plan_id = 'ci-precond-runconfig-missing'
    get_stub = _StubTimeoutGetMissing()
    set_stub = _StubTimeoutSet()
    wait_stub = _StubCiWait([{'status': 'success', 'final_status': 'success'}])

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=_StubGitHead(_SHA_A),
        timeout_get_runner=get_stub,
        timeout_set_runner=set_stub,
    )

    assert result['status'] == 'wait_succeeded'
    assert get_stub.calls == [DEFAULT_CI_WAIT_TIMEOUT_SECONDS]
    # The default reached the clamp, which reduced it to the largest inner
    # ceiling that still leaves the outer call strictly under the harness.
    assert wait_stub.calls[0][2] == _MAX_INNER_WAIT_SECONDS
    assert wait_stub.calls[0][2] + CI_WAIT_OUTER_BUFFER_SECONDS < HARNESS_BASH_CEILING_SECONDS


def test_consume_failures_mode_threads_wait_failed_envelope(plan_context):
    """Regression guard for the consume-failures envelope.

    A failing CI run resolved with ``mode='consume-failures'`` MUST surface
    the full ``wait_failed`` envelope — ``failing_checks``, ``wait_outcome``,
    AND a ``mode: consume-failures`` echo — so the ``default:ci-verify``
    consumer body can classify the failures into the multi-failure-mode
    taxonomy. The previous strict-only resolver short-circuited the body
    on ``wait_failed``, making the classify → file-findings →
    verification-feedback → loop_back machinery unreachable on red CI.

    This test feeds a ``ci_wait_runner`` seam reporting a failure envelope
    with two failing checks and asserts the resolver output preserves the
    mode, the failing-check enumeration, and the wait outcome.
    """
    plan_id = 'ci-precond-consume-failures-mode'
    git_stub = _StubGitHead(_SHA_A)
    wait_stub = _StubCiWait(
        [
            {
                'status': 'success',
                'final_status': 'failure',
                'failing_checks': [
                    {'name': 'lint', 'conclusion': 'FAILURE'},
                    {'name': 'unit-tests', 'conclusion': 'FAILURE'},
                ],
                'wait_outcome': 'completed',
            }
        ]
    )

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=git_stub,
        mode='consume-failures',
    )

    # The wait_failed envelope was NOT short-circuited — the resolver
    # returned the failure envelope verbatim so the ci-verify body
    # can classify the failing checks.
    assert result['status'] == 'wait_failed', (
        f'consume-failures resolution must surface wait_failed, not '
        f'{result["status"]!r} — short-circuiting on wait_failed would '
        'hide the failing checks this resolution exists to surface'
    )
    assert result['ci_final_status'] == 'failure'
    # The mode echo is the load-bearing signal: consumers branch on
    # this field to decide whether to short-circuit or thread the
    # envelope through to their body.
    assert result['mode'] == 'consume-failures', (
        'resolver output must echo the mode value so consumers can '
        'tell strict-mode wait_failed (short-circuit) from '
        'consume-failures wait_failed (run body with envelope)'
    )
    # The full failing-check enumeration is preserved verbatim.
    assert result['failing_checks'] == [
        {'name': 'lint', 'conclusion': 'FAILURE'},
        {'name': 'unit-tests', 'conclusion': 'FAILURE'},
    ]
    assert result['wait_outcome'] == 'completed'


def test_resolve_skips_writeback_when_duration_absent(plan_context):
    """When the ci wait envelope omits ``duration_sec``, resolve() MUST NOT
    write a bogus value back — the adaptive update is skipped.
    """
    plan_id = 'ci-precond-runconfig-no-duration'
    get_stub = _StubTimeoutGetMissing()
    set_stub = _StubTimeoutSet()
    # Envelope carries no duration_sec field.
    wait_stub = _StubCiWait([{'status': 'success', 'final_status': 'success'}])

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=_StubGitHead(_SHA_A),
        timeout_get_runner=get_stub,
        timeout_set_runner=set_stub,
    )

    assert result['status'] == 'wait_succeeded'
    # No duration → no write-back.
    assert set_stub.durations == []


def test_fixture_single_check_success_resolves_to_success(plan_context):
    """Smallest non-empty checks table — minimum parser surface."""
    fixture = _FIXTURE_DIR / 'single-check-success.toon'
    plan_id = 'ci-fixture-single-check-success'
    result = _run_fixture_through_resolver(fixture, plan_id)
    assert result['status'] == 'wait_succeeded'
    assert result['ci_final_status'] == 'success'


def test_fixture_failure_with_failing_checks_resolves_to_failure(plan_context):
    """One failing check — exercises failing_checks[] enumeration."""
    fixture = _FIXTURE_DIR / 'failure-with-failing-checks.toon'
    plan_id = 'ci-fixture-failure-with-failing-checks'
    result = _run_fixture_through_resolver(fixture, plan_id)
    assert result['status'] == 'wait_failed'
    assert result['ci_final_status'] == 'failure'
    assert len(result.get('failing_checks') or []) == 1


def test_fixture_no_checks_resolves_to_no_checks(plan_context):
    """Empty checks[] (no CI configured) — distinct from real failure."""
    fixture = _FIXTURE_DIR / 'no-checks.toon'
    plan_id = 'ci-fixture-no-checks'
    result = _run_fixture_through_resolver(fixture, plan_id)
    assert result['status'] == 'wait_failed'
    assert result['ci_final_status'] == 'no_checks'


def test_fixture_check_name_special_chars_preserves_all_rows():
    """Stressor (b): check names containing special characters — including
    the bug-trigger colon (`lint:strict`, `coverage = 95%`) — must NOT
    short-circuit the inline-table parse.

    A key/value detection heuristic that ignores tabs reads
    `lint:strict\\tcompleted\\t...` as a new key/value pair once `.strip()`
    leaves the colon at offset 4, breaks out of the array, and silently
    truncates downstream rows. This test feeds the raw fixture through
    `parse_toon` directly and asserts the full
    row count is preserved.
    """
    fixture = _FIXTURE_DIR / 'check-name-special-chars.toon'
    raw = fixture.read_text()
    parsed = _parse_toon(raw)
    assert len(parsed.get('checks') or []) == 5, (
        f'Expected 5 checks rows, got {len(parsed.get("checks") or [])}. '
        'The parser truncated the array — most likely the key/value '
        'detection heuristic in `_parse_uniform_array` fired on a row '
        "whose first column legitimately contains ':' (e.g. 'lint:strict')."
    )
    # The bug-trigger row must be present with name verbatim.
    names = [c['name'] for c in parsed['checks']]
    assert 'lint:strict' in names, f'lint:strict row missing: {names!r}'
    assert 'coverage = 95%' in names, f'coverage row missing: {names!r}'


def test_fixture_older_gh_envelope_resolves_to_success(plan_context):
    """Stressor (d): older `gh` envelope shapes with empty url and run_id
    fields must still parse and resolve to success when final_status is set."""
    fixture = _FIXTURE_DIR / 'older-gh-envelope.toon'
    plan_id = 'ci-fixture-older-gh'
    result = _run_fixture_through_resolver(fixture, plan_id)
    assert result['status'] == 'wait_succeeded'
    assert result['ci_final_status'] == 'success'


def test_fixture_failing_checks_with_colon_names_forwards_full_list(plan_context):
    """Companion regression for stressor (b): when a `failing_checks[N]:`
    inline-table block has rows whose first column contains `:` (e.g.
    `lint:strict`, `coverage:enforce`), the resolver MUST forward the full
    failing-check enumeration — not a truncated/empty list.

    Pre-fix observed: `failing_checks` came back as `[]` because the parser
    broke out of the array on the first colon-bearing row, silently
    losing both failure entries. Consumers that route on `failing_checks`
    (e.g. ci-verify consume-failures mode) would receive no signal about
    which checks actually failed.
    """
    fixture = _FIXTURE_DIR / 'failing-checks-with-colon-names.toon'
    plan_id = 'ci-fixture-failing-colon-names'
    result = _run_fixture_through_resolver(fixture, plan_id)
    assert result['status'] == 'wait_failed'
    assert result['ci_final_status'] == 'failure'
    failing_names = [c['name'] for c in result.get('failing_checks') or []]
    assert failing_names == ['lint:strict', 'coverage:enforce'], (
        f'Expected [lint:strict, coverage:enforce], got {failing_names!r}. '
        'If this is an empty list, the parser regression has returned — '
        'the key/value detection heuristic in _parse_uniform_array fired '
        'on the colon-bearing first column and truncated the array.'
    )


def test_run_config_timeout_get_uses_resolved_executor(tmp_path, monkeypatch):
    """_run_run_config_timeout_get spawns the helper-resolved executor path."""
    executor = tmp_path / 'execute-script.py'
    captured = {}

    def fake_run(cmd, *args, **kwargs):
        captured['cmd'] = cmd

        class _Proc:
            returncode = 0
            stdout = 'timeout_seconds: 777\n'
            stderr = ''

        return _Proc()

    monkeypatch.setattr(_resolver_mod, 'get_executor_path', lambda: executor)
    monkeypatch.setattr(_resolver_mod.subprocess, 'run', fake_run)

    result = _resolver_mod._run_run_config_timeout_get(600)

    assert result == 777
    assert str(executor) in captured['cmd']


def test_signal_arm_review_red_ci_proceeds_as_settled(plan_context):
    """(a) The SAME Sonar-only red CI leaves the review arm ``settled`` →
    ``arm_proceed`` so ``automatic-review`` fetches the PR comments. A red CI
    unrelated to the review signal no longer skips the comment FIND.
    """
    plan_id = 'ci-precond-signal-review-red'
    wait_stub = _StubCiWait([_sonar_red_ci_envelope()])

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=_StubGitHead(_SHA_A),
        signal_arm='review',
    )

    assert result['status'] == 'arm_proceed'
    assert result['signal_arm'] == 'review'
    assert result['arm_state'] == 'settled', (
        'the review arm is stable once CI has FINISHED regardless of colour — a red CI must not label it failed'
    )
    assert result['ci_final_status'] == 'failure'


def test_signal_arm_green_review_settles(plan_context):
    """CI green → the review arm settles cleanly → ``arm_proceed``."""
    plan_id = 'ci-precond-signal-green-review'
    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=_StubCiWait([{'status': 'success', 'final_status': 'success'}]),
        git_head_resolver=_StubGitHead(_SHA_A),
        signal_arm='review',
    )
    assert result['status'] == 'arm_proceed'
    assert result['arm_state'] == 'settled'
    assert result['ci_final_status'] == 'success'


def test_signal_arm_no_checks_sonar_proceeds_failed(plan_context):
    """``final_status: none`` (no CI configured) is a terminal state → the
    sonar arm proceeds (labelled failed, since the gate is not green).
    """
    plan_id = 'ci-precond-signal-no-checks-sonar'
    wait_stub = _StubCiWait(
        [
            {
                'status': 'success',
                'final_status': 'none',
                'failing_checks': [],
                'wait_outcome': 'completed',
            }
        ]
    )

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=_StubGitHead(_SHA_A),
        signal_arm='sonar',
    )

    assert result['status'] == 'arm_proceed'
    assert result['arm_state'] == 'failed'
    assert result['ci_final_status'] == 'no_checks'


def test_build_parser_accepts_signal_arm():
    """The CLI exposes ``--signal-arm`` with the {ci, review, sonar} choices."""
    parser = _resolver_mod.build_parser()
    args = parser.parse_args(
        [
            'resolve',
            '--plan-id',
            'p',
            '--worktree-path',
            '/w',
            '--pr-number',
            '1',
            '--signal-arm',
            'sonar',
        ]
    )
    assert args.signal_arm == 'sonar'


def test_explicit_timeout_above_the_harness_bound_is_clamped(plan_context):
    """An explicit ``--timeout`` overrides the learned value but does NOT
    waive the clamp — the harness ceiling binds every origin.
    """
    plan_id = 'ci-precond-clamp-explicit'
    get_stub = _StubTimeoutGetSeeded(seeded_value=120)
    wait_stub = _StubCiWait([{'status': 'success', 'final_status': 'success'}])

    resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        timeout_seconds=5000,
        ci_wait_runner=wait_stub,
        git_head_resolver=_StubGitHead(_SHA_A),
        timeout_get_runner=get_stub,
        timeout_set_runner=_StubTimeoutSet(),
    )

    # The explicit value still bypasses the run-config lookup entirely...
    assert get_stub.calls == []
    # ...but it is clamped exactly like a learned value.
    assert wait_stub.calls[0][2] == _MAX_INNER_WAIT_SECONDS


def test_outer_subprocess_timeout_is_strictly_below_the_harness_ceiling(plan_context, monkeypatch):
    """End-to-end through the REAL ``_run_ci_wait``: the outer
    ``subprocess.run(timeout=...)`` deadline the resolver actually consumes
    MUST be strictly below ``HARNESS_BASH_CEILING_SECONDS``, even when the
    persisted ceiling has ratcheted far above it.

    This is the load-bearing assertion of the deliverable — the seam-injected
    tests above pin the clamped INNER value, but only this one observes the
    OUTER deadline the host platform measures against.
    """
    capturing = _CapturingSubprocessRun(stdout='status: success\nfinal_status: success\n')
    monkeypatch.setattr(_resolver_mod.subprocess, 'run', capturing)

    result = resolve(
        plan_id='ci-precond-clamp-outer-deadline',
        worktree_path=str(PROJECT_ROOT),
        pr_number=_PR,
        git_head_resolver=_StubGitHead(_SHA_A),
        timeout_get_runner=_StubTimeoutGetSeeded(seeded_value=5000),
        timeout_set_runner=_StubTimeoutSet(),
    )

    assert result['status'] == 'wait_succeeded'
    assert capturing.captured_kwargs is not None
    outer = capturing.captured_kwargs['timeout']
    assert outer < HARNESS_BASH_CEILING_SECONDS, (
        f'The outer subprocess deadline ({outer}s) must be STRICTLY below '
        f'the harness per-call Bash ceiling '
        f'({HARNESS_BASH_CEILING_SECONDS}s); otherwise the harness kills the '
        'call before the resolver can return a structured envelope'
    )
    assert outer == _MAX_INNER_WAIT_SECONDS + CI_WAIT_OUTER_BUFFER_SECONDS


def test_ratchet_records_true_provider_duration_despite_the_clamp(plan_context):
    """The clamp bounds only the CONSUMED ceiling. The provider's true
    check-run duration is still recorded verbatim via ``timeout_set``, so the
    persisted ``ci:wait`` value stays honest and is free to exceed the clamp.
    """
    plan_id = 'ci-precond-clamp-ratchet-provider'
    set_stub = _StubTimeoutSet()
    wait_stub = _StubCiWait(
        [
            {
                'status': 'error',
                'wait_outcome': 'deadline_exceeded',
                'duration_sec': 4200,
            }
        ]
    )

    resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=_StubGitHead(_SHA_A),
        timeout_get_runner=_StubTimeoutGetSeeded(seeded_value=5000),
        timeout_set_runner=set_stub,
        monotonic_clock=_StubClock([0.0, float(_MAX_INNER_WAIT_SECONDS + 1)]),
    )

    assert set_stub.recorded == [4200], (
        'The clamp must not truncate the recorded observation — only the '
        'consumed ceiling is clamped, the persisted value stays truthful'
    )
    assert set_stub.recorded[0] > _MAX_INNER_WAIT_SECONDS, (
        'The recorded duration is deliberately allowed above the clamp'
    )


def test_build_parser_signal_arm_defaults_none():
    """When ``--signal-arm`` is omitted the parsed value is ``None`` — the
    legacy global path is the default.
    """
    parser = _resolver_mod.build_parser()
    args = parser.parse_args(
        [
            'resolve',
            '--plan-id',
            'p',
            '--worktree-path',
            '/w',
            '--pr-number',
            '1',
        ]
    )
    assert args.signal_arm is None


# ---------------------------------------------------------------------------
# D2 — no-ceiling fallback: bounded loud clamp with deadline_exceeded re-poll
# ---------------------------------------------------------------------------


def _simulate_no_ceiling_target(monkeypatch):
    """Pretend the active target declares no harness Bash ceiling."""
    monkeypatch.setattr(_resolver_mod, '_MAX_INNER_WAIT_SECONDS', None)


def test_no_ceiling_clamp_bounds_above_to_finite_fallback(monkeypatch):
    """Without a harness ceiling the clamp bounds above at the finite fallback."""
    _simulate_no_ceiling_target(monkeypatch)
    fallback = _resolver_mod.NO_CEILING_FALLBACK_INNER_SECONDS

    assert _resolver_mod._clamp_wait_ceiling(3600) == fallback
    assert _resolver_mod._clamp_wait_ceiling(fallback) == fallback
    # The lower bound survives the fallback: zero never yields a
    # zero-timeout subprocess call.
    assert _resolver_mod._clamp_wait_ceiling(0) == 1


def test_no_ceiling_resolve_is_loud_and_bounded(plan_context, monkeypatch, capsys):
    """Still-running CI under no ceiling resolves to deadline_exceeded re-poll.

    The consumed wait is the finite fallback (not unbounded), the
    disabled-clamp state is loud (stderr warning + ``clamp_state`` TOON
    field), and the timeout outcome is uncached so re-entry re-polls.
    """
    _simulate_no_ceiling_target(monkeypatch)
    fallback = _resolver_mod.NO_CEILING_FALLBACK_INNER_SECONDS
    plan_id = 'ci-precond-no-ceiling-timeout'
    git_stub = _StubGitHead(_SHA_A)
    timeout_set_stub = _StubTimeoutSet()
    wait_stub = _StubCiWait(
        [
            {
                'status': 'error',
                'operation': 'ci_wait',
                'error': 'Timeout waiting for CI',
                'pr_number': _PR,
                'failing_checks': [{'name': 'build', 'conclusion': None}],
                'wait_outcome': 'deadline_exceeded',
                'last_status': 'pending',
            }
        ]
    )

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=git_stub,
        timeout_get_runner=_StubTimeoutGetMissing(),
        timeout_set_runner=timeout_set_stub,
    )

    # Bounded: the wait consumed exactly the finite fallback ceiling.
    assert wait_stub.calls[0][2] == fallback
    # Verdict: still-running CI resolves to deadline_exceeded re-poll.
    assert result['status'] == 'wait_failed'
    assert result['ci_final_status'] == 'timeout'
    assert result['wait_outcome'] == 'deadline_exceeded'
    assert result['failing_checks'] == [{'name': 'build', 'conclusion': None}]
    # Loud: the disabled-clamp state rides the envelope ...
    assert result['clamp_state'] == 'no-ceiling-fallback'
    # ... and the warning names the fallback on stderr.
    captured = capsys.readouterr()
    assert 'no harness Bash ceiling' in captured.err
    assert str(fallback) in captured.err
    # Uncached: re-entry re-polls.
    assert not _cache_path(plan_id).exists()


def test_no_ceiling_upward_ratchet_records_full_request_elapsed(plan_context, monkeypatch):
    """The fallback does not corrupt the ratchet: a full-request elapsed records.

    With the default origin the requested ceiling equals the consumed
    fallback, so an elapsed-at-deadline at the bound still satisfies the
    ``elapsed >= requested`` guard and the learned ``ci:wait`` value records
    honestly instead of going silent.
    """
    _simulate_no_ceiling_target(monkeypatch)
    fallback = _resolver_mod.NO_CEILING_FALLBACK_INNER_SECONDS
    plan_id = 'ci-precond-no-ceiling-ratchet'
    timeout_set_stub = _StubTimeoutSet()
    wait_stub = _StubCiWait([{'status': 'error', 'error': 'Timeout waiting for CI'}])
    clock = _StubClock([0.0, float(fallback)])

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=_StubGitHead(_SHA_A),
        timeout_get_runner=_StubTimeoutGetMissing(),
        timeout_set_runner=timeout_set_stub,
        monotonic_clock=clock,
    )

    assert result['ci_final_status'] == 'timeout'
    assert result['clamp_state'] == 'no-ceiling-fallback'
    assert timeout_set_stub.recorded == [fallback]
