#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unit tests for the pure computation helpers in manage-metrics.py.

The integration suites (``test_manage_metrics.py``, ``..._phase_boundary.py``)
exercise these helpers indirectly through ``generate`` / ``end-phase`` with
phases whose ``duration_seconds`` is already persisted. This module pins the
helpers directly, covering the branches the integration paths skip:

- ``_coerce_numeric``'s string→int / string→float / non-coercible-string /
  non-string passthrough arms;
- ``_wall_clock_ms`` deriving the span from ``start_time`` / ``end_time``
  timestamps when ``duration_seconds`` is absent, including the ``Z``-suffix
  normalisation, the malformed-timestamp → ``None`` arm, and the
  no-signal → ``None`` arm;
- ``_worked_ms``'s agent-only / subagent-only / max-of-both / neither arms plus
  the non-numeric-guard;
- ``read_metrics_raw``'s empty-content and top-level-key-plus-numeric-coercion
  paths, and ``write_metrics``'s lossless round-trip of extra top-level keys.
"""

import importlib.util

from conftest import get_script_path

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-metrics', 'manage-metrics.py')

# kebab-case filename — load via importlib under a unique module name.
_spec = importlib.util.spec_from_file_location('manage_metrics_helpers', SCRIPT_PATH)
assert _spec is not None and _spec.loader is not None
manage_metrics = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(manage_metrics)

_coerce_numeric = manage_metrics._coerce_numeric
_wall_clock_ms = manage_metrics._wall_clock_ms
_worked_ms = manage_metrics._worked_ms
read_metrics_raw = manage_metrics.read_metrics_raw
write_metrics = manage_metrics.write_metrics


# =============================================================================
# _coerce_numeric
# =============================================================================


class TestCoerceNumeric:
    """_coerce_numeric coerces numeric strings, leaving everything else as-is."""

    def test_integer_string_coerces_to_int(self):
        """A pure-integer string becomes an int."""
        result = _coerce_numeric('42')
        assert result == 42
        assert isinstance(result, int)

    def test_float_string_coerces_to_float(self):
        """A decimal string that is not an int becomes a float."""
        result = _coerce_numeric('1.5')
        assert result == 1.5
        assert isinstance(result, float)

    def test_non_numeric_string_returned_unchanged(self):
        """A non-numeric string falls through both casts and is returned verbatim."""
        assert _coerce_numeric('alpha') == 'alpha'

    def test_empty_string_returned_unchanged(self):
        """An empty string is not coercible and is returned as the empty string."""
        assert _coerce_numeric('') == ''

    def test_non_string_int_passthrough(self):
        """A value that is already an int short-circuits the string casts."""
        assert _coerce_numeric(7) == 7

    def test_non_string_none_passthrough(self):
        """A non-string, non-numeric value (None) is returned unchanged."""
        assert _coerce_numeric(None) is None


# =============================================================================
# _wall_clock_ms
# =============================================================================


class TestWallClockMs:
    """_wall_clock_ms prefers duration_seconds, else derives from timestamps."""

    def test_duration_seconds_float_wins(self):
        """A persisted float duration_seconds is converted to milliseconds."""
        assert _wall_clock_ms({'duration_seconds': 1.5}) == 1500

    def test_duration_seconds_int_wins(self):
        """A persisted int duration_seconds is converted to milliseconds."""
        assert _wall_clock_ms({'duration_seconds': 2}) == 2000

    def test_derives_span_from_iso_timestamps(self):
        """Without duration_seconds the span is derived from start/end ISO stamps."""
        phase = {
            'start_time': '2026-01-01T00:00:00+00:00',
            'end_time': '2026-01-01T00:01:00+00:00',
        }
        assert _wall_clock_ms(phase) == 60000

    def test_normalises_z_suffix_timestamps(self):
        """The Z UTC suffix is normalised before fromisoformat parses the span."""
        phase = {
            'start_time': '2026-01-01T00:00:00Z',
            'end_time': '2026-01-01T00:02:00Z',
        }
        assert _wall_clock_ms(phase) == 120000

    def test_malformed_timestamps_return_none(self):
        """Unparseable timestamps degrade to None rather than raising."""
        phase = {'start_time': 'not-a-timestamp', 'end_time': 'also-bad'}
        assert _wall_clock_ms(phase) is None

    def test_no_signal_returns_none(self):
        """No duration_seconds and no timestamp pair yields None."""
        assert _wall_clock_ms({}) is None

    def test_only_start_time_returns_none(self):
        """A start_time without a paired end_time yields None (incomplete span)."""
        assert _wall_clock_ms({'start_time': '2026-01-01T00:00:00+00:00'}) is None


# =============================================================================
# _worked_ms
# =============================================================================


class TestWorkedMs:
    """_worked_ms = max(agent_duration_ms, subagent_duration_ms); missing → 0."""

    def test_agent_only(self):
        """With only an agent span present, that span is the worked value."""
        assert _worked_ms({'agent_duration_ms': 5000}) == 5000

    def test_subagent_only(self):
        """With only a subagent span present, that span is the worked value."""
        assert _worked_ms({'subagent_duration_ms': 7000}) == 7000

    def test_both_present_takes_max_not_sum(self):
        """When both spans are present the larger subsumes the overlap (no sum)."""
        assert _worked_ms({'agent_duration_ms': 5000, 'subagent_duration_ms': 7000}) == 7000

    def test_neither_present_is_zero(self):
        """Absent operands are treated as zero worked time."""
        assert _worked_ms({}) == 0

    def test_non_numeric_operand_treated_as_zero(self):
        """A non-numeric duration field is ignored (treated as zero)."""
        assert _worked_ms({'agent_duration_ms': 'oops'}) == 0


# =============================================================================
# read_metrics_raw / write_metrics
# =============================================================================


class TestReadMetricsRaw:
    """read_metrics_raw parses the custom TOON-like metrics format."""

    def test_missing_file_returns_empty_phases(self, plan_context):
        """A plan with no metrics.toon reads back as an empty phases map."""
        assert read_metrics_raw('helpers-no-file') == {'phases': {}}

    def test_whitespace_only_content_returns_empty_phases(self, plan_context):
        """A metrics.toon with only whitespace reads back as empty phases."""
        metrics_path = plan_context.plan_dir_for('helpers-blank') / 'work' / 'metrics.toon'
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        metrics_path.write_text('   \n\n', encoding='utf-8')

        assert read_metrics_raw('helpers-blank') == {'phases': {}}

    def test_top_level_keys_and_numeric_coercion(self, plan_context):
        """Lines before the first [phase] block become top-level keys; phase values coerce."""
        metrics_path = plan_context.plan_dir_for('helpers-toplevel') / 'work' / 'metrics.toon'
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        metrics_path.write_text(
            'plan_id: helpers-toplevel\n'
            'custom_note: hello world\n'
            '\n'
            '[1-init]\n'
            '  total_tokens: 1234\n'
            '  ratio: 1.5\n'
            '  label: alpha\n',
            encoding='utf-8',
        )

        data = read_metrics_raw('helpers-toplevel')

        # Top-level (pre-block) keys are captured as strings.
        assert data['plan_id'] == 'helpers-toplevel'
        assert data['custom_note'] == 'hello world'
        # Phase values coerce: int, then float, then string fallback.
        init = data['phases']['1-init']
        assert init['total_tokens'] == 1234
        assert init['ratio'] == 1.5
        assert init['label'] == 'alpha'

    def test_write_metrics_round_trips_extra_top_level_keys(self, plan_context):
        """write_metrics re-emits non-standard top-level keys (lossless round-trip)."""
        write_metrics(
            'helpers-roundtrip',
            {
                'plan_id': 'helpers-roundtrip',
                'session_message_count': 9,
                'phases': {'1-init': {'total_tokens': 50}},
            },
        )

        content = (
            plan_context.plan_dir_for('helpers-roundtrip') / 'work' / 'metrics.toon'
        ).read_text(encoding='utf-8')
        assert 'session_message_count: 9' in content

        # And the extra key survives a read. Top-level (pre-block) keys are kept
        # verbatim as strings — only phase-scoped values are numeric-coerced — so
        # the round-tripped value reads back as the string '9'.
        data = read_metrics_raw('helpers-roundtrip')
        assert data['session_message_count'] == '9'
        assert data['phases']['1-init']['total_tokens'] == 50
