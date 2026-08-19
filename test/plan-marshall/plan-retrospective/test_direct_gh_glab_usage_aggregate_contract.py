# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the generic ``direct-gh-glab-usage.py`` aspect (Surfaces A+B) and
the retrospective-aspect extension point that homes the former Surface C.

Covers the domain-invariant detection scenarios for the generic aspect:

(a) Fixture log files containing ``gh``/``glab`` invocations (positive
    detection) — surface ``log_leak``.
(b) Fixture diff with added ``gh``/``glab`` lines (positive detection)
    — surface ``diff_leak``.
(d) Fixture where ``gh`` appears only in a comment — negative, must NOT
    trip the diff scanner.

Plus the Surface C split contract, scoped to this file per the deliverable:

* Surfaces A+B remain in the generic, domain-invariant ``direct-gh-glab-usage``
  aspect; ``wrapper_tangle`` is no longer emitted there.
* Surface C moved to the ``plan-marshall-plugin-dev`` domain aspect
  ``pm-plugin-development:plan-marshall-plugin:wrapper-tangle-scan``,
  contributed via the ``provides_retrospective_aspects()`` extension point.
* ``extension_discovery.py`` discovers the hook and surfaces it through the
  ``list-retrospective-aspects`` CLI (the deterministic backing for
  plan-retrospective Step 3's domain-aspect merge).
* ``pm-plugin-development``'s ``extension.py`` contributes the aspect gated by
  the ``plan-marshall-plugin-dev`` domain only; ``ExtensionBase`` returns ``[]``
  by default.
* plan-retrospective Step 3 merges domain aspects per domain — modelled here as
  the deterministic ``filter list-retrospective-aspects by plan domain``
  predicate the workflow step relies on.

The wrapper-tangle DETECTION behaviour itself lives in
``test/pm-plugin-development/plan-marshall-plugin/test_wrapper_tangle_scan.py``.
"""


from __future__ import annotations

import importlib.util

from _direct_gh_glab_usage_fixtures import (
    _PLUGIN_DEV_DOMAIN,
    _PLUGIN_DEV_EXT_PATH,
    EXT_DISCOVERY_PATH,
    SCRIPT_PATH,
    _load_extension_module,
)
from _plan_retrospective_fixtures import setup_live_plan  # noqa: E402

from conftest import run_script  # noqa: E402

# ---------------------------------------------------------------------------
# Top-level aggregate contract (generic aspect, Surfaces A+B only)
# ---------------------------------------------------------------------------


class TestAggregateContract:
    """The script's output shape must remain stable even when findings exist.

    After the Surface C split, the generic aspect emits only ``log_leak`` and
    ``diff_leak`` surfaces — a ``wrapper_tangle`` key must NOT appear in the
    by-surface counts.
    """

    def test_counts_by_surface_reflect_findings(self, tmp_path, monkeypatch):
        """Both surviving counters must appear and equal the findings emitted."""
        plan_id, plan_dir = setup_live_plan(tmp_path, monkeypatch, plan_id='retro-ghglab-aggregate')
        # One log leak.
        work_log = plan_dir / 'logs' / 'work.log'
        work_log.write_text(
            '[2026-04-17T12:00:00Z] [INFO] [abcabc] [STATUS] (plan-marshall:phase-6-finalize) ran gh pr list\n',
            encoding='utf-8',
        )
        (plan_dir / 'logs' / 'script-execution.log').write_text('', encoding='utf-8')

        result = run_script(
            SCRIPT_PATH,
            'run',
            '--plan-id',
            plan_id,
            '--mode',
            'live',
            '--project-root',
            str(tmp_path),
        )
        assert result.success, result.stderr
        data = result.toon()
        counts = data['counts']['by_surface']
        findings = data['findings']

        log_n = sum(1 for f in findings if f['surface'] == 'log_leak')
        diff_n = sum(1 for f in findings if f['surface'] == 'diff_leak')

        assert int(counts['log_leak']) == log_n
        assert int(counts['diff_leak']) == diff_n
        assert int(data['counts']['total']) == log_n + diff_n
        assert log_n >= 1
        # Surface C moved out — the generic aspect must not emit a wrapper_tangle
        # surface or counter any more.
        assert 'wrapper_tangle' not in counts, (
            f'Surface C (wrapper_tangle) must no longer be emitted by the generic '
            f'aspect; got by_surface counts: {counts}'
        )
        assert all(f['surface'] != 'wrapper_tangle' for f in findings)


# ---------------------------------------------------------------------------
# Surface C split — extension-point declaration (extension.py)
# ---------------------------------------------------------------------------


class TestSurfaceCDomainContribution:
    """``pm-plugin-development``'s extension contributes Surface C (wrapper-tangle)
    via ``provides_retrospective_aspects()``, gated by the
    ``plan-marshall-plugin-dev`` domain. ``ExtensionBase`` returns ``[]``.
    """

    def test_plugin_dev_extension_declares_wrapper_tangle(self):
        """The pm-plugin-development extension declares exactly the wrapper-tangle
        aspect through the retrospective-aspect hook.
        """
        ext = _load_extension_module(_PLUGIN_DEV_EXT_PATH, 'pm_plugin_dev_ext_retro')
        aspects = ext.provides_retrospective_aspects()
        assert isinstance(aspects, list)
        names = {a['aspect'] for a in aspects}
        assert 'wrapper-tangle' in names, f'Expected wrapper-tangle aspect; got {names}'

    def test_wrapper_tangle_aspect_gated_by_plugin_dev_domain(self):
        """The contributed aspect carries the plugin-dev domain gate and the
        correct fragment-producer notation — so plan-retrospective only merges
        it for plan-marshall-plugin-dev plans.
        """
        ext = _load_extension_module(_PLUGIN_DEV_EXT_PATH, 'pm_plugin_dev_ext_gate')
        aspect = next(a for a in ext.provides_retrospective_aspects() if a['aspect'] == 'wrapper-tangle')
        assert aspect['domain'] == _PLUGIN_DEV_DOMAIN
        assert aspect['script'] == 'pm-plugin-development:plan-marshall-plugin:wrapper-tangle-scan'
        assert aspect['reference']
        assert aspect['description']
        assert isinstance(aspect['order'], int)

    def test_extension_base_returns_empty_by_default(self):
        """A domain extension that does not override the hook contributes no
        retrospective aspects — the default keeps the generic retrospective
        domain-invariant.
        """
        from extension_base import ExtensionBase

        class _Bare(ExtensionBase):
            def get_skill_domains(self) -> list[dict]:
                return []

            def applies_to_module(self, module_data, active_profiles=None) -> dict:  # type: ignore[override]
                return {'applicable': False, 'confidence': 'none', 'signals': [], 'additive_to': None,
                        'skills_by_profile': {}}

            def discover_modules(self, project_root: str) -> list:
                return []

        assert _Bare().provides_retrospective_aspects() == []


# ---------------------------------------------------------------------------
# Surface C split — extension_discovery.py hook + list-retrospective-aspects CLI
# ---------------------------------------------------------------------------


class TestRetrospectiveAspectDiscovery:
    """``extension_discovery.py`` discovers ``provides_retrospective_aspects()``
    across all extensions and exposes them via the ``list-retrospective-aspects``
    CLI — the deterministic backing for plan-retrospective Step 3.
    """

    @staticmethod
    def _load_discovery():
        spec = importlib.util.spec_from_file_location('extension_discovery_retro', EXT_DISCOVERY_PATH)
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_get_retrospective_aspects_attributes_bundle(self):
        """The discovery helper returns every declared aspect across all
        extensions and stamps each with its contributing ``bundle``.
        """
        mod = self._load_discovery()
        extensions = mod.discover_all_extensions()
        aspects = mod.get_retrospective_aspects_from_extensions(extensions)

        wrapper = [a for a in aspects if a.get('aspect') == 'wrapper-tangle']
        assert len(wrapper) == 1, f'Expected exactly one wrapper-tangle aspect across all extensions; got {aspects}'
        assert wrapper[0]['domain'] == _PLUGIN_DEV_DOMAIN
        assert wrapper[0]['bundle'] == 'pm-plugin-development'

    def test_helper_skips_extensions_without_module(self):
        """A discovery entry whose ``module`` is None contributes nothing — the
        helper must not raise on extensions that failed to load.
        """
        mod = self._load_discovery()
        aspects = mod.get_retrospective_aspects_from_extensions([{'bundle': 'broken', 'module': None}])
        assert aspects == []

    def test_cli_lists_wrapper_tangle_row(self):
        """The ``list-retrospective-aspects`` CLI emits one row per declared
        aspect with the documented field set.
        """
        result = run_script(EXT_DISCOVERY_PATH, 'list-retrospective-aspects')
        assert result.success, result.stderr
        data = result.toon()
        assert data['status'] == 'success'

        rows = data['aspects']
        if isinstance(rows, dict):  # single-row TOON tables parse to a dict
            rows = [rows]
        wrapper = [r for r in rows if r['aspect'] == 'wrapper-tangle']
        assert len(wrapper) == 1, f'Expected one wrapper-tangle row; got {rows}'
        row = wrapper[0]
        assert row['domain'] == _PLUGIN_DEV_DOMAIN
        assert row['script'] == 'pm-plugin-development:plan-marshall-plugin:wrapper-tangle-scan'
        assert row['bundle'] == 'pm-plugin-development'
        assert row['reference']
        assert row['description']


# ---------------------------------------------------------------------------
# plan-retrospective Step 3 — domain-gated merge predicate
# ---------------------------------------------------------------------------


class TestStep3DomainMerge:
    """plan-retrospective Step 3 merges domain aspects per the audited plan's
    domain. The workflow step is LLM-driven prose, but the merge it performs is
    the deterministic predicate ``keep rows whose domain == plan_domain`` over
    the ``list-retrospective-aspects`` output. These tests lock that predicate.
    """

    @staticmethod
    def _list_aspect_rows():
        result = run_script(EXT_DISCOVERY_PATH, 'list-retrospective-aspects')
        assert result.success, result.stderr
        rows = result.toon()['aspects']
        return [rows] if isinstance(rows, dict) else rows

    @staticmethod
    def _merge_for_domain(rows, plan_domain):
        """Mirror Step 3's filter: keep only aspects gated by ``plan_domain``."""
        return [r for r in rows if r['domain'] == plan_domain]

    def test_plugin_dev_plan_picks_up_wrapper_tangle(self):
        """A plan-marshall-plugin-dev plan merges the wrapper-tangle aspect."""
        rows = self._list_aspect_rows()
        merged = self._merge_for_domain(rows, _PLUGIN_DEV_DOMAIN)
        assert {r['aspect'] for r in merged} == {'wrapper-tangle'}

    def test_other_domain_plan_skips_wrapper_tangle(self):
        """A plan of any non-matching domain merges no domain aspects — the
        wrapper-tangle scan is skipped because its gate does not match.
        """
        rows = self._list_aspect_rows()
        merged = self._merge_for_domain(rows, 'pm-dev-java')
        assert merged == [], f'Non-plugin-dev plan must not merge wrapper-tangle; got {merged}'
