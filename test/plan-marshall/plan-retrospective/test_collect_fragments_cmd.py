# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``collect-fragments.py``."""


from __future__ import annotations

from pathlib import Path

from _collect_fragments_fixtures import _ArgsNS, _load_module, _valid_fragment_body
from _plan_retrospective_fixtures import setup_live_plan  # noqa: E402


class TestReadFragment:
    """Direct unit tests for _read_fragment error branches."""

    def test_missing_file_raises_value_error(self, tmp_path):
        module = _load_module()

        try:
            module._read_fragment(tmp_path / 'nope.toon')
        except ValueError as exc:
            assert 'does not exist' in str(exc)
        else:
            raise AssertionError('Expected ValueError for missing fragment')

    def test_empty_file_raises_value_error(self, tmp_path):
        module = _load_module()
        fragment = tmp_path / 'empty.toon'
        fragment.write_text('', encoding='utf-8')

        try:
            module._read_fragment(fragment)
        except ValueError as exc:
            assert 'empty' in str(exc).lower()
        else:
            raise AssertionError('Expected ValueError for empty fragment')

    def test_valid_fragment_returns_dict(self, tmp_path):
        module = _load_module()
        fragment = tmp_path / 'ok.toon'
        fragment.write_text('status: success\naspect: demo\n', encoding='utf-8')

        result = module._read_fragment(fragment)

        assert isinstance(result, dict)
        assert result['status'] == 'success'
        assert result['aspect'] == 'demo'


class TestCmdInit:
    """Direct unit tests for cmd_init."""

    def test_creates_bundle_with_meta_mode_in_live_mode(self, tmp_path, monkeypatch):
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        args = _ArgsNS(
            plan_id=plan_id,
            mode='live',
            archived_plan_path=None,
        )

        result = module.cmd_init(args)

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
        # use a plan_id whose work dir does not yet exist.
        base = tmp_path / 'base'
        base.mkdir()
        plan_id = 'fresh-plan'
        (base / 'plans' / plan_id).mkdir(parents=True)
        monkeypatch.setenv('PLAN_BASE_DIR', str(base))
        module = _load_module()
        args = _ArgsNS(plan_id=plan_id, mode='live', archived_plan_path=None)

        result = module.cmd_init(args)

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
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        # init bundle so _read_bundle finds it.
        module.cmd_init(_ArgsNS(plan_id=plan_id, mode='live', archived_plan_path=None))
        fragment = tmp_path / 'f.toon'
        fragment.write_text(_valid_fragment_body('x'), encoding='utf-8')
        # aspect is empty string — triggers the guard before _locate_bundle.
        args = self._args(plan_id, aspect='', fragment=fragment)

        try:
            module.cmd_add(args)
        except ValueError as exc:
            assert 'aspect' in str(exc).lower()
        else:
            raise AssertionError('Expected ValueError for empty aspect')

    def test_merges_fragment_and_reports_overwrote_false(self, tmp_path, monkeypatch):
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        module.cmd_init(_ArgsNS(plan_id=plan_id, mode='live', archived_plan_path=None))
        fragment = tmp_path / 'f.toon'
        fragment.write_text(_valid_fragment_body('request-result-alignment'), encoding='utf-8')

        result = module.cmd_add(self._args(plan_id, 'request-result-alignment', fragment))

        assert result['status'] == 'success'
        assert result['overwrote'] is False
        # _meta is filtered out of the aspects list.
        assert result['aspects'] == ['request-result-alignment']

    def test_duplicate_without_overwrite_returns_error_status(self, tmp_path, monkeypatch):
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        module.cmd_init(_ArgsNS(plan_id=plan_id, mode='live', archived_plan_path=None))
        fragment = tmp_path / 'f.toon'
        fragment.write_text(_valid_fragment_body('request-result-alignment'), encoding='utf-8')
        module.cmd_add(self._args(plan_id, 'request-result-alignment', fragment))

        result = module.cmd_add(self._args(plan_id, 'request-result-alignment', fragment))

        # duplicate add returns structured error, does not raise.
        assert result['status'] == 'error'
        assert result['operation'] == 'add'
        assert 'already registered' in result['error']

    def test_overwrite_replaces_existing_and_flags_overwrote_true(self, tmp_path, monkeypatch):
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        module.cmd_init(_ArgsNS(plan_id=plan_id, mode='live', archived_plan_path=None))
        fragment = tmp_path / 'f.toon'
        fragment.write_text('status: success\naspect: x\nmarker: original\n', encoding='utf-8')
        module.cmd_add(self._args(plan_id, 'request-result-alignment', fragment))
        replacement = tmp_path / 'g.toon'
        replacement.write_text('status: success\naspect: x\nmarker: replacement\n', encoding='utf-8')

        result = module.cmd_add(self._args(plan_id, 'request-result-alignment', replacement, overwrite=True))

        assert result['status'] == 'success'
        assert result['overwrote'] is True

    def test_rejects_bundle_missing_meta_mode(self, tmp_path, monkeypatch):
        """Regression: cmd_add must reject a bundle written without _meta.mode.

        Simulates a bundle produced by an incompatible (pre-persisted-mode)
        init or hand-crafted edit. The sanity guard in _read_mode_from_bundle
        must surface the problem via ValueError rather than silently falling
        back.
        """
        # set up a live plan, then write an empty bundle (no _meta).
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        bundle_path = plan_dir / 'work' / 'retro-fragments.toon'
        bundle_path.parent.mkdir(parents=True, exist_ok=True)
        bundle_path.write_text('', encoding='utf-8')
        fragment = tmp_path / 'f.toon'
        fragment.write_text(_valid_fragment_body('request-result-alignment'), encoding='utf-8')

        # a REGISTERED aspect key is used so the aspect-key
        # validation guard (which runs first) passes and the _meta.mode
        # rejection path is the one exercised here.
        try:
            module.cmd_add(
                _ArgsNS(
                    plan_id=plan_id,
                    archived_plan_path=None,
                    aspect='request-result-alignment',
                    fragment_file=str(fragment),
                    overwrite=False,
                )
            )
        except ValueError as exc:
            assert '_meta.mode' in str(exc)
        else:
            raise AssertionError('Expected ValueError for bundle missing _meta.mode')

    def test_rejects_reserved_underscore_aspect(self, tmp_path, monkeypatch):
        """Regression: cmd_add must reject aspect names starting with ``_``.

        Underscore-prefixed keys are reserved for internal metadata
        (e.g. ``_meta``) and would otherwise shadow mode resolution.
        """
        # bundle does not need to exist; the guard fires earlier.
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        fragment = tmp_path / 'f.toon'
        fragment.write_text(_valid_fragment_body('ignored'), encoding='utf-8')

        try:
            module.cmd_add(
                _ArgsNS(
                    plan_id=plan_id,
                    archived_plan_path=None,
                    aspect='_meta',
                    fragment_file=str(fragment),
                    overwrite=False,
                )
            )
        except ValueError as exc:
            assert 'Reserved aspect key' in str(exc)
        else:
            raise AssertionError('Expected ValueError for reserved aspect key')

    def test_rejects_unregistered_aspect_returns_error_status(self, tmp_path, monkeypatch):
        """Regression: cmd_add must reject an aspect key outside the registry.

        Direct-import counterpart to
        :meth:`TestAddAspectKeyValidation.test_rejects_unregistered_aspect_key_with_status_error`
        — exercises the registry branch in ``cmd_add`` without the subprocess
        layer so coverage instruments it. The unregistered key returns a
        structured ``status: error`` payload (it does NOT raise) and the bundle
        is left untouched.
        """
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        module.cmd_init(_ArgsNS(plan_id=plan_id, mode='live', archived_plan_path=None))
        fragment = tmp_path / 'f.toon'
        fragment.write_text(_valid_fragment_body('drift'), encoding='utf-8')

        # an unregistered key (underscored variant of a real section).
        result = module.cmd_add(self._args(plan_id, 'request_result_alignment', fragment))

        # structured error, names the offending key and the valid set.
        assert result['status'] == 'error'
        assert result['operation'] == 'add'
        assert result['aspect'] == 'request_result_alignment'
        assert 'Unregistered aspect key' in result['error']
        assert 'valid_aspects' in result
        assert 'request-result-alignment' in result['valid_aspects']

    def test_accepts_registered_static_aspect(self, tmp_path, monkeypatch):
        """A registered static section key (hyphenated) passes the guard."""
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        module.cmd_init(_ArgsNS(plan_id=plan_id, mode='live', archived_plan_path=None))
        fragment = tmp_path / 'f.toon'
        fragment.write_text(_valid_fragment_body('static'), encoding='utf-8')

        result = module.cmd_add(self._args(plan_id, 'lessons-proposal', fragment))

        assert result['status'] == 'success'
        assert result['aspects'] == ['lessons-proposal']


class TestCmdFinalize:
    """Direct unit tests for cmd_finalize."""

    def test_returns_sorted_aspect_list_and_path(self, tmp_path, monkeypatch):
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        module.cmd_init(_ArgsNS(plan_id=plan_id, mode='live', archived_plan_path=None))
        frag_b = tmp_path / 'b.toon'
        frag_b.write_text(_valid_fragment_body('log-analysis'), encoding='utf-8')
        frag_a = tmp_path / 'a.toon'
        frag_a.write_text(_valid_fragment_body('artifact-consistency'), encoding='utf-8')
        module.cmd_add(
            _ArgsNS(
                plan_id=plan_id,
                archived_plan_path=None,
                aspect='log-analysis',
                fragment_file=str(frag_b),
                overwrite=False,
            )
        )
        module.cmd_add(
            _ArgsNS(
                plan_id=plan_id,
                archived_plan_path=None,
                aspect='artifact-consistency',
                fragment_file=str(frag_a),
                overwrite=False,
            )
        )

        result = module.cmd_finalize(
            _ArgsNS(
                plan_id=plan_id,
                archived_plan_path=None,
            )
        )

        # _meta is filtered out of the aspects list.
        assert result['status'] == 'success'
        assert result['operation'] == 'finalize'
        assert result['aspect_count'] == 2
        assert result['aspects'] == ['artifact-consistency', 'log-analysis']
        assert Path(result['bundle_path']) == plan_dir / 'work' / 'retro-fragments.toon'

    def test_empty_bundle_returns_empty_aspect_list(self, tmp_path, monkeypatch):
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        module.cmd_init(_ArgsNS(plan_id=plan_id, mode='live', archived_plan_path=None))

        result = module.cmd_finalize(
            _ArgsNS(
                plan_id=plan_id,
                archived_plan_path=None,
            )
        )

        # only _meta is present, which is filtered out.
        assert result['aspect_count'] == 0
        assert result['aspects'] == []

    def test_rejects_bundle_missing_meta_mode(self, tmp_path, monkeypatch):
        """Regression: cmd_finalize must reject a bundle without _meta.mode.

        Finalize performs the same sanity guard as add; without the persisted
        mode, the bundle cannot be attributed to a resolution mode.
        """
        # set up a live plan, then write an empty bundle (no _meta).
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        bundle_path = plan_dir / 'work' / 'retro-fragments.toon'
        bundle_path.parent.mkdir(parents=True, exist_ok=True)
        bundle_path.write_text('', encoding='utf-8')

        try:
            module.cmd_finalize(
                _ArgsNS(
                    plan_id=plan_id,
                    archived_plan_path=None,
                )
            )
        except ValueError as exc:
            assert '_meta.mode' in str(exc)
        else:
            raise AssertionError('Expected ValueError for bundle missing _meta.mode')
