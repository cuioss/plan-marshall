#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
# ruff: noqa: I001
"""Tests for the plan-scoped security-skill resolver (``extension_api.py``).

The resolver aggregates each declared domain's profile-scoped skills (the
``security`` profile in the finalize-step use case) into a single deduped
``extra_security_skills`` map. Its two collaborators —
``require_references`` (reads ``references.json.domains``) and
``cmd_resolve_domain_skills`` (per-domain profile resolution, reused verbatim
from ``manage-config``) — are patched on the loaded module so the aggregation
logic is exercised in isolation, with no real ``marshal.json`` /
``references.json`` stack required.

Coverage:

- skill list lookup by domain — single domain, multiple-domain union,
  cross-domain dedup (first occurrence wins its description), and
  defaults-before-optionals precedence within a domain;
- empty / missing configuration — no ``domains`` key, empty ``domains`` list,
  and a missing ``references.json`` whose upstream error dict is propagated
  verbatim (with the per-domain resolver never consulted);
- invalid domain handling — a domain that resolves to ``status: error`` is
  swallowed as a graceful no-op, including the mixed valid/invalid case;
- TOON-format output — ``output_toon`` emits parseable TOON whose scalar and
  list fields round-trip and whose aggregated notations are present;
- the CLI argparse surface — required ``--plan-id`` / ``--profile`` and a
  required subcommand.
"""

from types import SimpleNamespace

import pytest

# conftest.py sets up the executor PYTHONPATH so the sibling script module
# (extension_api) and the shared cross-skill helpers import directly. The module
# object itself is imported so its module-level collaborators
# (``require_references`` / ``cmd_resolve_domain_skills``) can be monkeypatched.
import extension_api
from extension_api import (
    cmd_resolve_skills,
    resolve_security_skills,
)
from file_ops import output_toon
from toon_parser import parse_toon

from conftest import get_script_path, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'extension-api', 'extension_api.py')


# =============================================================================
# Test doubles for the two module-level collaborators
# =============================================================================


def _domain_success(defaults: dict | None = None, optionals: dict | None = None) -> dict:
    """Build a ``cmd_resolve_domain_skills`` success result.

    Mirrors the shape ``_cmd_skill_resolution.cmd_resolve_domain_skills``
    returns: ``status: success`` plus ``defaults`` / ``optionals`` notation ->
    description maps (the only fields the resolver reads).
    """
    return {
        'status': 'success',
        'defaults': defaults or {},
        'optionals': optionals or {},
    }


def _domain_error(message: str = 'Unknown domain') -> dict:
    """Build a ``cmd_resolve_domain_skills`` error result (graceful no-op input)."""
    return {'status': 'error', 'message': message}


def _patch_collaborators(monkeypatch, *, domains, domain_results):
    """Patch ``require_references`` and ``cmd_resolve_domain_skills`` on the module.

    ``require_references`` is replaced with a stub returning a references dict
    carrying *domains* (a successful ``references.json`` has no ``status`` key).
    ``cmd_resolve_domain_skills`` is replaced with a stub that dispatches on
    ``args.domain`` through *domain_results* (a domain absent from the map
    resolves to an error result, exercising the graceful-no-op path).
    """
    monkeypatch.setattr(
        extension_api,
        'require_references',
        lambda plan_id: {'domains': domains},
    )

    def _fake_resolve(args):
        return domain_results.get(args.domain, _domain_error(f'Unknown domain: {args.domain}'))

    monkeypatch.setattr(extension_api, 'cmd_resolve_domain_skills', _fake_resolve)


# =============================================================================
# Skill lookup by domain — success aggregation
# =============================================================================


class TestSkillLookupByDomain:
    """The resolver aggregates per-domain profile skills into one deduped map."""

    def test_single_domain_aggregates_defaults_and_optionals(self, monkeypatch):
        # Arrange
        _patch_collaborators(
            monkeypatch,
            domains=['python'],
            domain_results={
                'python': _domain_success(
                    defaults={'pm-dev-python:python-security': 'desc-default'},
                    optionals={'plan-marshall:persona-security-expert': 'desc-optional'},
                ),
            },
        )

        # Act
        result = resolve_security_skills('my-plan', 'security')

        # Assert
        assert result['status'] == 'success'
        assert result['plan_id'] == 'my-plan'
        assert result['profile'] == 'security'
        assert result['domains_resolved'] == ['python']
        assert result['extra_security_skills'] == {
            'pm-dev-python:python-security': 'desc-default',
            'plan-marshall:persona-security-expert': 'desc-optional',
        }

    def test_multiple_domains_union_preserves_domain_order(self, monkeypatch):
        # Arrange
        _patch_collaborators(
            monkeypatch,
            domains=['java', 'python'],
            domain_results={
                'java': _domain_success(defaults={'pm-dev-java:java-security': 'java-desc'}),
                'python': _domain_success(defaults={'pm-dev-python:python-security': 'python-desc'}),
            },
        )

        # Act
        result = resolve_security_skills('p', 'security')

        # Assert
        assert result['domains_resolved'] == ['java', 'python']
        assert result['extra_security_skills'] == {
            'pm-dev-java:java-security': 'java-desc',
            'pm-dev-python:python-security': 'python-desc',
        }

    def test_cross_domain_duplicate_keeps_first_domains_description(self, monkeypatch):
        # Arrange — both domains contribute the same shared notation; the first
        # domain in references order must win its description (setdefault).
        _patch_collaborators(
            monkeypatch,
            domains=['java', 'python'],
            domain_results={
                'java': _domain_success(defaults={'plan-marshall:persona-security-expert': 'from-java'}),
                'python': _domain_success(defaults={'plan-marshall:persona-security-expert': 'from-python'}),
            },
        )

        # Act
        result = resolve_security_skills('p', 'security')

        # Assert — one entry, first occurrence's description retained
        assert result['extra_security_skills'] == {
            'plan-marshall:persona-security-expert': 'from-java',
        }
        assert result['domains_resolved'] == ['java', 'python']

    def test_defaults_take_precedence_over_optionals_within_a_domain(self, monkeypatch):
        # Arrange — a notation present in BOTH defaults and optionals of one
        # domain keeps the defaults description (defaults iterated first).
        _patch_collaborators(
            monkeypatch,
            domains=['java'],
            domain_results={
                'java': _domain_success(
                    defaults={'pm-dev-java:java-security': 'from-defaults'},
                    optionals={'pm-dev-java:java-security': 'from-optionals'},
                ),
            },
        )

        # Act
        result = resolve_security_skills('p', 'security')

        # Assert
        assert result['extra_security_skills'] == {'pm-dev-java:java-security': 'from-defaults'}

    def test_profile_argument_is_forwarded_to_each_domain(self, monkeypatch):
        # Arrange — capture the args each per-domain resolution receives.
        seen = []
        monkeypatch.setattr(extension_api, 'require_references', lambda plan_id: {'domains': ['java', 'python']})

        def _capture(args):
            seen.append((args.domain, args.profile))
            return _domain_success()

        monkeypatch.setattr(extension_api, 'cmd_resolve_domain_skills', _capture)

        # Act
        resolve_security_skills('p', 'security')

        # Assert — each domain resolved against the requested profile
        assert seen == [('java', 'security'), ('python', 'security')]


# =============================================================================
# Empty and missing configuration
# =============================================================================


class TestEmptyAndMissingConfig:
    """Empty domain lists yield an empty aggregate; a missing references file
    propagates its upstream error verbatim."""

    def test_no_domains_key_yields_empty_aggregate(self, monkeypatch):
        # Arrange — references.json present but declares no domains key.
        monkeypatch.setattr(extension_api, 'require_references', lambda plan_id: {})
        monkeypatch.setattr(
            extension_api,
            'cmd_resolve_domain_skills',
            lambda args: pytest.fail('per-domain resolver must not run with no domains'),
        )

        # Act
        result = resolve_security_skills('p', 'security')

        # Assert
        assert result['status'] == 'success'
        assert result['domains_resolved'] == []
        assert result['extra_security_skills'] == {}

    def test_empty_domains_list_yields_empty_aggregate(self, monkeypatch):
        # Arrange
        _patch_collaborators(monkeypatch, domains=[], domain_results={})

        # Act
        result = resolve_security_skills('p', 'security')

        # Assert
        assert result['status'] == 'success'
        assert result['domains_resolved'] == []
        assert result['extra_security_skills'] == {}

    def test_missing_references_propagates_error_verbatim(self, monkeypatch):
        # Arrange — require_references signals file_not_found; the per-domain
        # resolver must never be consulted on the error path.
        error_dict = {
            'status': 'error',
            'plan_id': 'p',
            'error': 'file_not_found',
            'message': 'references.json not found',
        }
        monkeypatch.setattr(extension_api, 'require_references', lambda plan_id: error_dict)
        monkeypatch.setattr(
            extension_api,
            'cmd_resolve_domain_skills',
            lambda args: pytest.fail('per-domain resolver must not run when references are missing'),
        )

        # Act
        result = resolve_security_skills('p', 'security')

        # Assert — the upstream error dict is returned unchanged
        assert result is error_dict
        assert result['status'] == 'error'
        assert result['error'] == 'file_not_found'


# =============================================================================
# Invalid domain handling — graceful no-op
# =============================================================================


class TestInvalidDomainHandling:
    """A domain that declares no matching profile (or is otherwise
    unresolvable) is swallowed as a graceful no-op."""

    def test_unresolvable_domain_is_skipped(self, monkeypatch):
        # Arrange — the only domain resolves to an error.
        _patch_collaborators(
            monkeypatch,
            domains=['ghost'],
            domain_results={'ghost': _domain_error('Unknown domain: ghost')},
        )

        # Act
        result = resolve_security_skills('p', 'security')

        # Assert — error domain contributes nothing and is not marked resolved
        assert result['status'] == 'success'
        assert result['domains_resolved'] == []
        assert result['extra_security_skills'] == {}

    def test_mixed_valid_and_invalid_domains(self, monkeypatch):
        # Arrange — a valid domain, an error domain, then another valid domain.
        _patch_collaborators(
            monkeypatch,
            domains=['java', 'ghost', 'python'],
            domain_results={
                'java': _domain_success(defaults={'pm-dev-java:java-security': 'java-desc'}),
                'ghost': _domain_error(),
                'python': _domain_success(defaults={'pm-dev-python:python-security': 'python-desc'}),
            },
        )

        # Act
        result = resolve_security_skills('p', 'security')

        # Assert — only the valid domains contribute, in references order
        assert result['domains_resolved'] == ['java', 'python']
        assert result['extra_security_skills'] == {
            'pm-dev-java:java-security': 'java-desc',
            'pm-dev-python:python-security': 'python-desc',
        }

    def test_resolved_domain_with_no_skills_is_still_marked_resolved(self, monkeypatch):
        # Arrange — a success result that contributes zero skills still counts
        # as resolved (the discriminator is status, not skill count).
        _patch_collaborators(
            monkeypatch,
            domains=['empty-domain'],
            domain_results={'empty-domain': _domain_success()},
        )

        # Act
        result = resolve_security_skills('p', 'security')

        # Assert
        assert result['domains_resolved'] == ['empty-domain']
        assert result['extra_security_skills'] == {}


# =============================================================================
# CLI handler passthrough
# =============================================================================


class TestCmdHandlerPassthrough:
    """``cmd_resolve_skills`` forwards ``plan_id`` and ``profile`` from argparse
    namespace to the aggregation function."""

    def test_handler_forwards_plan_id_and_profile(self, monkeypatch):
        # Arrange
        _patch_collaborators(
            monkeypatch,
            domains=['java'],
            domain_results={'java': _domain_success(defaults={'pm-dev-java:java-security': 'd'})},
        )

        # Act
        result = cmd_resolve_skills(SimpleNamespace(plan_id='plan-xyz', profile='security'))

        # Assert
        assert result['plan_id'] == 'plan-xyz'
        assert result['profile'] == 'security'
        assert result['extra_security_skills'] == {'pm-dev-java:java-security': 'd'}


# =============================================================================
# TOON-format output
# =============================================================================


class TestToonOutput:
    """``output_toon`` emits parseable TOON; scalar and list fields round-trip
    and every aggregated notation is present in the serialized text."""

    def test_result_emits_parseable_toon_with_roundtrip_scalars(self, monkeypatch, capsys):
        # Arrange
        _patch_collaborators(
            monkeypatch,
            domains=['java', 'python'],
            domain_results={
                'java': _domain_success(
                    defaults={'pm-dev-java:java-security': 'Use when hardening Java: input validation'},
                ),
                'python': _domain_success(
                    defaults={'pm-dev-python:python-security': 'Use when hardening Python: injection sinks'},
                ),
            },
        )
        result = resolve_security_skills('my-plan', 'security')

        # Act — emit via the same helper the CLI uses, then re-parse stdout.
        output_toon(result)
        captured = capsys.readouterr().out
        parsed = parse_toon(captured)

        # Assert — scalar and list fields survive a TOON round-trip.
        assert parsed['status'] == 'success'
        assert parsed['plan_id'] == 'my-plan'
        assert parsed['profile'] == 'security'
        assert parsed['domains_resolved'] == ['java', 'python']

        # The aggregated notations and their descriptions are present in the
        # serialized payload. The map is emitted as a nested TOON object keyed by
        # notation; the notation keys themselves contain ':' (a TOON key/value
        # separator) so the nested map is asserted by substring presence rather
        # than by a full dict round-trip the format cannot provide for
        # colon-bearing keys.
        assert 'extra_security_skills:' in captured
        assert 'pm-dev-java:java-security' in captured
        assert 'pm-dev-python:python-security' in captured
        assert 'input validation' in captured
        assert 'injection sinks' in captured

    def test_empty_aggregate_emits_parseable_toon(self, monkeypatch, capsys):
        # Arrange
        _patch_collaborators(monkeypatch, domains=[], domain_results={})
        result = resolve_security_skills('p', 'security')

        # Act
        output_toon(result)
        parsed = parse_toon(capsys.readouterr().out)

        # Assert
        assert parsed['status'] == 'success'
        assert parsed['domains_resolved'] == []


# =============================================================================
# CLI argparse surface
# =============================================================================


class TestCliArgparseSurface:
    """The ``resolve-skills`` subcommand requires ``--plan-id`` and
    ``--profile``; a subcommand is mandatory."""

    def test_missing_profile_is_rejected(self):
        # Act
        result = run_script(SCRIPT_PATH, 'resolve-skills', '--plan-id', 'p')

        # Assert
        assert not result.success

    def test_missing_plan_id_is_rejected(self):
        # Act
        result = run_script(SCRIPT_PATH, 'resolve-skills', '--profile', 'security')

        # Assert
        assert not result.success

    def test_missing_subcommand_is_rejected(self):
        # Act
        result = run_script(SCRIPT_PATH)

        # Assert
        assert not result.success
