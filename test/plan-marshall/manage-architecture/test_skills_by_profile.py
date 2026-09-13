#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The ``skills_by_profile`` three-state signal, end to end.

A profile is in exactly one of three states, and the whole point of this file is
that all three stay distinguishable at every surface they cross:

* **resolved** — the block carries skills.
* **declared minimal** — the block is empty AND says so with ``"minimal": true``.
  The store was asked and answered "none".
* **unresolved** — the block is empty and says nothing, or there is no block at
  all. The store was never populated for it.

The distinction is cheap to lose and expensive to notice, so it is asserted at
each seam independently rather than once at the end:

1. **The write path** (``_cmd_enrich``) — enriching a declared-minimal profile
   with real skills must DROP the declaration, and a block that carries both is
   malformed.
2. **The read guard** (``_cmd_client_query``) — every unresolved shape surfaces
   the named condition, including the list-shaped block and the profile that is
   absent entirely, while the declared-minimal block stays silent.
3. **The read payload** (``get_module_info``) — the guard's messages reach the
   caller that asked the question, not just the log.
4. **The rendered surfaces** (``render_overview`` / ``render_module_markdown``) —
   the two zero-count states must not print the same line.

Every case that asserts silence is paired with a case that asserts the signal
for the neighbouring state. A silence assertion alone is satisfied by a guard
that never fires at all, which is the failure this file exists to rule out.
"""

import json
import sys
import tempfile
import types
from pathlib import Path

import pytest

from conftest import load_script_module

_architecture_core = load_script_module(
    'plan-marshall', 'manage-architecture', '_architecture_core.py', '_architecture_core'
)
_cmd_enrich = load_script_module('plan-marshall', 'manage-architecture', '_cmd_enrich.py', '_cmd_enrich')
_cmd_client_query = load_script_module(
    'plan-marshall', 'manage-architecture', '_cmd_client_query.py', '_cmd_client_query'
)
_cmd_client = load_script_module('plan-marshall', 'manage-architecture', '_cmd_client.py', '_cmd_client')

save_project_meta = _architecture_core.save_project_meta
save_module_derived = _architecture_core.save_module_derived
save_module_enriched = _architecture_core.save_module_enriched
load_module_enriched_or_empty = _architecture_core.load_module_enriched_or_empty

enrich_add_domain = _cmd_enrich.enrich_add_domain
_validate_skills_by_profile_structure = _cmd_enrich._validate_skills_by_profile_structure

detect_stale_skills_by_profile = _cmd_client_query.detect_stale_skills_by_profile
_configured_expected_profiles = _cmd_client_query._configured_expected_profiles
_emit_staleness_warning = _cmd_client_query._emit_skills_by_profile_staleness_warning
get_module_info = _cmd_client_query.get_module_info

render_overview = _cmd_client.render_overview
render_module_markdown = _cmd_client.render_module_markdown

#: A notation that really resolves in this repository, so the read guard's
#: stale-notation check stays quiet and cannot be mistaken for the condition
#: under test.
_LIVE_NOTATION = 'plan-marshall:persona-plan-marshall-agent'

#: The substring that identifies the unresolved-profile condition.
_UNRESOLVED = 'not declared minimal'

#: The substring that identifies the absent-profile condition.
_ABSENT = 'has no block in skills_by_profile'


def _all_live(_notation: str) -> bool:
    return True


# =============================================================================
# Seam 1 — the write path drops a declaration its own write contradicts
# =============================================================================


class _FakeExtension:
    """An extension supplying one domain whose skills land in one profile."""

    def __init__(self, domain_key: str, skills_by_profile: dict) -> None:
        self._domain_key = domain_key
        self._skills_by_profile = skills_by_profile

    def get_skill_domains(self) -> list[dict]:
        return [{'domain': {'key': self._domain_key}}]

    def applies_to_module(self, _module_data, active_profiles=None) -> dict:
        return {'skills_by_profile': self._skills_by_profile}


@pytest.fixture
def fake_extension(monkeypatch):
    """Install an ``extension_discovery`` the enrich path's deferred import sees.

    ``enrich_add_domain`` imports ``discover_all_extensions`` inside the function
    body, so the stub has to be in ``sys.modules`` rather than patched onto an
    already-imported name.
    """

    def install(domain_key: str, skills_by_profile: dict) -> None:
        extension = _FakeExtension(domain_key, skills_by_profile)

        def discover_all_extensions() -> list[dict]:
            return [{'bundle': 'stub', 'module': extension}]

        fake = types.ModuleType('extension_discovery')
        monkeypatch.setattr(fake, 'discover_all_extensions', discover_all_extensions, raising=False)
        monkeypatch.setitem(sys.modules, 'extension_discovery', fake)

    return install


def test_enriching_a_declared_minimal_profile_drops_the_declaration(fake_extension):
    """A profile that receives skills stops claiming it is deliberately empty.

    The persisted block is re-read from disk rather than taken from the return
    value: the write path is what had to change, and a return value assembled in
    memory could agree while the document on disk still carried the stale
    ``minimal`` for every later reader.
    """
    fake_extension('demo', {'module_testing': {'defaults': [{'skill': _LIVE_NOTATION, 'description': 'd'}]}})

    with tempfile.TemporaryDirectory() as tmpdir:
        save_module_enriched(
            'mod',
            {'skills_by_profile': {'module_testing': {'defaults': [], 'optionals': [], 'minimal': True}}},
            tmpdir,
        )

        enrich_add_domain('mod', 'demo', project_dir=tmpdir, crawled_modules={'mod': {'name': 'mod'}})

        persisted = load_module_enriched_or_empty('mod', tmpdir)['skills_by_profile']['module_testing']

    assert 'minimal' not in persisted, persisted
    assert _LIVE_NOTATION in [entry['skill'] for entry in persisted['defaults']]


def test_enriching_a_declared_minimal_profile_with_nothing_keeps_the_declaration(fake_extension):
    """The negative control: no skills appended means the declaration still holds.

    Without this arm, "drops the declaration" is equally satisfied by a write
    path that strips ``minimal`` unconditionally — which would erase a legitimate
    declaration on every no-op re-run of ``enrich all``.
    """
    fake_extension('demo', {'module_testing': {'defaults': []}})

    with tempfile.TemporaryDirectory() as tmpdir:
        save_module_enriched(
            'mod',
            {'skills_by_profile': {'module_testing': {'defaults': [], 'optionals': [], 'minimal': True}}},
            tmpdir,
        )

        enrich_add_domain('mod', 'demo', project_dir=tmpdir, crawled_modules={'mod': {'name': 'mod'}})

        persisted = load_module_enriched_or_empty('mod', tmpdir)['skills_by_profile']['module_testing']

    assert persisted['minimal'] is True, persisted


def test_validator_flags_a_block_that_declares_minimal_and_carries_entries():
    """``minimal: true`` beside real entries is malformed, not a judgement call."""
    warnings = _validate_skills_by_profile_structure(
        {'module_testing': {'defaults': [{'skill': _LIVE_NOTATION, 'description': 'd'}], 'minimal': True}}
    )

    assert any('module_testing' in w and 'carries defaults/optionals entries' in w for w in warnings), warnings


def test_validator_accepts_a_genuinely_empty_declared_minimal_block():
    """The matched control: an empty block declaring minimality is well-formed.

    The arm above is satisfied by a validator that rejects every ``minimal``
    declaration; this one is what confines the rejection to the contradiction.
    """
    warnings = _validate_skills_by_profile_structure(
        {'module_testing': {'defaults': [], 'optionals': [], 'minimal': True}}
    )

    assert warnings == []


# =============================================================================
# Seam 2 — the read guard names every unresolved shape
# =============================================================================


def test_empty_list_shaped_block_surfaces_the_unresolved_condition():
    """``{"module_testing": []}`` has nowhere to declare minimality, so it never can.

    A list-shaped block used to be passed over as the write path's problem, which
    left the read path silent about a profile that resolved nothing.
    """
    warnings = detect_stale_skills_by_profile('mod', {'module_testing': []}, _all_live)

    assert any('module_testing' in w and _UNRESOLVED in w for w in warnings), warnings


def test_non_empty_list_shaped_block_does_not_surface_the_unresolved_condition():
    """The control that bounds the case above to the EMPTY list.

    A non-empty list resolves skills, so the unresolved condition is not its
    condition — its shape is the enrich validator's surface. Without this arm the
    assertion above is satisfied by a guard that warns about every list.
    """
    warnings = detect_stale_skills_by_profile('mod', {'module_testing': [_LIVE_NOTATION]}, _all_live)

    assert not any('module_testing' in w and _UNRESOLVED in w for w in warnings), warnings


def test_unresolvable_registry_still_reports_the_unresolved_profile(monkeypatch):
    """A registry that cannot be resolved narrows the guard to one dropped check.

    Both halves are asserted: the unresolved-profile condition is PRESENT (the
    guard still ran) and the stale-notation condition is ABSENT (the registry
    check was skipped rather than run against a root that was never obtained).
    """

    def exploding_resolve_bundles_root(_start):
        raise RuntimeError('bundle root unresolvable')

    fake = types.ModuleType('marketplace_bundles')
    fake.resolve_bundles_root = exploding_resolve_bundles_root
    fake.resolve_bundle_path = lambda *_args: None
    monkeypatch.setitem(sys.modules, 'marketplace_bundles', fake)

    merged = {
        'skills_by_profile': {
            'implementation': {'defaults': [{'skill': 'plan-marshall:retired-and-gone'}]},
            'module_testing': {'defaults': [], 'optionals': []},
        }
    }

    messages = _emit_staleness_warning('mod', merged)

    assert any('module_testing' in m and _UNRESOLVED in m for m in messages), messages
    assert not any('absent from the live registry' in m for m in messages), messages


# =============================================================================
# Seam 2b — the absent-profile condition, expected set read from configuration
# =============================================================================


def _seed_marshal_active_profiles(tmpdir: str, profiles: list[str]) -> None:
    """Write the ``skill_domains.active_profiles`` declaration into ``tmpdir``."""
    plan_dir = Path(tmpdir) / '.plan'
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'marshal.json').write_text(
        json.dumps({'skill_domains': {'active_profiles': profiles}}), encoding='utf-8'
    )


def test_expected_profiles_come_from_configuration():
    """The expected set is read from ``marshal.json``, never hard-coded."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_marshal_active_profiles(tmpdir, ['implementation', 'module_testing'])

        assert _configured_expected_profiles(tmpdir) == {'implementation', 'module_testing'}


def test_no_configured_profiles_means_no_expectation():
    """A project that declares no active profiles gets no absent-profile report.

    ``None`` — not an invented default set — is what keeps the guard from warning
    every module in an unconfigured project about profiles nobody asked for.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        assert _configured_expected_profiles(tmpdir) is None


def test_profile_declared_active_but_absent_surfaces_the_named_condition():
    """A module answering only ``implementation`` under a two-profile declaration.

    The absent profile was never asked, which is a different fact from answering
    none — so it gets its own condition rather than riding the unresolved one.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_marshal_active_profiles(tmpdir, ['implementation', 'module_testing'])
        merged = {
            'skills_by_profile': {
                'implementation': {'defaults': [{'skill': _LIVE_NOTATION, 'description': 'd'}]},
            }
        }

        messages = _emit_staleness_warning('mod', merged, tmpdir)

    assert any('module_testing' in m and _ABSENT in m for m in messages), messages


def test_every_declared_profile_present_surfaces_no_absent_condition():
    """The matched control: nothing is absent, so nothing is reported absent."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_marshal_active_profiles(tmpdir, ['implementation', 'module_testing'])
        merged = {
            'skills_by_profile': {
                'implementation': {'defaults': [{'skill': _LIVE_NOTATION, 'description': 'd'}]},
                'module_testing': {'defaults': [{'skill': _LIVE_NOTATION, 'description': 'd'}]},
            }
        }

        messages = _emit_staleness_warning('mod', merged, tmpdir)

    assert not any(_ABSENT in m for m in messages), messages


# =============================================================================
# Seam 3 — the payload the caller reads, not just the log
# =============================================================================


def _seed_module(tmpdir: str, skills_by_profile: dict) -> None:
    """Write the minimum store a ``get_module_info`` / render call needs."""
    save_project_meta(
        {
            'name': 'demo',
            'description': '',
            'description_reasoning': '',
            'extensions_used': [],
            'modules': {'mod': {}},
        },
        tmpdir,
    )
    save_module_derived(
        'mod',
        {'name': 'mod', 'paths': {'module': 'mod'}, 'internal_dependencies': [], 'commands': {}},
        tmpdir,
    )
    save_module_enriched(
        'mod',
        {'purpose': 'library', 'responsibility': 'demo', 'skills_by_profile': skills_by_profile},
        tmpdir,
    )


def _zero_count_map(*, declared_minimal: bool) -> dict:
    """One resolved profile plus one empty profile, declared or not."""
    empty: dict = {'defaults': [], 'optionals': []}
    if declared_minimal:
        empty['minimal'] = True
    return {
        'implementation': {'defaults': [{'skill': _LIVE_NOTATION, 'description': 'd'}]},
        'module_testing': empty,
    }


def test_module_payload_names_the_condition_for_an_undeclared_empty_profile():
    """``get_module_info`` carries the guard's message in a ``warnings[]`` field."""
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_module(tmpdir, _zero_count_map(declared_minimal=False))

        payload = get_module_info('mod', project_dir=tmpdir)

    assert any('module_testing' in w and _UNRESOLVED in w for w in payload.get('warnings', [])), payload.get('warnings')


def test_module_payload_omits_warnings_for_a_declared_minimal_profile():
    """The matched control, and the presence gate.

    The key is ABSENT rather than an empty list: an always-present ``warnings:
    []`` would make "the guard found nothing" and "the guard never ran" the same
    payload, and a consumer reading the empty list would take it as a clean bill
    of health it was never given.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_module(tmpdir, _zero_count_map(declared_minimal=True))

        payload = get_module_info('mod', project_dir=tmpdir)

    assert 'warnings' not in payload, payload.get('warnings')


# =============================================================================
# Seam 4 — the rendered surfaces distinguish the two zero-count states
# =============================================================================


def _module_testing_line(rendered: str) -> str:
    """The one rendered line describing the ``module_testing`` profile."""
    lines = [line for line in rendered.splitlines() if line.startswith('- module_testing:')]
    assert len(lines) == 1, rendered
    return lines[0]


@pytest.mark.parametrize('render', ['overview', 'module'], ids=['overview', 'deep-dive'])
def test_rendered_surfaces_distinguish_the_two_zero_count_states(render):
    """A declared-minimal profile and an undeclared-empty one render differently.

    Both surfaces are covered by one parametrised case because they must agree:
    the deep-dive and the overview read the same store, and a reader who checks
    one and then the other must not be told two different things. Asserting the
    two lines DIFFER is the load-bearing part — a shared ``0 skills`` line
    reported both states identically, which is exactly what made an un-enriched
    profile look like a settled decision.
    """

    def render_it(tmpdir: str) -> str:
        if render == 'overview':
            return str(render_overview(tmpdir, budget=500))
        return str(render_module_markdown('mod', tmpdir, budget=500))

    with tempfile.TemporaryDirectory() as declared_dir, tempfile.TemporaryDirectory() as undeclared_dir:
        _seed_module(declared_dir, _zero_count_map(declared_minimal=True))
        _seed_module(undeclared_dir, _zero_count_map(declared_minimal=False))

        declared_line = _module_testing_line(render_it(declared_dir))
        undeclared_line = _module_testing_line(render_it(undeclared_dir))

    assert declared_line != undeclared_line
    assert 'minimal' in declared_line
    assert 'unresolved' in undeclared_line
    assert '0 skills' not in declared_line
    assert '0 skills' not in undeclared_line


@pytest.mark.parametrize('render', ['overview', 'module'], ids=['overview', 'deep-dive'])
def test_rendered_surfaces_still_count_a_resolved_profile(render):
    """The control that keeps the two zero-count forms from swallowing the count.

    Without it, "the two zero states differ" is satisfied by a renderer that
    stopped reporting counts altogether.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        _seed_module(tmpdir, _zero_count_map(declared_minimal=True))

        rendered = (
            render_overview(tmpdir, budget=500) if render == 'overview' else render_module_markdown('mod', tmpdir, 500)
        )

    assert '- implementation: 1 skill' in rendered, rendered
