#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Every recovery ``action`` the selector can publish has a route in the workflow.

``automatic-review/SKILL.md`` consumes ``github_re_review recovery-action``'s
``action`` and routes on it through a table of its own. That table cannot live in
the selector: the branches it names — ``Branch 0`` … ``Branch 5`` — are anchors
this DOCUMENT owns, and a selector that published them would be declaring the
structure of a workflow it knows nothing about. Route metadata therefore stays with
the router.

What the selector DOES own is the action vocabulary, published as
``RECOVERY_ACTIONS`` for exactly this reason. So the failure mode is not the table's
existence but its COMPLETENESS: an action added to the vocabulary and forgotten here
reaches a workflow with no branch to enter, and a branch renumbered out from under
a row sends a live recovery to a heading that no longer exists. Neither shows up in
any test of the selector, because both defects are entirely in the document.

This suite closes both directions, and every population is DERIVED:

* **Totality** — every member of ``RECOVERY_ACTIONS`` is routed. The population is
  the selector's own tuple, so an action added there joins this check with no test
  edit.
* **No phantom route** — every identifier-shaped action the table routes is a real
  member. A row surviving a rename would otherwise route a token nothing can
  publish, which reads as coverage while covering nothing.
* **Live anchors** — every ``Branch N`` a row cites resolves to a ``#### Branch N``
  heading in the same document.

⛔ **No branch number is asserted for any particular action.** Which branch handles
which action is a routing decision this document is free to change; pinning the
pairs would make an intentional restructure fail as though it were a defect. What
is pinned is that the mapping is TOTAL and its targets EXIST.
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

# ``github_ops`` MUST be resolved FIRST: importing ``_github_pr`` before it fails
# outright with a partially-initialised-module ImportError, because the two close
# an import cycle. Reached through ``import_module`` rather than an ``import``
# statement because isort sorts ``_github_pr`` ahead of ``github_ops``, so no
# arrangement of plain imports can express the ordering.
importlib.import_module('github_ops')

import github_re_review  # noqa: E402

from conftest import get_skill_dir  # noqa: E402

_SKILL_MD: Path = get_skill_dir('plan-marshall', 'automatic-review') / 'SKILL.md'

#: The table's header row. Matched as a literal because it IS the locator — a
#: heading-level scan would not find it, since the table sits inside prose rather
#: than under a heading of its own.
_ROUTE_TABLE_HEADER = '| `action` | Branch |'

#: A backticked token that could be an action name. Restricted to the identifier
#: shape so the surrounding prose in a first cell — ``reason: registry_empty``,
#: ``escalate_ask{...}`` — is not mistaken for a routed action.
_ACTION_TOKEN = re.compile(r'`([a-z][a-z_]*)`')

#: A branch citation in a route's target cell, and the heading it must resolve to.
_BRANCH_CITATION = re.compile(r'\bBranch (\d+)\b')
_BRANCH_HEADING = re.compile(r'^#### Branch (\d+)\b', re.MULTILINE)


def _route_rows() -> list[tuple[str, str]]:
    """The route table's ``(action cell, branch cell)`` pairs, in document order.

    The table is delimited by its own header and the first line that is no longer a
    row, rather than by a line count — a count would silently truncate the moment a
    route is added, which is the exact change this suite exists to observe.

    An ABSENT table yields the empty list rather than raising: this runs at import
    time, and an assertion here would surface as a collection error naming a line of
    parsing code instead of as the named failure the vacuity test below reports.
    """
    text = _SKILL_MD.read_text(encoding='utf-8')
    lines = text.splitlines()
    if _ROUTE_TABLE_HEADER not in lines:
        return []

    start = lines.index(_ROUTE_TABLE_HEADER)
    rows: list[tuple[str, str]] = []
    # +2 skips the header and the markdown separator row beneath it.
    for line in lines[start + 2 :]:
        if not line.startswith('|'):
            break
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if len(cells) >= 2:
            rows.append((cells[0], cells[1]))
    return rows


_ROUTE_ROWS = _route_rows()

#: Every identifier-shaped action the table routes, from the FIRST cell only — the
#: target cell names branches and escalation reasons, not actions.
_ROUTED_ACTIONS = {token for action_cell, _target in _ROUTE_ROWS for token in _ACTION_TOKEN.findall(action_cell)}


class TestTheRouteTableIsTotalOverTheSelectorVocabulary:
    """The mapping from published action to workflow branch covers every member."""

    def test_the_populations_are_non_empty_and_publish_their_sizes(self):
        """⛔ Vacuity guard for every derived check below, with both sizes STATED.

        A set comparison between two empty sets is a passing assertion that
        certifies nothing, and both sides here are derived — the vocabulary from the
        selector, the routes from a parsed document. Either coming back empty is a
        broken derivation, not a clean sheet, so both are asserted before anything
        is compared.
        """
        assert github_re_review.RECOVERY_ACTIONS, 'the selector publishes no actions'
        assert _ROUTE_ROWS, (
            f'no route rows parsed from {_SKILL_MD}: no line reads '
            f'{_ROUTE_TABLE_HEADER!r}, so either the table is gone or its shape moved '
            f'and nothing here is routing the selector output'
        )
        assert _ROUTED_ACTIONS, (
            f'{len(_ROUTE_ROWS)} route rows parsed but no action token matched — the '
            f'table shape changed and this suite is no longer reading it'
        )

    def test_every_published_action_is_routed(self):
        """The load-bearing direction: an action with no branch has nowhere to go.

        The population is the selector's OWN ``RECOVERY_ACTIONS``, so an arm added
        there fails here until the workflow gains a route for it — which is the
        whole point, since the workflow is where an unrouted action becomes a
        recovery that stops mid-sequence.
        """
        unrouted = set(github_re_review.RECOVERY_ACTIONS) - _ROUTED_ACTIONS

        assert not unrouted, (
            f'{sorted(unrouted)} are published by resolve_recovery_action but routed '
            f'nowhere in {_SKILL_MD}. Add a row to the `| `action` | Branch |` table '
            f'naming the branch each one enters.'
        )

    def test_no_route_names_an_action_the_selector_cannot_publish(self):
        """The reverse direction: a row surviving a rename routes a dead token.

        Without this, deleting an action from the vocabulary would leave its row in
        place and the totality check above would still pass — the table would look
        complete while one of its rows could never fire.
        """
        phantom = _ROUTED_ACTIONS - set(github_re_review.RECOVERY_ACTIONS)

        assert not phantom, (
            f'{sorted(phantom)} are routed in {_SKILL_MD} but are not members of '
            f'RECOVERY_ACTIONS {sorted(github_re_review.RECOVERY_ACTIONS)}'
        )

    def test_every_row_names_a_destination(self):
        """A row with an empty target cell routes an action to nothing at all."""
        for action_cell, target_cell in _ROUTE_ROWS:
            assert target_cell, f'route row for {action_cell!r} names no destination'


class TestEveryCitedBranchExists:
    """A route's target must resolve to a real heading in the same document.

    The anchors are resolved by literal number, which is what makes a renumbering
    observable here rather than at the moment a live recovery walks into a branch
    that is no longer there.
    """

    def test_the_branch_populations_are_non_empty(self):
        """⛔ Vacuity guard: a subset check against an empty superset is not evidence."""
        text = _SKILL_MD.read_text(encoding='utf-8')

        assert _BRANCH_HEADING.findall(text), f'no `#### Branch N` headings in {_SKILL_MD}'
        assert any(_BRANCH_CITATION.search(target) for _a, target in _ROUTE_ROWS), (
            'no route row cites a branch — the table is no longer routing to branches '
            'and this suite is checking a mapping that stopped existing'
        )

    def test_every_branch_a_route_cites_has_a_heading(self):
        """The renumbering tripwire, in the direction that breaks a live recovery."""
        text = _SKILL_MD.read_text(encoding='utf-8')
        declared = set(_BRANCH_HEADING.findall(text))

        for action_cell, target_cell in _ROUTE_ROWS:
            for cited in _BRANCH_CITATION.findall(target_cell):
                assert cited in declared, (
                    f'route {action_cell!r} sends to Branch {cited}, which has no '
                    f'`#### Branch {cited}` heading in {_SKILL_MD}. Declared: '
                    f'{sorted(declared)}'
                )
