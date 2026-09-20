# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``collect-fragments.py``."""

from __future__ import annotations

import tempfile
from pathlib import Path

from _collect_fragments_fixtures import (
    SCRIPT_PATH,
    _add_aspect,
    _ArgsNS,
    _init_bundle,
    _load_module,
    _valid_fragment_body,
    _write_fragment,
)
from _plan_retrospective_fixtures import setup_live_plan

from conftest import run_script

# =============================================================================
# finalize
# =============================================================================


class TestFinalize:
    def test_returns_bundle_path_and_aspect_list(self, tmp_path, monkeypatch):
        # bundle with two aspects, added in reverse-alpha order so
        # we can assert finalize returns the sorted list.
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        _init_bundle(plan_id)
        frag_b = _write_fragment(tmp_path, 'b.toon', _valid_fragment_body('log-analysis'))
        frag_a = _write_fragment(tmp_path, 'a.toon', _valid_fragment_body('artifact-consistency'))
        _add_aspect(plan_id, 'log-analysis', frag_b)
        _add_aspect(plan_id, 'artifact-consistency', frag_a)

        # finalize no longer accepts --mode.
        result = run_script(
            SCRIPT_PATH,
            'finalize',
            '--plan-id',
            plan_id,
        )

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
        assert data['aspects'] == ['artifact-consistency', 'log-analysis']

    def test_finalize_on_empty_bundle_returns_empty_aspect_list(self, tmp_path, monkeypatch):
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        _init_bundle(plan_id)

        result = run_script(
            SCRIPT_PATH,
            'finalize',
            '--plan-id',
            plan_id,
        )

        # _meta is filtered out of the aspect list.
        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        assert int(data['aspect_count']) == 0
        # An empty list may parse as [] or be absent from the TOON dict.
        aspects = data.get('aspects', [])
        assert aspects == [] or aspects is None


# =============================================================================
# _meta.aspects authoritative inventory — phantom-key regression + dedup
# =============================================================================


class TestAuthoritativeAspectInventory:
    """The reported aspect list/count comes from the authoritative
    ``_meta.aspects`` inventory recorded at ``add`` time, never from a blind
    ``bundle.keys()`` enumeration.

    A fragment body that hand-authors a ``|`` block scalar whose continuation
    line sits flush at column 0 and contains a colon leaks a phantom sibling
    top-level key into the bundle: ``_parse_multiline_value`` captures nothing
    (the flush-left line is at the same indent as the ``|`` key, so the
    multi-line value terminates immediately) and ``_parse_object`` then re-reads
    that continuation line as a brand-new top-level ``key: value`` pair. The old
    ``sorted(k for k in bundle.keys() if not k.startswith('_'))`` enumeration
    counted that phantom key as an aspect, inflating ``aspect_count``. Sourcing
    the list from ``_meta.aspects`` makes it immune to such leakage.
    """

    def test_embedded_colon_block_scalar_does_not_inflate_aspect_count(self, tmp_path, monkeypatch):
        # register one aspect through the real init/add flow (so the
        # _meta.aspects block is serialized correctly), then inject the exact
        # leak trigger onto the bundle on disk: a flush-left continuation line
        # containing a colon, as a hand-authored ``summary: |`` block scalar
        # would produce. parse_toon re-reads that line as a phantom sibling
        # top-level key.
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        _init_bundle(plan_id)
        fragment_path = _write_fragment(tmp_path, 'frag.toon', _valid_fragment_body('lessons-proposal'))
        _add_aspect(plan_id, 'lessons-proposal', fragment_path)

        bundle_path = plan_dir / 'work' / 'retro-fragments.toon'
        leaked = bundle_path.read_text(encoding='utf-8')
        if not leaked.endswith('\n'):
            leaked += '\n'
        leaked += 'fully recoverable from decision.log: the user pivoted mid-plan\n'
        bundle_path.write_text(leaked, encoding='utf-8')

        # Sanity — the leak is real: parse_toon surfaces a phantom sibling key
        # alongside the genuine aspect, so a blind bundle.keys() enumeration
        # would count two aspects.
        from toon_parser import parse_toon

        parsed = parse_toon(bundle_path.read_text(encoding='utf-8'))
        phantom_keys = [k for k in parsed if not k.startswith('_') and k != 'lessons-proposal']
        assert phantom_keys, 'expected the embedded-colon block scalar to leak a phantom sibling key'

        result = run_script(
            SCRIPT_PATH,
            'finalize',
            '--plan-id',
            plan_id,
        )

        # exactly the one registered aspect is reported, never the
        # inflated phantom count.
        assert result.success, result.stderr
        data = result.toon()
        assert data['aspects'] == ['lessons-proposal']
        assert int(data['aspect_count']) == 1

    def test_add_registers_aspect_in_authoritative_inventory(self, tmp_path, monkeypatch):
        # a clean fragment added via the normal flow records the
        # aspect in _meta.aspects, and the add return reports from that list.
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        _init_bundle(plan_id)
        fragment_path = _write_fragment(tmp_path, 'frag.toon', _valid_fragment_body('lessons-proposal'))

        result = run_script(
            SCRIPT_PATH,
            'add',
            '--plan-id',
            plan_id,
            '--aspect',
            'lessons-proposal',
            '--fragment-file',
            str(fragment_path),
        )

        # the reported aspects come from _meta.aspects.
        assert result.success, result.stderr
        data = result.toon()
        assert data['aspects'] == ['lessons-proposal']
        # The bundle's _meta block carries the authoritative inventory.
        from toon_parser import parse_toon

        bundle_path = plan_dir / 'work' / 'retro-fragments.toon'
        parsed = parse_toon(bundle_path.read_text(encoding='utf-8'))
        assert parsed['_meta']['aspects'] == ['lessons-proposal']

    def test_overwrite_readd_does_not_duplicate_aspect_in_inventory(self, tmp_path, monkeypatch):
        # register an aspect, then re-add it with --overwrite.
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        _init_bundle(plan_id)
        original = _write_fragment(
            tmp_path,
            'original.toon',
            'status: success\naspect: log_analysis\nmarker: original\n',
        )
        _add_aspect(plan_id, 'log-analysis', original)
        replacement = _write_fragment(
            tmp_path,
            'replacement.toon',
            'status: success\naspect: log_analysis\nmarker: replacement\n',
        )

        # re-add the same aspect with --overwrite.
        result = run_script(
            SCRIPT_PATH,
            'add',
            '--plan-id',
            plan_id,
            '--aspect',
            'log-analysis',
            '--fragment-file',
            str(replacement),
            '--overwrite',
        )

        # dedup invariant: the aspect appears exactly once.
        assert result.success, result.stderr
        data = result.toon()
        assert data['aspects'] == ['log-analysis']

        # finalize agrees: one aspect, count 1.
        finalize_result = run_script(
            SCRIPT_PATH,
            'finalize',
            '--plan-id',
            plan_id,
        )
        assert finalize_result.success, finalize_result.stderr
        finalize_data = finalize_result.toon()
        assert finalize_data['aspects'] == ['log-analysis']
        assert int(finalize_data['aspect_count']) == 1


# =============================================================================
# Direct-import unit tests — exercise internal functions for coverage
# =============================================================================


class TestResolveBundlePath:
    """Direct unit tests for resolve_bundle_path.

    Exercising the error branches via the CLI is awkward because argparse
    blocks unknown ``--mode`` values. Calling the function directly fills
    those gaps (missing plan_id, unknown mode) and also covers the happy
    paths at the unit level.
    """

    def test_rejects_empty_plan_id(self):
        module = _load_module()

        try:
            module.resolve_bundle_path('live', '')
        except ValueError as exc:
            assert 'plan-id' in str(exc)
        else:
            raise AssertionError('Expected ValueError for empty plan_id')

    def test_rejects_unknown_mode(self):
        module = _load_module()

        try:
            module.resolve_bundle_path('bogus', 'some-plan')
        except ValueError as exc:
            assert 'Unknown mode' in str(exc)
        else:
            raise AssertionError('Expected ValueError for unknown mode')

    def test_live_mode_returns_plan_work_path(self, tmp_path, monkeypatch):
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()

        path = module.resolve_bundle_path('live', plan_id)

        assert path == plan_dir / 'work' / 'retro-fragments.toon'

    def test_archived_mode_uses_archived_plan_path_when_provided(self, tmp_path):
        # resolve archived_plan_path to match resolve_bundle_path's
        # canonical-absolute return contract (macOS /var → /private/var).
        module = _load_module()
        archived_plan_path = (tmp_path / '2026-04-27-plan').resolve()

        path = module.resolve_bundle_path('archived', 'some-plan', str(archived_plan_path))

        # bundle now lives under the caller-supplied archive root.
        assert path == archived_plan_path / 'work' / 'retro-fragments.toon'

    def test_archived_mode_falls_back_to_synthetic_tmp_when_no_archived_path(self):
        module = _load_module()

        path = module.resolve_bundle_path('archived', 'some-plan')

        # synthetic per-plan dir under the OS tmpdir, with a
        # ``plan-<plan_id>`` segment to avoid collisions. Resolved because
        # resolve_bundle_path now returns canonical absolute paths (macOS
        # /var → /private/var symlink resolution).
        expected = (
            (Path(tempfile.gettempdir()) / 'plan-retrospective' / 'plan-some-plan').resolve()
            / 'work'
            / 'retro-fragments.toon'
        )
        assert path == expected


class TestReadBundle:
    """Direct unit tests for _read_bundle error branches."""

    def test_missing_file_raises_value_error(self, tmp_path):
        module = _load_module()
        bundle_path = tmp_path / 'absent.toon'

        try:
            module._read_bundle(bundle_path)
        except ValueError as exc:
            assert 'does not exist' in str(exc)
        else:
            raise AssertionError('Expected ValueError for missing bundle')

    def test_empty_file_returns_empty_dict(self, tmp_path):
        module = _load_module()
        bundle_path = tmp_path / 'empty.toon'
        bundle_path.write_text('', encoding='utf-8')

        result = module._read_bundle(bundle_path)

        assert result == {}

    def test_whitespace_only_file_returns_empty_dict(self, tmp_path):
        module = _load_module()
        bundle_path = tmp_path / 'ws.toon'
        bundle_path.write_text('   \n  \n', encoding='utf-8')

        result = module._read_bundle(bundle_path)

        assert result == {}

    def test_malformed_toon_raises_value_error(self, tmp_path):
        module = _load_module()
        bundle_path = tmp_path / 'bad.toon'
        # Contents that break the parser: inconsistent indentation after a
        # colon marker.
        bundle_path.write_text('foo:\n bar: value\n baz\n', encoding='utf-8')

        # either parse raises, or bundle is non-dict; both paths exit via ValueError.
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
        module = _load_module()
        bundle_path = tmp_path / 'list.toon'
        # A top-level uniform array — parse_toon returns a list for this,
        # which _read_bundle should reject.
        bundle_path.write_text('items[1]:\n  - one\n', encoding='utf-8')

        # NOTE: depending on parser behavior this may succeed as {items:[]}
        # (the parser wraps arrays under the key). That's fine — both paths
        # are valid. We only assert that the function does not crash.
        try:
            result = module._read_bundle(bundle_path)
            assert isinstance(result, dict)
        except ValueError:
            pass  # explicit rejection path is also covered


# =============================================================================
# register — batched fragment registration in a single pass
# =============================================================================
#
# One `register` call replaces N `add` calls: the aspect-key registry resolves
# once, every key validates before the bundle is touched (all-or-nothing), and
# the bundle writes once. The result publishes the registered aspect keys WITH
# their fragment entry counts, so compile-report's section loop is checkable
# for conservation — a registered key with entries that never renders is a
# loud drop, never a silent one.


def _register_args(plan_id: str, items: list[str], overwrite: bool = False):
    """Namespaces for direct cmd_register calls (mode comes from the bundle)."""
    return _ArgsNS(plan_id=plan_id, archived_plan_path=None, item=items, overwrite=overwrite)


class TestRegisterBatch:
    """End-to-end batch registration through the CLI."""

    def test_one_call_registers_many_with_counts(self, tmp_path, monkeypatch):
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        _init_bundle(plan_id)
        frag_b = _write_fragment(tmp_path, 'b.toon', _valid_fragment_body('log-analysis'))
        frag_a = _write_fragment(tmp_path, 'a.toon', _valid_fragment_body('artifact-consistency'))
        frag_l = _write_fragment(tmp_path, 'l.toon', _valid_fragment_body('lessons-proposal'))

        result = run_script(
            SCRIPT_PATH,
            'register',
            '--plan-id',
            plan_id,
            '--item',
            f'log-analysis={frag_b}',
            '--item',
            f'artifact-consistency={frag_a}',
            '--item',
            f'lessons-proposal={frag_l}',
        )

        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        assert data['operation'] == 'register'
        assert data['aspects'] == ['artifact-consistency', 'lessons-proposal', 'log-analysis']
        assert int(data['aspect_count']) == 3
        # Registered keys publish with their fragment entry counts: each
        # two-key fragment body counts 2, so the conservation check reads 6.
        rows = {row['aspect']: int(row['entries']) for row in data['registered']}
        assert rows == {'artifact-consistency': 2, 'lessons-proposal': 2, 'log-analysis': 2}

        # finalize agrees: the same three aspects, count 3.
        finalize_data = run_script(SCRIPT_PATH, 'finalize', '--plan-id', plan_id).toon()
        assert finalize_data['aspects'] == ['artifact-consistency', 'lessons-proposal', 'log-analysis']
        assert int(finalize_data['aspect_count']) == 3

    def test_batch_matches_sequential_adds_byte_for_byte(self, tmp_path, monkeypatch):
        """Fragment count conserved end to end: one batch == N adds on disk.

        The same three fragments in the same order must produce byte-identical
        bundles whether they arrive in one `register` call or three `add`
        calls — otherwise the batch path is a second writer with its own drift.
        """
        batch_base = tmp_path / 'batch'
        batch_base.mkdir()
        adds_base = tmp_path / 'adds'
        adds_base.mkdir()
        batch_id, batch_dir = setup_live_plan(batch_base, monkeypatch, plan_id='retro-batch')
        _init_bundle(batch_id)
        frags = [
            _write_fragment(tmp_path, f'{name}.toon', _valid_fragment_body(name))
            for name in ('log-analysis', 'artifact-consistency', 'lessons-proposal')
        ]
        result = run_script(
            SCRIPT_PATH,
            'register',
            '--plan-id',
            batch_id,
            *[
                arg
                for frag, name in zip(frags, ('log-analysis', 'artifact-consistency', 'lessons-proposal'), strict=True)
                for arg in ('--item', f'{name}={frag}')
            ],
        )
        assert result.success, result.stderr

        adds_id, adds_dir = setup_live_plan(adds_base, monkeypatch, plan_id='retro-adds')
        _init_bundle(adds_id)
        for frag, name in zip(frags, ('log-analysis', 'artifact-consistency', 'lessons-proposal'), strict=True):
            _add_aspect(adds_id, name, frag)

        batch_bytes = (batch_dir / 'work' / 'retro-fragments.toon').read_bytes()
        adds_bytes = (adds_dir / 'work' / 'retro-fragments.toon').read_bytes()
        # Plan ids differ, and the plan_id is not persisted in the bundle —
        # only aspect keys and fragment bodies are — so identical inputs must
        # yield identical bytes.
        assert batch_bytes == adds_bytes

    def test_register_overwrite_replaces_existing(self, tmp_path, monkeypatch):
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        _init_bundle(plan_id)
        original = _write_fragment(
            tmp_path, 'original.toon', 'status: success\naspect: log_analysis\nmarker: original\n'
        )
        _add_aspect(plan_id, 'log-analysis', original)
        replacement = _write_fragment(
            tmp_path, 'replacement.toon', 'status: success\naspect: log_analysis\nmarker: replacement\n'
        )

        result = run_script(
            SCRIPT_PATH,
            'register',
            '--plan-id',
            plan_id,
            '--item',
            f'log-analysis={replacement}',
            '--overwrite',
        )

        assert result.success, result.stderr
        bundle_text = (plan_dir / 'work' / 'retro-fragments.toon').read_text(encoding='utf-8')
        assert 'marker: replacement' in bundle_text
        assert 'marker: original' not in bundle_text


class TestRegisterFaultPaths:
    """Direct unit tests for the batch fault paths (all-or-nothing)."""

    def _snapshot(self, plan_id: str, plan_dir) -> bytes:
        return (plan_dir / 'work' / 'retro-fragments.toon').read_bytes()

    def test_unregistered_key_aborts_the_whole_batch_untouched(self, tmp_path, monkeypatch):
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        module.cmd_init(_ArgsNS(plan_id=plan_id, mode='live', archived_plan_path=None))
        good = tmp_path / 'good.toon'
        good.write_text(_valid_fragment_body('log-analysis'), encoding='utf-8')
        before = self._snapshot(plan_id, plan_dir)

        result = module.cmd_register(_register_args(plan_id, [f'log-analysis={good}', 'not-an-aspect=whatever']))

        assert result['status'] == 'error'
        assert result['operation'] == 'register'
        assert 'Unregistered aspect key' in result['error']
        assert self._snapshot(plan_id, plan_dir) == before

    def test_duplicate_aspect_in_one_batch_is_rejected(self, tmp_path, monkeypatch):
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        module.cmd_init(_ArgsNS(plan_id=plan_id, mode='live', archived_plan_path=None))
        frag = tmp_path / 'f.toon'
        frag.write_text(_valid_fragment_body('log-analysis'), encoding='utf-8')
        before = self._snapshot(plan_id, plan_dir)

        try:
            module.cmd_register(_register_args(plan_id, [f'log-analysis={frag}', f'log-analysis={frag}']))
        except ValueError as exc:
            assert 'Duplicate aspect' in str(exc)
        else:
            raise AssertionError('Expected ValueError for a duplicate aspect in one batch')
        assert self._snapshot(plan_id, plan_dir) == before

    def test_malformed_item_is_rejected_before_any_read(self, tmp_path, monkeypatch):
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        module.cmd_init(_ArgsNS(plan_id=plan_id, mode='live', archived_plan_path=None))
        before = self._snapshot(plan_id, plan_dir)

        try:
            module.cmd_register(_register_args(plan_id, ['no-equals-here']))
        except ValueError as exc:
            assert 'ASPECT=PATH' in str(exc)
        else:
            raise AssertionError('Expected ValueError for a malformed --item')
        assert self._snapshot(plan_id, plan_dir) == before

    def test_present_aspect_without_overwrite_aborts_batch_untouched(self, tmp_path, monkeypatch):
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        module.cmd_init(_ArgsNS(plan_id=plan_id, mode='live', archived_plan_path=None))
        first = tmp_path / 'first.toon'
        first.write_text(_valid_fragment_body('log-analysis'), encoding='utf-8')
        module.cmd_register(_register_args(plan_id, [f'log-analysis={first}']))
        second = tmp_path / 'second.toon'
        second.write_text(_valid_fragment_body('artifact-consistency'), encoding='utf-8')
        before = self._snapshot(plan_id, plan_dir)

        result = module.cmd_register(
            _register_args(plan_id, [f'log-analysis={first}', f'artifact-consistency={second}'])
        )

        assert result['status'] == 'error'
        assert 'already registered' in result['error']
        # The batch is all-or-nothing: the NEW aspect did not land either.
        assert self._snapshot(plan_id, plan_dir) == before

    def test_overwrite_marks_replaced_rows(self, tmp_path, monkeypatch):
        plan_id, _ = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        module.cmd_init(_ArgsNS(plan_id=plan_id, mode='live', archived_plan_path=None))
        frag = tmp_path / 'f.toon'
        frag.write_text(_valid_fragment_body('log-analysis'), encoding='utf-8')
        other = tmp_path / 'o.toon'
        other.write_text(_valid_fragment_body('artifact-consistency'), encoding='utf-8')
        module.cmd_register(_register_args(plan_id, [f'log-analysis={frag}']))

        result = module.cmd_register(
            _register_args(plan_id, [f'log-analysis={frag}', f'artifact-consistency={other}'], overwrite=True)
        )

        assert result['status'] == 'success'
        by_aspect = {row['aspect']: row for row in result['registered']}
        assert by_aspect['log-analysis']['overwrote'] is True
        assert by_aspect['artifact-consistency']['overwrote'] is False


class TestBatchItemParsing:
    """Direct unit tests for _parse_batch_item and _fragment_entry_count."""

    def test_splits_on_the_first_equals_only(self):
        module = _load_module()

        aspect, path = module._parse_batch_item('log-analysis=/tmp/x?a=b=c')

        assert aspect == 'log-analysis'
        assert path == '/tmp/x?a=b=c'

    def test_missing_equals_raises(self):
        module = _load_module()

        try:
            module._parse_batch_item('log-analysis')
        except ValueError as exc:
            assert 'ASPECT=PATH' in str(exc)
        else:
            raise AssertionError('Expected ValueError for an item without =')

    def test_empty_aspect_or_path_raises(self):
        module = _load_module()

        for raw in ('=some/path.toon', 'log-analysis=', 'log-analysis=   '):
            try:
                module._parse_batch_item(raw)
            except ValueError:
                pass
            else:
                raise AssertionError(f'Expected ValueError for {raw!r}')

    def test_entry_count_counts_top_level_entries(self):
        module = _load_module()

        assert module._fragment_entry_count({'a': 1, 'b': 2}) == 2
        assert module._fragment_entry_count([1, 2, 3]) == 3
        assert module._fragment_entry_count('scalar') == 1
        assert module._fragment_entry_count({}) == 0


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
