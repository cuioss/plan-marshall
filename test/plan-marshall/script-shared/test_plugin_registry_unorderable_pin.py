# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for how classify_parity treats a pinned field that carries no digits."""

import pytest
from plugin_registry import PARITY_BEHIND, PARITY_UNREADABLE, classify_parity

REFERENCE = '0.1.1069'
OLDER = '0.1.999'
NEWER = '0.1.1070'
DIGIT_FREE = 'latest'


def _row(install_path_version: str, version: str) -> dict[str, str | None]:
    return {
        'bundle': 'plan-marshall',
        'scope': 'user',
        'install_path_version': install_path_version,
        'version': version,
    }


@pytest.mark.parametrize(
    ('install_path_version', 'version', 'expected'),
    [
        (DIGIT_FREE, REFERENCE, PARITY_UNREADABLE),
        (REFERENCE, DIGIT_FREE, PARITY_UNREADABLE),
        (DIGIT_FREE, DIGIT_FREE, PARITY_UNREADABLE),
        (DIGIT_FREE, NEWER, PARITY_UNREADABLE),
        (DIGIT_FREE, OLDER, PARITY_BEHIND),
        (OLDER, DIGIT_FREE, PARITY_BEHIND),
    ],
    ids=[
        'digit-free-install-path-version',
        'digit-free-version-field',
        'both-fields-digit-free',
        'digit-free-beside-newer',
        'digit-free-beside-older-version-field',
        'digit-free-beside-older-install-path-version',
    ],
)
def test_classify_parity_digit_free_pin(install_path_version, version, expected):
    assert classify_parity([_row(install_path_version, version)], REFERENCE) == expected
