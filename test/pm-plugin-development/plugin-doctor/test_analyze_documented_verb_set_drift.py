# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Tests for the ``documented-verb-set-drift`` rule analyzer.

The analyzer compares two SETS per in-scope script: the top-level verbs the
script registers (AST-derived) and the verbs its skill documents in a fenced
bash invocation. Both directions of the difference are reported, which is what
distinguishes it from the per-invocation ``manage-invocation-invalid`` rule —
an undocumented verb appears in no invocation, so per-invocation analysis
structurally cannot see it.

Test layers:
  * (a) Positive — each drift direction fires, and both fire together on a skill
        carrying one instance of each class.
  * (b) Negative — a skill whose two sets agree emits nothing.
  * (c) Fail-closed derivation — an unreadable verb set SKIPS with a stated
        reason rather than passing silently, and (the fail-open this rule most
        needs to refuse) an underivable ROOT parser skips instead of reporting
        every documented verb as a phantom.
  * (d) Population — the size is derived from the walked tree, published on
        every finding, and an empty population over a non-empty tree is itself a
        finding rather than a clean pass. A tree with no skills at all is the
        matched negative control for that guard.

Every fixture is materialized under ``tmp_path``; the real marketplace tree is
never written to. The fixture BUILDERS are imported from
``_plugin_doctor_fixtures`` rather than re-authored here, so the shape the
suite-coverage corpus fires on and the shape these tests assert against cannot
drift apart.
"""

from pathlib import Path

from conftest import load_script_module
from _plugin_doctor_fixtures import (
    documented_verb_drift_entry_script,
    documented_verb_drift_files,
    documented_verb_drift_script,
    documented_verb_drift_skill_md,
)


# The SCRIPT and MODULE NAME are stated as literals at the call site. An indirection
# wrapper that forwards them as parameters cannot be resolved statically, and an
# unresolvable loader call site is one the ``sys.modules`` collision guard is blind
# to — see test/plan-marshall/script-shared/test_conftest_loader_contract.py, which
# holds that blind spot to a fixed, asserted size.
_mod = load_script_module(
    'pm-plugin-development',
    'plugin-doctor',
    '_analyze_documented_verb_set_drift.py',
    '_analyze_documented_verb_set_drift',
)

analyze = _mod.analyze_documented_verb_set_drift
analyze_with_population = _mod.analyze_documented_verb_set_drift_with_population
derive_population = _mod.derive_population

RULE_ID = _mod.RULE_ID
TYPE_MISSING_FROM_DOCS = _mod.TYPE_MISSING_FROM_DOCS
TYPE_PHANTOM_DOCUMENTED = _mod.TYPE_PHANTOM_DOCUMENTED
TYPE_SKIPPED = _mod.TYPE_SKIPPED
TYPE_EMPTY_POPULATION = _mod.TYPE_EMPTY_POPULATION

SKIP_UNPARSEABLE = _mod.SKIP_UNPARSEABLE
SKIP_NO_ROOT_PARSER = _mod.SKIP_NO_ROOT_PARSER
SKIP_NO_SUBPARSERS = _mod.SKIP_NO_SUBPARSERS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _materialize(root: Path, files: dict[str, str]) -> Path:
    """Write ``files`` (root-relative path -> content) under ``root``."""
    for rel_path, content in files.items():
        target = root / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
    return root


def _types(findings: list[dict]) -> list[str]:
    return sorted(f['type'] for f in findings)


def _detail(findings: list[dict], finding_type: str, key: str):
    """The ``details[key]`` of the single finding of ``finding_type``."""
    matches = [f for f in findings if f['type'] == finding_type]
    assert len(matches) == 1, f'expected exactly one {finding_type}, got {len(matches)}'
    return matches[0]['details'][key]


# ---------------------------------------------------------------------------
# (a) Positive — each drift direction
# ---------------------------------------------------------------------------


def test_a_script_with_no_fenced_invocation_at_all_still_fires(tmp_path):
    """⛔ The killing fixture: an entry script the docs never mention.

    The candidate set used to be built from the notations occurring in fenced
    documentation, so a skill containing a CLI script with NO fenced invocation
    created no entry, never reached ``derive_registered_verbs``, and the rule
    returned CLEAN — a detector that could not fire, for exactly the class it
    exists to detect, and the worst case of that class (a script documented
    nowhere) rather than an edge of it.

    The candidate set is now the UNION of the documented notations and the entry
    scripts the skill owns on disk, so this script is compared against an EMPTY
    documented set and every verb it registers is reported.
    """
    _materialize(
        tmp_path,
        documented_verb_drift_files(
            documented=(),
            script_source=documented_verb_drift_entry_script(('compose', 'record-step')),
        ),
    )

    findings = analyze(tmp_path)

    assert _types(findings) == [TYPE_MISSING_FROM_DOCS, TYPE_MISSING_FROM_DOCS], (
        'a script with zero documented verbs must report one finding per '
        f'registered verb, not silence; got {_types(findings)}'
    )
    assert {f['details']['verb'] for f in findings} == {'compose', 'record-step'}


def test_the_same_script_fully_documented_reports_nothing(tmp_path):
    """The matched negative control for the guard above.

    The SAME entry script, with both verbs now carrying a fenced invocation. If
    this also fired, the finding above would be produced by the script's mere
    presence on disk rather than by the missing documentation, and the union
    would be reporting every owned script unconditionally.
    """
    _materialize(
        tmp_path,
        documented_verb_drift_files(
            documented=('compose', 'record-step'),
            script_source=documented_verb_drift_entry_script(('compose', 'record-step')),
        ),
    )

    assert analyze(tmp_path) == []


def test_an_undocumented_helper_module_is_not_an_owned_entry_script(tmp_path):
    """⛔ The over-correction control: the union must not sweep in helper modules.

    Byte-identical to the killing fixture except that the script carries NO
    ``if __name__ == '__main__':`` guard — the shape of an imported helper
    module. This tree contains non-underscore helper modules that are imported
    and never invoked, so had the entry-script discriminator been "any
    ``scripts/*.py``", every one of them would report a derivation skip or a
    phantom verb list it was never meant to have.
    """
    _materialize(
        tmp_path,
        documented_verb_drift_files(
            documented=(),
            script_source=documented_verb_drift_script(('compose', 'record-step')),
        ),
    )

    assert analyze(tmp_path) == []


def test_registered_verb_absent_from_docs_fires(tmp_path):
    """A registered verb with no fenced invocation is reported."""
    _materialize(
        tmp_path,
        documented_verb_drift_files(
            registered=('compose', 'record-step'),
            documented=('compose',),
        ),
    )

    findings = analyze(tmp_path)

    assert _types(findings) == [TYPE_MISSING_FROM_DOCS]
    assert _detail(findings, TYPE_MISSING_FROM_DOCS, 'verb') == 'record-step'


def test_documented_verb_absent_from_the_script_fires(tmp_path):
    """A documented verb the script does not register is reported as a phantom."""
    _materialize(
        tmp_path,
        documented_verb_drift_files(
            registered=('compose',),
            documented=('compose', 'classify'),
        ),
    )

    findings = analyze(tmp_path)

    assert _types(findings) == [TYPE_PHANTOM_DOCUMENTED]
    assert _detail(findings, TYPE_PHANTOM_DOCUMENTED, 'verb') == 'classify'


def test_both_drift_directions_fire_on_one_skill(tmp_path):
    """One instance of each class on a single skill produces one finding each.

    This is the exact fixture shape the suite-coverage corpus registers, asserted
    here so the corpus entry's firing is a property of the rule rather than an
    accident of the corpus runner.
    """
    _materialize(
        tmp_path,
        documented_verb_drift_files(
            registered=('compose', 'record-step'),
            documented=('compose', 'classify'),
        ),
    )

    findings = analyze(tmp_path)

    assert _types(findings) == sorted([TYPE_MISSING_FROM_DOCS, TYPE_PHANTOM_DOCUMENTED])
    assert {f['rule_id'] for f in findings} == {RULE_ID}
    assert _detail(findings, TYPE_MISSING_FROM_DOCS, 'verb') == 'record-step'
    assert _detail(findings, TYPE_PHANTOM_DOCUMENTED, 'verb') == 'classify'


# ---------------------------------------------------------------------------
# (b) Negative — agreeing sets are silent
# ---------------------------------------------------------------------------


def test_agreeing_verb_sets_emit_nothing(tmp_path):
    """A skill documenting exactly the verbs it registers is clean."""
    _materialize(
        tmp_path,
        documented_verb_drift_files(
            skill='fixture-clean',
            registered=('compose', 'record-step'),
            documented=('compose', 'record-step'),
        ),
    )

    assert analyze(tmp_path) == []


def test_clean_run_still_reports_the_population_it_examined(tmp_path):
    """A clean run carries no finding, so the coverage figure comes back beside it.

    A passing gate is the one state in which no finding can publish
    ``population_size`` — which is exactly the state where "did it examine
    anything?" is unanswerable from the findings alone.
    """
    _materialize(
        tmp_path,
        documented_verb_drift_files(
            skill='fixture-clean',
            registered=('compose',),
            documented=('compose',),
        ),
    )

    findings, population_size = analyze_with_population(tmp_path)

    assert findings == []
    assert population_size == 1


# ---------------------------------------------------------------------------
# (c) Fail-closed derivation
# ---------------------------------------------------------------------------


def test_unparseable_script_skips_rather_than_passing(tmp_path):
    """A script that will not parse yields a stated skip, never silence.

    The distinction is the whole fail-closed contract: a rule that says nothing
    about a script it could not read is indistinguishable from one that read it
    and found it clean.
    """
    _materialize(
        tmp_path,
        documented_verb_drift_files(
            documented=('compose',),
            script_source='def main(\n    return 0\n',
        ),
    )

    findings = analyze(tmp_path)

    assert _types(findings) == [TYPE_SKIPPED]
    assert _detail(findings, TYPE_SKIPPED, 'reason') == SKIP_UNPARSEABLE
    # The skip REPLACES the comparison — no drift is asserted against a verb set
    # that was never derived.
    assert TYPE_PHANTOM_DOCUMENTED not in _types(findings)


def test_underivable_root_parser_skips_instead_of_phantoming_every_verb(tmp_path):
    """An empty derived set is a derivation failure, not "registers nothing".

    ``add_parser`` calls exist but none attaches to a variable recognised as the
    root parser (the parser is built in a helper). Treating the resulting empty
    set as authoritative is the fail-open that produced 60 phantom findings on
    the live tree, so the matched negative control is that ``compose`` — which
    IS registered — is not reported as a phantom.
    """
    _materialize(
        tmp_path,
        documented_verb_drift_files(
            documented=('compose',),
            script_source=(
                'import argparse\n\n\n'
                'def build():\n'
                '    return argparse.ArgumentParser()\n\n\n'
                'def main() -> int:\n'
                '    parser = build()\n'
                "    sub = parser.add_subparsers(dest='command')\n"
                "    sub.add_parser('compose')\n"
                '    return 0\n'
            ),
        ),
    )

    findings = analyze(tmp_path)

    assert _types(findings) == [TYPE_SKIPPED]
    assert _detail(findings, TYPE_SKIPPED, 'reason') == SKIP_NO_ROOT_PARSER
    assert TYPE_PHANTOM_DOCUMENTED not in _types(findings)


def test_no_add_parser_in_this_file_skips_instead_of_phantoming_every_verb(tmp_path):
    """The SIBLING fail-open, reached by the other route into the same refusal.

    ``SKIP_NO_ROOT_PARSER`` (above) and ``SKIP_NO_SUBPARSERS`` are one fail-open
    with two entrances: an empty derived set that is a DERIVATION FAILURE, not the
    observation "registers nothing". The route above has ``add_parser`` calls that
    attach to no recognised root; this one has no ``add_parser`` call in the file
    at all, because the walk is deliberately file-local and does not follow
    imports. The analyzer's own module docstring names ``git-workflow.py`` as the
    worked example — a dozen registered verbs, not one argparse call of its own —
    and reading that as an empty registered set reports every documented verb as a
    phantom.

    Guarding only the first entrance leaves the second free to regress to the
    fail-open while the suite stays green, which is exactly the state this test
    closes: the two are the same defect and must both be held.
    """
    _materialize(
        tmp_path,
        documented_verb_drift_files(
            documented=('compose',),
            script_source=(
                'from _fixture_parser import build_parser\n\n\n'
                'def main() -> int:\n'
                '    parser = build_parser()\n'
                '    parser.parse_args()\n'
                '    return 0\n'
            ),
        ),
    )

    findings = analyze(tmp_path)

    assert _types(findings) == [TYPE_SKIPPED]
    assert _detail(findings, TYPE_SKIPPED, 'reason') == SKIP_NO_SUBPARSERS
    assert TYPE_PHANTOM_DOCUMENTED not in _types(findings)


def test_the_same_documented_verb_IS_a_phantom_once_the_set_is_derivable(tmp_path):
    """The matched negative control for the skip above.

    Same skill, same single documented verb ``compose``, same absence of that verb
    from the registered set — the ONE thing that changes is that the set is now
    derivable, because the script registers a verb in this file. The phantom fires.

    Without this control the guard above would be satisfied by an analyzer that
    never reports a phantom at all, and the assertion ``TYPE_PHANTOM_DOCUMENTED
    not in _types(findings)`` would be passing for a reason unrelated to the skip.
    """
    _materialize(
        tmp_path,
        documented_verb_drift_files(
            registered=('record-step',),
            documented=('compose',),
        ),
    )

    findings = analyze(tmp_path)

    assert TYPE_PHANTOM_DOCUMENTED in _types(findings)
    assert _detail(findings, TYPE_PHANTOM_DOCUMENTED, 'verb') == 'compose'


# ---------------------------------------------------------------------------
# (d) Population
# ---------------------------------------------------------------------------


def test_every_finding_publishes_the_derived_population_size(tmp_path):
    """Each finding carries the size of the population the run actually walked.

    Two skills are in scope, only one of them drifting, so the published figure
    is distinguishable from both "1" (the skills that emitted) and "0".
    """
    files = documented_verb_drift_files(
        skill='fixture-drift',
        registered=('compose', 'record-step'),
        documented=('compose',),
    )
    files.update(
        documented_verb_drift_files(
            skill='fixture-clean',
            registered=('compose',),
            documented=('compose',),
        )
    )
    _materialize(tmp_path, files)

    findings = analyze(tmp_path)

    assert findings, 'expected the drifting skill to emit'
    assert {f['details']['population_size'] for f in findings} == {2}
    assert len(derive_population(tmp_path)) == 2


def test_population_excludes_a_skill_without_a_canonical_block(tmp_path):
    """The population is the skills carrying a canonical-invocations block.

    A skill without that heading contributes no population entry and no finding,
    however far its documented and registered verbs diverge.
    """
    files = documented_verb_drift_files(
        skill='fixture-in-scope',
        registered=('compose',),
        documented=('compose',),
    )
    base = 'plan-marshall/skills/fixture-out-of-scope'
    files[f'{base}/SKILL.md'] = documented_verb_drift_skill_md(
        'fixture-out-of-scope', ('classify',)
    ).replace('## Canonical invocations\n\n', '')
    files[f'{base}/scripts/fixture-out-of-scope.py'] = (
        'import argparse\n\n\n'
        'def main() -> int:\n'
        '    parser = argparse.ArgumentParser()\n'
        "    sub = parser.add_subparsers(dest='command')\n"
        "    sub.add_parser('compose')\n"
        '    return 0\n'
    )
    _materialize(tmp_path, files)

    assert [p.name for p in derive_population(tmp_path)] == ['fixture-in-scope']
    assert analyze(tmp_path) == []


def test_empty_population_over_a_non_empty_tree_fires(tmp_path):
    """No in-scope skill in a tree that HAS skills is a derivation failure.

    Reporting it as zero findings would be a vacuous pass over an unread
    population.
    """
    skill_md = documented_verb_drift_skill_md('fixture-skill', ()).replace(
        '## Canonical invocations\n\n', ''
    )
    _materialize(tmp_path, {'plan-marshall/skills/fixture-skill/SKILL.md': skill_md})

    findings = analyze(tmp_path)

    assert _types(findings) == [TYPE_EMPTY_POPULATION]
    assert _detail(findings, TYPE_EMPTY_POPULATION, 'population_size') == 0


def test_empty_population_over_an_empty_tree_is_clean(tmp_path):
    """The matched negative control for the guard above.

    A tree carrying no skills at all yields an empty population that is NOT a
    derivation failure — without this control the guard's positive case would
    equally be satisfied by a rule that fires on every empty population.
    """
    (tmp_path / 'plan-marshall').mkdir(parents=True)

    assert analyze(tmp_path) == []
