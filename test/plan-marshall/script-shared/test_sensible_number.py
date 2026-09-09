# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the sensible_number shared module.

``sensible_number.parse_sensible_int`` is the canonical human-friendly
number parser for config values. These tests pin every accepted form to
its expected int and assert ``ValueError`` on every rejected form, with at
least one test confirming the error message names the offending input.

The module is on the test PYTHONPATH via the conftest auto-discovery of
``script-shared/scripts`` (see ``test/conftest.py``), so the import is a
plain ``from sensible_number import parse_sensible_int``.
"""

import pytest
from sensible_number import parse_sensible_int

#: ``{the id naming the case: (input, the int it must resolve to)}``. The ids come
#: off THIS mapping's own keys rather than being left to pytest, because several
#: rows differ ONLY in the input's type — ``'50000'`` against ``50_000`` and
#: ``'0'`` against ``0`` — and a generated id renders both members of each pair as
#: the same text. pytest then tells them apart by appending an index, so the one
#: distinction those rows exist to draw is the one the report cannot show.
_ACCEPTED_SENSIBLE_INTS = {
    'an-uppercase-thousands-suffix': ('50K', 50_000),
    'a-fractional-millions-suffix': ('1.5M', 1_500_000),
    'a-plain-digit-string': ('50000', 50_000),
    'an-int-that-needs-no-parsing': (50_000, 50_000),
    'an-underscore-grouped-digit-string': ('50_000', 50_000),
    'a-billions-suffix': ('2G', 2_000_000_000),
    'a-lowercase-thousands-suffix': ('50k', 50_000),
    'a-suffixed-value-padded-with-whitespace': ('  50K  ', 50_000),
    'a-lowercase-fractional-millions-suffix': ('1.5m', 1_500_000),
    'zero-as-a-string': ('0', 0),
    'zero-as-an-int': (0, 0),
    'a-fraction-that-divides-cleanly-into-an-int': ('1.5K', 1_500),
}


class TestParseSensibleIntAccepted:
    """Happy path — every accepted form resolves to the correct int."""

    @pytest.mark.parametrize(
        ('value', 'expected'),
        list(_ACCEPTED_SENSIBLE_INTS.values()),
        ids=list(_ACCEPTED_SENSIBLE_INTS),
    )
    def test_accepted_form_resolves_to_int(self, value, expected):
        result = parse_sensible_int(value)

        assert result == expected
        assert isinstance(result, int)


#: ``{the id naming the case: the rejected input}``. Same reason the accepted
#: table states its ids: ``'-5'`` and ``-5`` generate the same text, so the
#: string/int split — the whole point of carrying both — survives only if the id
#: says which one it is. ``True`` is here because ``bool`` is an ``int`` subtype
#: and the parser must still refuse it.
_REJECTED_SENSIBLE_INTS = {
    'an-empty-string': '',
    'a-whitespace-only-string': '   ',
    'none-rather-than-a-value': None,
    'non-numeric-text': 'abc',
    'an-unrecognised-magnitude-suffix': '50T',
    'a-negative-with-a-suffix': '-5K',
    'a-negative-as-a-string': '-5',
    'a-negative-as-an-int': -5,
    'a-suffix-with-digits-trailing-it': '1.5G7',
    'a-bare-suffix-with-no-number': 'K',
    'two-decimal-points': '50.5.5',
    'a-bool-which-is-an-int-subtype': True,
}


class TestParseSensibleIntRejected:
    """Rejection path — every invalid form raises ValueError."""

    @pytest.mark.parametrize(
        'value',
        list(_REJECTED_SENSIBLE_INTS.values()),
        ids=list(_REJECTED_SENSIBLE_INTS),
    )
    def test_rejected_form_raises_value_error(self, value):
        with pytest.raises(ValueError):
            parse_sensible_int(value)

    def test_fractional_result_is_rejected(self):
        # 1.5 with no suffix does not divide cleanly into an int.
        with pytest.raises(ValueError):
            parse_sensible_int('1.5')

    def test_error_message_names_offending_input(self):
        offending = '50T'

        with pytest.raises(ValueError) as exc_info:
            parse_sensible_int(offending)

        assert '50T' in str(exc_info.value)

    def test_error_message_names_garbage_input(self):
        offending = 'totally-not-a-number'

        with pytest.raises(ValueError) as exc_info:
            parse_sensible_int(offending)

        assert offending in str(exc_info.value)
