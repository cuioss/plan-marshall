# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_manage_status_transition_fixtures import _lifecycle, load_script_module


def test_carry_back_vocabulary_agrees_with_restore_from_plan(plan_context):
    """The relationship is a STRICT superset by exactly one value.

    ``CARRY_BACK_ACTIONS`` is now DERIVED as
    ``RESTORE_ACTIONS | {'not_attempted'}``, so "the shared four agree" holds by
    construction and asserting it here would be vacuous. What the construction
    does NOT guarantee is that the union is strict: were ``not_attempted`` ever
    added upstream to ``RESTORE_ACTIONS``, the union would silently become a
    no-op and the two surfaces would claim the false identity the docstring
    explicitly warns against. The strictness and the exact-by-one cardinality
    are what this test pins — they also catch a regression to re-listed
    literals that drop or gain a member.
    """
    lessons_query = load_script_module(
        'plan-marshall', 'manage-lessons', '_lessons_query.py', '_transition_lessons_query'
    )

    # The one thing the union cannot enforce about itself: that it adds a value.
    assert 'not_attempted' not in lessons_query.RESTORE_ACTIONS, (
        'not_attempted leaked into RESTORE_ACTIONS, collapsing the union into a '
        'no-op and making the two vocabularies equal — the identity claim the '
        'CARRY_BACK_ACTIONS docstring exists to deny.'
    )
    assert len(_lifecycle.CARRY_BACK_ACTIONS) == len(lessons_query.RESTORE_ACTIONS) + 1
    assert _lifecycle.CARRY_BACK_ACTIONS > lessons_query.RESTORE_ACTIONS

    # ``restored`` is the value the two used to define incompatibly.
    assert 'restored' in _lifecycle.CARRY_BACK_ACTIONS
    assert 'restore_incomplete' in _lifecycle.CARRY_BACK_ACTIONS
