#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""CI-provider discovery REPORTS its failures; it never raises out of a parametrize source.

``_ci_provider_population.discover_ci_provider_skills`` is called at module import
by both body-fidelity suites, because a parametrize source needs its result before
any test body runs. An exception escaping it there is not one failing test: it is a
collection error that removes the whole module, including the ``population_defect``
assertion whose entire job is to EXPLAIN a discovery problem in words.

The boundary therefore has to cover every step that touches the scan's data, not
only the call that produced it. Discovery imports arbitrary ``*_provider.py``
modules and returns whatever their ``get_provider_declarations()`` handed back, so
the normalisation that reads ``skill_name`` off those declarations is as exposed to
a malformed one as the scan itself.

The arms are a matched set: the failing ones pin that a malformed declaration is
reported, the stubbed success pins that a well-formed scan is still normalised into
the sorted, unique tuple the suites parametrize over, and the unstubbed arm pins
that the function still reads the real tree — without which all three stub arms
would pass over a discovery that had stopped working entirely.
"""

from __future__ import annotations

import sys
import types

import pytest
from _ci_provider_population import CI_CATEGORY, discover_ci_provider_skills


@pytest.fixture
def declaring(monkeypatch):
    """Return a setter that makes discovery yield the given declarations.

    ``discover_ci_provider_skills`` resolves ``_list_providers`` by bare name from
    inside its own ``try``, so standing a stub module in ``sys.modules`` is what
    the real code path reads — the same substitution shape the rate-window suite
    uses for ``merge_lock``, and one that needs no assumption about where the real
    module sits on ``sys.path``.
    """

    def _declare(declarations):
        stub = types.ModuleType('_list_providers')
        stub.find_full_providers_by_category = lambda _category: declarations
        monkeypatch.setitem(sys.modules, '_list_providers', stub)

    return _declare


@pytest.mark.parametrize(
    'declarations,expected_error,reason',
    [
        (
            [{'skill_name': ['a-list', 'not-a-name']}],
            'TypeError',
            'an unhashable skill_name breaks the set construction',
        ),
        (
            [{'skill_name': 'plain'}, {'skill_name': 7}],
            'TypeError',
            'a mixed-type skill_name breaks the sort',
        ),
        (
            [{'skill_name': 7}],
            'TypeError',
            'a LONE non-string skill_name is malformed too — set and sort both '
            'succeed over a single homogeneous scalar, so nothing downstream '
            'would have caught it and the declared tuple[str, ...] would ship a 7',
        ),
        (
            ['not-a-mapping'],
            'AttributeError',
            'a declaration that is not a mapping has no .get at all',
        ),
    ],
)
def test_a_malformed_declaration_is_reported_rather_than_raised(declaring, declarations, expected_error, reason):
    """A provider module that declares nonsense yields a failure string, not an exception.

    ``pytest.raises`` is deliberately absent: the assertion is that NOTHING
    propagates. The returned population is empty and the failure names the
    exception type, so ``population_defect`` can say the cases below it are vacuous
    instead of the suite disappearing before it can say anything.
    """
    declaring(declarations)

    skills, failure = discover_ci_provider_skills()

    assert skills == (), reason
    assert failure.startswith(f'{expected_error}: '), (
        f'the failure must name the exception so the defect message explains itself, got {failure!r}'
    )


def test_a_well_formed_scan_is_still_normalised_into_a_sorted_unique_tuple(declaring):
    """MATCHED CONTROL — moving the normalisation inside the boundary did not disable it.

    Declarations without a ``skill_name`` are dropped, duplicates collapse, and the
    result is ordered, because both body-fidelity suites parametrize over this
    tuple and a reordering would silently re-key their arms.
    """
    declaring(
        [
            {'skill_name': 'plan-marshall:workflow-integration-gitlab'},
            {'skill_name': 'plan-marshall:workflow-integration-github'},
            {'skill_name': 'plan-marshall:workflow-integration-github'},
            {'category': CI_CATEGORY},
            {'skill_name': ''},
        ]
    )

    skills, failure = discover_ci_provider_skills()

    assert failure == ''
    assert skills == (
        'plan-marshall:workflow-integration-github',
        'plan-marshall:workflow-integration-gitlab',
    )


def test_the_real_tree_still_discovers_its_ci_providers():
    """MATCHED CONTROL for the stubs — the unpatched path reads the actual tree.

    Every arm above drives a stub, so all of them would pass over a function that
    had stopped resolving ``_list_providers`` at all. This one asserts the
    production resolution the two body-fidelity suites parametrize on, at the parity
    floor those suites require.
    """
    skills, failure = discover_ci_provider_skills()

    assert failure == '', f'CI-provider discovery failed against the real tree — {failure}'
    assert len(skills) >= 2, f'the tree declares fewer CI providers than parity needs: {list(skills)}'
