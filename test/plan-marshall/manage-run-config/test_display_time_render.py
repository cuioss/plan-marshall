#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the display-only timestamp render helper (_display_time) — D3 and D5.

Covers:
- D5(a) — with the knob unset (UTC), a rendered timestamp is byte-identical to
  the pre-knob strftime output, for BOTH routed caller formats.
- D5(b) — with a positive-offset zone, a rendered timestamp converts AND carries
  an unambiguous label from which the zone and the exact instant are recoverable.
- D3 — a CONVERTED timestamp can never be emitted without its label.
- D5(c) — a stored timestamp is UTC under ANY knob value (the write path never
  consults the display timezone), asserted on the DIGITS at both canonical store
  sites: ``file_ops.now_utc_iso`` and the ``manage-lessons.get_next_id``
  identifier prefix.

Render determinism comes from a fixed instant plus an explicit ``tz=`` override;
the config-resolution path is exercised separately through the persisted store.

The store-site assertions pin the clock and compare digits rather than checking
for a trailing ``Z``. Both store sites format the zone as a LITERAL in their
format string, so a suffix check passes under every timezone and observes the
format string instead of the instant — the digits are the only part a leak moves.
"""

import json
from datetime import UTC, datetime

import file_ops
from _display_time import render_timestamp, resolve_display_timezone
from conftest import load_script_module
from run_config import DISPLAY_TIMEZONE_DEFAULT, read_display_timezone

# A fixed UTC instant: 2026-08-11 14:30:45 UTC. In Asia/Kolkata (+05:30, no DST)
# this is 20:00:45; that pair is the deterministic conversion checked below.
FIXED = datetime(2026, 8, 11, 14, 30, 45, tzinfo=UTC)

# The store-site digits the pinned instant must produce, and the digits it would
# produce if the display zone (Asia/Kolkata, +05:30) leaked into the write path.
# Naming both is what makes each store assertion a two-sided discriminator
# rather than a shape check that any zone would satisfy.
STORED_UTC_STAMP = '2026-08-11T14:30:45Z'
UTC_HOUR_PREFIX = '2026-08-11-14-'
KOLKATA_HOUR_PREFIX = '2026-08-11-20-'

# The two caller formats routed through the helper at the live RENDER sites.
METRICS_BODY, METRICS_SUFFIX = '%Y-%m-%d %H:%M:%S', ' UTC'  # manage-metrics.py
RETRO_BODY, RETRO_SUFFIX = '%Y-%m-%dT%H:%M:%S', 'Z'  # compile-report.py

# The hyphenated production script is not importable by name. It is loaded
# unregistered so this module cannot displace the ``manage_lessons`` entry the
# manage-lessons suite publishes under that name.
_lessons_mod = load_script_module('plan-marshall', 'manage-lessons', 'manage-lessons.py', register=False)


class _FrozenClock:
    """Stand-in for ``datetime.datetime`` that pins one INSTANT.

    ``now(tz)`` projects the pinned instant into ``tz`` rather than returning a
    fixed wall-clock reading, so a caller that asks for UTC and a caller that
    asks for a converted zone receive the same moment expressed differently.
    That is precisely what lets a digits assertion tell a UTC store apart from a
    converted one: a leak changes the digits, not merely the tzinfo.
    """

    def __init__(self, instant: datetime) -> None:
        self._instant = instant

    def now(self, tz=None) -> datetime:  # noqa: D102 - mirrors the datetime API
        if tz is None:
            # ``datetime.now()`` yields the LOCAL wall clock with no tzinfo.
            return self._instant.astimezone().replace(tzinfo=None)
        return self._instant.astimezone(tz)


def _configure_display_zone(plan_context, zone: str) -> None:
    """Persist ``zone`` as the project's display_timezone for one test."""
    plan_context.fixture_dir.mkdir(parents=True, exist_ok=True)
    (plan_context.fixture_dir / 'run-configuration.json').write_text(
        json.dumps({'version': 1, 'commands': {}, 'display_timezone': zone})
    )


# =============================================================================
# D5(a) — unset (UTC) is byte-identical to today
# =============================================================================


def test_utc_render_is_byte_identical_to_legacy_metrics_format():
    """UTC render of the metrics format equals the pre-knob strftime output."""
    rendered = render_timestamp(FIXED, METRICS_BODY, METRICS_SUFFIX, tz='UTC')
    assert rendered == FIXED.strftime('%Y-%m-%d %H:%M:%S UTC')
    assert rendered == '2026-08-11 14:30:45 UTC'


def test_utc_render_is_byte_identical_to_legacy_retro_format():
    """UTC render of the retrospective format equals the pre-knob strftime output."""
    rendered = render_timestamp(FIXED, RETRO_BODY, RETRO_SUFFIX, tz='UTC')
    assert rendered == FIXED.strftime('%Y-%m-%dT%H:%M:%SZ')
    assert rendered == '2026-08-11T14:30:45Z'


def test_default_resolution_is_utc_and_byte_identical(plan_context):
    """With no display_timezone configured, resolution defaults to UTC output."""
    plan_context.fixture_dir.mkdir(parents=True, exist_ok=True)
    rendered = render_timestamp(FIXED, METRICS_BODY, METRICS_SUFFIX)
    assert rendered == '2026-08-11 14:30:45 UTC'


def test_naive_datetime_is_treated_as_utc():
    """A naive datetime is interpreted as UTC (never localised twice)."""
    naive = datetime(2026, 8, 11, 14, 30, 45)
    assert render_timestamp(naive, METRICS_BODY, METRICS_SUFFIX, tz='UTC') == '2026-08-11 14:30:45 UTC'


# =============================================================================
# D5(b) — positive-offset zone converts AND labels
# =============================================================================


def test_positive_offset_zone_converts_and_labels():
    """A positive-offset zone converts the instant and appends its zone label."""
    rendered = render_timestamp(FIXED, METRICS_BODY, METRICS_SUFFIX, tz='Asia/Kolkata')

    # Converted body: 14:30:45 UTC -> 20:00:45 IST.
    assert rendered.startswith('2026-08-11 20:00:45 ')
    # Zone named for a human...
    assert 'IST' in rendered
    # ...and the exact instant recoverable from the offset (cold-read safe).
    assert '(UTC+05:30)' in rendered
    # The stale UTC suffix must NOT survive a conversion.
    assert not rendered.endswith(' UTC')
    assert rendered != FIXED.strftime('%Y-%m-%d %H:%M:%S UTC')


def test_conversion_instant_is_recoverable_from_the_offset():
    """The offset in the label reconstructs the original UTC instant."""
    rendered = render_timestamp(FIXED, RETRO_BODY, RETRO_SUFFIX, tz='Asia/Kolkata')
    # 20:00:45 at +05:30 == 14:30:45 UTC == FIXED.
    assert rendered.startswith('2026-08-11T20:00:45 ')
    assert '(UTC+05:30)' in rendered


# =============================================================================
# D3 — a converted timestamp can never be emitted without its label
# =============================================================================


def test_every_converted_zone_carries_a_nonempty_offset_label():
    """For a spread of non-UTC zones, the output always carries a UTC-offset label."""
    for zone in ('Asia/Kolkata', 'America/New_York', 'Europe/Berlin', 'Pacific/Chatham'):
        rendered = render_timestamp(FIXED, METRICS_BODY, METRICS_SUFFIX, tz=zone)
        body_only = render_timestamp(FIXED, METRICS_BODY, '', tz='UTC').rsplit(' UTC', 1)[0]
        # A converted timestamp is never the bare UTC body, and always names its offset.
        assert '(UTC' in rendered, f'{zone}: converted render lacks a UTC-offset label: {rendered!r}'
        assert rendered != body_only


def test_utc_suffix_is_preserved_per_caller_when_unset():
    """The UTC path preserves each caller's historical label spelling verbatim."""
    assert render_timestamp(FIXED, METRICS_BODY, ' UTC', tz='UTC').endswith(' UTC')
    assert render_timestamp(FIXED, RETRO_BODY, 'Z', tz='UTC').endswith('Z')


# =============================================================================
# D5(c) — a stored timestamp is UTC under ANY knob value
# =============================================================================


def test_stored_timestamp_is_utc_under_any_knob_value(plan_context, monkeypatch):
    """The stored stamp carries the UTC DIGITS under a non-UTC display zone.

    ``now_utc_iso`` formats through ``strftime('%Y-%m-%dT%H:%M:%SZ')``, where the
    trailing ``Z`` is a literal character of the format string rather than a
    rendering of the zone. An ``endswith('Z')`` assertion is therefore true for
    every possible timezone and cannot fail under any conversion — it observes
    the format string, not the instant. The digits are what a conversion moves,
    so pinning the instant and asserting the exact stamp is what makes a
    converted write path red.
    """
    _configure_display_zone(plan_context, 'Asia/Kolkata')
    # The knob really is set to a non-UTC zone...
    assert read_display_timezone() == 'Asia/Kolkata'

    monkeypatch.setattr(file_ops, 'datetime', _FrozenClock(FIXED))
    stored = file_ops.now_utc_iso()

    # ...yet the canonical store primitive reports the UTC digits, ignoring it.
    assert stored == STORED_UTC_STAMP, f'stored timestamp is not UTC: {stored!r}'
    # The stamp round-trips to the pinned instant — the digits, not the suffix,
    # are what carries the zone.
    assert datetime.strptime(stored, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=UTC) == FIXED


def test_stored_lesson_id_prefix_is_utc_under_any_knob_value(plan_context, monkeypatch):
    """The lesson-id ``{date}-{hour}`` prefix is derived from UTC, not the display zone.

    ``get_next_id`` derives the prefix from ``datetime.now(UTC)``, and that
    prefix is simultaneously the identifier and the corpus sort key — the id
    format ``YYYY-MM-DD-HH-NNN`` is parsed back out to allocate the next
    sequence number. A converted derivation would therefore reorder the corpus
    silently rather than raise. The pinned instant is 14:30:45 UTC, which is
    20:00:45 in Asia/Kolkata, so the hour segment discriminates the two.
    """
    _configure_display_zone(plan_context, 'Asia/Kolkata')
    assert read_display_timezone() == 'Asia/Kolkata'

    monkeypatch.setattr(_lessons_mod, 'datetime', _FrozenClock(FIXED))
    lesson_id = _lessons_mod.get_next_id()

    assert lesson_id.startswith(UTC_HOUR_PREFIX), f'lesson id prefix is not UTC: {lesson_id!r}'
    assert not lesson_id.startswith(KOLKATA_HOUR_PREFIX), (
        f'lesson id prefix was derived from the display zone: {lesson_id!r}'
    )


# =============================================================================
# Config resolution — read/resolve behaviour
# =============================================================================


def test_read_display_timezone_defaults_to_utc(plan_context):
    """A fresh project with no config resolves the default UTC."""
    plan_context.fixture_dir.mkdir(parents=True, exist_ok=True)
    assert read_display_timezone() == DISPLAY_TIMEZONE_DEFAULT == 'UTC'


def test_read_display_timezone_reads_persisted_value(plan_context):
    """A persisted IANA zone is read back."""
    _configure_display_zone(plan_context, 'Europe/Berlin')
    assert read_display_timezone() == 'Europe/Berlin'


def test_read_display_timezone_fails_safe_on_unloadable_stored_zone(plan_context):
    """A stored zone that no longer loads degrades to UTC rather than crashing."""
    _configure_display_zone(plan_context, 'Not/AZone')
    assert read_display_timezone() == 'UTC'


def test_resolve_prefers_explicit_override_over_config(plan_context):
    """An explicit tz argument wins over the persisted value."""
    _configure_display_zone(plan_context, 'Asia/Kolkata')
    assert resolve_display_timezone('Europe/Berlin') == 'Europe/Berlin'
    assert resolve_display_timezone(None) == 'Asia/Kolkata'
