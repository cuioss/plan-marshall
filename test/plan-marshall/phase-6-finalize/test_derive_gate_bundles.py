#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Regression tests for the ``derive_gate_bundles`` pre-push-quality-gate seam.

The seam at ``phase-6-finalize/scripts/derive_gate_bundles.py`` replaces the
former four-rule prose in ``standards/pre-push-quality-gate.md`` "Derive unique
bundle set" section. These tests pin the deliverable's Success Criteria against
the **real** ``marketplace/bundles/`` tree (via ``conftest.MARKETPLACE_ROOT``)
so the "is a real bundle directory" predicate is exercised, not stubbed:

* The exact reported path shape ``test/marketplace/targets/test_frontmatter.py``
  derives **no** ``marketplace`` bundle and contributes exactly one
  ``unresolved[]`` entry — the phantom-bundle regression (D1).
* ``test/plan-marshall/…`` → ``plan-marshall`` (the second segment names a real
  bundle).
* ``marketplace/bundles/plan-marshall/…`` → ``plan-marshall``.
* A mixed footprint yields a sorted, de-duplicated bundle set.
* A path matching no build_map glob contributes nothing (neither a bundle nor
  an ``unresolved[]`` entry).

The module lives alongside the 14 pre-existing non-package test modules in
``test/plan-marshall/phase-6-finalize/`` — no ``__init__.py`` is added, and a
guard test pins that the directory remains a non-package directory.
"""

from __future__ import annotations

from pathlib import Path

from conftest import (
    MARKETPLACE_ROOT,
    PROJECT_ROOT,
    get_script_path,
    load_script_module,
    run_script,
)

_mod = load_script_module(
    'plan-marshall', 'phase-6-finalize', 'derive_gate_bundles.py'
)
derive_gate_bundles = _mod.derive_gate_bundles

# Globs broad enough to admit both a bundle-rooted path and a test-rooted path.
# fnmatch ``*`` spans ``/``, so these match any depth beneath the prefix.
_ALL_GLOBS = ['marketplace/bundles/*', 'test/*']


def _as_list(value) -> list:
    """Coerce a TOON-parsed scalar-or-list field into a list."""
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


# ---------------------------------------------------------------------------
# Pure-function tests against the real marketplace/bundles/ tree
# ---------------------------------------------------------------------------


def test_test_marketplace_path_yields_no_bundle_and_one_unresolved():
    # Arrange — the exact reported phantom-bundle path shape.
    files = ['test/marketplace/targets/test_frontmatter.py']

    # Act
    bundles, unresolved = derive_gate_bundles(files, ['test/*'], MARKETPLACE_ROOT)

    # Assert — no phantom ``marketplace`` bundle; the path is diagnosable, not dropped.
    assert bundles == []
    assert 'marketplace' not in bundles
    assert unresolved == ['test/marketplace/targets/test_frontmatter.py']


def test_test_plan_marshall_path_resolves_to_plan_marshall():
    files = ['test/plan-marshall/phase-6-finalize/test_ci_verify.py']

    bundles, unresolved = derive_gate_bundles(files, ['test/*'], MARKETPLACE_ROOT)

    assert bundles == ['plan-marshall']
    assert unresolved == []


def test_marketplace_bundles_path_resolves_to_bundle():
    files = [
        'marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/foo.py'
    ]

    bundles, unresolved = derive_gate_bundles(
        files, ['marketplace/bundles/*'], MARKETPLACE_ROOT
    )

    assert bundles == ['plan-marshall']
    assert unresolved == []


def test_mixed_footprint_yields_sorted_deduplicated_set():
    # Arrange — two distinct real bundles across both path shapes, plus a
    # duplicate ``plan-marshall`` contribution that must collapse.
    files = [
        'marketplace/bundles/pm-dev-java/skills/java-core/scripts/foo.py',
        'test/plan-marshall/phase-6-finalize/test_bar.py',
        'marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/baz.py',
        'test/plan-marshall/phase-6-finalize/test_qux.py',
    ]

    # Act
    bundles, unresolved = derive_gate_bundles(files, _ALL_GLOBS, MARKETPLACE_ROOT)

    # Assert — sorted and de-duplicated ('plan-marshall' < 'pm-dev-java').
    assert bundles == ['plan-marshall', 'pm-dev-java']
    assert bundles == sorted(bundles)
    assert unresolved == []


def test_non_matching_glob_entry_contributes_nothing():
    files = ['doc/developer/build.adoc']

    bundles, unresolved = derive_gate_bundles(files, _ALL_GLOBS, MARKETPLACE_ROOT)

    assert bundles == []
    assert unresolved == []


def test_full_mixed_footprint_partitions_correctly():
    # Arrange — one of each class: real bundle-rooted, real test-rooted,
    # phantom test-rooted (unresolved), and non-matching (dropped).
    files = [
        'marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/x.py',
        'test/pm-dev-java/junit-core/test_y.py',
        'test/marketplace/targets/test_frontmatter.py',
        'README.md',
    ]

    bundles, unresolved = derive_gate_bundles(files, _ALL_GLOBS, MARKETPLACE_ROOT)

    assert bundles == ['plan-marshall', 'pm-dev-java']
    assert unresolved == ['test/marketplace/targets/test_frontmatter.py']


# ---------------------------------------------------------------------------
# CLI / TOON output-contract smoke against the executor entry point
# ---------------------------------------------------------------------------


def test_cli_emits_toon_bundles_and_unresolved():
    script = get_script_path('plan-marshall', 'phase-6-finalize', 'derive_gate_bundles.py')

    result = run_script(
        script,
        'derive',
        '--files',
        'test/marketplace/targets/test_frontmatter.py,'
        'test/plan-marshall/test_bar.py,'
        'marketplace/bundles/pm-dev-java/skills/foo.py',
        '--globs',
        'test/*,marketplace/bundles/*',
        '--marketplace-root',
        str(PROJECT_ROOT),
    )

    assert result.success, result.stderr
    data = result.toon()
    assert data['status'] == 'success'
    assert _as_list(data['bundles']) == ['plan-marshall', 'pm-dev-java']
    assert _as_list(data['unresolved']) == [
        'test/marketplace/targets/test_frontmatter.py'
    ]


# ---------------------------------------------------------------------------
# Non-package directory guard
# ---------------------------------------------------------------------------


def test_test_directory_remains_non_package():
    # The directory is an established non-package test directory; adding an
    # ``__init__.py`` would change collection semantics for its 14+ siblings.
    test_dir = Path(__file__).parent
    assert not (test_dir / '__init__.py').exists()
