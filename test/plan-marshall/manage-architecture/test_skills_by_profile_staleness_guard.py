#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the skills_by_profile staleness guard in ``_cmd_client_query.py``.

The guard is a non-blocking, read-path WARNING surface over a module's
``skills_by_profile`` map. It never raises. THREE distinct conditions surface a
warning, and this file covers all three — the docstring lists them because a
two-signal description of a three-signal guard is how the third stops being
maintained:

1. **A notation absent from the live registry** — a retired or renamed skill id
   still referenced by the map.
2. **The whole map missing or empty** — reported without any registry lookup,
   since there is nothing to look up.
3. **A present-but-empty PROFILE block that does not declare itself minimal** —
   the per-profile condition, distinct from (2) because the map itself is
   non-empty and contributes no notations to (1), so neither of the other two
   signals fires. A block declaring ``"minimal": true`` is the escape hatch and
   is deliberately silent; the two states differ by exactly that declaration.

The pure ``detect_stale_skills_by_profile`` core takes an injected ``is_live``
predicate so staleness detection is deterministic without a real bundle tree.
"""

import sys
import types
from pathlib import Path

import pytest

from conftest import load_script_module

_cmd_client_query = load_script_module(
    'plan-marshall', 'manage-architecture', '_cmd_client_query.py', '_cmd_client_query'
)

detect_stale_skills_by_profile = _cmd_client_query.detect_stale_skills_by_profile
_iter_skill_notations = _cmd_client_query._iter_skill_notations
_emit_staleness_warning = _cmd_client_query._emit_skills_by_profile_staleness_warning


# A retired ID that no longer resolves in the registry.
_STALE_NOTATION = 'plan-marshall:dev-agent-behavior-rules'
_LIVE_NOTATION = 'plan-marshall:persona-plan-marshall-agent'


def _profile_map(*skills: str) -> dict:
    """Build a skills_by_profile map with the given notations under one profile."""
    return {'implementation': {'defaults': [{'skill': s, 'description': f'desc for {s}'} for s in skills]}}


def _all_live(_notation: str) -> bool:
    return True


def _none_live(_notation: str) -> bool:
    return False


def test_warns_on_retired_notation():
    """A retired skill notation absent from the live registry surfaces one WARNING."""
    sbp = _profile_map(_LIVE_NOTATION, _STALE_NOTATION)
    warnings = detect_stale_skills_by_profile('default', sbp, lambda n: n != _STALE_NOTATION)
    assert len(warnings) == 1
    assert _STALE_NOTATION in warnings[0]
    assert 'absent from the live registry' in warnings[0]


def test_warns_on_missing_map():
    """A missing/empty skills_by_profile surfaces one WARNING without a registry lookup."""
    warnings = detect_stale_skills_by_profile('documentation', {}, _none_live)
    assert len(warnings) == 1
    assert 'missing or empty' in warnings[0]


def test_no_warning_when_all_notations_live():
    """A fully-resolvable skills_by_profile produces no WARNING."""
    sbp = _profile_map(_LIVE_NOTATION)
    assert detect_stale_skills_by_profile('default', sbp, _all_live) == []


def test_guard_is_non_blocking():
    """The guard returns a list and never raises, even for an all-stale map."""
    sbp = _profile_map(_STALE_NOTATION)
    warnings = detect_stale_skills_by_profile('default', sbp, _none_live)
    assert isinstance(warnings, list)
    assert len(warnings) == 1


def test_iter_collects_defaults_and_optionals():
    """``_iter_skill_notations`` walks both defaults and optionals, and string entries."""
    sbp = {
        'implementation': {
            'defaults': [{'skill': 'a:one'}, 'b:two'],
            'optionals': [{'skill': 'c:three'}],
        }
    }
    assert _iter_skill_notations(sbp) == ['a:one', 'b:two', 'c:three']


def test_multiple_stale_notations_are_sorted_and_deduped():
    """Several stale notations across profiles are reported once each, sorted."""
    sbp = {
        'implementation': {'defaults': [{'skill': 'z:retired'}, {'skill': 'a:retired'}]},
        'quality': {'defaults': [{'skill': 'a:retired'}]},
    }
    warnings = detect_stale_skills_by_profile('default', sbp, _none_live)
    assert len(warnings) == 1
    assert 'a:retired, z:retired' in warnings[0]


# =============================================================================
# Per-profile unresolved-vs-declared-minimal distinction
# =============================================================================
#
# A per-profile empty resolution (a profile block present in the map but with
# no defaults and no optionals) must be distinguishable from a deliberately
# MINIMAL profile that declares itself with ``"minimal": true``. Before the
# guard learned the distinction, a non-empty map whose one profile block was
# empty produced NO signal at all — the whole-map "missing or empty" branch did
# not fire, and an empty block contributes no notations to the stale check — so
# an unresolved profile and a deliberately-minimal one were byte-identical here.


def _map_with_empty_profile(*, declared_minimal: bool) -> dict:
    """Build a map with a populated ``implementation`` and an empty ``module_testing``.

    ``declared_minimal`` toggles the ``"minimal": true`` declaration on the
    empty ``module_testing`` block — the single bit that must separate a
    deliberately-minimal profile from an unmarked-empty one.
    """
    module_testing: dict = {'defaults': [], 'optionals': []}
    if declared_minimal:
        module_testing['minimal'] = True
    return {
        'implementation': {'defaults': [{'skill': _LIVE_NOTATION, 'description': 'core'}]},
        'module_testing': module_testing,
    }


def test_warns_on_unresolved_undeclared_empty_profile():
    """A present-but-empty profile with no minimal declaration surfaces the named condition.

    This is the empty-case assertion. It FAILS before the guard fix: the pre-fix
    function returns ``[]`` for a non-empty map whose ``module_testing`` block is
    empty, so the unresolved profile is invisible.
    """
    sbp = _map_with_empty_profile(declared_minimal=False)
    warnings = detect_stale_skills_by_profile('default', sbp, _all_live)
    assert any('module_testing' in w and 'not declared minimal' in w for w in warnings), warnings


def test_no_warning_on_declared_minimal_profile():
    """A present-but-empty profile that DECLARES minimality surfaces no condition — the escape hatch."""
    sbp = _map_with_empty_profile(declared_minimal=True)
    warnings = detect_stale_skills_by_profile('default', sbp, _all_live)
    assert not any('module_testing' in w for w in warnings), warnings


def test_declared_minimal_and_unmarked_empty_are_distinguishable():
    """The two states differ by exactly the declaration: one warns, the other does not.

    Both directions asserted together — the vacuous-guard trap this deliverable
    exists to close. An empty-only assertion cannot detect that the
    declared-minimal escape hatch silently swallowed the signal.
    """
    unmarked = detect_stale_skills_by_profile('default', _map_with_empty_profile(declared_minimal=False), _all_live)
    declared = detect_stale_skills_by_profile('default', _map_with_empty_profile(declared_minimal=True), _all_live)
    unmarked_condition = any('module_testing' in w and 'not declared minimal' in w for w in unmarked)
    declared_condition = any('module_testing' in w for w in declared)
    assert unmarked_condition and not declared_condition


# =============================================================================
# D6-S01: the declaration is the boolean ``True``, never mere truthiness
# =============================================================================
#
# ``_profile_declares_minimal`` compares with ``is True`` rather than reading the
# value for truthiness, and that choice is what keeps the marker fail-closed: a
# profile block carrying ``"minimal": "yes"`` has not declared anything the guard
# understands, so it must stay in the undeclared-empty state.
#
# The distinction is INVISIBLE to a test that only ever passes ``True`` or omits
# the key — a truthiness implementation (``if profile_data.get('minimal')``)
# satisfies both of those inputs identically. Only a truthy NON-boolean
# separates the two implementations, which is why the negative controls below
# are parametrised over one and each asserts its own truthiness first: a control
# value that turned out to be falsy would silence the condition for the wrong
# reason and the case would prove nothing.


#: Truthy values that are not the boolean ``True``. Every one of these silences
#: the condition under a truthiness implementation and must NOT silence it under
#: the identity comparison the guard actually uses.
_TRUTHY_NON_BOOLEANS = [1, 1.0, 'true', 'minimal', ['x'], {'declared': 'yes'}, (0,)]

#: Falsy values, including the explicit ``False`` refusal. None declares
#: minimality under either implementation — these are the shared-agreement
#: controls that keep the truthy set above from being the only evidence.
_FALSY_MINIMAL_VALUES = [False, 0, '', None, [], {}]


def _empty_profile_with_minimal_value(value) -> dict:
    """Build the empty-``module_testing`` map with ``minimal`` set to ``value``."""
    sbp = _map_with_empty_profile(declared_minimal=False)
    sbp['module_testing']['minimal'] = value
    return sbp


def _module_testing_condition_fired(sbp: dict) -> bool:
    """Whether the unresolved-profile condition surfaced for ``module_testing``."""
    warnings = detect_stale_skills_by_profile('default', sbp, _all_live)
    return any('module_testing' in w and 'not declared minimal' in w for w in warnings)


@pytest.mark.parametrize('truthy', _TRUTHY_NON_BOOLEANS, ids=repr)
def test_truthy_non_boolean_minimal_does_not_silence_the_condition(truthy):
    """A truthy non-boolean ``minimal`` leaves the profile undeclared-empty."""
    assert bool(truthy), 'control value must be truthy or the case proves nothing'
    assert _module_testing_condition_fired(_empty_profile_with_minimal_value(truthy))


@pytest.mark.parametrize('falsy', _FALSY_MINIMAL_VALUES, ids=repr)
def test_falsy_minimal_does_not_silence_the_condition(falsy):
    """A falsy ``minimal`` — including an explicit ``False`` — declares nothing."""
    assert not bool(falsy), 'control value must be falsy or the case proves nothing'
    assert _module_testing_condition_fired(_empty_profile_with_minimal_value(falsy))


def test_boolean_true_is_the_only_value_that_silences_the_condition():
    """The silencing set is DERIVED from the candidate population, not asserted.

    Partitioning the whole candidate set — ``True``, every truthy non-boolean,
    and every falsy value — and asserting the silencing partition is exactly
    ``[True]`` is what makes this a completeness claim rather than a sample. The
    population size rides with the verdict so a shrunken candidate list cannot
    quietly weaken the assertion.
    """
    candidates = [True, *_TRUTHY_NON_BOOLEANS, *_FALSY_MINIMAL_VALUES]
    silenced = [v for v in candidates if not _module_testing_condition_fired(_empty_profile_with_minimal_value(v))]

    assert len(candidates) == 1 + len(_TRUTHY_NON_BOOLEANS) + len(_FALSY_MINIMAL_VALUES)
    assert [type(v) for v in silenced] == [bool], silenced
    assert silenced == [True], silenced


# =============================================================================
# D6-S02: ``_emit_skills_by_profile_staleness_warning`` — the message on each
# branch, and the no-escaping-exception verdict
# =============================================================================
#
# The emitter is the read-path surface: ``get_module_info`` calls it on every
# module read, so a raise here would convert a non-blocking advisory into a
# broken read verb. Its three deferred imports (``marketplace_bundles`` twice,
# ``plan_logging`` once) are each guarded, and the guards are only observable if
# the test controls what those names resolve to — hence the injected modules
# below rather than a real bundle tree.


class _RecordingLogEntry:
    """Stand-in for ``plan_logging.log_entry`` that records every call."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def __call__(self, channel, plan_id, level, message):
        self.calls.append((channel, plan_id, level, message))

    @property
    def messages(self) -> list[str]:
        return [call[3] for call in self.calls]


@pytest.fixture
def recorded_log(monkeypatch):
    """Install a recording ``plan_logging`` for the emitter's deferred import."""
    recorder = _RecordingLogEntry()
    fake = types.ModuleType('plan_logging')
    fake.log_entry = recorder
    monkeypatch.setitem(sys.modules, 'plan_logging', fake)
    return recorder


def _install_registry(monkeypatch, *, live=(), root_raises=False):
    """Install a fake ``marketplace_bundles`` the emitter's deferred imports see.

    ``live`` is the set of ``bundle:skill`` notations whose SKILL.md "exists";
    ``root_raises`` makes ``resolve_bundles_root`` raise, which is the
    registry-unresolvable branch.
    """

    class _StubPath:
        def __init__(self, present: bool) -> None:
            self._present = present

        def exists(self) -> bool:
            return self._present

    def resolve_bundles_root(_start):
        if root_raises:
            raise RuntimeError('bundle root unresolvable')
        return Path('/nonexistent-bundles-root')

    def resolve_bundle_path(_root, bundle, relative):
        skill = relative.split('/')[1]
        return _StubPath(f'{bundle}:{skill}' in set(live))

    fake = types.ModuleType('marketplace_bundles')
    fake.resolve_bundles_root = resolve_bundles_root
    fake.resolve_bundle_path = resolve_bundle_path
    monkeypatch.setitem(sys.modules, 'marketplace_bundles', fake)


def test_emitter_logs_the_missing_map_message_with_the_full_log_signature(recorded_log, monkeypatch):
    """The empty-map branch logs exactly one WARNING carrying the ``[STALENESS]`` prefix."""
    _install_registry(monkeypatch)

    _emit_staleness_warning('mod-a', {'skills_by_profile': {}})

    assert len(recorded_log.calls) == 1
    channel, plan_id, level, message = recorded_log.calls[0]
    assert (channel, plan_id, level) == ('script', None, 'WARNING')
    assert message.startswith('[STALENESS] ')
    assert "module 'mod-a'" in message
    assert 'missing or empty' in message


def test_missing_map_message_needs_no_registry(recorded_log, monkeypatch):
    """The empty-map branch fires even when the registry root cannot be resolved.

    An empty map short-circuits before the ``resolve_bundles_root`` call, so a
    broken registry cannot suppress this signal.
    """
    _install_registry(monkeypatch, root_raises=True)

    _emit_staleness_warning('mod-a', {})

    assert [m for m in recorded_log.messages if 'missing or empty' in m]


def test_emitter_logs_the_unresolved_profile_message(recorded_log, monkeypatch):
    """A present-but-empty undeclared profile reaches the sink naming the profile."""
    _install_registry(monkeypatch, live={_LIVE_NOTATION})

    _emit_staleness_warning('mod-b', {'skills_by_profile': _map_with_empty_profile(declared_minimal=False)})

    assert len(recorded_log.calls) == 1
    message = recorded_log.messages[0]
    assert message.startswith('[STALENESS] ')
    assert "module 'mod-b'" in message
    assert "profile 'module_testing'" in message
    assert 'not declared minimal' in message


def test_emitter_logs_the_stale_notation_message(recorded_log, monkeypatch):
    """A notation the injected registry does not resolve reaches the sink by name."""
    _install_registry(monkeypatch, live={_LIVE_NOTATION})

    _emit_staleness_warning('mod-c', {'skills_by_profile': _profile_map(_LIVE_NOTATION, _STALE_NOTATION)})

    assert len(recorded_log.calls) == 1
    message = recorded_log.messages[0]
    assert _STALE_NOTATION in message
    assert 'absent from the live registry' in message
    assert _LIVE_NOTATION not in message


def test_emitter_logs_one_entry_per_condition_when_two_fire(recorded_log, monkeypatch):
    """Two independent conditions produce two separate sink entries, not one merged line."""
    sbp = _map_with_empty_profile(declared_minimal=False)
    sbp['implementation']['defaults'].append({'skill': _STALE_NOTATION})
    _install_registry(monkeypatch, live={_LIVE_NOTATION})

    _emit_staleness_warning('mod-d', {'skills_by_profile': sbp})

    assert len(recorded_log.calls) == 2
    assert any('not declared minimal' in m for m in recorded_log.messages)
    assert any('absent from the live registry' in m for m in recorded_log.messages)


def test_emitter_is_silent_on_a_clean_map(recorded_log, monkeypatch):
    """A fully-resolvable map with no empty profile reaches the sink zero times."""
    _install_registry(monkeypatch, live={_LIVE_NOTATION})

    _emit_staleness_warning('mod-e', {'skills_by_profile': _profile_map(_LIVE_NOTATION)})

    assert recorded_log.calls == []


def test_unresolvable_registry_suppresses_every_condition_on_a_non_empty_map(recorded_log, monkeypatch):
    """⚠ Documented DIVERGENCE between the guard's prose and its code.

    The module comment above ``_iter_skill_notations`` states that when the
    bundle root cannot be located "the stale-notation check is skipped, but the
    missing/empty and unresolved-profile checks still fire because they need no
    registry". The code does NOT do that: for a NON-empty map the emitter returns
    from inside the ``resolve_bundles_root`` guard before
    ``detect_stale_skills_by_profile`` is ever called, so the unresolved-profile
    condition is suppressed along with the stale-notation one.

    This test pins the OBSERVED behaviour and names the divergence rather than
    asserting the documented behaviour, because closing the gap is a production
    change this test-only task does not own. The divergence is reported as a
    finding; do not read this test as an endorsement of the current arm.
    """
    _install_registry(monkeypatch, root_raises=True)
    sbp = _map_with_empty_profile(declared_minimal=False)

    _emit_staleness_warning('mod-f', {'skills_by_profile': sbp})

    assert recorded_log.calls == []
    # The condition itself is real — the pure core surfaces it for the same map.
    assert _module_testing_condition_fired(sbp)


def test_no_exception_escapes_when_the_log_sink_raises(monkeypatch):
    """A raising ``log_entry`` is swallowed per message and the emitter returns None.

    The ``calls`` assertion is what keeps the verdict non-vacuous: without it, an
    emitter that produced no message at all would also "not raise".
    """
    calls: list[tuple] = []

    def exploding_log_entry(*args, **_kwargs):
        calls.append(args)
        raise RuntimeError('log sink unavailable')

    fake = types.ModuleType('plan_logging')
    fake.log_entry = exploding_log_entry
    monkeypatch.setitem(sys.modules, 'plan_logging', fake)
    _install_registry(monkeypatch, live={_LIVE_NOTATION})
    sbp = _map_with_empty_profile(declared_minimal=False)
    sbp['implementation']['defaults'].append({'skill': _STALE_NOTATION})

    assert _emit_staleness_warning('mod-g', {'skills_by_profile': sbp}) is None
    assert len(calls) == 2, 'both messages must have reached the raising sink'


def test_no_exception_escapes_when_the_log_module_is_unimportable(monkeypatch):
    """An unimportable ``plan_logging`` is swallowed too — the read path still returns."""
    monkeypatch.setitem(sys.modules, 'plan_logging', None)
    _install_registry(monkeypatch, live={_LIVE_NOTATION})
    sbp = _map_with_empty_profile(declared_minimal=False)

    assert _emit_staleness_warning('mod-h', {'skills_by_profile': sbp}) is None
    # The message existed — the swallowed failure was the sink, not an empty run.
    assert _module_testing_condition_fired(sbp)
