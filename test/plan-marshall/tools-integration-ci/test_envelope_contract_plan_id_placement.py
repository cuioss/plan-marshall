#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""
Doc-vs-parser guard for the ``plan_id`` row of ``agents/execution-context.md``.

The envelope contract tells a dispatched leaf where ``--plan-id`` goes on a
``ci`` call. ``ci`` is split: the router consumes the flag only ahead of the
first verb token, while the body-consumer and prepare verbs declare a
**required** ``--plan-id`` on their own subparser. A contract cell that names a
post-verb verb as taking a pre-verb flag prescribes an argparse rejection.

The post-verb population is DERIVED from ``ci_base``'s own parser tree — never
transcribed — so the guard fails the moment the prose and the parser disagree.
``add_pr_create_args`` is applied on top of ``build_parser`` because each
provider front-end registers ``pr create`` itself, and that verb is exactly the
one a cold read of the cell is most likely to get wrong.
"""

import argparse
import re
from pathlib import Path

import pytest
from ci_base import add_pr_create_args, build_parser

from conftest import PROJECT_ROOT

#: Annotated because ``conftest`` is an untyped import for mypy, so ``PROJECT_ROOT``
#: arrives as ``Any`` and every path derived from it would too.
_CONTRACT_DOC: Path = PROJECT_ROOT / 'marketplace' / 'bundles' / 'plan-marshall' / 'agents' / 'execution-context.md'

#: The sentence that ends the cell's pre-verb clause and opens the post-verb one.
#: Everything before it is the region in which the cell names verbs as taking a
#: ROUTER-level ``--plan-id``; a post-verb verb named there is the defect.
_SPLIT_MARKER = 'This does not extend to `ci` as a whole:'

#: A backticked ``ci`` verb phrase, e.g. ``pr view`` or ``checks pull-request-runs``.
_VERB_PHRASE_RE = re.compile(r'`((?:pr|checks|issue|branch|repo)(?:\s+[a-z][a-z-]*)+)`')

#: A backticked bare ``ci`` noun, e.g. ``checks``. Naming a noun as a whole is
#: only true when NO leaf beneath it declares its own ``--plan-id``.
_BARE_NOUN_RE = re.compile(r'`(pr|checks|issue|branch|repo)`')


def _named_verb_phrases(region: str) -> set[str]:
    """Return the ``ci`` verb phrases *region* names, whitespace-normalized."""
    return {' '.join(phrase.split()) for phrase in _VERB_PHRASE_RE.findall(region)}


def _leaf_subparsers(parser, prefix=()):
    """Yield ``(path, parser)`` for every leaf subparser under *parser*."""
    actions = [a for a in parser._actions if isinstance(a, argparse._SubParsersAction)]
    if not actions:
        yield prefix, parser
        return
    for action in actions:
        for name, sub in action.choices.items():
            yield from _leaf_subparsers(sub, (*prefix, name))


def _declares_plan_id(parser) -> bool:
    return any('--plan-id' in action.option_strings for action in parser._actions)


def _build_full_parser():
    """Build the ``ci`` parser tree as a provider front-end actually registers it."""
    parser, pr_sub, _checks_sub, _issue_sub, _branch_sub = build_parser('envelope-contract-guard')
    add_pr_create_args(pr_sub)
    return parser


def _derive_populations() -> tuple[frozenset[str], frozenset[str]]:
    """Return ``(post_verb_subcommands, all_subcommands)`` as space-joined paths."""
    parser = _build_full_parser()
    post_verb: set[str] = set()
    every: set[str] = set()
    for path, leaf in _leaf_subparsers(parser):
        joined = ' '.join(path)
        every.add(joined)
        if _declares_plan_id(leaf):
            post_verb.add(joined)
    return frozenset(post_verb), frozenset(every)


POST_VERB_SUBCOMMANDS, ALL_SUBCOMMANDS = _derive_populations()


def _plan_id_cell() -> str:
    """Return the ``plan_id`` row of the prompt-body contract table."""
    for line in _CONTRACT_DOC.read_text(encoding='utf-8').splitlines():
        if line.startswith('| `plan_id` |'):
            return line
    raise AssertionError(f'No `plan_id` contract row found in {_CONTRACT_DOC}')


def _pre_verb_region() -> str:
    """Return the part of the cell that names verbs as taking a pre-verb flag."""
    cell = _plan_id_cell()
    marker_at = cell.find(_SPLIT_MARKER)
    assert marker_at != -1, (
        f'The `plan_id` cell no longer carries the split marker {_SPLIT_MARKER!r}, so the pre-verb '
        f'clause cannot be bounded and no post-verb verb can be shown to be excluded from it. '
        f'{len(POST_VERB_SUBCOMMANDS)} ci subcommand(s) declare a required post-verb --plan-id.'
    )
    return cell[:marker_at]


def test_derived_post_verb_population_is_non_empty():
    """The parser tree yields the post-verb ``--plan-id`` population the cell describes."""
    assert POST_VERB_SUBCOMMANDS, (
        'No ci subcommand declares its own --plan-id. Either the parser changed shape or the '
        'derivation stopped reaching the leaf subparsers; the guard would then pass vacuously.'
    )
    assert POST_VERB_SUBCOMMANDS < ALL_SUBCOMMANDS, (
        'Every ci subcommand declares its own --plan-id, so nothing takes the router flag and the '
        "cell's pre-verb case describes no verb at all."
    )


#: Published on EVERY run — passing included — by the root conftest's
#: ``pytest_report_header``, which reads this pair rather than re-deriving
#: anything. Declared here rather than reported from inside a test because a
#: test-body reporter call is not a publication channel on the canonical
#: ``module-tests`` / ``verify`` path: that path carries no ``-s`` /
#: ``--capture=no`` / ``-rP``, so pytest captures and discards a passing test's
#: stdout — the only run on which a population line is supposed to appear.
GUARD_POPULATION_LABEL = 'post-verb --plan-id ci subcommands'
GUARD_POPULATION_SIZE = len(POST_VERB_SUBCOMMANDS)


def test_pre_verb_clause_names_no_post_verb_subcommand():
    """No verb that declares its own ``--plan-id`` is named as taking the router flag."""
    region = _pre_verb_region()
    falsified = sorted(_named_verb_phrases(region) & POST_VERB_SUBCOMMANDS)
    assert not falsified, (
        f'The `plan_id` cell names {falsified} as taking a pre-verb --plan-id, but each declares a '
        f'required --plan-id on its own subparser, so the prescribed placement is an argparse '
        f'rejection. Derived post-verb population: {sorted(POST_VERB_SUBCOMMANDS)}'
    )


def test_pre_verb_clause_names_only_registered_subcommands():
    """Every verb phrase the pre-verb clause names is a registered ``ci`` subcommand."""
    region = _pre_verb_region()
    unregistered = sorted(_named_verb_phrases(region) - ALL_SUBCOMMANDS)
    assert not unregistered, (
        f'The `plan_id` cell names {unregistered} as ci subcommands, but the parser registers no '
        f'such verb. Registered population: {len(ALL_SUBCOMMANDS)} subcommand(s).'
    )


def test_pre_verb_clause_names_no_split_noun_as_a_whole():
    """A noun named as a whole has no leaf declaring its own ``--plan-id``."""
    region = _pre_verb_region()
    split_nouns = sorted(
        noun
        for noun in set(_BARE_NOUN_RE.findall(region))
        if any(sub.split(' ', 1)[0] == noun for sub in POST_VERB_SUBCOMMANDS)
    )
    assert not split_nouns, (
        f'The `plan_id` cell names the bare noun(s) {split_nouns} in its pre-verb clause, but each '
        f'covers at least one verb that declares a required post-verb --plan-id, so the statement is '
        f'false for part of the noun. Derived post-verb population: {sorted(POST_VERB_SUBCOMMANDS)}'
    )


@pytest.mark.parametrize('subcommand', sorted(POST_VERB_SUBCOMMANDS))
def test_each_post_verb_subcommand_declares_plan_id_as_required(subcommand):
    """Each derived post-verb subcommand declares its own ``--plan-id`` as required.

    The cell calls the post-verb flag *required*; an optional one would make the
    pre-verb form merely lossy rather than rejected, which is a different claim.
    """
    leaf = dict(_leaf_subparsers(_build_full_parser()))[tuple(subcommand.split(' '))]
    plan_id_actions = [a for a in leaf._actions if '--plan-id' in a.option_strings]
    assert len(plan_id_actions) == 1
    assert plan_id_actions[0].required, (
        f'`ci {subcommand}` declares --plan-id on its own subparser but does not require it, so the '
        f'contract cell overstates the post-verb case for this verb.'
    )
