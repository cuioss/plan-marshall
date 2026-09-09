# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``compile-report.py``.

Scope: the documents a live run writes, which conditional sections it emits, and how
archived mode differs — its filename, and its refusal to overwrite.
"""

from __future__ import annotations

import itertools
import re
import shutil
from datetime import UTC, datetime, timedelta
from pathlib import Path

import retro_sections as _retro_sections
from _compile_report_fixtures import (
    _COLLECT_FRAGMENTS_SCRIPT,
    _FRAGMENT_TO_ASPECT,
    _STRIPPED_ARCHIVE_FIXTURE,
    SCRIPT_PATH,
    _compile_report,
    _registry_render_fragment_lines,
    _run_args,
    _write_fragments,
    cmd_run,
)
from _plan_retrospective_fixtures import setup_archived_plan, setup_live_plan
from toon_parser import parse_toon

from conftest import MARKETPLACE_ROOT, run_script

_REFERENCES_DIR = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'references'

#: Top-level keys the log-analysis fragment shape carries beyond the original
#: fixture's counts/percentiles core. Written out rather than derived from the
#: reference document: a list read back from the same document the widened
#: fixture is measured against could not see that document change.
WIDENED_LOG_ANALYSIS_KEYS = (
    'build_time',
    'script_cost_rollup',
    'context_position_cost',
    'global_log_signals',
)


def _documented_ratio_keys() -> set[str]:
    """The ratio identifiers declared by ``plan-efficiency.md``'s fragment shape.

    Parsed from the document rather than restated here, so the fixture below is
    measured against the shipped contract and not against a second copy of it.
    Anchored on the ``ratios:`` line itself and terminated by the first line that
    is not an indented ``key:`` entry, so a reflow or an inserted block above
    cannot shift what is read.
    """
    lines = (_REFERENCES_DIR / 'plan-efficiency.md').read_text(encoding='utf-8').split('\n')
    keys: set[str] = set()
    inside = False
    for line in lines:
        if line.rstrip() == 'ratios:':
            inside = True
            continue
        if not inside:
            continue
        entry = re.match(r'^  (\w+):', line)
        if entry is None:
            break
        keys.add(entry.group(1))
    if not keys:
        raise AssertionError(
            'no ratio identifiers were parsed out of plan-efficiency.md — the '
            'assertions below would compare against an empty set and prove nothing'
        )
    return keys


class TestCommittedFragmentKeyNames:
    """The committed fixtures are measured against the shipped contract by NAME.

    A fixture renamed to a new key while nothing asserts the key name is a
    fixture that cannot see the contract revert: the ratio block would go back to
    the retired spelling and the whole directory would stay green, because every
    consumer test reads whatever the fixture happens to carry.
    """

    def test_the_efficiency_fixture_names_the_worked_time_ratio(self) -> None:
        """``worked_seconds_per_task`` is the key; ``seconds_per_task`` is retired.

        The rename is load-bearing rather than cosmetic — the retired spelling
        divided WALL CLOCK by task count and asserted a per-task cost the number
        was not — so the identifier is what carries the meaning here and is what
        is asserted. Keyed on the identifier alone: a prose assertion over the
        document would be brittle to rewording, and the document deliberately
        still MENTIONS the retired name when explaining why it was retired.
        """
        fragment = parse_toon(
            (_STRIPPED_ARCHIVE_FIXTURE / 'work' / 'fragment-plan-efficiency.toon').read_text(encoding='utf-8')
        )
        documented = _documented_ratio_keys()
        ratios = fragment['ratios']

        assert 'worked_seconds_per_task' in documented
        assert 'seconds_per_task' not in documented
        assert 'worked_seconds_per_task' in ratios
        assert 'seconds_per_task' not in ratios
        assert set(ratios) <= documented, (
            f'the fixture carries ratio keys the shipped shape does not declare: {sorted(set(ratios) - documented)}'
        )

    def test_the_efficiency_fixture_carries_the_ratio_numerator_companion(self) -> None:
        """A ratio key without its numerator in ``totals`` is not a whole record.

        ``worked_seconds_per_task`` reads ``totals.worked_seconds``; the retired
        spelling read ``totals.duration_seconds``. Both fields exist in the
        fixture, so the ratio key alone does not tell a reader which numerator
        produced it — the companion is what makes the pair legible, and its
        absence is what a revert would leave behind.
        """
        fragment = parse_toon(
            (_STRIPPED_ARCHIVE_FIXTURE / 'work' / 'fragment-plan-efficiency.toon').read_text(encoding='utf-8')
        )
        totals = fragment['totals']

        assert 'worked_seconds' in totals
        assert 'files_modified' in totals, 'the companion of tokens_per_file_modified'


class TestLiveMode:
    def test_writes_quality_verification_document(self, tmp_path, monkeypatch):
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        fragments = _write_fragments(tmp_path)

        result = run_script(
            SCRIPT_PATH,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--fragments-file',
            str(fragments),
        )
        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        expected = plan_dir / 'quality-verification-report.md'
        assert Path(data['output_path']) == expected
        assert expected.exists()
        content = expected.read_text(encoding='utf-8')
        assert f'Plan Retrospective — {plan_id}' in content
        assert 'Executive Summary' in content
        assert 'mode: live' in content

    def test_conditional_sections_omitted_when_empty(self, tmp_path, monkeypatch):
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        fragments = _write_fragments(tmp_path, with_failure_aspects=False)

        result = run_script(
            SCRIPT_PATH,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--fragments-file',
            str(fragments),
        )
        assert result.success, result.stderr
        data = result.toon()
        # Benign omission: the trigger fragments are absent, so nothing was
        # dropped and the run stays clean.
        assert data['status'] == 'success'
        assert not data.get('sections_dropped')
        omitted = data['sections_omitted']
        assert 'Script Failure Analysis' in omitted
        assert 'Permission Prompt Analysis' in omitted
        content = (plan_dir / 'quality-verification-report.md').read_text()
        assert 'Script Failure Analysis' not in content
        assert 'Permission Prompt Analysis' not in content

    def test_conditional_sections_emitted_when_data_present(self, tmp_path, monkeypatch):
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        fragments = _write_fragments(tmp_path, with_failure_aspects=True)

        result = run_script(
            SCRIPT_PATH,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--fragments-file',
            str(fragments),
        )
        assert result.success, result.stderr
        data = result.toon()
        written = data['sections_written']
        assert 'Script Failure Analysis' in written
        assert 'Permission Prompt Analysis' in written


class TestArchivedMode:
    def test_archived_mode_writes_audit_filename(self, tmp_path):
        archived = setup_archived_plan(tmp_path)
        fragments = _write_fragments(tmp_path)
        result = run_script(
            SCRIPT_PATH,
            'run',
            '--archived-plan-path',
            str(archived),
            '--mode',
            'archived',
            '--fragments-file',
            str(fragments),
        )
        assert result.success, result.stderr
        data = result.toon()
        output_path = Path(data['output_path'])
        assert output_path.parent == archived
        assert output_path.name.startswith('quality-verification-report-audit-')
        assert output_path.name.endswith('.md')

    def test_archived_mode_does_not_overwrite(self, tmp_path, monkeypatch):
        archived = setup_archived_plan(tmp_path)

        # The archived-report filename stamp has 1-second resolution, so this
        # test used to sleep 1.1 s to force two distinct names. Inject a
        # monotonically advancing clock instead: every now() call returns a
        # timestamp one second later than the last, so consecutive runs are
        # deterministically distinct with no wall-clock wait. Run in-process so
        # the seam reaches the production module.
        ticks = itertools.count()

        class _AdvancingClock:
            """Stand-in for ``datetime`` whose ``now()`` advances one second per call."""

            @staticmethod
            def now(tz=None):
                return datetime(2026, 1, 15, 12, 0, 0, tzinfo=tz or UTC) + timedelta(seconds=next(ticks))

        monkeypatch.setattr(_compile_report, 'datetime', _AdvancingClock)

        # compile-report auto-deletes the fragments bundle on success, so
        # each invocation needs its own freshly-written bundle.
        fragments_a = _write_fragments(tmp_path)
        data_a = cmd_run(_run_args('archived', fragments_a, archived_plan_path=archived))
        fragments_b = _write_fragments(tmp_path)
        data_b = cmd_run(_run_args('archived', fragments_b, archived_plan_path=archived))

        assert data_a['output_path'] != data_b['output_path']
        assert Path(data_a['output_path']).exists()
        assert Path(data_b['output_path']).exists()


class TestStrippedArchiveIntegration:
    """Regression: full retrospective pipeline on the committed stripped archive.

    Copies the production-shape archived-plan fixture into a tmp dir and
    drives collect-fragments init → add → finalize → compile-report run
    end-to-end, with one ``add`` per registerable registry key — the
    committed fixture file where one exists, a fragment synthesized into
    the tmp archive otherwise. Asserts the rendered report contains real
    content for every registered section (no ``_No data provided._``
    placeholders and no missing headings). This is the integration test
    that would have caught all four bugs the parent plan fixes: wrong key
    names, wrong filenames, wrong log-source filenames, and missing-file
    silent-swallow.
    """

    def test_full_retrospective_on_stripped_archive(self, tmp_path):
        # copy the committed fixture so the test never mutates the
        # checked-in tree. Use a unique plan_id to avoid collisions with
        # the OS-tmp bundle path used by collect-fragments in archived
        # mode (``/tmp/plan-retrospective/retro-fragments-<plan_id>.toon``).
        archived = tmp_path / 'archived-plan-copy'
        shutil.copytree(_STRIPPED_ARCHIVE_FIXTURE, archived)
        plan_id = 'stripped-archive-integration-test'

        # init the bundle in archived mode.
        result_init = run_script(
            _COLLECT_FRAGMENTS_SCRIPT,
            'init',
            '--plan-id',
            plan_id,
            '--mode',
            'archived',
            '--archived-plan-path',
            str(archived),
        )
        assert result_init.success, result_init.stderr

        # Register one fragment per registerable registry key. The population is
        # DERIVED from the live ``SECTION_SPEC`` rather than hand-listed, so a
        # new registry row is covered here automatically: a committed fixture
        # file is used when ``_FRAGMENT_TO_ASPECT`` names one (keeping the
        # fixture-drift guard on the committed ten), and a minimal fragment is
        # synthesized into the already-copied tmp archive otherwise.
        #
        # ``collect-fragments add`` stores the PARSED fragment file as
        # ``bundle[aspect]``, so a synthesized file must carry the fragment BODY
        # only — the shared ``_registry_render_fragment_lines`` helper emits the
        # body under a leading ``{fragment_key}:`` line, so drop that line and
        # de-indent the remainder one level (which also de-indents the
        # ``dispatch_boundaries`` per-phase mapping correctly).
        work_dir = archived / 'work'
        aspect_to_fixture = {aspect: name for name, aspect in _FRAGMENT_TO_ASPECT.items()}
        for _heading, aspect, trigger in _retro_sections.SECTION_SPEC:
            if aspect.startswith('_'):
                continue
            fixture_name = aspect_to_fixture.get(aspect)
            if fixture_name is not None:
                fragment_path = work_dir / fixture_name
                assert fragment_path.exists(), f'Fixture drift: missing fragment file {fragment_path}'
            else:
                fragment_path = work_dir / f'fragment-{aspect}.toon'
                body_lines = _registry_render_fragment_lines(aspect, trigger)[1:]
                fragment_path.write_text('\n'.join(line[2:] for line in body_lines) + '\n', encoding='utf-8')
            result_add = run_script(
                _COLLECT_FRAGMENTS_SCRIPT,
                'add',
                '--plan-id',
                plan_id,
                '--archived-plan-path',
                str(archived),
                '--aspect',
                aspect,
                '--fragment-file',
                str(fragment_path),
            )
            assert result_add.success, f'add failed for aspect={aspect}: {result_add.stderr}'

        # finalize — returns the bundle path compile-report consumes.
        result_finalize = run_script(
            _COLLECT_FRAGMENTS_SCRIPT,
            'finalize',
            '--plan-id',
            plan_id,
            '--archived-plan-path',
            str(archived),
        )
        assert result_finalize.success, result_finalize.stderr
        finalize_data = result_finalize.toon()
        bundle_path = finalize_data['bundle_path']
        # The bundle carries one aspect per registerable registry key — derived,
        # never a hand-maintained count.
        assert int(finalize_data['aspect_count']) == len(_retro_sections.valid_aspect_keys())
        try:
            # compile the report in archived mode.
            result_compile = run_script(
                SCRIPT_PATH,
                'run',
                '--archived-plan-path',
                str(archived),
                '--mode',
                'archived',
                '--fragments-file',
                bundle_path,
            )
            assert result_compile.success, result_compile.stderr
            data = result_compile.toon()
            output_path = Path(data['output_path'])
            assert output_path.exists()

            # every section expected in _SECTION_SPEC was written —
            # none were omitted silently.
            sections_written = data.get('sections_written') or []
            sections_omitted = data.get('sections_omitted') or []
            # Derived from the live registry — the same population-derived shape
            # TestRegistryConsistencyGuard uses — so a new SECTION_SPEC row is
            # asserted here without editing a hand-maintained heading list.
            expected_headings = {
                heading
                for heading, fragment_key, _trigger in _retro_sections.SECTION_SPEC
                if not fragment_key.startswith('_')
            }
            missing = expected_headings - set(sections_written)
            assert not missing, f'Sections missing from report: {sorted(missing)} (omitted={sections_omitted})'

            # the rendered markdown carries real content for every
            # section, not the ``_No data provided._`` placeholder that
            # ``render_section_body`` emits when a fragment is missing.
            content = output_path.read_text(encoding='utf-8')
            assert '_No data provided._' not in content, (
                'Every registered section must render with real fragment data on the production-shape archive fixture.'
            )
            # Sanity: each non-executive section heading appears in the body.
            for heading in expected_headings:
                assert f'## {heading}' in content, f'Expected heading "## {heading}" not found in report'

            # The log-analysis fragment's newer blocks reach the RENDERED section.
            # The committed fixture stopped at the counts/percentiles core, so the
            # render path for every block added since was exercised by nothing —
            # a section could silently stop naming them and no test would move.
            # The section body is sliced out rather than searched whole, so a key
            # named under a different section cannot satisfy this.
            log_heading = next(
                heading
                for heading, fragment_key, _trigger in _retro_sections.SECTION_SPEC
                if fragment_key == 'log-analysis'
            )
            section = content.split(f'## {log_heading}', 1)[1].split('\n## ', 1)[0]
            for key in WIDENED_LOG_ANALYSIS_KEYS:
                assert key in section, (
                    f'the rendered "{log_heading}" section does not name {key!r}; '
                    'the widened fragment reached the report but the render dropped it'
                )
        finally:
            # compile-report auto-deletes the bundle on success but may
            # leave it behind on failure — clean up so we never leak into
            # the OS tmpdir across runs.
            try:
                Path(bundle_path).unlink()
            except FileNotFoundError:
                pass
