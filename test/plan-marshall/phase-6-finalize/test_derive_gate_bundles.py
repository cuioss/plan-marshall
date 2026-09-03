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
* A path that DID match a build_map glob but is of any other shape — the
  consumer-layout case — lands in ``unresolved[]`` rather than being dropped
  (rule 4). That contrast with the bullet above is the point: "matched no glob"
  and "matched a glob but resolves to no bundle" are different answers, and
  only the second is diagnosable.

This module is the **sole owner** of the rule-4 behavioural pair — the
consumer-shaped negative AND its matched positive control. The control is not
optional: a test asserting only the negative would pass just as well against a
seam that routed *everything* to ``unresolved``. Deliverable 6's
``test_gate_derivation_diagnosability.py`` covers the disjoint contract-text
dimension and must not re-assert this pair.

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
# Rule 4 — the consumer-layout shape is REPORTED, not dropped.
#
# This section owns the behavioural pair. Each negative below is stated
# together with a positive control, because a seam that routed every path to
# ``unresolved`` would satisfy the negatives alone.
# ---------------------------------------------------------------------------


def test_consumer_shaped_glob_matching_path_lands_in_unresolved():
    # Arrange — a consumer project's source path. It matches the project's own
    # registered build_map glob, so the project declared it build-relevant, but
    # it is neither ``marketplace/bundles/<b>/…`` nor ``test/<b>/…``.
    files = ['src/main/java/com/example/Foo.java']

    # Act
    bundles, unresolved = derive_gate_bundles(files, ['src/*'], MARKETPLACE_ROOT)

    # Assert — no bundle, and the path is REPORTED rather than silently dropped.
    # An empty ``unresolved`` here is the defect: it left the gate's per-bundle
    # loop with nothing to iterate and nothing to say about why.
    assert bundles == []
    assert unresolved == ['src/main/java/com/example/Foo.java']


def test_whole_consumer_footprint_is_reported_not_silently_green():
    # Arrange — the real-world shape: a consumer project whose every build-
    # relevant path is of a layout this seam cannot resolve.
    files = [
        'src/main/java/com/example/Foo.java',
        'src/main/java/com/example/Bar.java',
        'lib/widget.py',
    ]

    # Act
    bundles, unresolved = derive_gate_bundles(files, ['*'], MARKETPLACE_ROOT)

    # Assert — the pre-fix seam returned ([], []) here, so the gate's per-bundle
    # loop iterated zero times and reported green. Every path is now accounted
    # for, in footprint order.
    assert bundles == []
    assert unresolved == files


def test_tests_plural_root_is_unresolved_not_a_phantom_bundle():
    # Arrange — ``tests/`` is NOT ``test/``; the prefix must not match loosely
    # and must not derive ``foo`` as a bundle from segment 1.
    files = ['tests/foo/test_bar.py']

    # Act
    bundles, unresolved = derive_gate_bundles(files, ['tests/*'], MARKETPLACE_ROOT)

    # Assert
    assert bundles == []
    assert unresolved == ['tests/foo/test_bar.py']


def test_rule_four_negative_with_matched_positive_control():
    # Arrange — the pair in ONE act, which is what makes each half falsifiable:
    # a consumer-shaped path, a real bundle-rooted path, and a real test-rooted
    # path whose bundle directory exists on disk.
    files = [
        'src/main/java/com/example/Foo.java',
        'marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/x.py',
        'test/pm-dev-java/junit-core/test_y.py',
    ]

    # Act
    bundles, unresolved = derive_gate_bundles(
        files, ['src/*', 'marketplace/bundles/*', 'test/*'], MARKETPLACE_ROOT
    )

    # Assert — POSITIVE CONTROL: both resolvable shapes still resolve, and
    # neither leaked into ``unresolved``. Without this half, a seam that routed
    # everything to ``unresolved`` would pass the negative above.
    assert bundles == ['plan-marshall', 'pm-dev-java']
    assert 'marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/x.py' \
        not in unresolved
    assert 'test/pm-dev-java/junit-core/test_y.py' not in unresolved

    # Assert — NEGATIVE: only the consumer-shaped path is reported.
    assert unresolved == ['src/main/java/com/example/Foo.java']


def test_unmatched_glob_and_rule_four_are_different_answers():
    # Arrange — two paths of the same unresolvable shape. Only one is admitted
    # by the globs, so the glob filter (rule 1) and rule 4 must be visibly
    # distinguishable rather than collapsing into one silent outcome.
    files = ['src/main/java/com/example/Foo.java', 'doc/developer/build.adoc']

    # Act
    bundles, unresolved = derive_gate_bundles(files, ['src/*'], MARKETPLACE_ROOT)

    # Assert — the glob-matching path is diagnosable; the non-matching one is
    # genuinely out of remit and stays absent from BOTH lists.
    assert bundles == []
    assert unresolved == ['src/main/java/com/example/Foo.java']
    assert 'doc/developer/build.adoc' not in unresolved


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
