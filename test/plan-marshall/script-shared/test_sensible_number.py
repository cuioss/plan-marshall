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


class TestParseSensibleIntAccepted:
    """Happy path — every accepted form resolves to the correct int."""

    @pytest.mark.parametrize(
        ('value', 'expected'),
        [
            ('50K', 50_000),
            ('1.5M', 1_500_000),
            ('50000', 50_000),
            (50_000, 50_000),
            ('50_000', 50_000),
            ('2G', 2_000_000_000),
            ('50k', 50_000),
            ('  50K  ', 50_000),
            ('1.5m', 1_500_000),
            ('0', 0),
            (0, 0),
            ('1.5K', 1_500),
        ],
    )
    def test_accepted_form_resolves_to_int(self, value, expected):
        result = parse_sensible_int(value)

        assert result == expected
        assert isinstance(result, int)


class TestParseSensibleIntRejected:
    """Rejection path — every invalid form raises ValueError."""

    @pytest.mark.parametrize(
        'value',
        [
            '',
            '   ',
            None,
            'abc',
            '50T',
            '-5K',
            '-5',
            -5,
            '1.5G7',
            'K',
            '50.5.5',
            True,
        ],
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
