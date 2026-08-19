# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``collect-fragments.py``.

Covers the three subcommands (``init``, ``add``, ``finalize``) across live
and archived modes, plus the fault paths documented in the script header:
malformed TOON fragments and duplicate aspect registration without
``--overwrite``. Mode is now a bundle property (persisted under
``_meta.mode`` by ``init``); ``add`` and ``finalize`` read it from the
bundle rather than accepting ``--mode`` as an argument.

``cmd_add`` validates ``--aspect`` against the canonical aspect-key registry
(static :data:`retro_sections.SECTION_SPEC` keys ∪ domain-contributed aspects)
before touching the bundle. Every aspect key used across these tests is a
member of that registry — the registered static keys are hyphenated
(``request-result-alignment``, ``log-analysis``, ``artifact-consistency``,
``plan-efficiency``, ``lessons-proposal``, …) to match the consumer's section
map, never the underscored variants that would silently empty a report
section. The validation guard itself is exercised by
:class:`TestAddAspectKeyValidation`.
"""


from __future__ import annotations

from _collect_fragments_fixtures import _load_module, _valid_fragment_body
from _plan_retrospective_fixtures import setup_live_plan  # noqa: E402

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
        module = _load_module()
        bundle_path = tmp_path / 'b.toon'
        bundle_path.write_text('anything\n', encoding='utf-8')

        def _boom(_content):
            raise RuntimeError('deliberate parser failure')

        monkeypatch.setattr(module, 'parse_toon', _boom)

        try:
            module._read_bundle(bundle_path)
        except ValueError as exc:
            assert 'Failed to parse bundle TOON' in str(exc)
            assert 'deliberate parser failure' in str(exc)
        else:
            raise AssertionError('Expected ValueError wrapping parse failure')

    def test_read_bundle_rejects_non_dict_top_level(self, tmp_path, monkeypatch):
        module = _load_module()
        bundle_path = tmp_path / 'b.toon'
        bundle_path.write_text('anything\n', encoding='utf-8')

        monkeypatch.setattr(module, 'parse_toon', lambda _c: ['a', 'b', 'c'])

        try:
            module._read_bundle(bundle_path)
        except ValueError as exc:
            assert 'top-level dict' in str(exc)
            assert 'list' in str(exc)
        else:
            raise AssertionError('Expected ValueError for non-dict top level')

    def test_read_fragment_wraps_parse_exception(self, tmp_path, monkeypatch):
        module = _load_module()
        fragment = tmp_path / 'f.toon'
        fragment.write_text('anything\n', encoding='utf-8')

        def _boom(_content):
            raise RuntimeError('deliberate fragment failure')

        monkeypatch.setattr(module, 'parse_toon', _boom)

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
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        monkeypatch.setattr(
            'sys.argv',
            ['collect-fragments.py', 'init', '--plan-id', plan_id, '--mode', 'live'],
        )

        try:
            module.main()
        except SystemExit as exc:
            assert exc.code == 0, f'main() exited non-zero: {exc.code}'

        captured = capsys.readouterr()
        assert 'status: success' in captured.out
        assert 'operation: init' in captured.out
        assert (plan_dir / 'work' / 'retro-fragments.toon').exists()

    def test_main_add_then_finalize(self, tmp_path, monkeypatch, capsys):
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        fragment = tmp_path / 'f.toon'
        fragment.write_text(_valid_fragment_body('request-result-alignment'), encoding='utf-8')

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

        # add — no --mode under the new contract. A registered aspect key is
        # used so the aspect-key validation guard accepts it.
        monkeypatch.setattr(
            'sys.argv',
            [
                'collect-fragments.py',
                'add',
                '--plan-id',
                plan_id,
                '--aspect',
                'request-result-alignment',
                '--fragment-file',
                str(fragment),
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

        # finalize output carries the aspect list.
        assert 'status: success' in captured.out
        assert 'operation: finalize' in captured.out
        assert 'aspect_count: 1' in captured.out
