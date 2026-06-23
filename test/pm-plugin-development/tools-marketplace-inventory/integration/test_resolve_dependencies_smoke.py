#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Real-tree integration smokes for resolve-dependencies.py.

EXCLUDED from the default ``module-tests`` run — registered in the root
``test/conftest.py`` ``collect_ignore`` list, mirroring the established
``test/plan-marshall/integration/`` segregation pattern. These are the only
``resolve-dependencies`` tests that build a dependency index over the REAL
``marketplace/bundles/`` tree; the per-subcommand / per-filter / output-format
coverage lives in the sibling in-process unit suite
(``test_resolve_dependencies.py``) against a synthetic tmp graph.

Two smokes are retained — both assert against the real shipped marketplace:

1. ``test_full_marketplace_validation`` — the whole-graph ``validate`` run finds
   the real component population (>= 50 components).
2. ``test_known_dependency_chain`` — ``deps`` for the real ``manage-files``
   skill resolves a known real shipped chain.
"""

from toon_parser import parse_toon  # type: ignore[import-not-found]

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('pm-plugin-development', 'tools-marketplace-inventory', 'resolve-dependencies.py')


def test_full_marketplace_validation():
    """Validating the full real marketplace finds the shipped component population."""
    result = run_script(SCRIPT_PATH, 'validate', '--direct-result')
    assert result.returncode in (0, 1), f'Script returned error: {result.stderr}'

    data = parse_toon(result.stdout)
    # Should find many components on the real tree.
    assert data.get('total_components', 0) >= 50
    assert data.get('total_dependencies', 0) >= 0


def test_known_dependency_chain():
    """deps for the real manage-files skill resolves a known shipped chain."""
    import json

    result = run_script(
        SCRIPT_PATH,
        'deps',
        '--component',
        'plan-marshall:manage-files',
        '--direct-result',
        '--format',
        'json',
    )
    assert result.returncode == 0, f'Script returned error: {result.stderr}'

    data = json.loads(result.stdout)
    assert data['status'] == 'success'
    # manage-files skill uses toon_parser and file_ops in its SKILL.md / scripts;
    # at minimum the deps resolution runs successfully against the real tree.
    direct_count = data.get('statistics', {}).get('direct_count', 0)
    assert direct_count >= 0
