# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavioural tests for the ``outline-vs-shipped`` retrospective aspect.

The aspect places what ``phase-3-outline`` said it would touch beside what the
landing actually touched. Nothing checked that correspondence before, and the
value of the check is entirely in keeping its three outcomes APART — two of them
are routinely benign and one is not — so the tests fire each class on its own and
assert the other two stayed at zero. A single "divergence" count would pass a test
that only checked "something was detected".

Four further properties are pinned because each is a way the aspect could ship
looking healthy while saying nothing true:

* **It reports, never gates.** No finding above informational severity and no
  failing status on ANY input. The aspect grades a planning-time forecast against
  an outcome; a gate would convert an honest forecast into a failure.
* **Assessments gain no ``resolution`` lifecycle.** Asserted against a store
  written by the PRODUCTION writer, and against the store bytes before and after
  the aspect runs. Reading assessments as findings has already produced a public
  claim ("29 findings never resolved") that was false and had to be retracted.
* **An unresolvable footprint withholds the counts.** ``comparison:
  inconclusive`` with no ``counts`` key at all — never three confident zeros —
  and a matched positive on the same code path proves the branch is
  discriminating rather than always-inconclusive.
* **The section reaches the RENDERED report.** Two sections in this skill are
  already structurally unrenderable while their non-emission reads as benign, so
  a test that stops at the emitted fragment cannot tell a rendered section from a
  silently dropped one. The matched-control (all-zero) run is asserted to render
  too — that is the shape a self-trigger would drop.

The store is seeded through ``manage-findings._findings_core.add_assessment``
rather than by hand-writing JSONL: a hand-written fixture can only prove the
reader reads what the FIXTURE writes, and the ``resolution``-absence claim is
about what the WRITER writes.
"""

from __future__ import annotations

import json
import re
from argparse import Namespace
from pathlib import Path

import retro_sections as _rs
from _registered_aspects_render_fixtures import _SKILL_MD_PATH, _scan_aspect_table_keys
from file_ops import base_path
from toon_parser import serialize_toon

from conftest import load_script_module

_cos = load_script_module(
    'plan-marshall', 'plan-retrospective', 'check-outline-vs-shipped.py', 'cos_behavior_mod'
)

_cr = load_script_module(
    'plan-marshall', 'plan-retrospective', 'compile-report.py', 'cr_outline_vs_shipped_mod'
)

_fc = load_script_module(
    'plan-marshall', 'manage-findings', '_findings_core.py', 'fc_outline_vs_shipped_mod'
)

_PLAN_ID = 'outline-vs-shipped-fixture'

_HEADING = 'Outline vs Shipped'

_INCLUDE = 'CERTAIN_INCLUDE'
_EXCLUDE = 'CERTAIN_EXCLUDE'
_UNCERTAIN = 'UNCERTAIN'

#: The aspect-table row the Enforcement sentence's trailing "then record
#: proposals per Step 5b" clause covers, rather than its "dispatch the N aspect
#: references" clause. It is the one aspect whose reference is loaded in Step 5
#: (after the report is compiled in Step 4), so it is not one of the dispatched N.
_RECORDED_NOT_DISPATCHED = 'lessons-proposal'


# =============================================================================
# Fixture construction — the store is written by the PRODUCTION writer
# =============================================================================


def _plan_dir(plan_id: str = _PLAN_ID) -> Path:
    """Create and return the sandboxed live plan directory for ``plan_id``.

    ``PLAN_BASE_DIR`` is redirected to a per-test tmp sandbox by conftest's
    autouse fixture, so ``base_path`` resolves inside it and both the writer and
    the aspect under test agree on the location without either being told it.

    ``plan_id`` is a parameter because the store is APPEND-only: two seeds under
    one id inside a single test would accumulate into one store, so a test
    building several independent input shapes gives each its own plan.
    """
    plan_dir = base_path('plans', plan_id)
    plan_dir.mkdir(parents=True, exist_ok=True)
    return plan_dir


def _seed(assessments: list[tuple[str, str]], plan_id: str = _PLAN_ID) -> Path:
    """Write ``(file_path, certainty)`` pairs through ``add_assessment``.

    Returns the plan directory. Each write is asserted to have succeeded, so a
    rejected certainty value cannot leave an empty store that every downstream
    assertion then passes over vacuously.
    """
    plan_dir = _plan_dir(plan_id)
    for file_path, certainty in assessments:
        result = _fc.add_assessment(
            plan_id,
            file_path=file_path,
            certainty=certainty,
            confidence=90,
            agent='phase-3-outline',
        )
        assert result['status'] == 'success', result
    return plan_dir


def _store_path(plan_dir: Path) -> Path:
    return plan_dir.joinpath(*_cos.ASSESSMENTS_RELPATH)


def _run(plan_dir: Path, footprint: list[str] | None, plan_id: str = _PLAN_ID) -> dict:
    """Run the aspect in live mode.

    ``footprint`` supplied → written to ``work/footprint.txt`` and passed as the
    documented PLAN-RELATIVE ``--diff-file``, which short-circuits resolution
    entirely (no git, no provider). ``None`` → no ``--diff-file``, so the shared
    resolver runs and answers from whatever the plan directory carries.
    """
    diff_file = None
    if footprint is not None:
        target = plan_dir / 'work' / 'footprint.txt'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text('\n'.join(footprint) + '\n', encoding='utf-8')
        diff_file = 'work/footprint.txt'
    args = Namespace(
        command='run',
        plan_id=plan_id,
        archived_plan_path=None,
        mode='live',
        diff_file=diff_file,
    )
    return _cos.cmd_run(args)


def _counts(result: dict, name: str) -> dict:
    return result['counts'][name]


# =============================================================================
# The three outcome classes fire INDEPENDENTLY
# =============================================================================


class TestThreeClassesFireIndependently:
    """Each class is fired alone and the other two are asserted at exactly zero.

    That pairing is the whole point: if two classes shared a code path, a test
    asserting only "the expected class fired" would still pass while the sibling
    fired alongside it — and the one class that matters (``exclude_violated``)
    would be indistinguishable from the two that routinely do not.
    """

    def test_include_unrealised_fires_alone(self):
        plan_dir = _seed([('src/a.py', _INCLUDE), ('src/b.py', _INCLUDE)])

        result = _run(plan_dir, ['src/b.py'])

        assert result['comparison'] == 'measured'
        unrealised = _counts(result, 'include_unrealised')
        assert unrealised['count'] == 1
        assert unrealised['members'] == ['src/a.py']
        assert unrealised['denominator'] == 2
        # The other two classes must be untouched by this input.
        assert _counts(result, 'touched_but_unassessed')['count'] == 0
        assert _counts(result, 'exclude_violated')['count'] == 0

    def test_touched_but_unassessed_fires_alone(self):
        plan_dir = _seed([('src/a.py', _INCLUDE)])

        result = _run(plan_dir, ['src/a.py', 'src/discovered.py'])

        touched = _counts(result, 'touched_but_unassessed')
        assert touched['count'] == 1
        assert touched['members'] == ['src/discovered.py']
        assert touched['denominator'] == 2
        assert _counts(result, 'include_unrealised')['count'] == 0
        assert _counts(result, 'exclude_violated')['count'] == 0

    def test_exclude_violated_fires_alone(self):
        plan_dir = _seed([('src/a.py', _INCLUDE), ('src/forbidden.py', _EXCLUDE)])

        result = _run(plan_dir, ['src/a.py', 'src/forbidden.py'])

        violated = _counts(result, 'exclude_violated')
        assert violated['count'] == 1
        assert violated['members'] == ['src/forbidden.py']
        assert violated['denominator'] == 1
        assert _counts(result, 'include_unrealised')['count'] == 0
        assert _counts(result, 'touched_but_unassessed')['count'] == 0

    def test_an_uncertain_assessment_counts_as_assessed(self):
        """An `UNCERTAIN` path was looked at, so touching it is not discovery.

        Without this the class would report every deliberately-uncertain file as
        undeclared work, which inverts what outline actually recorded.
        """
        plan_dir = _seed([('src/maybe.py', _UNCERTAIN)])

        result = _run(plan_dir, ['src/maybe.py'])

        assert _counts(result, 'touched_but_unassessed')['count'] == 0
        # And it belongs to neither certain class.
        assert _counts(result, 'include_unrealised')['denominator'] == 0
        assert _counts(result, 'exclude_violated')['denominator'] == 0

    def test_all_three_can_fire_together_without_merging(self):
        """The classes stay separately counted when the same run produces all three."""
        plan_dir = _seed(
            [
                ('src/planned.py', _INCLUDE),
                ('src/dropped.py', _INCLUDE),
                ('src/forbidden.py', _EXCLUDE),
            ]
        )

        result = _run(plan_dir, ['src/planned.py', 'src/forbidden.py', 'src/discovered.py'])

        assert _counts(result, 'include_unrealised')['members'] == ['src/dropped.py']
        assert _counts(result, 'touched_but_unassessed')['members'] == ['src/discovered.py']
        assert _counts(result, 'exclude_violated')['members'] == ['src/forbidden.py']


# =============================================================================
# The matched control — full agreement reports zeros WITH denominators
# =============================================================================


class TestMatchedControl:
    """The must-report-nothing half, and it must still publish its populations."""

    def test_full_agreement_reports_zero_in_all_three(self):
        plan_dir = _seed(
            [
                ('src/a.py', _INCLUDE),
                ('src/b.py', _INCLUDE),
                ('src/forbidden.py', _EXCLUDE),
            ]
        )

        result = _run(plan_dir, ['src/a.py', 'src/b.py'])

        assert result['comparison'] == 'measured'
        for name in ('include_unrealised', 'touched_but_unassessed', 'exclude_violated'):
            assert _counts(result, name)['count'] == 0, name
            assert _counts(result, name)['members'] == [], name
        assert result['findings'] == []

    def test_the_zeros_publish_the_populations_they_were_taken_over(self):
        """A zero with no denominator is inadmissible — it may be a zero of zero.

        The control above is only meaningful because the denominators are
        NON-zero: outline really did assess three paths and the footprint really
        did carry two.
        """
        plan_dir = _seed(
            [
                ('src/a.py', _INCLUDE),
                ('src/b.py', _INCLUDE),
                ('src/forbidden.py', _EXCLUDE),
            ]
        )

        result = _run(plan_dir, ['src/a.py', 'src/b.py'])

        assert _counts(result, 'include_unrealised')['denominator'] == 2
        assert _counts(result, 'touched_but_unassessed')['denominator'] == 2
        assert _counts(result, 'exclude_violated')['denominator'] == 1
        assert result['assessed_path_count'] == 3
        assert result['assessments_read'] == 3
        assert result['footprint_path_count'] == 2
        for name in ('include_unrealised', 'touched_but_unassessed', 'exclude_violated'):
            assert _counts(result, name)['population'], name

    def test_an_absent_store_is_distinguishable_from_an_empty_one(self):
        """`assessments_store_present` separates 'assessed nothing' from 'could not open'."""
        plan_dir = _plan_dir()
        assert not _store_path(plan_dir).exists()

        result = _run(plan_dir, ['src/a.py'])

        assert result['assessments_store_present'] is False
        assert result['assessments_read'] == 0
        # Denominators that depend on assessments are honestly zero.
        assert _counts(result, 'include_unrealised')['denominator'] == 0
        assert _counts(result, 'exclude_violated')['denominator'] == 0
        # And every touched path is unassessed, which is exactly true.
        assert _counts(result, 'touched_but_unassessed')['count'] == 1

        seeded = _seed([('src/a.py', _INCLUDE)])
        assert _run(seeded, ['src/a.py'])['assessments_store_present'] is True


# =============================================================================
# An unresolvable footprint is inconclusive, and the counts are ABSENT
# =============================================================================


class TestUnresolvableFootprint:
    """Three confident zeros over a comparison that never ran is the failure mode."""

    def test_no_tier_resolves_and_the_counts_key_is_absent(self):
        plan_dir = _seed([('src/a.py', _INCLUDE), ('src/forbidden.py', _EXCLUDE)])

        result = _run(plan_dir, None)

        assert result['footprint_source'] == 'unresolved'
        assert result['comparison'] == 'inconclusive'
        assert 'counts' not in result, (
            'the counts block must be ABSENT on an unresolvable footprint — a zero '
            'published by a run that compared nothing reads exactly like a measured one'
        )
        assert 'footprint_path_count' not in result
        # The assessments WERE read, and that stays reported.
        assert result['assessments_read'] == 2

    def test_the_inconclusive_outcome_is_stated_in_a_finding(self):
        plan_dir = _seed([('src/a.py', _INCLUDE)])

        result = _run(plan_dir, None)

        assert len(result['findings']) == 1
        assert 'inconclusive' in result['findings'][0]['message']

    def test_matched_positive_the_shared_resolver_answers_and_the_counts_appear(self):
        """The same code path, with a resolvable footprint — the branch discriminates.

        Without this pairing the assertion above would also pass against an aspect
        that reported ``inconclusive`` unconditionally.
        """
        plan_dir = _seed([('src/a.py', _INCLUDE), ('src/forbidden.py', _EXCLUDE)])
        (plan_dir / 'references.json').write_text(
            json.dumps({'realized_footprint': ['src/a.py']}), encoding='utf-8'
        )

        result = _run(plan_dir, None)

        assert result['footprint_source'] == 'resolved'
        assert result['comparison'] == 'measured'
        assert _counts(result, 'exclude_violated')['count'] == 0
        assert _counts(result, 'touched_but_unassessed')['count'] == 0


# =============================================================================
# Assessments gain no resolution lifecycle
# =============================================================================


class TestNoResolutionLifecycle:
    """They are scope INPUTS, not defects awaiting closure."""

    def test_the_production_writer_records_no_resolution_field(self):
        plan_dir = _seed([('src/a.py', _INCLUDE), ('src/forbidden.py', _EXCLUDE)])

        records = [
            json.loads(line)
            for line in _store_path(plan_dir).read_text(encoding='utf-8').splitlines()
            if line.strip()
        ]

        assert len(records) == 2, 'anchor: an empty store would pass the claim vacuously'
        for record in records:
            assert 'resolution' not in record, record

    def test_the_aspect_leaves_the_store_byte_identical(self):
        plan_dir = _seed([('src/a.py', _INCLUDE)])
        before = _store_path(plan_dir).read_bytes()

        _run(plan_dir, ['src/a.py'])

        assert _store_path(plan_dir).read_bytes() == before

    def test_no_resolution_key_appears_anywhere_in_the_fragment(self):
        plan_dir = _seed([('src/a.py', _INCLUDE), ('src/forbidden.py', _EXCLUDE)])

        result = _run(plan_dir, ['src/forbidden.py'])

        assert 'resolution' not in _all_keys(result)
        assert result['assessment_lifecycle'] == _cos.ASSESSMENT_LIFECYCLE_NONE


def _all_keys(value: object) -> set[str]:
    """Every dict key anywhere in a nested structure."""
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            keys.add(str(key))
            keys |= _all_keys(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            keys |= _all_keys(item)
    return keys


# =============================================================================
# Reports, never gates
# =============================================================================


def _every_input_shape() -> list[tuple[str, dict]]:
    """Run the aspect over every distinct input shape these tests construct.

    Each shape gets its OWN plan id: the assessments store is append-only, so
    sharing one id would let a later shape inherit an earlier shape's records and
    stop being the shape it is named for.
    """
    shapes: list[tuple[str, dict]] = []

    plan = 'shape-all-three'
    shapes.append(('all three classes fire', _run(
        _seed([('src/planned.py', _INCLUDE), ('src/dropped.py', _INCLUDE),
               ('src/forbidden.py', _EXCLUDE)], plan),
        ['src/planned.py', 'src/forbidden.py', 'src/discovered.py'], plan,
    )))

    plan = 'shape-agreement'
    shapes.append(('full agreement', _run(
        _seed([('src/a.py', _INCLUDE)], plan), ['src/a.py'], plan,
    )))

    plan = 'shape-unresolvable'
    shapes.append(('unresolvable footprint', _run(
        _seed([('src/a.py', _INCLUDE)], plan), None, plan,
    )))

    plan = 'shape-no-store'
    shapes.append(('no assessments store', _run(_plan_dir(plan), ['src/a.py'], plan)))

    plan = 'shape-empty-footprint'
    shapes.append(('empty footprint', _run(_seed([('src/a.py', _INCLUDE)], plan), [], plan)))
    return shapes


class TestReportsNeverGates:
    """No failing status and no severity above informational, on any input.

    No failure has been demonstrated for this comparison — only an absence of
    visibility — so the aspect is not permitted to fail a run.
    """

    def test_the_status_is_success_on_every_input_shape(self):
        shapes = _every_input_shape()
        assert len(shapes) >= 5, 'anchor: an empty shape list would pass vacuously'
        for label, result in shapes:
            assert result['status'] == 'success', label

    def test_every_finding_is_informational(self):
        for label, result in _every_input_shape():
            severities = {f['severity'] for f in result['findings']}
            assert severities <= {_cos.SEVERITY_INFO}, (label, severities)

    def test_the_report_only_posture_is_published_not_merely_implied(self):
        result = _run(_seed([('src/a.py', _INCLUDE)]), ['src/a.py'])
        assert result['gating'] == _cos.GATING_REPORT_ONLY


# =============================================================================
# The section reaches the RENDERED report
# =============================================================================


def _compile(tmp_dir: Path, fragment: dict) -> tuple[dict, str]:
    """Drive ``compile-report cmd_run`` end-to-end; return ``(result, document)``."""
    tmp_dir.mkdir(parents=True, exist_ok=True)
    bundle = tmp_dir / 'fragments.toon'
    bundle.write_text(
        serialize_toon({'_meta': {'mode': 'archived'}, _cos.ASPECT: fragment}), encoding='utf-8'
    )
    args = Namespace(
        command='run',
        plan_id=None,
        archived_plan_path=str(tmp_dir),
        mode='archived',
        fragments_file=str(bundle),
        session_id=None,
    )
    result = _cr.cmd_run(args)
    return result, Path(result['output_path']).read_text(encoding='utf-8')


class TestSectionReachesTheRenderedReport:
    """A computed-but-never-emitted section fails here rather than reading benign."""

    def test_the_aspect_has_a_registry_row(self):
        assert _cos.ASPECT in {key for _h, key, _t in _rs.SECTION_SPEC}

    def test_a_positive_fire_renders_and_names_its_member(self, tmp_path):
        plan_dir = _seed([('src/forbidden.py', _EXCLUDE)])
        fragment = _run(plan_dir, ['src/forbidden.py'])

        result, document = _compile(tmp_path / 'report-fire', fragment)

        assert f'## {_HEADING}' in document
        assert _HEADING in result['sections_written']
        assert 'src/forbidden.py' in document

    def test_the_matched_control_renders_too(self, tmp_path):
        """The all-zero run is exactly the shape a self-trigger would drop.

        Its ``findings`` list is empty, so a conditional row gating on findings
        would refuse it while ``_fragment_has_payload`` still reports payload —
        classifying the healthy run as a dropped section.
        """
        plan_dir = _seed([('src/a.py', _INCLUDE)])
        fragment = _run(plan_dir, ['src/a.py'])
        assert fragment['findings'] == []

        result, document = _compile(tmp_path / 'report-clean', fragment)

        assert f'## {_HEADING}' in document
        assert _HEADING in result['sections_written']
        assert _HEADING not in result['sections_dropped']

    def test_the_clean_run_is_not_reported_as_an_unattributed_zero(self, tmp_path):
        """Its ``findings: []`` is qualified by the ``counts`` block beside it."""
        plan_dir = _seed([('src/a.py', _INCLUDE)])
        fragment = _run(plan_dir, ['src/a.py'])

        result, _document = _compile(tmp_path / 'report-attributed', fragment)

        assert _HEADING not in result['sections_unattributed_zero']

    def test_the_inconclusive_fragment_renders(self, tmp_path):
        plan_dir = _seed([('src/a.py', _INCLUDE)])
        fragment = _run(plan_dir, None)

        _result, document = _compile(tmp_path / 'report-inconclusive', fragment)

        assert f'## {_HEADING}' in document
        assert 'inconclusive' in document


# =============================================================================
# The aspect is a footprint-derivation roster member
# =============================================================================


class TestFootprintRosterMembership:
    """It resolves the shared derivation and declares degradation, so it is a member.

    The roster's own rule is that membership follows the publication of a
    degradation verdict. This aspect publishes one, and these tests hold both
    directions of it: the token really is emitted on the unresolvable path, and
    really is absent on the measured one — the second is what keeps the aggregate
    able to stay silent on a healthy plan.
    """

    def test_the_aspect_is_on_the_derived_roster(self):
        assert _cos.ASPECT in _rs.footprint_consuming_aspect_keys()

    def test_the_inconclusive_fragment_declares_degradation(self):
        fragment = _run(_seed([('src/a.py', _INCLUDE)]), None)
        assert _cr._declares_degraded(fragment, _rs.FOOTPRINT_DEGRADED_TOKENS) is True

    def test_the_measured_fragment_does_not(self):
        fragment = _run(_seed([('src/a.py', _INCLUDE)]), ['src/a.py'])
        assert _cr._declares_degraded(fragment, _rs.FOOTPRINT_DEGRADED_TOKENS) is False


# =============================================================================
# The declared aspect count equals the registered set
# =============================================================================


_ENFORCEMENT_COUNT_RE = re.compile(r'dispatch the (\d+) aspect references')


def _declared_aspect_count(skill_text: str) -> int:
    match = _ENFORCEMENT_COUNT_RE.search(skill_text)
    assert match is not None, (
        'the Enforcement block no longer declares an aspect count in the expected '
        'phrasing — this check reads it by pattern, so a reworded sentence must fail '
        'here rather than silently stop checking anything'
    )
    return int(match.group(1))


class TestDeclaredAspectCountMatchesTheRoster:
    """A stated count is a claim about a population, so it is derived from one.

    The population is the Step-3 aspect table, read by the SAME parser the
    registry-correspondence guard uses, minus the single row the Enforcement
    sentence's own trailing clause covers: it reads *"dispatch the N aspect
    references …, compile the report, then record proposals per Step 5b"*, and
    ``lessons-proposal`` is the aspect whose reference is loaded in Step 5 —
    after the Step 4 compile — so it is not one of the dispatched N.
    """

    def test_the_excluded_row_really_is_in_the_table(self):
        # Anchor: if the exclusion named a key the table does not carry, the
        # subtraction below would be a no-op and the equality would be luck.
        assert _RECORDED_NOT_DISPATCHED in _scan_aspect_table_keys()

    def test_the_declared_count_equals_the_dispatched_rows(self):
        skill_text = _SKILL_MD_PATH.read_text(encoding='utf-8')
        keys = _scan_aspect_table_keys(skill_text)
        assert len(keys) >= 16, f'aspect-table scan returned {len(keys)} rows: {keys}'

        dispatched = [key for key in keys if key != _RECORDED_NOT_DISPATCHED]

        assert _declared_aspect_count(skill_text) == len(dispatched), (
            f'the Enforcement block declares {_declared_aspect_count(skill_text)} '
            f'dispatched aspect references but the Step-3 table carries '
            f'{len(dispatched)} dispatched rows: {dispatched}'
        )

    def test_the_new_aspect_is_one_of_the_counted_rows(self):
        assert _cos.ASPECT in _scan_aspect_table_keys()

    def test_the_check_bites_on_a_stale_count(self):
        """Run the real reader over a deliberately corrupted count.

        Set arithmetic on a literal would prove nothing about the parse.
        """
        skill_text = _SKILL_MD_PATH.read_text(encoding='utf-8')
        declared = _declared_aspect_count(skill_text)
        corrupted = skill_text.replace(
            f'dispatch the {declared} aspect references',
            f'dispatch the {declared + 1} aspect references',
            1,
        )
        assert corrupted != skill_text, 'the corruption did not apply'

        keys = _scan_aspect_table_keys(corrupted)
        dispatched = [key for key in keys if key != _RECORDED_NOT_DISPATCHED]

        assert _declared_aspect_count(corrupted) != len(dispatched)
        # And the uncorrupted document agrees, so the assertion discriminates.
        assert _declared_aspect_count(skill_text) == len(dispatched)
