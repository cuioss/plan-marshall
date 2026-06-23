#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Real-tree integration smokes for scan-marketplace-inventory.py.

EXCLUDED from the default ``module-tests`` run — registered in the root
``test/conftest.py`` ``collect_ignore`` list, mirroring the established
``test/plan-marshall/integration/`` segregation pattern. These are the only
tests that walk the REAL ``marketplace/bundles/`` tree (or shell ``find`` over
it); the per-filter / per-field / content-filtering coverage lives in the
sibling in-process unit suite (``test_scan_marketplace_inventory.py``) against a
synthetic tmp marketplace.

Two smokes are retained:

1. ``test_scan_from_repo_produces_single_plan_marshall_block`` — end-to-end
   subprocess scan of the real tree, anchored on git-root resolution, producing
   exactly one ``plan-marshall`` block whose path references
   ``marketplace/bundles`` (source, not cache).
2. ``test_script_count_matches_filesystem`` — relocated filesystem cross-check
   that the inventory's ``total_scripts`` equals the ``find``-counted public
   ``.py``/``.sh`` files under ``*/skills/*/scripts/*`` on the real tree.
"""

import subprocess
from pathlib import Path

from toon_parser import parse_toon  # type: ignore[import-not-found]

from conftest import get_script_path, run_script

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent
SCRIPT_PATH = get_script_path('pm-plugin-development', 'tools-marketplace-inventory', 'scan-marketplace-inventory.py')

METADATA_KEYS = {
    'status',
    'scope',
    'base_path',
    'statistics',
    'content_filter_stats',
    'content_pattern',
    'content_exclude',
}


def _get_bundles(data: dict) -> list[dict]:
    return [{'name': k, **v} for k, v in data.items() if k not in METADATA_KEYS and isinstance(v, dict)]


def test_scan_from_repo_produces_single_plan_marshall_block():
    """End-to-end real-tree scan with --bundles plan-marshall produces one block."""
    result = run_script(SCRIPT_PATH, '--direct-result', '--bundles', 'plan-marshall')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = parse_toon(result.stdout)
    bundles = _get_bundles(data)
    assert len(bundles) == 1, f'Should produce exactly 1 plan-marshall block, found {len(bundles)}'
    assert bundles[0]['name'] == 'plan-marshall', f"Bundle name should be 'plan-marshall', got '{bundles[0]['name']}'"

    bundle_path = bundles[0].get('path', '')
    assert 'marketplace/bundles' in bundle_path, (
        f'Bundle path should reference marketplace/bundles (source), got: {bundle_path}'
    )


def test_script_count_matches_filesystem():
    """Inventory total_scripts equals the filesystem public-script count (real tree)."""
    find_result = subprocess.run(
        [
            'find',
            str(PROJECT_ROOT / 'marketplace' / 'bundles'),
            '-path',
            '*/skills/*/scripts/*',
            '-type',
            'f',
            '(',
            '-name',
            '*.sh',
            '-o',
            '-name',
            '*.py',
            ')',
        ],
        capture_output=True,
        text=True,
    )
    all_files = [line for line in find_result.stdout.strip().split('\n') if line]
    public_files = [f for f in all_files if not Path(f).name.startswith('_')]
    expected_count = len(public_files)

    result = run_script(SCRIPT_PATH, '--direct-result')
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = parse_toon(result.stdout)
    actual_count = data.get('statistics', {}).get('total_scripts', 0)

    assert actual_count == expected_count, f'Script count mismatch: expected {expected_count}, got {actual_count}'
