# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001, E402
"""Regression tests for the declarative rule registry (``_rule_registry.py``).

D4 replaces three hand-maintained sets — ``_analyze.__all__``, the
``doctor-marketplace.py::_OPTIN_RULE_NAMES`` literal, and the ``active_rules``
gating literals — with pure functions of a descriptor registry. Each
rule-bearing ``_analyze_*.py`` module exposes a module-level ``RULE_DESCRIPTOR``
(or a ``RULE_DESCRIPTORS`` list for multi-rule modules); ``_rule_registry.py``
imports every such module and collects its descriptor(s).

The HARD acceptance contract these tests pin:

1. Descriptor schema — every collected descriptor is a frozen ``RuleDescriptor``
   with a non-empty ``rule_id``, a known ``severity`` / ``category``, a ``scope``
   in ``{file-local, corpus-relational}``, and boolean ``opt_in`` /
   ``default_on`` / ``has_fixer`` flags.
2. No duplicate ``rule_id`` across the registry; the collector raises
   ``ValueError`` on a collision rather than silently shadowing.
3. The descriptor-derived opt-in set is byte-identical to the prior literal
   ``frozenset({'argument_naming', 'verb_chain', 'script_call_drift'})``, and
   the value ``doctor-marketplace.py`` consumes (``_OPTIN_RULE_NAMES``) is the
   same derived set.
4. The derived opt-in set drives byte-identical active-rule gating through
   ``doctor-marketplace.py``'s ``_parse_rules_flag`` / ``_resolve_active_rules``.
5. Every module in ``_DESCRIPTOR_MODULES`` contributes at least one descriptor
   (every rule-bearing analyzer exposes a descriptor).
"""

from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

import pytest

from conftest import get_scripts_dir, load_script_module

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
# Inserted on sys.path so the analyzer modules' intra-bundle
# ``from _rule_registry import RuleDescriptor`` and sibling ``from _analyze_*
# import ...`` references resolve when the registry imports them.
SCRIPTS_DIR = get_scripts_dir('pm-plugin-development', 'plugin-doctor')
# file_ops lives in plan-marshall; needed so loading doctor-marketplace.py
# (``from file_ops import ...``) succeeds.
_FILE_OPS_DIR = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'tools-file-ops'
    / 'scripts'
)
sys.path.insert(0, str(SCRIPTS_DIR))
sys.path.insert(0, str(_FILE_OPS_DIR))


# The pre-D4 hand-maintained opt-in literal, captured verbatim from the prior
# ``doctor-marketplace.py::_OPTIN_RULE_NAMES``. This is the byte-identical
# regression target the derivation must reproduce.
PRIOR_OPTIN_RULE_NAMES = frozenset({'argument_naming', 'verb_chain', 'script_call_drift'})

VALID_SCOPES = frozenset({'file-local', 'corpus-relational'})
VALID_SEVERITIES = frozenset({'error', 'warning', 'info', 'tip'})
VALID_CATEGORIES = frozenset({'structural', 'content', 'style', 'safety'})


def _load_registry():
    """Load ``_rule_registry.py`` under its canonical name.

    Registering under ``_rule_registry`` (not an alias) means the analyzer
    modules the collector imports resolve ``from _rule_registry import
    RuleDescriptor`` to THIS instance, so ``isinstance(d, reg.RuleDescriptor)``
    holds for every collected descriptor. ``load_script_module`` re-execs the
    module, resetting the lazy ``_REGISTRY`` cache to ``None``.
    """
    return load_script_module(
        'pm-plugin-development', 'plugin-doctor', '_rule_registry.py', '_rule_registry'
    )


def _load_doctor_marketplace():
    return load_script_module(
        'pm-plugin-development',
        'plugin-doctor',
        'doctor-marketplace.py',
        '_doctor_marketplace_under_test',
    )


# =============================================================================
# Descriptor schema
# =============================================================================


def test_registry_builds_non_empty():
    """``get_registry`` returns a non-empty tuple of descriptors."""
    reg = _load_registry()
    registry = reg.get_registry()
    assert isinstance(registry, tuple)
    assert registry, 'the rule registry must collect at least one descriptor'


def test_registry_cached_on_repeat_access():
    """The registry is built once and returned by identity on repeat access."""
    reg = _load_registry()
    first = reg.get_registry()
    second = reg.get_registry()
    assert first is second, 'get_registry must memoise the built registry'


def test_rule_descriptor_is_frozen():
    """``RuleDescriptor`` is a frozen dataclass — fields cannot be reassigned."""
    reg = _load_registry()
    descriptor = reg.RuleDescriptor(
        rule_id='example',
        severity='error',
        category='structural',
        scope=reg.SCOPE_FILE_LOCAL,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        descriptor.rule_id = 'mutated'  # type: ignore[misc]


def test_scope_constants_are_the_two_runner_dispatch_values():
    """The two scope constants are exactly the runner's dispatch vocabulary."""
    reg = _load_registry()
    assert reg.SCOPE_FILE_LOCAL == 'file-local'
    assert reg.SCOPE_CORPUS_RELATIONAL == 'corpus-relational'
    assert {reg.SCOPE_FILE_LOCAL, reg.SCOPE_CORPUS_RELATIONAL} == VALID_SCOPES


def test_every_descriptor_has_a_valid_schema():
    """Each collected descriptor carries well-typed, in-vocabulary fields."""
    reg = _load_registry()
    for descriptor in reg.get_registry():
        # Duck-type the descriptor class rather than asserting strict identity:
        # under pytest-xdist the analyzer modules may have been imported against
        # a different in-process ``_rule_registry`` instance than this freshly
        # loaded one, so ``isinstance`` against ``reg.RuleDescriptor`` is an
        # artifact of module-reload identity, not a schema property. The
        # structural checks below are the real contract.
        assert dataclasses.is_dataclass(descriptor)
        assert type(descriptor).__name__ == 'RuleDescriptor', (
            f'expected a RuleDescriptor, got {type(descriptor).__name__}'
        )
        assert isinstance(descriptor.rule_id, str) and descriptor.rule_id, (
            f'rule_id must be a non-empty string: {descriptor!r}'
        )
        assert descriptor.severity in VALID_SEVERITIES, (
            f'{descriptor.rule_id}: unknown severity {descriptor.severity!r}'
        )
        assert descriptor.category in VALID_CATEGORIES, (
            f'{descriptor.rule_id}: unknown category {descriptor.category!r}'
        )
        assert descriptor.scope in VALID_SCOPES, (
            f'{descriptor.rule_id}: scope must be file-local or corpus-relational, '
            f'got {descriptor.scope!r}'
        )
        assert isinstance(descriptor.opt_in, bool)
        assert isinstance(descriptor.default_on, bool)
        assert isinstance(descriptor.has_fixer, bool)


# =============================================================================
# Uniqueness / collision handling
# =============================================================================


def test_no_duplicate_rule_ids_in_registry():
    """Every ``rule_id`` in the collected registry is unique."""
    reg = _load_registry()
    rule_ids = [descriptor.rule_id for descriptor in reg.get_registry()]
    duplicates = sorted({rid for rid in rule_ids if rule_ids.count(rid) > 1})
    assert not duplicates, f'duplicate rule_id(s) collected by the registry: {duplicates}'
    assert len(rule_ids) == len(set(rule_ids))


def test_build_registry_rejects_duplicate_rule_id(monkeypatch):
    """A copy-paste descriptor collision fails loudly instead of shadowing."""
    reg = _load_registry()
    dup = reg.RuleDescriptor(
        rule_id='dup-rule',
        severity='error',
        category='structural',
        scope=reg.SCOPE_FILE_LOCAL,
    )
    monkeypatch.setattr(reg, '_DESCRIPTOR_MODULES', ('mod_a', 'mod_b'))
    monkeypatch.setattr(reg, '_descriptors_for_module', lambda _name: [dup])
    with pytest.raises(ValueError, match='duplicate rule_id'):
        reg._build_registry()


# =============================================================================
# Module coverage — every rule-bearing analyzer exposes a descriptor
# =============================================================================


def test_every_descriptor_module_contributes_at_least_one():
    """Each module in ``_DESCRIPTOR_MODULES`` declares at least one descriptor."""
    reg = _load_registry()
    missing = [
        name for name in reg._DESCRIPTOR_MODULES if not reg._descriptors_for_module(name)
    ]
    assert not missing, (
        f'rule-bearing modules exposing no RULE_DESCRIPTOR(S): {missing}'
    )


def test_descriptor_modules_are_unique_and_sorted():
    """The descriptor-module roster carries no duplicates and is sorted."""
    reg = _load_registry()
    modules = list(reg._DESCRIPTOR_MODULES)
    assert len(modules) == len(set(modules)), 'duplicate module in _DESCRIPTOR_MODULES'
    assert modules == sorted(modules), '_DESCRIPTOR_MODULES must stay in sorted order'


# =============================================================================
# Opt-in derivation — byte-identical to the prior literal
# =============================================================================


def test_optin_rule_names_matches_prior_literal():
    """The descriptor-derived opt-in set equals the pre-D4 hand-maintained literal."""
    reg = _load_registry()
    assert reg.optin_rule_names() == PRIOR_OPTIN_RULE_NAMES


def test_optin_rule_names_returns_frozenset():
    """``optin_rule_names`` returns a frozenset (immutable, matching the literal)."""
    reg = _load_registry()
    assert isinstance(reg.optin_rule_names(), frozenset)


def test_opt_in_descriptors_are_exactly_the_prior_set():
    """The set of descriptors flagged ``opt_in`` equals the prior opt-in literal."""
    reg = _load_registry()
    opt_in_ids = {descriptor.rule_id for descriptor in reg.get_registry() if descriptor.opt_in}
    assert opt_in_ids == PRIOR_OPTIN_RULE_NAMES


def test_non_opt_in_descriptors_are_excluded_from_the_optin_set():
    """No ``opt_in=False`` descriptor leaks into the derived opt-in set."""
    reg = _load_registry()
    derived = reg.optin_rule_names()
    for descriptor in reg.get_registry():
        if not descriptor.opt_in:
            assert descriptor.rule_id not in derived, (
                f'{descriptor.rule_id} is opt_in=False but appears in the derived opt-in set'
            )


# =============================================================================
# Active-rule gating — derived set drives byte-identical behaviour
# =============================================================================


def test_doctor_marketplace_optin_names_are_the_derived_set():
    """``doctor-marketplace.py`` consumes the registry-derived opt-in set."""
    doctor = _load_doctor_marketplace()
    assert doctor._OPTIN_RULE_NAMES == PRIOR_OPTIN_RULE_NAMES


def test_parse_rules_flag_accepts_every_opt_in_token():
    """Every derived opt-in token survives ``_parse_rules_flag`` selection."""
    doctor = _load_doctor_marketplace()
    selected = doctor._parse_rules_flag('argument_naming,verb_chain,script_call_drift')
    assert selected == PRIOR_OPTIN_RULE_NAMES


def test_parse_rules_flag_selects_a_single_token():
    """A single opt-in token resolves to exactly that rule."""
    doctor = _load_doctor_marketplace()
    assert doctor._parse_rules_flag('script_call_drift') == frozenset({'script_call_drift'})


def test_parse_rules_flag_drops_unknown_tokens():
    """An unknown ``--rules`` token is filtered out against the derived set."""
    doctor = _load_doctor_marketplace()
    assert doctor._parse_rules_flag('not_a_real_rule') == frozenset()
    # A valid token in the same invocation still activates; the unknown is dropped.
    assert doctor._parse_rules_flag('verb_chain,not_a_real_rule') == frozenset({'verb_chain'})


def test_parse_rules_flag_empty_input_is_empty_set():
    """Absent / empty ``--rules`` yields the empty active set."""
    doctor = _load_doctor_marketplace()
    assert doctor._parse_rules_flag(None) == frozenset()
    assert doctor._parse_rules_flag('') == frozenset()


def test_resolve_active_rules_unions_aliases_with_rules_flag():
    """The alias flags desugar into the derived opt-in tokens and union in."""
    import types

    doctor = _load_doctor_marketplace()
    args = types.SimpleNamespace(
        rules='script_call_drift',
        enable_argument_naming=True,
        enable_verb_chain=True,
    )
    resolved = doctor._resolve_active_rules(args)
    assert set(resolved) == {'script_call_drift', 'argument_naming', 'verb_chain'}


def test_resolve_active_rules_without_opt_in_is_empty():
    """No ``--rules`` and no alias flags keeps every opt-in cluster silent."""
    import types

    doctor = _load_doctor_marketplace()
    args = types.SimpleNamespace(
        rules=None,
        enable_argument_naming=False,
        enable_verb_chain=False,
    )
    assert doctor._resolve_active_rules(args) == frozenset()
