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
import contextlib
import io
import re
from pathlib import Path

import pytest
from ci_base import add_pr_create_args, build_parser, parse_ci_args
from input_validation import _root_router_option_strings

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


# ---------------------------------------------------------------------------
# Behavioural arm — the cell's claim driven through parse_args(), not structure
# ---------------------------------------------------------------------------
#
# Every assertion above reads parser STRUCTURE: set membership, name analysis,
# and `.required` off `leaf._actions`. None of them calls `parse_args()`, so the
# guard could not fail for the reason it exists — the cell makes a BEHAVIOURAL
# claim about where `--plan-id` may be written, and the structural arms would
# stay green while the documented placement stopped parsing.
#
# The subjects below are DERIVED from the two populations rather than named
# literally: a hand-picked verb goes stale exactly the way the doc cell did.

#: The verbs the ROUTER's `--plan-id` serves — every registered subcommand that
#: does NOT declare its own. Derived by subtraction, never transcribed.
ROUTER_CONSUMED_SUBCOMMANDS = ALL_SUBCOMMANDS - POST_VERB_SUBCOMMANDS


def _option_argv(action) -> list[str]:
    """A minimal argv fragment satisfying one option action.

    The value is synthesized from the action's own declaration (`choices`, then
    `type`), so no verb's flag vocabulary is transcribed here.
    """
    flag = action.option_strings[0]
    if action.nargs == 0:
        return [flag]
    if action.choices:
        return [flag, str(next(iter(action.choices)))]
    if action.type is int:
        return [flag, '1']
    return [flag, 'x']


def _minimal_argv(leaf, *, skip: frozenset[str] = frozenset()) -> list[str] | None:
    """Minimal argv satisfying *leaf*'s own required arguments, or ``None``.

    Derived from the leaf parser's declared actions and its required mutually
    exclusive groups (argparse marks the GROUP required, not its members, so a
    member-only scan would miss `--pr-number | --head`). Returns ``None`` when
    the leaf requires a positional, which this builder cannot synthesize a
    meaningful value for — such a verb is simply not used as a subject.
    """
    argv: list[str] = []
    grouped: set[int] = set()

    for group in leaf._mutually_exclusive_groups:
        members = [a for a in group._group_actions if a.option_strings]
        if not members:
            continue
        grouped.update(id(a) for a in group._group_actions)
        if group.required and members[0].option_strings[0] not in skip:
            argv.extend(_option_argv(members[0]))

    for action in leaf._actions:
        if id(action) in grouped:
            continue
        if not action.option_strings:
            if getattr(action, 'required', False):
                return None  # a required positional — not synthesizable here
            continue
        if action.required and action.option_strings[0] not in skip:
            argv.extend(_option_argv(action))

    return argv


def _parses(argv: list[str]) -> argparse.Namespace | None:
    """Parse *argv* through a fresh full parser, or ``None`` if argparse rejects it."""
    # Annotated because `ci_base` is an untyped import for mypy, so the parser it
    # builds — and everything parsed through it — arrives as `Any`.
    parser: argparse.ArgumentParser = _build_full_parser()
    with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
        try:
            return parser.parse_args(argv)
        except SystemExit:
            return None


def _first_parsable_subject(subcommands, *, skip: frozenset[str] = frozenset()):
    """The first subcommand (sorted) whose derived minimal argv actually parses.

    Self-validating: the candidate is accepted only once a real ``parse_args``
    round-trip succeeds, so a verb whose requirements this builder cannot meet is
    passed over rather than producing a spurious failure. Returns
    ``(subcommand, leaf_argv)``.

    Parsability is probed with the COMPLETE argv and *skip* is applied only to
    the returned fragment. Probing the skipped form instead would reject every
    candidate whenever the skipped flag is a required one — which is exactly the
    case the post-verb subjects are selected for.
    """
    leaves = dict(_leaf_subparsers(_build_full_parser()))
    for subcommand in sorted(subcommands):
        leaf = leaves[tuple(subcommand.split(' '))]
        complete = _minimal_argv(leaf)
        if complete is None:
            continue
        if _parses([*subcommand.split(' '), *complete]) is None:
            continue
        reduced = _minimal_argv(leaf, skip=skip)
        if reduced is None:
            continue
        return subcommand, reduced
    raise AssertionError(
        f'No subject could be built from {len(set(subcommands))} derived subcommand(s): '
        f'{sorted(subcommands)}. Without one the behavioural arm below asserts nothing.'
    )


def test_ci_root_parser_declares_no_router_level_plan_id():
    """Matched control: the pre-verb form is ROUTER-owned, not parser-owned.

    ``ci.py`` consumes ``--plan-id`` with ``extract_routing_args`` and rewrites
    ``sys.argv`` BEFORE the provider parser is built, so the provider's root
    parser declares the flag nowhere. That fact is what makes the pre-verb
    placement work at all, and it is the premise the two router-consumed cases
    below depend on: were a root-level ``--plan-id`` ever added here, the
    post-verb rejection would stop being the parser's verdict and this control
    would fail rather than letting those cases quietly change meaning.
    """
    assert _root_router_option_strings(_build_full_parser()) == set(), (
        'The ci root parser now declares a router-level flag. The envelope cell describes a '
        'router that consumes --plan-id ahead of the parser; if the parser declares it too, the '
        'documented placement contract has changed and the cases below no longer test it.'
    )


def test_router_consumed_subcommand_parses_with_no_plan_id_at_all():
    """A router-consumed verb parses without ``--plan-id`` — the router supplies it.

    This is the positive half of the pre-verb claim that IS observable at the
    parser: the verb is complete without the flag, which is why writing it ahead
    of the verb (where the router eats it) leaves a well-formed command behind.
    """
    subcommand, leaf_argv = _first_parsable_subject(ROUTER_CONSUMED_SUBCOMMANDS)
    namespace = _parses([*subcommand.split(' '), *leaf_argv])

    assert namespace is not None, (
        f'`ci {subcommand}` does not parse without --plan-id, though it declares none. '
        'The pre-verb form would then leave an argv the provider parser rejects.'
    )


def test_router_consumed_subcommand_rejects_a_post_verb_plan_id(monkeypatch, capsys):
    """The post-verb form is REJECTED for a verb that declares no ``--plan-id``.

    Driven through ``parse_ci_args`` so the rejection is the real caller-facing
    one: it names the flag AND says it belongs before the verb, which is the
    disposition the contract cell prescribes.
    """
    subcommand, leaf_argv = _first_parsable_subject(ROUTER_CONSUMED_SUBCOMMANDS)
    argv = [*subcommand.split(' '), *leaf_argv, '--plan-id', 'PLAN-X']
    monkeypatch.setattr('sys.argv', ['ci', *argv])

    with pytest.raises(SystemExit) as excinfo:
        parse_ci_args(_build_full_parser())

    assert excinfo.value.code == 2
    stderr = capsys.readouterr().err
    assert '--plan-id' in stderr
    assert 'belongs BEFORE the subcommand' in stderr, (
        f'`ci {subcommand} --plan-id ...` was rejected without telling the caller the flag '
        f'belongs before the verb. Stderr: {stderr}'
    )


def test_post_verb_subcommand_parses_and_binds_its_own_plan_id():
    """A post-verb verb accepts ``--plan-id`` AFTER the verb and binds the value."""
    subcommand, leaf_argv = _first_parsable_subject(
        POST_VERB_SUBCOMMANDS, skip=frozenset({'--plan-id'})
    )
    namespace = _parses([*subcommand.split(' '), *leaf_argv, '--plan-id', 'PLAN-X'])

    assert namespace is not None, (
        f'`ci {subcommand} --plan-id PLAN-X` did not parse, though the verb declares a required '
        'post-verb --plan-id. The cell prescribes exactly this placement for it.'
    )
    assert namespace.plan_id == 'PLAN-X', (
        f'`ci {subcommand}` parsed the post-verb --plan-id but bound {namespace.plan_id!r}.'
    )


def test_post_verb_subcommand_rejects_the_pre_verb_form():
    """The pre-verb form's documented disposition on a post-verb verb: REJECTED.

    Once the router has consumed a pre-verb ``--plan-id``, what reaches the
    provider parser is the verb WITHOUT it — and a verb that declares its own
    required ``--plan-id`` rejects that. This is the argparse rejection the whole
    deliverable is about: the cell must not name such a verb as taking the
    pre-verb flag.
    """
    subcommand, leaf_argv = _first_parsable_subject(
        POST_VERB_SUBCOMMANDS, skip=frozenset({'--plan-id'})
    )

    assert _parses([*subcommand.split(' '), *leaf_argv]) is None, (
        f'`ci {subcommand}` parsed with NO --plan-id, so its post-verb flag is not really '
        'required and the pre-verb form would be merely lossy rather than rejected.'
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
