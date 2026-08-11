#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Population-derived contract over the finalize merge-and-review script invocations.

Two invariants, each derived from the tree at run time rather than a curated list of
call sites — a curated list is the artifact this plan exists to retire:

* **D0 — the exit-code convention covers every invoked script.** The observed
  swallowed-rejection failures reached ``github_pr``, ``review_completeness`` and
  ``ci`` — none of which is ``manage-*`` — yet the merge-and-review docs carried an
  exit-code convention scoped to ``manage-*`` only, so a non-zero exit from exactly
  those three fell outside the rule and could be read as an empty-but-clean result.
  This suite derives the NON-``manage-*`` invocation population from the merge-and-review
  docs and fails unless each doc's exit-code convention is widened past ``manage-*``.

* **D3 — every documented review-and-merge invocation parses against its own parser.**
  A workflow doc that prescribes a flag no script declares (``--enabled-bots``), or a
  flag in a position the parser rejects (``--plan-id`` after a router verb), makes a
  dispatched leaf that quotes the doc verbatim fail with an argparse rejection (exit 2).
  This suite derives the documented invocation population from the docs, substitutes
  the placeholders, runs each against its REAL parser, and fails on any argparse
  rejection — so a reintroduced ``--enabled-bots`` fails here where it previously only
  failed a dispatched agent at merge time.

Both populations are asserted NON-EMPTY before anything is swept over them (an empty
parametrize is a pytest SKIP, not a failure) and publish their size in the failure
message, so a scan that silently matched nothing fails loudly rather than reporting a
healthy sweep over an empty set. The derivation copies the heading/fenced-block walk
already used by ``_dispatch_roster`` and ``test_bot_participation_contract`` rather than
introducing a third.
"""

from __future__ import annotations

import re
import shlex

import pytest

from conftest import MARKETPLACE_ROOT, get_script_path, run_script

# =============================================================================
# The finalize merge-and-review docs — the population source
# =============================================================================
#
# These two documents carry the review-and-merge DECISION invocations: the
# pre-merge barrier (branch-cleanup.md) and the FIND + participation guard
# (automatic-review/SKILL.md). The dispatcher SKILL.md orchestrates them and
# carries the same exit-code convention, so it is included in the convention-scope
# check but not scanned for invocations (its own calls are the dispatcher's, not the
# barrier's).

_SKILLS = MARKETPLACE_ROOT / 'plan-marshall' / 'skills'
_BARRIER_DOC = _SKILLS / 'phase-6-finalize' / 'standards' / 'branch-cleanup.md'
_REVIEW_DOC = _SKILLS / 'automatic-review' / 'SKILL.md'
_DISPATCHER_DOC = _SKILLS / 'phase-6-finalize' / 'SKILL.md'

#: The docs scanned for the invocation population.
_INVOCATION_DOCS = (_BARRIER_DOC, _REVIEW_DOC)
#: The docs whose exit-code convention must be widened past manage-*.
_CONVENTION_DOCS = (_BARRIER_DOC, _REVIEW_DOC, _DISPATCHER_DOC)

#: A canonical `bundle:skill:script` executor notation.
_NOTATION = re.compile(r'\bplan-marshall:[a-z0-9-]+:[a-z0-9_-]+\b')
#: An `execute-script.py` invocation opening (up to and including the notation).
_EXEC_CALL = re.compile(
    r'python3\s+\.plan/execute-script\.py\s+(?P<notation>plan-marshall:[a-z0-9-]+:[a-z0-9_-]+)'
)

#: The review-and-merge participation SURFACE D3 parses: the three (script, verb)
#: pairs the plan names — the producer FIND (`github_pr fetch_findings`), the
#: participation predicate (`review_completeness check`), and the PR-wide
#: `not_triggered` read (`ci checks pull-request-runs`). This is a definition of the
#: SURFACE, not a list of call sites — WHERE each is invoked is still derived from
#: the docs. It is deliberately narrower than "every runnable call": the re-review /
#: completion-poll / CI-wait verbs (`bot_completion`, `re-review`,
#: `pr wait-for-comments`) carry choice-constrained or value-required flags whose
#: valid values are not derivable from the doc text, so a placeholder-substituted
#: parse of them tests the substitution, not the doc. The plan's flag/script mismatch
#: lives entirely on the three surface verbs below.
def _is_review_merge_surface(command: str) -> bool:
    """True for a concrete invocation of one of the three review-and-merge surface verbs."""
    if 'automatic-review:review_completeness' in command and re.search(r'\bcheck\b', command):
        return True
    if 'workflow-integration-github:github_pr' in command and 'fetch_findings' in command:
        return True
    if 'tools-integration-ci:ci' in command and 'pull-request-runs' in command:
        return True
    return False

#: Placeholder substitutions that keep an invocation PARSEABLE. A bot-list value's
#: shape is irrelevant to argparse (the malformed-value rejection is a post-parse
#: caller error, exit 1, not an argparse rejection, exit 2), so an unknown placeholder
#: collapses to the empty string — the empty-list form every list flag accepts.
_SUBSTITUTIONS = {
    'plan_id': 'rmi-parse-probe',
    'pr_number': '1',
    'worktree_path': '.',
}
_PLACEHOLDER = re.compile(r'\{[a-zA-Z_][a-zA-Z0-9_]*\}')


def _fenced_commands(doc_text: str) -> list[str]:
    """Return every fenced code block, backslash-continuations folded to one line each."""
    blocks: list[str] = []
    in_fence = False
    current: list[str] = []
    for raw in doc_text.splitlines():
        if raw.lstrip().startswith('```'):
            if in_fence:
                blocks.append(re.sub(r'\\\n\s*', ' ', '\n'.join(current)))
                current = []
            in_fence = not in_fence
            continue
        if in_fence:
            current.append(raw)
    return blocks


def _invoked_notations(doc_text: str) -> set[str]:
    """Every distinct executor notation invoked in a doc's fenced blocks."""
    notations: set[str] = set()
    for block in _fenced_commands(doc_text):
        for match in _EXEC_CALL.finditer(block):
            notations.add(match.group('notation'))
    return notations


def _is_manage_star(notation: str) -> bool:
    """True when the notation's skill segment is a manage-* skill."""
    _bundle, skill, _script = notation.split(':')
    return skill.startswith('manage-')


def _script_path_for(notation: str):
    """Resolve a `bundle:skill:script` notation to its script file path."""
    bundle, skill, script = notation.split(':')
    return get_script_path(bundle, skill, f'{script}.py')


def _substitute(command: str) -> str:
    """Replace every `{placeholder}` with a parseable value (unknowns -> empty)."""
    return _PLACEHOLDER.sub(lambda m: _SUBSTITUTIONS.get(m.group(0)[1:-1], ''), command)


def _documented_invocations() -> list[tuple[str, str, str]]:
    """Return `(doc_name, notation, command)` for every RUNNABLE documented invocation.

    A runnable invocation is a concrete `execute-script.py` call of one of the three
    review-and-merge surface verbs (see `_is_review_merge_surface`), excluding the
    `## Canonical invocations` advertised forms (which carry argparse's
    `[--flag [VALUE]]` optional-bracket notation and are specifications, not calls).
    The population is derived from the docs, never listed.
    """
    invocations: list[tuple[str, str, str]] = []
    for doc in _INVOCATION_DOCS:
        text = doc.read_text(encoding='utf-8')
        for block in _fenced_commands(text):
            match = _EXEC_CALL.search(block)
            if not match:
                continue
            if not _is_review_merge_surface(block):
                continue
            # Skip an advertised form: argparse renders optional flags as
            # `[--flag [VALUE]]`, which is a spec, not a runnable call.
            if '[' in block:
                continue
            invocations.append((doc.name, match.group('notation'), block.strip()))
    return invocations


_DOCUMENTED_INVOCATIONS = _documented_invocations()

# Non-emptiness asserted at IMPORT, before any parametrize sweeps it — an empty
# parametrize is a pytest SKIP, not a failure, so a scan that matched nothing would
# report a clean sweep over nothing. The size travels in the message so a silently
# shrunken scan is visible as a number.
assert _DOCUMENTED_INVOCATIONS, (
    'no runnable review/merge invocation was scanned from the finalize merge-and-review '
    f'docs {[d.name for d in _INVOCATION_DOCS]} — the D3 population is vacuous and the '
    'parse sweep would pass over an empty set'
)


def _invocation_id(item: tuple[str, str, str]) -> str:
    doc, notation, _command = item
    return re.sub(r'[^A-Za-z0-9]+', '-', f'{doc}--{notation.split(":")[-1]}').strip('-').lower()


# =============================================================================
# D0 — the exit-code convention covers every invoked script, not only manage-*
# =============================================================================

_WIDE_HEADING = '## Exit-code convention for every script call'
_NARROW_HEADING = '## Exit-code convention for `manage-*` script calls'


class TestExitCodeConventionCoversEveryScript:
    """Each merge-and-review doc's exit-code convention is scoped past ``manage-*``.

    The defect this pins: the convention was scoped to ``manage-*`` script calls,
    which structurally excluded the ``github_pr`` / ``review_completeness`` / ``ci``
    calls that gate the merge-and-review path and were the swallowed-rejection sites.
    """

    def test_the_invocation_population_is_non_empty_and_reaches_non_manage_star(self):
        """The derivation found real invocations, including the non-manage-* ones.

        Published as a size, and asserted to REACH the non-manage-* scripts — a
        population of only manage-* calls could not demonstrate the widening this
        suite exists to enforce.
        """
        all_notations: set[str] = set()
        for doc in _INVOCATION_DOCS:
            all_notations |= _invoked_notations(doc.read_text(encoding='utf-8'))

        assert all_notations, (
            f'no executor notation was scanned from {[d.name for d in _INVOCATION_DOCS]} '
            '— the population is vacuous'
        )
        non_manage = {n for n in all_notations if not _is_manage_star(n)}
        assert non_manage, (
            f'the merge-and-review docs invoke only manage-* scripts across '
            f'{len(all_notations)} notations, so the widening past manage-* cannot be '
            f'demonstrated: {sorted(all_notations)}'
        )
        # The three families the plan names must all be present, derived from the scan.
        skills = {n.split(':')[1] for n in non_manage}
        assert {'workflow-integration-github', 'automatic-review', 'tools-integration-ci'} <= skills, (
            f'the scan reached non-manage-* skills {sorted(skills)} but not all three of '
            'github / review_completeness / ci — the swallowed-rejection families'
        )

    @pytest.mark.parametrize('doc', _CONVENTION_DOCS, ids=lambda d: d.parent.name + '-' + d.name)
    def test_convention_is_widened_past_manage_star(self, doc):
        """The doc's exit-code convention names EVERY script call, not manage-* only.

        Mutation-proof in both directions: reverting the heading to the manage-*
        form fails the first assertion, and leaving the manage-*-scoped heading in
        place alongside the wide one fails the second.
        """
        text = doc.read_text(encoding='utf-8')

        assert _WIDE_HEADING in text, (
            f'{doc.name}: the exit-code convention must be widened to {_WIDE_HEADING!r} — '
            'a manage-*-scoped convention leaves the non-manage-* github_pr / '
            'review_completeness / ci calls in the merge-and-review path uncovered, which '
            'is exactly the swallowed-rejection gap'
        )
        assert _NARROW_HEADING not in text, (
            f'{doc.name}: the manage-*-scoped convention heading {_NARROW_HEADING!r} '
            'survives, so the widening did not fully land'
        )


# =============================================================================
# D3 — every documented review-and-merge invocation parses against its own parser
# =============================================================================


class TestDocumentedReviewMergeInvocationsParse:
    """Every documented review/merge invocation parses against its live argparse.

    A documented ``--enabled-bots`` (a flag no parser declares) or a ``--plan-id``
    after a router verb (a mispositioned flag) is an argparse rejection — exit 2 —
    when a leaf quotes the doc verbatim. This sweep runs each documented invocation
    against its REAL parser and fails on that rejection.
    """

    def test_the_population_size_is_published(self):
        """A future reader can tell a passing sweep from an empty one by the count."""
        assert len(_DOCUMENTED_INVOCATIONS) >= 1
        # The floor is derived-not-guessed: the two docs each carry at least a
        # fetch_findings and a review_completeness check invocation, so the honest
        # floor of the scan is four. A scan that silently dropped below it means the
        # matcher stopped seeing real invocations.
        assert len(_DOCUMENTED_INVOCATIONS) >= 4, (
            f'only {len(_DOCUMENTED_INVOCATIONS)} runnable invocations were scanned from '
            f'{[d.name for d in _INVOCATION_DOCS]}; the barrier and the FIND step each '
            'document a fetch_findings and a review_completeness check, so the floor is 4 '
            f'— the matcher likely stopped matching: {[i[1] for i in _DOCUMENTED_INVOCATIONS]}'
        )

    @pytest.mark.parametrize('invocation', _DOCUMENTED_INVOCATIONS, ids=_invocation_id)
    def test_documented_invocation_parses(self, invocation):
        """The documented flags parse against the script's real argparse (no exit 2).

        Placeholders are substituted with parseable values, and provider scripts run
        with an emptied ``PATH`` so they fail at the provider boundary (an argparse
        rejection would happen BEFORE that boundary, so it is still observed). A
        malformed VALUE is a post-parse caller error (exit 1), not an argparse
        rejection (exit 2), so only exit 2 — an unrecognized or mispositioned flag —
        fails this test.
        """
        doc_name, notation, command = invocation
        substituted = _substitute(command)
        tokens = shlex.split(substituted)
        # Drop `python3`, `.plan/execute-script.py`, and the notation; keep the rest
        # (verb + args) for the direct script invocation.
        try:
            notation_idx = tokens.index(notation)
        except ValueError:  # pragma: no cover - notation always present by construction
            pytest.fail(f'{doc_name}: notation {notation} vanished from {tokens}')
        args = tokens[notation_idx + 1 :]

        result = run_script(
            _script_path_for(notation), *args, env_overrides={'PATH': ''}
        )

        assert result.returncode != 2, (
            f'{doc_name}: the documented invocation `{command}` is an argparse rejection '
            f'(exit 2) against {notation.split(":")[-1]}.py — a flag it prescribes is not '
            f'declared by that parser, or is placed where the parser rejects it.\n'
            f'stderr: {result.stderr.strip()}'
        )
        assert 'unrecognized arguments' not in result.stderr, (
            f'{doc_name}: `{command}` names a flag {notation.split(":")[-1]}.py does not '
            f'declare.\nstderr: {result.stderr.strip()}'
        )
