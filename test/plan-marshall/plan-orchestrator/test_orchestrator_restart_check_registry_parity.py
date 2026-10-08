#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``registry_parity`` arm of the ``cleanup restart-check`` verb.

The arm answers one question — would a restarted session load the version the
executor was generated at? — from three stores it reads through the shared
``plugin_registry`` reader. Every test arranges those stores as real files under
a fixture tree; none reads the machine's own registry, executor or cache.

The arm has exactly one definite hazard: a registry pinned BEHIND the executor.
Everything it could not establish — an unreadable store, a checkout that does
not install plan-marshall through the registry at all, a registry pinned AHEAD
of the executor — is ``indeterminate``. Reading any of those as ``not_ready``
would report something the arm never observed, so the degraded arrangements
below are each asserted against ``not_ready`` as well as for ``indeterminate``.
"""

import shutil
from collections.abc import Callable

import plugin_registry
import pytest
from _restart_check_fixtures import (
    INDETERMINATE,
    NEWER_VERSION,
    NOT_READY,
    OLDER_VERSION,
    PARITY_BUNDLE,
    PARITY_VERSION,
    READINESS_ORDER,
    READY,
    SCRIPT_PATH,
    ParityStores,
    _orch,
    _ready_epic,
    _run,
    _signal_row,
    add_cache_version,
    install_parity_stores,
    pin_registry,
    registry_entry,
    set_executor_version,
    write_executor,
    write_registry,
)

from conftest import get_skill_dir

SIGNAL = 'registry_parity'


@pytest.fixture(autouse=True)
def parity_stores(tmp_path, monkeypatch):
    """Point the parity arm of every test at fixture stores that are in parity."""
    return install_parity_stores(tmp_path, monkeypatch)


# =============================================================================
# Arrangements — each one moves the in-parity default stores to one state
# =============================================================================


def _in_parity(stores: ParityStores) -> None:
    """Leave the default stores as built: all three agree."""


def _registry_behind(stores: ParityStores) -> None:
    pin_registry(stores, OLDER_VERSION)


def _one_scope_behind(stores: ParityStores) -> None:
    pin_registry(stores, PARITY_VERSION, OLDER_VERSION)


def _comma_in_pinned_version(stores: ParityStores) -> None:
    pin_registry(stores, '0.1,5')


def _registry_ahead(stores: ParityStores) -> None:
    pin_registry(stores, NEWER_VERSION)


def _registry_absent(stores: ParityStores) -> None:
    stores.registry.unlink()


def _registry_not_json(stores: ParityStores) -> None:
    stores.registry.write_text('{"plugins": ', encoding='utf-8')


def _registry_is_a_directory(stores: ParityStores) -> None:
    stores.registry.unlink()
    stores.registry.mkdir()


def _no_entry_and_executor_newer(stores: ParityStores) -> None:
    # The executor is moved ahead so that ANY pinned row would read as behind:
    # the arrangement can only stay clear of not_ready by holding no row at all.
    write_registry(stores, {})
    set_executor_version(stores, NEWER_VERSION)


def _foreign_marketplace_only(stores: ParityStores) -> None:
    write_registry(stores, {'plan-marshall@elsewhere': [registry_entry(OLDER_VERSION)]})
    set_executor_version(stores, NEWER_VERSION)


def _executor_absent(stores: ParityStores) -> None:
    stores.executor.unlink()


def _executor_without_assignment(stores: ParityStores) -> None:
    write_executor(stores, '#!/usr/bin/env python3\nSCRIPTS = {}\n')


def _executor_empty_sentinel(stores: ParityStores) -> None:
    write_executor(stores, "MARSHALL_VERSION = ''\n")


def _pin_not_orderable(stores: ParityStores) -> None:
    pin_registry(stores, '0.1-1069')


def _cache_absent(stores: ParityStores) -> None:
    shutil.rmtree(stores.cache_root)


def _cache_newer_than_the_pin(stores: ParityStores) -> None:
    add_cache_version(stores, NEWER_VERSION)


#: Every arrangement with the verdict it must read.
ARRANGEMENTS: dict[str, tuple[Callable[[ParityStores], None], str]] = {
    'in-parity': (_in_parity, READY),
    'registry-behind': (_registry_behind, NOT_READY),
    'one-scope-behind': (_one_scope_behind, NOT_READY),
    'comma-in-pinned-version': (_comma_in_pinned_version, NOT_READY),
    'registry-ahead': (_registry_ahead, INDETERMINATE),
    'registry-absent': (_registry_absent, INDETERMINATE),
    'registry-not-json': (_registry_not_json, INDETERMINATE),
    'registry-is-a-directory': (_registry_is_a_directory, INDETERMINATE),
    'no-entry-and-executor-newer': (_no_entry_and_executor_newer, INDETERMINATE),
    'foreign-marketplace-only': (_foreign_marketplace_only, INDETERMINATE),
    'executor-absent': (_executor_absent, INDETERMINATE),
    'executor-without-assignment': (_executor_without_assignment, INDETERMINATE),
    'executor-empty-sentinel': (_executor_empty_sentinel, INDETERMINATE),
    'pin-not-orderable': (_pin_not_orderable, INDETERMINATE),
    'cache-absent': (_cache_absent, INDETERMINATE),
    'cache-newer-than-the-pin': (_cache_newer_than_the_pin, INDETERMINATE),
}
assert {verdict for _, verdict in ARRANGEMENTS.values()} == set(READINESS_ORDER), (
    'the arrangements do not reach all three verdicts, so the parametrized tests below prove less than they read'
)

_NO_ENTRY = ('no-entry-and-executor-newer', 'foreign-marketplace-only')
_NOT_READY = tuple(name for name, (_, verdict) in ARRANGEMENTS.items() if verdict == NOT_READY)
_NEVER_NOT_READY = tuple(name for name, (_, verdict) in ARRANGEMENTS.items() if verdict != NOT_READY)
assert _NOT_READY and _NEVER_NOT_READY


def _report(name: str, stores: ParityStores, plan_context, monkeypatch) -> dict:
    """Run the verb over an otherwise fully ready epic with one parity arrangement applied."""
    _ready_epic(plan_context, monkeypatch)
    ARRANGEMENTS[name][0](stores)
    return _run()


# =============================================================================
# Verdicts
# =============================================================================


class TestParityVerdicts:
    @pytest.mark.parametrize('name', sorted(ARRANGEMENTS))
    def test_each_arrangement_reads_its_verdict(self, name, parity_stores, plan_context, monkeypatch):
        result = _report(name, parity_stores, plan_context, monkeypatch)

        row = _signal_row(result, SIGNAL)
        assert row['verdict'] == ARRANGEMENTS[name][1]
        assert row['verdict'] in READINESS_ORDER
        assert result['signals_scored'] == result['signals_total']

    @pytest.mark.parametrize('name', sorted(ARRANGEMENTS))
    def test_no_field_of_the_row_carries_a_comma(self, name, parity_stores, plan_context, monkeypatch):
        row = _signal_row(_report(name, parity_stores, plan_context, monkeypatch), SIGNAL)

        assert row['evidence'].strip() and row['population'].strip()
        assert ',' not in row['evidence']
        assert ',' not in row['population']

    @pytest.mark.parametrize('name', _NEVER_NOT_READY)
    def test_only_a_registry_behind_the_executor_reads_not_ready(self, name, parity_stores, plan_context, monkeypatch):
        row = _signal_row(_report(name, parity_stores, plan_context, monkeypatch), SIGNAL)

        assert row['verdict'] != NOT_READY

    @pytest.mark.parametrize('name', _NO_ENTRY)
    def test_a_checkout_without_a_registry_entry_is_indeterminate(self, name, parity_stores, plan_context, monkeypatch):
        row = _signal_row(_report(name, parity_stores, plan_context, monkeypatch), SIGNAL)

        assert row['verdict'] == INDETERMINATE
        assert 'not installed through the plugin registry' in row['evidence']


# =============================================================================
# Evidence — a verdict names what was compared and what to do about it
# =============================================================================


class TestParityEvidence:
    def test_ready_evidence_names_the_agreed_version(self, parity_stores, plan_context, monkeypatch):
        row = _signal_row(_report('in-parity', parity_stores, plan_context, monkeypatch), SIGNAL)

        assert PARITY_VERSION in row['evidence']

    def test_not_ready_evidence_names_both_versions_and_the_repin_command(
        self, parity_stores, plan_context, monkeypatch
    ):
        row = _signal_row(_report('registry-behind', parity_stores, plan_context, monkeypatch), SIGNAL)

        assert OLDER_VERSION in row['evidence']
        assert PARITY_VERSION in row['evidence']
        assert 'python3 marketplace/targets/claude/registry_pin.py --apply' in row['evidence']
        assert 'meta-repository only' in row['evidence']
        assert 'ADR-020' in row['evidence']

    def test_ahead_evidence_names_both_versions_and_executor_regeneration(
        self, parity_stores, plan_context, monkeypatch
    ):
        row = _signal_row(_report('registry-ahead', parity_stores, plan_context, monkeypatch), SIGNAL)

        assert NEWER_VERSION in row['evidence']
        assert PARITY_VERSION in row['evidence']
        assert 'regenerate the executor' in row['evidence']
        assert 'registry_pin.py' not in row['evidence']

    def test_unreadable_registry_evidence_names_the_read_state(self, parity_stores, plan_context, monkeypatch):
        absent = _signal_row(_report('registry-absent', parity_stores, plan_context, monkeypatch), SIGNAL)

        assert plugin_registry.REGISTRY_ABSENT in absent['evidence']
        assert plugin_registry.REGISTRY_ABSENT in absent['population']

    def test_unreadable_executor_evidence_names_the_read_state(self, parity_stores, plan_context, monkeypatch):
        row = _signal_row(_report('executor-empty-sentinel', parity_stores, plan_context, monkeypatch), SIGNAL)

        assert plugin_registry.EXECUTOR_VERSION_EMPTY in row['evidence']

    def test_cache_evidence_names_the_bundle_and_the_differing_version(self, parity_stores, plan_context, monkeypatch):
        row = _signal_row(_report('cache-newer-than-the-pin', parity_stores, plan_context, monkeypatch), SIGNAL)

        assert f'{PARITY_BUNDLE}={NEWER_VERSION}' in row['evidence']
        assert 'cache: 1 bundle directory(ies) read' in row['population']


# =============================================================================
# The floor — the arm takes part in the overall verdict
# =============================================================================


class TestParityInTheFloor:
    def test_stores_in_parity_leave_a_ready_report_ready(self, parity_stores, plan_context, monkeypatch):
        result = _report('in-parity', parity_stores, plan_context, monkeypatch)

        assert result['verdict'] == READY

    @pytest.mark.parametrize('name', _NOT_READY)
    def test_a_not_ready_parity_row_lowers_the_overall_verdict(self, name, parity_stores, plan_context, monkeypatch):
        # Every other signal is ready, so the parity row alone decides the floor.
        result = _report(name, parity_stores, plan_context, monkeypatch)

        others = {row['verdict'] for row in result['signals'] if row['signal'] != SIGNAL}
        assert others == {READY}
        assert result['verdict'] == NOT_READY

    def test_an_indeterminate_parity_row_floors_the_report_without_failing_it(
        self, parity_stores, plan_context, monkeypatch
    ):
        result = _report('no-entry-and-executor-newer', parity_stores, plan_context, monkeypatch)

        assert result['verdict'] == INDETERMINATE


# =============================================================================
# The clean break — the excluded arm is gone and the reader is shared
# =============================================================================


class TestParityArmIsScoredThroughTheSharedReader:
    def test_the_excluded_arm_vocabulary_is_gone_from_the_module(self):
        source = SCRIPT_PATH.read_text(encoding='utf-8')

        assert 'cleanup-restart-check' in source, 'the scan did not read the module under test'
        for token in ('NOT_AVAILABLE', 'REGISTRY_PARITY_OWNER', 'PLAN-TRUTH-059', 'not_available'):
            assert token not in source, f'{token} survives in the orchestrator script'
        assert not hasattr(_orch, 'NOT_AVAILABLE')
        assert not hasattr(_orch, 'REGISTRY_PARITY_OWNER')

    def test_the_module_carries_no_store_parser_or_store_location_of_its_own(self):
        # The registry shape, the executor assignment and the store locations
        # belong to the shared reader. Finding one of them spelled here would
        # mean a second reader, or a second copy of a path.
        source = SCRIPT_PATH.read_text(encoding='utf-8')

        assert '_registry_parity_signal' in source, 'the scan did not read the module under test'
        for token in ('installPath', 'MARSHALL_VERSION', 'installed_plugins.json'):
            assert token not in source, f'{token} is spelled in the orchestrator script'
        assert _orch.plugin_registry is plugin_registry

    def test_the_skill_document_describes_a_scored_arm(self):
        document = (get_skill_dir('plan-marshall', 'plan-orchestrator') / 'SKILL.md').read_text(encoding='utf-8')
        _, found, tail = document.partition('### cleanup restart-check')
        assert found, 'the cleanup restart-check section was not found'
        section = tail.split('\n### ', 1)[0]

        assert 'not_available' not in section
        assert SIGNAL in section
        for verdict in READINESS_ORDER:
            assert f'`{verdict}`' in section
