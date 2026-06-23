# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``compile-report.py``."""

from __future__ import annotations

import importlib.util
import shutil
import sys
import time
from argparse import Namespace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _plan_retrospective_fixtures import setup_archived_plan, setup_live_plan  # noqa: E402

from conftest import MARKETPLACE_ROOT, run_script  # noqa: E402

# Absolute path to the committed stripped-archive fixture. The regression
# test below copies this tree into a tmp dir and drives the full
# collect-fragments + compile-report pipeline end-to-end. The fixture lives
# under version control so regressions in fragment key naming, bundle
# mode-propagation, or section rendering are caught deterministically.
_STRIPPED_ARCHIVE_FIXTURE = Path(__file__).parent / 'fixtures' / 'archived-plan'

_COLLECT_FRAGMENTS_SCRIPT = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts' / 'collect-fragments.py'
)

# Mapping from committed fragment filename (``fragment-{slug}.toon``) to the
# ``--aspect`` key that ``compile-report`` expects in _SECTION_SPEC. The
# ``invariant-check-summary`` filename intentionally differs from the
# consumer key ``invariant-summary`` — producers and consumers agreed on a
# rename and the fixture records the producer-side filename verbatim.
_FRAGMENT_TO_ASPECT = {
    'fragment-artifact-consistency.toon': 'artifact-consistency',
    'fragment-invariant-check-summary.toon': 'invariant-summary',
    'fragment-lessons-proposal.toon': 'lessons-proposal',
    'fragment-llm-to-script-opportunities.toon': 'llm-to-script-opportunities',
    'fragment-log-analysis.toon': 'log-analysis',
    'fragment-logging-gap-analysis.toon': 'logging-gap-analysis',
    'fragment-permission-prompt-analysis.toon': 'permission-prompt-analysis',
    'fragment-plan-efficiency.toon': 'plan-efficiency',
    'fragment-request-result-alignment.toon': 'request-result-alignment',
    'fragment-script-failure-analysis.toon': 'script-failure-analysis',
}

SCRIPT_PATH = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts' / 'compile-report.py'

# Direct import of compile-report.py (hyphenated filename → importlib). This
# gives the cleanup tests access to cmd_run and Path.unlink from the same
# namespace the script uses, so monkeypatching affects the production code.
_spec = importlib.util.spec_from_file_location('compile_report', str(SCRIPT_PATH))
assert _spec is not None and _spec.loader is not None
_compile_report = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_compile_report)
cmd_run = _compile_report.cmd_run


def _write_fragments(tmp_path: Path, with_failure_aspects: bool = False) -> Path:
    """Write a minimal TOON fragments bundle.

    The conditional aspects include at least one ``failures``/``prompts``
    item so ``should_emit`` recognizes them as non-empty.
    """
    # Top-level fragment keys are HYPHENATED to match the keys produced by
    # ``collect-fragments add --aspect <name>`` and consumed by
    # ``compile-report.py`` _SECTION_SPEC. Underscored variants would be
    # silently dropped by the consumer lookup.
    lines = [
        '_executive-summary:',
        '  summary: "All green. 2 warnings worth reviewing."',
        'request-result-alignment:',
        '  status: success',
        '  aspect: request_result_alignment',
        'artifact-consistency:',
        '  status: success',
        '  aspect: artifact_consistency',
        'log-analysis:',
        '  status: success',
        '  aspect: log_analysis',
        'invariant-summary:',
        '  status: success',
        '  aspect: invariant_summary',
        'plan-efficiency:',
        '  status: success',
        '  aspect: plan_efficiency',
        'llm-to-script-opportunities:',
        '  status: success',
        '  aspect: llm_to_script_opportunities',
        'logging-gap-analysis:',
        '  status: success',
        '  aspect: logging_gap_analysis',
        'lessons-proposal:',
        '  status: success',
        '  aspect: lessons_proposal',
    ]
    if with_failure_aspects:
        lines.extend(
            [
                'script-failure-analysis:',
                '  status: success',
                '  aspect: script_failure_analysis',
                '  failures[1]{notation,exit_code}:',
                '    plan-marshall:foo:bar,1',
                'permission-prompt-analysis:',
                '  status: success',
                '  aspect: permission_prompt_analysis',
                '  prompts[1]{tool,resource}:',
                '    Bash,some-command',
            ]
        )
    fragments_file = tmp_path / 'fragments.toon'
    fragments_file.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return fragments_file


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

    def test_archived_mode_does_not_overwrite(self, tmp_path):
        archived = setup_archived_plan(tmp_path)
        # compile-report auto-deletes the fragments bundle on success, so
        # each invocation needs its own freshly-written bundle.
        fragments_a = _write_fragments(tmp_path)
        result_a = run_script(
            SCRIPT_PATH,
            'run',
            '--archived-plan-path',
            str(archived),
            '--mode',
            'archived',
            '--fragments-file',
            str(fragments_a),
        )
        data_a = result_a.toon()
        time.sleep(1.1)
        fragments_b = _write_fragments(tmp_path)
        result_b = run_script(
            SCRIPT_PATH,
            'run',
            '--archived-plan-path',
            str(archived),
            '--mode',
            'archived',
            '--fragments-file',
            str(fragments_b),
        )
        data_b = result_b.toon()
        assert data_a['output_path'] != data_b['output_path']
        assert Path(data_a['output_path']).exists()
        assert Path(data_b['output_path']).exists()


class TestStrippedArchiveIntegration:
    """Regression: full retrospective pipeline on the committed stripped archive.

    Copies the production-shape archived-plan fixture into a tmp dir and
    drives collect-fragments init → add (x10) → finalize → compile-report
    run end-to-end. Asserts the rendered report contains real content for
    every registered section (no ``_No data provided._`` placeholders and
    no missing headings). This is the integration test that would have
    caught all four bugs the parent plan fixes: wrong key names, wrong
    filenames, wrong log-source filenames, and missing-file silent-swallow.
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

        # add each of the 10 committed fragment files under its
        # consumer-expected aspect key.
        work_dir = archived / 'work'
        for fragment_name, aspect in _FRAGMENT_TO_ASPECT.items():
            fragment_path = work_dir / fragment_name
            assert fragment_path.exists(), f'Fixture drift: missing fragment file {fragment_path}'
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
        assert int(finalize_data['aspect_count']) == 10
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
            expected_headings = {
                'Executive Summary',
                'Goals vs Outcomes',
                'Artifact Consistency',
                'Log Analysis',
                'Invariant Outcomes',
                'Plan Efficiency',
                'LLM-to-Script Opportunities',
                'Logging Gaps',
                'Script Failure Analysis',
                'Permission Prompt Analysis',
                'Proposed Lessons',
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
        finally:
            # compile-report auto-deletes the bundle on success but may
            # leave it behind on failure — clean up so we never leak into
            # the OS tmpdir across runs.
            try:
                Path(bundle_path).unlink()
            except FileNotFoundError:
                pass


class TestFaultPaths:
    def test_missing_fragments_file_errors(self, tmp_path, monkeypatch):
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        result = run_script(
            SCRIPT_PATH,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--fragments-file',
            str(tmp_path / 'does-not-exist.toon'),
        )
        assert not result.success


class TestSessionIdPassthrough:
    def test_session_id_written_to_header_when_provided(self, tmp_path, monkeypatch):
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
            '--session-id',
            'abc-123',
        )
        assert result.success, result.stderr
        content = (plan_dir / 'quality-verification-report.md').read_text()
        assert 'session_id: abc-123' in content

    def test_session_id_default_string_when_missing(self, tmp_path, monkeypatch):
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        fragments = _write_fragments(tmp_path)
        run_script(
            SCRIPT_PATH,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--fragments-file',
            str(fragments),
        )
        content = (plan_dir / 'quality-verification-report.md').read_text()
        assert 'session_id: not provided' in content


def _run_args(
    mode: str,
    fragments_path: Path,
    plan_id: str | None = None,
    archived_plan_path: Path | None = None,
    session_id: str | None = None,
) -> Namespace:
    """Build the ``argparse.Namespace`` that ``cmd_run`` expects."""
    return Namespace(
        command='run',
        plan_id=plan_id,
        archived_plan_path=str(archived_plan_path) if archived_plan_path else None,
        mode=mode,
        fragments_file=str(fragments_path),
        session_id=session_id,
        func=cmd_run,
    )


class TestFragmentBundleCleanup:
    """Task-4 coverage: fragment-bundle cleanup on cmd_run success vs failure."""

    def test_bundle_deleted_after_successful_live_run(self, tmp_path, monkeypatch):
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        fragments = _write_fragments(tmp_path)
        assert fragments.exists()

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
        assert (plan_dir / 'quality-verification-report.md').exists()
        assert not fragments.exists(), 'Fragments bundle should be deleted after successful live run'

    def test_bundle_deleted_after_successful_archived_run(self, tmp_path):
        archived = setup_archived_plan(tmp_path)
        fragments = _write_fragments(tmp_path)
        assert fragments.exists()

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
        output_path = Path(result.toon()['output_path'])
        assert output_path.exists()
        assert not fragments.exists(), 'Fragments bundle should be deleted after successful archived run'

    def test_bundle_persists_when_cmd_run_raises_before_write(self, tmp_path, monkeypatch):
        # create a live-mode plan directory, then point the script at
        # a non-existent plan_id so resolve_plan_dir() → plan_dir.exists() is
        # False and cmd_run raises ValueError BEFORE reaching the markdown
        # write (and therefore before the cleanup block).
        setup_live_plan(tmp_path, monkeypatch, plan_id='retro-happy')
        fragments = _write_fragments(tmp_path)
        assert fragments.exists()
        missing_plan_id = 'plan-that-does-not-exist'

        result = run_script(
            SCRIPT_PATH,
            'run',
            '--plan-id',
            missing_plan_id,
            '--mode',
            'live',
            '--fragments-file',
            str(fragments),
        )

        # script errored AND bundle still exists on disk for debugging
        assert not result.success
        assert fragments.exists(), 'Fragments bundle must persist when cmd_run raises before the markdown write'

    def test_cleanup_tolerates_missing_bundle_silently(self, tmp_path, monkeypatch, capsys):
        # call cmd_run in-process so we can monkeypatch Path.unlink.
        # The real fragments file exists during load_fragments; unlink raises
        # FileNotFoundError, simulating "bundle already removed" races.
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        fragments = _write_fragments(tmp_path)

        original_unlink = Path.unlink

        def fake_unlink(self, *args, **kwargs):
            if self == fragments:
                raise FileNotFoundError(str(self))
            return original_unlink(self, *args, **kwargs)

        monkeypatch.setattr(Path, 'unlink', fake_unlink)

        cmd_run(_run_args('live', fragments, plan_id=plan_id))

        # no raise (test would fail otherwise), no stderr warning
        captured = capsys.readouterr()
        assert 'WARN' not in captured.err
        assert 'failed to delete fragments bundle' not in captured.err
        # Markdown was still written since unlink failure is silent-tolerated
        assert (plan_dir / 'quality-verification-report.md').exists()

    def test_cleanup_logs_warning_on_permission_error(self, tmp_path, monkeypatch, capsys):
        # PermissionError (non-FileNotFoundError OSError) must be
        # logged to stderr but MUST NOT abort cmd_run.
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        fragments = _write_fragments(tmp_path)

        original_unlink = Path.unlink

        def fake_unlink(self, *args, **kwargs):
            if self == fragments:
                raise PermissionError(f'permission denied: {self}')
            return original_unlink(self, *args, **kwargs)

        monkeypatch.setattr(Path, 'unlink', fake_unlink)

        # cmd_run should complete successfully despite the unlink failure
        result = cmd_run(_run_args('live', fragments, plan_id=plan_id))

        # success path, stderr carries the WARN line
        assert result['status'] == 'success'
        assert (plan_dir / 'quality-verification-report.md').exists()
        captured = capsys.readouterr()
        assert 'WARN' in captured.err
        assert 'failed to delete fragments bundle' in captured.err
        assert str(fragments) in captured.err


# =============================================================================
# Phase Dispatch Boundaries section (lesson 2026-05-20-12-002)
# =============================================================================


def _write_fragments_with_dispatch_boundaries(
    tmp_path: Path,
    phases: dict[str, dict] | None,
) -> Path:
    """Write a fragments bundle that includes a ``dispatch_boundaries`` key.

    Args:
        tmp_path: pytest tmp_path fixture.
        phases: dict mapping phase name (e.g. ``"5-execute"``) to a per-phase
            dict (``present``, ``rows``, ``unknown_count``,
            ``clean_exit_queue_empty_count``). Pass ``None`` to omit the key
            entirely; pass ``{}`` to emit an empty dict.
    """
    import json

    # Start from the minimal fragments bundle.
    base_fragments = _write_fragments(tmp_path)
    content = base_fragments.read_text(encoding='utf-8')

    if phases is None:
        return base_fragments
    # Inline the dispatch_boundaries dict as a TOON nested block.
    lines = ['dispatch_boundaries:']
    if phases:
        for phase, data in phases.items():
            # TOON keys are unquoted bare identifiers; phase names like
            # ``4-plan`` are accepted verbatim by the parser.
            lines.append(f'  {phase}:')
            for k, v in data.items():
                if isinstance(v, list):
                    if not v:
                        lines.append(f'    {k}[0]:')
                    else:
                        lines.append(f'    {k}: {json.dumps(v)}')
                elif isinstance(v, bool):
                    lines.append(f'    {k}: {"true" if v else "false"}')
                else:
                    lines.append(f'    {k}: {v}')
    content = content + '\n'.join(lines) + '\n'
    fragments_file = tmp_path / 'fragments-dispatch-boundaries.toon'
    fragments_file.write_text(content, encoding='utf-8')
    return fragments_file


# =============================================================================
# Registry-consistency regression guard (deliverable 2)
# =============================================================================
#
# The class of defect this guard pins down: a producer aspect key drifting from
# the consumer's section map. ``retro_sections.SECTION_SPEC`` is the single
# shared registry both scripts consume — ``compile-report`` renders from it and
# ``collect-fragments add`` validates ``--aspect`` against the derived
# ``valid_aspect_keys()``. This guard asserts the full registry↔producer↔consumer
# round-trip so a future aspect-key add or rename that drifts the two apart fails
# at test time, distinct from D1's hand-picked local ``cmd_add`` unit cases.

# Direct import of retro_sections.py from the same scripts/ directory the
# executor puts on PYTHONPATH (conftest mirrors that path setup). Importing the
# live registry — rather than restating the key list — is what makes this guard
# self-maintaining: a new SECTION_SPEC row is automatically covered.
import retro_sections as _retro_sections  # noqa: E402

_COLLECT_FRAGMENTS_SCRIPT_REGISTRY = (
    MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts' / 'collect-fragments.py'
)


def _registry_render_fragment_lines(fragment_key: str, trigger: str | None) -> list[str]:
    """Return TOON lines for a single registry aspect that ``should_emit`` accepts.

    Conditional sections (``trigger is not None``) emit only when their fragment
    carries non-empty payload, so this synthesizes the minimal shape each
    ``should_emit`` branch recognizes:

    - ``dispatch_boundaries`` → a per-phase dict with one ``present: true`` phase.
    - ``manifest-decisions`` → ``manifest_present: true``.
    - every other conditional key → a one-item ``findings`` list.

    Unconditional sections (``trigger is None``) emit on a bare ``status: success``
    fragment.
    """
    if fragment_key == 'dispatch_boundaries':
        return [
            'dispatch_boundaries:',
            '  5-execute:',
            '    present: true',
            '    rows[0]:',
            '    unknown_count: 0',
            '    clean_exit_queue_empty_count: 0',
        ]
    lines = [f'{fragment_key}:', '  status: success']
    if trigger is None:
        return lines
    if fragment_key == 'manifest-decisions':
        lines.append('  manifest_present: true')
        return lines
    # Generic conditional section — a single findings entry satisfies should_emit.
    lines.extend(
        [
            '  findings[1]{severity,message}:',
            '    info,registry-consistency probe finding',
        ]
    )
    return lines


def _write_full_registry_fragments(tmp_path: Path) -> Path:
    """Write a fragments bundle carrying EVERY non-``_`` key in SECTION_SPEC.

    Each aspect's fragment is shaped so its (possibly conditional) section
    emits, so the rendered report must contain a section for every registry
    key — exercising the consumer-render side of the round-trip invariant.
    """
    lines = [
        '_executive-summary:',
        '  summary: "Registry-consistency round-trip probe."',
    ]
    for _heading, fragment_key, trigger in _retro_sections.SECTION_SPEC:
        if fragment_key.startswith('_'):
            continue
        lines.extend(_registry_render_fragment_lines(fragment_key, trigger))
    fragments_file = tmp_path / 'fragments-full-registry.toon'
    fragments_file.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return fragments_file


class TestRegistryConsistencyGuard:
    """End-to-end registry↔producer↔consumer round-trip guard.

    Pins the shared ``retro_sections.SECTION_SPEC`` registry to BOTH ends:
    every renderable section key must (a) render a report section through
    ``compile-report`` and (b) be a key ``collect-fragments add`` accepts. A
    future drift between the producer-validation set and the consumer-render
    set fails here, closing the silent-section-drop hole from both sides.
    """

    def test_every_registered_static_aspect_renders_a_report_section(self, tmp_path, monkeypatch):
        """Consumer side: compile-report renders a section for EVERY SECTION_SPEC key.

        Loops the live registry rather than a hand-curated heading list, so a
        new SECTION_SPEC row that compile-report fails to render is caught
        automatically.
        """
        # expected headings are derived from the registry itself.
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        fragments = _write_full_registry_fragments(tmp_path)
        expected_headings = {
            heading
            for heading, fragment_key, _trigger in _retro_sections.SECTION_SPEC
            if not fragment_key.startswith('_')
        }

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

        # every registry heading is written, none silently omitted.
        assert result.success, result.stderr
        data = result.toon()
        written = set(data['sections_written'])
        missing = expected_headings - written
        assert not missing, (
            f'Registry drift: SECTION_SPEC keys rendered no section: {sorted(missing)} '
            f'(omitted={data.get("sections_omitted")})'
        )
        # The rendered markdown carries each heading — guards against a
        # sections_written entry that names a heading the body never emits.
        content = (plan_dir / 'quality-verification-report.md').read_text(encoding='utf-8')
        for heading in expected_headings:
            assert f'## {heading}' in content, f'Registry key "{heading}" claimed written but absent from report body'

    def test_every_valid_aspect_key_is_accepted_by_collect_fragments_add(self, tmp_path, monkeypatch):
        """Producer side: collect-fragments add accepts EVERY valid_aspect_keys() entry.

        Loops the derived registerable-key set so the producer-validation set
        and the consumer-render set stay in lockstep — a key compile-report
        renders but cmd_add rejects (or vice versa) fails here.
        """
        # one plan, one bundle, then add each registry key in turn.
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        init_result = run_script(
            _COLLECT_FRAGMENTS_SCRIPT_REGISTRY,
            'init',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
        )
        assert init_result.success, init_result.stderr

        valid_keys = sorted(_retro_sections.valid_aspect_keys())
        assert valid_keys, 'valid_aspect_keys() returned an empty set — registry is mis-wired'

        # add every registry key; each must be accepted.
        for aspect in valid_keys:
            fragment = tmp_path / f'frag-{aspect}.toon'
            fragment.write_text(f'status: success\naspect: {aspect}\n', encoding='utf-8')
            add_result = run_script(
                _COLLECT_FRAGMENTS_SCRIPT_REGISTRY,
                'add',
                '--plan-id',
                plan_id,
                '--aspect',
                aspect,
                '--fragment-file',
                str(fragment),
            )
            assert add_result.success, f'add subprocess failed for aspect={aspect}: {add_result.stderr}'
            data = add_result.toon()
            assert data['status'] == 'success', (
                f'Registry drift: collect-fragments add rejected the registry key {aspect!r} '
                f'that compile-report renders — payload: {data}'
            )
            assert data['aspect'] == aspect

    def test_render_set_and_accept_set_are_identical(self, tmp_path, monkeypatch):
        """Lockstep invariant: the consumer-render key set == the producer-accept key set.

        The render set is every non-``_`` ``fragment_key`` in SECTION_SPEC; the
        accept set is ``valid_aspect_keys()``. Both derive from the same
        registry, so they must be byte-for-byte equal — this asserts the
        derivation never diverges (e.g. a future ``valid_aspect_keys`` filter
        change that drops a renderable key).
        """
        render_set = {
            fragment_key
            for _heading, fragment_key, _trigger in _retro_sections.SECTION_SPEC
            if not fragment_key.startswith('_')
        }
        accept_set = _retro_sections.valid_aspect_keys()
        assert render_set == accept_set, (
            'Registry drift: the compile-report render-set and the collect-fragments '
            f'accept-set diverged.\n  render-only: {sorted(render_set - accept_set)}'
            f'\n  accept-only: {sorted(accept_set - render_set)}'
        )


class TestPhaseDispatchBoundariesSection:
    """Rendering tests for the Phase Dispatch Boundaries section."""

    def test_section_emitted_when_fragment_has_present_phase(self, tmp_path, monkeypatch):
        """The section emits when at least one phase reports present=true."""
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        fragments = _write_fragments_with_dispatch_boundaries(
            tmp_path,
            phases={
                '5-execute': {
                    'present': True,
                    'rows': [],
                    'unknown_count': 0,
                    'clean_exit_queue_empty_count': 3,
                },
            },
        )
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
        assert 'Phase Dispatch Boundaries' in data['sections_written']
        content = (plan_dir / 'quality-verification-report.md').read_text(encoding='utf-8')
        assert '## Phase Dispatch Boundaries' in content
        # The per-phase markdown table renders with one row per recorded phase.
        assert '| 5-execute | 0 | 0 | 3 |' in content

    def test_section_omitted_when_fragment_absent(self, tmp_path, monkeypatch):
        """No fragment ⇒ section is omitted (gate returns false)."""
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        fragments = _write_fragments_with_dispatch_boundaries(tmp_path, phases=None)
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
        assert 'Phase Dispatch Boundaries' in data['sections_omitted']
        content = (plan_dir / 'quality-verification-report.md').read_text(encoding='utf-8')
        assert '## Phase Dispatch Boundaries' not in content

    def test_per_phase_table_renders_one_row_per_recorded_phase(self, tmp_path, monkeypatch):
        """All three phases (4-plan, 5-execute, 6-finalize) appear as table rows."""
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        fragments = _write_fragments_with_dispatch_boundaries(
            tmp_path,
            phases={
                '4-plan': {
                    'present': True,
                    'rows': [],
                    'unknown_count': 0,
                    'clean_exit_queue_empty_count': 0,
                },
                '5-execute': {
                    'present': True,
                    'rows': [],
                    'unknown_count': 1,
                    'clean_exit_queue_empty_count': 2,
                },
                '6-finalize': {
                    'present': True,
                    'rows': [],
                    'unknown_count': 0,
                    'clean_exit_queue_empty_count': 0,
                },
            },
        )
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
        content = (plan_dir / 'quality-verification-report.md').read_text(encoding='utf-8')
        # Per-phase markdown table includes one row per recorded phase, sorted.
        assert '| 4-plan | 0 | 0 | 0 |' in content
        assert '| 5-execute | 0 | 1 | 2 |' in content
        assert '| 6-finalize | 0 | 0 | 0 |' in content
