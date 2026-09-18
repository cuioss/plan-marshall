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


def test_head_advance_invalidates_cache(plan_context):
    plan_id = 'ci-precond-head-advance'
    # First call observes SHA_A; second observes SHA_B.
    git_stub = _StubGitHead(_SHA_A)
    wait_stub = _StubCiWait(
        [
            {'status': 'success', 'final_status': 'success'},
            {'status': 'success', 'final_status': 'success'},
        ]
    )

    first = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=git_stub,
    )
    assert first['status'] == 'wait_succeeded'
    assert first['head_sha'] == _SHA_A
    assert len(wait_stub.calls) == 1

    # Advance HEAD.
    git_stub.sha = _SHA_B

    second = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=git_stub,
    )
    # Cache is stale → resolver re-polls and reports wait_succeeded again.
    assert second['status'] == 'wait_succeeded'
    assert second['head_sha'] == _SHA_B
    assert len(wait_stub.calls) == 2, 'HEAD advance must force a fresh ci wait poll'
    # Cache now reflects the new SHA.
    cache_after = _read_cache(plan_id)
    assert cache_after is not None
    assert cache_after['head_sha'] == _SHA_B


def test_deadline_exceeded_records_measured_elapsed_via_timeout_set(plan_context):
    """A synthetic deadline envelope WITHOUT duration_sec records the
    measured elapsed-at-deadline (>= the ceiling) via the timeout_set seam.

    Requested ceiling and injected elapsed stay strictly below
    ``_MAX_INNER_WAIT_SECONDS`` so no clamping intervenes: the reported
    elapsed is a genuinely reachable measurement, not a value the harness
    ceiling could never produce.
    """
    plan_id = 'ci-precond-elapsed-record'
    git_stub = _StubGitHead(_SHA_A)
    timeout_set_stub = _StubTimeoutSet()
    # No duration_sec — the elapsed fallback drives the record.
    wait_stub = _StubCiWait([{'status': 'timeout', 'wait_outcome': 'deadline_exceeded'}])
    # clock ticks [0, 301] → measured elapsed 301s, >= the 300s ceiling.
    clock = _StubClock([0.0, 301.0])

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        timeout_seconds=300,
        ci_wait_runner=wait_stub,
        git_head_resolver=git_stub,
        timeout_set_runner=timeout_set_stub,
        monotonic_clock=clock,
    )

    assert result['status'] == 'wait_failed'
    assert result['ci_final_status'] == 'timeout'
    assert timeout_set_stub.recorded == [301], (
        'The measured elapsed-at-deadline must be recorded so the ci:wait ceiling ratchets upward'
    )


def test_repeated_deadline_exceeded_ratchets_upward(plan_context):
    """Across finalizes, each deadline_exceeded records its elapsed-at-deadline;
    as the run-config mechanism grows the ceiling between calls, the recorded
    observations grow with it — proving resolve feeds the upward ratchet.

    Both rounds stay strictly below ``_MAX_INNER_WAIT_SECONDS`` so the
    elapsed values are genuinely reachable (see the test above).
    """
    git_stub = _StubGitHead(_SHA_A)
    timeout_set_stub = _StubTimeoutSet()

    # Finalize 1: ceiling 300, elapsed 301 → records 301.
    resolve(
        plan_id='ci-precond-ratchet',
        worktree_path=_WORKTREE,
        pr_number=_PR,
        timeout_seconds=300,
        ci_wait_runner=_StubCiWait([{'status': 'timeout', 'wait_outcome': 'deadline_exceeded'}]),
        git_head_resolver=git_stub,
        timeout_set_runner=timeout_set_stub,
        monotonic_clock=_StubClock([0.0, 301.0]),
    )

    # Finalize 2: the ceiling has grown to 400 (the run-config ratchet);
    # a fresh deadline at elapsed 401 → records 401.
    resolve(
        plan_id='ci-precond-ratchet',
        worktree_path=_WORKTREE,
        pr_number=_PR,
        timeout_seconds=400,
        ci_wait_runner=_StubCiWait([{'status': 'timeout', 'wait_outcome': 'deadline_exceeded'}]),
        git_head_resolver=git_stub,
        timeout_set_runner=timeout_set_stub,
        monotonic_clock=_StubClock([0.0, 401.0]),
    )

    assert timeout_set_stub.recorded == [301, 401]
    assert timeout_set_stub.recorded[1] > timeout_set_stub.recorded[0], (
        'The recorded elapsed observations must grow as the ceiling ratchets up'
    )


def test_source_script_has_no_self_bootstrap():
    """Pin the absence of the legacy ``sys.path`` self-bootstrap block.

    The pre-rename helper computed the script-shared directory via
    parent-arithmetic on ``__file__`` and called ``sys.path.insert(...)``
    inside the script body. That pattern broke when the script was
    relocated under ``target/claude/`` or the plugin cache because the
    parent count was hard-coded for the source tree layout. The
    executor-injected PYTHONPATH replaces this scheme.

    If a future change re-introduces a path-arithmetic ``sys.path``
    mutation in this script, the executor invocation may still succeed
    (the executor PYTHONPATH would mask the issue) but the regression
    would silently land. This text-level check catches it directly.
    """
    body = _SOURCE_SCRIPT_PATH.read_text(encoding='utf-8')

    # The legacy patterns we are guarding against.
    forbidden_markers = (
        # The exact identifiers the old self-bootstrap block defined.
        '_SCRIPTS_DIR',
        '_SCRIPT_SHARED',
        '_REF_TOON',
        # Any sys.path mutation inside the source script body. The
        # executor's PYTHONPATH injection is the only allowed mechanism.
        'sys.path.insert',
        'sys.path.append',
    )
    for marker in forbidden_markers:
        assert marker not in body, (
            f'Legacy self-bootstrap marker {marker!r} reappeared in '
            f'{_SOURCE_SCRIPT_PATH}. The renamed helper MUST rely on the '
            'executor proxy to inject PYTHONPATH; in-script sys.path '
            'mutation breaks when the script is relocated under '
            'target/claude/ or the plugin cache.'
        )


def test_timeout_forwards_wait_outcome_deadline_exceeded(plan_context):
    """A wait-deadline exhaustion MUST forward
    ``wait_outcome: deadline_exceeded`` and the still-running checks so the
    dispatcher routes to the ``ci-verify-timeout`` producer.
    """
    plan_id = 'ci-precond-timeout-forward'
    git_stub = _StubGitHead(_SHA_A)
    wait_stub = _StubCiWait(
        [
            {
                'status': 'error',
                'operation': 'ci_wait',
                'error': 'Timeout waiting for CI',
                'pr_number': _PR,
                'duration_sec': 600,
                'last_status': 'pending',
                'wait_outcome': 'deadline_exceeded',
                'failing_checks': [
                    {'name': 'slow-deploy', 'conclusion': 'PENDING'},
                ],
            }
        ]
    )

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=git_stub,
        timeout_set_runner=_StubTimeoutSet(),
    )

    assert result['status'] == 'wait_failed'
    assert result['ci_final_status'] == 'timeout'
    assert result['wait_outcome'] == 'deadline_exceeded'
    assert [c['name'] for c in result['failing_checks']] == ['slow-deploy']


def test_run_ci_wait_uses_checks_wait_subcommand_vector(monkeypatch):
    """``_run_ci_wait`` MUST construct the executor command with the
    ``checks wait`` subcommand vector — never the non-existent ``ci wait``.
    """
    capturing = _CapturingSubprocessRun(stdout='status: success\nfinal_status: success\n')
    monkeypatch.setattr(_resolver_mod.subprocess, 'run', capturing)

    result = _resolver_mod._run_ci_wait(
        plan_id='ci-precond-vector-check',
        pr_number=_PR,
        timeout_seconds=DEFAULT_CI_WAIT_TIMEOUT_SECONDS,
        worktree_path=str(PROJECT_ROOT),
    )

    assert capturing.captured_cmd is not None
    cmd = capturing.captured_cmd
    # The corrected vector: 'checks' immediately followed by 'wait'.
    assert 'checks' in cmd, f'cmd missing "checks" segment: {cmd!r}'
    checks_idx = cmd.index('checks')
    assert cmd[checks_idx + 1] == 'wait', f'"checks" must be immediately followed by "wait": {cmd!r}'
    # The legacy non-existent vector MUST NOT be present: there must be no
    # 'ci' element immediately followed by 'wait'.
    for i, token in enumerate(cmd[:-1]):
        assert not (token == 'ci' and cmd[i + 1] == 'wait'), (
            f'legacy "ci wait" subcommand vector reappeared in {cmd!r} — the ci.py executor has no "ci" subcommand'
        )
    # The wait primitive's --pr-number / --timeout flags are unchanged.
    assert '--pr-number' in cmd
    assert '--timeout' in cmd
    # The envelope parsed cleanly into the success outcome.
    assert result.get('final_status') == 'success'


def test_resolve_routes_subprocess_timeout_to_wait_failed_timeout(plan_context, monkeypatch):
    """End-to-end: a ``subprocess.TimeoutExpired`` from the real
    ``_run_ci_wait`` (driven through ``resolve`` without the ci_wait_runner
    seam) MUST resolve to ``wait_failed`` / ``ci_final_status: timeout`` and
    write no cache entry — the same terminal shape as an inner ci-wait
    deadline. This pins that the new except-branch envelope threads cleanly
    through resolve()'s non-success classification.
    """
    monkeypatch.setattr(_resolver_mod.subprocess, 'run', _raise_timeout_expired)

    plan_id = 'ci-precond-subprocess-timeout-end-to-end'
    result = resolve(
        plan_id=plan_id,
        worktree_path=str(PROJECT_ROOT),
        pr_number=_PR,
        git_head_resolver=_StubGitHead(_SHA_A),
    )

    assert result['status'] == 'wait_failed'
    assert result['head_sha'] == _SHA_A
    assert result['ci_final_status'] == 'timeout'
    assert result['wait_outcome'] == 'deadline_exceeded'
    # Timeout outcomes are never cached — re-entry must re-poll.
    assert not _cache_path(plan_id).exists(), 'A subprocess-timeout outcome must not be cached'


def test_resolve_records_observed_duration_after_successful_wait(plan_context):
    """(c) After a successful ci wait, resolve() MUST write the observed
    ``duration_sec`` back via the run-config timeout-set helper so the
    ci:wait ceiling adapts to real run lengths.
    """
    plan_id = 'ci-precond-runconfig-writeback'
    get_stub = _StubTimeoutGetMissing()
    set_stub = _StubTimeoutSet()
    wait_stub = _StubCiWait(
        [
            {
                'status': 'success',
                'final_status': 'success',
                'duration_sec': 137,
            }
        ]
    )

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
    # The observed duration was written back exactly once.
    assert set_stub.durations == [137]


def test_consume_failures_mode_preserves_timeout_envelope(plan_context):
    """A timeout under consume-failures MUST still surface as wait_failed
    with ci_final_status=timeout — the consume-failures path is for
    *all* wait_failed shapes (failure, timeout, no_checks), not just
    final_status=failure.
    """
    plan_id = 'ci-precond-consume-failures-timeout'
    git_stub = _StubGitHead(_SHA_A)
    wait_stub = _StubCiWait(
        [
            {
                'status': 'error',
                'operation': 'ci_wait',
                'error': 'Timeout waiting for CI',
                'wait_outcome': 'deadline_exceeded',
                'failing_checks': [
                    {'name': 'slow-deploy', 'conclusion': 'PENDING'},
                ],
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

    assert result['status'] == 'wait_failed'
    assert result['ci_final_status'] == 'timeout'
    assert result['mode'] == 'consume-failures'
    assert result['wait_outcome'] == 'deadline_exceeded'
    assert [c['name'] for c in result['failing_checks']] == ['slow-deploy']


def test_fixture_dir_present():
    """Every catalogued fixture — the base captures plus the six stressor
    categories (a-f) — is present on disk.

    The roster is DERIVED from the ``## Fixture catalogue`` section of the
    fixtures README (the authoritative catalogue), never transcribed: a
    fixture added on disk but not documented, or documented but missing,
    fails here rather than silently narrowing what the fixture-driven tests
    below cover. The derivation asserts non-empty so an unparseable README
    cannot pass vacuously.
    """
    assert _FIXTURE_DIR.is_dir(), f'Fixture directory missing: {_FIXTURE_DIR}'
    catalogue_text = (_FIXTURE_DIR / 'README.md').read_text(encoding='utf-8')
    section = catalogue_text.split('## Fixture catalogue', 1)[1].split('\n## ', 1)[0]
    expected = set(re.findall(r'`([\w][\w.\-]*\.toon)`', section))
    assert expected, 'README fixture catalogue yielded no fixture names — the derivation is vacuous'
    found = {f.name for f in _FIXTURE_DIR.iterdir() if f.is_file() and f.suffix == '.toon'}
    assert expected == found, f'Fixture directory out of sync. Missing: {expected - found}, Extra: {found - expected}'


def test_fixture_many_checks_success_resolves_to_success(plan_context):
    """Larger checks table — exercises the parser at realistic counts."""
    fixture = _FIXTURE_DIR / 'many-checks-success.toon'
    plan_id = 'ci-fixture-many-checks-success'
    result = _run_fixture_through_resolver(fixture, plan_id)
    assert result['status'] == 'wait_succeeded'
    assert result['ci_final_status'] == 'success'


def test_fixture_mixed_success_failure_resolves_to_failure(plan_context):
    """Multiple failing checks alongside passing — multi-row failing list."""
    fixture = _FIXTURE_DIR / 'mixed-success-failure.toon'
    plan_id = 'ci-fixture-mixed-success-failure'
    result = _run_fixture_through_resolver(fixture, plan_id)
    assert result['status'] == 'wait_failed'
    assert result['ci_final_status'] == 'failure'
    assert len(result.get('failing_checks') or []) == 2


def test_fixture_timeout_deadline_exceeded_resolves_to_timeout(plan_context):
    """True timeout (deadline_exceeded) — distinct from the false-timeout
    mis-classification the lesson identifies."""
    fixture = _FIXTURE_DIR / 'timeout-deadline-exceeded.toon'
    plan_id = 'ci-fixture-timeout-deadline-exceeded'
    result = _run_fixture_through_resolver(fixture, plan_id)
    assert result['status'] == 'wait_failed'
    assert result['ci_final_status'] == 'timeout'
    assert result.get('wait_outcome') == 'deadline_exceeded'


def test_fixture_check_name_special_chars_resolves_to_success(plan_context):
    """End-to-end: the special-chars fixture still resolves to wait_succeeded."""
    fixture = _FIXTURE_DIR / 'check-name-special-chars.toon'
    plan_id = 'ci-fixture-check-name-special-chars'
    result = _run_fixture_through_resolver(fixture, plan_id)
    assert result['status'] == 'wait_succeeded'
    assert result['ci_final_status'] == 'success'


def test_fixture_huge_checks_block_resolves_to_success(plan_context):
    """Stressor (e): a >50-row checks block must parse without performance
    cliff and resolve cleanly. The fixture carries exactly 55 rows."""
    fixture = _FIXTURE_DIR / 'huge-checks-block.toon'
    plan_id = 'ci-fixture-huge-checks-block'
    result = _run_fixture_through_resolver(fixture, plan_id)
    assert result['status'] == 'wait_succeeded'
    assert result['ci_final_status'] == 'success'
    # Verify the parser captured every row — pin the structural completeness.
    raw = fixture.read_text()
    parsed = _parse_toon(raw)
    assert len(parsed['checks']) == 55, f'Expected all 55 rows, got {len(parsed["checks"])}'


def test_parse_toon_inline_table_handles_colon_in_first_column():
    """`parse_toon` MUST treat a tab-separated row whose first column
    contains a colon (e.g. CI check names like `lint:strict`) as a data
    row, NOT as a key/value pair.

    The pre-fix heuristic at `_parse_uniform_array`:

        if re.match(r'^[a-zA-Z_][\\w_]*\\s*:', content) and not ...:
            break

    matched `lint:strict\\tcompleted\\t...` after `.strip()` (the `\\s*`
    matched zero whitespace before the colon) and broke out of the
    array. The fix added `'\\t' not in content` to the heuristic.
    """
    toon = (
        'rows[3]{name,status,result}:\n'
        '\tlint:strict\tcompleted\tpass\n'
        '\tcoverage:enforce\tcompleted\tfail\n'
        '\tbuild\tcompleted\tpass\n'
        'sentinel: present\n'
    )
    parsed = _parse_toon(toon)
    rows = parsed.get('rows') or []
    assert len(rows) == 3, (
        f'Parser truncated colon-bearing tab-separated rows: got '
        f'{len(rows)}/3 rows. The `_parse_uniform_array` key/value heuristic '
        'must not treat a tab-separated row as a new key/value pair.'
    )
    assert [r['name'] for r in rows] == [
        'lint:strict',
        'coverage:enforce',
        'build',
    ]
    # The post-table sentinel key/value MUST still be picked up — the
    # array-exit condition must work for genuine top-level keys.
    assert parsed.get('sentinel') == 'present', (
        'The fix must not interfere with array-exit on genuine top-level key/value pairs that follow the array.'
    )


def test_run_config_timeout_get_degrades_when_executor_unresolvable(monkeypatch):
    """When get_executor_path raises (no resolvable plan root), the helper
    degrades to the default without spawning a subprocess."""
    run_called = {'hit': False}

    def _should_not_run(*args, **kwargs):
        run_called['hit'] = True
        raise AssertionError('subprocess.run must not be called when unresolvable')

    def _raise_resolver():
        raise RuntimeError('no .plan/local ancestor of cwd')

    monkeypatch.setattr(_resolver_mod, 'get_executor_path', _raise_resolver)
    monkeypatch.setattr(_resolver_mod.subprocess, 'run', _should_not_run)

    result = _resolver_mod._run_run_config_timeout_get(600)

    assert result == 600
    assert run_called['hit'] is False


def test_signal_arm_tokensheriff_572_both_producers_proceed(plan_context):
    """TokenSheriff-572 reproduction: a Sonar-only red CI must NOT skip either
    FIND. Under the retired global-CI gate both ``automatic-review`` and
    ``sonar-roundtrip`` blackout-skipped; the per-signal gate proceeds on
    both, so the deadlock is resolved.
    """
    sonar = resolve(
        plan_id='ci-precond-ts572-sonar',
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=_StubCiWait([_sonar_red_ci_envelope()]),
        git_head_resolver=_StubGitHead(_SHA_A),
        signal_arm='sonar',
    )
    review = resolve(
        plan_id='ci-precond-ts572-review',
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=_StubCiWait([_sonar_red_ci_envelope()]),
        git_head_resolver=_StubGitHead(_SHA_A),
        signal_arm='review',
    )

    assert sonar['status'] == 'arm_proceed'
    assert review['status'] == 'arm_proceed'


def test_signal_arm_pending_sonar_waits(plan_context):
    """(b) CI not yet terminal (timeout) → the sonar arm is ``pending`` →
    ``arm_pending`` so the dispatcher waits and re-polls on re-entry.
    """
    plan_id = 'ci-precond-signal-pending-sonar'
    wait_stub = _StubCiWait(
        [
            {
                'status': 'error',
                'operation': 'ci_wait',
                'error': 'Timeout waiting for CI',
                'wait_outcome': 'deadline_exceeded',
                'duration_sec': 600,
                'failing_checks': [{'name': 'build', 'conclusion': 'PENDING'}],
            }
        ]
    )

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=_StubGitHead(_SHA_A),
        timeout_set_runner=_StubTimeoutSet(),
        signal_arm='sonar',
    )

    assert result['status'] == 'arm_pending'
    assert result['arm_state'] == 'pending'
    assert result['ci_final_status'] == 'timeout'
    assert result['wait_outcome'] == 'deadline_exceeded'
    # A pending arm is never cached — re-entry re-polls.
    assert not _cache_path(plan_id).exists()


def test_signal_arm_cache_hit_settles_without_repolling(plan_context):
    """A cache hit (a prior success at the same HEAD) settles the arm without
    re-polling ``ci wait`` — the per-signal path reuses the shared cache.
    """
    plan_id = 'ci-precond-signal-cache-hit'
    git_stub = _StubGitHead(_SHA_A)
    # First: a legacy success populates the per-HEAD cache.
    resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=_StubCiWait([{'status': 'success', 'final_status': 'success'}]),
        git_head_resolver=git_stub,
    )
    # Second: a per-signal resolution with NO envelopes — must hit the cache.
    empty_wait = _StubCiWait([])
    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=empty_wait,
        git_head_resolver=git_stub,
        signal_arm='sonar',
    )

    assert result['status'] == 'arm_proceed'
    assert result['arm_state'] == 'settled'
    assert len(empty_wait.calls) == 0, 'a cache hit must settle the arm without re-invoking ci wait'


def test_clamp_constants_leave_the_outer_call_under_the_harness_ceiling():
    """The derived maximum inner ceiling plus the outer buffer MUST be
    strictly below the harness Bash ceiling — the invariant every other
    clamp test depends on.
    """
    assert _MAX_INNER_WAIT_SECONDS + CI_WAIT_OUTER_BUFFER_SECONDS < HARNESS_BASH_CEILING_SECONDS, (
        f'{_MAX_INNER_WAIT_SECONDS} + {CI_WAIT_OUTER_BUFFER_SECONDS} must be '
        f'strictly below {HARNESS_BASH_CEILING_SECONDS}'
    )
    # Strictly below, not merely at-or-below: the largest admissible inner
    # ceiling is exactly one second short of the buffer-adjusted ceiling.
    assert _MAX_INNER_WAIT_SECONDS == HARNESS_BASH_CEILING_SECONDS - CI_WAIT_OUTER_BUFFER_SECONDS - 1


def test_below_bound_ceiling_passes_through_the_clamp_unchanged(plan_context):
    """The clamp is a ceiling, not a rewrite: a value that already fits
    reaches the wait subprocess verbatim.
    """
    plan_id = 'ci-precond-clamp-passthrough'
    wait_stub = _StubCiWait([{'status': 'success', 'final_status': 'success'}])

    resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        timeout_seconds=120,
        ci_wait_runner=wait_stub,
        git_head_resolver=_StubGitHead(_SHA_A),
        timeout_set_runner=_StubTimeoutSet(),
    )

    assert wait_stub.calls[0][2] == 120


def test_clamped_deadline_still_returns_structured_wait_failed(plan_context):
    """A CI run genuinely longer than the CLAMPED ceiling must still produce
    the structured ``wait_failed`` / ``deadline_exceeded`` envelope — the
    whole point of clamping is that the resolver gets to return at all.
    """
    plan_id = 'ci-precond-clamp-structured-wait-failed'
    wait_stub = _StubCiWait(
        [
            {
                'status': 'timeout',
                'wait_outcome': 'deadline_exceeded',
                'failing_checks': [{'name': 'build', 'conclusion': 'PENDING'}],
            }
        ]
    )

    result = resolve(
        plan_id=plan_id,
        worktree_path=_WORKTREE,
        pr_number=_PR,
        ci_wait_runner=wait_stub,
        git_head_resolver=_StubGitHead(_SHA_A),
        timeout_get_runner=_StubTimeoutGetSeeded(seeded_value=5000),
        timeout_set_runner=_StubTimeoutSet(),
        monotonic_clock=_StubClock([0.0, float(_MAX_INNER_WAIT_SECONDS + 1)]),
    )

    assert wait_stub.calls[0][2] == _MAX_INNER_WAIT_SECONDS
    assert result['status'] == 'wait_failed'
    assert result['ci_final_status'] == 'timeout'
    assert result['wait_outcome'] == 'deadline_exceeded'
    assert [c['name'] for c in result['failing_checks']] == ['build']
    # A clamped deadline is still a non-cacheable verdict.
    assert not _cache_path(plan_id).exists()


def test_ratchet_never_records_below_the_requested_ceiling(plan_context):
    """The elapsed-at-deadline fallback measures against the REQUESTED
    (pre-clamp) ceiling, never the clamped one.

    When the persisted ``ci:wait`` value sits above the harness clamp, the
    wait can only ever consume the clamped window, so an elapsed-vs-clamped
    comparison would fire on every single deadline-exceeded finalize and feed
    ``compute_weighted_timeout`` an observation strictly BELOW the persisted
    value — the learned value silently self-capping back down to the clamp.
    Comparing against the requested ceiling keeps the guard silent in exactly
    that case, so the persisted value is never dragged downward.
    """
    plan_id = 'ci-precond-ratchet-not-below-request'
    set_stub = _StubTimeoutSet()
    wait_stub = _StubCiWait([{'status': 'timeout', 'wait_outcome': 'deadline_exceeded'}])
    requested = 5000
    elapsed = _MAX_INNER_WAIT_SECONDS + 2

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

    # The wait itself is still clamped — the clamp is not what changed.
    assert wait_stub.calls[0][2] == _MAX_INNER_WAIT_SECONDS
    assert elapsed < requested, 'fixture precondition: the clamp cut the wait short'
    assert not [d for d in set_stub.recorded if d < requested], (
        f'The ratchet recorded {set_stub.recorded} — an observation below the '
        f'requested ceiling of {requested}s drifts the learned value DOWNWARD '
        'on every deadline-exceeded finalize. The elapsed fallback must '
        'compare against the requested ceiling, not the clamped one.'
    )
