# SPDX-License-Identifier: FSL-1.1-ALv2
"""parse_ns applies the parser defaults the caller did not name.

The property under test is why :func:`conftest.parse_ns` exists instead of a
hand-built ``argparse.Namespace``.
"""

import argparse

from _shared_harness_fixtures import (
    _DEFAULTS_ARGV,
    _DEFAULTS_CASE,
    _UNNAMED_DEFAULTS,
)
from conftest import parse_ns


def test_parse_ns_applies_defaults_the_caller_did_not_name():
    """The namespace carries parser defaults for flags the caller never passed."""
    ns = parse_ns(*_DEFAULTS_CASE, *_DEFAULTS_ARGV)

    assert ns.command == 'list'
    assert ns.plan_id == 'p1'
    # A store_true flag defaults to a real value, not to absence.
    assert ns.include_qgate is False
    missing = [name for name in _UNNAMED_DEFAULTS if not hasattr(ns, name)]
    assert missing == [], f'parse_ns dropped parser defaults the CLI would apply: {missing}'


def test_hand_built_namespace_lacks_the_defaults_parse_ns_supplies():
    """The defect parse_ns closes, stated as a test.

    A hand-built namespace carries only what its author remembered. This is the
    control that makes the test above meaningful: without it, a `parse_ns` that
    happened to return a namespace with every attribute set would look identical
    to one that returned a hand-built guess.
    """
    hand_built = argparse.Namespace(command='list', plan_id='p1')

    assert not hasattr(hand_built, 'include_qgate')
    assert [name for name in _UNNAMED_DEFAULTS if not hasattr(hand_built, name)] == list(_UNNAMED_DEFAULTS)
