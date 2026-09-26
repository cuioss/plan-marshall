# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_classify_paths_via_extensions_fixtures import (
    _INFRA_ONLY_FOOTPRINT,
    _classify_paths_via_extensions,
    _real_build_extensions,
)


def test_d3b_infra_only_footprint_falsifies_the_phase_4_qgate_blocking_predicate():
    """D3(b): an infra-only plan clears the phase-4 Q-Gate without an operator override.

    The Q-Gate's blocking predicate is exactly ``bucket == 'unknown'``
    (equivalently: a non-empty ``unclaimed`` list) — that is the sole condition
    under which the ``unknown`` remedy fires and an operator override is
    demanded. Falsifying BOTH halves of that predicate here IS the Q-Gate
    outcome, not a proxy for it.

    The run uses the REAL discovered extension set rather than the
    ``_FakeExtension`` fixtures the sibling cases use: a fake-extension
    assertion could pass while the shipped extension set still leaves these
    paths unclaimed. The non-empty-extensions assertion keeps the case from
    passing vacuously if discovery ever returns nothing.
    """
    extensions = _real_build_extensions()
    assert extensions, 'discover_build_extensions() returned no build extensions'

    bucket, unclaimed = _classify_paths_via_extensions(list(_INFRA_ONLY_FOOTPRINT), extensions=extensions)
    assert bucket != 'unknown'
    assert unclaimed == []
