#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Display-only timestamp rendering.

A stored timestamp is ALWAYS UTC. This module is the single sanctioned surface
that converts such a timestamp into the operator's configured display timezone
for HUMAN reading. It is consumed at rendering surfaces exclusively and is never
called on a write or compare path — it reads the clock from its argument only,
never from ``datetime.now``, and mutates nothing.

The invariant this module enforces structurally: a CONVERTED timestamp can never
be emitted without a zone label. The UTC path (the default, and the fail-safe on
an unloadable zone) reproduces the caller's historical output byte-for-byte; the
conversion path always appends an unambiguous ``ABBREV (UTC±HH:MM)`` label from
which both the zone and the exact instant are recoverable.
"""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from run_config import DISPLAY_TIMEZONE_DEFAULT, read_display_timezone


def resolve_display_timezone(tz: str | None = None) -> str:
    """Resolve the display zone: an explicit *tz* wins, else the run-config value.

    Args:
        tz: Explicit zone override (IANA name). ``None`` reads the persisted
            ``display_timezone`` (default ``'UTC'``).

    Returns:
        The resolved IANA zone name.
    """
    return tz if tz is not None else read_display_timezone()


def _zone_label(local: datetime, zone: str) -> str:
    """Build an unambiguous zone label: ``ABBREV (UTC±HH:MM)``.

    The abbreviation (``%Z`` — e.g. ``EDT``, ``IST``) names the zone for a human;
    the numeric offset makes the instant recoverable even when the abbreviation
    is ambiguous across regions. When ``%Z`` yields nothing usable, the IANA zone
    name stands in for the abbreviation.

    Args:
        local: The instant already converted into the display zone.
        zone: The IANA zone name (abbreviation fallback).

    Returns:
        A non-empty label string.
    """
    abbrev = local.strftime('%Z') or zone
    offset = local.strftime('%z')  # e.g. '+0530', '-0400', '' when naive
    if offset:
        offset = f'{offset[:3]}:{offset[3:]}'  # '+0530' -> '+05:30'
        return f'{abbrev} (UTC{offset})'
    return abbrev


def render_timestamp(moment: datetime, body_fmt: str, utc_suffix: str, *, tz: str | None = None) -> str:
    """Render a stored-UTC datetime for human display, always labelled on conversion.

    Args:
        moment: The instant to render. Interpreted as UTC — a naive datetime is
            assumed UTC, an aware datetime is converted from its own zone. The
            clock is read from *moment* only; this function never calls
            ``datetime.now`` and never mutates a stored value.
        body_fmt: ``strftime`` format for the date/time BODY, carrying NO zone
            token. The zone label is owned by this function, not the caller.
        utc_suffix: The exact string appended verbatim when the display zone is
            UTC. It preserves each caller's historical UTC label (e.g. ``' UTC'``
            or ``'Z'``) so the unset/default output is byte-identical to today.
        tz: Display zone override (IANA name). ``None`` resolves the zone from
            run configuration (default ``'UTC'``).

    Returns:
        ``f'{body}{utc_suffix}'`` when the display zone is UTC (byte-identical to
        the pre-knob output); ``f'{body} {ABBREV (UTC±HH:MM)}'`` when converted.
    """
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=UTC)
    zone = resolve_display_timezone(tz)
    if zone == DISPLAY_TIMEZONE_DEFAULT:
        return moment.astimezone(UTC).strftime(body_fmt) + utc_suffix
    try:
        info = ZoneInfo(zone)
    except (ZoneInfoNotFoundError, ValueError):
        # Fail-safe: an unloadable zone renders in UTC rather than crashing a
        # display surface. This branch does NOT convert, so the byte-identical
        # UTC suffix stays the correct (and honest) label.
        return moment.astimezone(UTC).strftime(body_fmt) + utc_suffix
    local = moment.astimezone(info)
    return f'{local.strftime(body_fmt)} {_zone_label(local, zone)}'
