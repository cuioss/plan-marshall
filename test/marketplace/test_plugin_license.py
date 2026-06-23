# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests asserting every bundle plugin.json declares the FSL license.

The license revert (AGPL-3.0-only -> FSL-1.1-ALv2) must be reflected in every
bundle manifest. This test reads all bundle ``plugin.json`` files under
``marketplace/bundles/*/.claude-plugin/`` and asserts each declares
``"license": "FSL-1.1-ALv2"``. It fails if any manifest declares a different
license or if the count of discovered manifests is not the expected 10.
"""

import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BUNDLES_DIR = PROJECT_ROOT / 'marketplace' / 'bundles'

EXPECTED_LICENSE = 'FSL-1.1-ALv2'
EXPECTED_MANIFEST_COUNT = 10


def _bundle_manifests() -> list[Path]:
    """Return the sorted list of bundle plugin.json manifest paths."""
    return sorted(BUNDLES_DIR.glob('*/.claude-plugin/plugin.json'))


def test_expected_number_of_bundle_manifests():
    manifests = _bundle_manifests()

    assert len(manifests) == EXPECTED_MANIFEST_COUNT, (
        f'expected {EXPECTED_MANIFEST_COUNT} bundle plugin.json manifests, '
        f'found {len(manifests)}: {[str(m.relative_to(PROJECT_ROOT)) for m in manifests]}'
    )


@pytest.mark.parametrize('manifest', _bundle_manifests(), ids=lambda p: p.parent.parent.name)
def test_bundle_manifest_declares_fsl_license(manifest):
    data = json.loads(manifest.read_text(encoding='utf-8'))

    assert data.get('license') == EXPECTED_LICENSE, (
        f'{manifest.relative_to(PROJECT_ROOT)} declares license '
        f'{data.get("license")!r}, expected {EXPECTED_LICENSE!r}'
    )
