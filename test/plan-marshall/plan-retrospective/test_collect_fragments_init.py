# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``collect-fragments.py``."""


from __future__ import annotations

import tempfile
from pathlib import Path

from _collect_fragments_fixtures import (
    SCRIPT_PATH,
    _add_aspect,
    _init_bundle,
    _valid_fragment_body,
    _write_fragment,
)
from _plan_retrospective_fixtures import setup_live_plan  # noqa: E402

from conftest import run_script  # noqa: E402

# =============================================================================
# init — live mode
# =============================================================================


class TestInitLiveMode:
    def test_creates_bundle_with_meta_mode_in_plan_dir(self, tmp_path, monkeypatch):
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)

        result = run_script(
            SCRIPT_PATH,
            'init',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
        )

        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        assert data['operation'] == 'init'
        expected_path = plan_dir / 'work' / 'retro-fragments.toon'
        assert Path(data['bundle_path']) == expected_path
        assert expected_path.exists()
        # Bundle is seeded with _meta.mode — it is never literally empty.
        from toon_parser import parse_toon

        parsed = parse_toon(expected_path.read_text(encoding='utf-8'))
        assert parsed['_meta']['mode'] == 'live'

    def test_init_is_idempotent_overwriting_existing_bundle(self, tmp_path, monkeypatch):
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        bundle_path = plan_dir / 'work' / 'retro-fragments.toon'
        bundle_path.parent.mkdir(parents=True, exist_ok=True)
        bundle_path.write_text('stale: data\n', encoding='utf-8')

        result = run_script(
            SCRIPT_PATH,
            'init',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
        )

        assert result.success, result.stderr
        from toon_parser import parse_toon

        parsed = parse_toon(bundle_path.read_text(encoding='utf-8'))
        # Stale content is replaced with the meta-only bundle.
        assert parsed == {'_meta': {'mode': 'live'}}


# =============================================================================
# init — archived mode
# =============================================================================


class TestInitArchivedMode:
    """Archived-mode init now honours ``--archived-plan-path``.

    When the caller passes ``--archived-plan-path``, the bundle is created at
    ``<archived_plan_path>/work/retro-fragments.toon`` so that
    ``init``/``add``/``finalize`` from the same caller all converge on the
    same bundle root. When the flag is omitted, archived mode falls back to a
    synthetic per-plan tmp directory so production audits without an explicit
    archive path never write into a real archived plan dir.
    """

    def test_honours_archived_plan_path_when_provided(self, tmp_path):
        plan_id = 'archived-honored'
        archived_plan_path = tmp_path / '2026-04-27-archived-honored'
        archived_plan_path.mkdir(parents=True, exist_ok=True)

        result = run_script(
            SCRIPT_PATH,
            'init',
            '--plan-id',
            plan_id,
            '--mode',
            'archived',
            '--archived-plan-path',
            str(archived_plan_path),
        )

        assert result.success, result.stderr
        data = result.toon()
        bundle_path = Path(data['bundle_path']).resolve()
        # Bundle now lives under the caller-supplied archive root.
        # Resolve both sides because resolve_bundle_path canonicalizes paths
        # (macOS /var → /private/var symlink) and pytest's tmp_path on Linux
        # may share /tmp with tempfile.gettempdir().
        assert bundle_path == (archived_plan_path / 'work' / 'retro-fragments.toon').resolve()
        assert bundle_path.exists()
        # OS-tmp synthetic fallback is NOT used when --archived-plan-path is
        # provided. Check the synthetic path specifically rather than
        # tempfile.gettempdir() — on Linux, pytest's tmp_path lives under
        # /tmp, so a generic "tempdir not an ancestor" assertion fails there.
        synthetic_root = (Path(tempfile.gettempdir()) / 'plan-retrospective' / f'plan-{plan_id}').resolve()
        assert synthetic_root not in bundle_path.parents

    def test_falls_back_to_synthetic_tmp_when_archived_plan_path_missing(self):
        # The synthetic fallback root is keyed on plan_id
        # (<tmp>/plan-retrospective/plan-<plan_id>), so a fixed plan_id makes
        # the synthetic path shared state across test runs — a leftover from
        # an interrupted run or a concurrent xdist worker collides on the same
        # directory. Use a per-invocation-unique plan_id so each run resolves
        # to its own synthetic root, removing the shared-state collision and
        # the pre-clean step it forced.
        import uuid

        plan_id = f'archived-fallback-{uuid.uuid4().hex}'
        # resolve the synthetic root because resolve_bundle_path now
        # returns canonical absolute paths; on macOS tempfile.gettempdir()
        # is /var/folders/... while .resolve() canonicalizes to
        # /private/var/folders/...
        synthetic_root = (Path(tempfile.gettempdir()) / 'plan-retrospective' / f'plan-{plan_id}').resolve()

        result = run_script(
            SCRIPT_PATH,
            'init',
            '--plan-id',
            plan_id,
            '--mode',
            'archived',
        )

        try:
            assert result.success, result.stderr
            data = result.toon()
            bundle_path = Path(data['bundle_path'])
            assert bundle_path == synthetic_root / 'work' / 'retro-fragments.toon'
            assert bundle_path.exists()
        finally:
            # Cleanup this invocation's unique synthetic dir.
            if synthetic_root.exists():
                import shutil

                shutil.rmtree(synthetic_root)


# =============================================================================
# add — happy path
# =============================================================================


class TestAddHappyPath:
    def test_merges_valid_fragment_under_aspect_key(self, tmp_path, monkeypatch):
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        _init_bundle(plan_id)
        fragment_path = _write_fragment(tmp_path, 'aspect-a.toon', _valid_fragment_body('request-result-alignment'))

        # add no longer accepts --mode; it reads the mode from the bundle.
        result = run_script(
            SCRIPT_PATH,
            'add',
            '--plan-id',
            plan_id,
            '--aspect',
            'request-result-alignment',
            '--fragment-file',
            str(fragment_path),
        )

        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        assert data['operation'] == 'add'
        assert data['aspect'] == 'request-result-alignment'
        # overwrote is false on first insertion (TOON serializes bool as false).
        assert data['overwrote'] is False or str(data['overwrote']).lower() == 'false'
        # Bundle file now contains the aspect section.
        bundle_path = plan_dir / 'work' / 'retro-fragments.toon'
        content = bundle_path.read_text(encoding='utf-8')
        assert 'request-result-alignment:' in content
        assert 'status: success' in content


# =============================================================================
# add — fault paths
# =============================================================================


class TestAddFaultPaths:
    def test_rejects_malformed_toon_fragment(self, tmp_path, monkeypatch):
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        _init_bundle(plan_id)
        # An empty fragment file is explicitly flagged as malformed by
        # _read_fragment (empty content raises ValueError).
        fragment_path = _write_fragment(tmp_path, 'empty.toon', '')

        result = run_script(
            SCRIPT_PATH,
            'add',
            '--plan-id',
            plan_id,
            '--aspect',
            'request-result-alignment',
            '--fragment-file',
            str(fragment_path),
        )

        # script exits non-zero via @safe_main when ValueError raises.
        assert not result.success
        assert (
            'empty' in (result.stderr + result.stdout).lower() or 'fragment' in (result.stderr + result.stdout).lower()
        )

    def test_rejects_duplicate_aspect_without_overwrite(self, tmp_path, monkeypatch):
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        _init_bundle(plan_id)
        fragment_path = _write_fragment(tmp_path, 'aspect.toon', _valid_fragment_body('request-result-alignment'))
        _add_aspect(plan_id, 'request-result-alignment', fragment_path)

        # second add for the same aspect without --overwrite.
        result = run_script(
            SCRIPT_PATH,
            'add',
            '--plan-id',
            plan_id,
            '--aspect',
            'request-result-alignment',
            '--fragment-file',
            str(fragment_path),
        )

        # cmd_add returns a structured error payload with status=error.
        # The process still exits 0 because the status is reported via output_toon.
        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'error'
        assert data['operation'] == 'add'
        assert data['aspect'] == 'request-result-alignment'
        assert 'already registered' in data['error']
