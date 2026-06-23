# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``extract-chat-signal.py``.

The script reduces a Claude Code session JSONL transcript to its
signal-bearing turns (Aspect 13 of ``plan-retrospective``). It keeps every
``user`` turn verbatim and every ``assistant`` turn carrying a decision
marker, dropping everything else. It then emits a TOON payload carrying the
two Tier-2 trigger flags:

- ``no_signal`` — true when the reduction kept zero turns.
- ``over_budget`` — true when the reduced text exceeds ``--read-budget-bytes``.

Either flag is the orchestrator's signal to fall back to the Tier-2 WARNING
finding (``reason: transcript_too_large``). A missing transcript yields
``status: skipped, reason: transcript_unavailable``.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from conftest import MARKETPLACE_ROOT, run_script  # noqa: E402

SCRIPT_PATH = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'plan-retrospective'
    / 'scripts'
    / 'extract-chat-signal.py'
)

# Direct module load so unit tests can poke the pure helpers.
_spec = importlib.util.spec_from_file_location('extract_chat_signal', str(SCRIPT_PATH))
assert _spec is not None and _spec.loader is not None
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


# ---------------------------------------------------------------------------
# JSONL turn builders
# ---------------------------------------------------------------------------


def _turn(role: str, content) -> str:
    """Produce one JSONL event line carrying a ``message`` with ``role``/``content``."""
    return json.dumps({'type': 'turn', 'message': {'role': role, 'content': content}})


def _text_blocks(*texts: str) -> list[dict[str, str]]:
    """Build a list of ``text`` content blocks (the common multi-block shape)."""
    return [{'type': 'text', 'text': t} for t in texts]


# ---------------------------------------------------------------------------
# Unit tests: extract_text
# ---------------------------------------------------------------------------


class TestExtractText:
    def test_plain_string_content_returned_verbatim(self):
        assert _mod.extract_text('hello world') == 'hello world'

    def test_text_blocks_joined_by_newline(self):
        content = _text_blocks('first', 'second')
        assert _mod.extract_text(content) == 'first\nsecond'

    def test_non_text_blocks_skipped(self):
        content = [
            {'type': 'tool_use', 'name': 'Bash'},
            {'type': 'text', 'text': 'kept'},
            {'type': 'tool_result', 'content': 'ignored'},
        ]
        assert _mod.extract_text(content) == 'kept'

    def test_typeless_block_with_text_treated_as_text(self):
        # Defensive shape drift: a block missing ``type`` but carrying ``text``.
        content = [{'text': 'recovered'}]
        assert _mod.extract_text(content) == 'recovered'

    def test_unknown_shape_yields_empty_string(self):
        assert _mod.extract_text(42) == ''
        assert _mod.extract_text(None) == ''
        assert _mod.extract_text({'role': 'user'}) == ''

    def test_block_with_non_string_text_ignored(self):
        content = [{'type': 'text', 'text': 123}]
        assert _mod.extract_text(content) == ''


# ---------------------------------------------------------------------------
# Unit tests: is_signal_bearing
# ---------------------------------------------------------------------------


class TestIsSignalBearing:
    def test_user_turn_always_kept(self):
        assert _mod.is_signal_bearing('user', 'anything at all') is True

    def test_user_turn_kept_even_when_empty(self):
        assert _mod.is_signal_bearing('user', '') is True

    def test_assistant_turn_kept_with_decision_marker(self):
        assert _mod.is_signal_bearing('assistant', 'now [STATUS] running phase') is True

    def test_assistant_turn_dropped_without_marker(self):
        assert _mod.is_signal_bearing('assistant', 'just some prose') is False

    def test_each_marker_triggers_retention(self):
        for marker in _mod.DECISION_MARKERS:
            assert _mod.is_signal_bearing('assistant', f'prefix {marker} suffix') is True

    def test_other_roles_dropped(self):
        assert _mod.is_signal_bearing('tool', '[STATUS] still dropped') is False
        assert _mod.is_signal_bearing('system', 'whatever') is False


# ---------------------------------------------------------------------------
# Unit tests: parse_turn
# ---------------------------------------------------------------------------


class TestParseTurn:
    def test_parses_valid_user_turn(self):
        line = _turn('user', 'hello')
        assert _mod.parse_turn(line) == ('user', 'hello')

    def test_parses_assistant_text_blocks(self):
        line = _turn('assistant', _text_blocks('[STATUS] up'))
        assert _mod.parse_turn(line) == ('assistant', '[STATUS] up')

    def test_blank_line_returns_none(self):
        assert _mod.parse_turn('') is None
        assert _mod.parse_turn('   \t  ') is None

    def test_non_json_line_returns_none(self):
        assert _mod.parse_turn('this is not json') is None
        assert _mod.parse_turn('{ broken json') is None

    def test_non_object_payload_returns_none(self):
        assert _mod.parse_turn(json.dumps([1, 2, 3])) is None
        assert _mod.parse_turn(json.dumps('a bare string')) is None

    def test_event_without_message_returns_none(self):
        assert _mod.parse_turn(json.dumps({'type': 'summary'})) is None

    def test_message_not_object_returns_none(self):
        assert _mod.parse_turn(json.dumps({'message': 'not-a-dict'})) is None

    def test_missing_role_returns_none(self):
        assert _mod.parse_turn(json.dumps({'message': {'content': 'x'}})) is None

    def test_empty_role_returns_none(self):
        assert _mod.parse_turn(json.dumps({'message': {'role': '', 'content': 'x'}})) is None

    def test_turn_with_only_non_text_blocks_yields_empty_text(self):
        line = _turn('user', [{'type': 'tool_result', 'content': 'r'}])
        assert _mod.parse_turn(line) == ('user', '')


# ---------------------------------------------------------------------------
# Unit tests: reduce_transcript
# ---------------------------------------------------------------------------


class TestReduceTranscript:
    def test_keeps_user_and_marked_assistant_drops_rest(self):
        lines = [
            _turn('user', 'do the thing'),
            _turn('assistant', 'thinking out loud with no marker'),
            _turn('assistant', _text_blocks('[DISPATCH] launching agent')),
            _turn('tool', 'tool output that must be dropped'),
        ]
        kept = _mod.reduce_transcript(lines)
        assert kept == [
            {'role': 'user', 'text': 'do the thing'},
            {'role': 'assistant', 'text': '[DISPATCH] launching agent'},
        ]

    def test_preserves_document_order(self):
        lines = [
            _turn('assistant', '[STATUS] a'),
            _turn('user', 'b'),
            _turn('assistant', '[ERROR] c'),
        ]
        kept = _mod.reduce_transcript(lines)
        assert [t['text'] for t in kept] == ['[STATUS] a', 'b', '[ERROR] c']

    def test_malformed_lines_dropped_silently(self):
        lines = [
            'not json at all',
            '{ truncated',
            _turn('user', 'survives'),
            json.dumps({'type': 'summary'}),
        ]
        kept = _mod.reduce_transcript(lines)
        assert kept == [{'role': 'user', 'text': 'survives'}]

    def test_empty_history_keeps_nothing(self):
        assert _mod.reduce_transcript([]) == []

    def test_all_unmarked_assistant_keeps_nothing(self):
        lines = [
            _turn('assistant', 'prose one'),
            _turn('assistant', 'prose two'),
            _turn('tool', 'output'),
        ]
        assert _mod.reduce_transcript(lines) == []


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


# ---------------------------------------------------------------------------
# Unit tests: cmd_run (pure, via a Namespace-like shim)
# ---------------------------------------------------------------------------


class _Args:
    """Minimal stand-in for ``argparse.Namespace`` carrying the two run args."""

    def __init__(self, transcript_path: str, read_budget_bytes: int):
        self.transcript_path = transcript_path
        self.read_budget_bytes = read_budget_bytes


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
