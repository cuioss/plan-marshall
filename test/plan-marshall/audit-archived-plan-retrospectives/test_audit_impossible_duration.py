#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The call-class-aware impossible-duration ceiling — a deterministic call over
the flat ceiling is flagged, while a ci-wait call is measured against its own
ratcheted ceiling and degrades to the flat one when no config supplies it.

The ratcheted ceiling is read from TWO homes, and the max of them wins:

* ``commands.{key}.timeout_seconds`` in the MAIN-ANCHORED
  ``.plan/local/run-configuration.json`` — the path ``get_run_config_path()``
  resolves to, and the only one that file ever sits at. The reader previously
  looked at ``.plan/run-configuration.json``, where it never sits, so it always
  degraded to the flat floor; a control below pins that the old path is not read.
* the top-level ``upper_limit_seconds`` of the MACHINE-GLOBAL
  ``build-queue.json`` under the home root — the reap threshold's new home, since
  it is applied to every repository's entries in the one host-wide build queue.

Every test that exercises the ceiling pins ``PLAN_MARSHALL_HOME`` at an empty tmp
directory, INCLUDING the degrade-to-flat test. Without that pin the reader would
resolve the developer's real ``~/.plan-marshall/build-queue.json``, so a machine
that happens to carry a ratcheted threshold would silently raise the ceiling and
the degrade test would assert the floor against a value it never controlled.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from _audit_fixtures import PROBE_LOG_NAME, _write_log, audit

#: A call key the build / ci-wait classifier matches, so it is bounded by the
#: ratcheted ceiling rather than the flat deterministic one.
_CI_WAIT_KEY = 'ci:wait'

#: A build-class notation+subcommand the log lines below use.
_BUILD_CALL = 'plan-marshall:build-pyproject:pyproject_build run --command-args verify'

#: A deterministic per-plan-op call — NOT build/ci-wait class, so it keeps the
#: flat 600 s bound however high the ratcheted ceiling goes.
_DETERMINISTIC_CALL = 'plan-marshall:manage-tasks:manage-tasks read --task-number 3'


@pytest.fixture
def empty_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Pin ``PLAN_MARSHALL_HOME`` at an empty directory and return it.

    The pin is the isolation boundary for every ceiling assertion: the
    machine-global ``build-queue.json`` resolves under this root, so without it a
    test would read whatever threshold the developer's own host has ratcheted to.
    """
    home = tmp_path / 'home'
    home.mkdir()
    monkeypatch.setenv('PLAN_MARSHALL_HOME', str(home))
    return home


def _seed_queue_threshold(home: Path, seconds: object) -> None:
    """Seed the machine-global queue state's top-level reap threshold."""
    (home / 'build-queue.json').write_text(
        json.dumps({'active': [], 'waiting': [], 'run_log': [], 'upper_limit_seconds': seconds}),
        encoding='utf-8',
    )


def _seed_main_anchored_timeout(repo_root: Path, key: str, seconds: object) -> None:
    """Seed ``commands.{key}.timeout_seconds`` at the MAIN-ANCHORED path."""
    config_dir = repo_root / '.plan' / 'local'
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / 'run-configuration.json').write_text(
        json.dumps({'version': 1, 'commands': {key: {'timeout_seconds': seconds}}}),
        encoding='utf-8',
    )


def _seed_legacy_path_timeout(repo_root: Path, key: str, seconds: object) -> None:
    """Seed the SAME payload at the retired ``<repo>/.plan/`` path.

    The control's staging helper: this path is where the reader used to look and
    where the file never sits, so anything here must NOT reach the ceiling.
    """
    config_dir = repo_root / '.plan'
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / 'run-configuration.json').write_text(
        json.dumps({'version': 1, 'commands': {key: {'timeout_seconds': seconds}}}),
        encoding='utf-8',
    )


def _log_line(notation_sub: str, seconds: float, level: str = 'INFO') -> str:
    """Build one script-execution log line with a trailing (Ns) duration."""
    return f'[2026-06-29T09:00:01Z] [{level}] [3befe7] {notation_sub} (%.1fs)' % seconds


class TestImpossibleDurationFlagging:
    """Which calls the impossible-duration band flags, per call class."""

    def test_flags_a_deterministic_call_over_600(self, tmp_path, empty_home):
        # Arrange: a deterministic per-plan-op call recorded well over the flat 600s
        # ceiling (no build / ci-wait class match) and NO config anywhere.
        _write_log(tmp_path, PROBE_LOG_NAME, [_log_line(_DETERMINISTIC_CALL, 700.0)])

        # Act
        result = audit.cross_global_log_analysis(tmp_path)

        # Assert: the deterministic call keeps the flat 600s ceiling and is flagged.
        keys = [r['key'] for r in result['impossible_calls']]
        assert result['impossible_count'] == 1, result['impossible_calls']
        assert keys == ['plan-marshall:manage-tasks:manage-tasks read']

    def test_a_deterministic_call_keeps_the_flat_bound_despite_a_high_ratchet(self, tmp_path, empty_home):
        """The ratcheted ceiling applies to the build/ci-wait class ONLY.

        The matched control for the sparing test below: with the SAME 1200 s
        ratchet staged, a deterministic call at 700 s is still flagged. Without
        it, "the ratchet spared the call" would be satisfiable by a ratchet that
        raised the bound for everything.
        """
        _seed_queue_threshold(empty_home, 1200)
        _write_log(tmp_path, PROBE_LOG_NAME, [_log_line(_DETERMINISTIC_CALL, 700.0)])

        result = audit.cross_global_log_analysis(tmp_path)

        assert result['impossible_count'] == 1, result['impossible_calls']

    def test_spares_a_ci_wait_call_under_the_queue_state_ratchet(self, tmp_path, empty_home):
        # Arrange: a build/ci-wait class call at 700s AND a machine-global queue
        # state whose ratcheted reap threshold (1200s) covers it.
        _seed_queue_threshold(empty_home, 1200)
        _write_log(tmp_path, PROBE_LOG_NAME, [_log_line(_BUILD_CALL, 700.0)])

        # Act
        result = audit.cross_global_log_analysis(tmp_path)

        # Assert: the ratcheted ci-wait call is NOT flagged impossible; it lands in the
        # slow band instead (700 >= slow ceiling but < ratcheted 1200).
        assert result['impossible_count'] == 0, result['impossible_calls']
        slow_keys = [r['key'] for r in result['slow_calls']]
        assert 'plan-marshall:build-pyproject:pyproject_build run' in slow_keys

    def test_flags_a_ci_wait_call_over_the_ratcheted_ceiling(self, tmp_path, empty_home):
        # Arrange: a build/ci-wait class call that EXCEEDS even the ratcheted ceiling
        # (1300 > 1200) — a real hang past the adaptive budget, still flagged.
        _seed_queue_threshold(empty_home, 1200)
        _write_log(tmp_path, PROBE_LOG_NAME, [_log_line(_BUILD_CALL, 1300.0)])

        # Act
        result = audit.cross_global_log_analysis(tmp_path)

        # Assert: over the ratcheted ceiling → flagged impossible.
        assert result['impossible_count'] == 1, result['impossible_calls']


class TestRatchetedCeilingSources:
    """Where ``_ratcheted_ci_wait_ceiling`` reads from, and what it ignores."""

    def test_degrades_to_the_flat_ceiling_without_any_config(self, tmp_path, empty_home):
        """No run-configuration and no queue state → the flat floor.

        ``empty_home`` is what makes this assertion mean anything: the floor is
        being compared against a host whose machine-global state is known empty,
        not against whatever the developer's own home root happens to hold.
        """
        assert audit._ratcheted_ci_wait_ceiling(tmp_path) == audit._IMPOSSIBLE_DURATION_SECONDS

    def test_reads_the_queue_state_reap_threshold(self, tmp_path, empty_home):
        """The machine-global ``build-queue.json`` supplies a ceiling."""
        _seed_queue_threshold(empty_home, 1500)

        assert audit._ratcheted_ci_wait_ceiling(tmp_path) == 1500.0

    def test_reads_commands_timeout_from_the_main_anchored_path(self, tmp_path, empty_home):
        """``commands.{key}.timeout_seconds`` is read from ``.plan/local/``.

        This is the path ``get_run_config_path()`` resolves to. The reader used to
        look one directory up, where the file never sits, so this ceiling never
        reached it and every ci-wait call was measured against the bare floor.
        """
        _seed_main_anchored_timeout(tmp_path, _CI_WAIT_KEY, 1500)

        assert audit._ratcheted_ci_wait_ceiling(tmp_path) == 1500.0

    def test_a_run_configuration_at_the_retired_path_is_not_read(self, tmp_path, empty_home):
        """The control: the same payload at ``<repo>/.plan/`` contributes NOTHING.

        Paired with the test above, this is what distinguishes "reads the
        main-anchored path" from "reads any run-configuration it can find" — the
        two are indistinguishable from a passing positive alone.
        """
        _seed_legacy_path_timeout(tmp_path, _CI_WAIT_KEY, 1500)

        assert audit._ratcheted_ci_wait_ceiling(tmp_path) == audit._IMPOSSIBLE_DURATION_SECONDS

    def test_a_non_build_command_key_contributes_no_ceiling(self, tmp_path, empty_home):
        """Only a build / ci-wait class command key raises the ceiling.

        A deterministic key's persisted timeout is not a ci-wait budget, so it
        must not widen the band that judges ci-wait calls.
        """
        _seed_main_anchored_timeout(tmp_path, 'manage-tasks:read', 1500)

        assert audit._ratcheted_ci_wait_ceiling(tmp_path) == audit._IMPOSSIBLE_DURATION_SECONDS

    def test_the_ceiling_is_the_max_across_both_homes(self, tmp_path, empty_home):
        """Both sources are consulted and the larger wins."""
        _seed_queue_threshold(empty_home, 1200)
        _seed_main_anchored_timeout(tmp_path, _CI_WAIT_KEY, 2400)

        assert audit._ratcheted_ci_wait_ceiling(tmp_path) == 2400.0

    def test_either_source_degrades_on_its_own(self, tmp_path, empty_home):
        """An absent or unusable source contributes nothing and suppresses nothing.

        Asserted in both directions, because the reader's two blocks are
        independent: an early return on the first would have silently discarded
        the second, which is exactly the shape the previous single-file reader
        had.
        """
        # Queue state present and usable, run-configuration missing entirely.
        _seed_queue_threshold(empty_home, 1500)
        assert audit._ratcheted_ci_wait_ceiling(tmp_path) == 1500.0

        # Queue state UNUSABLE (a bool, and a non-positive), run-configuration usable.
        _seed_queue_threshold(empty_home, True)
        _seed_main_anchored_timeout(tmp_path, _CI_WAIT_KEY, 1800)
        assert audit._ratcheted_ci_wait_ceiling(tmp_path) == 1800.0

        _seed_queue_threshold(empty_home, -5)
        assert audit._ratcheted_ci_wait_ceiling(tmp_path) == 1800.0

    def test_an_unreadable_queue_state_degrades_to_the_flat_ceiling(self, tmp_path, empty_home):
        """A corrupt machine-global file is not a ceiling, and is not a crash."""
        (empty_home / 'build-queue.json').write_text('{not json', encoding='utf-8')

        assert audit._ratcheted_ci_wait_ceiling(tmp_path) == audit._IMPOSSIBLE_DURATION_SECONDS


def test_is_build_or_ci_wait_call_classifier():
    assert audit._is_build_or_ci_wait_call('plan-marshall:build-pyproject:pyproject_build run')
    assert audit._is_build_or_ci_wait_call('plan-marshall:tools-integration-ci:ci checks')
    assert not audit._is_build_or_ci_wait_call('plan-marshall:manage-tasks:manage-tasks read')
