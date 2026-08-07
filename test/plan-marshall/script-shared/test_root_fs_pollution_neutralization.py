#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Proof that the ``/nonexistent`` absence assumption is guaranteed BY THE
GUARD, not by the host happening to run unprivileged.

The autouse ``_root_fs_pollution_guard`` fixture in ``test/conftest.py`` clears
the ``/nonexistent`` filesystem-root sentinel before every test and fails any
test that materializes it. A guard like that is easy to believe and hard to
check: if it silently stopped engaging, every existence-probe test it protects
would keep passing on an UNPRIVILEGED host (where ``/nonexistent`` can never be
created anyway), and the regression would surface only as ambient cross-test
pollution on a ROOT host — precisely the sandbox-only failure the guard exists
to prevent.

The two tests below are a MATCHED PAIR and are the standing check on that. They
drive the guard's decision core, ``conftest._root_fs_leak_violation``, with a
SIMULATED ``(before, after)`` snapshot in which the sentinel appeared during the
test — the state the guard suppresses — so neither arm depends on the host being
root to create the sentinel for real:

* **Positive arm** — the guard is engaged (the test carries no opt-out marker,
  its default). Given a simulated leak, the guard MUST report a violation.
* **Negative control** — the identical simulated leak, but the test carries
  ``@pytest.mark.allow_root_filesystem_pollution`` so the guard disengages. The
  guard must now report NO violation (the leak is allowed through).

DELETING OR WEAKENING EITHER ARM SILENTLY VOIDS THE OTHER'S EVIDENTIARY VALUE.
The positive arm alone cannot distinguish "the guard flags leaks" from "this
``(before, after)`` can never occur"; the negative control alone proves only
that the marker suppresses flagging, not that anything is flagged by default.
Only the contrast between two otherwise-identical simulated leaks attributes the
outcome to the marker.

Both arms pass ``before=False, after=True`` — the sentinel absent at test start
and present at test end — which is the exact leak signature a root host produces
when a test hands ``/nonexistent/...`` to a creating operation. Neither arm
writes to ``/`` and neither depends on the process's uid, so both are honest and
neither may be skipped.
"""

from __future__ import annotations

import pytest

import conftest


def test_root_fs_leak_is_flagged_when_guard_engaged(request) -> None:
    """POSITIVE ARM — the engaged guard flags a simulated sentinel leak.

    Pairs with ``test_root_fs_leak_is_ignored_when_marker_disengages_guard``.
    """
    violation = conftest._root_fs_leak_violation(request.node, before=False, after=True)

    assert violation is not None, (
        'the _root_fs_pollution_guard decision core did not flag a leak for an '
        'un-opted-out test — a root host materializing /nonexistent would go '
        'unattributed and poison every existence-probe test'
    )
    assert 'nonexistent' in violation


@pytest.mark.allow_root_filesystem_pollution
def test_root_fs_leak_is_ignored_when_marker_disengages_guard(request) -> None:
    """NEGATIVE CONTROL — the marker disengages the guard, so the same simulated
    leak is NOT flagged.

    This is what makes the positive arm meaningful: it proves the
    ``(before=False, after=True)`` input genuinely represents a flaggable leak,
    so the positive arm's violation is attributable to the guard being engaged
    rather than to a vacuous input. Pairs with
    ``test_root_fs_leak_is_flagged_when_guard_engaged``.
    """
    violation = conftest._root_fs_leak_violation(request.node, before=False, after=True)

    assert violation is None, (
        'the allow_root_filesystem_pollution marker did not disengage the guard '
        '— a test that owns a real-root write under "/" would still be failed, '
        'so the positive arm proves nothing'
    )
