#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``corpus`` verb group of the plan-orchestrator script.

Covers the four sub-verbs against a SCAFFOLDED FIXTURE EPIC under
``PLAN_BASE_DIR`` isolation — never the live ``truthful-signals`` tree:

- ``corpus enumerate``: the bidirectional reconciliation of ``status.json``'s
  ``plans[]`` queue against the ``plans/PLAN-*.md`` spec files, with every count
  riding beside the population it was computed over.
- ``corpus cross-check``: the cross-ledger duplication arm — this epic's specs
  scored against sibling epics (active and archived), the live plan set, and
  this epic's own corpus, on the two ``sibling-collision-check`` classes.
- ``corpus verdicts``: the sole interpreter of the re-grounding verdict field —
  one control per row of the admission table in
  ``persona-plan-orchestrator/standards/orchestration-model.md``
  § Re-Grounding Verdict Field.
- ``corpus set-verdict``: the sole emitter of that field — in-place replacement,
  and each rejection path proven to reject WITHOUT writing.

Every detector carries a matched pair. The positive controls are seeded defects
(an orphan row, an orphan spec, an unreadable spec, a blocking verdict); the
negative controls are legitimate near-misses that must stay silent (a fully
reconciled corpus, a ``running`` row that is present-but-excluded rather than
missing, an ``unverifiable`` verdict that must NOT be read as a refutation).

A further group pins the fenced-code-block state every line-wise markdown scan
carries. A ``#`` comment inside a fence is not a heading and a ``- item`` inside
one is not a bullet; admitting either truncates the enclosing section, which
drops Expected Surface paths behind a confident no-overlap and makes later
claims vanish from ``--claim-index`` addressing. Each detector there carries a
matched pair, because suppression that also disabled real headings would be a
different defect wearing the same green. The delimiter comparison is pinned on
both sides of the run-LENGTH boundary — a four-backtick block carrying a
three-backtick example, with the shorter, equal and longer closes around it —
because a mask that compares only the delimiter CHARACTER passes every
same-length case while leaving a nested block's body unmasked.

The last group pins the INDENTATION boundary of the same scanners. CommonMark
bounds a fence delimiter and an ATX heading to three spaces of leading
indentation and counts a tab as four columns, so a four-space- or tab-indented
delimiter inside a block is body text rather than a close. The controls
deliberately STRADDLE that boundary — one, two and three spaces on the
permitted side, four spaces and four tab-bearing forms on the rejected side,
each parametrized over a published population — because the preceding rounds
each wrote controls that sat entirely on one side of the clause they moved,
which is how a scanner passed three reviews while still disagreeing with the
rendered document. Both directions across the boundary are pinned, since an
over-indented delimiter must fail to OPEN a block as well as fail to close one,
and the consumer-level and WRITE-path consequences are pinned beside the mask:
an Expected Surface list that still yields every declared path, and a
``--claim-index`` that still addresses the intended bullet rather than a line
inside a fenced example.

Non-vacuity is guarded on three fronts rather than assumed: the
fixture-materialization guard below fails loudly when the fixture epic did not
land on disk; the single-implementation guard enumerates the marketplace Python
surface at test time rather than asserting against a hard-coded file list; and
the indentation group closes with pre-fix negative fixtures carrying the
superseded scanners verbatim, so the bound is proven to have CHANGED the match
set rather than merely to be present.

Note on the rejection contract: these scripts follow the canonical output
contract, so a rejected call returns a ``status: error`` TOON envelope rather
than raising a Python exception. Each rejection test therefore asserts BOTH the
error envelope AND that the spec file is byte-identical afterwards — the "rejects
instead of writing" obligation is about the disk, not about the exception type.
"""

import json
import re
from argparse import Namespace
from pathlib import Path
from typing import Any

import pytest

from conftest import (
    MARKETPLACE_ROOT,
    PROJECT_ROOT,
    get_script_path,
    load_script_module,
    run_script,
)

SCRIPT_PATH = get_script_path('plan-marshall', 'plan-orchestrator', 'orchestrator.py')

_orch = load_script_module(
    'plan-marshall', 'plan-orchestrator', 'orchestrator.py', 'orchestrator_script'
)

#: The relocated SINGLE reader of ``## Expected Surface``, which ``orchestrator.py``
#: now consumes instead of carrying its own parse.
#:
#: Registered under an explicit, collision-proof name rather than its stem: the
#: ``tools-epic-surface-partition`` suites import ``epic_spec_parser`` plainly, and
#: publishing this load under that stem would displace theirs and trip
#: ``test_conftest_loader_contract``'s registration-collision guard. The three
#: addressing arguments are module-level string constants so the call stays
#: statically resolvable to that guard's walker.
_SURFACE_BUNDLE = 'plan-marshall'
_SURFACE_SKILL = 'script-shared'
_SURFACE_SCRIPT = 'epic_spec_parser.py'
_SURFACE_MODULE_NAME = 'epic_spec_parser_orchestrator_corpus_tests'

_surface_reader = load_script_module(
    _SURFACE_BUNDLE, _SURFACE_SKILL, _SURFACE_SCRIPT, module_name=_SURFACE_MODULE_NAME
)

cmd_corpus_enumerate = _orch.cmd_corpus_enumerate
cmd_corpus_cross_check = _orch.cmd_corpus_cross_check
cmd_corpus_surfaces = _orch.cmd_corpus_surfaces
SURFACE_STATES = _orch.SURFACE_STATES
SURFACE_DECLARATIVE = _orch.SURFACE_DECLARATIVE
SURFACE_DERIVED = _orch.SURFACE_DERIVED
SURFACE_PROSE = _orch.SURFACE_PROSE
SURFACE_ABSENT = _orch.SURFACE_ABSENT
SURFACE_UNREADABLE = _orch.SURFACE_UNREADABLE
SURFACE_INDETERMINATE_STATES = _orch.SURFACE_INDETERMINATE_STATES
cmd_corpus_verdicts = _orch.cmd_corpus_verdicts
cmd_corpus_set_verdict = _orch.cmd_corpus_set_verdict
format_verdict_line = _orch._format_verdict_line
parse_verdict_text = _orch._parse_verdict_text
fenced_mask = _orch._fenced_mask
section_span = _orch._section_span
parse_claim_section = _orch._parse_claim_section
build_arg_parser = _orch._build_arg_parser
CLAIM_LABELS_HEADING_RE = _orch.CLAIM_LABELS_HEADING_RE
HEADING_RE = _orch._HEADING_RE


def expected_surface_paths(text: str, tmp_path: Path) -> set:
    """Resolve a spec's declared surface through the relocated single reader.

    The retired ``orchestrator._expected_surface_paths`` took the spec TEXT; the
    single reader takes the spec PATH, because it resolves directory, recursive
    glob and bullet-relative entries against the repository root rather than
    matching named files by regex. The fixture text is therefore written under
    ``tmp_path`` and classified from there, and the repo root passed in is the
    real ``PROJECT_ROOT`` — the declared fixture paths are real repo paths, and
    the reader only treats an entry as rooted when its first segment exists.

    A spec carrying no ``## Expected Surface`` section resolves to the empty set,
    which is what the retired reader returned for that case too; the distinct
    third state that absence resolves to at the GATE is
    ``orchestrator._row_surface``'s ``(no expected surface section)`` marker.
    """
    spec = tmp_path / 'PLAN-01-fixture.md'
    # ``parents=True`` so a caller resolving two specs in one test can pass two
    # distinct sub-directories of its ``tmp_path`` without creating them first.
    spec.parent.mkdir(parents=True, exist_ok=True)
    spec.write_text(text, encoding='utf-8')
    try:
        claim = _surface_reader.classify_spec(spec, PROJECT_ROOT)
    except _surface_reader.UnclassifiableSpecError:
        return set()
    return {entry.path for entry in claim.claimed}
VERDICT_KEYS = _orch.VERDICT_KEYS
VERDICT_SEPARATOR = _orch.VERDICT_SEPARATOR
VERDICT_VALUES = _orch.VERDICT_VALUES
RESCOPED_VALUES = _orch.RESCOPED_VALUES
CLAIM_SECTION_STATES = _orch.CLAIM_SECTION_STATES
CLAIM_SECTION_ABSENT = _orch.CLAIM_SECTION_ABSENT
CLAIM_SECTION_EMPTY = _orch.CLAIM_SECTION_EMPTY
CLAIM_SECTION_UNREADABLE = _orch.CLAIM_SECTION_UNREADABLE
CLAIM_SECTION_PARSED = _orch.CLAIM_SECTION_PARSED

SLUG = 'fixture-corpus-epic'
FIXED_TIMESTAMP = '2020-01-01T00:00:00Z'
SHA = '9f3a1c2'
OTHER_SHA = 'abc1234'
PRODUCER = 'fixture-corpus-epic/cleanup'

# --- cross-check fixtures --------------------------------------------------

SIBLING_SLUG = 'fixture-sibling-epic'
ARCHIVED_SLUG = 'fixture-archived-epic'
LIVE_PLAN_ID = 'fixture-live-plan'

#: A concrete repo-relative path a spec declares in its ``## Expected Surface``
#: and a candidate carries on its own surface — the file-overlap class's input.
SHARED_PATH = 'marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py'
#: A DIFFERENT concrete path, so every file-overlap negative control is a real
#: non-empty surface that simply does not intersect — never an empty one.
OTHER_PATH = 'marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_sibling_collision.py'
#: A lesson two documents both cite. A real file path and a real shared
#: reference, but NOT an orchestrator spec pointer — the near-miss the
#: deliberately narrow ``SPEC_POINTER_RE`` exists to keep silent.
SHARED_LESSON = '.plan/local/lessons-learned/LESSON-001-shared-origin.md'
#: A THIRD real path, cited outside the ``## Expected Surface`` section. The
#: section boundary must still exclude it once fenced lines stop truncating the
#: body — widening the body past a fenced comment is not the same as unbounding it.
OUTSIDE_PATH = 'marketplace/bundles/plan-marshall/skills/manage-files/scripts/manage-files.py'


# =============================================================================
# Fixture builders
# =============================================================================


def _epic_dir(plan_context, slug: str = SLUG) -> Path:
    return Path(plan_context.fixture_dir) / 'orchestrator' / slug


def _row(plan_id: str, status: str = 'staged') -> dict:
    return {
        'id': plan_id,
        'slug': plan_id.lower(),
        'workstream': 'WS-01',
        'status': status,
        'plan_marshall_plan_id': '',
        'pr': '',
        'landing': '',
    }


def _write_status(plan_context, rows: list, slug: str = SLUG) -> Path:
    """Write a kind=orchestrator fixture status.json into the isolated store."""
    doc = {
        'kind': 'orchestrator',
        'title': 'Fixture Corpus Epic',
        'phase': 'orchestrating',
        'workstreams': ['WS-01'],
        'plans': rows,
        'resume_anchor': 'fixture',
        'metadata': {},
        'created': FIXED_TIMESTAMP,
        'updated': FIXED_TIMESTAMP,
    }
    path = _epic_dir(plan_context, slug) / 'status.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2), encoding='utf-8')
    return path


#: The default ``## Expected Surface`` body. ``a.py`` carries no ``/`` segment,
#: so the path extractor never sees a path here — a spec written without an
#: explicit surface contributes NOTHING to the file-overlap class.
_DEFAULT_SURFACE = ['- OBSERVED: `a.py` — `f`']

_DEFAULT_CLAIM = '- OBSERVED: a claim — read at `a.py` § `f`'


def _spec_text(
    claim_lines: list,
    surface_lines: list | None = None,
    objective: str = 'Fixture objective.',
) -> str:
    """Render a minimal spec carrying ``## Claim Labels`` and ``## Expected Surface``.

    ``objective`` and ``surface_lines`` are separately addressable because the
    two sections mean different things to ``corpus cross-check``: the surface is
    the declared file set the overlap class compares, while the objective is
    ordinary prose whose paths must NOT be read as a surface.
    """
    lines = [
        '# PLAN-NN: Fixture',
        '',
        '## Objective',
        '',
        objective,
        '',
        '## Claim Labels',
        '',
        *claim_lines,
        '',
        '## Expected Surface',
        '',
        *(_DEFAULT_SURFACE if surface_lines is None else surface_lines),
    ]
    return '\n'.join(lines) + '\n'


def _write_spec(
    plan_context,
    name: str,
    claim_lines: list | None = None,
    *,
    epic_dir: Path | None = None,
    surface_lines: list | None = None,
    objective: str = 'Fixture objective.',
) -> Path:
    """Write one spec file, defaulting to this fixture epic's ``plans/`` dir.

    ``epic_dir`` retargets the write at a sibling epic (active or archived) so
    the cross-check's candidate populations can be materialized with the same
    builder the own-corpus tests use.
    """
    root = _epic_dir(plan_context) if epic_dir is None else epic_dir
    path = root / 'plans' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    # ``is None`` rather than falsy: the EMPTY list is a meaningful fixture (a
    # present-but-empty claim section), and a falsy test would silently swap it
    # for the default one-claim body — the exact collapse this module now pins.
    body = [_DEFAULT_CLAIM] if claim_lines is None else claim_lines
    path.write_text(_spec_text(body, surface_lines, objective), encoding='utf-8')
    return path


def _write_spec_without_surface_section(plan_context, name: str) -> Path:
    """Write one spec carrying NO ``## Expected Surface`` heading at all.

    ``_spec_text`` always writes the heading, which is precisely the variable the
    ``absent`` derivation status turns on, so that section is omitted here rather
    than emptied. The distinction is the point: a spec that declared NO surface
    and a spec whose surface resolves to NOTHING are different facts, and only
    the first is a spec-authoring gap.
    """
    lines = [
        '# PLAN-NN: Fixture',
        '',
        '## Objective',
        '',
        'Fixture objective.',
        '',
        '## Claim Labels',
        '',
        _DEFAULT_CLAIM,
    ]
    path = _epic_dir(plan_context) / 'plans' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return path


def _spec_text_without_claim_section() -> str:
    """Render a spec carrying NO ``## Claim Labels`` heading at all.

    ``_spec_text`` always writes the heading, which is precisely the variable the
    ``absent`` state turns on, so that section is omitted here rather than
    emptied.
    """
    lines = [
        '# PLAN-NN: Fixture',
        '',
        '## Objective',
        '',
        'Fixture objective.',
        '',
        '## Expected Surface',
        '',
        *_DEFAULT_SURFACE,
    ]
    return '\n'.join(lines) + '\n'


def _write_spec_without_claim_section(plan_context, name: str) -> Path:
    """Write one spec whose claim section is ABSENT — a legitimately empty population."""
    path = _epic_dir(plan_context) / 'plans' / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_spec_text_without_claim_section(), encoding='utf-8')
    return path


def _archived_epic_dir(plan_context, slug: str) -> Path:
    """The ARCHIVED home of one epic — the second store root the scan walks."""
    return Path(plan_context.fixture_dir) / 'archived-orchestrators' / slug


def _pointer(spec_name: str, slug: str = SLUG, store: str = 'orchestrator') -> str:
    """Render the on-disk spec-pointer text a ``source_id`` or a spec carries."""
    return f'.plan/local/{store}/{slug}/plans/{spec_name}'


def _surface(*paths: str) -> list:
    """Render an ``## Expected Surface`` body declaring ``paths``."""
    return [f'- OBSERVED: `{path}` — `f`' for path in paths]


def _write_live_plan(
    plan_context,
    plan_id: str,
    source_id: str = '',
    affected_files: list | None = None,
) -> Path:
    """Materialize one ACTIVE plan — the OTHER ledger the cross-check reaches into.

    A plan directory counts as active only when it carries the ``status.json``
    sentinel, so the sentinel is written even though the cross-check reads only
    ``request.md`` (for the origin) and ``references.json`` (for the surface).
    """
    plan_dir: Path = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'status.json').write_text(json.dumps({'plan_id': plan_id}), encoding='utf-8')
    (plan_dir / 'request.md').write_text(
        '\n'.join(
            [
                f'# Request: {plan_id}',
                '',
                f'plan_id: {plan_id}',
                'source: orchestrator',
                f'source_id: {source_id}',
                '',
                '## Clarified Request',
                '',
                'Fixture live plan.',
            ]
        )
        + '\n',
        encoding='utf-8',
    )
    (plan_dir / 'references.json').write_text(
        json.dumps({'affected_files': list(affected_files or [])}), encoding='utf-8'
    )
    return plan_dir


def _verdict_bullet(verdict: str, rescoped: str, evidence: str = 'checked', checked_at: str = SHA) -> str:
    body = VERDICT_SEPARATOR.join(
        (
            f'verdict: {verdict}',
            f'checked_at: {checked_at}',
            f'by: {PRODUCER}',
            f'rescoped: {rescoped}',
            f'evidence: {evidence}',
        )
    )
    return f'  - {body}'


def _set_verdict_args(
    plan: str,
    claim_index: int | None,
    verdict: str = 'corroborated',
    rescoped: str = 'n/a',
    evidence: str = 'holds at this sha',
    checked_at: str = SHA,
    by: str = PRODUCER,
    slug: str = SLUG,
    section_scope: bool = False,
) -> Namespace:
    """Build a complete ``set-verdict`` Namespace so every flag attribute exists.

    ``claim_index`` and ``section_scope`` are the two addressing modes argparse
    declares as a REQUIRED mutually exclusive pair. This builder does not enforce
    the exclusivity — that is argparse's job, pinned separately — so a caller may
    construct either mode, and the section mode passes ``claim_index=None``
    exactly as the parser's default would.
    """
    return Namespace(
        slug=slug,
        plan=plan,
        claim_index=claim_index,
        section_scope=section_scope,
        verdict=verdict,
        checked_at=checked_at,
        by=by,
        rescoped=rescoped,
        evidence=evidence,
    )


def _section_scope_args(plan: str, **overrides) -> Namespace:
    """The ``--section-scope`` addressing mode: no ordinal, section flag set."""
    return _set_verdict_args(plan, None, section_scope=True, **overrides)


# =============================================================================
# corpus enumerate — population guard and the two directions
# =============================================================================


class TestCorpusEnumeratePopulation:
    def test_should_report_a_materialized_fixture_population(self, plan_context):
        """Non-empty-population guard: a fixture that did not land must fail loudly."""
        _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _write_spec(plan_context, 'PLAN-02-beta.md')

        result = cmd_corpus_enumerate(Namespace(slug=SLUG))

        assert result['status'] == 'success'
        assert result['operation'] == 'corpus-enumerate'
        assert result['rows_total'] == 2, 'fixture queue did not materialize'
        assert result['specs_total'] == 2, 'fixture spec files did not materialize'
        assert result['rows_scanned'] == 2
        assert result['specs_scanned'] == 2

    def test_should_ride_every_count_beside_its_population(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')

        result = cmd_corpus_enumerate(Namespace(slug=SLUG))

        for count_field, population_field in (
            ('rows_without_spec_count', 'rows_total'),
            ('specs_without_row_count', 'specs_total'),
            ('unreadable_count', 'specs_total'),
        ):
            assert count_field in result
            assert population_field in result

    def test_should_error_when_status_json_missing(self, plan_context):
        result = cmd_corpus_enumerate(Namespace(slug='absent-corpus-epic'))

        assert result['status'] == 'error'
        assert result['error'] == 'file_not_found'

    def test_should_reject_invalid_slug(self, plan_context):
        result = cmd_corpus_enumerate(Namespace(slug='../evil'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_slug'


class TestCorpusEnumerateDirections:
    """The two directions are separate defects with separate causes."""

    def test_should_report_a_seeded_orphan_row(self, plan_context):
        # Positive control for direction one: a queue row whose spec is absent.
        _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')

        result = cmd_corpus_enumerate(Namespace(slug=SLUG))

        assert result['rows_without_spec'] == [{'id': 'PLAN-02', 'status': 'staged'}]
        assert result['rows_without_spec_count'] == 1
        assert result['specs_without_row_count'] == 0

    def test_should_report_a_seeded_orphan_spec(self, plan_context):
        # Positive control for direction two, asserted INDEPENDENTLY of the first.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _write_spec(plan_context, 'PLAN-09-unqueued.md')

        result = cmd_corpus_enumerate(Namespace(slug=SLUG))

        assert result['specs_without_row'] == ['PLAN-09-unqueued.md']
        assert result['specs_without_row_count'] == 1
        assert result['rows_without_spec_count'] == 0

    def test_should_report_zero_in_both_directions_for_a_reconciled_corpus(self, plan_context):
        # Negative control: a legitimate near-miss (a real, fully-reconciled
        # corpus), not an empty input — an empty corpus would report zero
        # vacuously.
        _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _write_spec(plan_context, 'PLAN-02-beta.md')

        result = cmd_corpus_enumerate(Namespace(slug=SLUG))

        assert result['rows_without_spec_count'] == 0
        assert result['specs_without_row_count'] == 0
        assert result['rows_total'] == 2
        assert result['specs_total'] == 2

    def test_should_not_confuse_a_prefix_row_id_with_a_longer_one(self, plan_context):
        # PLAN-1 must not claim PLAN-10's spec: the separating hyphen is what
        # keeps the exact-or-prefix match honest.
        _write_status(plan_context, [_row('PLAN-1')])
        _write_spec(plan_context, 'PLAN-10-decoy.md')

        result = cmd_corpus_enumerate(Namespace(slug=SLUG))

        assert result['rows_without_spec_count'] == 1
        assert result['specs_without_row'] == ['PLAN-10-decoy.md']

    def test_should_enumerate_from_status_json_not_from_a_plans_glob(self, plan_context):
        """The authority is ``plans[]``; a directory glob returns a DIFFERENT set."""
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-02-orphan.md')

        result = cmd_corpus_enumerate(Namespace(slug=SLUG))

        glob_stems = sorted(path.stem for path in (_epic_dir(plan_context) / 'plans').glob('PLAN-*.md'))
        row_ids = sorted(row['id'] for row in result['rows'])
        assert row_ids == ['PLAN-01']
        assert glob_stems == ['PLAN-02-orphan']
        assert row_ids != glob_stems
        assert result['rows_without_spec_count'] == 1
        assert result['specs_without_row_count'] == 1


class TestCorpusEnumerateRunningExclusion:
    def test_should_report_a_running_row_as_present_but_excluded(self, plan_context):
        # Positive control: the running row is ENUMERATED, carrying its reason.
        _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02', status='running')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _write_spec(plan_context, 'PLAN-02-beta.md')

        result = cmd_corpus_enumerate(Namespace(slug=SLUG))

        by_id = {row['id']: row for row in result['rows']}
        assert set(by_id) == {'PLAN-01', 'PLAN-02'}, 'a running row was omitted rather than excluded'
        assert by_id['PLAN-02']['excluded_reason'] == 'running'

    def test_should_leave_a_staged_row_unexcluded(self, plan_context):
        # Negative control: exclusion is status-scoped, not blanket.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')

        result = cmd_corpus_enumerate(Namespace(slug=SLUG))

        assert result['rows'][0]['excluded_reason'] == ''

    def test_should_tally_rows_by_status_over_the_scanned_population(self, plan_context):
        _write_status(
            plan_context,
            [_row('PLAN-01'), _row('PLAN-02', status='running'), _row('PLAN-03', status='shipped')],
        )

        result = cmd_corpus_enumerate(Namespace(slug=SLUG))

        assert result['status_tally'] == [
            {'status': 'running', 'count': 1},
            {'status': 'shipped', 'count': 1},
            {'status': 'staged', 'count': 1},
        ]
        assert sum(entry['count'] for entry in result['status_tally']) == result['rows_total']


class TestCorpusEnumerateUnreadable:
    def test_should_report_an_unreadable_spec_without_aborting(self, plan_context):
        # Positive control: report-never-skip. The enumeration still completes.
        _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        broken = _epic_dir(plan_context) / 'plans' / 'PLAN-02-broken.md'
        broken.write_bytes(b'\xff\xfe not valid utf-8 \xff')

        result = cmd_corpus_enumerate(Namespace(slug=SLUG))

        assert result['status'] == 'success'
        assert result['unreadable'] == [{'spec': 'PLAN-02-broken.md', 'error': 'unreadable'}]
        assert result['unreadable_count'] == 1
        assert result['specs_total'] == 2
        assert result['specs_scanned'] == 1, 'the unreadable spec must not count as scanned'

    def test_should_report_no_unreadable_specs_for_a_healthy_corpus(self, plan_context):
        # Negative control: a real corpus of readable specs, not an empty one.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')

        result = cmd_corpus_enumerate(Namespace(slug=SLUG))

        assert result['unreadable'] == []
        assert result['unreadable_count'] == 0
        assert result['specs_scanned'] == result['specs_total'] == 1


# =============================================================================
# corpus verdicts — one control per admission-table row
# =============================================================================

# --- claim-section parse-coverage fixtures -----------------------------------
#
# One fixture per authoring form the four-member parse-coverage vocabulary has to
# tell apart. The two UNREADABLE forms are the ones the collapsed parser reported
# as an empty claim population; the empty and absent pair are the matched
# negative controls that keep the resulting block attributable to unreadability
# alone rather than to any spec that declares no claims.

#: A claim section authored as a markdown TABLE — content the parser cannot
#: address, because a claim is read only as a top-level ``- `` bullet.
_TABLE_CLAIM_SECTION = [
    '| Claim | Confirm at |',
    '|-------|------------|',
    '| the write seam is single | `a.py` § `f` |',
]

#: A claim section authored as PROSE — the second known-blind form.
_PROSE_CLAIM_SECTION = [
    'The write seam is single: every stamp goes through `a.py` § `f`, verify at outline.',
]

#: A body whose ONLY non-blank content sits inside a fence. The parser
#: deliberately never reads a fenced ``- item`` as a claim, so by the stated
#: conservative rule this section is EMPTY rather than unreadable.
_FENCED_ONLY_CLAIM_SECTION = [
    '```text',
    '- OBSERVED: an illustrative claim — read at `a.py` § `f`',
    '```',
]

#: A present-but-empty claim section.
_EMPTY_CLAIM_SECTION: list = []


def _section_verdict_bullet(
    verdict: str = 'corroborated',
    rescoped: str = 'n/a',
    evidence: str = 'the section is settled as a whole',
) -> str:
    """A TOP-LEVEL verdict bullet — the SECTION-scoped verdict, not a claim's.

    Built from :func:`_verdict_bullet` so both scopes are formatted by one
    fixture body; only the nesting differs, which is exactly the distinction the
    parser reads.
    """
    return _verdict_bullet(verdict, rescoped, evidence).lstrip()


_ADMISSION_CLAIMS = [
    '- HYPOTHESIS: absent clause — confirm/refute at `a.py` § `f` (verify-at-outline)',
    '- HYPOTHESIS: corroborated clause — confirm/refute at `a.py` § `f` (verify-at-outline)',
    _verdict_bullet('corroborated', 'n/a', 'the branch is present at this sha'),
    '- HYPOTHESIS: unverifiable clause — confirm/refute at `a.py` § `f` (verify-at-outline)',
    _verdict_bullet('unverifiable', 'n/a', 'the population could not be reached'),
    '- HYPOTHESIS: absorbed clause — confirm/refute at `a.py` § `f` (verify-at-outline)',
    _verdict_bullet('contradicted', 'yes', 'refuted and the spec now reflects it'),
    '- HYPOTHESIS: blocking clause — confirm/refute at `a.py` § `f` (verify-at-outline)',
    _verdict_bullet('contradicted', 'no', 'refuted and not yet re-scoped'),
    '- HYPOTHESIS: malformed clause — confirm/refute at `a.py` § `f` (verify-at-outline)',
    '  - verdict: contradicted | checked_at: nothexvalue | by: x/y | rescoped: no | evidence: bad sha',
]

_MALFORMED_LINE = _ADMISSION_CLAIMS[-1].strip()


class TestCorpusVerdictsAdmissionTable:
    """One passing control per row of the admission table, plus its blocking pair."""

    def _rows(self, plan_context) -> dict:
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', _ADMISSION_CLAIMS)
        result = cmd_corpus_verdicts(Namespace(slug=SLUG))
        assert result['status'] == 'success'
        assert result['claims_scanned'] == 6, 'the claim population did not materialize'
        return {row['claim_index']: row for row in result['claims']}

    def test_absent_field_yields_no_row_at_all(self, plan_context):
        rows = self._rows(plan_context)

        assert 0 not in rows, 'an unstamped claim must produce no verdict row'

    def test_corroborated_admits(self, plan_context):
        rows = self._rows(plan_context)

        assert rows[1]['verdict'] == 'corroborated'
        assert rows[1]['admits'] is True
        assert rows[1]['rescoped'] == 'n/a'

    def test_unverifiable_admits(self, plan_context):
        # ⛔ An unreached population is not a refutation.
        rows = self._rows(plan_context)

        assert rows[2]['verdict'] == 'unverifiable'
        assert rows[2]['admits'] is True

    def test_contradicted_with_rescoped_yes_admits(self, plan_context):
        rows = self._rows(plan_context)

        assert rows[3]['verdict'] == 'contradicted'
        assert rows[3]['rescoped'] == 'yes'
        assert rows[3]['admits'] is True

    def test_contradicted_with_rescoped_no_blocks(self, plan_context):
        # The ONE blocking settled state.
        rows = self._rows(plan_context)

        assert rows[4]['verdict'] == 'contradicted'
        assert rows[4]['rescoped'] == 'no'
        assert rows[4]['admits'] is False

    def test_malformed_blocks_and_is_quoted_never_dropped(self, plan_context):
        rows = self._rows(plan_context)

        assert rows[5]['verdict'] == 'indeterminate'
        assert rows[5]['admits'] is False
        assert rows[5]['line'] == _MALFORMED_LINE

    def test_an_unsettled_unreadable_section_contributes_one_blocking_row(self, plan_context):
        # The re-pointed control. This pins the BLOCKING property, not the
        # not-blocking one: a table-form section carries claim content the parser
        # cannot address, and before the parse-state split it contributed NO row,
        # so the prep-ready test passed it over an empty population.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', list(_TABLE_CLAIM_SECTION))

        result = cmd_corpus_verdicts(Namespace(slug=SLUG))

        assert result['specs_scanned'] == 1, 'the fixture population did not materialize'
        assert result['claims_scanned'] == 0, 'a table-form section yields no addressable claim'
        assert result['count'] == 1, 'exactly one section-scoped row, never one per table line'
        row = result['claims'][0]
        assert row['verdict'] == 'indeterminate'
        assert row['admits'] is False
        assert row['scope'] == 'section'
        assert row['claim_index'] == -1
        assert row['synthesised'] is True, 'the row stands in for a verdict never written'
        assert result['blocking_count'] == 1

    def test_an_empty_or_absent_section_contributes_no_row_and_no_block(self, plan_context):
        # Matched negative control for the row above, both forms in ONE payload:
        # the block is therefore shown to be caused by unreadability SPECIFICALLY.
        # Without this pair the blocking assertion is equally consistent with a
        # parser that blocks every spec declaring no claims — which would make the
        # gate fire on the whole corpus.
        _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02')])
        _write_spec(plan_context, 'PLAN-01-empty.md', list(_EMPTY_CLAIM_SECTION))
        _write_spec_without_claim_section(plan_context, 'PLAN-02-absent.md')

        result = cmd_corpus_verdicts(Namespace(slug=SLUG))

        assert result['specs_scanned'] == 2, 'the fixture population did not materialize'
        assert result['count'] == 0
        assert result['blocking_count'] == 0
        assert result['unreadable_claim_section_count'] == 0
        assert result['unreadable_claim_sections'] == []

    def test_counts_ride_with_their_populations(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', _ADMISSION_CLAIMS)

        result = cmd_corpus_verdicts(Namespace(slug=SLUG))

        assert result['specs_total'] == 1
        assert result['specs_scanned'] == 1
        assert result['claims_scanned'] == 6
        assert result['count'] == 5
        assert result['blocking_count'] == 2

    def test_a_zero_count_states_which_zero_it_is(self, plan_context):
        # A corpus of real, unstamped specs — not an empty corpus.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')

        result = cmd_corpus_verdicts(Namespace(slug=SLUG))

        assert result['count'] == 0
        assert result['specs_scanned'] == 1
        assert result['claims_scanned'] == 1

    def test_should_report_an_unreadable_spec_rather_than_dropping_it(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        broken = _epic_dir(plan_context) / 'plans' / 'PLAN-01-broken.md'
        broken.parent.mkdir(parents=True, exist_ok=True)
        broken.write_bytes(b'\xff\xfe \xff')

        result = cmd_corpus_verdicts(Namespace(slug=SLUG))

        assert result['unreadable'] == [{'spec': 'PLAN-01-broken.md', 'error': 'unreadable'}]
        assert result['specs_scanned'] == 0
        assert result['specs_total'] == 1

    def test_should_reject_invalid_slug(self, plan_context):
        result = cmd_corpus_verdicts(Namespace(slug='../evil'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_slug'


class TestVerdictStaleness:
    # The git seam is stubbed in both tests below rather than read live. ``stale``
    # is derived from ``_current_head_sha()``, which yields ``''`` whenever git
    # cannot be read — and an empty head makes ``stale`` False for every row. A
    # staleness assertion guarded on a live head therefore silently does not run
    # in any environment without git, and the test still passes green having
    # asserted nothing. Stubbing makes both assertions unconditional.
    STUB_HEAD = '1234567890abcdef1234567890abcdef12345678'

    def test_a_verdict_at_another_sha_is_reported_stale_yet_still_admits(
        self, plan_context, monkeypatch
    ):
        # Staleness is REPORTED, never promoted to blocking.
        monkeypatch.setattr(_orch, '_git_read', lambda operation: (self.STUB_HEAD, ''))
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(
            plan_context,
            'PLAN-01-alpha.md',
            [
                '- HYPOTHESIS: a clause — confirm/refute at `a.py` § `f` (verify-at-outline)',
                _verdict_bullet('corroborated', 'n/a', 'held', checked_at=OTHER_SHA),
            ],
        )

        result = cmd_corpus_verdicts(Namespace(slug=SLUG))
        row = result['claims'][0]

        assert result['head_sha'] == self.STUB_HEAD
        assert row['stale'] is True
        assert row['admits'] is True

    def test_a_verdict_whose_sha_prefixes_head_is_not_stale(self, plan_context, monkeypatch):
        # The matched control: same code path, opposite verdict. Without it, a
        # ``stale`` that was hard-wired True would satisfy the test above.
        monkeypatch.setattr(_orch, '_git_read', lambda operation: (self.STUB_HEAD, ''))
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(
            plan_context,
            'PLAN-01-alpha.md',
            [
                '- HYPOTHESIS: a clause — confirm/refute at `a.py` § `f` (verify-at-outline)',
                _verdict_bullet(
                    'corroborated', 'n/a', 'held', checked_at=self.STUB_HEAD[:7]
                ),
            ],
        )

        result = cmd_corpus_verdicts(Namespace(slug=SLUG))
        row = result['claims'][0]

        assert result['head_sha'] == self.STUB_HEAD
        assert row['stale'] is False
        assert row['admits'] is True


# =============================================================================
# The parse rule — evidence is the remainder
# =============================================================================


class TestVerdictParseRule:
    def test_evidence_containing_the_separator_round_trips_byte_identically(self):
        """Negative control for a naive full split, at the emitter/parser pair."""
        evidence = 'left | middle | right'
        values = {
            'verdict': 'contradicted',
            'checked_at': SHA,
            'by': PRODUCER,
            'rescoped': 'no',
            'evidence': evidence,
        }

        parsed = parse_verdict_text(format_verdict_line(values))

        assert parsed is not None
        assert parsed['evidence'] == evidence
        assert parsed == values

    def test_evidence_containing_the_separator_survives_the_disk_round_trip(self, plan_context):
        evidence = 'left | middle | right'
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(
            plan_context,
            'PLAN-01-alpha.md',
            ['- HYPOTHESIS: a clause — confirm/refute at `a.py` § `f` (verify-at-outline)'],
        )

        cmd_corpus_set_verdict(
            _set_verdict_args('PLAN-01', 0, verdict='contradicted', rescoped='no', evidence=evidence)
        )
        result = cmd_corpus_verdicts(Namespace(slug=SLUG))

        assert result['claims'][0]['evidence'] == evidence

    def test_the_key_order_is_fixed(self):
        assert VERDICT_KEYS == ('verdict', 'checked_at', 'by', 'rescoped', 'evidence')

    def test_a_reordered_line_does_not_parse(self):
        reordered = VERDICT_SEPARATOR.join(
            (f'checked_at: {SHA}', 'verdict: corroborated', f'by: {PRODUCER}', 'rescoped: n/a', 'evidence: x')
        )

        assert parse_verdict_text(reordered) is None

    def test_a_verdict_outside_the_closed_set_does_not_parse(self):
        line = VERDICT_SEPARATOR.join(
            ('verdict: probably', f'checked_at: {SHA}', f'by: {PRODUCER}', 'rescoped: n/a', 'evidence: x')
        )

        assert parse_verdict_text(line) is None
        assert 'probably' not in VERDICT_VALUES

    def test_rescoped_no_on_a_non_refutation_does_not_parse(self):
        line = VERDICT_SEPARATOR.join(
            ('verdict: corroborated', f'checked_at: {SHA}', f'by: {PRODUCER}', 'rescoped: no', 'evidence: x')
        )

        assert parse_verdict_text(line) is None
        assert 'no' in RESCOPED_VALUES, 'the value is legal — only this COMBINATION is not'


# =============================================================================
# corpus set-verdict — the single write action
# =============================================================================

_ONE_CLAIM = ['- HYPOTHESIS: a clause — confirm/refute at `a.py` § `f` (verify-at-outline)']

_TWO_CLAIMS = [
    '- HYPOTHESIS: first clause — confirm/refute at `a.py` § `f` (verify-at-outline)',
    '- HYPOTHESIS: second clause — confirm/refute at `b.py` § `g` (verify-at-outline)',
]


class TestCorpusSetVerdict:
    def test_should_stamp_a_nested_bullet_under_the_addressed_claim(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        spec = _write_spec(plan_context, 'PLAN-01-alpha.md', _ONE_CLAIM)

        result = cmd_corpus_set_verdict(_set_verdict_args('PLAN-01', 0))

        assert result['status'] == 'success'
        assert result['operation'] == 'corpus-set-verdict'
        assert result['replaced'] is False
        assert result['claims_total'] == 1
        text = spec.read_text(encoding='utf-8')
        assert '  - verdict: corroborated' in text
        assert text.index(_ONE_CLAIM[0]) < text.index('  - verdict:')

    def test_should_bind_the_verdict_by_nesting_not_by_ordinal_position(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', _TWO_CLAIMS)

        cmd_corpus_set_verdict(_set_verdict_args('PLAN-01', 1, evidence='second only'))
        result = cmd_corpus_verdicts(Namespace(slug=SLUG))

        assert result['count'] == 1
        assert result['claims'][0]['claim_index'] == 1
        assert result['claims'][0]['evidence'] == 'second only'

    def test_should_replace_an_existing_verdict_in_place(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        spec = _write_spec(plan_context, 'PLAN-01-alpha.md', _ONE_CLAIM)

        first = cmd_corpus_set_verdict(_set_verdict_args('PLAN-01', 0, evidence='first pass'))
        second = cmd_corpus_set_verdict(
            _set_verdict_args('PLAN-01', 0, verdict='contradicted', rescoped='no', evidence='second pass')
        )

        assert first['replaced'] is False
        assert second['replaced'] is True
        assert 'first pass' in second['previous_line']
        text = spec.read_text(encoding='utf-8')
        assert text.count('- verdict:') == 1, 'a claim must never carry two verdicts'
        assert 'first pass' not in text
        assert 'second pass' in text

    def test_should_be_idempotent_on_an_identical_restamp(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        spec = _write_spec(plan_context, 'PLAN-01-alpha.md', _ONE_CLAIM)

        cmd_corpus_set_verdict(_set_verdict_args('PLAN-01', 0))
        after_first = spec.read_bytes()
        cmd_corpus_set_verdict(_set_verdict_args('PLAN-01', 0))

        assert spec.read_bytes() == after_first

    def test_should_preserve_the_trailing_newline(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        spec = _write_spec(plan_context, 'PLAN-01-alpha.md', _ONE_CLAIM)

        cmd_corpus_set_verdict(_set_verdict_args('PLAN-01', 0))

        assert spec.read_text(encoding='utf-8').endswith('\n')

    def test_should_error_when_the_spec_is_absent(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', _ONE_CLAIM)

        result = cmd_corpus_set_verdict(_set_verdict_args('PLAN-99', 0))

        assert result['status'] == 'error'
        assert result['error'] == 'spec_not_found'
        assert result['available_specs'] == ['PLAN-01-alpha.md']


class TestCorpusSetVerdictRejections:
    """Each rejection path rejects WITHOUT writing — asserted against the bytes."""

    def _spec(self, plan_context) -> Path:
        _write_status(plan_context, [_row('PLAN-01')])
        return _write_spec(plan_context, 'PLAN-01-alpha.md', _ONE_CLAIM)

    def test_should_reject_a_rescoped_verdict_combination_without_writing(self, plan_context):
        spec = self._spec(plan_context)
        before = spec.read_bytes()

        result = cmd_corpus_set_verdict(
            _set_verdict_args('PLAN-01', 0, verdict='corroborated', rescoped='no')
        )

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_rescoped_combination'
        assert spec.read_bytes() == before

    def test_should_reject_an_out_of_range_claim_index_without_appending(self, plan_context):
        spec = self._spec(plan_context)
        before = spec.read_bytes()

        result = cmd_corpus_set_verdict(_set_verdict_args('PLAN-01', 7))

        assert result['status'] == 'error'
        assert result['error'] == 'claim_index_out_of_range'
        assert result['claims_total'] == 1
        # The refusal reports the state it observed and names its own remedy, so
        # a caller never has to re-derive why the ordinal was refused.
        assert result['claim_section_state'] == CLAIM_SECTION_PARSED
        assert '--section-scope' in result['recovery']
        assert spec.read_bytes() == before

    def test_should_reject_an_out_of_set_verdict_without_writing(self, plan_context):
        spec = self._spec(plan_context)
        before = spec.read_bytes()

        result = cmd_corpus_set_verdict(_set_verdict_args('PLAN-01', 0, verdict='probably'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_verdict'
        assert spec.read_bytes() == before

    def test_should_reject_an_out_of_set_rescoped_without_writing(self, plan_context):
        spec = self._spec(plan_context)
        before = spec.read_bytes()

        result = cmd_corpus_set_verdict(
            _set_verdict_args('PLAN-01', 0, verdict='contradicted', rescoped='maybe')
        )

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_rescoped'
        assert spec.read_bytes() == before

    def test_should_reject_a_non_hex_checked_at_without_writing(self, plan_context):
        spec = self._spec(plan_context)
        before = spec.read_bytes()

        result = cmd_corpus_set_verdict(_set_verdict_args('PLAN-01', 0, checked_at='HEAD'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_checked_at'
        assert spec.read_bytes() == before

    def test_should_reject_empty_evidence_without_writing(self, plan_context):
        spec = self._spec(plan_context)
        before = spec.read_bytes()

        result = cmd_corpus_set_verdict(_set_verdict_args('PLAN-01', 0, evidence='   '))

        assert result['status'] == 'error'
        assert result['error'] == 'wrong_parameters'
        assert spec.read_bytes() == before

    def test_should_accept_the_legal_counterpart_of_each_rejection(self, plan_context):
        """Negative control: the rejections are combination-scoped, not blanket."""
        spec = self._spec(plan_context)
        before = spec.read_bytes()

        result = cmd_corpus_set_verdict(
            _set_verdict_args('PLAN-01', 0, verdict='contradicted', rescoped='no')
        )

        assert result['status'] == 'success'
        assert spec.read_bytes() != before


# =============================================================================
# Claim-section parse coverage — the four-state discrimination and its reporting
# =============================================================================
#
# ``_parse_claims`` returned an empty list for two structurally different
# documents: a spec with no ``## Claim Labels`` section, and a spec whose section
# is present but authored as a table or as prose. Only the first is a legitimate
# empty population. The controls below pin the discrimination at the unit seam,
# its reporting on the ``corpus verdicts`` payload, and the section-scoped write
# that recovers a spec the parser cannot read — each count stated beside the
# population it was computed over.

#: The parse-state cases, each an ``(expected_state, claim_lines)`` pair. The
#: population is published so the coverage guard below can DERIVE which members
#: of the vocabulary it exercises rather than asserting a hand-typed count.
_PARSE_STATE_CASES = (
    (CLAIM_SECTION_PARSED, [_DEFAULT_CLAIM]),
    (CLAIM_SECTION_EMPTY, list(_EMPTY_CLAIM_SECTION)),
    (CLAIM_SECTION_EMPTY, list(_FENCED_ONLY_CLAIM_SECTION)),
    (CLAIM_SECTION_UNREADABLE, list(_TABLE_CLAIM_SECTION)),
    (CLAIM_SECTION_UNREADABLE, list(_PROSE_CLAIM_SECTION)),
)

_PARSE_STATE_IDS = ('parsed', 'empty', 'empty-fenced-only', 'unreadable-table', 'unreadable-prose')


class TestClaimSectionStateDiscrimination:
    """Unit controls on ``_parse_claim_section``, one per authoring form."""

    def test_the_case_population_covers_the_whole_vocabulary(self):
        # Non-vacuity guard, derived rather than asserted: the parametrized cases
        # plus the separately-built absent case must cover EVERY member of the
        # vocabulary, so a state added to the module without a control here fails
        # loudly instead of going unexercised.
        covered = {state for state, _ in _PARSE_STATE_CASES} | {CLAIM_SECTION_ABSENT}

        assert len(_PARSE_STATE_CASES) == len(_PARSE_STATE_IDS)
        assert covered == set(CLAIM_SECTION_STATES), (
            f'{len(CLAIM_SECTION_STATES)} state(s) in the vocabulary, {len(covered)} exercised'
        )

    @pytest.mark.parametrize(
        ('expected_state', 'claim_lines'), _PARSE_STATE_CASES, ids=_PARSE_STATE_IDS
    )
    def test_each_authoring_form_resolves_to_its_own_state(self, expected_state, claim_lines):
        lines = _spec_text(claim_lines).splitlines()

        section = parse_claim_section(lines)

        assert section['state'] == expected_state

    def test_a_missing_heading_resolves_to_absent_not_to_empty(self):
        lines = _spec_text_without_claim_section().splitlines()

        section = parse_claim_section(lines)

        assert section['state'] == CLAIM_SECTION_ABSENT
        assert section['claims'] == []
        assert section['body_start'] == -1, 'an absent section offers no insertion point'

    def test_an_all_fenced_body_is_empty_because_a_fenced_bullet_is_never_a_claim(self):
        # The conservative rule stated in the parser's docstring, pinned: the
        # fenced bullet IS in the document, so ``empty`` here is the rule holding
        # rather than the scan failing to reach the body.
        text = _spec_text(list(_FENCED_ONLY_CLAIM_SECTION))

        section = parse_claim_section(text.splitlines())

        assert section['state'] == CLAIM_SECTION_EMPTY
        assert '- OBSERVED: an illustrative claim' in text

    def test_an_unreadable_section_quotes_its_first_body_line(self):
        lines = _spec_text(list(_TABLE_CLAIM_SECTION)).splitlines()

        section = parse_claim_section(lines)

        assert section['state'] == CLAIM_SECTION_UNREADABLE
        assert section['first_line'] == _TABLE_CLAIM_SECTION[0]

    def test_a_top_level_verdict_bullet_is_the_section_verdict_not_a_claim(self):
        bullet = _section_verdict_bullet()
        lines = _spec_text([bullet, *_TWO_CLAIMS]).splitlines()

        section = parse_claim_section(lines)

        assert section['section_verdict_line'] >= 0
        assert section['section_verdict_text'] == bullet.removeprefix('- ')
        assert [claim['text'] for claim in section['claims']] == [
            line.removeprefix('- ') for line in _TWO_CLAIMS
        ]


class TestCorpusVerdictsClaimSectionReporting:
    """The three readings ride the payload beside ``specs_scanned``."""

    def _payload(self, plan_context) -> dict:
        _write_status(
            plan_context,
            [_row('PLAN-01'), _row('PLAN-02'), _row('PLAN-03'), _row('PLAN-04')],
        )
        _write_spec_without_claim_section(plan_context, 'PLAN-01-absent.md')
        _write_spec(plan_context, 'PLAN-02-empty.md', list(_EMPTY_CLAIM_SECTION))
        _write_spec(plan_context, 'PLAN-03-unreadable.md', list(_TABLE_CLAIM_SECTION))
        _write_spec(plan_context, 'PLAN-04-parsed.md', list(_ONE_CLAIM))
        result: dict = cmd_corpus_verdicts(Namespace(slug=SLUG))
        assert result['status'] == 'success'
        assert result['specs_scanned'] == 4, 'the fixture population did not materialize'
        return result

    def test_the_tally_spans_the_whole_vocabulary_with_one_spec_per_state(self, plan_context):
        result = self._payload(plan_context)

        tally = {row['state']: row['count'] for row in result['claim_section_states']}

        assert [row['state'] for row in result['claim_section_states']] == list(
            CLAIM_SECTION_STATES
        ), 'the tally is derived from the vocabulary, so its order and membership are total'
        assert tally == dict.fromkeys(CLAIM_SECTION_STATES, 1)
        assert sum(tally.values()) == result['specs_scanned']

    def test_a_state_no_spec_is_in_reports_a_stated_zero(self, plan_context):
        # The whole point of deriving the tally from the vocabulary: an absent
        # state must publish 0, not vanish from the list and read as "unasked".
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-parsed.md', list(_ONE_CLAIM))

        result = cmd_corpus_verdicts(Namespace(slug=SLUG))
        tally = {row['state']: row['count'] for row in result['claim_section_states']}

        assert result['specs_scanned'] == 1
        assert tally[CLAIM_SECTION_PARSED] == 1
        assert tally[CLAIM_SECTION_UNREADABLE] == 0
        assert set(tally) == set(CLAIM_SECTION_STATES)

    def test_only_the_unreadable_spec_is_named_with_its_offending_line(self, plan_context):
        result = self._payload(plan_context)

        assert result['unreadable_claim_section_count'] == 1
        assert result['unreadable_claim_sections'] == [
            {
                'spec': 'PLAN-03-unreadable.md',
                'first_line': _TABLE_CLAIM_SECTION[0],
                'section_verdict': 'absent',
            }
        ]

    def test_the_blocking_row_belongs_to_the_unreadable_spec_alone(self, plan_context):
        result = self._payload(plan_context)

        blocking = [row for row in result['claims'] if not row['admits']]

        assert result['blocking_count'] == 1
        assert [row['spec'] for row in blocking] == ['PLAN-03-unreadable.md']
        assert result['claims_scanned'] == 1, 'only the parsed spec contributes a claim'

    def test_a_claim_scoped_row_still_carries_its_own_scope_and_ordinal(self, plan_context):
        # The new key is TOTAL over the payload, so a claim row is readable by the
        # same test a section row is — no consumer has to special-case its absence.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', _ONE_CLAIM)
        cmd_corpus_set_verdict(_set_verdict_args('PLAN-01', 0))

        result = cmd_corpus_verdicts(Namespace(slug=SLUG))

        assert result['count'] == 1
        assert result['claims'][0]['scope'] == 'claim'
        assert result['claims'][0]['claim_index'] == 0
        assert result['claims'][0]['synthesised'] is False


class TestSectionScopedStamp:
    """``--section-scope``: the write-side recovery address for an unread section."""

    def _unreadable_spec(self, plan_context) -> Path:
        _write_status(plan_context, [_row('PLAN-01')])
        return _write_spec(plan_context, 'PLAN-01-alpha.md', list(_TABLE_CLAIM_SECTION))

    def test_should_stamp_a_top_level_bullet_and_clear_the_block(self, plan_context):
        spec = self._unreadable_spec(plan_context)

        stamped = cmd_corpus_set_verdict(_section_scope_args('PLAN-01'))
        result = cmd_corpus_verdicts(Namespace(slug=SLUG))

        assert stamped['status'] == 'success'
        assert stamped['scope'] == 'section'
        assert stamped['claim_index'] == -1
        assert stamped['claim_section_state'] == CLAIM_SECTION_UNREADABLE
        assert stamped['replaced'] is False
        # The recovery CLEARS the block rather than merely writing a bullet.
        assert result['count'] == 1
        assert result['blocking_count'] == 0
        row = result['claims'][0]
        assert row['scope'] == 'section'
        assert row['claim_index'] == -1
        assert row['admits'] is True
        assert row['synthesised'] is False
        for key in VERDICT_KEYS:
            assert row[key], f'{key} did not survive the section-scoped round trip'
        assert result['unreadable_claim_sections'][0]['section_verdict'] == 'present'
        assert spec.read_text(encoding='utf-8').count('- verdict:') == 1

    def test_should_leave_the_claim_prose_byte_identical(self, plan_context):
        # "Recovered without re-authoring the prose", pinned on the DISK rather
        # than on the return envelope: every original body line survives verbatim.
        spec = self._unreadable_spec(plan_context)
        before = spec.read_text(encoding='utf-8')

        cmd_corpus_set_verdict(_section_scope_args('PLAN-01'))

        after = spec.read_text(encoding='utf-8')
        for line in _TABLE_CLAIM_SECTION:
            assert line in after
        assert after.endswith('\n')
        assert len(after.splitlines()) == len(before.splitlines()) + 1

    def test_should_replace_an_existing_section_verdict_in_place(self, plan_context):
        spec = self._unreadable_spec(plan_context)

        first = cmd_corpus_set_verdict(_section_scope_args('PLAN-01', evidence='first pass'))
        second = cmd_corpus_set_verdict(
            _section_scope_args(
                'PLAN-01', verdict='contradicted', rescoped='no', evidence='second pass'
            )
        )

        assert first['replaced'] is False
        assert second['replaced'] is True
        assert 'first pass' in second['previous_line']
        text = spec.read_text(encoding='utf-8')
        assert text.count('- verdict:') == 1, 'a section must never carry two verdicts'
        assert 'first pass' not in text

    def test_should_be_idempotent_on_an_identical_restamp(self, plan_context):
        spec = self._unreadable_spec(plan_context)

        cmd_corpus_set_verdict(_section_scope_args('PLAN-01'))
        after_first = spec.read_bytes()
        cmd_corpus_set_verdict(_section_scope_args('PLAN-01'))

        assert spec.read_bytes() == after_first

    @pytest.mark.parametrize(
        ('claim_lines', 'expected_state'),
        ((list(_EMPTY_CLAIM_SECTION), CLAIM_SECTION_EMPTY), (list(_ONE_CLAIM), CLAIM_SECTION_PARSED)),
        ids=['empty', 'parsed'],
    )
    def test_should_refuse_a_readable_section_without_writing(
        self, plan_context, claim_lines, expected_state
    ):
        _write_status(plan_context, [_row('PLAN-01')])
        spec = _write_spec(plan_context, 'PLAN-01-alpha.md', claim_lines)
        before = spec.read_bytes()

        result = cmd_corpus_set_verdict(_section_scope_args('PLAN-01'))

        assert result['status'] == 'error'
        assert result['error'] == 'section_scope_not_applicable'
        assert result['claim_section_state'] == expected_state
        assert spec.read_bytes() == before

    def test_should_refuse_an_absent_section_without_writing(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        spec = _write_spec_without_claim_section(plan_context, 'PLAN-01-alpha.md')
        before = spec.read_bytes()

        result = cmd_corpus_set_verdict(_section_scope_args('PLAN-01'))

        assert result['status'] == 'error'
        assert result['error'] == 'claim_section_absent'
        assert result['claim_section_state'] == CLAIM_SECTION_ABSENT
        assert spec.read_bytes() == before


class TestSetVerdictAddressingModes:
    """The two addressing modes are mutually exclusive AND one is required."""

    _BASE = (
        'corpus',
        'set-verdict',
        '--slug',
        SLUG,
        '--plan',
        'PLAN-01',
        '--verdict',
        'corroborated',
        '--checked-at',
        SHA,
        '--by',
        PRODUCER,
        '--rescoped',
        'n/a',
        '--evidence',
        'holds at this sha',
    )

    def test_argparse_refuses_both_addressing_modes(self):
        parser = build_arg_parser()

        with pytest.raises(SystemExit):
            parser.parse_args([*self._BASE, '--claim-index', '0', '--section-scope'])

    def test_argparse_refuses_neither_addressing_mode(self):
        parser = build_arg_parser()

        with pytest.raises(SystemExit):
            parser.parse_args(list(self._BASE))

    def test_argparse_accepts_each_addressing_mode_on_its_own(self):
        # Matched positive control: the pair is EXCLUSIVE, not disabled — without
        # this both refusals above are equally consistent with a broken parser.
        parser = build_arg_parser()

        by_index = parser.parse_args([*self._BASE, '--claim-index', '0'])
        by_section = parser.parse_args([*self._BASE, '--section-scope'])

        assert by_index.claim_index == 0
        assert by_index.section_scope is False
        assert by_section.claim_index is None
        assert by_section.section_scope is True

    def test_a_section_verdict_does_not_shift_the_claim_ordinals(self, plan_context):
        # The section verdict is excluded from ``claims[]``, so the ordinal a
        # caller already holds keeps addressing the same bullet. Asserted against
        # a hand-authored section verdict, since the tool refuses to write one
        # onto a parsed section.
        _write_status(plan_context, [_row('PLAN-01')])
        spec = _write_spec(
            plan_context, 'PLAN-01-alpha.md', [_section_verdict_bullet(), *_TWO_CLAIMS]
        )

        stamped = cmd_corpus_set_verdict(_set_verdict_args('PLAN-01', 1, evidence='second only'))

        assert stamped['status'] == 'success'
        assert stamped['claims_total'] == 2, 'the section verdict was counted as a claim'
        assert stamped['claim_index'] == 1
        assert stamped['scope'] == 'claim'
        text = spec.read_text(encoding='utf-8')
        assert text.index('second only') > text.index(_TWO_CLAIMS[1])


# =============================================================================
# corpus cross-check — the cross-ledger duplication arm
# =============================================================================
#
# The arm a single ledger structurally CANNOT perform: a duplicate held in
# another epic's ledger, or in a launched plan's own ledger, is invisible to
# this epic's ``plans[]`` queue. Three candidate populations are therefore
# scanned — sibling epics (active AND archived), the live plan set, and this
# epic's own corpus — and each is named in the payload so a zero states which
# zero it is.
#
# Both collision classes carry a matched pair. The positives are seeded
# duplicates (a live plan launched from one of these specs, a sibling spec
# citing one, a shared declared surface); the negatives are legitimate
# near-misses that must stay silent — two documents citing the same LESSON
# (a shared reference that is not an origin pointer), a description-sourced
# plan with no traceable origin, two real-but-disjoint surfaces, and the same
# path cited as background prose rather than declared as a surface.


class TestCorpusCrossCheckPopulation:
    def test_should_name_all_three_scanned_populations(self, plan_context):
        """Non-empty-population guard: each candidate source must materialize."""
        _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _write_spec(plan_context, 'PLAN-02-beta.md')
        _write_spec(plan_context, 'PLAN-77-sibling.md', epic_dir=_epic_dir(plan_context, SIBLING_SLUG))
        _write_live_plan(plan_context, LIVE_PLAN_ID)

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['status'] == 'success'
        assert result['operation'] == 'corpus-cross-check'
        assert result['specs_total'] == 2, 'the own corpus did not materialize'
        assert result['specs_scanned'] == 2
        assert result['epics_scanned'] == 1, 'the sibling epic did not materialize'
        assert result['plans_scanned'] == 1, 'the live plan did not materialize'
        assert result['candidates_scanned'] == 2

    def test_should_ride_every_count_beside_its_population(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        for count_field, population_field in (
            ('source_origin_match_count', 'candidates_scanned'),
            ('file_overlap_match_count', 'candidates_scanned'),
            ('unreadable_count', 'specs_total'),
        ):
            assert count_field in result
            assert population_field in result
        for population_field in ('epics_scanned', 'plans_scanned', 'specs_scanned'):
            assert population_field in result

    def test_a_zero_count_states_which_zero_it_is(self, plan_context):
        # Every population is REAL and non-empty — an empty corpus, an epic with
        # no siblings, or no live plans would report the same zeros vacuously.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface_lines=_surface(SHARED_PATH))
        _write_spec(
            plan_context,
            'PLAN-77-sibling.md',
            epic_dir=_epic_dir(plan_context, SIBLING_SLUG),
            surface_lines=_surface(OTHER_PATH),
        )
        _write_live_plan(
            plan_context,
            LIVE_PLAN_ID,
            source_id=_pointer('PLAN-99-elsewhere.md', slug='some-other-epic'),
            affected_files=[OTHER_PATH],
        )

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['source_origin_match_count'] == 0
        assert result['file_overlap_match_count'] == 0
        assert result['unreadable_count'] == 0
        assert result['collision_detected'] is False
        assert result['specs_scanned'] == 1
        assert result['epics_scanned'] == 1
        assert result['plans_scanned'] == 1
        assert result['candidates_scanned'] == 2

    def test_should_error_when_the_epic_has_no_store_tree(self, plan_context):
        result = cmd_corpus_cross_check(Namespace(slug='absent-corpus-epic'))

        assert result['status'] == 'error'
        assert result['error'] == 'not_found'

    def test_should_reject_invalid_slug(self, plan_context):
        result = cmd_corpus_cross_check(Namespace(slug='../evil'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_slug'


class TestCrossCheckSourceOriginClass:
    """Collision class one — a shared spec-pointer origin. Matched pair."""

    def test_should_match_a_live_plan_launched_from_this_epics_spec(self, plan_context):
        # Positive control, CROSS-LEDGER: the duplicate this epic's own queue
        # structurally cannot see, because it is recorded in the plan's ledger.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _write_live_plan(plan_context, LIVE_PLAN_ID, source_id=_pointer('PLAN-01-alpha.md'))

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['source_origin_matches'] == [
            {
                'spec': 'PLAN-01-alpha.md',
                'candidate_kind': 'live_plan',
                'candidate': LIVE_PLAN_ID,
                'shared_origin': f'{SLUG}/plans/PLAN-01-alpha.md',
            }
        ]
        assert result['source_origin_match_count'] == 1
        assert result['collision_detected'] is True
        assert result['plans_scanned'] == 1

    def test_should_match_a_sibling_epic_spec_that_cites_this_epics_spec(self, plan_context):
        # Positive control, cross-EPIC.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _write_spec(
            plan_context,
            'PLAN-77-sibling.md',
            epic_dir=_epic_dir(plan_context, SIBLING_SLUG),
            objective=f'Supersedes {_pointer("PLAN-01-alpha.md")} in full.',
        )

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['source_origin_match_count'] == 1
        row = result['source_origin_matches'][0]
        assert row['spec'] == 'PLAN-01-alpha.md'
        assert row['candidate_kind'] == 'sibling_epic_spec'
        assert row['candidate'] == f'{SIBLING_SLUG}/PLAN-77-sibling.md'
        assert row['shared_origin'] == f'{SLUG}/plans/PLAN-01-alpha.md'

    def test_should_see_an_archived_sibling_epic(self, plan_context):
        # An archived epic still holds work; closing it does not make its specs
        # invisible to the duplication check.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _write_spec(
            plan_context,
            'PLAN-88-archived.md',
            epic_dir=_archived_epic_dir(plan_context, ARCHIVED_SLUG),
            objective=f'Already delivered by {_pointer("PLAN-01-alpha.md")}.',
        )

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['epics_scanned'] == 1
        assert result['source_origin_match_count'] == 1
        assert result['source_origin_matches'][0]['candidate'] == f'{ARCHIVED_SLUG}/PLAN-88-archived.md'

    def test_should_stay_silent_when_two_documents_merely_cite_the_same_lesson(self, plan_context):
        # Negative control: a REAL shared reference that is not an origin
        # pointer. The narrow pointer shape is the whole reason this stays a
        # near-miss instead of a match.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', objective=f'Grounded in {SHARED_LESSON}.')
        _write_spec(
            plan_context,
            'PLAN-77-sibling.md',
            epic_dir=_epic_dir(plan_context, SIBLING_SLUG),
            objective=f'Grounded in {SHARED_LESSON}.',
        )

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['source_origin_match_count'] == 0
        assert result['collision_detected'] is False
        assert result['candidates_scanned'] == 1, 'the candidate population must be non-empty'

    def test_should_stay_silent_for_a_live_plan_with_no_traceable_origin(self, plan_context):
        # Negative control on the cross-ledger arm: a description-sourced plan
        # carries no source_id, so it can never match on origin.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        _write_live_plan(plan_context, LIVE_PLAN_ID, source_id='')

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['source_origin_match_count'] == 0
        assert result['plans_scanned'] == 1, 'the plan population must be non-empty'

    def test_should_not_match_a_spec_against_itself(self, plan_context):
        # Every spec carries its OWN pointer in its pointer set — deliberately,
        # so a candidate citing it matches. The self-exclusion is therefore the
        # only thing keeping a lone spec silent.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['source_origin_match_count'] == 0
        assert result['specs_scanned'] == 1


class TestCrossCheckFileOverlapClass:
    """Collision class two — an exact declared-surface overlap. Matched pair."""

    def test_should_match_a_live_plans_affected_files(self, plan_context):
        # Positive control, CROSS-LEDGER: the spec's declared surface against
        # the launched plan's references.json.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface_lines=_surface(SHARED_PATH))
        _write_live_plan(plan_context, LIVE_PLAN_ID, affected_files=[SHARED_PATH, OTHER_PATH])

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['file_overlap_matches'] == [
            {
                'spec': 'PLAN-01-alpha.md',
                'candidate_kind': 'live_plan',
                'candidate': LIVE_PLAN_ID,
                'overlap_count': 1,
                'overlapping_files': SHARED_PATH,
            }
        ]
        assert result['file_overlap_match_count'] == 1
        assert result['collision_detected'] is True

    def test_should_match_a_sibling_epic_specs_expected_surface(self, plan_context):
        # Positive control, cross-EPIC: spec surface against spec surface.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface_lines=_surface(SHARED_PATH))
        _write_spec(
            plan_context,
            'PLAN-77-sibling.md',
            epic_dir=_epic_dir(plan_context, SIBLING_SLUG),
            surface_lines=_surface(SHARED_PATH, OTHER_PATH),
        )

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['file_overlap_match_count'] == 1
        row = result['file_overlap_matches'][0]
        assert row['candidate_kind'] == 'sibling_epic_spec'
        assert row['candidate'] == f'{SIBLING_SLUG}/PLAN-77-sibling.md'
        assert row['overlap_count'] == 1
        assert row['overlapping_files'] == SHARED_PATH

    def test_should_name_every_overlapping_file_never_a_bare_score(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface_lines=_surface(SHARED_PATH, OTHER_PATH))
        _write_live_plan(plan_context, LIVE_PLAN_ID, affected_files=[OTHER_PATH, SHARED_PATH])

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        row = result['file_overlap_matches'][0]
        assert row['overlap_count'] == 2
        assert sorted(row['overlapping_files'].split(';')) == sorted([SHARED_PATH, OTHER_PATH])

    def test_should_match_within_this_epics_own_corpus(self, plan_context):
        # The within-corpus direction. Rows are emitted per (spec, candidate)
        # pair, so a surface shared by two of this epic's own specs is reported
        # from BOTH sides — the symmetry is the report shape, not a duplicate.
        _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface_lines=_surface(SHARED_PATH))
        _write_spec(plan_context, 'PLAN-02-beta.md', surface_lines=_surface(SHARED_PATH))

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['file_overlap_match_count'] == 2
        assert {row['candidate_kind'] for row in result['file_overlap_matches']} == {'corpus_spec'}
        assert sorted((row['spec'], row['candidate']) for row in result['file_overlap_matches']) == [
            ('PLAN-01-alpha.md', 'PLAN-02-beta.md'),
            ('PLAN-02-beta.md', 'PLAN-01-alpha.md'),
        ]

    def test_should_stay_silent_for_disjoint_surfaces(self, plan_context):
        # Negative control: two REAL non-empty surfaces that do not intersect.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface_lines=_surface(SHARED_PATH))
        _write_live_plan(plan_context, LIVE_PLAN_ID, affected_files=[OTHER_PATH])

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['file_overlap_match_count'] == 0
        assert result['collision_detected'] is False
        assert result['candidates_scanned'] == 1

    def test_should_ignore_a_path_cited_outside_the_expected_surface_section(self, plan_context):
        # Negative control on the SECTION boundary: the very same path, cited as
        # background prose in the objective rather than DECLARED as the surface.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(
            plan_context,
            'PLAN-01-alpha.md',
            objective=f'Background reading: {SHARED_PATH} explains the seam.',
            surface_lines=_surface(OTHER_PATH),
        )
        _write_live_plan(plan_context, LIVE_PLAN_ID, affected_files=[SHARED_PATH])

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['file_overlap_match_count'] == 0
        assert result['candidates_scanned'] == 1


class TestCrossCheckUnreadable:
    """Report-never-skip, on BOTH sides of the comparison."""

    def test_should_report_an_unreadable_own_spec_without_aborting(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        broken = _epic_dir(plan_context) / 'plans' / 'PLAN-02-broken.md'
        broken.write_bytes(b'\xff\xfe not valid utf-8 \xff')

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['status'] == 'success'
        assert result['unreadable'] == [{'spec': 'PLAN-02-broken.md', 'error': 'unreadable'}]
        assert result['unreadable_count'] == 1
        assert result['specs_total'] == 2
        assert result['specs_scanned'] == 1, 'the unreadable spec must not count as scanned'

    def test_should_report_an_unreadable_candidate_under_its_own_epic(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')
        broken = _epic_dir(plan_context, SIBLING_SLUG) / 'plans' / 'PLAN-77-broken.md'
        broken.parent.mkdir(parents=True, exist_ok=True)
        broken.write_bytes(b'\xff\xfe \xff')

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['unreadable'] == [
            {'spec': f'{SIBLING_SLUG}/PLAN-77-broken.md', 'error': 'unreadable'}
        ]
        assert result['unreadable_count'] == 1
        assert result['epics_scanned'] == 1, 'the epic itself was still scanned'
        assert result['candidates_scanned'] == 0, 'an unreadable candidate must not count as scanned'


class TestCrossCheckReadOnlyBoundary:
    def test_cross_check_leaves_every_scanned_tree_byte_identical(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface_lines=_surface(SHARED_PATH))
        _write_spec(
            plan_context,
            'PLAN-77-sibling.md',
            epic_dir=_epic_dir(plan_context, SIBLING_SLUG),
            surface_lines=_surface(SHARED_PATH),
        )
        _write_live_plan(
            plan_context,
            LIVE_PLAN_ID,
            source_id=_pointer('PLAN-01-alpha.md'),
            affected_files=[SHARED_PATH],
        )
        root = Path(plan_context.fixture_dir)
        before = {path: path.read_bytes() for path in sorted(root.rglob('*')) if path.is_file()}
        assert before, 'fixture tree did not materialize'

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        after = {path: path.read_bytes() for path in sorted(root.rglob('*')) if path.is_file()}
        assert after == before
        assert result['collision_detected'] is True, (
            'the read-only claim must be proven on a scan that actually HIT — '
            'a scan finding nothing would leave the tree untouched vacuously'
        )


# =============================================================================
# corpus surfaces — the read the disjointness gate decides on
# =============================================================================
#
# The gate's input used to be a RENDERED table cell read by a human. These cases
# pin it as a parser decision with a published population, and — the part that
# matters most — pin the THIRD STATE: a declaration the parser cannot resolve
# must be distinguishable from one it resolved to nothing, and neither may read
# as disjoint.

#: A surface declaring a DIRECTORY and a RECURSIVE GLOB — the two shapes the
#: retired reader resolved to ZERO paths, which is what made a spec declaring
#: them invisible to the overlap matcher and its silence read as disjoint.
_DIR_AND_GLOB_SURFACE = [
    '- Adds `test/plan-marshall/plan-orchestrator/`',
    '- Adds `marketplace/bundles/plan-marshall/skills/plan-orchestrator/**`',
]


def _surfaces(plan_context) -> Any:
    """Run the verb against the fixture epic.

    Returns ``Any`` rather than ``dict``: the subject is reached through
    ``load_script_module``, so every handler is untyped at check time and a
    narrower annotation would be a claim mypy cannot substantiate.
    """
    return cmd_corpus_surfaces(Namespace(slug=SLUG))


def _row_for(result: Any, spec_name: str) -> Any:
    """The single ``specs[]`` row for one spec, asserting it is single."""
    match = [row for row in result['specs'] if row['spec'] == spec_name]
    assert len(match) == 1, f'{spec_name} contributed {len(match)} rows, expected exactly 1'
    return match[0]


class TestCorpusSurfacesResolvesTheShapesTheOldReaderCouldNot:
    def test_a_directory_and_a_recursive_glob_resolve_to_entries(self, plan_context):
        # The defect, pinned at the verb: the pre-change reader required a ``/``
        # AND a trailing ``.ext``, so BOTH of these resolved to nothing and the
        # spec contributed no comparable path at all.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface_lines=list(_DIR_AND_GLOB_SURFACE))

        row = _row_for(_surfaces(plan_context), 'PLAN-01-alpha.md')

        assert row['derivation_status'] == SURFACE_DECLARATIVE
        assert row['claimed_count'] == len(_DIR_AND_GLOB_SURFACE), (
            f'{len(_DIR_AND_GLOB_SURFACE)} entries declared, {row["claimed_count"]} resolved'
        )
        assert row['admits_disjointness_check'] is True

    def test_the_resolved_entries_carry_their_kinds(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface_lines=list(_DIR_AND_GLOB_SURFACE))

        result = _surfaces(plan_context)

        kinds = {entry['kind'] for entry in result['claimed']}
        assert kinds == {'directory', 'recursive_glob'}, (
            f'expected both entry shapes to be classified, got {sorted(kinds)}'
        )


class TestCorpusSurfacesThirdState:
    """An unresolvable declaration is its own state, and it never reads as disjoint."""

    def test_a_spec_with_no_surface_section_is_absent_not_an_empty_surface(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec_without_surface_section(plan_context, 'PLAN-01-alpha.md')

        row = _row_for(_surfaces(plan_context), 'PLAN-01-alpha.md')

        assert row['derivation_status'] == SURFACE_ABSENT
        assert row['admits_disjointness_check'] is False
        assert row['claimed_count'] == 0

    def test_a_present_but_unresolvable_surface_is_prose_not_absent(self, plan_context):
        # The matched partner of the case above. Both resolve to zero paths, and
        # collapsing them is the defect: only ONE of them is a spec that failed
        # to declare a surface at all.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface_lines=list(_DEFAULT_SURFACE))

        row = _row_for(_surfaces(plan_context), 'PLAN-01-alpha.md')

        assert row['derivation_status'] == SURFACE_PROSE
        assert row['admits_disjointness_check'] is False
        assert row['claimed_count'] == 0

    def test_a_declarative_surface_is_the_only_state_that_admits(self, plan_context):
        # Positive control for the two negatives above: without it, a verb that
        # returned False for EVERY spec would pass both of them.
        _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface_lines=_surface(SHARED_PATH))
        _write_spec_without_surface_section(plan_context, 'PLAN-02-beta.md')

        result = _surfaces(plan_context)

        admitting = {r['spec'] for r in result['specs'] if r['admits_disjointness_check']}
        assert admitting == {'PLAN-01-alpha.md'}
        assert result['admitting_count'] == 1
        assert result['indeterminate_count'] == 1

    def test_every_non_declarative_state_is_in_the_indeterminate_set(self):
        """The admission rule is derived from the vocabulary, not hand-listed.

        A state added to :data:`SURFACE_STATES` later is indeterminate unless it
        is explicitly ``declarative``, so a new class cannot default into
        admitting the gate by being forgotten here.
        """
        assert SURFACE_INDETERMINATE_STATES == frozenset(SURFACE_STATES) - {SURFACE_DECLARATIVE}
        assert SURFACE_DECLARATIVE not in SURFACE_INDETERMINATE_STATES
        for state in (SURFACE_DERIVED, SURFACE_PROSE, SURFACE_ABSENT, SURFACE_UNREADABLE):
            assert state in SURFACE_INDETERMINATE_STATES


class TestCorpusSurfacesPublishesItsPopulation:
    def test_the_class_tally_spans_the_whole_vocabulary_including_zeroes(self, plan_context):
        # Only two of the five classes are populated by this fixture, so the
        # other three are the ones that must still appear — as stated zeros.
        _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface_lines=_surface(SHARED_PATH))
        _write_spec(plan_context, 'PLAN-02-beta.md', surface_lines=list(_DEFAULT_SURFACE))

        result = _surfaces(plan_context)

        tallied = [row['derivation_status'] for row in result['class_tally']]
        assert tallied == list(SURFACE_STATES), (
            'the tally must span the WHOLE vocabulary in its declared order, so a '
            'class no spec is in publishes a stated zero instead of vanishing'
        )
        counts = {row['derivation_status']: row['count'] for row in result['class_tally']}
        assert counts[SURFACE_DECLARATIVE] == 1
        assert counts[SURFACE_PROSE] == 1
        assert counts[SURFACE_DERIVED] == 0
        assert counts[SURFACE_ABSENT] == 0
        assert counts[SURFACE_UNREADABLE] == 0

    def test_the_tally_reconciles_with_the_population_it_was_computed_over(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface_lines=_surface(SHARED_PATH))
        _write_spec_without_surface_section(plan_context, 'PLAN-02-beta.md')

        result = _surfaces(plan_context)

        assert result['specs_total'] == 2, 'the corpus did not materialize'
        assert sum(row['count'] for row in result['class_tally']) == result['specs_total']
        assert len(result['specs']) == result['specs_scanned'] == result['specs_total']
        assert result['admitting_count'] + result['indeterminate_count'] == result['specs_total']

    def test_the_payload_names_its_governing_authority(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface_lines=_surface(SHARED_PATH))

        result = _surfaces(plan_context)

        assert 'ADR-019' in result['governing_authority']
        assert 'indeterminate' in result['governing_authority']


class TestCrossCheckPublishesTheComparedPopulation:
    """``file_overlap_match_count: 0`` must state WHICH zero it is."""

    def test_an_indeterminate_spec_is_counted_apart_from_a_compared_one(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface_lines=_surface(SHARED_PATH))
        _write_spec_without_surface_section(plan_context, 'PLAN-02-beta.md')

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['specs_scanned'] == 2
        assert result['specs_comparable'] == 1
        assert result['specs_indeterminate'] == 1
        assert result['compared_path_count'] == 1

    def test_a_zero_overlap_rides_with_the_population_that_produced_it(self, plan_context):
        # The whole point: a corpus whose every spec is unresolvable reports NO
        # overlap — and the counts beside it say that nothing was comparable,
        # rather than leaving the zero to read as a checked negative.
        _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02')])
        _write_spec_without_surface_section(plan_context, 'PLAN-01-alpha.md')
        _write_spec_without_surface_section(plan_context, 'PLAN-02-beta.md')

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['file_overlap_match_count'] == 0
        assert result['specs_comparable'] == 0, (
            'a zero overlap over a zero comparable population is an UNCHECKED '
            'negative, and the payload has to say so'
        )
        assert result['specs_indeterminate'] == 2
        assert result['compared_path_count'] == 0

    def test_a_real_overlap_still_reports_with_a_non_empty_compared_population(self, plan_context):
        # Matched positive control: the counts above must not be green merely
        # because nothing ever collides.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface_lines=_surface(SHARED_PATH))
        _write_live_plan(plan_context, LIVE_PLAN_ID, affected_files=[SHARED_PATH])

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['file_overlap_match_count'] == 1
        assert result['specs_comparable'] == 1
        assert result['compared_path_count'] == 1

    def test_a_DERIVED_spec_that_also_resolves_paths_is_not_comparable(self, plan_context):
        # The state where comparability-by-non-empty-paths and the published
        # ``admits_disjointness_check`` predicate disagreed. ``classify_spec``
        # assigns DERIVED on the token alone, BEFORE it considers resolved
        # entries, so a spec can be derived AND resolve a real path — and only
        # this shape separates the two rules. A spec that resolves nothing is
        # excluded by either of them, so it cannot witness the difference.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(
            plan_context,
            'PLAN-01-alpha.md',
            surface_lines=[
                '- DERIVED from the plans this one supersedes.',
                *_surface(SHARED_PATH),
            ],
        )
        _write_live_plan(plan_context, LIVE_PLAN_ID, affected_files=[SHARED_PATH])

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))
        surfaces_row = _row_for(_surfaces(plan_context), 'PLAN-01-alpha.md')

        assert surfaces_row['derivation_status'] == SURFACE_DERIVED
        assert surfaces_row['claimed_count'] == 1, (
            'the fixture is only load-bearing if the derived spec DOES resolve a path'
        )
        assert surfaces_row['admits_disjointness_check'] is False
        assert result['specs_comparable'] == 0, (
            'a spec corpus surfaces reports as not admitting the check must not be counted '
            'comparable by cross-check: one spec, two verbs, one answer'
        )
        assert result['compared_path_count'] == 0
        assert result['file_overlap_match_count'] == 0, (
            'the record contract states an indeterminate spec contributes NO rows to the '
            'overlap matcher; a shared path must not produce one here'
        )
        assert result['specs_indeterminate'] == 1

    def test_the_surface_state_tally_spans_the_whole_vocabulary(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface_lines=_surface(SHARED_PATH))

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        tallied = [row['derivation_status'] for row in result['spec_surface_states']]
        assert tallied == list(SURFACE_STATES)
        assert sum(row['count'] for row in result['spec_surface_states']) == result['specs_total']
        assert result['spec_surfaces'] == [
            {'spec': 'PLAN-01-alpha.md', 'derivation_status': SURFACE_DECLARATIVE}
        ]

    def test_the_tally_invariant_holds_when_a_SIBLING_epic_has_an_unreadable_spec(
        self, plan_context
    ):
        # The population the test above cannot reach. Its fixture registers no
        # sibling epic, so the shared ``unreadable`` list holds only OWN entries
        # there and the sum-equals-total invariant passes whether the own tally is
        # derived from the own population or from that shared list. The two
        # derivations only disagree once a sibling contributes to the list — which
        # is exactly the state this fixture creates and that one cannot.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface_lines=_surface(SHARED_PATH))
        broken = _epic_dir(plan_context, SIBLING_SLUG) / 'plans' / 'PLAN-77-broken.md'
        broken.parent.mkdir(parents=True, exist_ok=True)
        broken.write_bytes(b'\xff\xfe \xff')

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['unreadable_count'] == 1, 'the sibling breakage must reach the shared list'
        assert result['specs_total'] == 1, "the sibling's spec is not one of OUR specs"
        assert sum(row['count'] for row in result['spec_surface_states']) == result['specs_total'], (
            "the own-corpus tally must be derived from the own population: reading the SHARED "
            'unreadable list here adds the sibling and breaks sum == specs_total'
        )
        unreadable_row = next(
            row
            for row in result['spec_surface_states']
            if row['derivation_status'] == SURFACE_UNREADABLE
        )
        assert unreadable_row['count'] == 0, (
            'no OWN spec was unreadable, so the own unreadable tally is zero even though '
            'the shared list is not empty'
        )
        assert result['specs_indeterminate'] == 0, (
            'specs_indeterminate is an own-corpus figure and must not absorb the sibling either'
        )


class TestCorpusSurfacesRefusals:
    def test_an_unsafe_slug_is_refused(self):
        result = cmd_corpus_surfaces(Namespace(slug='../escape'))

        assert result['status'] == 'error'
        assert result['error'] == 'invalid_slug'

    def test_an_epic_with_no_store_tree_is_refused(self, plan_context):
        result = cmd_corpus_surfaces(Namespace(slug='no-such-epic'))

        assert result['status'] == 'error'
        assert result['error'] == 'not_found'


class TestCorpusSurfacesReadOnlyBoundary:
    def test_surfaces_leaves_the_tree_byte_identical(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface_lines=_surface(SHARED_PATH))
        root = _epic_dir(plan_context)
        before = {path: path.read_bytes() for path in sorted(root.rglob('*')) if path.is_file()}
        assert before, 'fixture tree did not materialize'

        result = cmd_corpus_surfaces(Namespace(slug=SLUG))

        after = {path: path.read_bytes() for path in sorted(root.rglob('*')) if path.is_file()}
        assert after == before
        assert result['admitting_count'] == 1, (
            'the read-only claim must be proven on a scan that actually RESOLVED '
            'a surface — a scan finding nothing would leave the tree untouched vacuously'
        )


# =============================================================================
# Read-only boundary
# =============================================================================


class TestCorpusReadOnlyBoundary:
    def test_enumerate_and_verdicts_leave_the_tree_byte_identical(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02', status='running')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', _ADMISSION_CLAIMS)
        _write_spec(plan_context, 'PLAN-02-beta.md', _ONE_CLAIM)
        root = _epic_dir(plan_context)
        before = {path: path.read_bytes() for path in sorted(root.rglob('*')) if path.is_file()}
        assert before, 'fixture tree did not materialize'

        cmd_corpus_enumerate(Namespace(slug=SLUG))
        cmd_corpus_verdicts(Namespace(slug=SLUG))

        after = {path: path.read_bytes() for path in sorted(root.rglob('*')) if path.is_file()}
        assert after == before


# =============================================================================
# Fenced-code-block state — suppression of the heading and bullet scans
# =============================================================================
#
# Every line-wise markdown scan in the module runs against a fence mask, because
# a ``#`` comment inside a fenced example is not a heading and a ``- item``
# inside one is not a bullet. Without the mask a fenced comment TERMINATES the
# enclosing section: the Expected Surface body is truncated at that line and
# every later path is dropped, so ``corpus cross-check`` reports a confident
# no-overlap while still counting the spec in ``specs_scanned`` — a silently
# narrowed population behind a clean zero. In ``_parse_claims`` the same
# truncation makes every later claim vanish, shifting ``--claim-index``
# addressing and understating ``claims_total``.
#
# Every detector carries a MATCHED PAIR. The positive controls prove a REAL
# heading still terminates the scan (the suppression is fence-scoped, not a
# blanket disable); the negative controls prove the fenced look-alike does not.

#: An Expected Surface whose fenced example's FIRST body line is a ``#`` comment —
#: the exact shape that truncated the section — followed by the DECLARED bullets.
#: ``OTHER_PATH`` is deliberately LAST, so an assertion that finds it proves the
#: whole declaration survived.
#:
#: The declared entries sit AFTER the fence rather than inside it, because the
#: single reader treats fenced content as a SAMPLE and never as a claim (its own
#: ``test_fenced_block_entries_are_ignored`` pins that). The defect this fixture
#: exists for is unaffected and is if anything pinned harder: if the fence is not
#: masked, the ``#`` comment reads as a heading, the section is truncated there,
#: and BOTH declared bullets vanish from the resolved set.
_FENCED_SURFACE = [
    '```text',
    '# the files this spec expects to touch',
    '```',
    *_surface(SHARED_PATH, OTHER_PATH),
]

#: The same Expected Surface written with a FOUR-backtick outer fence that
#: CONTAINS a three-backtick example — the ordinary way a spec shows a fenced
#: snippet inside a fenced block. CommonMark closes only on a run at least as
#: long as the opener, so the inner ``` lines are body text and the outer block
#: runs to the ```` line. A mask that compares only the delimiter CHARACTER ends
#: the block at the first inner ```, after which the ``#`` comment on the next
#: line reads as a heading and truncates the section — so BOTH declared bullets
#: vanish and the spec resolves as ``prose``, a confident empty surface over a
#: spec that declared two files. This case is the reason the relocated reader
#: retains the opening run's LENGTH and not merely its character.
#: The nested fenced BLOCK on its own, without the declaration that follows it.
#:
#: The mask cases take the block by itself, because they are about where a block
#: BEGINS and ENDS; the surface cases take the block PLUS the declared bullets,
#: because the single reader resolves entries only OUTSIDE a fence. Sharing one
#: fixture between the two would make each case's expected mask length a fact
#: about the other case's fixture.
_NESTED_FENCE_BLOCK = [
    '````text',
    '# the files this spec expects to touch',
    '```',
    '# an inner example, not the close of the outer block',
    '```',
    '````',
]

_NESTED_FENCED_SURFACE = [
    *_NESTED_FENCE_BLOCK,
    *_surface(SHARED_PATH, OTHER_PATH),
]

#: Two real claims with a fenced example between them. The fence carries both a
#: ``#`` comment (a heading look-alike) and a ``- `` line (a bullet look-alike),
#: so one fixture exercises both suppressions.
_FENCED_CLAIMS = [
    _DEFAULT_CLAIM,
    '',
    '```text',
    '# an illustrative fragment, not a heading',
    '- an illustrative bullet, not a claim',
    '```',
    '',
    '- OBSERVED: a second claim — read at `b.py` § `g`',
]


class TestFenceMask:
    """The mask itself, asserted against a published per-line population."""

    def test_should_mark_only_the_fenced_run(self):
        lines = ['before', '```text', '# not a heading', '```', '# a real heading']

        mask = fenced_mask(lines)

        assert len(mask) == len(lines), 'the mask must carry one entry per scanned line'
        assert mask == [False, True, True, True, False]

    def test_an_unterminated_fence_runs_to_the_end_of_the_document(self):
        # CommonMark's rule, and the conservative reading: text that may be code
        # is treated as code rather than admitted as a heading.
        lines = ['```text', '# not a heading', 'still inside the block']

        mask = fenced_mask(lines)

        assert len(mask) == len(lines)
        assert mask == [True, True, True]

    def test_a_tilde_line_does_not_close_a_backtick_fence(self):
        # A close must be built from the character that OPENED the block.
        lines = ['```text', '~~~', '# still fenced', '```', '# a real heading']

        mask = fenced_mask(lines)

        assert len(mask) == len(lines)
        assert mask == [True, True, True, True, False]

    def test_a_four_backtick_block_masks_a_three_backtick_example(self):
        # The straddling case: the run LENGTH decides the close, not just the
        # character. Reading the character alone ends the outer block at the
        # first inner ```, leaving the real fenced body — and the paths after
        # it — unmasked behind a mask that still reports one entry per line.
        lines = ['before', *_NESTED_FENCE_BLOCK, '# a real heading']

        mask = fenced_mask(lines)

        assert len(mask) == len(lines), 'the mask must carry one entry per scanned line'
        assert sum(mask) == len(_NESTED_FENCE_BLOCK), (
            f'{sum(mask)} of {len(lines)} lines masked, expected exactly the '
            f'{len(_NESTED_FENCE_BLOCK)}-line fenced block'
        )
        assert mask == [False, *[True] * len(_NESTED_FENCE_BLOCK), False]

    def test_a_shorter_run_does_not_close_a_longer_opener(self):
        # No delimiter here is long enough to close, so the block runs to the
        # end of the document — the unterminated-fence reading, reached through
        # the run-length comparison rather than through an absent delimiter.
        lines = ['````text', '```', '# still fenced', '```', 'also still fenced']

        mask = fenced_mask(lines)

        assert len(mask) == len(lines)
        assert sum(mask) == len(lines), (
            f'{sum(mask)} of {len(lines)} lines masked, expected every line: a '
            'three-backtick run cannot close a four-backtick opener'
        )

    def test_an_equal_length_run_closes_the_block(self):
        # Control against a fix that passes by never closing a long fence.
        lines = ['````text', '# not a heading', '````', '# a real heading']

        mask = fenced_mask(lines)

        assert len(mask) == len(lines)
        assert mask == [True, True, True, False]

    def test_a_longer_run_closes_a_shorter_opener(self):
        # CommonMark closes on AT LEAST the opening length, not on equality.
        lines = ['```text', '# not a heading', '`````', '# a real heading']

        mask = fenced_mask(lines)

        assert len(mask) == len(lines)
        assert mask == [True, True, True, False]

    def test_a_delimiter_carrying_an_info_string_does_not_close_a_block(self):
        # Only the OPENING fence may carry an info string, so a ```python line
        # inside a block is body text — the same conservative direction.
        lines = ['```text', '```python', '# still fenced', '```', '# a real heading']

        mask = fenced_mask(lines)

        assert len(mask) == len(lines)
        assert mask == [True, True, True, True, False]

    def test_an_unfenced_document_masks_nothing(self):
        # Negative control on the mask itself: a REAL document with real
        # headings, not an empty one, must produce an all-False mask.
        lines = ['## Expected Surface', '', SHARED_PATH, '', '## Objective']

        mask = fenced_mask(lines)

        assert len(mask) == len(lines)
        assert not any(mask)


class TestFencedSectionSpan:
    """``orchestrator._section_span`` against its own fence mask.

    Exercised through ``CLAIM_LABELS_HEADING_RE`` — the heading this module still
    owns — now that the ``## Expected Surface`` grammar has moved to the single
    reader in ``script-shared``. The primitive under test is unchanged; only the
    heading it is driven with is, and the two are interchangeable here because
    both are ordinary addressed ATX headings fed to the same scanner.
    """

    def test_a_real_heading_still_ends_a_section(self):
        # Positive control: the terminator works, so the negative control below
        # is testing suppression rather than a scan that never terminates.
        lines = ['## Claim Labels', '', SHARED_PATH, '', '## Objective', '', OTHER_PATH]

        start, end = section_span(lines, CLAIM_LABELS_HEADING_RE)

        body = '\n'.join(lines[start:end])
        assert (start, end) == (1, 4)
        assert SHARED_PATH in body
        assert OTHER_PATH not in body

    def test_a_hash_line_inside_a_fence_does_not_end_a_section(self):
        lines = ['## Claim Labels', '', *_FENCED_SURFACE, '', '## Objective']

        start, end = section_span(lines, CLAIM_LABELS_HEADING_RE)

        body = '\n'.join(lines[start:end])
        assert '# the files this spec expects to touch' in body
        assert OTHER_PATH in body, 'a fenced comment truncated the section body'

    def test_a_fenced_heading_does_not_open_a_section(self):
        # The opening scan carries the same state: a fenced ``## Claim Labels``
        # line inside an earlier example is not this document's section.
        lines = ['```text', '## Claim Labels', OTHER_PATH, '```']

        assert section_span(lines, CLAIM_LABELS_HEADING_RE) == (-1, -1)


class TestFencedExpectedSurface:
    def test_a_fenced_path_list_with_a_leading_comment_yields_every_path(self, tmp_path):
        declared = (SHARED_PATH, OTHER_PATH)
        text = _spec_text([_DEFAULT_CLAIM], list(_FENCED_SURFACE))

        paths = expected_surface_paths(text, tmp_path)

        assert len(paths) == len(declared), (
            f'{len(declared)} path(s) declared after the fenced example, {len(paths)} extracted'
        )
        assert paths == set(declared)

    def test_a_nested_fenced_path_list_yields_every_path(self, tmp_path):
        # The consumer-level proof that the run-length comparison reaches the
        # defect it was filed for: with the outer block ended at the first inner
        # ```, the following ``#`` comment reads as a heading and truncates the
        # section, dropping every path declared after it.
        declared = (SHARED_PATH, OTHER_PATH)
        text = _spec_text([_DEFAULT_CLAIM], list(_NESTED_FENCED_SURFACE))

        paths = expected_surface_paths(text, tmp_path)

        assert len(paths) == len(declared), (
            f'{len(declared)} path(s) declared after the nested fenced example, '
            f'{len(paths)} extracted'
        )
        assert paths == set(declared)

    def test_cross_check_reports_an_overlap_declared_after_a_nested_fence(self, plan_context):
        # End to end through the verb: the overlapping path sits after the inner
        # three-backtick example, so a truncated section reports a confident
        # no-overlap while still counting the spec in ``specs_scanned``.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(
            plan_context, 'PLAN-01-alpha.md', surface_lines=list(_NESTED_FENCED_SURFACE)
        )
        _write_live_plan(plan_context, LIVE_PLAN_ID, affected_files=[OTHER_PATH])

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['specs_scanned'] == 1, 'the own corpus did not materialize'
        assert result['candidates_scanned'] == 1, 'the candidate population did not materialize'
        assert result['file_overlap_match_count'] == 1
        assert result['file_overlap_matches'][0]['overlapping_files'] == OTHER_PATH
        assert result['collision_detected'] is True

    def test_a_path_outside_the_section_is_still_excluded(self, tmp_path):
        # Negative control: the fix widens the body past a fenced comment, it
        # does not stop bounding the section.
        text = _spec_text(
            [_DEFAULT_CLAIM],
            list(_FENCED_SURFACE),
            objective=f'Background reading: {OUTSIDE_PATH} explains the seam.',
        )

        paths = expected_surface_paths(text, tmp_path)

        assert OUTSIDE_PATH not in paths
        assert paths == {SHARED_PATH, OTHER_PATH}

    def test_cross_check_reports_the_overlap_a_fenced_comment_used_to_hide(self, plan_context):
        # The end-to-end consequence: the overlap is on the LAST path of the
        # fenced list, the one a truncated body drops.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface_lines=list(_FENCED_SURFACE))
        _write_live_plan(plan_context, LIVE_PLAN_ID, affected_files=[OTHER_PATH])

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['specs_scanned'] == 1, 'the own corpus did not materialize'
        assert result['candidates_scanned'] == 1, 'the candidate population did not materialize'
        assert result['file_overlap_match_count'] == 1
        assert result['file_overlap_matches'][0]['overlapping_files'] == OTHER_PATH
        assert result['collision_detected'] is True


class TestFencedClaimParsing:
    def test_a_real_heading_still_ends_the_claim_section(self, plan_context):
        # Positive control: ``_DEFAULT_SURFACE`` is itself a top-level bullet, so
        # a claim count of 1 proves the ``## Expected Surface`` heading terminated
        # the claim section rather than the scan simply finding one bullet.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')

        result = cmd_corpus_verdicts(Namespace(slug=SLUG))

        assert result['specs_scanned'] == 1
        assert result['claims_scanned'] == 1

    def test_a_fenced_bullet_is_not_counted_and_later_claims_survive(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', _FENCED_CLAIMS)

        result = cmd_corpus_verdicts(Namespace(slug=SLUG))

        assert result['specs_scanned'] == 1
        assert result['claims_scanned'] == 2, (
            'the fenced bullet was counted as a claim, or the fenced comment '
            'truncated the section and dropped the claim after it'
        )

    def test_claim_index_addressing_survives_a_fenced_block(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', _FENCED_CLAIMS)

        stamped = cmd_corpus_set_verdict(_set_verdict_args('PLAN-01', 1, evidence='second only'))
        result = cmd_corpus_verdicts(Namespace(slug=SLUG))

        assert stamped['status'] == 'success'
        assert stamped['claims_total'] == 2
        assert result['count'] == 1
        assert result['claims'][0]['claim_index'] == 1
        assert result['claims'][0]['evidence'] == 'second only'

    def test_a_verdict_stamped_before_a_fence_round_trips(self, plan_context):
        # Exercises ``_claim_block_end`` with fence state: the insertion point for
        # a claim whose block CONTAINS a fenced example.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', _FENCED_CLAIMS)

        cmd_corpus_set_verdict(_set_verdict_args('PLAN-01', 0, evidence='first only'))
        result = cmd_corpus_verdicts(Namespace(slug=SLUG))

        assert result['claims_scanned'] == 2, 'the stamp changed the claim population'
        assert result['count'] == 1
        assert result['claims'][0]['claim_index'] == 0
        assert result['claims'][0]['evidence'] == 'first only'


# =============================================================================
# Indentation boundary — the 0-3 space bound on fences and ATX headings
# =============================================================================
#
# CommonMark bounds block-level leading indentation to three spaces and counts a
# tab as four columns, so a four-space- or tab-indented delimiter inside a block
# is body text rather than a close, and one at top level opens nothing. Every
# control below is parametrized over a PUBLISHED indent population and pinned on
# BOTH sides of the boundary, because each earlier round's controls sat entirely
# on the permitted side of the clause it had just moved — a shape that passes
# while the scanner still disagrees with the rendered document.

#: The leading indentation CommonMark PERMITS on a fence delimiter or an ATX
#: heading. Enumerated rather than sampled: the boundary is at four columns, so
#: every value below it is a distinct case the scanner must admit.
_PERMITTED_INDENTS = ('', ' ', '  ', '   ')

#: The leading indentation CommonMark REJECTS. Four spaces is the first rejected
#: width; the tab-bearing forms are rejected because a tab advances to the next
#: four-column tab stop, so each of them reaches column four or beyond. All four
#: tab forms are kept because a bound written over ``\s`` admits every one of
#: them while a bound written over the literal space admits none.
_REJECTED_INDENTS = ('    ', '     ', '\t', ' \t', '   \t')

#: An Expected Surface fenced path list carrying a FOUR-SPACE-INDENTED
#: triple-backtick delimiter. That line is body text, so the outer block runs to
#: the column-0 close. Reading it as a close ends the block early, after which
#: the column-0 ``#`` comment on the next line reads as a heading and truncates
#: the section — and because BOTH declared paths sit after the indented
#: delimiter, the extracted surface is EMPTIED rather than merely shortened,
#: which is a confident no-overlap over a spec that declared two files.
#: The over-indented-delimiter BLOCK on its own — the mask-level counterpart of
#: :data:`_INDENTED_DELIMITER_SURFACE`, kept separate for the same reason
#: :data:`_NESTED_FENCE_BLOCK` is.
_INDENTED_DELIMITER_BLOCK = [
    '```text',
    '# the files this spec expects to touch',
    '    ```',
    '# an indented delimiter is body text, not the close of this block',
    '```',
]

_INDENTED_DELIMITER_SURFACE = [
    *_INDENTED_DELIMITER_BLOCK,
    *_surface(SHARED_PATH, OTHER_PATH),
]

#: The same shape with a TAB-indented delimiter. Kept as its own fixture rather
#: than folded into the parametrization above because the consumer-level proof
#: has to run end to end through the relocated single reader, and a tab reaches
#: the four-column boundary by a different mechanism than four spaces do.
_TAB_DELIMITER_SURFACE = [
    '```text',
    '# the files this spec expects to touch',
    '\t```',
    '# a tab is four columns, so this is body text too',
    '```',
    *_surface(SHARED_PATH, OTHER_PATH),
]

#: Two real claims with a fenced example between them whose body carries a
#: FOUR-SPACE-INDENTED triple-backtick line followed by a ``- `` line that is
#: still inside the block. Reading the indented delimiter as a close makes that
#: in-fence bullet the claim at index 1 — the index ``corpus set-verdict`` uses
#: to pick the bullet it WRITES — so the stamp lands inside the fenced example
#: instead of under the second real claim. Note that the pre-fix parse reports
#: the SAME claim count of two, because the column-0 ``` line then opens a fresh
#: block that swallows the real second claim: the count is not the
#: discriminator here, the membership is.
_INDENTED_DELIMITER_CLAIMS = [
    '- OBSERVED: first claim — read at `a.py` § `f`',
    '',
    '```text',
    '# an illustrative fragment, not a heading',
    '    ```',
    '- an illustrative bullet, not a claim',
    '```',
    '',
    '- OBSERVED: second claim — read at `b.py` § `g`',
]


class TestIndentPopulations:
    def test_the_swept_indent_populations_are_published_and_disjoint(self):
        """Publishes the population every parametrized control below sweeps."""
        assert len(_PERMITTED_INDENTS) == 4, (
            f'{len(_PERMITTED_INDENTS)} permitted indent(s) swept, expected the '
            'four widths below the four-column boundary'
        )
        assert len(_REJECTED_INDENTS) == 5, (
            f'{len(_REJECTED_INDENTS)} rejected indent(s) swept, expected two '
            'space widths at or past the boundary plus three tab-bearing forms'
        )
        assert not set(_PERMITTED_INDENTS) & set(_REJECTED_INDENTS)
        assert sum('\t' in indent for indent in _REJECTED_INDENTS) == 3, (
            'the tab arm of the rejected population shrank'
        )


class TestFenceDelimiterIndentationBound:
    """The bound applies independently to the OPEN and the CLOSE decision."""

    @pytest.mark.parametrize('indent', _PERMITTED_INDENTS)
    def test_a_permitted_indent_both_opens_and_closes_a_block(self, indent):
        # Positive control: the bound must not disable the indentation
        # CommonMark allows. Opener and closer carry the same indent here; the
        # independence of the two is pinned separately below.
        lines = [f'{indent}```text', '# not a heading', f'{indent}```', '# a real heading']

        mask = fenced_mask(lines)

        assert len(mask) == len(lines), 'the mask must carry one entry per scanned line'
        assert mask == [True, True, True, False]

    def test_the_opening_and_closing_indents_need_not_match(self):
        # CommonMark bounds each delimiter independently rather than requiring
        # the close to reproduce the opener's indentation.
        lines = ['   ```text', '# not a heading', ' ```', '# a real heading']

        mask = fenced_mask(lines)

        assert mask == [True, True, True, False]

    @pytest.mark.parametrize('indent', _REJECTED_INDENTS)
    def test_a_rejected_indent_does_not_close_an_open_block(self, indent):
        # The finding's direction: a delimiter past the bound is body text, so
        # the block runs on and the heading look-alike after it stays masked.
        lines = [
            '```text',
            '# not a heading',
            f'{indent}```',
            '# still not a heading',
            '```',
            '# a real heading',
        ]

        mask = fenced_mask(lines)

        assert len(mask) == len(lines)
        assert mask == [True, True, True, True, True, False]

    @pytest.mark.parametrize('indent', _REJECTED_INDENTS)
    def test_a_rejected_indent_does_not_open_a_block(self, indent):
        # The OTHER direction across the same boundary, and the reason the
        # docstring no longer claims a uniform bias: an over-indented delimiter
        # opens nothing, so the real heading after it must still be seen.
        lines = [f'{indent}```text', '# a real heading', 'trailing prose']

        mask = fenced_mask(lines)

        assert len(mask) == len(lines)
        assert not any(mask)

    def test_a_backtick_fence_whose_info_string_carries_a_backtick_opens_nothing(self):
        # A backtick fence's info string may not itself contain a backtick, so
        # this is a paragraph — the shape a sentence takes when it opens with
        # the fence marker and then quotes inline code. Reading it as an opener
        # masks the remainder of the document behind one prose line.
        lines = ['``` see `x` for the marker', '# a real heading', 'trailing prose']

        mask = fenced_mask(lines)

        assert len(mask) == len(lines)
        assert not any(mask)

    def test_a_tilde_fence_may_carry_a_backtick_in_its_info_string(self):
        # Matched pair: the info-string restriction is backtick-fence-scoped,
        # not a blanket ban on backticks in an info string.
        lines = ['~~~ see `x` for the marker', '# not a heading', '~~~', '# a real heading']

        mask = fenced_mask(lines)

        assert len(mask) == len(lines)
        assert mask == [True, True, True, False]


class TestHeadingIndentationBound:
    """The same clause, opposite direction: 1-3 space ATX headings ARE headings."""

    @pytest.mark.parametrize('indent', _PERMITTED_INDENTS)
    def test_a_permitted_indent_still_opens_a_section(self, indent):
        lines = [
            f'{indent}## Claim Labels',
            '',
            SHARED_PATH,
            '',
            '## Objective',
            '',
            OTHER_PATH,
        ]

        start, end = section_span(lines, CLAIM_LABELS_HEADING_RE)

        body = '\n'.join(lines[start:end])
        assert (start, end) == (1, 4)
        assert SHARED_PATH in body
        assert OTHER_PATH not in body

    @pytest.mark.parametrize('indent', _PERMITTED_INDENTS)
    def test_a_permitted_indent_still_terminates_a_section(self, indent):
        lines = ['## Claim Labels', '', SHARED_PATH, f'{indent}## Objective', '', OUTSIDE_PATH]

        start, end = section_span(lines, CLAIM_LABELS_HEADING_RE)

        body = '\n'.join(lines[start:end])
        assert (start, end) == (1, 3)
        assert SHARED_PATH in body
        assert OUTSIDE_PATH not in body

    @pytest.mark.parametrize('indent', _REJECTED_INDENTS)
    def test_a_rejected_indent_is_not_a_heading(self, indent):
        lines = [f'{indent}## Claim Labels', SHARED_PATH]

        assert HEADING_RE.match(lines[0]) is None
        assert CLAIM_LABELS_HEADING_RE.match(lines[0]) is None
        assert section_span(lines, CLAIM_LABELS_HEADING_RE) == (-1, -1)


class TestAtxHeadingShape:
    """The rest of the ATX clause the section scanners depend on."""

    def test_a_hashtag_word_is_not_a_heading(self):
        assert HEADING_RE.match('#hashtag') is None

    def test_a_seven_hash_run_is_not_a_heading(self):
        assert HEADING_RE.match('####### too many hashes') is None

    def test_a_bare_hash_line_is_a_heading(self):
        # An empty ATX heading is still a heading, so it still terminates the
        # section above it rather than reading as body text.
        assert HEADING_RE.match('##') is not None

    def test_a_tab_separated_heading_is_recognised(self):
        assert CLAIM_LABELS_HEADING_RE.match('##\tClaim Labels') is not None

    def test_an_optional_closing_hash_sequence_is_accepted(self):
        assert CLAIM_LABELS_HEADING_RE.match('## Claim Labels ##') is not None
        assert CLAIM_LABELS_HEADING_RE.match('  ## Claim Labels ###') is not None

    def test_a_trailing_hash_run_without_a_separator_is_not_a_closing_sequence(self):
        # The closing sequence must be preceded by whitespace, so this is a
        # heading whose TEXT differs and therefore not the addressed section.
        assert CLAIM_LABELS_HEADING_RE.match('## Claim Labels##') is None


#: The heading-case variants a spec may legitimately use. Markdown does not make
#: a heading's case significant, so each of these names the SAME section as the
#: template casing — they are spellings, not different sections.
_SURFACE_HEADING_CASES = ('## Expected Surface', '## expected surface', '## EXPECTED SURFACE')
_CLAIM_HEADING_CASES = ('## Claim Labels', '## claim labels', '## CLAIM LABELS')


def _spec_with_headings(
    claim_heading: str,
    surface_heading: str,
    claim_lines: list,
    surface_lines: list,
) -> str:
    """Render a spec whose two addressed headings are written verbatim.

    ``_spec_text`` hard-codes the template casing, which is exactly the variable
    under test here, so the two headings are caller-supplied instead.
    """
    lines = [
        '# PLAN-NN: Fixture',
        '',
        '## Objective',
        '',
        'Fixture objective.',
        '',
        claim_heading,
        '',
        *claim_lines,
        '',
        surface_heading,
        '',
        *surface_lines,
    ]
    return '\n'.join(lines) + '\n'


class TestHeadingCaseIsNotSectionIdentity:
    """A case-variant heading names the SAME section as its template-cased twin.

    The scanners matched the two addressed headings case-SENSITIVELY, so a spec
    written ``## expected surface`` resolved to an empty surface and an empty
    claim list. That is the confident-absence shape: nothing errors, the spec is
    still counted in ``specs_scanned``, and a zero overlap reads as "no
    collision" when the truth is "never looked". Each control below asserts the
    OBSERVED EVIDENCE — the resolved path set, the parsed claim list, and the
    population size — because a bare pass/fail cannot tell those two apart.
    """

    # --- Expected Surface: positive control ---------------------------------

    @pytest.mark.parametrize('surface_heading', _SURFACE_HEADING_CASES)
    def test_a_case_variant_surface_heading_yields_the_same_declared_paths(
        self, surface_heading, tmp_path
    ):
        declared = (SHARED_PATH, OTHER_PATH)
        template = _spec_with_headings(
            '## Claim Labels', '## Expected Surface', [_DEFAULT_CLAIM], _surface(*declared)
        )
        variant = _spec_with_headings(
            '## Claim Labels', surface_heading, [_DEFAULT_CLAIM], _surface(*declared)
        )

        template_paths = expected_surface_paths(template, tmp_path / 'template')
        variant_paths = expected_surface_paths(variant, tmp_path / 'variant')

        # The population the assertion was computed over, stated beside it: a
        # two-path surface, so an empty result is a measured miss, not an
        # uninteresting "there was nothing to find".
        assert len(template_paths) == len(declared), (
            f'{len(declared)} path(s) declared, {len(template_paths)} extracted '
            'from the TEMPLATE-cased spec — the comparand itself is broken'
        )
        assert variant_paths == set(declared), (
            f'{len(declared)} path(s) declared under {surface_heading!r}, '
            f'{len(variant_paths)} extracted'
        )
        assert variant_paths == template_paths

    # --- Expected Surface: negative control ----------------------------------

    def test_a_spec_that_declares_no_surface_section_still_resolves_to_empty(self, tmp_path):
        # Matched negative control. Case-blindness must not manufacture a
        # section: a spec with genuinely no Expected Surface heading resolves to
        # the empty set, and that zero is the CORRECT answer here.
        lines = [
            '# PLAN-NN: Fixture',
            '',
            '## Objective',
            '',
            f'Background reading: {OUTSIDE_PATH} explains the seam.',
            '',
            '## Claim Labels',
            '',
            _DEFAULT_CLAIM,
        ]
        text = '\n'.join(lines) + '\n'

        paths = expected_surface_paths(text, tmp_path)

        assert paths == set()
        # The path IS present in the document — so the empty result is the
        # section boundary holding, not the extractor failing to see anything.
        assert OUTSIDE_PATH in text

    def test_a_near_miss_heading_that_is_not_a_case_variant_is_still_rejected(self, tmp_path):
        # Case-blindness is not word-blindness: a DIFFERENT heading text must
        # still fail to open the section, or the widening went too far.
        text = _spec_with_headings(
            '## Claim Labels',
            '## Expected Surfaces',
            [_DEFAULT_CLAIM],
            _surface(SHARED_PATH, OTHER_PATH),
        )

        assert expected_surface_paths(text, tmp_path) == set()

    # --- Claim Labels: the symmetric peer pair -------------------------------

    @pytest.mark.parametrize('claim_heading', _CLAIM_HEADING_CASES)
    def test_a_case_variant_claim_heading_yields_the_same_parsed_claims(self, claim_heading):
        claim_lines = [
            '- OBSERVED: first claim — read at `a.py` § `f`',
            '- OBSERVED: second claim — read at `b.py` § `g`',
        ]
        variant = _spec_with_headings(
            claim_heading, '## Expected Surface', claim_lines, list(_DEFAULT_SURFACE)
        )

        section = parse_claim_section(variant.splitlines())
        claims = section['claims']

        assert section['state'] == CLAIM_SECTION_PARSED
        assert len(claims) == len(claim_lines), (
            f'{len(claim_lines)} claim(s) declared under {claim_heading!r}, '
            f'{len(claims)} parsed'
        )
        assert [claim['text'] for claim in claims] == [
            'OBSERVED: first claim — read at `a.py` § `f`',
            'OBSERVED: second claim — read at `b.py` § `g`',
        ]

    def test_a_spec_that_declares_no_claim_section_still_parses_no_claims(self):
        # Matched negative control for the claim peer. The empty claim list is
        # asserted TOGETHER with the state that explains it: after the parse-state
        # split, "no claims" is only the right answer here because the section is
        # genuinely ABSENT rather than merely unread.
        lines = [
            '# PLAN-NN: Fixture',
            '',
            '## Objective',
            '',
            'Fixture objective.',
            '',
            '## Expected Surface',
            '',
            *_DEFAULT_SURFACE,
        ]

        section = parse_claim_section(lines)

        assert section['claims'] == []
        assert section['state'] == CLAIM_SECTION_ABSENT

    def test_the_section_span_locates_a_case_variant_heading(self):
        # The shared primitive both consumers ride, pinned directly: the span is
        # resolved rather than the (-1, -1) "absent" pair. Driven through the
        # SURVIVING peer heading, which exercises the identical primitive against
        # a section ``orchestrator.py`` still owns; the surface heading's own
        # case-insensitivity is now pinned in the single reader's suite.
        lines = ['## claim labels', '', SHARED_PATH, '', '## Objective']

        assert section_span(lines, CLAIM_LABELS_HEADING_RE) != (-1, -1)


class TestIndentedDelimiterExpectedSurface:
    """Consumer-level proof: the declared path set survives the indented line."""

    @pytest.mark.parametrize(
        ('label', 'surface'),
        (('four-space', _INDENTED_DELIMITER_SURFACE), ('tab', _TAB_DELIMITER_SURFACE)),
    )
    def test_a_fenced_list_containing_an_over_indented_delimiter_yields_every_path(
        self, label, surface, tmp_path
    ):
        declared = (SHARED_PATH, OTHER_PATH)
        text = _spec_text([_DEFAULT_CLAIM], list(surface))

        paths = expected_surface_paths(text, tmp_path)

        assert len(paths) == len(declared), (
            f'{len(declared)} path(s) declared after the {label}-indented '
            f'delimiter, {len(paths)} extracted'
        )
        assert paths == set(declared)

    def test_a_path_outside_the_section_is_still_excluded(self, tmp_path):
        # Negative control: widening the body past an over-indented delimiter
        # must not stop the section being bounded at all.
        text = _spec_text(
            [_DEFAULT_CLAIM],
            list(_INDENTED_DELIMITER_SURFACE),
            objective=f'Background reading: {OUTSIDE_PATH} explains the seam.',
        )

        paths = expected_surface_paths(text, tmp_path)

        assert OUTSIDE_PATH not in paths
        assert paths == {SHARED_PATH, OTHER_PATH}

    def test_cross_check_reports_the_overlap_an_indented_delimiter_used_to_hide(self, plan_context):
        # End to end through the verb: with the section emptied, the spec is
        # still counted in ``specs_scanned`` and the zero reads as clean.
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(
            plan_context, 'PLAN-01-alpha.md', surface_lines=list(_INDENTED_DELIMITER_SURFACE)
        )
        _write_live_plan(plan_context, LIVE_PLAN_ID, affected_files=[OTHER_PATH])

        result = cmd_corpus_cross_check(Namespace(slug=SLUG))

        assert result['specs_scanned'] == 1, 'the own corpus did not materialize'
        assert result['candidates_scanned'] == 1, 'the candidate population did not materialize'
        assert result['file_overlap_match_count'] == 1
        assert result['file_overlap_matches'][0]['overlapping_files'] == OTHER_PATH
        assert result['collision_detected'] is True


class TestIndentedDelimiterClaimAddressing:
    """Write-path proof: ``--claim-index`` still addresses the intended bullet."""

    def test_the_parsed_claims_exclude_the_in_fence_bullet(self):
        lines = _spec_text(list(_INDENTED_DELIMITER_CLAIMS)).splitlines()

        section = parse_claim_section(lines)
        claims = section['claims']

        assert section['state'] == CLAIM_SECTION_PARSED
        assert len(claims) == 2, (
            f'{len(claims)} claim(s) parsed from a section declaring 2 — note the '
            'count alone does not discriminate here, so the membership is asserted next'
        )
        assert [claim['text'] for claim in claims] == [
            'OBSERVED: first claim — read at `a.py` § `f`',
            'OBSERVED: second claim — read at `b.py` § `g`',
        ]

    def test_claim_index_one_writes_under_the_second_claim_not_the_fenced_bullet(
        self, plan_context
    ):
        _write_status(plan_context, [_row('PLAN-01')])
        spec = _write_spec(plan_context, 'PLAN-01-alpha.md', list(_INDENTED_DELIMITER_CLAIMS))

        stamped = cmd_corpus_set_verdict(_set_verdict_args('PLAN-01', 1, evidence='second only'))

        assert stamped['status'] == 'success'
        assert stamped['claims_total'] == 2, 'the claim population did not materialize'
        text = spec.read_text(encoding='utf-8')
        assert text.count('- verdict:') == 1, 'a claim must never carry two verdicts'
        assert text.index('- verdict:') > text.index('- an illustrative bullet'), (
            'the verdict was written inside the fenced example — --claim-index 1 '
            'addressed the in-fence bullet'
        )
        assert text.index('- verdict:') > text.index('- OBSERVED: second claim'), (
            'the verdict was written above the second claim rather than beneath it'
        )

    def test_the_stamped_verdict_reads_back_bound_to_the_second_claim(self, plan_context):
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', list(_INDENTED_DELIMITER_CLAIMS))

        cmd_corpus_set_verdict(_set_verdict_args('PLAN-01', 1, evidence='second only'))
        result = cmd_corpus_verdicts(Namespace(slug=SLUG))

        assert result['specs_scanned'] == 1
        assert result['claims_scanned'] == 2, 'the stamp changed the claim population'
        assert result['count'] == 1
        assert result['claims'][0]['claim_index'] == 1
        assert result['claims'][0]['evidence'] == 'second only'

    def test_an_index_past_the_real_claims_is_rejected_without_writing(self, plan_context):
        # Negative control on the same addressing: the in-fence bullet is not
        # reachable by index at all, so index 2 is out of range over a
        # population of 2.
        _write_status(plan_context, [_row('PLAN-01')])
        spec = _write_spec(plan_context, 'PLAN-01-alpha.md', list(_INDENTED_DELIMITER_CLAIMS))
        before = spec.read_bytes()

        result = cmd_corpus_set_verdict(_set_verdict_args('PLAN-01', 2))

        assert result['status'] == 'error'
        assert result['error'] == 'claim_index_out_of_range'
        assert result['claims_total'] == 2
        assert result['claim_section_state'] == CLAIM_SECTION_PARSED
        assert '--section-scope' in result['recovery']
        assert spec.read_bytes() == before


# =============================================================================
# Non-vacuity guard for the indentation bound (pre-fix negative fixtures)
# =============================================================================
#
# The controls above are green by construction once the bound is in place, which
# is exactly the shape that let the preceding two rounds pass while the scanner
# still disagreed with the rendered document. These fixtures carry the pre-fix
# scanners VERBATIM — this module's accepted substitute for a red-first run,
# matching the negative-fixture pattern in
# ``test_orchestrator_read_boundary_contract.py`` — so the bound is proven to
# have CHANGED the match set rather than merely to be present.

#: The pre-fix delimiter regex, verbatim: an unbounded leading-whitespace
#: anchor, which admits any indentation and any tab.
_PRE_FIX_FENCE_DELIMITER_RE = re.compile(r'^\s*(?P<fence>`{3,}|~{3,})(?P<info>.*)$')

#: The pre-fix generic ATX heading regex, verbatim: column-0 only.
_PRE_FIX_HEADING_RE = re.compile(r'^#{1,6}\s')


def _pre_fix_fenced_mask(lines: list[str]) -> list[bool]:
    """The pre-fix mask, reproduced verbatim as frozen evidence.

    Not a second implementation to keep in step with the live one: it exists
    only to show that the fix changed behaviour on the recorded input. It
    differs from the live mask in exactly the two clauses this round closed —
    the unbounded indent anchor it matches with, and the absent info-string
    clause on an OPENING backtick fence.
    """
    mask = [False] * len(lines)
    open_char = ''
    open_length = 0
    for index, line in enumerate(lines):
        match = _PRE_FIX_FENCE_DELIMITER_RE.match(line)
        if match is None:
            mask[index] = bool(open_char)
            continue
        mask[index] = True
        run = match.group('fence')
        if not open_char:
            open_char, open_length = run[0], len(run)
        elif (
            run[0] == open_char
            and len(run) >= open_length
            and not match.group('info').strip()
        ):
            open_char, open_length = '', 0
    return mask


def test_the_bound_changed_the_delimiter_match_set():
    admitted_before = [
        indent for indent in _REJECTED_INDENTS if _PRE_FIX_FENCE_DELIMITER_RE.match(f'{indent}```')
    ]
    admitted_now = [
        indent for indent in _REJECTED_INDENTS if _orch._FENCE_DELIMITER_RE.match(f'{indent}```')
    ]

    assert len(admitted_before) == len(_REJECTED_INDENTS), (
        f'{len(admitted_before)} of {len(_REJECTED_INDENTS)} rejected indents were admitted '
        'by the pre-fix regex — the negative fixture no longer reproduces it, so every '
        'control above is vacuous'
    )
    assert admitted_now == [], (
        f'{len(admitted_now)} of {len(_REJECTED_INDENTS)} rejected indents are still '
        'admitted by the live regex'
    )


def test_the_bound_changed_the_heading_match_set():
    indented = [indent for indent in _PERMITTED_INDENTS if indent]
    rejected_before = [
        indent for indent in indented if _PRE_FIX_HEADING_RE.match(f'{indent}## Objective') is None
    ]
    accepted_now = [
        indent for indent in _PERMITTED_INDENTS if HEADING_RE.match(f'{indent}## Objective')
    ]

    assert len(rejected_before) == len(indented) == 3, (
        f'{len(rejected_before)} of {len(indented)} indented headings were rejected by the '
        'pre-fix regex — the negative fixture no longer reproduces it'
    )
    assert len(accepted_now) == len(_PERMITTED_INDENTS), (
        f'{len(accepted_now)} of {len(_PERMITTED_INDENTS)} permitted indents are accepted now'
    )


def test_the_pre_fix_mask_reproduces_the_recorded_disagreement():
    """The recorded finding, line for line, against the fixed mask beside it."""
    lines = list(_INDENTED_DELIMITER_BLOCK)

    pre_fix = _pre_fix_fenced_mask(lines)
    fixed = fenced_mask(lines)

    assert len(pre_fix) == len(fixed) == len(lines) == 5
    assert pre_fix == [True, True, True, False, True], (
        'the negative fixture no longer reproduces the pre-fix mask'
    )
    assert fixed == [True] * len(lines)
    assert sum(pre_fix) == 4, (
        f'{sum(pre_fix)} of {len(lines)} lines masked before the fix, {sum(fixed)} after — '
        'the unmasked line is the block\'s ``#`` comment, and reading it as a heading is '
        'what truncated the enclosing section and emptied the surface declared after it'
    )


def test_the_pre_fix_regex_opened_a_fence_on_a_prose_line_quoting_inline_code():
    lines = ['``` see `x` for the marker', '# a real heading', 'trailing prose']

    pre_fix = _pre_fix_fenced_mask(lines)
    fixed = fenced_mask(lines)

    assert pre_fix == [True, True, True], (
        'the negative fixture no longer reproduces the pre-fix reading of an '
        'inadmissible backtick info string'
    )
    assert not any(fixed), (
        f'{sum(fixed)} of {len(lines)} lines masked — a backtick fence whose info string '
        'carries a backtick is a paragraph, not an opener'
    )


# =============================================================================
# Non-vacuity guard for the own-corpus tally and the comparable population
# =============================================================================
#
# The two controls in ``TestCrossCheckPublishesTheComparedPopulation`` are green
# by construction once both fixes are in place — the same shape that let the
# pre-existing tally invariant pass over a fixture with no sibling epic, which is
# how the contamination survived review.
#
# Each control below reproduces a pre-fix expression verbatim and asserts it
# disagrees with the SHIPPED PRODUCTION VALUE over the same inputs. Binding the
# comparison to the real code rather than to a re-typed copy of it is the point:
# a control whose "shipped" side is re-implemented locally proves only that two
# expressions differ, and would stay green if the fix were reverted — which is
# exactly the confident-but-inert signal this epic exists to remove. The
# production side here comes from ``cmd_corpus_cross_check`` and ``_spec_record``
# themselves, so reverting either fix turns these red.


def _pre_fix_own_unreadable_count(shared_unreadable: list) -> int:
    """The pre-fix own-unreadable tally, verbatim: the length of the SHARED list.

    The shipped expression derives the count from the OWN population instead
    (``len(own_paths) - len(own)``), which is why this reproduction takes only the
    shared list — taking the own population would make it the shipped rule.
    """
    return len(shared_unreadable)


def _own_unreadable_tally(result: dict) -> int:
    """The shipped own-unreadable count, read off the real verb's payload."""
    return next(
        row['count']
        for row in result['spec_surface_states']
        if row['derivation_status'] == SURFACE_UNREADABLE
    )


def test_the_own_unreadable_tally_changed_over_a_sibling_bearing_population(plan_context):
    # One own spec, readable; one SIBLING spec unreadable. The shared list is what
    # the two rules disagree about, and the shipped side is the real verb's own
    # output — not a re-typed copy of its expression.
    _write_status(plan_context, [_row('PLAN-01')])
    _write_spec(plan_context, 'PLAN-01-alpha.md', surface_lines=_surface(SHARED_PATH))
    broken = _epic_dir(plan_context, SIBLING_SLUG) / 'plans' / 'PLAN-77-broken.md'
    broken.parent.mkdir(parents=True, exist_ok=True)
    broken.write_bytes(b'\xff\xfe \xff')

    result = cmd_corpus_cross_check(Namespace(slug=SLUG))

    pre_fix = _pre_fix_own_unreadable_count(result['unreadable'])
    shipped = _own_unreadable_tally(result)

    assert pre_fix == 1, 'the negative fixture no longer reproduces the pre-fix tally'
    assert shipped == 0, 'no OWN spec was unreadable, so the own tally is zero'
    assert pre_fix != shipped, (
        'the shipped verb agrees with the pre-fix expression, so the fix is not in force'
    )


def test_the_own_unreadable_tally_agrees_when_no_sibling_is_registered(plan_context):
    # Matched partner over the population the pre-existing invariant test uses
    # (no sibling epic): the two rules AGREE there, which is precisely why that
    # test could not observe the defect and why the sibling fixture was added.
    _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02')])
    _write_spec(plan_context, 'PLAN-01-alpha.md', surface_lines=_surface(SHARED_PATH))
    broken = _epic_dir(plan_context) / 'plans' / 'PLAN-02-broken.md'
    broken.write_bytes(b'\xff\xfe \xff')

    result = cmd_corpus_cross_check(Namespace(slug=SLUG))

    assert _pre_fix_own_unreadable_count(result['unreadable']) == _own_unreadable_tally(result) == 1, (
        'with no sibling contributing, both rules return the own count — the agreement '
        'that made the sibling-free fixture blind'
    )


def _pre_fix_comparable(claim, record: dict) -> bool:
    """The pre-fix predicate: comparability from the RESOLVED set, ungated.

    Takes the claim directly so the resolved entries are read the way the pre-fix
    ``_spec_record`` exposed them — before the admits gate withheld them.
    """
    return bool(_orch._claimed_paths(claim))


def test_the_comparable_predicate_changed_for_a_derived_spec_that_resolves_paths(tmp_path):
    """The one shape that separates the two rules: DERIVED and resolving.

    The shipped side is ``_spec_record``'s own output, so reverting the gate turns
    this red. A spec that resolves nothing is excluded by both rules and cannot
    witness the change — pinned below as the matched negative, alongside a
    declarative positive so the fix cannot pass by excluding everything.
    """
    spec = tmp_path / 'PLAN-01-derived.md'
    spec.write_text(
        '# PLAN-01\n\n## Expected Surface\n\n'
        '- DERIVED from the plans this one supersedes.\n'
        f'- OBSERVED: `{SHARED_PATH}` — `f`\n',
        encoding='utf-8',
    )
    claim = _orch._spec_claim(spec, PROJECT_ROOT)
    record = _orch._spec_record(SLUG, spec, PROJECT_ROOT)

    assert claim is not None and claim.spec_class == SURFACE_DERIVED
    assert _pre_fix_comparable(claim, record) is True, (
        'the fixture is only load-bearing if the derived spec DOES resolve a path'
    )
    assert record['paths'] == set(), (
        'a derived spec must contribute no comparable path however many it resolves'
    )


def test_the_comparable_predicate_is_unchanged_for_the_two_non_witnessing_shapes(tmp_path):
    # Matched controls for the test above: neither shape can distinguish the two
    # rules, so a fix that narrowed everything, or nothing, would still pass here.
    derived_empty = tmp_path / 'empty' / 'PLAN-02-derived.md'
    derived_empty.parent.mkdir(parents=True, exist_ok=True)
    derived_empty.write_text(
        '# PLAN-02\n\n## Expected Surface\n\n- DERIVED, and nothing resolvable.\n',
        encoding='utf-8',
    )
    declarative = tmp_path / 'declarative' / 'PLAN-03-alpha.md'
    declarative.parent.mkdir(parents=True, exist_ok=True)
    declarative.write_text(
        f'# PLAN-03\n\n## Expected Surface\n\n- OBSERVED: `{SHARED_PATH}` — `f`\n',
        encoding='utf-8',
    )

    empty_record = _orch._spec_record(SLUG, derived_empty, PROJECT_ROOT)
    declarative_record = _orch._spec_record(SLUG, declarative, PROJECT_ROOT)

    assert empty_record['derivation_status'] == SURFACE_DERIVED
    assert empty_record['paths'] == set(), 'both rules exclude a derived spec resolving nothing'
    assert declarative_record['derivation_status'] == SURFACE_DECLARATIVE
    assert declarative_record['paths'] == {SHARED_PATH}, (
        'the gate must not narrow the declarative case — without this the fix could pass '
        'by withholding paths from everything'
    )


def test_a_spec_whose_bytes_are_not_utf8_is_unreadable_in_both_verbs(tmp_path):
    """The decode route must reach ``unreadable`` rather than escaping as an error.

    ``read_text`` raises ``UnicodeDecodeError`` — a ``ValueError``, not an
    ``OSError`` — so a reader catching only ``OSError`` let this case propagate,
    leaving ``unreadable`` reachable through the open-failure route alone. Both
    entry points are pinned, because only one of them re-read the file itself and
    the two must agree about the same spec.
    """
    spec = tmp_path / 'PLAN-01-broken.md'
    spec.write_bytes(b'\xff\xfe not valid utf-8 \xff')

    assert _orch._spec_claim(spec, PROJECT_ROOT) is None
    assert _orch._spec_record(SLUG, spec, PROJECT_ROOT) is None
    assert _orch._surface_state(spec, PROJECT_ROOT) == (SURFACE_UNREADABLE, None)


# =============================================================================
# Separate vocabularies, separate bindings
# =============================================================================


def test_the_parse_outcome_and_the_readiness_verdict_have_distinct_bindings():
    """Two independent vocabularies must not share one module-level binding.

    They coincide in spelling, so a single ``INDETERMINATE`` name would let a
    change to either silently move the other. The value equality is asserted
    alongside the binding separation so this reads as "two names, same spelling"
    rather than as an accidental divergence.
    """
    assert _orch.VERDICT_INDETERMINATE == 'indeterminate'
    assert _orch.READINESS_INDETERMINATE == 'indeterminate'
    assert not hasattr(_orch, 'INDETERMINATE'), (
        'the shadowed shared binding is back — each vocabulary owns its own name'
    )


# =============================================================================
# Single-implementation guard (population-derived)
# =============================================================================


#: The code-level signature of the verdict grammar: the distinctive key names
#: together with the separator literal. A second formatter or parser cannot be
#: written without carrying all three.
_GRAMMAR_SIGNATURE = ('checked_at', 'rescoped', VERDICT_SEPARATOR)


def _marketplace_modules() -> list:
    return sorted(MARKETPLACE_ROOT.rglob('*.py'))


def test_marketplace_module_population_is_non_empty():
    """Guards the single-implementation assertion below against a vacuous pass."""
    modules = _marketplace_modules()

    assert modules, f'no Python modules enumerated under {MARKETPLACE_ROOT}'
    assert any(module.name == 'orchestrator.py' for module in modules)


def test_only_one_module_implements_the_verdict_grammar():
    """Fails the moment a second formatter or parser of the field appears.

    Population-derived: the marketplace Python surface is enumerated at test
    time, never listed by hand — a hard-coded list would pass vacuously against
    exactly the duplicate this guard exists to catch.
    """
    carriers = [
        module
        for module in _marketplace_modules()
        if all(token in module.read_text(encoding='utf-8', errors='ignore') for token in _GRAMMAR_SIGNATURE)
    ]

    assert [module.name for module in carriers] == ['orchestrator.py'], (
        'the re-grounding verdict grammar has a second implementation: '
        f'{[str(module) for module in carriers]}'
    )


# =============================================================================
# CLI boundary (constructed argv at the subprocess boundary)
# =============================================================================


class TestCorpusCli:
    def test_should_enumerate_through_cli(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}
        _write_status(plan_context, [_row('PLAN-01'), _row('PLAN-02')])
        _write_spec(plan_context, 'PLAN-01-alpha.md')

        result = run_script(SCRIPT_PATH, 'corpus', 'enumerate', '--slug', SLUG, env_overrides=env)

        assert result.returncode == 0
        assert 'status: success' in result.stdout
        assert 'rows_total: 2' in result.stdout
        assert 'rows_without_spec_count: 1' in result.stdout

    def test_should_cross_check_through_cli(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', surface_lines=_surface(SHARED_PATH))
        _write_live_plan(plan_context, LIVE_PLAN_ID, affected_files=[SHARED_PATH])

        result = run_script(SCRIPT_PATH, 'corpus', 'cross-check', '--slug', SLUG, env_overrides=env)

        assert result.returncode == 0
        assert 'status: success' in result.stdout
        assert 'plans_scanned: 1' in result.stdout
        assert 'file_overlap_match_count: 1' in result.stdout
        assert 'collision_detected: true' in result.stdout

    def test_should_set_and_read_a_verdict_through_cli(self, plan_context):
        env = {'PLAN_BASE_DIR': str(plan_context.fixture_dir)}
        _write_status(plan_context, [_row('PLAN-01')])
        _write_spec(plan_context, 'PLAN-01-alpha.md', _ONE_CLAIM)

        stamped = run_script(
            SCRIPT_PATH,
            'corpus',
            'set-verdict',
            '--slug',
            SLUG,
            '--plan',
            'PLAN-01',
            '--claim-index',
            '0',
            '--verdict',
            'contradicted',
            '--checked-at',
            SHA,
            '--by',
            PRODUCER,
            '--rescoped',
            'no',
            '--evidence',
            'no such branch at this sha',
            env_overrides=env,
        )
        read_back = run_script(SCRIPT_PATH, 'corpus', 'verdicts', '--slug', SLUG, env_overrides=env)

        assert stamped.returncode == 0
        assert 'replaced: false' in stamped.stdout
        assert read_back.returncode == 0
        assert 'blocking_count: 1' in read_back.stdout
