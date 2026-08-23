#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""The ARGUMENT_NAMING corpus over the real tree, reported against its own population.

``analyze_argument_naming`` is a corpus-relational rule: it judges every
executor invocation written anywhere in the marketplace markdown against the
argparse surface the generated executor exposes. A bare finding count says
nothing about how much of that corpus was reached — and the cluster's substrate
is git-ignored, so "reached none of it" is a state a checkout can genuinely be
in. This module therefore never reports a count alone. Every figure it publishes
is derived, in one pass, from the same walk the findings came from:

* ``markdown_targets`` — the files ``_markdown_targets`` enumerates.
* ``invocations`` — the executor tokens those files actually carry.
* ``registered_notations`` — what the executor's ``SCRIPTS`` literal declares.
* ``derivable_surfaces`` — the notations whose ``--help`` surface was derived.
* ``non_derivable_omitted`` — the remainder, dropped fail-closed so an
  unparseable ``--help`` can never manufacture a finding. This is a coverage
  figure, not a defect count: those notations were registered and NOT judged.

The clean assertion is reported as FIXED / REMAINING against the population, not
as a bare "clean", so a number that moves has to say what it moved against.

Substrate handling is the module's own thesis applied to itself. When the
registry is unusable the corpus was not judged at all, so these tests SKIP with
the substrate state named rather than passing — a pass would be the exact
could_not_look-read-as-clean confusion the rule exists to end. A checkout
without ``.plan/execute-script.py`` (a fresh clone, CI) is that case; bootstrap
it with ``/marshall-steward`` to make the corpus judgeable.
"""

from __future__ import annotations

from collections import Counter
from functools import lru_cache
from pathlib import Path

import pytest

from conftest import MARKETPLACE_ROOT, load_script_module

_aan = load_script_module(
    'pm-plugin-development',
    'plugin-doctor',
    '_analyze_argument_naming.py',
    '_analyze_argument_naming_real_tree_corpus',
)

#: The MARKETPLACE dir — the parent of ``bundles/``. The cluster derives its
#: markdown corpus as ``{root}/bundles`` and its executor as
#: ``{root.parent}/.plan/execute-script.py``, so passing the bundles dir here
#: would resolve the executor to a path that does not exist and the run would
#: report the substrate absence instead of the corpus.
MARKETPLACE: Path = MARKETPLACE_ROOT.parent

#: The population keys every report line and every assertion message carries.
POPULATION_KEYS = (
    'markdown_targets',
    'invocations',
    'registered_notations',
    'derivable_surfaces',
    'non_derivable_omitted',
)


@lru_cache(maxsize=1)
def _corpus() -> dict:
    """Derive the corpus population and the findings in ONE pass.

    Ordering is load-bearing. ``analyze_argument_naming`` runs first so the
    shared ``argparse_surface`` in-process memo is warm; the ``build_script_index``
    call below then re-reads the SAME derivation rather than paying a second
    whole-tree ``--help`` walk, and — more importantly — rather than producing a
    second answer that could disagree with the one the findings came from.

    When the registry is unusable both the cluster and ``build_script_index``
    short-circuit on the empty notation set, so the unusable path costs nothing
    and still yields every markdown figure.
    """
    executor_path = MARKETPLACE.parent / '.plan' / 'execute-script.py'
    registry = _aan.read_notation_registry(executor_path)
    findings = _aan.analyze_argument_naming(MARKETPLACE)
    targets = _aan._markdown_targets(MARKETPLACE)
    invocations = sum(len(_aan._extract_invocations(path)) for path in targets)
    index = _aan.build_script_index(set(registry.notations), MARKETPLACE)
    registered = len(registry.notations)
    derivable = len(index)
    return {
        'substrate_status': registry.status,
        'substrate_path': str(executor_path),
        'markdown_targets': len(targets),
        'invocations': invocations,
        'registered_notations': registered,
        'derivable_surfaces': derivable,
        'non_derivable_omitted': registered - derivable,
        'findings': findings,
    }


def _findings_by_file(findings: list[dict]) -> Counter:
    """Count findings per anchoring file — the enumeration a RED run publishes."""
    return Counter(str(finding.get('file', '<unanchored>')) for finding in findings)


def corpus_report() -> str:
    """Render the population, the substrate state, and the per-file finding split."""
    corpus = _corpus()
    findings = corpus['findings']
    per_file = _findings_by_file(findings)
    lines = [
        f'substrate_status: {corpus["substrate_status"]}',
        f'substrate_path: {corpus["substrate_path"]}',
    ]
    lines.extend(f'{key}: {corpus[key]}' for key in POPULATION_KEYS)
    lines.append(f'findings: {len(findings)}')
    lines.append(f'files_with_findings: {len(per_file)}')
    lines.extend(f'  {path}: {count}' for path, count in sorted(per_file.items()))
    return '\n'.join(lines)


def _require_judged_corpus() -> dict:
    """Return the corpus, or SKIP when the substrate made it unjudgeable.

    A checkout whose registry is unusable produced no verdict about the corpus.
    Reporting that as a pass is the defect this rule cluster exists to remove, so
    the skip names the state and the substrate path instead.
    """
    corpus = _corpus()
    if corpus['substrate_status'] != _aan.SUBSTRATE_PRESENT:
        pytest.skip(
            f'could_not_look: the notation registry is {corpus["substrate_status"]} '
            f'({corpus["substrate_path"]}), so the corpus was NOT judged — this is '
            f'not a clean corpus. Bootstrap the checkout (/marshall-steward) to '
            f'make it judgeable.\n{corpus_report()}'
        )
    return corpus


def test_the_derived_population_is_non_empty():
    """Nothing below reports against a corpus of zero.

    A finding count of zero over an unwalked corpus is indistinguishable from a
    clean sweep, so the walk is asserted to have reached something before any
    verdict is drawn from it. Both the file corpus AND the invocation corpus are
    asserted: a walk that found files but extracted no invocation from any of
    them would judge nothing while still reporting a healthy file count.
    """
    corpus = _require_judged_corpus()

    assert corpus['markdown_targets'] > 0, (
        f'The markdown corpus is EMPTY, so every count below would be a zero '
        f'over nothing.\n{corpus_report()}'
    )
    assert corpus['invocations'] > 0, (
        f'The corpus carries NO executor invocation, so the cluster judged '
        f'nothing regardless of how many files it opened.\n{corpus_report()}'
    )
    assert corpus['registered_notations'] > 0, (
        f'The accept-set is EMPTY, so no invocation could have been judged '
        f'against anything.\n{corpus_report()}'
    )


def test_the_report_publishes_every_population_figure():
    """A clean run still states what it walked.

    The clean case is the one that matters: on a passing gate the finding list is
    empty, so unless the population is published alongside it, a run that
    examined the whole tree reads exactly like one that examined nothing. The
    coverage figure ``non_derivable_omitted`` is published too — those notations
    were registered and deliberately NOT judged, which a bare pass hides.
    """
    corpus = _require_judged_corpus()
    report = corpus_report()
    print(report)

    for key in POPULATION_KEYS:
        assert f'{key}: {corpus[key]}' in report, (
            f'{key} is absent from the published report.\n{report}'
        )
    assert f'findings: {len(corpus["findings"])}' in report, report


def test_the_argument_naming_corpus_is_clean_against_its_published_population():
    """Every documented invocation in the real tree matches its script's argparse surface.

    The verdict is reported against the population it was derived from, never as
    a bare "clean": the assertion message carries the whole report, so a RED run
    IS the enumeration — the per-file split names every offending document — and
    a GREEN run states the corpus size the zero was drawn from.
    """
    corpus = _require_judged_corpus()
    findings = corpus['findings']
    per_file = _findings_by_file(findings)

    assert not findings, (
        f'REMAINING {len(findings)} argument-naming finding(s) across '
        f'{len(per_file)} file(s), derived from a population of '
        f'{corpus["markdown_targets"]} markdown target(s) / '
        f'{corpus["invocations"]} invocation(s) / '
        f'{corpus["registered_notations"]} registered notation(s) '
        f'({corpus["derivable_surfaces"]} derivable, '
        f'{corpus["non_derivable_omitted"]} omitted fail-closed).\n'
        f'{corpus_report()}'
    )
