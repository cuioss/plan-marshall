#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the format_tokens_short helper in file_ops.py.

Covers small, K-suffix, M-suffix, edge cases, and trailing .0 trim.
"""

import pytest
from file_ops import format_tokens_short


class TestFormatTokensShortSmall:
    """Values below the K threshold render as plain integer strings."""

    @pytest.mark.parametrize(
        'value,expected',
        [
            (0, '0'),
            (1, '1'),
            (42, '42'),
            (999, '999'),
        ],
    )
    def test_small_values_render_plain(self, value, expected):
        assert format_tokens_short(value) == expected


class TestFormatTokensShortKSuffix:
    """Values in [1_000, 1_000_000) render with the K suffix."""

    @pytest.mark.parametrize(
        'value,expected',
        [
            (1_000, '1K'),
            (1_500, '1.5K'),
            (12_000, '12K'),
            (12_500, '12.5K'),
            (599_089, '599.1K'),
            (999_999, '1000K'),
        ],
    )
    def test_thousand_values_use_k_suffix(self, value, expected):
        assert format_tokens_short(value) == expected

    def test_trailing_zero_is_trimmed_for_round_thousands(self):
        # 12000 / 1000 = 12.0 -> trim to "12K", not "12.0K".
        assert format_tokens_short(12_000) == '12K'

    def test_trailing_zero_preserved_for_non_round_thousands(self):
        # 12500 / 1000 = 12.5 -> "12.5K", no trim.
        assert format_tokens_short(12_500) == '12.5K'


class TestFormatTokensShortMSuffix:
    """Values >= 1_000_000 render with the M suffix."""

    @pytest.mark.parametrize(
        'value,expected',
        [
            (1_000_000, '1M'),
            (1_200_000, '1.2M'),
            (1_500_000, '1.5M'),
            (12_000_000, '12M'),
            (12_345_678, '12.3M'),
        ],
    )
    def test_million_values_use_m_suffix(self, value, expected):
        assert format_tokens_short(value) == expected


class TestFormatTokensShortEdgeCases:
    """Edge cases: negative input is clamped to zero."""

    @pytest.mark.parametrize('value', [-1, -1_000, -999_999])
    def test_negative_values_clamp_to_zero(self, value):
        assert format_tokens_short(value) == '0'
