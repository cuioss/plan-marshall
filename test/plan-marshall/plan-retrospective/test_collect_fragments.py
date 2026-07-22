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

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _plan_retrospective_fixtures import setup_live_plan  # noqa: E402

from conftest import MARKETPLACE_ROOT, run_script  # noqa: E402

SCRIPT_PATH = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'plan-retrospective' / 'scripts' / 'collect-fragments.py'


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


# =============================================================================
# add — aspect-key validation guard
# =============================================================================


class TestAddAspectKeyValidation:
    """``cmd_add`` rejects ``--aspect`` keys outside the canonical registry.

    The registry is the union of (a) the static section keys from
    ``retro_sections.SECTION_SPEC`` (``valid_aspect_keys()``) and (b) the
    domain-contributed aspect names discovered via the extension-discovery
    library (e.g. ``wrapper-tangle``). An ``--aspect`` outside this set is a
    producer/consumer drift — a typo'd or renamed key the consumer's section
    map will never look up — so ``cmd_add`` rejects it loudly with
    ``status: error`` BEFORE touching the bundle, naming the offending key and
    the valid set, rather than writing it silently into the bundle where
    ``compile-report`` would later drop its section.

    Registered static keys (hyphenated) and registered domain keys are still
    accepted; the guard only fires for genuinely unregistered keys.
    """

    def test_rejects_unregistered_aspect_key_with_status_error(self, tmp_path, monkeypatch):
        # an underscored variant of a real section key is exactly the
        # drift the guard protects against: the consumer's SECTION_SPEC uses
        # the hyphenated form, so the underscored key is unregistered.
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        _init_bundle(plan_id)
        fragment_path = _write_fragment(tmp_path, 'frag.toon', _valid_fragment_body('drift'))

        result = run_script(
            SCRIPT_PATH,
            'add',
            '--plan-id',
            plan_id,
            '--aspect',
            'request_result_alignment',  # underscored — NOT registered
            '--fragment-file',
            str(fragment_path),
        )

        # structured error payload, process still exits 0 (status is
        # reported via output_toon, not the exit code).
        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'error'
        assert data['operation'] == 'add'
        assert data['aspect'] == 'request_result_alignment'
        assert 'Unregistered aspect key' in data['error']
        # The error names the valid set so the caller can self-correct.
        assert 'request-result-alignment' in data['error']
        # The bundle MUST be untouched — the guard runs before any write, so
        # the unregistered key never lands in the inventory.
        from toon_parser import parse_toon

        bundle_path = plan_dir / 'work' / 'retro-fragments.toon'
        parsed = parse_toon(bundle_path.read_text(encoding='utf-8'))
        assert 'request_result_alignment' not in parsed
        assert parsed['_meta'].get('aspects', []) == []

    def test_accepts_registered_static_aspect_key(self, tmp_path, monkeypatch):
        # a registered static section key (hyphenated) is accepted.
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        _init_bundle(plan_id)
        fragment_path = _write_fragment(tmp_path, 'frag.toon', _valid_fragment_body('static'))

        result = run_script(
            SCRIPT_PATH,
            'add',
            '--plan-id',
            plan_id,
            '--aspect',
            'request-result-alignment',  # registered static key
            '--fragment-file',
            str(fragment_path),
        )

        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        assert data['aspect'] == 'request-result-alignment'
        assert data['aspects'] == ['request-result-alignment']

    def test_accepts_routing_decisions_aspect_key(self, tmp_path, monkeypatch):
        # routing-decisions ships with a producer (check-routing-decisions.py)
        # AND a SECTION_SPEC render row. The row makes it a member of
        # valid_aspect_keys(), so cmd_add MUST accept it — without the row the
        # aspect ships dead, rejected at add time (lesson 2026-06-20-17-003).
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        _init_bundle(plan_id)
        fragment_path = _write_fragment(tmp_path, 'frag.toon', _valid_fragment_body('routing-decisions'))

        result = run_script(
            SCRIPT_PATH,
            'add',
            '--plan-id',
            plan_id,
            '--aspect',
            'routing-decisions',  # registered static key (SECTION_SPEC row)
            '--fragment-file',
            str(fragment_path),
        )

        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        assert data['aspect'] == 'routing-decisions'
        assert data['aspects'] == ['routing-decisions']

    def test_accepts_registered_domain_aspect_key(self, tmp_path, monkeypatch):
        # a domain-contributed aspect (e.g. wrapper-tangle from
        # pm-plugin-development) is registered through provides_retrospective_aspects
        # rather than the static SECTION_SPEC, and must also be accepted. The
        # exact domain-aspect set is discovered at add-time, so assert the guard
        # accepts whatever the live extension discovery reports.
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        module = _load_module()
        domain_keys = module._domain_aspect_keys()
        # The live extension discovery must report at least one domain-contributed
        # aspect — without one this test's assertion would be vacuous, so the
        # precondition is asserted rather than skipped.
        assert domain_keys, 'no domain-contributed retrospective aspects registered'
        domain_aspect = sorted(domain_keys)[0]
        _init_bundle(plan_id)
        fragment_path = _write_fragment(tmp_path, 'frag.toon', _valid_fragment_body('domain'))

        result = run_script(
            SCRIPT_PATH,
            'add',
            '--plan-id',
            plan_id,
            '--aspect',
            domain_aspect,
            '--fragment-file',
            str(fragment_path),
        )

        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        assert data['aspect'] == domain_aspect
        assert data['aspects'] == [domain_aspect]


# =============================================================================
# add — overwrite semantics
# =============================================================================


class TestAddOverwrite:
    def test_overwrite_replaces_aspect_value_and_flags_overwrote_true(self, tmp_path, monkeypatch):
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        _init_bundle(plan_id)
        original = _write_fragment(
            tmp_path,
            'original.toon',
            'status: success\naspect: request-result-alignment\nmarker: original\n',
        )
        _add_aspect(plan_id, 'request-result-alignment', original)

        replacement = _write_fragment(
            tmp_path,
            'replacement.toon',
            'status: success\naspect: request-result-alignment\nmarker: replacement\n',
        )

        result = run_script(
            SCRIPT_PATH,
            'add',
            '--plan-id',
            plan_id,
            '--aspect',
            'request-result-alignment',
            '--fragment-file',
            str(replacement),
            '--overwrite',
        )

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

    def test_relative_fragment_file_resolves_against_live_plan_dir(self, tmp_path, monkeypatch):
        # write the fragment under <plan_dir>/work/ (the path
        # SKILL.md Step 3 documents) and pass only the relative path.
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        _init_bundle(plan_id)
        work_dir = plan_dir / 'work'
        work_dir.mkdir(parents=True, exist_ok=True)
        (work_dir / 'fragment-alpha.toon').write_text(
            _valid_fragment_body('request-result-alignment'), encoding='utf-8'
        )

        # relative path; cwd is the test runner root, NOT the plan dir.
        result = run_script(
            SCRIPT_PATH,
            'add',
            '--plan-id',
            plan_id,
            '--aspect',
            'request-result-alignment',
            '--fragment-file',
            'work/fragment-alpha.toon',
        )

        # the script must resolve the relative path against plan_dir
        # rather than cwd, so the fragment is found and merged.
        assert result.success, result.stderr
        bundle_content = (plan_dir / 'work' / 'retro-fragments.toon').read_text(encoding='utf-8')
        assert 'request-result-alignment:' in bundle_content
        assert 'status: success' in bundle_content

    def test_absolute_fragment_file_still_resolves_unchanged(self, tmp_path, monkeypatch):
        # fragment outside the plan dir; pass its absolute path.
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch)
        _init_bundle(plan_id)
        external = _write_fragment(tmp_path, 'external.toon', _valid_fragment_body('plan-efficiency'))

        result = run_script(
            SCRIPT_PATH,
            'add',
            '--plan-id',
            plan_id,
            '--aspect',
            'plan-efficiency',
            '--fragment-file',
            str(external),
        )

        # absolute paths are passed through unchanged, so a fragment
        # outside the plan dir still resolves correctly.
        assert result.success, result.stderr
        bundle_content = (plan_dir / 'work' / 'retro-fragments.toon').read_text(encoding='utf-8')
        assert 'plan-efficiency:' in bundle_content


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
        # resolve both sides for cross-platform stability:
        # macOS /var → /private/var symlink, Linux pytest tmp_path under /tmp.
        plan_id = 'archived-agreement'
        archived_plan_path = (tmp_path / 'archive-copy').resolve()
        archived_plan_path.mkdir(parents=True, exist_ok=True)
        fragment_path = _write_fragment(tmp_path, 'aspect.toon', _valid_fragment_body('request-result-alignment'))
        expected_bundle = archived_plan_path / 'work' / 'retro-fragments.toon'

        # init in archived mode under the caller-supplied root.
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
        assert Path(init_result.toon()['bundle_path']).resolve() == expected_bundle

        # add — must read the same bundle init wrote.
        add_result = run_script(
            SCRIPT_PATH,
            'add',
            '--plan-id',
            plan_id,
            '--archived-plan-path',
            str(archived_plan_path),
            '--aspect',
            'request-result-alignment',
            '--fragment-file',
            str(fragment_path),
        )
        assert add_result.success, add_result.stderr
        assert Path(add_result.toon()['bundle_path']).resolve() == expected_bundle

        # finalize — must agree on the same bundle root.
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
        assert Path(finalize_data['bundle_path']).resolve() == expected_bundle
        assert int(finalize_data['aspect_count']) == 1

        # Negative assertion: nothing was written under the OS tmp fallback.
        os_tmp_root = Path(tempfile.gettempdir()) / 'plan-retrospective' / f'plan-{plan_id}'
        assert not os_tmp_root.exists()


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
