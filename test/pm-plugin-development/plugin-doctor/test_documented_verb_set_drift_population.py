#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""The ``documented-verb-set-drift`` rule over the REAL tree, against its own population.

The sibling suite (``test_analyze_documented_verb_set_drift.py``) proves the rule's
BEHAVIOUR on synthetic fixtures under ``tmp_path``. This module answers the other
question, which no fixture can: *what does the rule actually say about this tree,
and how much of the tree did it reach to say it?*

Why a count alone is not an answer
----------------------------------
The rule is corpus-relational and opt-in, so its finding count is never read as a
build verdict — which makes it exactly the shape that rots unwatched. Two figures
move independently and must therefore be published together:

* ``population`` — the skills carrying a ``## Canonical invocations`` block, which
  is what ``derive_population`` walked. A finding count of zero over a population
  of zero is not a clean tree; it is an unread one, and the rule's own
  ``verb_set_drift_empty_population`` guard exists because of that.
* ``skips`` — candidates whose registered verb set could not be DERIVED. A skip is
  coverage lost, not drift found, so a run can lower its finding count purely by
  raising this. Published per reason, because the reasons have different owners:
  ``no_subparser_registration_in_file`` is the file-local walk meeting a parser
  built in an imported helper (expected, and benign), while
  ``no_root_parser_resolved`` is the fail-open the rule most needs to keep
  refusing.

No absolute figure is pinned
----------------------------
⛔ Not one assertion here compares a finding or population count against a written
literal. Both move on any commit that adds a script or a fenced invocation, so a
pinned number is stale by the next one — the analyzer's own module docstring says
so, and this module obeys it rather than restating it. What IS asserted is
structural: the population is non-empty, every finding publishes the size it was
derived from, the per-type census reconciles to the total, and *this bundle's own
surfaces* carry no finding that is neither fixed nor triaged with a stated reason.
The live figures are PUBLISHED (printed, and carried in every assertion message)
so a reader gets them from a run instead of from a stale constant.

The help cache does not apply to this rule
------------------------------------------
A stale plugin-doctor help cache has previously produced hundreds of false
``manage-invocation`` findings, so any figure quoted off a doctor rule is owed a
cache check first. For THIS rule the check is discharged structurally rather than
operationally, and the answer is that there is no cache to be stale:
``derive_registered_verbs`` is a pure ``ast.parse`` walk of the script source. It
runs no ``--help``, spawns no subprocess, and does not consume
``script-shared/argparse_surface.py`` — the shared live-``--help`` derivation the
``ARGUMENT_NAMING_*`` cluster and ``manage-invocation-invalid`` DO read, and the
one a cache sits in front of. :func:`test_the_rule_derives_without_a_help_cache`
holds that contraindication, so the figures below cannot be a cached tree's
figures.

That independence is deliberate and is recorded in ``argparse_surface.py``'s own
docstring: a static ``add_parser`` walk is blind to loop-registered, helper-built
and aliased subcommands, and produced 1323 false positives in ``plan-marshall``
alone before being abandoned there. This rule keeps the static walk and pays for
that blindness with the explicit SKIP states above — refusing to compare rather
than comparing a set it knows may be partial — which is why its blindness costs
coverage instead of manufacturing findings.
"""

from __future__ import annotations

from collections import Counter
from functools import lru_cache
from pathlib import Path

from conftest import MARKETPLACE_ROOT, load_script_module
from _plugin_doctor_fixtures import documented_verb_drift_files

_mod = load_script_module(
    'pm-plugin-development',
    'plugin-doctor',
    '_analyze_documented_verb_set_drift.py',
    '_analyze_documented_verb_set_drift_population',
)

analyze_with_population = _mod.analyze_documented_verb_set_drift_with_population
analyze = _mod.analyze_documented_verb_set_drift
derive_population = _mod.derive_population

TYPE_MISSING_FROM_DOCS = _mod.TYPE_MISSING_FROM_DOCS
TYPE_PHANTOM_DOCUMENTED = _mod.TYPE_PHANTOM_DOCUMENTED
TYPE_SKIPPED = _mod.TYPE_SKIPPED
TYPE_EMPTY_POPULATION = _mod.TYPE_EMPTY_POPULATION

#: The MARKETPLACE dir — the parent of ``bundles/``. This is the argument
#: ``_runner.run_analyze_marketplace_rules`` passes (``root.parent``, where ``root``
#: is the bundles dir), so the population walked here is the one a real
#: ``analyze --rules documented_verb_set_drift`` run walks.
MARKETPLACE: Path = MARKETPLACE_ROOT.parent

#: The bundle whose surfaces this suite holds to account. The rule runs
#: whole-marketplace, so most of its findings belong to skills this bundle does not
#: own; requiring the whole tree to be clean would make this module a gate on every
#: other bundle's documentation, which is not its job and not this plan's scope.
OWNED_BUNDLE = 'pm-plugin-development'

#: Findings on :data:`OWNED_BUNDLE`'s surfaces that are deliberately ACCEPTED,
#: each with the reason it is not a defect. Keyed ``(skill, finding_type, verb)``.
#:
#: This registry is the "or triaged with a stated reason" half of the contract, and
#: it is held from BOTH sides: a finding absent from it fails
#: :func:`test_owned_bundle_findings_are_fixed_or_triaged`, and an entry that no
#: longer fires fails :func:`test_no_triage_entry_has_gone_stale`. A one-sided
#: registry rots into a permanent suppression list, which is the failure mode that
#: makes "triaged" indistinguishable from "ignored".
#: Why the twelve ``plugin-doctor`` entries below are accepted rather than fixed.
#:
#: All twelve are registered by ``_analyze.py`` / ``_fix.py`` / ``_validate.py``
#: (four verbs each; ``cross-file`` is registered by two of them, so eleven
#: distinct verbs cover twelve findings). Those three are underscore-prefixed
#: INTERNAL sub-CLIs — ``doctor-marketplace.py`` is the skill's documented public
#: surface, and it is the one the canonical-invocations block carries.
#:
#: They enter the candidate population because ``owned_entry_scripts``
#: discriminates on the ``if __name__ == '__main__':`` guard rather than on a
#: leading underscore, and that choice is deliberate and correct: this tree
#: carries non-underscore helper MODULES that are imported and never invoked, so
#: an underscore filter would both admit those and drop real entry points. The
#: cost of the correct predicate is this case — an invocable file that is not a
#: public surface — and publishing a copyable invocation for it would advertise
#: an interface callers are meant to reach through ``doctor-marketplace.py``.
_INTERNAL_SUBCLI = (
    'registered by an underscore-prefixed internal sub-CLI (_analyze/_fix/_validate); '
    'doctor-marketplace.py is this skill documented public surface, and documenting an '
    'internal sub-CLI would advertise an interface callers must not use directly'
)

#: ``serve`` is the corpus language server's long-running daemon entry point. It is
#: started by the client rather than invoked by an agent, so the skill documents
#: the client-facing surface instead. Not drift — a verb that is correctly absent
#: from the copyable-invocation surface.
_DAEMON_ENTRY_POINT = (
    'long-running daemon entry point started by the client, not an agent-callable verb; '
    'the skill documents the client-facing surface instead'
)

#: The three ``tools-marketplace-inventory`` entry scripts build their parser in an
#: imported helper, and the rule's AST walk is deliberately file-local. This is the
#: ``no_subparser_registration_in_file`` state the analyzer DISCLOSES as a coverage
#: gap rather than reporting as drift — it asserts nothing about the verb sets, and
#: is exactly the fail-closed behaviour the rule is built around. Accepted as a
#: known, reported blind spot of the static derivation.
_FILE_LOCAL_WALK_BLIND_SPOT = (
    'parser built in an imported helper; the rule AST walk is deliberately file-local, so '
    'this is a DISCLOSED coverage gap (no drift asserted), not a finding about the verb set'
)

TRIAGED: dict[tuple[str, str, str], str] = {
    ('plugin-doctor', TYPE_MISSING_FROM_DOCS, 'apply'): _INTERNAL_SUBCLI,
    ('plugin-doctor', TYPE_MISSING_FROM_DOCS, 'categorize'): _INTERNAL_SUBCLI,
    ('plugin-doctor', TYPE_MISSING_FROM_DOCS, 'coverage'): _INTERNAL_SUBCLI,
    ('plugin-doctor', TYPE_MISSING_FROM_DOCS, 'cross-file'): _INTERNAL_SUBCLI,
    ('plugin-doctor', TYPE_MISSING_FROM_DOCS, 'extension'): _INTERNAL_SUBCLI,
    ('plugin-doctor', TYPE_MISSING_FROM_DOCS, 'extract'): _INTERNAL_SUBCLI,
    ('plugin-doctor', TYPE_MISSING_FROM_DOCS, 'inventory'): _INTERNAL_SUBCLI,
    ('plugin-doctor', TYPE_MISSING_FROM_DOCS, 'markdown'): _INTERNAL_SUBCLI,
    ('plugin-doctor', TYPE_MISSING_FROM_DOCS, 'references'): _INTERNAL_SUBCLI,
    ('plugin-doctor', TYPE_MISSING_FROM_DOCS, 'structure'): _INTERNAL_SUBCLI,
    ('plugin-doctor', TYPE_MISSING_FROM_DOCS, 'verify'): _INTERNAL_SUBCLI,
    ('tools-corpus-language-server', TYPE_MISSING_FROM_DOCS, 'serve'): _DAEMON_ENTRY_POINT,
    (
        'tools-marketplace-inventory',
        TYPE_SKIPPED,
        _mod.SKIP_NO_SUBPARSERS,
    ): _FILE_LOCAL_WALK_BLIND_SPOT,
}


@lru_cache(maxsize=1)
def _corpus() -> dict:
    """Derive the population and the findings in ONE pass at HEAD.

    ``analyze_documented_verb_set_drift_with_population`` is the population-returning
    entry point, so the size published here is the one the findings were actually
    derived against rather than a second walk that could disagree with it.
    """
    findings, population_size = analyze_with_population(MARKETPLACE)
    return {
        'population': population_size,
        'population_dirs': derive_population(MARKETPLACE),
        'findings': findings,
    }


def _bundle_of(finding: dict) -> str:
    """The bundle a finding's anchoring path belongs to, or ``'<unknown>'``.

    Derived from the path rather than carried on the finding: the rule anchors a
    ``verb_missing_from_docs`` on the SCRIPT and a ``phantom_documented_verb`` on
    the DOCUMENT, so there is no single finding field that names the owner.
    """
    parts = Path(str(finding.get('file', ''))).parts
    if 'bundles' in parts:
        index = parts.index('bundles')
        if index + 1 < len(parts):
            return parts[index + 1]
    return '<unknown>'


def _skill_of(finding: dict) -> str:
    """The skill directory name a finding's anchoring path belongs to."""
    parts = Path(str(finding.get('file', ''))).parts
    if 'skills' in parts:
        index = parts.index('skills')
        if index + 1 < len(parts):
            return parts[index + 1]
    return '<unknown>'


def _key(finding: dict) -> tuple[str, str, str]:
    """The triage key of one finding — ``(skill, type, verb)``."""
    details = finding.get('details') or {}
    return (_skill_of(finding), str(finding.get('type', '')), str(details.get('verb', details.get('reason', ''))))


def _by_type(findings: list[dict]) -> Counter:
    return Counter(str(finding.get('type', '<untyped>')) for finding in findings)


def _by_bundle(findings: list[dict]) -> Counter:
    return Counter(_bundle_of(finding) for finding in findings)


def _skip_reasons(findings: list[dict]) -> Counter:
    """The skip reasons actually REACHED on this tree, by count.

    The rule declares six skip states. Which of them a real tree reaches is a
    property of the tree, not of the rule, so it is published rather than asserted
    to any particular shape.
    """
    return Counter(
        str((finding.get('details') or {}).get('reason', '<unstated>'))
        for finding in findings
        if finding.get('type') == TYPE_SKIPPED
    )


def corpus_report() -> str:
    """Render the population, the finding census, and the reached skip states."""
    corpus = _corpus()
    findings = corpus['findings']
    per_type = _by_type(findings)
    per_bundle = _by_bundle(findings)
    skips = _skip_reasons(findings)
    owned = [f for f in findings if _bundle_of(f) == OWNED_BUNDLE]
    lines = [
        f'population: {corpus["population"]}',
        f'findings: {len(findings)}',
        f'types_with_findings: {len(per_type)}',
    ]
    lines.extend(f'  {name}: {count}' for name, count in sorted(per_type.items()))
    lines.append(f'bundles_with_findings: {len(per_bundle)}')
    lines.extend(f'  {name}: {count}' for name, count in sorted(per_bundle.items()))
    lines.append(f'skip_reasons_reached: {len(skips)}')
    lines.extend(f'  {name}: {count}' for name, count in sorted(skips.items()))
    lines.append(f'{OWNED_BUNDLE}_findings: {len(owned)}')
    lines.extend(f'  {_key(f)}' for f in sorted(owned, key=_key))
    lines.append(f'triaged_entries: {len(TRIAGED)}')
    return '\n'.join(lines)


def test_the_derived_population_is_non_empty():
    """Nothing below reports against a population of zero.

    The rule's own ``verb_set_drift_empty_population`` guard fires for exactly this
    state, so a run that tripped it would be reporting a derivation failure rather
    than a clean tree — and every figure the other tests publish would be a zero
    over nothing.
    """
    corpus = _corpus()

    assert corpus['population'] > 0, (
        f'The population is EMPTY — no skill carrying a "## Canonical invocations" '
        f'block was found, so the rule examined nothing.\n{corpus_report()}'
    )
    assert corpus['population'] == len(corpus['population_dirs']), (
        f'The published population size disagrees with the walk it came from.\n{corpus_report()}'
    )
    assert not [f for f in corpus['findings'] if f.get('type') == TYPE_EMPTY_POPULATION], (
        f'The empty-population guard fired, so this run is a derivation failure, not a measurement.\n{corpus_report()}'
    )


def test_every_finding_publishes_the_population_it_was_derived_from():
    """A finding without its denominator cannot be read.

    ``population_size`` rides on the finding precisely so a reader can tell a
    finding drawn from a whole-tree walk from one drawn from a partial one. The
    check is that EVERY finding carries the same derived size — a mixture would
    mean two different walks contributed to one report.
    """
    corpus = _corpus()
    findings = corpus['findings']
    if not findings:
        return

    sizes = {(f.get('details') or {}).get('population_size') for f in findings}
    assert sizes == {corpus['population']}, (
        f'Findings publish population sizes {sorted(str(s) for s in sizes)}, but the '
        f'walk derived {corpus["population"]}.\n{corpus_report()}'
    )


def test_the_report_publishes_the_live_figures_and_reconciles():
    """The live finding count and population are published, and the census adds up.

    A per-type census that does not reconcile to the total is the shape in which a
    class quietly stops being counted, so the reconciliation is asserted rather
    than assumed. The report is printed so the figures come from THIS run.
    """
    corpus = _corpus()
    report = corpus_report()
    print(report)

    per_type = _by_type(corpus['findings'])
    assert f'population: {corpus["population"]}' in report, report
    assert f'findings: {len(corpus["findings"])}' in report, report
    assert sum(per_type.values()) == len(corpus['findings']), (
        f'the per-type census does not reconcile to the finding total.\n{report}'
    )
    assert sum(_by_bundle(corpus['findings']).values()) == len(corpus['findings']), (
        f'the per-bundle census does not reconcile to the finding total.\n{report}'
    )


def test_the_reached_skip_states_are_published_and_all_declared():
    """Which skip states a real tree reaches is published; none may be unrecognised.

    Reachability is a property of the tree and is reported, not asserted to a
    shape: a tree whose every script the walk can read reaches no skip at all, and
    that is a legitimate state rather than a coverage failure. What IS asserted is
    that every reason reached belongs to the rule's declared vocabulary — an
    unrecognised reason means a skip path grew without the vocabulary following it,
    and a reader would have no way to tell what coverage was lost.
    """
    declared = {
        _mod.SKIP_UNREADABLE,
        _mod.SKIP_UNPARSEABLE,
        _mod.SKIP_DYNAMIC,
        _mod.SKIP_UNRESOLVED_GROUP,
        _mod.SKIP_NO_SUBPARSERS,
        _mod.SKIP_NO_ROOT_PARSER,
    }
    reached = set(_skip_reasons(_corpus()['findings']))

    assert reached <= declared, (
        f"Skip reason(s) {sorted(reached - declared)} are not in the rule's declared "
        f'vocabulary {sorted(declared)}.\n{corpus_report()}'
    )


def test_owned_bundle_findings_are_fixed_or_triaged():
    """Every finding on this bundle's own surfaces is fixed, or accepted with a reason.

    The rule runs whole-marketplace, so this is deliberately scoped to
    :data:`OWNED_BUNDLE` rather than to the tree: holding every other bundle's
    documentation to this gate is neither this module's job nor this plan's scope,
    and a suite that fails on a skill it does not own gets suppressed rather than
    fixed.

    A RED run IS the work list — the message names each untriaged finding by
    ``(skill, type, verb)``, which is the same key :data:`TRIAGED` accepts.
    """
    corpus = _corpus()
    owned = [f for f in corpus['findings'] if _bundle_of(f) == OWNED_BUNDLE]
    untriaged = [f for f in owned if _key(f) not in TRIAGED]

    assert not untriaged, (
        f'REMAINING {len(untriaged)} untriaged {OWNED_BUNDLE} finding(s), out of '
        f'{len(owned)} on this bundle and {len(corpus["findings"])} across a '
        f'population of {corpus["population"]} skill(s). Fix each, or add it to '
        f'TRIAGED with the reason it is not a defect:\n'
        + '\n'.join(f'  {_key(f)}: {(f.get("extra") or {}).get("message", "")}' for f in sorted(untriaged, key=_key))
        + f'\n{corpus_report()}'
    )


def test_no_triage_entry_has_gone_stale():
    """The matched control for the triage registry: an entry that no longer fires is an error.

    Without this, :data:`TRIAGED` decays into a permanent suppression list — every
    accepted finding stays accepted after the underlying cause is gone, and
    "triaged" becomes indistinguishable from "ignored". Holding the registry from
    both sides is what keeps each entry a live claim about the tree.
    """
    corpus = _corpus()
    live = {_key(f) for f in corpus['findings'] if _bundle_of(f) == OWNED_BUNDLE}
    stale = sorted(key for key in TRIAGED if key not in live)

    assert not stale, (
        f'{len(stale)} TRIAGED entr(ies) no longer correspond to a live finding — '
        f'remove them rather than carrying a suppression for a fixed defect: '
        f'{stale}\n{corpus_report()}'
    )


def test_the_rule_derives_without_a_help_cache():
    """The contraindication: this rule reads no ``--help`` and consumes no cache.

    A stale plugin-doctor help cache has previously manufactured hundreds of false
    ``manage-invocation`` findings, so a figure quoted off a doctor rule is owed a
    cache check. This test IS that check for this rule, and it discharges it by
    establishing there is no cache in the path at all: the derivation is a pure
    ``ast.parse`` walk, so it spawns nothing and reads nothing that could be stale.

    The assertion is on the analyzer SOURCE rather than on behaviour because the
    property is an absence — no subprocess, no ``argparse_surface`` import — and an
    absence has no call to observe. ``argparse_surface`` is named explicitly: it is
    the shared live-``--help`` derivation the caching consumers read, and the one
    thing whose appearance here would silently put this rule behind that cache.
    """
    source = Path(_mod.__file__).read_text(encoding='utf-8')

    assert 'subprocess' not in source, (
        'the drift analyzer has grown a subprocess call — its figures would then '
        'depend on live --help output and the help-cache staleness question would '
        'apply to them.'
    )
    assert 'argparse_surface' not in source, (
        'the drift analyzer now consumes argparse_surface (the shared live --help '
        "derivation), so its figures sit behind the help cache and this module's "
        'published counts can no longer be read as cache-independent.'
    )
    assert 'import ast' in source, 'the drift analyzer no longer AST-walks; the derivation contract changed.'


def test_a_deliberately_undocumented_verb_still_fails_the_rule(tmp_path):
    """The matched negative control for every real-tree assertion above.

    ⛔ Without this, a clean ``OWNED_BUNDLE`` verdict would be satisfied by a rule
    that had stopped firing altogether — the real-tree tests assert an ABSENCE, and
    an absence is only meaningful once the detector is shown to be live in the same
    session. A synthetic skill carrying one registered-but-undocumented verb is run
    through the SAME entry point the corpus above uses, and must report it.
    """
    for rel_path, content in documented_verb_drift_files(
        skill='fixture-control',
        registered=('compose', 'record-step'),
        documented=('compose',),
    ).items():
        target = tmp_path / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')

    findings, population_size = analyze_with_population(tmp_path)

    assert population_size == 1, (
        f'the control fixture must contribute exactly one in-scope skill, got {population_size}'
    )
    assert [f['type'] for f in findings] == [TYPE_MISSING_FROM_DOCS], (
        f'the detector did not fire on a deliberately undocumented verb, so every '
        f'clean verdict above is unfalsifiable; got {[f["type"] for f in findings]}'
    )
    assert findings[0]['details']['verb'] == 'record-step'
