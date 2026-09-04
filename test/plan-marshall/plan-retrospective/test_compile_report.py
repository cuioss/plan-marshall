# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``compile-report.py``."""


from __future__ import annotations

from pathlib import Path

import retro_sections as _retro_sections
from _compile_report_fixtures import (
    _COLLECT_FRAGMENTS_SCRIPT_REGISTRY,
    SCRIPT_PATH,
    _run_args,
    _write_fragments,
    _write_full_registry_fragments,
    cmd_run,
)
from _plan_retrospective_fixtures import setup_archived_plan, setup_live_plan

from conftest import run_script


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
