# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``analyze-logs.py``."""


from __future__ import annotations

import pytest
from _analyze_logs_fixtures import _analyze_logs, _attempt, _plain


class TestDetectVoluntaryCheckpointPolling:
    """Unit + regression tests for the tightened voluntary-checkpoint detector."""

    # ------------------------------------------------------------------
    # Precondition gate
    # ------------------------------------------------------------------

    def test_precondition_not_met_without_attempt_line(self):
        """No ``[ATTEMPT]`` line → precondition not met, zero candidates."""
        lines = [
            _plain('run_in_background=true'),
            _plain('until x; do sleep 1; done'),
        ]
        result = _analyze_logs.detect_voluntary_checkpoint_polling(lines)
        assert result['precondition_met'] is False
        assert result['polling_pairs_count'] == 0
        assert result['candidate_line_numbers'] == []

    def test_precondition_met_but_no_signal_fires_no_candidate(self):
        """An ``[ATTEMPT]`` line with a benign window → precondition met but
        no candidate. This is the load-bearing false-positive fix: the mere
        presence of an ATTEMPT line is not enough to flag a pair.
        """
        lines = [
            _attempt(),
            _plain('Wrote foo.py'),
            _plain('verification passed'),
        ]
        result = _analyze_logs.detect_voluntary_checkpoint_polling(lines)
        assert result['precondition_met'] is True
        assert result['polling_pairs_count'] == 0
        assert result['candidate_line_numbers'] == []

    # ------------------------------------------------------------------
    # Genuine background-poll signals
    # ------------------------------------------------------------------

    @pytest.mark.parametrize('window_text', [
        'launched Bash with run_in_background=true',
        'config has run_in_background: TRUE here',
    ])
    def test_run_in_background_marker_fires_candidate(self, window_text):
        """``run_in_background=true`` or ``run_in_background: TRUE`` in the
        window fires a candidate — the marker tolerates ``=`` or ``:`` and is
        matched case-insensitively.
        """
        lines = [
            _attempt(),
            _plain(window_text),
        ]
        result = _analyze_logs.detect_voluntary_checkpoint_polling(lines)
        assert result['precondition_met'] is True
        assert result['polling_pairs_count'] == 1
        # ATTEMPT line is index 0 → 1-based line number 1.
        assert result['candidate_line_numbers'] == [1]

    def test_until_sleep_done_shape_spanning_window_fires_candidate(self):
        """An ``until ... sleep ... done`` shape spanning several window lines
        fires a candidate (the hand-rolled poll loop the rule catches).
        """
        lines = [
            _attempt(),
            _plain('until [ -f marker ]; do'),
            _plain('  sleep 5'),
            _plain('done'),
        ]
        result = _analyze_logs.detect_voluntary_checkpoint_polling(lines)
        assert result['polling_pairs_count'] == 1
        assert result['candidate_line_numbers'] == [1]

    # ------------------------------------------------------------------
    # Regression: bare keywords no longer trigger (false-positive class)
    # ------------------------------------------------------------------

    def test_bare_wait_keyword_does_not_fire(self):
        """A bare ``wait`` keyword with no genuine poll signal → no candidate.
        Before the tightening this was a false positive.
        """
        lines = [
            _attempt(),
            _plain('please wait for the build to settle'),
        ]
        result = _analyze_logs.detect_voluntary_checkpoint_polling(lines)
        assert result['precondition_met'] is True
        assert result['polling_pairs_count'] == 0

    def test_bare_background_and_sleep_keywords_do_not_fire(self):
        """Bare ``background`` / ``sleep`` keywords without the
        ``until ... done`` shape or a ``run_in_background=true`` marker →
        no candidate. Guards the false-positive regression.
        """
        lines = [
            _attempt(),
            _plain('moved the task to the background queue'),
            _plain('sleep until the next dispatch'),
        ]
        result = _analyze_logs.detect_voluntary_checkpoint_polling(lines)
        assert result['polling_pairs_count'] == 0

    # ------------------------------------------------------------------
    # CI-wait exemptions
    # ------------------------------------------------------------------

    def test_ci_checks_wait_line_is_exempt(self):
        """A ``ci checks wait`` line in the window is a legitimate synchronous
        CI wait → exempt, never flagged as polling.
        """
        lines = [
            _attempt(),
            _plain('invoking ci checks wait for PR #123'),
        ]
        result = _analyze_logs.detect_voluntary_checkpoint_polling(lines)
        assert result['precondition_met'] is True
        assert result['polling_pairs_count'] == 0

    def test_ci_complete_precondition_marker_is_exempt(self):
        """The ``ci_complete_precondition`` work-log marker is a synchronous
        CI-completion gate → exempt.
        """
        lines = [
            _attempt(),
            _plain('ci_complete_precondition satisfied; continuing'),
        ]
        result = _analyze_logs.detect_voluntary_checkpoint_polling(lines)
        assert result['polling_pairs_count'] == 0

    def test_ci_wait_line_does_not_complete_until_sleep_done_span(self):
        """A CI-wait line is dropped BEFORE the ``until ... sleep ... done``
        scan, so it cannot bridge an otherwise-incomplete poll-loop span.
        Here ``done`` lives only on the exempt CI-wait line, so no candidate.
        """
        lines = [
            _attempt(),
            _plain('until [ -f marker ]; do'),
            _plain('  sleep 5'),
            # The only 'done' token is on the exempt CI-wait line, which is
            # stripped before the span scan → span never completes.
            _plain('ci checks wait done waiting'),
        ]
        result = _analyze_logs.detect_voluntary_checkpoint_polling(lines)
        assert result['polling_pairs_count'] == 0

    def test_ci_wait_does_not_suppress_genuine_signal_on_other_line(self):
        """An exempt CI-wait line in the window must not suppress a genuine
        ``run_in_background=true`` signal sitting on a different window line.
        """
        lines = [
            _attempt(),
            _plain('ci checks wait for PR #123'),
            _plain('also launched run_in_background=true'),
        ]
        result = _analyze_logs.detect_voluntary_checkpoint_polling(lines)
        assert result['polling_pairs_count'] == 1
        assert result['candidate_line_numbers'] == [1]

    # ------------------------------------------------------------------
    # Window boundary + multi-attempt counting
    # ------------------------------------------------------------------

    def test_signal_outside_five_line_window_does_not_fire(self):
        """A genuine signal beyond the 5-line window (lines idx+1..idx+5) is
        out of range → no candidate.
        """
        lines = [
            _attempt(),
            _plain('filler 1'),
            _plain('filler 2'),
            _plain('filler 3'),
            _plain('filler 4'),
            _plain('filler 5'),
            # 6th line after ATTEMPT — outside the window.
            _plain('run_in_background=true'),
        ]
        result = _analyze_logs.detect_voluntary_checkpoint_polling(lines)
        assert result['polling_pairs_count'] == 0

    def test_signal_on_last_window_line_fires(self):
        """A genuine signal on the 5th line after ATTEMPT (last in-window line)
        still fires — boundary inclusive.
        """
        lines = [
            _attempt(),
            _plain('filler 1'),
            _plain('filler 2'),
            _plain('filler 3'),
            _plain('filler 4'),
            _plain('run_in_background=true'),
        ]
        result = _analyze_logs.detect_voluntary_checkpoint_polling(lines)
        assert result['polling_pairs_count'] == 1
        assert result['candidate_line_numbers'] == [1]

    def test_multiple_attempts_count_each_candidate_with_line_numbers(self):
        """Each ATTEMPT line with a genuine signal in its window contributes a
        distinct 1-based candidate line number.
        """
        lines = [
            _attempt('first dispatch'),           # index 0 → line 1 (candidate)
            _plain('run_in_background=true'),      # index 1
            _plain('benign filler'),               # index 2
            _attempt('second dispatch'),           # index 3 → line 4 (candidate)
            _plain('until x; do sleep 1; done'),   # index 4
            _attempt('third dispatch'),            # index 5 → line 6 (no signal)
            _plain('verification passed'),          # index 6
        ]
        result = _analyze_logs.detect_voluntary_checkpoint_polling(lines)
        assert result['precondition_met'] is True
        assert result['polling_pairs_count'] == 2
        assert result['candidate_line_numbers'] == [1, 4]
