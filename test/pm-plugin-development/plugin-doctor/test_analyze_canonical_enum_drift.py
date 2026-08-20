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
    """
    _write_shared_fence_bundle(tmp_path, add_enum='x|y', remove_enum='p')

    findings = assert_analyzer_findings(analyze_canonical_enum_drift, tmp_path, [RULE_ID])

    assert findings[0]['details']['missing_from_doc'] == ['q']
    assert findings[0]['details']['subcommand'] == 'remove'


def test_real_tree_shared_fence_sites_resolve_to_their_own_invocation():
    """Over the REAL tree, a site below a second invocation names that invocation.

    The live subject is ``plan-marshall:manage-run-config``'s canonical block,
    whose fence documents ``architecture-refresh set-tier-0`` and
    ``set-tier-1`` in sequence. Under the latch both enums were attributed to the
    fence's first invocation, whose flag has no ``choices=`` — so both sites
    resolved to ``choices is None`` and were never compared at all.

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
