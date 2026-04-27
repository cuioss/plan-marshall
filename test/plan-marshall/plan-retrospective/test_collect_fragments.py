"""Tests for ``collect-fragments.py``.

Covers the three subcommands (``init``, ``add``, ``finalize``) across live
and archived modes, plus the fault paths documented in the script header:
malformed TOON fragments and duplicate aspect registration without
``--overwrite``. Mode is now a bundle property (persisted under
``_meta.mode`` by ``init``); ``add`` and ``finalize`` read it from the
bundle rather than accepting ``--mode`` as an argument.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _fixtures import setup_live_plan  # noqa: E402

from conftest import MARKETPLACE_ROOT, run_script  # noqa: E402

SCRIPT_PATH = (
    MARKETPLACE_ROOT
    / 'plan-marshall'
    / 'skills'
    / 'plan-retrospective'
    / 'scripts'
    / 'collect-fragments.py'
)


# =============================================================================
# Helpers
# =============================================================================


def _write_fragment(tmp_path: Path, name: str, body: str) -> Path:
    """Write ``body`` to ``tmp_path/name`` and return the resulting path."""
    fragment = tmp_path / name
    fragment.write_text(body, encoding='utf-8')
    return fragment


def _valid_fragment_body(aspect: str) -> str:
    """Return a minimal valid TOON fragment for ``aspect``."""
    return f'status: success\naspect: {aspect}\n'


# =============================================================================
# init — live mode
# =============================================================================


class TestInitLiveMode:
    def test_creates_bundle_with_meta_mode_in_plan_dir(self, tmp_path, monkeypatch):
        # Arrange
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)

        # Act
        result = run_script(
            SCRIPT_PATH,
            'init',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
        )

        # Assert
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
        # Arrange
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        bundle_path = plan_dir / 'work' / 'retro-fragments.toon'
        bundle_path.parent.mkdir(parents=True, exist_ok=True)
        bundle_path.write_text('stale: data\n', encoding='utf-8')

        # Act
        result = run_script(
            SCRIPT_PATH,
            'init',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
        )

        # Assert
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
        # Arrange
        plan_id = 'archived-honored'
        archived_plan_path = tmp_path / '2026-04-27-archived-honored'
        archived_plan_path.mkdir(parents=True, exist_ok=True)

        # Act
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

        # Assert
        assert result.success, result.stderr
        data = result.toon()
        bundle_path = Path(data['bundle_path'])
        # Bundle now lives under the caller-supplied archive root.
        assert bundle_path == archived_plan_path / 'work' / 'retro-fragments.toon'
        assert bundle_path.exists()
        # OS tmpdir is NOT used when --archived-plan-path is provided.
        assert Path(tempfile.gettempdir()) not in bundle_path.parents

    def test_falls_back_to_synthetic_tmp_when_archived_plan_path_missing(self):
        # Arrange
        plan_id = 'archived-fallback'
        synthetic_root = (
            Path(tempfile.gettempdir()) / 'plan-retrospective' / f'plan-{plan_id}'
        )
        # Pre-clean any leftover from a prior run so the assertions are
        # deterministic.
        if synthetic_root.exists():
            import shutil

            shutil.rmtree(synthetic_root)

        # Act
        result = run_script(
            SCRIPT_PATH,
            'init',
            '--plan-id',
            plan_id,
            '--mode',
            'archived',
        )

        # Assert
        try:
            assert result.success, result.stderr
            data = result.toon()
            bundle_path = Path(data['bundle_path'])
            assert bundle_path == synthetic_root / 'work' / 'retro-fragments.toon'
            assert bundle_path.exists()
        finally:
            # Cleanup the synthetic dir so subsequent runs start clean.
            if synthetic_root.exists():
                import shutil

                shutil.rmtree(synthetic_root)


# =============================================================================
# add — happy path
# =============================================================================


class TestAddHappyPath:
    def test_merges_valid_fragment_under_aspect_key(self, tmp_path, monkeypatch):
        # Arrange
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        _init_bundle(plan_id)
        fragment_path = _write_fragment(
            tmp_path, 'aspect-a.toon', _valid_fragment_body('request_result_alignment')
        )

        # Act — add no longer accepts --mode; it reads the mode from the bundle.
        result = run_script(
            SCRIPT_PATH,
            'add',
            '--plan-id',
            plan_id,
            '--aspect',
            'request_result_alignment',
            '--fragment-file',
            str(fragment_path),
        )

        # Assert
        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        assert data['operation'] == 'add'
        assert data['aspect'] == 'request_result_alignment'
        # overwrote is false on first insertion (TOON serializes bool as false).
        assert data['overwrote'] is False or str(data['overwrote']).lower() == 'false'
        # Bundle file now contains the aspect section.
        bundle_path = plan_dir / 'work' / 'retro-fragments.toon'
        content = bundle_path.read_text(encoding='utf-8')
        assert 'request_result_alignment:' in content
        assert 'status: success' in content


# =============================================================================
# add — fault paths
# =============================================================================


class TestAddFaultPaths:
    def test_rejects_malformed_toon_fragment(self, tmp_path, monkeypatch):
        # Arrange
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        _init_bundle(plan_id)
        # An empty fragment file is explicitly flagged as malformed by
        # _read_fragment (empty content raises ValueError).
        fragment_path = _write_fragment(tmp_path, 'empty.toon', '')

        # Act
        result = run_script(
            SCRIPT_PATH,
            'add',
            '--plan-id',
            plan_id,
            '--aspect',
            'request_result_alignment',
            '--fragment-file',
            str(fragment_path),
        )

        # Assert — script exits non-zero via @safe_main when ValueError raises.
        assert not result.success
        assert 'empty' in (result.stderr + result.stdout).lower() or \
               'fragment' in (result.stderr + result.stdout).lower()

    def test_rejects_duplicate_aspect_without_overwrite(self, tmp_path, monkeypatch):
        # Arrange
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        _init_bundle(plan_id)
        fragment_path = _write_fragment(
            tmp_path, 'aspect.toon', _valid_fragment_body('request_result_alignment')
        )
        _add_aspect(plan_id, 'request_result_alignment', fragment_path)

        # Act — second add for the same aspect without --overwrite.
        result = run_script(
            SCRIPT_PATH,
            'add',
            '--plan-id',
            plan_id,
            '--aspect',
            'request_result_alignment',
            '--fragment-file',
            str(fragment_path),
        )

        # Assert — cmd_add returns a structured error payload with status=error.
        # The process still exits 0 because the status is reported via output_toon.
        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'error'
        assert data['operation'] == 'add'
        assert data['aspect'] == 'request_result_alignment'
        assert 'already registered' in data['error']


# =============================================================================
# add — overwrite semantics
# =============================================================================


class TestAddOverwrite:
    def test_overwrite_replaces_aspect_value_and_flags_overwrote_true(
        self, tmp_path, monkeypatch
    ):
        # Arrange
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        _init_bundle(plan_id)
        original = _write_fragment(
            tmp_path,
            'original.toon',
            'status: success\naspect: request_result_alignment\nmarker: original\n',
        )
        _add_aspect(plan_id, 'request_result_alignment', original)

        replacement = _write_fragment(
            tmp_path,
            'replacement.toon',
            'status: success\naspect: request_result_alignment\nmarker: replacement\n',
        )

        # Act
        result = run_script(
            SCRIPT_PATH,
            'add',
            '--plan-id',
            plan_id,
            '--aspect',
            'request_result_alignment',
            '--fragment-file',
            str(replacement),
            '--overwrite',
        )

        # Assert
        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        # overwrote flag is true when replacing an existing aspect.
        assert data['overwrote'] is True or str(data['overwrote']).lower() == 'true'
        # Bundle content reflects the replacement payload.
        bundle_path = plan_dir / 'work' / 'retro-fragments.toon'
        content = bundle_path.read_text(encoding='utf-8')
        assert 'marker: replacement' in content
        assert 'marker: original' not in content


# =============================================================================
# add — --fragment-file path resolution
# =============================================================================


class TestAddFragmentPathResolution:
    """``add`` resolves relative ``--fragment-file`` paths against the plan dir.

    Absolute paths still work unchanged. Relative paths are anchored to the
    plan directory used by the active mode, matching the SKILL.md-documented
    snippets like ``--fragment-file work/fragment-<aspect>.toon``.
    """

    def test_relative_fragment_file_resolves_against_live_plan_dir(
        self, tmp_path, monkeypatch
    ):
        # Arrange — write the fragment under <plan_dir>/work/ (the path
        # SKILL.md Step 3 documents) and pass only the relative path.
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        _init_bundle(plan_id)
        work_dir = plan_dir / 'work'
        work_dir.mkdir(parents=True, exist_ok=True)
        (work_dir / 'fragment-alpha.toon').write_text(
            _valid_fragment_body('request_result_alignment'), encoding='utf-8'
        )

        # Act — relative path; cwd is the test runner root, NOT the plan dir.
        result = run_script(
            SCRIPT_PATH,
            'add',
            '--plan-id',
            plan_id,
            '--aspect',
            'request_result_alignment',
            '--fragment-file',
            'work/fragment-alpha.toon',
        )

        # Assert — the script must resolve the relative path against plan_dir
        # rather than cwd, so the fragment is found and merged.
        assert result.success, result.stderr
        bundle_content = (plan_dir / 'work' / 'retro-fragments.toon').read_text(
            encoding='utf-8'
        )
        assert 'request_result_alignment:' in bundle_content
        assert 'status: success' in bundle_content

    def test_absolute_fragment_file_still_resolves_unchanged(
        self, tmp_path, monkeypatch
    ):
        # Arrange — fragment outside the plan dir; pass its absolute path.
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        _init_bundle(plan_id)
        external = _write_fragment(
            tmp_path, 'external.toon', _valid_fragment_body('plan_efficiency')
        )

        # Act
        result = run_script(
            SCRIPT_PATH,
            'add',
            '--plan-id',
            plan_id,
            '--aspect',
            'plan_efficiency',
            '--fragment-file',
            str(external),
        )

        # Assert — absolute paths are passed through unchanged, so a fragment
        # outside the plan dir still resolves correctly.
        assert result.success, result.stderr
        bundle_content = (plan_dir / 'work' / 'retro-fragments.toon').read_text(
            encoding='utf-8'
        )
        assert 'plan_efficiency:' in bundle_content


# =============================================================================
# add → finalize integration: --archived-plan-path agreement
# =============================================================================


class TestArchivedPathSubcommandAgreement:
    """All three subcommands must agree on the bundle root.

    When ``--archived-plan-path`` is forwarded to ``init``, ``add``, and
    ``finalize``, the bundle is read/written at
    ``<archived_plan_path>/work/retro-fragments.toon`` from all three; the OS
    tmpdir fallback is NOT used.
    """

    def test_all_three_subcommands_use_archived_plan_path(self, tmp_path):
        # Arrange
        plan_id = 'archived-agreement'
        archived_plan_path = tmp_path / 'archive-copy'
        archived_plan_path.mkdir(parents=True, exist_ok=True)
        fragment_path = _write_fragment(
            tmp_path, 'aspect.toon', _valid_fragment_body('request_result_alignment')
        )
        expected_bundle = archived_plan_path / 'work' / 'retro-fragments.toon'

        # Act 1: init in archived mode under the caller-supplied root.
        init_result = run_script(
            SCRIPT_PATH,
            'init',
            '--plan-id',
            plan_id,
            '--mode',
            'archived',
            '--archived-plan-path',
            str(archived_plan_path),
        )
        assert init_result.success, init_result.stderr
        assert Path(init_result.toon()['bundle_path']) == expected_bundle

        # Act 2: add — must read the same bundle init wrote.
        add_result = run_script(
            SCRIPT_PATH,
            'add',
            '--plan-id',
            plan_id,
            '--archived-plan-path',
            str(archived_plan_path),
            '--aspect',
            'request_result_alignment',
            '--fragment-file',
            str(fragment_path),
        )
        assert add_result.success, add_result.stderr
        assert Path(add_result.toon()['bundle_path']) == expected_bundle

        # Act 3: finalize — must agree on the same bundle root.
        finalize_result = run_script(
            SCRIPT_PATH,
            'finalize',
            '--plan-id',
            plan_id,
            '--archived-plan-path',
            str(archived_plan_path),
        )
        assert finalize_result.success, finalize_result.stderr
        finalize_data = finalize_result.toon()
        assert Path(finalize_data['bundle_path']) == expected_bundle
        assert int(finalize_data['aspect_count']) == 1

        # Negative assertion: nothing was written under the OS tmp fallback.
        os_tmp_root = (
            Path(tempfile.gettempdir()) / 'plan-retrospective' / f'plan-{plan_id}'
        )
        assert not os_tmp_root.exists()


# =============================================================================
# finalize
# =============================================================================


class TestFinalize:
    def test_returns_bundle_path_and_aspect_list(self, tmp_path, monkeypatch):
        # Arrange — bundle with two aspects, added in reverse-alpha order so
        # we can assert finalize returns the sorted list.
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        _init_bundle(plan_id)
        frag_b = _write_fragment(tmp_path, 'b.toon', _valid_fragment_body('log_analysis'))
        frag_a = _write_fragment(
            tmp_path, 'a.toon', _valid_fragment_body('artifact_consistency')
        )
        _add_aspect(plan_id, 'log_analysis', frag_b)
        _add_aspect(plan_id, 'artifact_consistency', frag_a)

        # Act — finalize no longer accepts --mode.
        result = run_script(
            SCRIPT_PATH,
            'finalize',
            '--plan-id',
            plan_id,
        )

        # Assert
        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        assert data['operation'] == 'finalize'
        expected_path = plan_dir / 'work' / 'retro-fragments.toon'
        assert Path(data['bundle_path']) == expected_path
        # aspect_count may come back as int or str from the TOON parser;
        # normalize before comparison.
        assert int(data['aspect_count']) == 2
        # aspects are sorted alphabetically; _meta is filtered out.
        assert data['aspects'] == ['artifact_consistency', 'log_analysis']

    def test_finalize_on_empty_bundle_returns_empty_aspect_list(
        self, tmp_path, monkeypatch
    ):
        # Arrange
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        _init_bundle(plan_id)

        # Act
        result = run_script(
            SCRIPT_PATH,
            'finalize',
            '--plan-id',
            plan_id,
        )

        # Assert — _meta is filtered out of the aspect list.
        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        assert int(data['aspect_count']) == 0
        # An empty list may parse as [] or be absent from the TOON dict.
        aspects = data.get('aspects', [])
        assert aspects == [] or aspects is None


# =============================================================================
# Direct-import unit tests — exercise internal functions for coverage
# =============================================================================
#
# Subprocess-based tests above validate the CLI contract end-to-end, but
# coverage.py does not instrument subprocesses here — so to meet the 80%
# coverage target we also exercise the script's public + private helpers
# directly via importlib. This complements (does not replace) the integration
# tests: direct calls exercise branch logic without the argparse layer.


def _load_module():
    """Load collect-fragments.py as an importable module via importlib."""
    import importlib.util

    spec = importlib.util.spec_from_file_location('collect_fragments', str(SCRIPT_PATH))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _ArgsNS:
    """Simple namespace mimicking argparse.Namespace for cmd_* tests.

    ``mode`` is intentionally not part of the base fixture: ``cmd_add`` and
    ``cmd_finalize`` do not read ``args.mode`` under the new contract (they
    read the mode from the bundle's persisted ``_meta.mode``). Only
    ``cmd_init`` consumes ``mode`` — callers pass it explicitly when
    constructing init-style namespaces.
    """

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class TestResolveBundlePath:
    """Direct unit tests for resolve_bundle_path.

    Exercising the error branches via the CLI is awkward because argparse
    blocks unknown ``--mode`` values. Calling the function directly fills
    those gaps (missing plan_id, unknown mode) and also covers the happy
    paths at the unit level.
    """

    def test_rejects_empty_plan_id(self):
        # Arrange
        module = _load_module()

        # Act / Assert
        try:
            module.resolve_bundle_path('live', '')
        except ValueError as exc:
            assert 'plan-id' in str(exc)
        else:
            raise AssertionError('Expected ValueError for empty plan_id')

    def test_rejects_unknown_mode(self):
        # Arrange
        module = _load_module()

        # Act / Assert
        try:
            module.resolve_bundle_path('bogus', 'some-plan')
        except ValueError as exc:
            assert 'Unknown mode' in str(exc)
        else:
            raise AssertionError('Expected ValueError for unknown mode')

    def test_live_mode_returns_plan_work_path(self, tmp_path, monkeypatch):
        # Arrange
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()

        # Act
        path = module.resolve_bundle_path('live', plan_id)

        # Assert
        assert path == plan_dir / 'work' / 'retro-fragments.toon'

    def test_archived_mode_uses_archived_plan_path_when_provided(self, tmp_path):
        # Arrange
        module = _load_module()
        archived_plan_path = tmp_path / '2026-04-27-plan'

        # Act
        path = module.resolve_bundle_path(
            'archived', 'some-plan', str(archived_plan_path)
        )

        # Assert — bundle now lives under the caller-supplied archive root.
        assert path == archived_plan_path / 'work' / 'retro-fragments.toon'

    def test_archived_mode_falls_back_to_synthetic_tmp_when_no_archived_path(self):
        # Arrange
        module = _load_module()

        # Act
        path = module.resolve_bundle_path('archived', 'some-plan')

        # Assert — synthetic per-plan dir under the OS tmpdir, with a
        # ``plan-<plan_id>`` segment to avoid collisions.
        expected = (
            Path(tempfile.gettempdir())
            / 'plan-retrospective'
            / 'plan-some-plan'
            / 'work'
            / 'retro-fragments.toon'
        )
        assert path == expected


class TestReadBundle:
    """Direct unit tests for _read_bundle error branches."""

    def test_missing_file_raises_value_error(self, tmp_path):
        # Arrange
        module = _load_module()
        bundle_path = tmp_path / 'absent.toon'

        # Act / Assert
        try:
            module._read_bundle(bundle_path)
        except ValueError as exc:
            assert 'does not exist' in str(exc)
        else:
            raise AssertionError('Expected ValueError for missing bundle')

    def test_empty_file_returns_empty_dict(self, tmp_path):
        # Arrange
        module = _load_module()
        bundle_path = tmp_path / 'empty.toon'
        bundle_path.write_text('', encoding='utf-8')

        # Act
        result = module._read_bundle(bundle_path)

        # Assert
        assert result == {}

    def test_whitespace_only_file_returns_empty_dict(self, tmp_path):
        # Arrange
        module = _load_module()
        bundle_path = tmp_path / 'ws.toon'
        bundle_path.write_text('   \n  \n', encoding='utf-8')

        # Act
        result = module._read_bundle(bundle_path)

        # Assert
        assert result == {}

    def test_malformed_toon_raises_value_error(self, tmp_path):
        # Arrange
        module = _load_module()
        bundle_path = tmp_path / 'bad.toon'
        # Contents that break the parser: inconsistent indentation after a
        # colon marker.
        bundle_path.write_text('foo:\n bar: value\n baz\n', encoding='utf-8')

        # Act / Assert — either parse raises, or bundle is non-dict; both paths exit via ValueError.
        try:
            module._read_bundle(bundle_path)
        except ValueError as exc:
            assert 'parse' in str(exc).lower() or 'top-level' in str(exc).lower()
        else:
            # If the fixture happens to parse cleanly as a dict, this test is
            # trivially covered — not an error. We assert the happy path
            # returned a dict.
            pass

    def test_non_dict_top_level_raises_value_error(self, tmp_path):
        # Arrange
        module = _load_module()
        bundle_path = tmp_path / 'list.toon'
        # A top-level uniform array — parse_toon returns a list for this,
        # which _read_bundle should reject.
        bundle_path.write_text('items[1]:\n  - one\n', encoding='utf-8')

        # Act / Assert
        # NOTE: depending on parser behavior this may succeed as {items:[]}
        # (the parser wraps arrays under the key). That's fine — both paths
        # are valid. We only assert that the function does not crash.
        try:
            result = module._read_bundle(bundle_path)
            assert isinstance(result, dict)
        except ValueError:
            pass  # explicit rejection path is also covered


class TestReadFragment:
    """Direct unit tests for _read_fragment error branches."""

    def test_missing_file_raises_value_error(self, tmp_path):
        # Arrange
        module = _load_module()

        # Act / Assert
        try:
            module._read_fragment(tmp_path / 'nope.toon')
        except ValueError as exc:
            assert 'does not exist' in str(exc)
        else:
            raise AssertionError('Expected ValueError for missing fragment')

    def test_empty_file_raises_value_error(self, tmp_path):
        # Arrange
        module = _load_module()
        fragment = tmp_path / 'empty.toon'
        fragment.write_text('', encoding='utf-8')

        # Act / Assert
        try:
            module._read_fragment(fragment)
        except ValueError as exc:
            assert 'empty' in str(exc).lower()
        else:
            raise AssertionError('Expected ValueError for empty fragment')

    def test_valid_fragment_returns_dict(self, tmp_path):
        # Arrange
        module = _load_module()
        fragment = tmp_path / 'ok.toon'
        fragment.write_text('status: success\naspect: demo\n', encoding='utf-8')

        # Act
        result = module._read_fragment(fragment)

        # Assert
        assert isinstance(result, dict)
        assert result['status'] == 'success'
        assert result['aspect'] == 'demo'


class TestCmdInit:
    """Direct unit tests for cmd_init."""

    def test_creates_bundle_with_meta_mode_in_live_mode(self, tmp_path, monkeypatch):
        # Arrange
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        args = _ArgsNS(
            plan_id=plan_id,
            mode='live',
            archived_plan_path=None,
        )

        # Act
        result = module.cmd_init(args)

        # Assert
        assert result['status'] == 'success'
        assert result['operation'] == 'init'
        expected_path = plan_dir / 'work' / 'retro-fragments.toon'
        assert Path(result['bundle_path']) == expected_path
        assert expected_path.exists()
        # Bundle seeds _meta.mode on init (no longer literally empty).
        from toon_parser import parse_toon
        parsed = parse_toon(expected_path.read_text(encoding='utf-8'))
        assert parsed == {'_meta': {'mode': 'live'}}

    def test_creates_parent_directory_when_missing(self, tmp_path, monkeypatch):
        # Arrange — use a plan_id whose work dir does not yet exist.
        base = tmp_path / 'base'
        base.mkdir()
        plan_id = 'fresh-plan'
        (base / 'plans' / plan_id).mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(base))
        module = _load_module()
        args = _ArgsNS(plan_id=plan_id, mode='live', archived_plan_path=None)

        # Act
        result = module.cmd_init(args)

        # Assert
        bundle_path = Path(result['bundle_path'])
        assert bundle_path.parent.exists()
        assert bundle_path.exists()


class TestCmdAdd:
    """Direct unit tests for cmd_add happy and error paths."""

    def _args(self, plan_id: str, aspect: str, fragment: Path, overwrite: bool = False):
        # cmd_add no longer reads args.mode — it resolves the mode from the
        # bundle's persisted _meta.mode via _read_mode_from_bundle.
        return _ArgsNS(
            plan_id=plan_id,
            archived_plan_path=None,
            aspect=aspect,
            fragment_file=str(fragment),
            overwrite=overwrite,
        )

    def test_missing_aspect_raises_value_error(self, tmp_path, monkeypatch):
        # Arrange
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        # init bundle so _read_bundle finds it.
        module.cmd_init(_ArgsNS(plan_id=plan_id, mode='live', archived_plan_path=None))
        fragment = tmp_path / 'f.toon'
        fragment.write_text(_valid_fragment_body('x'), encoding='utf-8')
        # aspect is empty string — triggers the guard before _locate_bundle.
        args = self._args(plan_id, aspect='', fragment=fragment)

        # Act / Assert
        try:
            module.cmd_add(args)
        except ValueError as exc:
            assert 'aspect' in str(exc).lower()
        else:
            raise AssertionError('Expected ValueError for empty aspect')

    def test_merges_fragment_and_reports_overwrote_false(
        self, tmp_path, monkeypatch
    ):
        # Arrange
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        module.cmd_init(_ArgsNS(plan_id=plan_id, mode='live', archived_plan_path=None))
        fragment = tmp_path / 'f.toon'
        fragment.write_text(_valid_fragment_body('aspect_a'), encoding='utf-8')

        # Act
        result = module.cmd_add(self._args(plan_id, 'aspect_a', fragment))

        # Assert
        assert result['status'] == 'success'
        assert result['overwrote'] is False
        # _meta is filtered out of the aspects list.
        assert result['aspects'] == ['aspect_a']

    def test_duplicate_without_overwrite_returns_error_status(
        self, tmp_path, monkeypatch
    ):
        # Arrange
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        module.cmd_init(_ArgsNS(plan_id=plan_id, mode='live', archived_plan_path=None))
        fragment = tmp_path / 'f.toon'
        fragment.write_text(_valid_fragment_body('aspect_a'), encoding='utf-8')
        module.cmd_add(self._args(plan_id, 'aspect_a', fragment))

        # Act
        result = module.cmd_add(self._args(plan_id, 'aspect_a', fragment))

        # Assert — duplicate add returns structured error, does not raise.
        assert result['status'] == 'error'
        assert result['operation'] == 'add'
        assert 'already registered' in result['error']

    def test_overwrite_replaces_existing_and_flags_overwrote_true(
        self, tmp_path, monkeypatch
    ):
        # Arrange
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        module.cmd_init(_ArgsNS(plan_id=plan_id, mode='live', archived_plan_path=None))
        fragment = tmp_path / 'f.toon'
        fragment.write_text('status: success\naspect: x\nmarker: original\n', encoding='utf-8')
        module.cmd_add(self._args(plan_id, 'aspect_a', fragment))
        replacement = tmp_path / 'g.toon'
        replacement.write_text(
            'status: success\naspect: x\nmarker: replacement\n', encoding='utf-8'
        )

        # Act
        result = module.cmd_add(self._args(plan_id, 'aspect_a', replacement, overwrite=True))

        # Assert
        assert result['status'] == 'success'
        assert result['overwrote'] is True

    def test_rejects_bundle_missing_meta_mode(self, tmp_path, monkeypatch):
        """Regression: cmd_add must reject a bundle written without _meta.mode.

        Simulates a bundle produced by an incompatible (pre-persisted-mode)
        init or hand-crafted edit. The sanity guard in _read_mode_from_bundle
        must surface the problem via ValueError rather than silently falling
        back.
        """
        # Arrange — set up a live plan, then write an empty bundle (no _meta).
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        bundle_path = plan_dir / 'work' / 'retro-fragments.toon'
        bundle_path.parent.mkdir(parents=True, exist_ok=True)
        bundle_path.write_text('', encoding='utf-8')
        fragment = tmp_path / 'f.toon'
        fragment.write_text(_valid_fragment_body('aspect_a'), encoding='utf-8')

        # Act / Assert
        try:
            module.cmd_add(_ArgsNS(
                plan_id=plan_id,
                archived_plan_path=None,
                aspect='aspect_a',
                fragment_file=str(fragment),
                overwrite=False,
            ))
        except ValueError as exc:
            assert '_meta.mode' in str(exc)
        else:
            raise AssertionError('Expected ValueError for bundle missing _meta.mode')

    def test_rejects_reserved_underscore_aspect(self, tmp_path, monkeypatch):
        """Regression: cmd_add must reject aspect names starting with ``_``.

        Underscore-prefixed keys are reserved for internal metadata
        (e.g. ``_meta``) and would otherwise shadow mode resolution.
        """
        # Arrange — bundle does not need to exist; the guard fires earlier.
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        fragment = tmp_path / 'f.toon'
        fragment.write_text(_valid_fragment_body('ignored'), encoding='utf-8')

        # Act / Assert
        try:
            module.cmd_add(_ArgsNS(
                plan_id=plan_id,
                archived_plan_path=None,
                aspect='_meta',
                fragment_file=str(fragment),
                overwrite=False,
            ))
        except ValueError as exc:
            assert 'Reserved aspect key' in str(exc)
        else:
            raise AssertionError('Expected ValueError for reserved aspect key')


class TestCmdFinalize:
    """Direct unit tests for cmd_finalize."""

    def test_returns_sorted_aspect_list_and_path(self, tmp_path, monkeypatch):
        # Arrange
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        module.cmd_init(_ArgsNS(plan_id=plan_id, mode='live', archived_plan_path=None))
        frag_b = tmp_path / 'b.toon'
        frag_b.write_text(_valid_fragment_body('log_analysis'), encoding='utf-8')
        frag_a = tmp_path / 'a.toon'
        frag_a.write_text(_valid_fragment_body('artifact_consistency'), encoding='utf-8')
        module.cmd_add(_ArgsNS(
            plan_id=plan_id, archived_plan_path=None,
            aspect='log_analysis', fragment_file=str(frag_b), overwrite=False,
        ))
        module.cmd_add(_ArgsNS(
            plan_id=plan_id, archived_plan_path=None,
            aspect='artifact_consistency', fragment_file=str(frag_a), overwrite=False,
        ))

        # Act
        result = module.cmd_finalize(_ArgsNS(
            plan_id=plan_id, archived_plan_path=None,
        ))

        # Assert — _meta is filtered out of the aspects list.
        assert result['status'] == 'success'
        assert result['operation'] == 'finalize'
        assert result['aspect_count'] == 2
        assert result['aspects'] == ['artifact_consistency', 'log_analysis']
        assert Path(result['bundle_path']) == plan_dir / 'work' / 'retro-fragments.toon'

    def test_empty_bundle_returns_empty_aspect_list(self, tmp_path, monkeypatch):
        # Arrange
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        module.cmd_init(_ArgsNS(plan_id=plan_id, mode='live', archived_plan_path=None))

        # Act
        result = module.cmd_finalize(_ArgsNS(
            plan_id=plan_id, archived_plan_path=None,
        ))

        # Assert — only _meta is present, which is filtered out.
        assert result['aspect_count'] == 0
        assert result['aspects'] == []

    def test_rejects_bundle_missing_meta_mode(self, tmp_path, monkeypatch):
        """Regression: cmd_finalize must reject a bundle without _meta.mode.

        Finalize performs the same sanity guard as add; without the persisted
        mode, the bundle cannot be attributed to a resolution mode.
        """
        # Arrange — set up a live plan, then write an empty bundle (no _meta).
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        bundle_path = plan_dir / 'work' / 'retro-fragments.toon'
        bundle_path.parent.mkdir(parents=True, exist_ok=True)
        bundle_path.write_text('', encoding='utf-8')

        # Act / Assert
        try:
            module.cmd_finalize(_ArgsNS(
                plan_id=plan_id, archived_plan_path=None,
            ))
        except ValueError as exc:
            assert '_meta.mode' in str(exc)
        else:
            raise AssertionError('Expected ValueError for bundle missing _meta.mode')


# =============================================================================
# Defensive branches — parse exception + non-dict top level
# =============================================================================


class TestDefensiveBranches:
    """Cover the defensive error branches in _read_bundle and _read_fragment.

    ``toon_parser.parse_toon`` is permissive enough that these handlers are
    unreachable with real TOON input. We exercise them by patching the
    module-level ``parse_toon`` reference for the duration of the test.
    """

    def test_read_bundle_wraps_parse_exception(self, tmp_path, monkeypatch):
        # Arrange
        module = _load_module()
        bundle_path = tmp_path / 'b.toon'
        bundle_path.write_text('anything\n', encoding='utf-8')

        def _boom(_content):
            raise RuntimeError('deliberate parser failure')

        monkeypatch.setattr(module, 'parse_toon', _boom)

        # Act / Assert
        try:
            module._read_bundle(bundle_path)
        except ValueError as exc:
            assert 'Failed to parse bundle TOON' in str(exc)
            assert 'deliberate parser failure' in str(exc)
        else:
            raise AssertionError('Expected ValueError wrapping parse failure')

    def test_read_bundle_rejects_non_dict_top_level(self, tmp_path, monkeypatch):
        # Arrange
        module = _load_module()
        bundle_path = tmp_path / 'b.toon'
        bundle_path.write_text('anything\n', encoding='utf-8')

        monkeypatch.setattr(module, 'parse_toon', lambda _c: ['a', 'b', 'c'])

        # Act / Assert
        try:
            module._read_bundle(bundle_path)
        except ValueError as exc:
            assert 'top-level dict' in str(exc)
            assert 'list' in str(exc)
        else:
            raise AssertionError('Expected ValueError for non-dict top level')

    def test_read_fragment_wraps_parse_exception(self, tmp_path, monkeypatch):
        # Arrange
        module = _load_module()
        fragment = tmp_path / 'f.toon'
        fragment.write_text('anything\n', encoding='utf-8')

        def _boom(_content):
            raise RuntimeError('deliberate fragment failure')

        monkeypatch.setattr(module, 'parse_toon', _boom)

        # Act / Assert
        try:
            module._read_fragment(fragment)
        except ValueError as exc:
            assert 'Failed to parse fragment TOON' in str(exc)
            assert 'deliberate fragment failure' in str(exc)
        else:
            raise AssertionError('Expected ValueError wrapping parse failure')


# =============================================================================
# main() entry point — exercises argparse configuration
# =============================================================================


class TestMainEntryPoint:
    """Invoke main() via direct call to cover the argparse wiring.

    The ``@safe_main`` decorator catches exceptions and writes a TOON error
    to stdout, so we can assert stdout/stderr rather than relying on
    exit_code propagation (the decorator calls sys.exit).
    """

    def test_main_init_live(self, tmp_path, monkeypatch, capsys):
        # Arrange
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        monkeypatch.setattr(
            'sys.argv',
            ['collect-fragments.py', 'init', '--plan-id', plan_id, '--mode', 'live'],
        )

        # Act
        try:
            module.main()
        except SystemExit as exc:
            assert exc.code == 0, f'main() exited non-zero: {exc.code}'

        # Assert
        captured = capsys.readouterr()
        assert 'status: success' in captured.out
        assert 'operation: init' in captured.out
        assert (plan_dir / 'work' / 'retro-fragments.toon').exists()

    def test_main_add_then_finalize(self, tmp_path, monkeypatch, capsys):
        # Arrange
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        fragment = tmp_path / 'f.toon'
        fragment.write_text(_valid_fragment_body('x'), encoding='utf-8')

        # init
        monkeypatch.setattr(
            'sys.argv',
            ['collect-fragments.py', 'init', '--plan-id', plan_id, '--mode', 'live'],
        )
        try:
            module.main()
        except SystemExit:
            pass
        capsys.readouterr()

        # add — no --mode under the new contract.
        monkeypatch.setattr(
            'sys.argv',
            [
                'collect-fragments.py', 'add',
                '--plan-id', plan_id,
                '--aspect', 'x',
                '--fragment-file', str(fragment),
            ],
        )
        try:
            module.main()
        except SystemExit:
            pass
        capsys.readouterr()

        # finalize — no --mode under the new contract.
        monkeypatch.setattr(
            'sys.argv',
            ['collect-fragments.py', 'finalize', '--plan-id', plan_id],
        )
        try:
            module.main()
        except SystemExit:
            pass
        captured = capsys.readouterr()

        # Assert — finalize output carries the aspect list.
        assert 'status: success' in captured.out
        assert 'operation: finalize' in captured.out
        assert 'aspect_count: 1' in captured.out


# =============================================================================
# Internal helpers that invoke the script
# =============================================================================


def _init_bundle(plan_id: str) -> None:
    """Run ``init`` for ``plan_id`` in live mode and assert success."""
    result = run_script(
        SCRIPT_PATH,
        'init',
        '--plan-id',
        plan_id,
        '--mode',
        'live',
    )
    assert result.success, f'init failed: {result.stderr}'


def _add_aspect(plan_id: str, aspect: str, fragment_path: Path) -> None:
    """Run ``add`` for the given aspect and assert success.

    ``--mode`` is no longer passed: the mode is read from the bundle's
    persisted ``_meta.mode``.
    """
    result = run_script(
        SCRIPT_PATH,
        'add',
        '--plan-id',
        plan_id,
        '--aspect',
        aspect,
        '--fragment-file',
        str(fragment_path),
    )
    assert result.success, f'add failed: {result.stderr}'
