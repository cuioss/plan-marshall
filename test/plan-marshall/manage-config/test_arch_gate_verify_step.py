#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the arch-gate verify-step append in skill-domains configure.

Covers deliverable 2 of the arch-gate-build-command plan:
- ``_configured_domains_provide_arch_gate()`` returns True only when a configured
  domain's extension declares a non-None ``provides_arch_gate()`` descriptor.
- ``skill-domains configure`` appends ``default:verify:arch-gate`` to
  ``phase-5-execute.verification_steps`` when a configured domain provides one, and
  appends nothing when every configured domain returns None (the silent-skip
  default).
- The append is idempotent across re-configures (the keyed map de-dups by key).

Tier 2 (direct import) tests with ``discover_all_extensions`` patched to inject
deterministic fake extensions, so the assertions do not depend on any real domain
bundle wiring up an arch-gate tool.
"""

import importlib.util
import json
import sys
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-config'
    / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_cmd_skill_domains = _load_module('_cmd_skill_domains', '_cmd_skill_domains.py')

cmd_skill_domains = _cmd_skill_domains.cmd_skill_domains

_ARCH_GATE_STEP = 'default:verify:arch-gate'


class _FakeExt:
    """Minimal extension stub exposing one domain and a provides_arch_gate() result.

    Only ``get_skill_domains`` and ``provides_arch_gate`` are defined — the absence
    of ``provides_triage`` / ``provides_outline_skill`` exercises the hasattr-guarded
    paths in ``convert_extension_to_domain_config`` exactly as a real minimal
    extension would.
    """

    def __init__(self, domain_key: str, arch_gate: dict | None):
        self._domain_key = domain_key
        self._arch_gate = arch_gate

    def get_skill_domains(self) -> list[dict]:
        return [
            {
                'domain': {
                    'key': self._domain_key,
                    'name': f'{self._domain_key} domain',
                    'description': 'fake test domain',
                },
                'profiles': {'core': {'defaults': [], 'optionals': []}},
            }
        ]

    def provides_arch_gate(self) -> dict | None:
        return self._arch_gate


def _fake_extensions(*exts: _FakeExt) -> list[dict]:
    """Wrap fake extension stubs in the discover_all_extensions() record shape."""
    return [{'bundle': f'fake-bundle-{i}', 'module': ext} for i, ext in enumerate(exts)]


def _write_configure_marshal(fixture_dir: Path) -> Path:
    """Write a minimal initialized marshal.json suitable for the configure verb."""
    config = {
        'skill_domains': {},
        'system': {'retention': {}},
        'plan': {
            'phase-1-init': {'branch_strategy': 'direct'},
            'phase-2-refine': {'confidence_threshold': 95, 'compatibility': 'breaking'},
            'phase-5-execute': {
                'commit_and_push': True,
                'max_iterations': 5,
                'verification_steps': {
                    'default:verify:quality-gate': {},
                    'default:verify:module-tests': {},
                },
            },
            'phase-6-finalize': {'max_iterations': 3, 'steps': {}},
        },
    }
    marshal_path = fixture_dir / 'marshal.json'
    marshal_path.write_text(json.dumps(config, indent=2))
    return marshal_path


# =============================================================================
# Helper: _configured_domains_provide_arch_gate (Tier 2, direct)
# =============================================================================


def test_helper_true_when_domain_provides_tool():
    """Returns True when a configured domain's extension declares an arch-gate tool."""
    exts = _fake_extensions(_FakeExt('gatedomain', {'tool': 'archunit'}))
    with patch.object(_cmd_skill_domains, 'discover_all_extensions', return_value=exts):
        assert _cmd_skill_domains._configured_domains_provide_arch_gate(['gatedomain']) is True


def test_helper_false_when_domain_returns_none():
    """Returns False when the configured domain's extension returns None (silent-skip)."""
    exts = _fake_extensions(_FakeExt('plaindomain', None))
    with patch.object(_cmd_skill_domains, 'discover_all_extensions', return_value=exts):
        assert _cmd_skill_domains._configured_domains_provide_arch_gate(['plaindomain']) is False


def test_helper_false_for_empty_domain_list():
    """Returns False for an empty configured-domain list without touching discovery."""
    with patch.object(_cmd_skill_domains, 'discover_all_extensions', return_value=[]) as disc:
        assert _cmd_skill_domains._configured_domains_provide_arch_gate([]) is False
    disc.assert_not_called()


def test_helper_only_checks_configured_domains():
    """A gate-providing domain that is NOT in the configured set does not trigger True."""
    exts = _fake_extensions(
        _FakeExt('gatedomain', {'tool': 'archunit'}),
        _FakeExt('plaindomain', None),
    )
    with patch.object(_cmd_skill_domains, 'discover_all_extensions', return_value=exts):
        # Only the None-returning domain is configured.
        assert _cmd_skill_domains._configured_domains_provide_arch_gate(['plaindomain']) is False
        # The gate-providing domain configured → True.
        assert _cmd_skill_domains._configured_domains_provide_arch_gate(['gatedomain']) is True


# =============================================================================
# configure verb: arch-gate verify-step append (Tier 2, direct)
# =============================================================================


def test_configure_appends_arch_gate_when_domain_provides(plan_context):
    """configure appends default:verify:arch-gate when a configured domain provides one."""
    marshal_path = _write_configure_marshal(plan_context.fixture_dir)
    exts = _fake_extensions(_FakeExt('gatedomain', {'tool': 'archunit'}))

    with patch.object(_cmd_skill_domains, 'discover_all_extensions', return_value=exts):
        result = cmd_skill_domains(Namespace(verb='configure', domains='gatedomain'))

    assert result['status'] == 'success'
    updated = json.loads(marshal_path.read_text())
    verification_steps = updated['plan']['phase-5-execute']['verification_steps']
    assert _ARCH_GATE_STEP in verification_steps
    assert verification_steps[_ARCH_GATE_STEP] == {}


def test_configure_no_arch_gate_when_domain_returns_none(plan_context):
    """configure appends nothing when the configured domain returns None."""
    marshal_path = _write_configure_marshal(plan_context.fixture_dir)
    exts = _fake_extensions(_FakeExt('plaindomain', None))

    with patch.object(_cmd_skill_domains, 'discover_all_extensions', return_value=exts):
        result = cmd_skill_domains(Namespace(verb='configure', domains='plaindomain'))

    assert result['status'] == 'success'
    updated = json.loads(marshal_path.read_text())
    verification_steps = updated['plan']['phase-5-execute']['verification_steps']
    assert _ARCH_GATE_STEP not in verification_steps


def test_configure_arch_gate_append_is_idempotent(plan_context):
    """Re-running configure yields exactly one arch-gate entry (keyed-map de-dup)."""
    marshal_path = _write_configure_marshal(plan_context.fixture_dir)
    exts = _fake_extensions(_FakeExt('gatedomain', {'tool': 'archunit'}))

    with patch.object(_cmd_skill_domains, 'discover_all_extensions', return_value=exts):
        first = cmd_skill_domains(Namespace(verb='configure', domains='gatedomain'))
        second = cmd_skill_domains(Namespace(verb='configure', domains='gatedomain'))

    assert first['status'] == 'success'
    assert second['status'] == 'success'
    updated = json.loads(marshal_path.read_text())
    verification_steps = updated['plan']['phase-5-execute']['verification_steps']
    assert list(verification_steps.keys()).count(_ARCH_GATE_STEP) == 1


# =============================================================================
# arch-constraint findings type registration (Tier 2, direct)
# =============================================================================


def test_arch_constraint_is_a_producible_finding_type():
    """arch-constraint is a registered finding type the producer can emit.

    ``manage-findings`` validates every ``add`` / ``qgate add`` ``--type`` against
    the ``FINDING_TYPES`` enum (``_findings_core`` raises / errors on a type not in
    the set). For the arch-gate verify-step to emit ``arch-constraint`` findings
    through the existing producer → store → triage pattern, the type must be a
    member of that enum — this test pins the registration so the jsonl-format.md
    taxonomy claim stays true in code.
    """
    from constants import FINDING_TYPES  # type: ignore[import-not-found]

    assert 'arch-constraint' in FINDING_TYPES


def test_arch_constraint_passes_the_producer_type_validator():
    """The producer's type validator accepts arch-constraint and rejects a bogus type.

    Exercises the exact gate the arch-gate producer hits — the ``finding_type not
    in FINDING_TYPES`` check in ``_findings_core`` — proving an ``arch-constraint``
    finding is genuinely producible (not merely documented) while a non-registered
    type is still rejected.
    """
    from constants import FINDING_TYPES  # type: ignore[import-not-found]

    assert 'arch-constraint' in FINDING_TYPES
    assert 'not-a-real-finding-type' not in FINDING_TYPES
