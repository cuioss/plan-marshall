# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``canonical-enum-choices-drift`` rule analyzer.

The analyzer compares a documented ``{a|b|c}`` enum in a skill's
``## Canonical invocations`` block (the hand-maintained mirror) against the live
argparse ``choices=`` of the flag the enum describes, scoped to the documented
subcommand path. The authority is resolved statically from the script AST,
reading ``choices=`` only — never a ``description=`` hand-list — so the
declared-vs-derived distinction holds. Every unresolvable site fails closed.

Test layers:
  * (D6a) A deliberately truncated enum is flagged, with the omitted member
    surfaced in ``missing_from_doc``.
  * (D6b) A correct enum passes.
  * (D6c) The population derived over the REAL marketplace tree is non-empty and
    contains a known-good member (the positive-population assertion) — a guard
    whose glob matched nothing would be indistinguishable from a clean one
    without it.
  * Declared-vs-derived: a misleading ``description=`` hand-list is never read as
    the authority; only ``choices=`` is.
  * Subcommand scoping: a flag that is free-form (no ``choices=``) in the
    documented subcommand is never judged against a *different* subcommand's
    choices — the ``manage-tasks`` ``update``-vs-``list`` ``--status`` shape.
  * Fail-closed: a flag with no ``choices=`` and an unresolvable ``choices=``
    each emit nothing.
  * A ``choices=CONST`` reference is resolved to the constant's members.
"""

import ast
from pathlib import Path

from conftest import MARKETPLACE_ROOT, load_script_module

from _plugin_doctor_fixtures import assert_analyzer_findings

_mod = load_script_module(
    'pm-plugin-development', 'plugin-doctor', '_analyze_canonical_enum_drift.py',
    '_analyze_canonical_enum_drift',
)
analyze_canonical_enum_drift = _mod.analyze_canonical_enum_drift
derive_population = _mod.derive_population
RULE_ID = _mod.RULE_ID

_FENCE = '```'


def _write_bundle(
    root: Path,
    *,
    doc_enum: str,
    script_body: str,
    subcommand: str = 'add',
    flag: str = 'kind',
    bundle: str = 'mybundle',
    skill: str = 'myskill',
    script: str = 'myscript',
) -> Path:
    """Write a synthetic bundle: one SKILL.md canonical block + its argparse script.

    ``doc_enum`` is the ``{...}`` body documented for ``--{flag}`` under
    ``subcommand``; ``script_body`` is the full Python source of the argparse
    script it is compared against.
    """
    skill_dir = root / bundle / 'skills' / skill
    scripts_dir = skill_dir / 'scripts'
    scripts_dir.mkdir(parents=True, exist_ok=True)
    (scripts_dir / f'{script}.py').write_text(script_body, encoding='utf-8')
    skill_md = skill_dir / 'SKILL.md'
    skill_md.write_text(
        '# My Skill\n\n'
        '## Canonical invocations\n\n'
        f'### {subcommand}\n\n'
        f'{_FENCE}bash\n'
        f'python3 .plan/execute-script.py {bundle}:{skill}:{script} {subcommand} \\\n'
        f'  --{flag} {{{doc_enum}}}\n'
        f'{_FENCE}\n',
        encoding='utf-8',
    )
    return skill_md


_SCRIPT_LITERAL_CHOICES = '''\
import argparse


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')
    add = sub.add_parser('add')
    add.add_argument('--kind', choices=['x', 'y', 'z'])


if __name__ == '__main__':
    main()
'''


def test_flags_truncated_enum(tmp_path):
    """(D6a) A block documenting fewer members than choices= is flagged."""
    _write_bundle(tmp_path, doc_enum='x|y', script_body=_SCRIPT_LITERAL_CHOICES)
    findings = assert_analyzer_findings(analyze_canonical_enum_drift, tmp_path, [RULE_ID])
    finding = findings[0]
    assert finding['details']['flag'] == '--kind'
    assert finding['details']['missing_from_doc'] == ['z']
    assert finding['details']['choices'] == ['x', 'y', 'z']
    assert finding['details']['population_size'] >= 1


def test_passes_correct_enum(tmp_path):
    """(D6b) A block whose documented enum equals choices= is clean."""
    _write_bundle(tmp_path, doc_enum='x|y|z', script_body=_SCRIPT_LITERAL_CHOICES)
    assert_analyzer_findings(analyze_canonical_enum_drift, tmp_path, [])


def test_flags_invented_value(tmp_path):
    """A documented member absent from choices= is flagged as not_in_choices."""
    _write_bundle(tmp_path, doc_enum='x|y|z|w', script_body=_SCRIPT_LITERAL_CHOICES)
    findings = assert_analyzer_findings(analyze_canonical_enum_drift, tmp_path, [RULE_ID])
    assert findings[0]['details']['not_in_choices'] == ['w']


def test_positive_population_over_real_tree():
    """(D6c) The real-tree population is non-empty and holds a known-good member.

    Without this a glob that matched zero canonical blocks would look identical
    to one whose every block passed. The known-good member is
    ``manage-lessons`` ``add --category``, whose choices= derive from
    LESSON_CATEGORIES across a cross-module constant reference.
    """
    population = derive_population(MARKETPLACE_ROOT)
    assert len(population) > 0
    resolved = [s for s in population if s.resolved]
    assert resolved, 'no enum site resolved an argparse-choices authority'
    known = [
        s
        for s in population
        if s.notation == 'plan-marshall:manage-lessons:manage-lessons'
        and s.flag == 'category'
        and s.subcommand == ('add',)
    ]
    assert known, 'known-good member manage-lessons add --category not in population'
    site = known[0]
    assert site.resolved and not site.diverged
    assert site.choices == frozenset({'bug', 'improvement', 'anti-pattern', 'arch-constraint'})


def test_description_hand_list_is_not_the_authority(tmp_path):
    """A misleading description= hand-list is never read as the choices authority.

    choices= is the derived source tuple (correct, complete); description= lists
    a stale subset. Reading description= would manufacture a false positive; the
    guard must read choices= only, so a doc that matches choices= is clean.
    """
    script = '''\
import argparse

KINDS = ('x', 'y', 'z')


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')
    add = sub.add_parser('add')
    add.add_argument(
        '--kind',
        choices=KINDS,
        help='one of x, y (description hand-list is stale and must be ignored)',
    )


if __name__ == '__main__':
    main()
'''
    _write_bundle(tmp_path, doc_enum='x|y|z', script_body=script)
    assert_analyzer_findings(analyze_canonical_enum_drift, tmp_path, [])


def test_free_form_flag_in_documented_subcommand_not_flagged(tmp_path):
    """A flag free-form in the documented subcommand is not judged against another's choices.

    The ``manage-tasks`` shape: ``update --status`` is free-form while
    ``list --status`` is choices-constrained. A block documenting ``update
    --status {a|b}`` must NOT be compared against ``list``'s choices.
    """
    script = '''\
import argparse


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')
    p_update = sub.add_parser('update')
    p_update.add_argument('--status', help='new status (free-form)')
    p_list = sub.add_parser('list')
    p_list.add_argument('--status', choices=['a', 'b', 'all'])


if __name__ == '__main__':
    main()
'''
    _write_bundle(
        tmp_path, doc_enum='a|b', script_body=script, subcommand='update', flag='status'
    )
    assert_analyzer_findings(analyze_canonical_enum_drift, tmp_path, [])


def test_flag_without_choices_skipped(tmp_path):
    """A documented enum on a flag that has no choices= anywhere is skipped."""
    script = '''\
import argparse


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')
    add = sub.add_parser('add')
    add.add_argument('--kind', help='free-form')


if __name__ == '__main__':
    main()
'''
    _write_bundle(tmp_path, doc_enum='x|y', script_body=script)
    assert_analyzer_findings(analyze_canonical_enum_drift, tmp_path, [])


def test_unresolvable_choices_fails_closed(tmp_path):
    """A choices= expression that cannot be resolved to a concrete set emits nothing."""
    script = '''\
import argparse


def _dynamic_choices():
    return ['x', 'y']


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')
    add = sub.add_parser('add')
    add.add_argument('--kind', choices=_dynamic_choices())


if __name__ == '__main__':
    main()
'''
    _write_bundle(tmp_path, doc_enum='x|y', script_body=script)
    assert_analyzer_findings(analyze_canonical_enum_drift, tmp_path, [])


def test_resolves_constant_choices(tmp_path):
    """choices=CONST resolves to the constant's members; a truncated doc is flagged."""
    script = '''\
import argparse

KINDS = ('x', 'y', 'z')


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')
    add = sub.add_parser('add')
    add.add_argument('--kind', choices=list(KINDS))


if __name__ == '__main__':
    main()
'''
    _write_bundle(tmp_path, doc_enum='x|y', script_body=script)
    findings = assert_analyzer_findings(analyze_canonical_enum_drift, tmp_path, [RULE_ID])
    assert findings[0]['details']['missing_from_doc'] == ['z']


# ---------------------------------------------------------------------------
# Shared fence: every enum is scoped to the invocation ABOVE it, not the first.
# ---------------------------------------------------------------------------
_SHARED_FENCE_SCRIPT = '''\
import argparse


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')
    add = sub.add_parser('add')
    add.add_argument('--kind', choices=['x', 'y'])
    remove = sub.add_parser('remove')
    remove.add_argument('--kind', choices=['p', 'q'])


if __name__ == '__main__':
    main()
'''


def _write_shared_fence_bundle(root: Path, *, add_enum: str, remove_enum: str) -> Path:
    """One fenced block documenting TWO invocations under DIFFERENT subcommands.

    The shape the notation latch got wrong: a single fence carrying an ``add``
    invocation and a ``remove`` invocation, each with its own ``--kind`` enum.
    """
    skill_dir = root / 'mybundle' / 'skills' / 'myskill'
    scripts_dir = skill_dir / 'scripts'
    scripts_dir.mkdir(parents=True, exist_ok=True)
    (scripts_dir / 'myscript.py').write_text(_SHARED_FENCE_SCRIPT, encoding='utf-8')
    skill_md = skill_dir / 'SKILL.md'
    notation = 'mybundle:myskill:myscript'
    skill_md.write_text(
        '# My Skill\n\n'
        '## Canonical invocations\n\n'
        f'{_FENCE}bash\n'
        f'python3 .plan/execute-script.py {notation} add \\\n'
        f'  --kind {{{add_enum}}}\n'
        f'python3 .plan/execute-script.py {notation} remove \\\n'
        f'  --kind {{{remove_enum}}}\n'
        f'{_FENCE}\n',
        encoding='utf-8',
    )
    return skill_md


def test_second_invocation_in_a_shared_fence_owns_the_enums_below_it(tmp_path):
    """Two correctly-documented invocations in one fence yield ZERO findings.

    The notation latch recorded only the FIRST invocation's notation and
    subcommand path for the whole block, so ``remove``'s enum was compared
    against ``add``'s choices and flagged. Both enums here are correct for their
    own subcommand, so the only way to produce a finding is to attribute one to
    the wrong invocation.
    """
    _write_shared_fence_bundle(tmp_path, add_enum='x|y', remove_enum='p|q')

    assert_analyzer_findings(analyze_canonical_enum_drift, tmp_path, [])


def test_shared_fence_sites_carry_their_own_subcommand_path(tmp_path):
    """Each site's ``subcommand`` is the one the invocation line above it names.

    Asserted positively and per site, rather than only through the absence of a
    finding: an attribution regression that happened to leave the enums
    coincidentally equal would satisfy the zero-findings test above.
    """
    _write_shared_fence_bundle(tmp_path, add_enum='x|y', remove_enum='p|q')

    by_subcommand = {
        site.subcommand: sorted(site.documented) for site in derive_population(tmp_path)
    }

    assert by_subcommand == {('add',): ['x', 'y'], ('remove',): ['p', 'q']}


def test_shared_fence_second_invocation_drift_is_still_caught(tmp_path):
    """The control: a genuinely wrong second enum is flagged against ITS subcommand.

    Without this, the fix would be indistinguishable from one that simply stopped
    examining anything below the first invocation.

    The wrong enum carries TWO members (``p|z`` against a live ``p|q``) rather
    than one. A one-member body IS collected — it is filed under
    ``single_member_ambiguous`` and never compared — so spelling the drift that
    way would produce no finding at all and would test the one-member rule
    instead of the attribution this control is for. This said "never enters the
    population", which stopped being true when that rule changed.
    """
    _write_shared_fence_bundle(tmp_path, add_enum='x|y', remove_enum='p|z')

    findings = assert_analyzer_findings(analyze_canonical_enum_drift, tmp_path, [RULE_ID])

    assert findings[0]['details']['missing_from_doc'] == ['q']
    assert findings[0]['details']['not_in_choices'] == ['z']
    assert findings[0]['details']['subcommand'] == 'remove'


def test_real_tree_shared_fence_sites_resolve_to_their_own_invocation():
    """Over the REAL tree, a site below a second invocation names that invocation.

    The live subject is ``plan-marshall:manage-run-config``'s canonical block,
    whose fence documents four ``architecture-refresh`` invocations in sequence,
    beginning with ``get-tier-0`` and including ``set-tier-0`` and
    ``set-tier-1``. Under the latch every enum in that fence was attributed to
    its FIRST invocation — ``get-tier-0``, whose flag has no ``choices=`` — so
    the ``set-tier-*`` sites resolved to ``choices is None`` and were never
    compared at all.

    Asserted by property (a site exists whose documented members equal its
    resolved choices under its own subcommand) rather than by line number, which
    moves whenever the document is edited.
    """
    population = derive_population(MARKETPLACE_ROOT)
    tier_sites = {
        site.subcommand: (sorted(site.documented), sorted(site.choices) if site.choices else None)
        for site in population
        if site.subcommand[:1] == ('architecture-refresh',)
    }

    assert ('architecture-refresh', 'set-tier-1') in tier_sites
    documented, choices = tier_sites[('architecture-refresh', 'set-tier-1')]
    assert choices is not None
    assert documented == choices


# ---------------------------------------------------------------------------
# The brace-less enum form, and the shapes it must NOT read as one.
# ---------------------------------------------------------------------------
def _write_braceless_bundle(root: Path, doc_flag_and_members: str) -> Path:
    """A bundle whose canonical block documents ``--kind`` in brace-less form."""
    skill_dir = root / 'mybundle' / 'skills' / 'myskill'
    scripts_dir = skill_dir / 'scripts'
    scripts_dir.mkdir(parents=True, exist_ok=True)
    (scripts_dir / 'myscript.py').write_text(_SCRIPT_LITERAL_CHOICES, encoding='utf-8')
    (skill_dir / 'SKILL.md').write_text(
        '# My Skill\n\n'
        '## Canonical invocations\n\n'
        f'{_FENCE}bash\n'
        'python3 .plan/execute-script.py mybundle:myskill:myscript add \\\n'
        f'  {doc_flag_and_members}\n'
        f'{_FENCE}\n',
        encoding='utf-8',
    )
    return skill_dir / 'SKILL.md'


def test_braceless_pipe_enum_is_collected_and_compared(tmp_path):
    """``--kind x|y`` is an enum claim and is compared, not skipped.

    Requiring braces made the brace-less spelling invisible: the flag was never
    compared and the sweep reported clean over a site it had not read.
    """
    _write_braceless_bundle(tmp_path, '--kind x|y')

    findings = assert_analyzer_findings(analyze_canonical_enum_drift, tmp_path, [RULE_ID])

    assert findings[0]['details']['missing_from_doc'] == ['z']


def test_braceless_enum_matching_choices_is_clean(tmp_path):
    """The control: a correct brace-less enum yields nothing."""
    _write_braceless_bundle(tmp_path, '--kind x|y|z')

    assert_analyzer_findings(analyze_canonical_enum_drift, tmp_path, [])


def test_optional_argument_brackets_are_not_swallowed_into_a_member(tmp_path):
    """``[--kind x|y|z]`` documents an OPTIONAL flag, not a member named ``z]``.

    A permissive member class read the closing bracket as part of the last
    member and manufactured a drift finding out of punctuation — observed on the
    real tree against a correctly-documented flag.
    """
    _write_braceless_bundle(tmp_path, '[--kind x|y|z]')

    assert_analyzer_findings(analyze_canonical_enum_drift, tmp_path, [])


def test_a_single_metavar_is_not_read_as_a_one_member_enum(tmp_path):
    """``--kind VALUE`` carries no pipe and is not an enum claim."""
    _write_braceless_bundle(tmp_path, '--kind VALUE')

    assert derive_population(tmp_path) == []


def test_a_mutually_exclusive_flag_list_is_not_read_as_an_enum(tmp_path):
    """``--kind --a|--b`` is a group of FLAGS, not one flag's member set.

    Reading it as an enum would compare ``--kind``'s choices against a list of
    other flags' names.
    """
    _write_braceless_bundle(tmp_path, '--kind --a|--b')

    assert derive_population(tmp_path) == []


# ---------------------------------------------------------------------------
# The declarative dict-spec parser form.
# ---------------------------------------------------------------------------
_SCRIPT_DICT_SPEC = '''\
import argparse

KINDS = ['x', 'y', 'z']


def build():
    return dict(
        description='demo',
        subcommands=[
            {
                'name': 'add',
                'args': [
                    {'flags': ['--kind'], 'dest': 'kind', 'choices': KINDS},
                ],
            },
        ],
    )


def main():
    parser = argparse.ArgumentParser()
    parser.parse_args()


if __name__ == '__main__':
    main()
'''


def test_declarative_dict_spec_choices_resolve(tmp_path):
    """A ``{'flags': [...], 'choices': [...]}`` spec is an authority.

    Scripts that build their parser from a data structure have no
    ``add_argument(..., choices=...)`` call to walk, so every documented enum on
    them resolved to "no authority" and was silently never compared — the same
    unread-population failure this rule exists to catch, inside the rule. The
    spec is a same-file parse; no import hop is involved.
    """
    skill_dir = tmp_path / 'mybundle' / 'skills' / 'myskill'
    scripts_dir = skill_dir / 'scripts'
    scripts_dir.mkdir(parents=True)
    (scripts_dir / 'myscript.py').write_text(_SCRIPT_DICT_SPEC, encoding='utf-8')
    (skill_dir / 'SKILL.md').write_text(
        '# My Skill\n\n'
        '## Canonical invocations\n\n'
        f'{_FENCE}bash\n'
        'python3 .plan/execute-script.py mybundle:myskill:myscript add \\\n'
        '  --kind {x|y}\n'
        f'{_FENCE}\n',
        encoding='utf-8',
    )

    population = derive_population(tmp_path)

    assert len(population) == 1
    assert population[0].resolved is True
    assert population[0].choices == frozenset({'x', 'y', 'z'})
    findings = assert_analyzer_findings(analyze_canonical_enum_drift, tmp_path, [RULE_ID])
    assert findings[0]['details']['missing_from_doc'] == ['z']


# ---------------------------------------------------------------------------
# Declared coverage — the share the sweep did NOT compare.
# ---------------------------------------------------------------------------
def test_coverage_reports_the_unresolved_share_and_its_causes(tmp_path):
    """An unresolved site is counted and ATTRIBUTED, not silently dropped.

    A finding count answers "how many enums are wrong"; it cannot answer "how
    many were checked". Here one site resolves and one names a notation that
    resolves to no script at all.
    """
    _write_bundle(tmp_path, doc_enum='x|y|z', script_body=_SCRIPT_LITERAL_CHOICES)
    (tmp_path / 'mybundle' / 'skills' / 'myskill' / 'SKILL.md').write_text(
        '# My Skill\n\n'
        '## Canonical invocations\n\n'
        f'{_FENCE}bash\n'
        'python3 .plan/execute-script.py mybundle:myskill:myscript add \\\n'
        '  --kind {x|y|z}\n'
        f'{_FENCE}\n'
        f'{_FENCE}bash\n'
        'python3 .plan/execute-script.py mybundle:myskill:absent add \\\n'
        '  --kind {a|b}\n'
        f'{_FENCE}\n',
        encoding='utf-8',
    )

    coverage = _mod.derive_coverage(derive_population(tmp_path))

    assert coverage['population_size'] == 2
    assert coverage['resolved'] == 1
    assert coverage['unresolved'] == 1
    assert coverage['unresolved_fraction'] == 0.5
    assert coverage['unresolved_causes'] == {
        _mod.UNRESOLVED_NOTATION: 1,
        _mod.UNRESOLVED_SCRIPT_UNPARSEABLE: 0,
        _mod.UNRESOLVED_PARSER_NOT_DERIVED: 0,
        _mod.UNRESOLVED_AUTHORITY_INCOMPLETE: 0,
        _mod.UNRESOLVED_NO_CHOICES_DECLARED: 0,
        _mod.UNRESOLVED_CHOICES_UNRESOLVABLE: 0,
        _mod.UNRESOLVED_SINGLE_MEMBER: 0,
    }
    # An unresolvable notation is a real gap, so it counts as a blind spot.
    assert coverage['blind_spots'] == 1


def test_coverage_over_an_empty_population_reports_zero_not_a_division_error():
    """An empty population reports a 0.0 share rather than raising.

    The cause census is COMPLETE even here: every cause reads ``0`` rather than
    being omitted, so an absent cause is never indistinguishable from one folded
    into a neighbour.
    """
    assert _mod.derive_coverage([]) == {
        'population_size': 0,
        'resolved': 0,
        'unresolved': 0,
        'unresolved_fraction': 0.0,
        'blind_spots': 0,
        'unresolved_causes': dict.fromkeys(_mod.UNRESOLVED_CAUSES, 0),
    }


def test_a_flag_with_no_choices_is_a_different_cause_from_an_unresolvable_one(tmp_path):
    """The two fail-closed skips carry DIFFERENT risk and are reported apart.

    ``no_choices_declared`` means this rule's authority is established as ABSENT:
    the parser was fully modelled and declares no ``choices=`` for the flag.
    ``choices_unresolvable`` means a real enum claim was made and went
    unverified. Only the second is a blind spot, which is why the census sums
    ``blind_spots`` over every cause except the first.

    ⛔ Established-absent is NOT harmless, and this docstring said so twice —
    "makes no enum claim the script can contradict, nothing to check" and
    "mostly harmless" — both being the exact phrasings the analyzer's own ⛔
    forbids. A flag in that bucket is routinely constrained somewhere this rule
    does not read: ``untrusted-ingestion validate --schema`` rejects an unknown
    value and names the four it accepts. What the bucket licenses is "this rule
    has no oracle here", never "nothing constrains this flag".
    """
    script = '''\
import argparse

from somewhere_else import KINDS


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')
    add = sub.add_parser('add')
    add.add_argument('--kind', choices=KINDS)
    add.add_argument('--freeform')


if __name__ == '__main__':
    main()
'''
    skill_dir = tmp_path / 'mybundle' / 'skills' / 'myskill'
    (skill_dir / 'scripts').mkdir(parents=True)
    (skill_dir / 'scripts' / 'myscript.py').write_text(script, encoding='utf-8')
    (skill_dir / 'SKILL.md').write_text(
        '# My Skill\n\n'
        '## Canonical invocations\n\n'
        f'{_FENCE}bash\n'
        'python3 .plan/execute-script.py mybundle:myskill:myscript add \\\n'
        '  --kind {x|y} --freeform {p|q}\n'
        f'{_FENCE}\n',
        encoding='utf-8',
    )

    causes = _mod.derive_coverage(derive_population(tmp_path))['unresolved_causes']

    assert causes[_mod.UNRESOLVED_CHOICES_UNRESOLVABLE] == 1
    assert causes[_mod.UNRESOLVED_NO_CHOICES_DECLARED] == 1


def test_findings_publish_the_unresolved_share(tmp_path):
    """Every finding carries the coverage figures alongside the population size."""
    _write_bundle(tmp_path, doc_enum='x|y', script_body=_SCRIPT_LITERAL_CHOICES)

    findings = assert_analyzer_findings(analyze_canonical_enum_drift, tmp_path, [RULE_ID])

    details = findings[0]['details']
    assert details['unresolved_notation_fraction'] == 0.0
    assert details['unresolved_notation_blind_spots'] == 0
    assert details['unresolved_notation_causes'] == dict.fromkeys(_mod.UNRESOLVED_CAUSES, 0)


def test_real_tree_coverage_is_published_and_non_trivial():
    """Over the REAL tree the declared gap is a real number, not a formality.

    Asserted as a range rather than a literal: the exact share moves whenever a
    skill documents another enum, and pinning it would make an unrelated doc
    edit fail this test. What must hold is that the population is non-empty and
    the unresolved share is genuinely published.
    """
    coverage = _mod.derive_coverage(derive_population(MARKETPLACE_ROOT))

    assert coverage['population_size'] > 0
    assert coverage['resolved'] + coverage['unresolved'] == coverage['population_size']
    assert 0.0 < coverage['unresolved_fraction'] < 1.0
    assert set(coverage['unresolved_causes']) == set(_mod.UNRESOLVED_CAUSES)
    assert sum(coverage['unresolved_causes'].values()) == coverage['unresolved']


def test_a_parser_built_by_an_imported_helper_is_a_blind_spot_not_nothing_to_check(tmp_path):
    """The largest gap must not be filed as "this flag declares no choices".

    A script whose parser is built by an IMPORTED helper has no
    ``ArgumentParser()`` in the file the notation names, so the walk models no
    parser at all and the authority key is absent — indistinguishable, on key
    presence alone, from a flag that genuinely declares nothing. Reading the
    first as the second reports the largest coverage gap as reassurance, which
    is the failure this rule exists to catch, committed by its own figure.
    """
    skill_dir = tmp_path / 'mybundle' / 'skills' / 'myskill'
    (skill_dir / 'scripts').mkdir(parents=True)
    (skill_dir / 'scripts' / 'myscript.py').write_text(
        'from build_cli import build\n\n\ndef main():\n    build().parse_args()\n',
        encoding='utf-8',
    )
    (skill_dir / 'SKILL.md').write_text(
        '# My Skill\n\n'
        '## Canonical invocations\n\n'
        f'{_FENCE}bash\n'
        'python3 .plan/execute-script.py mybundle:myskill:myscript run \\\n'
        '  --mode {a|b}\n'
        f'{_FENCE}\n',
        encoding='utf-8',
    )

    coverage = _mod.derive_coverage(derive_population(tmp_path))

    assert coverage['unresolved_causes'][_mod.UNRESOLVED_PARSER_NOT_DERIVED] == 1
    assert coverage['unresolved_causes'][_mod.UNRESOLVED_NO_CHOICES_DECLARED] == 0
    assert coverage['blind_spots'] == 1


def test_a_modelled_parser_with_no_choices_is_not_a_blind_spot(tmp_path):
    """The control: an established-absent authority is not counted as a blind spot.

    The fixture's parser IS fully modelled and declares no ``choices=`` for the
    flag, so this rule's authority over it is established as absent rather than
    merely unread — the one cause ``blind_spots`` excludes. Without this control
    the split above would be indistinguishable from calling every unresolved site
    a blind spot.

    Phrased as "declares free-form … nothing to check" until round 8. That is
    true of THIS fixture's flag and false as a description of the bucket, which
    is why the analyzer's ⛔ forbids both words: a live member of it
    (``untrusted-ingestion validate --schema``) rejects unknown values in its
    handler. A control's docstring should describe the property it controls for,
    not generalise from its own fixture.
    """
    _write_bundle(tmp_path, doc_enum='x|y|z', script_body=_SCRIPT_LITERAL_CHOICES, flag='freeform')

    coverage = _mod.derive_coverage(derive_population(tmp_path))

    assert coverage['unresolved_causes'][_mod.UNRESOLVED_NO_CHOICES_DECLARED] == 1
    assert coverage['unresolved_causes'][_mod.UNRESOLVED_PARSER_NOT_DERIVED] == 0
    assert coverage['blind_spots'] == 0


def test_real_tree_blind_spot_count_is_published_and_dominated_by_underived_parsers():
    """Over the REAL tree the blind-spot figure is the actionable one.

    The first assertion is a genuine INVARIANT: the census is complete over
    ``UNRESOLVED_CAUSES`` and ``no_choices_declared`` is the only excluded cause,
    so the identity holds for any tree.

    ⛔ The two below it are NOT invariants, and this docstring called all three
    invariants once. They describe the census as it stands: modelling more parser
    surfaces — following the ``script-shared`` build-CLI factory, say — drives
    ``parser_surface_not_derived`` to zero and reddens them on an IMPROVEMENT the
    suite should reward. They are kept as a tripwire that the census is still
    non-trivial. When a real improvement makes one false, DELETE it; do not
    "fix" it by weakening the census.
    """
    coverage = _mod.derive_coverage(derive_population(MARKETPLACE_ROOT))
    causes = coverage['unresolved_causes']

    assert coverage['blind_spots'] == coverage['unresolved'] - causes[_mod.UNRESOLVED_NO_CHOICES_DECLARED]
    # Current-census tripwires — see the ⛔ above before changing either.
    assert coverage['blind_spots'] > causes[_mod.UNRESOLVED_NO_CHOICES_DECLARED]
    assert causes[_mod.UNRESOLVED_PARSER_NOT_DERIVED] > 0


def test_a_dict_spec_subcommand_with_no_choices_is_not_a_blind_spot(tmp_path):
    """A declaratively-modelled verb whose args are all free-form was MODELLED.

    The path set was derived from the authority map's keys, and that map only
    gains a key when an arg carries ``choices`` — so a dict-spec subcommand
    declaring nothing but ``help`` contributed no path and was filed as a parser
    that was never seen. It is the opposite: the spec models the verb in plain
    sight, and the flag genuinely declares no choices.

    Live subject when this was found: `untrusted-ingestion`'s `validate
    --schema`, which the census reported as a blind spot.
    """
    skill_dir = tmp_path / 'mybundle' / 'skills' / 'myskill'
    (skill_dir / 'scripts').mkdir(parents=True)
    (skill_dir / 'scripts' / 'myscript.py').write_text(
        'from helper import build\n'
        '\n'
        '\n'
        'def main():\n'
        '    return build(\n'
        "        subcommands=[\n"
        "            {'name': 'validate', 'args': [\n"
        "                {'flags': ['--schema'], 'help': 'a|b'},\n"
        '            ]},\n'
        '        ],\n'
        '    )\n',
        encoding='utf-8',
    )
    (skill_dir / 'SKILL.md').write_text(
        '# My Skill\n\n'
        '## Canonical invocations\n\n'
        f'{_FENCE}bash\n'
        'python3 .plan/execute-script.py mybundle:myskill:myscript validate \\\n'
        '  --schema {a|b}\n'
        f'{_FENCE}\n',
        encoding='utf-8',
    )

    coverage = _mod.derive_coverage(derive_population(tmp_path))

    assert coverage['unresolved_causes'][_mod.UNRESOLVED_NO_CHOICES_DECLARED] == 1
    assert coverage['unresolved_causes'][_mod.UNRESOLVED_PARSER_NOT_DERIVED] == 0
    assert coverage['blind_spots'] == 0


def test_a_nameless_dict_spec_contributes_no_modelled_path():
    """A spec whose verb cannot be named must not inject the PARENT path.

    ``here = path + (name,) if name else path`` followed by an unconditional
    append made a nameless top-level entry contribute ``()`` — the root path — to
    the modelled set. A documented root-level flag on such a script would then
    read as ``no_choices_declared`` ("the authority was established and is
    absent") although the parser was never reached: the census mis-attribution
    this module exists to prevent, arriving through a second entry point.

    Nested entries are still walked, so a named child below a nameless parent is
    not lost — it is simply attributed to the path its named ancestors give it.
    """
    tree = ast.parse(
        'def build():\n'
        '    return helper(subcommands=[\n'
        "        {'help': 'nameless top-level',\n"
        "         'subcommands': [{'name': 'orphan', 'args': []}]},\n"
        "        {'name': 'outer', 'subcommands': [{'name': 'inner', 'args': []}]},\n"
        '    ])\n'
    )

    paths = _mod._derived_subcommand_paths(tree)

    assert () not in paths
    # ``orphan`` is the RECURSION half: a named child below a nameless parent is
    # still walked, and takes the path its named ancestors give it — here none,
    # so it sits at top level. Without this entry the test pins only the early
    # return, and deleting the recursion branch leaves the suite green while the
    # docstring, the comment and the commit message all advertise it.
    assert paths == {('orphan',), ('outer',), ('outer', 'inner')}


def test_choices_on_a_mutually_exclusive_group_resolve(tmp_path):
    """A flag declared on an argument GROUP is declared on its parser.

    ``g = p.add_mutually_exclusive_group()`` returns an object whose
    ``add_argument`` adds to ``p``. The walk did not map the group variable back
    to the parser's paths, so every ``choices=`` declared on a group was walked
    PAST — and the site then read as "the parser declares no choices for this
    flag", which is the census's only non-blind-spot cause. Four live sites were
    reported that way.
    """
    script = '''\
import argparse


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')
    add = sub.add_parser('add')
    group = add.add_mutually_exclusive_group(required=True)
    group.add_argument('--settings')
    group.add_argument('--kind', choices=['x', 'y', 'z'])


if __name__ == '__main__':
    main()
'''
    _write_bundle(tmp_path, doc_enum='x|y', script_body=script)

    population = derive_population(tmp_path)

    assert len(population) == 1
    assert population[0].resolved is True
    assert population[0].choices == frozenset({'x', 'y', 'z'})
    assert_analyzer_findings(analyze_canonical_enum_drift, tmp_path, [RULE_ID])


def test_a_parser_rebound_by_a_helper_parameter_is_not_attributed_to_the_root(tmp_path):
    """Declining to attribute an authority is not establishing its absence.

    ``def _add(parser): parser.add_argument(..., choices=...)`` re-binds the name
    ``parser`` to a PARAMETER. The module-wide assignment walk resolved it to the
    module-level ``parser`` — the ROOT — so the helper's choices were filed
    against the root path. That is wrong twice: the real subcommand's authority
    is never recorded, and a root-level flag of the same name would be compared
    against a subcommand's choices, manufacturing a finding out of a scope
    confusion.

    It now fails closed, and the site is reported under its own cause rather than
    as "declares no choices". The subcommand's parser IS modelled here (the
    fixture assigns it before passing it, as the live subject does), so the cause
    is the incomplete authority rather than an underived surface.
    """
    script = '''\
import argparse


def _add_init_args(parser):
    parser.add_argument('--mode', choices=['live', 'archived'])


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')
    p_add = sub.add_parser('add')
    _add_init_args(p_add)


if __name__ == '__main__':
    main()
'''
    _write_bundle(tmp_path, doc_enum='live|archived', script_body=script, flag='mode')

    population = derive_population(tmp_path)
    coverage = _mod.derive_coverage(population)

    assert population[0].resolved is False
    assert population[0].unresolved_cause == _mod.UNRESOLVED_AUTHORITY_INCOMPLETE
    assert coverage['unresolved_causes'][_mod.UNRESOLVED_NO_CHOICES_DECLARED] == 0
    assert coverage['blind_spots'] == 1

    # The load-bearing half, and the one the assertions above do NOT reach: the
    # helper's choices must not be attributed to the ROOT path. Without this the
    # skip in the authority walk can be deleted and the suite stays green,
    # because the cause is decided by the sibling completeness check.
    script_path = tmp_path / 'mybundle' / 'skills' / 'myskill' / 'scripts' / 'myscript.py'
    tree = ast.parse(script_path.read_text(encoding='utf-8'))
    resolver = _mod._Resolver(tmp_path, lambda path: ast.parse(path.read_text(encoding='utf-8')))
    authority = _mod._authority_by_subcommand_flag(tree, resolver)

    assert ((), 'mode') not in authority
    assert not [key for key in authority if key[0] == ()]


def test_a_parser_handed_to_an_unmodelled_call_makes_that_path_incomplete(tmp_path):
    """An IMPORTED helper that declares the flag leaves the authority unread.

    ``add_phase_arg(capture)`` — the live shape at
    ``plan-marshall:plan-marshall:phase_handshake`` — hands a modelled parser to
    a callee this module does not walk. The path IS derived (the caller's own
    ``add_parser`` gives it), so ``parser_surface_not_derived`` is wrong; and the
    flag's ``choices=`` live in the imported module, so ``no_choices_declared``
    is wrong too — its published meaning is "this rule's authority is established
    as ABSENT", and here it is simply unread. Three live sites were filed that
    way.

    The gate is the parser's POSITION in the call, not the callee's name: only a
    parser passed as an ARGUMENT marks the path, so an ordinary
    ``sub.add_parser('verb')`` — which takes the parser as its receiver — does
    not make every path incomplete. The sibling test below pins that half. An
    exclusion list of argparse call names stood here instead for one round; it
    was inert, and naming it described a discriminator the code did not have.
    """
    script = '''\
import argparse

from _shared_args import add_mode_arg


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')
    p_add = sub.add_parser('add')
    add_mode_arg(p_add)


if __name__ == '__main__':
    main()
'''
    _write_bundle(tmp_path, doc_enum='live|archived', script_body=script, flag='mode')

    population = derive_population(tmp_path)
    coverage = _mod.derive_coverage(population)

    assert population[0].resolved is False
    assert population[0].unresolved_cause == _mod.UNRESOLVED_AUTHORITY_INCOMPLETE
    assert coverage['unresolved_causes'][_mod.UNRESOLVED_NO_CHOICES_DECLARED] == 0

    # The mechanism, reached directly: the call marks the parser's OWN path, not
    # the whole module. Without this the cause could be produced by any
    # module-wide flag and the assertions above would still pass.
    script_path = tmp_path / 'mybundle' / 'skills' / 'myskill' / 'scripts' / 'myscript.py'
    tree = ast.parse(script_path.read_text(encoding='utf-8'))

    assert _mod._paths_with_incomplete_authority(tree) == {('add',)}


def test_a_parser_in_receiver_position_does_not_make_a_path_incomplete(tmp_path):
    """Only ARGUMENTS are inspected, so argparse's own surface needs no exclusion.

    ``sub.add_parser(...)``, ``p.add_argument(...)`` and ``parser.parse_args()``
    all carry the parser as the RECEIVER. If a receiver counted as handing the
    parser to an unmodelled callee, every path in every script would read
    ``authority_incomplete`` and the census would go blind — the failure this
    rule exists to catch, committed by the fix for it.

    A name-based skip list for those calls shipped here for one round and was
    INERT: no argparse call ever reaches the argument scan with a parser in an
    argument position, so deleting the skip left the whole-tree census
    byte-identical and its own control test green. This test is written against
    the structural reason instead — a fixture whose parser appears ONLY as a
    receiver must yield no incomplete path, and that assertion cannot be
    satisfied by a skip list.
    """
    script = '''\
import argparse


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')
    p_add = sub.add_parser('add')
    p_add.add_argument('--mode', choices=['live', 'archived'])
    p_add.set_defaults(func=None)
    group = p_add.add_argument_group('extra')
    group.add_argument('--verbose', action='store_true')
    parser.parse_args()


if __name__ == '__main__':
    main()
'''
    _write_bundle(tmp_path, doc_enum='live|archived', script_body=script, flag='mode')
    script_path = tmp_path / 'mybundle' / 'skills' / 'myskill' / 'scripts' / 'myscript.py'
    tree = ast.parse(script_path.read_text(encoding='utf-8'))
    population = derive_population(tmp_path)

    assert _mod._paths_with_incomplete_authority(tree) == set()
    assert population[0].resolved is True
    assert population[0].choices == frozenset({'live', 'archived'})

    # The discriminator, stated directly: the SAME parser moved into an argument
    # position DOES mark its path. Without this the assertions above would also
    # hold for a scan that inspects nothing at all.
    handed_off = script.replace("    parser.parse_args()", "    _configure(p_add)")
    _write_bundle(tmp_path, doc_enum='live|archived', script_body=handed_off, flag='mode')
    handed_tree = ast.parse(script_path.read_text(encoding='utf-8'))

    assert _mod._paths_with_incomplete_authority(handed_tree) == {('add',)}


def test_a_group_built_off_a_shadowed_parser_is_not_attributed_to_the_root(tmp_path):
    """The shadowing guard must not be defeated by one indirection.

    ``grp = parser.add_mutually_exclusive_group()`` inside
    ``def _extra(parser)`` builds a group of whatever parser the CALLER passed.
    ``grp`` is not itself a parameter, so the direct shadowing test does not
    reach it — and the group branch handed it the module-level ``parser``'s ROOT
    paths, so ``grp.add_argument(..., choices=...)`` was filed against the root.
    That is the wrong-authority comparison the guard promises is impossible,
    reached through the group rather than directly.

    Both halves are asserted: ``grp`` gets NO paths, and the module's authority
    reads incomplete. The first is the load-bearing one — the second could be
    produced by an unrelated shadowed receiver.

    The fixture builds the module-level ``parser`` BEFORE the helper on purpose.
    ``_build_parser_path_sets`` processes assignments in source order, so a
    ``parser = ArgumentParser()`` written BELOW the helper is not yet mapped when
    the group assignment is read, and the group inherits nothing whatever the
    scope gate does. Spelled that way the assertion holds for a reason that is
    not the guard, and deleting the gate leaves the suite green — which is what
    the first draft of this test did.
    """
    script = '''\
import argparse

parser = argparse.ArgumentParser()
sub = parser.add_subparsers(dest='cmd')
p_add = sub.add_parser('add')


def _extra(parser):
    grp = parser.add_mutually_exclusive_group()
    grp.add_argument('--mode', choices=['live', 'archived'])


_extra(p_add)
'''
    _write_bundle(tmp_path, doc_enum='live|archived', script_body=script, flag='mode')
    script_path = tmp_path / 'mybundle' / 'skills' / 'myskill' / 'scripts' / 'myscript.py'
    tree = ast.parse(script_path.read_text(encoding='utf-8'))

    assert 'grp' not in _mod._build_parser_path_sets(tree)
    assert _mod._has_unattributed_choices(tree) is True

    population = derive_population(tmp_path)

    assert population[0].resolved is False
    assert population[0].unresolved_cause == _mod.UNRESOLVED_AUTHORITY_INCOMPLETE
    assert_analyzer_findings(analyze_canonical_enum_drift, tmp_path, [])


def test_choices_on_an_argument_group_resolve(tmp_path):
    """``add_argument_group`` inherits its parser's paths, as its sibling does.

    ``_PARSER_GROUP_FACTORIES`` names two factories and only the
    mutually-exclusive one was pinned, so deleting ``add_argument_group`` from
    the set left the suite green while every ``choices=`` declared on a named
    group went unread.
    """
    script = '''\
import argparse


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')
    add = sub.add_parser('add')
    group = add.add_argument_group('selection')
    group.add_argument('--kind', choices=['x', 'y', 'z'])


if __name__ == '__main__':
    main()
'''
    _write_bundle(tmp_path, doc_enum='x|y|z', script_body=script)

    population = derive_population(tmp_path)

    assert population[0].resolved is True
    assert population[0].choices == frozenset({'x', 'y', 'z'})
    assert_analyzer_findings(analyze_canonical_enum_drift, tmp_path, [])


def test_a_one_member_group_is_counted_as_ambiguous_not_dropped(tmp_path):
    """A one-member group is examined, not compared, and COUNTED.

    The notation cannot tell a template slot from a truncated enum:
    ``--scope {phase}.{role}|plan|orchestrator[...]`` (live at
    ``manage-config/SKILL.md``) yields ``{phase}``, a slot for a phase NAME,
    while ``{bug}`` against a live ``choices=['bug','improvement']`` is this
    rule's own headline drift shape. Neither is compared.

    The load-bearing half is that it stays IN the population under its own
    cause. Dropping it at collection — which is what shipped for one round —
    made the sweep examine a token, decline to judge it, and publish no figure
    saying so: this analyzer's subject committed by the analyzer. The cause is
    a BLIND SPOT, because the token may be a real claim.

    The duplicate-collapsing case is asserted too: the test is on the parsed
    member SET, so ``{a|a}`` is one member however it is spelled.
    """
    _write_bundle(tmp_path, doc_enum='phase', script_body=_SCRIPT_LITERAL_CHOICES)
    population = derive_population(tmp_path)
    coverage = _mod.derive_coverage(population)

    assert len(population) == 1
    assert population[0].resolved is False
    assert population[0].unresolved_cause == _mod.UNRESOLVED_SINGLE_MEMBER
    assert coverage['unresolved_causes'][_mod.UNRESOLVED_SINGLE_MEMBER] == 1
    assert coverage['blind_spots'] == 1
    assert_analyzer_findings(analyze_canonical_enum_drift, tmp_path, [])

    _write_bundle(tmp_path, doc_enum='x|x', script_body=_SCRIPT_LITERAL_CHOICES)
    collapsed = derive_population(tmp_path)

    assert len(collapsed) == 1
    assert collapsed[0].unresolved_cause == _mod.UNRESOLVED_SINGLE_MEMBER

    # The control: two distinct members over the same fixture ARE compared, so
    # the cause above is the one-member rule and not a broken fixture.
    _write_bundle(tmp_path, doc_enum='x|y', script_body=_SCRIPT_LITERAL_CHOICES)
    compared = derive_population(tmp_path)

    assert len(compared) == 1
    assert compared[0].resolved is True


def test_a_truncated_one_member_enum_is_a_declared_gap_not_a_clean_pass(tmp_path):
    """The cost of not comparing a one-member group is PUBLISHED, not zero.

    ``--kind {bug}`` against a live ``choices=['bug','improvement']`` is a real
    drift this rule does not report. That exclusion was once defended in a
    comment saying a one-member group "carries no drift signal anyway", which
    this fixture refutes. It is admissible only because the census names it, so
    what is pinned here is the census entry, not the silence.
    """
    script = '''\
import argparse


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd')
    add = sub.add_parser('add')
    add.add_argument('--kind', choices=['bug', 'improvement'])


if __name__ == '__main__':
    main()
'''
    _write_bundle(tmp_path, doc_enum='bug', script_body=script)

    coverage = _mod.derive_coverage(derive_population(tmp_path))

    assert_analyzer_findings(analyze_canonical_enum_drift, tmp_path, [])
    assert coverage['unresolved_causes'][_mod.UNRESOLVED_SINGLE_MEMBER] == 1
    assert coverage['blind_spots'] == 1
    assert coverage['unresolved_fraction'] == 1.0


def test_a_laundered_group_name_does_not_poison_the_same_name_elsewhere(tmp_path):
    """Shadowing is scoped, so the laundering derived from it must be too.

    ``_group_vars_off_shadowed_owner`` returned bare group NAMES for one round,
    and the caller unioned them into every ``add_argument``'s shadowed set. One
    helper binding ``grp`` therefore marked the name ``grp`` shadowed at every
    ``add_argument`` in the file — discarding the resolved authority of a
    correctly-attributed module-level ``grp = p_add.add_argument_group('g')``,
    which is a false negative manufactured by the guard against false positives.

    Keying on ``(group, owner_name)`` was the second attempt and leaked too: it
    narrowed the scope to "any function with a parameter of that name", so an
    unrelated ``def _c(parser)`` calling the honest module-level ``grp`` still
    had its authority discarded. The key is the binding's own ENCLOSING
    FUNCTION, which is the scope a local binding actually has.

    Three shapes are asserted: the honest module-level group resolves, the
    honest group resolves even when READ from inside another function that has a
    parameter of the laundered owner's name, and the laundered group itself
    still fails closed.
    """
    script = '''\
import argparse

parser = argparse.ArgumentParser()
sub = parser.add_subparsers(dest='cmd')
p_add = sub.add_parser('add')
grp = p_add.add_argument_group('g')
grp.add_argument('--kind', choices=['x', 'y', 'z'])


def _extra(parser):
    grp = parser.add_mutually_exclusive_group()
    grp.add_argument('--other')
'''
    _write_bundle(tmp_path, doc_enum='x|y|z', script_body=script)
    script_path = tmp_path / 'mybundle' / 'skills' / 'myskill' / 'scripts' / 'myscript.py'
    tree = ast.parse(script_path.read_text(encoding='utf-8'))
    population = derive_population(tmp_path)

    laundered = _mod._group_vars_off_shadowed_owner(
        tree, _mod._enclosing_params(tree), _mod._enclosing_functions(tree)
    )

    assert [name for name, _func in laundered] == ['grp']
    assert _mod._has_unattributed_choices(tree) is False
    assert population[0].resolved is True
    assert population[0].choices == frozenset({'x', 'y', 'z'})

    # The cross-FUNCTION read, which the owner-name keying got wrong: the honest
    # ``grp`` is used inside a function whose parameter happens to be spelled
    # like the laundered binding's owner. Nothing about that changes which group
    # ``grp`` names here.
    cross = script.replace(
        "grp.add_argument('--kind', choices=['x', 'y', 'z'])\n",
        '',
    ).rstrip() + '''


def _read(parser):
    grp.add_argument('--kind', choices=['x', 'y', 'z'])
'''
    _write_bundle(tmp_path, doc_enum='x|y|z', script_body=cross)
    cross_tree = ast.parse(script_path.read_text(encoding='utf-8'))
    cross_population = derive_population(tmp_path)

    assert _mod._has_unattributed_choices(cross_tree) is False
    assert cross_population[0].resolved is True
    assert cross_population[0].choices == frozenset({'x', 'y', 'z'})


def test_a_script_mixing_both_declaration_forms_with_different_sets_fails_closed(tmp_path):
    """A conflict between the dict-spec and ``add_argument`` resolves to NOTHING.

    The resolver seeds the declarative spec first, so a later
    ``add_argument(..., choices=...)`` for the same ``(path, flag)`` meets an
    occupied key. A comment said the explicit call "is the one that wins"; it
    does not — an agreeing re-declaration is a no-op and a differing one takes
    the conflict branch, resolving the key to ``None``. Both arms are asserted,
    because the claim is vacuous in the agreeing case and only testable here.
    """
    spec = '''\
import argparse

from script_shared import create_workflow_cli

cli = create_workflow_cli(
    description='d',
    subcommands=[
        {'name': 'add', 'help': 'h', 'args': [
            {'flags': ['--kind'], 'choices': ['a', 'b']},
        ]},
    ],
)

parser = argparse.ArgumentParser()
sub = parser.add_subparsers(dest='cmd')
p = sub.add_parser('add')
p.add_argument('--kind', choices=%s)
'''
    resolver = _mod._Resolver(tmp_path, lambda path: ast.parse(path.read_text(encoding='utf-8')))

    agreeing = _mod._authority_by_subcommand_flag(ast.parse(spec % "['a', 'b']"), resolver)
    differing = _mod._authority_by_subcommand_flag(
        ast.parse(spec % "['a', 'b', 'c']"), resolver
    )

    assert agreeing[(('add',), 'kind')] == frozenset({'a', 'b'})
    assert differing[(('add',), 'kind')] is None

    # And the fail-closed reading reaches the census: no finding, counted as
    # unresolvable rather than compared against either set.
    _write_bundle(tmp_path, doc_enum='a|b', script_body=spec % "['a', 'b', 'c']")
    population = derive_population(tmp_path)

    assert population[0].resolved is False
    assert population[0].unresolved_cause == _mod.UNRESOLVED_CHOICES_UNRESOLVABLE
    assert_analyzer_findings(analyze_canonical_enum_drift, tmp_path, [])


def test_the_two_entry_points_agree_on_findings_over_the_real_tree():
    """``_with_population`` must not be a second, divergent derivation.

    The runner publishes the examined population from the sibling entry point;
    if it re-derived the roster, its number and its findings could disagree with
    the ones the gate reports. One derivation feeds both.
    """
    plain = analyze_canonical_enum_drift(MARKETPLACE_ROOT)
    paired, population_size = _mod.analyze_canonical_enum_drift_with_population(
        MARKETPLACE_ROOT
    )

    assert paired == plain
    assert population_size == len(derive_population(MARKETPLACE_ROOT))
    assert population_size > 0
