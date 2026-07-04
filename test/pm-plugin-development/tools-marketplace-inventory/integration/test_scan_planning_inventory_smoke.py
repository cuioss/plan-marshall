#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Real-tree integration smoke for scan-planning-inventory.py.

EXCLUDED from the default ``module-tests`` run — registered in the root
``test/conftest.py`` ``collect_ignore`` list, mirroring the established
``test/plan-marshall/integration/`` segregation pattern. This is the only
planning-scan test that walks the REAL ``marketplace/bundles/`` tree (the
script spawns ``scan-marketplace-inventory.py`` against it). The per-filter /
per-field / statistics coverage lives in the sibling in-process unit suite
(``test_scan_planning_inventory.py``) against a synthetic tmp marketplace.

One smoke is retained: an end-to-end real-tree planning scan producing a
``plan-marshall`` core block and ``pm-plugin-development`` in derived.
"""

from toon_parser import parse_toon

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('pm-plugin-development', 'tools-marketplace-inventory', 'scan-planning-inventory.py')


def test_planning_scan_from_repo_categorizes_core_and_derived():
    """Real-tree planning scan yields a plan-marshall core block + derived plugin bundle."""
    result = run_script(SCRIPT_PATH)
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = parse_toon(result.stdout)

    core = data.get('core', {})
    assert core.get('bundle') == 'plan-marshall', f"Core bundle should be 'plan-marshall', got {core.get('bundle')}"
    assert len(core.get('skills', [])) > 0, 'Core should have planning skills on the real tree'

    derived = data.get('derived', [])
    bundle_names = [d['bundle'] for d in derived]
    assert 'pm-plugin-development' in bundle_names, (
        f'Derived should include pm-plugin-development, got {bundle_names}'
    )
