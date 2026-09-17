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

def test_ci_failure_returns_wait_failed_without_caching(plan_context):
    plan_id = 'ci-precond-ci-failure'
    git_stub = _StubGitHead(_SHA_A)
    wait_stub = _StubCiWait([{'status': 'success', 'final_status': 'failure'}])

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=git_stub,
    )

    assert result['status'] == 'wait_failed'
    assert result['head_sha'] == _SHA_A
    assert result['ci_final_status'] == 'failure'
    # Critically: NO cache entry written on failure.
    cache_path = _cache_path(plan_id)
    assert not cache_path.exists(), 'Failure outcomes must not be cached; re-entry must re-poll'


def test_provider_duration_preferred_over_measured_elapsed(plan_context):
    """When the timeout envelope surfaces the provider's true check-run
    duration (duration_sec), it is preferred over the measured elapsed
    lower-bound — collapsing the geometric ratchet to a single step.
    """
    plan_id = 'ci-precond-provider-duration'
    git_stub = _StubGitHead(_SHA_A)
    timeout_set_stub = _StubTimeoutSet()
    wait_stub = _StubCiWait(
        [
            {
                'status': 'error',
                'wait_outcome': 'deadline_exceeded',
                'duration_sec': 800,
            }
        ]
    )
    # Measured elapsed would be 605, but the provider's 800 must win.
    clock = _StubClock([0.0, 605.0])

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

    assert timeout_set_stub.recorded == [800], 'Provider duration_sec must be preferred over the measured elapsed'


def test_default_timeout_matches_documented_ceiling():
    # The deliverable's design notes specify a 600s (10-minute) ceiling
    # matching the documented ci-wait budget. A change here would silently
    # tighten the precondition's tolerance, so we pin it.
    assert DEFAULT_CI_WAIT_TIMEOUT_SECONDS == 600


def test_failure_forwards_failing_checks_list(plan_context):
    """A ``ci wait`` envelope with ``failing_checks`` MUST forward the list
    verbatim through the resolver return so the dispatcher can name the
    failing checks in the consumer step's display_detail and emit the
    documented structured triage finding.
    """
    plan_id = 'ci-precond-failing-checks'
    git_stub = _StubGitHead(_SHA_A)
    wait_stub = _StubCiWait(
        [
            {
                'status': 'success',
                'final_status': 'failure',
                'failing_checks': [
                    {'name': 'lint', 'conclusion': 'FAILURE'},
                    {'name': 'dep-review', 'conclusion': 'CANCELLED'},
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
    )

    assert result['status'] == 'wait_failed'
    assert result['ci_final_status'] == 'failure'
    assert result['failing_checks'] == [
        {'name': 'lint', 'conclusion': 'FAILURE'},
        {'name': 'dep-review', 'conclusion': 'CANCELLED'},
    ]
    assert result['wait_outcome'] == 'completed'


def test_satisfied_does_not_carry_failing_checks_field(plan_context):
    """``satisfied`` (cache hit) MUST NOT include the failing_checks /
    wait_outcome fields — they are wait_failed-only signals. The contract is
    "satisfied and wait_succeeded outcomes produce no finding"; the absence of
    the fields is the structural complement.
    """
    plan_id = 'ci-precond-satisfied-no-failing-checks'
    git_stub = _StubGitHead(_SHA_A)
    # First call: populate the cache via wait_succeeded.
    wait_stub = _StubCiWait([{'status': 'success', 'final_status': 'success'}])
    resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=git_stub,
    )
    # Second call: cache hit → satisfied.
    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=git_stub,
    )

    assert result['status'] == 'satisfied'
    # The "no triage finding on satisfied" guarantee is structurally
    # enforced by the absence of the failing_checks field — the SKILL.md
    # dispatcher only emits findings when wait_failed is observed.
    assert 'failing_checks' not in result
    assert 'wait_outcome' not in result


def test_run_ci_wait_success_envelope_yields_wait_succeeded(plan_context, monkeypatch):
    """End-to-end through ``resolve``: when the executor (subprocess.run)
    returns a success envelope, ``resolve`` MUST report ``wait_succeeded``.
    This pins the corrected vector all the way to the public return value
    without injecting the ``ci_wait_runner`` seam.
    """
    capturing = _CapturingSubprocessRun(stdout='status: success\nfinal_status: success\n')
    monkeypatch.setattr(_resolver_mod.subprocess, 'run', capturing)

    plan_id = 'ci-precond-vector-end-to-end'
    result = resolve(
        plan_id=plan_id,
        worktree_path=str(PROJECT_ROOT),
        pr_number=_PR,
        git_head_resolver=_StubGitHead(_SHA_A),
    )

    assert result['status'] == 'wait_succeeded'
    assert result['ci_final_status'] == 'success'
    # The real _run_ci_wait ran and constructed the corrected vector.
    assert capturing.captured_cmd is not None
    checks_idx = capturing.captured_cmd.index('checks')
    assert capturing.captured_cmd[checks_idx + 1] == 'wait'


def test_resolve_reads_timeout_from_run_config_entry(plan_context):
    """(a) When run-configuration.json carries a ci:wait entry, resolve()
    MUST forward that persisted value as the ci wait --timeout ceiling
    rather than the hard-coded DEFAULT_CI_WAIT_TIMEOUT_SECONDS.
    """
    plan_id = 'ci-precond-runconfig-seeded'
    get_stub = _StubTimeoutGetSeeded(seeded_value=420)
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
    # The run-config lookup fired with the documented fallback default.
    assert get_stub.calls == [DEFAULT_CI_WAIT_TIMEOUT_SECONDS]
    # The seeded value (not the default) reached the ci wait runner.
    assert len(wait_stub.calls) == 1
    # _StubCiWait records (plan_id, pr_number, timeout_seconds, worktree).
    assert wait_stub.calls[0][2] == 420


def test_resolve_explicit_timeout_overrides_run_config_lookup(plan_context):
    """An explicit ``timeout_seconds`` argument bypasses the run-config
    lookup entirely — the get helper MUST NOT be consulted.
    """
    plan_id = 'ci-precond-runconfig-explicit'
    get_stub = _StubTimeoutGetSeeded(seeded_value=420)
    set_stub = _StubTimeoutSet()
    wait_stub = _StubCiWait([{'status': 'success', 'final_status': 'success'}])

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        timeout_seconds=55,
        ci_wait_runner=wait_stub,
        git_head_resolver=_StubGitHead(_SHA_A),
        timeout_get_runner=get_stub,
        timeout_set_runner=set_stub,
    )

    assert result['status'] == 'wait_succeeded'
    # The run-config get helper was never consulted.
    assert get_stub.calls == []
    # The explicit value reached the ci wait runner.
    assert wait_stub.calls[0][2] == 55


def test_strict_mode_default_does_not_echo_consume_failures(plan_context):
    """Sanity guard: a default (strict) resolution MUST NOT echo
    ``mode: consume-failures`` — the mode echo is a load-bearing signal
    and accidentally setting it under strict would mis-route consumers
    into the consume-failures branch.
    """
    plan_id = 'ci-precond-strict-mode-default'
    git_stub = _StubGitHead(_SHA_A)
    wait_stub = _StubCiWait(
        [
            {
                'status': 'success',
                'final_status': 'failure',
                'failing_checks': [{'name': 'lint'}],
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
        # No mode argument — defaults to strict.
    )

    assert result['status'] == 'wait_failed'
    # The mode echo is present on wait_failed but carries strict.
    assert result.get('mode') == 'strict'


def test_fixture_green_success_resolves_to_success(plan_context):
    """An all-green fixture classifies as ``wait_succeeded`` /
    ``ci_final_status: success``.

    This is the headline mis-classification risk: a green CI run read as a
    failure blocks finalize on every passing PR, so the precondition resolver
    reports ``ci_failure`` for a tree that is in fact ready to merge. A failure
    here means the parse-and-extract pipeline is broken end to end, not that one
    field drifted.
    """
    fixture = _FIXTURE_DIR / 'green-success.toon'
    plan_id = 'ci-fixture-green-success'
    result = _run_fixture_through_resolver(fixture, plan_id)
    assert result['status'] == 'wait_succeeded', (
        f'green-success.toon expected wait_succeeded, got '
        f'{result["status"]} (ci_final_status='
        f'{result.get("ci_final_status")!r}). A green run read as a failure '
        f'blocks finalize on every passing PR.'
    )
    assert result['ci_final_status'] == 'success'


def test_fixture_skipped_checks_resolves_to_success(plan_context):
    """Mix of pass + skipping rows — variant of green-success."""
    fixture = _FIXTURE_DIR / 'skipped-checks.toon'
    plan_id = 'ci-fixture-skipped-checks'
    result = _run_fixture_through_resolver(fixture, plan_id)
    assert result['status'] == 'wait_succeeded'
    assert result['ci_final_status'] == 'success'


def test_fixture_pending_then_cancelled_resolves_to_failure(plan_context):
    """All checks cancelled (non-failure terminal) — classifies as failure
    per the resolver contract (only success/none distinguish)."""
    fixture = _FIXTURE_DIR / 'pending-then-cancelled.toon'
    plan_id = 'ci-fixture-pending-then-cancelled'
    result = _run_fixture_through_resolver(fixture, plan_id)
    assert result['status'] == 'wait_failed'
    assert result['ci_final_status'] == 'failure'


def test_fixture_url_with_commas_and_quotes_resolves_to_success(plan_context):
    """Stressor (a): commas and quotes inside URL columns of a tab-separated
    row must not break parsing — the tab-mode splitter ignores commas."""
    fixture = _FIXTURE_DIR / 'url-with-commas-and-quotes.toon'
    plan_id = 'ci-fixture-url-commas-quotes'
    result = _run_fixture_through_resolver(fixture, plan_id)
    assert result['status'] == 'wait_succeeded'
    assert result['ci_final_status'] == 'success'


def test_fixture_multi_line_error_summary_resolves_to_timeout(plan_context):
    """Stressor (c): multi-line `|` content in a top-level envelope field
    must parse without breaking the trailing `checks[N]:` table or the
    top-level `status: error` classification."""
    fixture = _FIXTURE_DIR / 'multi-line-error-summary.toon'
    plan_id = 'ci-fixture-multi-line-error'
    result = _run_fixture_through_resolver(fixture, plan_id)
    assert result['status'] == 'wait_failed'
    assert result['ci_final_status'] == 'timeout'
    assert result.get('wait_outcome') == 'deadline_exceeded'
    # The failing_checks list captures the still-pending checks at deadline.
    assert len(result.get('failing_checks') or []) == 2


def test_fixture_mixed_skipped_cancelled_neutral_resolves_to_failure(plan_context):
    """Stressor (f): a mix of pass + SKIPPED + CANCELLED + NEUTRAL + FAIL
    conclusions where `final_status: failure` MUST classify as wait_failed
    and forward the failing_checks list verbatim."""
    fixture = _FIXTURE_DIR / 'mixed-skipped-cancelled-neutral.toon'
    plan_id = 'ci-fixture-mixed-conclusions'
    result = _run_fixture_through_resolver(fixture, plan_id)
    assert result['status'] == 'wait_failed'
    assert result['ci_final_status'] == 'failure'
    failing_names = [c['name'] for c in result.get('failing_checks') or []]
    assert set(failing_names) == {'test', 'lint', 'security-scan'}, (
        f'Failing-check enumeration drifted: {failing_names!r}'
    )


def test_parse_toon_inline_table_handles_colon_in_first_column_csv():
    """`parse_toon` MUST treat a comma-separated row whose first column
    contains BOTH a hyphen AND a colon (e.g. plan-retrospective
    `failures[N]{notation,exit_code}` rows like
    ``plan-marshall:foo:bar,1``) as data, NOT as a key/value pair.

    The post-`\\t-guard` regression: extending the identifier character
    class to ``[\\w_-]*`` so hyphenated TOON keys still terminate arrays
    inadvertently made the heuristic match ``plan-marshall:`` at the
    start of a CSV row. The lookahead ``(?=\\s|$)`` after the colon
    re-tightens the heuristic — a real TOON key/value pair always has
    whitespace (or EOL) after the colon, CSV first-column-with-colon
    never does.
    """
    toon = 'failures[1]{notation,exit_code}:\n  plan-marshall:foo:bar,1\nsentinel: present\n'
    parsed = _parse_toon(toon)
    failures = parsed.get('failures') or []
    assert len(failures) == 1, (
        f'Parser truncated colon-bearing comma-separated row: got '
        f'{len(failures)}/1 rows. The `[\\w_-]*` identifier widening '
        'matched `plan-marshall:` at the start of the row and broke out '
        'of the array — the `(?=\\s|$)` lookahead must re-tighten the '
        'heuristic.'
    )
    assert failures[0]['notation'] == 'plan-marshall:foo:bar'
    assert int(failures[0]['exit_code']) == 1
    assert parsed.get('sentinel') == 'present', (
        'The fix must not interfere with array-exit on genuine top-level key/value pairs that follow the array.'
    )


def test_signal_arm_sonar_red_ci_proceeds_as_failed(plan_context):
    """(a) CI red only via the Sonar check → the sonar arm is terminal-but-red
    → ``arm_proceed`` with ``arm_state=failed`` so ``sonar-roundtrip`` FINDs
    its new-code issues rather than skipping the very signal it consumes.
    """
    plan_id = 'ci-precond-signal-sonar-red'
    wait_stub = _StubCiWait([_sonar_red_ci_envelope()])

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=_StubGitHead(_SHA_A),
        signal_arm='sonar',
    )

    assert result['status'] == 'arm_proceed', (
        'a failed sonar arm must PROCEED to FIND, not skip — a red gate is '
        'exactly when its findings exist (the TokenSheriff-572 fix)'
    )
    assert result['signal_arm'] == 'sonar'
    assert result['arm_state'] == 'failed'
    assert result['ci_final_status'] == 'failure'
    assert result['head_sha'] == _SHA_A
    # A red terminal is not cached — re-entry re-polls.
    assert not _cache_path(plan_id).exists()


def test_signal_arm_green_sonar_settles(plan_context):
    """CI green → the sonar arm settles cleanly → ``arm_proceed``."""
    plan_id = 'ci-precond-signal-green-sonar'
    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=_StubCiWait([{'status': 'success', 'final_status': 'success'}]),
        git_head_resolver=_StubGitHead(_SHA_A),
        signal_arm='sonar',
    )
    assert result['status'] == 'arm_proceed'
    assert result['arm_state'] == 'settled'
    assert result['ci_final_status'] == 'success'


def test_signal_arm_pending_review_waits(plan_context):
    """(b) A pending arm waits for the review arm too — the per-signal wait
    semantics are symmetric across producer arms.
    """
    plan_id = 'ci-precond-signal-pending-review'
    wait_stub = _StubCiWait([{'status': 'timeout', 'wait_outcome': 'deadline_exceeded'}])

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        timeout_seconds=600,
        ci_wait_runner=wait_stub,
        git_head_resolver=_StubGitHead(_SHA_A),
        timeout_set_runner=_StubTimeoutSet(),
        monotonic_clock=_StubClock([0.0, 601.0]),
        signal_arm='review',
    )

    assert result['status'] == 'arm_pending'
    assert result['arm_state'] == 'pending'
    assert result['ci_final_status'] == 'timeout'


def test_signal_arm_ci_value_falls_back_to_legacy(plan_context):
    """``--signal-arm ci`` (like an absent value) resolves the legacy global
    ci-complete path unchanged — the return carries the legacy
    ``wait_succeeded`` shape, NOT the ``arm_proceed`` shape.
    """
    plan_id = 'ci-precond-signal-ci-legacy'
    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=_StubCiWait([{'status': 'success', 'final_status': 'success'}]),
        git_head_resolver=_StubGitHead(_SHA_A),
        signal_arm='ci',
    )
    assert result['status'] == 'wait_succeeded'
    assert 'signal_arm' not in result
    assert 'arm_state' not in result


def test_learned_ceiling_above_the_harness_bound_is_clamped(plan_context):
    """A persisted ``ci:wait`` value that has ratcheted far above the harness
    ceiling MUST be clamped before it reaches the wait subprocess.
    """
    plan_id = 'ci-precond-clamp-learned'
    # The ratchet has grown the persisted ceiling well past the harness bound.
    get_stub = _StubTimeoutGetSeeded(seeded_value=5000)
    wait_stub = _StubCiWait([{'status': 'success', 'final_status': 'success'}])

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=_StubGitHead(_SHA_A),
        timeout_get_runner=get_stub,
        timeout_set_runner=_StubTimeoutSet(),
    )

    assert result['status'] == 'wait_succeeded'
    consumed = wait_stub.calls[0][2]
    assert consumed == _MAX_INNER_WAIT_SECONDS, (
        f'A learned ceiling of 5000s must be clamped to '
        f'{_MAX_INNER_WAIT_SECONDS}s, got {consumed}s — an unclamped value '
        'lets the harness kill the call before the resolver can return'
    )
    assert consumed + CI_WAIT_OUTER_BUFFER_SECONDS < HARNESS_BASH_CEILING_SECONDS


def test_zero_and_negative_ceilings_are_raised_to_the_positive_lower_bound(
    plan_context,
):
    """The clamp bounds from BELOW as well as above.

    ``subprocess.run`` raises an uncaught ``ValueError`` on a zero or negative
    ``timeout``, and ``_run_ci_wait`` catches only ``TimeoutExpired`` — so an
    explicit ``--timeout 0`` or a corrupt negative persisted ``ci:wait`` value
    must resolve to a safe positive minimum rather than propagate.
    """
    for requested in (0, -1, -5000):
        assert _resolver_mod._clamp_wait_ceiling(requested) == 1, (
            f'A requested ceiling of {requested}s must clamp up to 1s — '
            'a non-positive subprocess timeout raises an uncaught ValueError'
        )

    plan_id = 'ci-precond-clamp-lower-bound'
    wait_stub = _StubCiWait([{'status': 'success', 'final_status': 'success'}])

    resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        timeout_seconds=0,
        ci_wait_runner=wait_stub,
        git_head_resolver=_StubGitHead(_SHA_A),
        timeout_set_runner=_StubTimeoutSet(),
    )

    assert wait_stub.calls[0][2] == 1, 'The consumed ceiling reaching the wait seam must be positive'


def test_clamped_deadline_still_returns_structured_arm_pending(plan_context):
    """The per-signal arms inherit the clamp because they delegate to
    ``resolve`` — a clamped deadline still yields the structured
    ``arm_pending`` envelope rather than an opaque harness kill.
    """
    plan_id = 'ci-precond-clamp-structured-arm-pending'
    wait_stub = _StubCiWait([{'status': 'timeout', 'wait_outcome': 'deadline_exceeded'}])

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=_StubGitHead(_SHA_A),
        timeout_get_runner=_StubTimeoutGetSeeded(seeded_value=5000),
        timeout_set_runner=_StubTimeoutSet(),
        monotonic_clock=_StubClock([0.0, float(_MAX_INNER_WAIT_SECONDS + 1)]),
        signal_arm='review',
    )

    assert wait_stub.calls[0][2] == _MAX_INNER_WAIT_SECONDS
    assert result['status'] == 'arm_pending'
    assert result['arm_state'] == 'pending'
    assert result['ci_final_status'] == 'timeout'
    assert result['wait_outcome'] == 'deadline_exceeded'


def test_ratchet_records_measured_elapsed_when_request_fits_under_the_clamp(
    plan_context,
):
    """The upward ratchet is NOT starved for a requested ceiling that fits
    under the clamp: a wait that consumed the full requested window still
    feeds the measured elapsed into ``timeout_set``.
    """
    plan_id = 'ci-precond-ratchet-elapsed-under-clamp'
    set_stub = _StubTimeoutSet()
    wait_stub = _StubCiWait([{'status': 'timeout', 'wait_outcome': 'deadline_exceeded'}])
    requested = 300
    elapsed = requested + 5

    resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=_StubGitHead(_SHA_A),
        timeout_get_runner=_StubTimeoutGetSeeded(seeded_value=requested),
        timeout_set_runner=set_stub,
        monotonic_clock=_StubClock([0.0, float(elapsed)]),
    )

    assert requested < _MAX_INNER_WAIT_SECONDS, 'fixture precondition: the requested ceiling is consumed unclamped'
    assert wait_stub.calls[0][2] == requested
    assert set_stub.recorded == [elapsed], (
        'A wait that consumed the full requested ceiling must still feed the upward ratchet'
    )
