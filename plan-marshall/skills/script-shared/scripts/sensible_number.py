# SPDX-License-Identifier: FSL-1.1-ALv2
"""Canonical human-friendly number parser for config values.

This module is the single, reusable parser that turns human-friendly
numeric strings (``"50K"``, ``"1.5M"``, ``"50_000"``) into plain ``int``
values. Config sites that store a readable magnitude string parse it back
to an integer through :func:`parse_sensible_int` at read time, so the
on-disk config stays readable while the consumer still works with an int.

The module is dependency-free (stdlib only) and pure — no I/O, no globals,
no side effects. It is import-reachable as ``import sensible_number`` because
``script-shared/scripts`` is already on the executor's PYTHONPATH; it carries
no ``plugin.json`` notation (imported-only library module).

Accepted forms (via :func:`parse_sensible_int`):

* plain integers — ``50000`` (``int``) or ``"50000"`` (numeric ``str``);
* underscore-grouped integer strings — ``"50_000"`` → ``50000``;
* magnitude-suffixed strings, case-insensitive, with multipliers
  ``K`` = 1_000, ``M`` = 1_000_000, ``G`` = 1_000_000_000 —
  ``"50K"`` → 50000, ``"1.5M"`` → 1_500_000, ``"2G"`` → 2_000_000_000.
  The suffixed form MAY carry a decimal mantissa (``"1.5M"``) as long as
  the product is a whole number;
* optional surrounding whitespace around any of the above.

Rejected forms raise ``ValueError`` naming the offending input:
empty / ``None`` / non-numeric garbage / unknown suffix / negative /
a suffixed form whose product is fractional (e.g. ``"1.5K"`` → 1500 is
fine, but a form that does not divide cleanly is rejected).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

__all__ = ['parse_sensible_int']

# Magnitude suffix → multiplier. Keys are upper-case; lookup upper-cases
# the input suffix so the parser is case-insensitive.
_MULTIPLIERS: dict[str, int] = {
    'K': 1_000,
    'M': 1_000_000,
    'G': 1_000_000_000,
}


def parse_sensible_int(value: object) -> int:
    """Parse a human-friendly numeric value into a non-negative ``int``.

    Args:
        value: An ``int`` or a ``str`` in any accepted form (see module
            docstring). ``int`` inputs are validated and returned as-is;
            ``str`` inputs are stripped, underscore-grouped, and optionally
            magnitude-suffixed.

    Returns:
        The parsed value as a plain ``int``.

    Raises:
        ValueError: when *value* is ``None``, an empty / whitespace-only
            string, a non-numeric string, carries an unknown magnitude
            suffix, is negative, or is a suffixed form whose product is
            fractional. The message names the offending input.
    """
    if value is None:
        raise ValueError('cannot parse sensible int from None')

    # Accept genuine ints (and reject bools, which are an int subclass but
    # never a meaningful magnitude here).
    if isinstance(value, bool):
        raise ValueError(f'cannot parse sensible int from boolean: {value!r}')
    if isinstance(value, int):
        if value < 0:
            raise ValueError(f'negative values are not allowed: {value!r}')
        return value

    if not isinstance(value, str):
        raise ValueError(f'cannot parse sensible int from {type(value).__name__}: {value!r}')

    text = value.strip()
    if not text:
        raise ValueError(f'cannot parse sensible int from empty value: {value!r}')

    if text.startswith('-'):
        raise ValueError(f'negative values are not allowed: {value!r}')

    # Split off an optional trailing magnitude suffix (alphabetic).
    multiplier = 1
    numeric_part = text
    last = text[-1]
    if last.isalpha():
        suffix = last.upper()
        if suffix not in _MULTIPLIERS:
            raise ValueError(f'unknown magnitude suffix in {value!r}: {last!r}')
        multiplier = _MULTIPLIERS[suffix]
        numeric_part = text[:-1].strip()
        if not numeric_part:
            raise ValueError(f'magnitude suffix without a number in {value!r}')

    # Underscore grouping is only meaningful for plain integer literals;
    # it would be ambiguous around a decimal mantissa, so allow it only
    # when there is no decimal point.
    if '_' in numeric_part:
        if '.' in numeric_part:
            raise ValueError(f'cannot mix underscore grouping with a decimal point in {value!r}')
        numeric_part = numeric_part.replace('_', '')

    try:
        magnitude = Decimal(numeric_part)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f'cannot parse sensible int from {value!r}') from exc

    if magnitude < 0:
        raise ValueError(f'negative values are not allowed: {value!r}')

    product = magnitude * multiplier
    if product != product.to_integral_value():
        raise ValueError(f'value does not resolve to a whole number: {value!r}')

    return int(product)
