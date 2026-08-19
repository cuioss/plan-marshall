# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for ``collect-fragments.py``."""


from __future__ import annotations

import tempfile
from pathlib import Path

from _collect_fragments_fixtures import (
    SCRIPT_PATH,
    _add_aspect,
    _init_bundle,
    _load_module,
    _valid_fragment_body,
    _write_fragment,
)
from _plan_retrospective_fixtures import setup_live_plan  # noqa: E402

from conftest import run_script  # noqa: E402

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
        # aspect ships dead, rejected at add time.
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

    def test_accepts_chat_history_analysis_aspect_key(self, tmp_path, monkeypatch):
        # chat-history-analysis (aspect 14) ships with a producer
        # (extract-chat-signal.py + the reference-doc synthesis step) AND a
        # SECTION_SPEC render row. The row makes it a member of
        # valid_aspect_keys(), so cmd_add MUST accept it — without the row the
        # registration is rejected with `Unregistered aspect key` and the
        # fragment can never reach the report.
        plan_id, _plan_dir = setup_live_plan(tmp_path, monkeypatch)
        _init_bundle(plan_id)
        fragment_path = _write_fragment(
            tmp_path, 'frag.toon', _valid_fragment_body('chat-history-analysis')
        )

        result = run_script(
            SCRIPT_PATH,
            'add',
            '--plan-id',
            plan_id,
            '--aspect',
            'chat-history-analysis',  # registered static key (SECTION_SPEC row)
            '--fragment-file',
            str(fragment_path),
        )

        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'
        assert data['aspect'] == 'chat-history-analysis'
        assert data['aspects'] == ['chat-history-analysis']

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
