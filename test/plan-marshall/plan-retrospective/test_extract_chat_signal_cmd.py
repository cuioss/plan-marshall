# SPDX-License-Identifier: FSL-1.1-ALv2
"""Parsing, reduction and output-contract tests for ``extract-chat-signal.py``."""


from __future__ import annotations

import json

from _extract_chat_signal_fixtures import SCRIPT_PATH, SKILL_LOAD_TEXT, _Args, _mod, _turn

from conftest import run_script  # noqa: E402

# ---------------------------------------------------------------------------
# Unit tests: render_reduced
# ---------------------------------------------------------------------------


class TestRenderReduced:
    def test_renders_role_text_blocks_separated_by_blank_line(self):
        turns = [
            {'role': 'user', 'text': 'hi'},
            {'role': 'assistant', 'text': '[STATUS] go'},
        ]
        assert _mod.render_reduced(turns) == 'user: hi\n\nassistant: [STATUS] go'

    def test_empty_turns_render_empty_string(self):
        assert _mod.render_reduced([]) == ''

    def test_deterministic_for_identical_input(self):
        turns = [{'role': 'user', 'text': 'x'}, {'role': 'assistant', 'text': '[ERROR] y'}]
        assert _mod.render_reduced(turns) == _mod.render_reduced(turns)


# ---------------------------------------------------------------------------
# Unit tests: read_transcript_lines
# ---------------------------------------------------------------------------


class TestReadTranscriptLines:
    def test_reads_lines_of_existing_file(self, tmp_path):
        path = tmp_path / 'session.jsonl'
        path.write_text('line one\nline two\n', encoding='utf-8')
        assert _mod.read_transcript_lines(path) == ['line one', 'line two']

    def test_missing_file_raises_file_not_found(self, tmp_path):
        import pytest

        missing = tmp_path / 'nope.jsonl'
        with pytest.raises(FileNotFoundError):
            _mod.read_transcript_lines(missing)


class TestCmdRun:
    def test_normal_operation_within_threshold(self, tmp_path):
        path = tmp_path / 'session.jsonl'
        path.write_text(
            _turn('user', 'implement the feature') + '\n'
            + _turn('assistant', '[STATUS] starting work') + '\n'
            + _turn('assistant', 'unmarked prose dropped') + '\n',
            encoding='utf-8',
        )
        result = _mod.cmd_run(_Args(str(path), _mod.DEFAULT_READ_BUDGET_BYTES))
        assert result['aspect'] == 'chat-signal-extraction'
        assert result['status'] == 'success'
        assert result['reduced_turn_count'] == 2
        assert result['no_signal'] is False
        assert result['over_budget'] is False
        assert result['reduced_bytes'] > 0
        assert 'implement the feature' in result['reduced_transcript']
        assert 'unmarked prose dropped' not in result['reduced_transcript']

    def test_reduction_keeps_only_the_operator_turn(self, tmp_path):
        """Regression: a transcript of one operator turn plus three synthetic
        turns reduces to exactly the operator turn, and reports the removal.

        Before the fix every ``user`` turn was kept verbatim, so the "reduced"
        transcript was dominated by injected skill bodies and empty
        placeholders.
        """
        path = tmp_path / 'session.jsonl'
        path.write_text(
            _turn('user', 'rename the module please') + '\n'
            + _turn('user', SKILL_LOAD_TEXT) + '\n'
            + _turn('user', '') + '\n'
            + _turn('user', '   \n  ') + '\n',
            encoding='utf-8',
        )
        result = _mod.cmd_run(_Args(str(path), _mod.DEFAULT_READ_BUDGET_BYTES))

        assert result['reduced_turn_count'] == 1
        assert result['raw_turn_count'] == 4
        assert result['dropped_turn_count'] == 3
        assert result['no_signal'] is False
        assert result['reduced_transcript'] == 'user: rename the module please'
        assert 'Base directory for this skill:' not in result['reduced_transcript']

    def test_only_skill_load_and_empty_turns_yields_no_signal(self, tmp_path):
        """A transcript composed entirely of framework boilerplate degrades
        honestly to Tier 2 instead of paying a full Tier-1 read."""
        path = tmp_path / 'boilerplate.jsonl'
        path.write_text(
            _turn('user', SKILL_LOAD_TEXT) + '\n'
            + _turn('user', SKILL_LOAD_TEXT) + '\n'
            + _turn('user', '') + '\n',
            encoding='utf-8',
        )
        result = _mod.cmd_run(_Args(str(path), _mod.DEFAULT_READ_BUDGET_BYTES))

        assert result['no_signal'] is True
        assert result['reduced_turn_count'] == 0
        assert result['raw_turn_count'] == 3
        assert result['dropped_turn_count'] == 3

    def test_marker_bearing_assistant_turns_still_retained(self, tmp_path):
        """The reduction narrows only the user-turn branch."""
        path = tmp_path / 'mixed.jsonl'
        path.write_text(
            _turn('user', SKILL_LOAD_TEXT) + '\n'
            + _turn('assistant', '[DECISION] chose option A') + '\n',
            encoding='utf-8',
        )
        result = _mod.cmd_run(_Args(str(path), _mod.DEFAULT_READ_BUDGET_BYTES))
        assert result['reduced_turn_count'] == 1
        assert '[DECISION] chose option A' in result['reduced_transcript']

    def test_empty_history_sets_no_signal(self, tmp_path):
        path = tmp_path / 'empty.jsonl'
        path.write_text('', encoding='utf-8')
        result = _mod.cmd_run(_Args(str(path), _mod.DEFAULT_READ_BUDGET_BYTES))
        assert result['status'] == 'success'
        assert result['reduced_turn_count'] == 0
        assert result['no_signal'] is True
        assert result['over_budget'] is False
        assert result['reduced_transcript'] == ''

    def test_all_dropped_turns_set_no_signal(self, tmp_path):
        path = tmp_path / 'no-signal.jsonl'
        path.write_text(
            _turn('assistant', 'prose with no marker') + '\n'
            + _turn('tool', 'tool output') + '\n',
            encoding='utf-8',
        )
        result = _mod.cmd_run(_Args(str(path), _mod.DEFAULT_READ_BUDGET_BYTES))
        assert result['no_signal'] is True
        assert result['reduced_turn_count'] == 0

    def test_over_budget_when_reduced_exceeds_small_budget(self, tmp_path):
        path = tmp_path / 'big.jsonl'
        # A single large user turn whose reduced rendering exceeds a tiny budget.
        path.write_text(_turn('user', 'x' * 5000) + '\n', encoding='utf-8')
        result = _mod.cmd_run(_Args(str(path), 100))
        assert result['status'] == 'success'
        assert result['reduced_turn_count'] == 1
        assert result['no_signal'] is False
        assert result['over_budget'] is True
        assert result['reduced_bytes'] > result['read_budget_bytes']

    def test_within_budget_not_over_budget(self, tmp_path):
        path = tmp_path / 'small.jsonl'
        path.write_text(_turn('user', 'short') + '\n', encoding='utf-8')
        result = _mod.cmd_run(_Args(str(path), 10_000))
        assert result['over_budget'] is False

    def test_two_mb_threshold_is_default_budget(self, tmp_path):
        # The canonical 2 MiB threshold: a reduced transcript just over 2 MiB
        # trips over_budget against the default budget.
        assert _mod.DEFAULT_READ_BUDGET_BYTES == 2 * 1024 * 1024
        path = tmp_path / 'two-mb.jsonl'
        path.write_text(_turn('user', 'y' * (2 * 1024 * 1024 + 10)) + '\n', encoding='utf-8')
        result = _mod.cmd_run(_Args(str(path), _mod.DEFAULT_READ_BUDGET_BYTES))
        assert result['over_budget'] is True

    def test_missing_transcript_returns_skipped(self, tmp_path):
        missing = tmp_path / 'absent.jsonl'
        result = _mod.cmd_run(_Args(str(missing), _mod.DEFAULT_READ_BUDGET_BYTES))
        assert result['status'] == 'skipped'
        assert result['reason'] == 'transcript_unavailable'
        assert result['no_signal'] is True
        assert result['over_budget'] is False
        assert result['reduced_turn_count'] == 0
        assert result['raw_turn_count'] == 0
        assert result['dropped_turn_count'] == 0
        assert result['reduced_transcript'] == ''

    def test_malformed_lines_do_not_crash(self, tmp_path):
        path = tmp_path / 'mixed.jsonl'
        path.write_text(
            'not json\n'
            + '{ broken\n'
            + _turn('user', 'kept after garbage') + '\n'
            + json.dumps([1, 2, 3]) + '\n',
            encoding='utf-8',
        )
        result = _mod.cmd_run(_Args(str(path), _mod.DEFAULT_READ_BUDGET_BYTES))
        assert result['status'] == 'success'
        assert result['reduced_turn_count'] == 1
        assert 'kept after garbage' in result['reduced_transcript']


# ---------------------------------------------------------------------------
# Integration tests (subprocess + TOON output contract)
# ---------------------------------------------------------------------------


class TestCmdRunIntegration:
    def test_emits_toon_for_normal_transcript(self, tmp_path):
        path = tmp_path / 'session.jsonl'
        path.write_text(
            _turn('user', 'do it') + '\n'
            + _turn('assistant', '[DECISION] chose option A') + '\n',
            encoding='utf-8',
        )
        result = run_script(
            SCRIPT_PATH, 'run', '--transcript-path', str(path)
        )
        assert result.success, result.stderr
        data = result.toon()
        assert data['aspect'] == 'chat-signal-extraction'
        assert data['status'] == 'success'
        assert int(data['reduced_turn_count']) == 2
        assert data['no_signal'] is False
        assert data['over_budget'] is False

    def test_toon_reports_raw_and_dropped_turn_counts(self, tmp_path):
        """The reduction must be observable in the emitted TOON."""
        path = tmp_path / 'session.jsonl'
        path.write_text(
            _turn('user', 'operator turn') + '\n'
            + _turn('user', SKILL_LOAD_TEXT) + '\n'
            + _turn('assistant', 'unmarked prose') + '\n',
            encoding='utf-8',
        )
        result = run_script(SCRIPT_PATH, 'run', '--transcript-path', str(path))
        assert result.success, result.stderr
        data = result.toon()
        assert int(data['reduced_turn_count']) == 1
        assert int(data['raw_turn_count']) == 3
        assert int(data['dropped_turn_count']) == 2

    def test_skipped_status_for_missing_transcript(self, tmp_path):
        missing = tmp_path / 'gone.jsonl'
        result = run_script(
            SCRIPT_PATH, 'run', '--transcript-path', str(missing)
        )
        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'skipped'
        assert data['reason'] == 'transcript_unavailable'
        assert data['no_signal'] is True

    def test_over_budget_flag_via_small_read_budget(self, tmp_path):
        path = tmp_path / 'big.jsonl'
        path.write_text(_turn('user', 'z' * 4000) + '\n', encoding='utf-8')
        result = run_script(
            SCRIPT_PATH, 'run', '--transcript-path', str(path),
            '--read-budget-bytes', '100',
        )
        assert result.success, result.stderr
        data = result.toon()
        assert data['over_budget'] is True
        assert int(data['reduced_bytes']) > int(data['read_budget_bytes'])

    def test_no_signal_flag_for_empty_transcript(self, tmp_path):
        path = tmp_path / 'empty.jsonl'
        path.write_text('', encoding='utf-8')
        result = run_script(
            SCRIPT_PATH, 'run', '--transcript-path', str(path)
        )
        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        assert data['no_signal'] is True
        assert int(data['reduced_turn_count']) == 0

    def test_missing_required_transcript_path_rejected(self):
        result = run_script(SCRIPT_PATH, 'run')
        assert not result.success
        assert result.returncode != 0

    def test_default_read_budget_reported_when_flag_omitted(self, tmp_path):
        path = tmp_path / 'session.jsonl'
        path.write_text(_turn('user', 'hi') + '\n', encoding='utf-8')
        result = run_script(
            SCRIPT_PATH, 'run', '--transcript-path', str(path)
        )
        assert result.success, result.stderr
        data = result.toon()
        assert int(data['read_budget_bytes']) == _mod.DEFAULT_READ_BUDGET_BYTES
