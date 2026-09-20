#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the template-content stamp and the sanctioned bootstrap verb.

Deliverable 2 of PLAN-03 (process-compliance): the generator-bootstrap
exception is narrowed to a detection-gated ``bootstrap`` verb, and
template-content staleness is detected via an embedded ``TEMPLATE_SHA256``
stamp instead of relying solely on version bumps (which missed the post-merge
stale-executor incident where the live executor ran pre-fix code).

Covers, each with a matched refusal-or-path pair:

- The stamp: the live template hashes to a 64-hex digest, and a freshly
  generated executor embeds that same digest (path); an executor generated
  before the stamp carries no digest and reads ``unknown`` (the measured
  absence, never a vacuous ``fresh``).
- ``bootstrap`` on an absent executor generates (fresh-clone path).
- ``bootstrap`` on an invalid executor regenerates (stale-cache path).
- ``bootstrap`` on a valid executor with a mismatched template hash
  regenerates (template-stale path).
- ``bootstrap`` on a valid, template-fresh executor refuses with
  ``action: not_needed`` (the proof the exception did not widen into general
  direct-path use).
- ``bootstrap`` on a valid executor with an unstampable side reports
  ``template_status: unknown`` and still refuses (unknown never drives a
  regeneration on its own).

All generation legs are monkeypatched — no executor is written and no
subprocess spawns; the decision table is what is pinned here.
"""

import argparse
import hashlib
from pathlib import Path

import pytest

from conftest import PROJECT_ROOT, load_script_module

_gen = load_script_module(
    'plan-marshall', 'tools-script-executor', 'generate_executor.py', 'gen_executor_template_bootstrap'
)

_TEMPLATE_PATH = (
    PROJECT_ROOT / 'marketplace/bundles/plan-marshall/skills/tools-script-executor/templates/execute-script.py.template'
)


def _ns(**overrides) -> argparse.Namespace:
    base = argparse.Namespace(marketplace=False, marketplace_root=None, target=None)
    for field, value in overrides.items():
        setattr(base, field, value)
    return base


class TestTemplateStamp:
    def test_live_template_hash_is_64_hex_and_matches_file_bytes(self):
        digest = _gen.current_template_sha256()
        assert len(digest) == 64
        int(digest, 16)
        assert digest == hashlib.sha256(_TEMPLATE_PATH.read_bytes()).hexdigest()

    def test_template_carries_the_stamp_placeholder(self):
        text = _TEMPLATE_PATH.read_text(encoding='utf-8')
        assert "TEMPLATE_SHA256 = '{{TEMPLATE_SHA256}}'" in text

    def test_missing_executor_reads_unknown(self, tmp_path, monkeypatch):
        monkeypatch.setattr(_gen, 'executor_path', lambda: tmp_path / 'execute-script.py')
        assert _gen.read_executor_template_sha() == ''

    def test_pre_stamp_executor_reads_unknown(self, tmp_path, monkeypatch):
        executor = tmp_path / 'execute-script.py'
        executor.write_text("MARSHALL_VERSION = '0.1.1'\nSCRIPTS = {}\n", encoding='utf-8')
        monkeypatch.setattr(_gen, 'executor_path', lambda: executor)
        assert _gen.read_executor_template_sha() == ''

    def test_stamped_executor_round_trips(self, tmp_path, monkeypatch):
        executor = tmp_path / 'execute-script.py'
        executor.write_text("TEMPLATE_SHA256 = 'abc123'\n", encoding='utf-8')
        monkeypatch.setattr(_gen, 'executor_path', lambda: executor)
        assert _gen.read_executor_template_sha() == 'abc123'


class TestBootstrapDecisions:
    def test_absent_executor_generates_fresh_clone_path(self, tmp_path, monkeypatch):
        monkeypatch.setattr(_gen, 'executor_path', lambda: tmp_path / 'execute-script.py')
        calls: list = []
        monkeypatch.setattr(_gen, 'cmd_generate', lambda args: calls.append(args) or {'status': 'success'})
        result = _gen.cmd_bootstrap(_ns())
        assert result['status'] == 'success'
        assert result['action'] == 'generated'
        assert result['reason'] == 'executor_absent'
        assert calls, 'bootstrap on an absent executor must generate'

    def test_absent_executor_generate_failure_is_visible(self, tmp_path, monkeypatch):
        monkeypatch.setattr(_gen, 'executor_path', lambda: tmp_path / 'execute-script.py')
        monkeypatch.setattr(_gen, 'cmd_generate', lambda args: {'status': 'error', 'error': 'boom'})
        result = _gen.cmd_bootstrap(_ns())
        assert result['status'] == 'error'
        assert result['action'] == 'failed'
        assert result['reason'] == 'executor_absent'

    def test_invalid_executor_regenerates_stale_cache_path(self, tmp_path, monkeypatch):
        executor = tmp_path / 'execute-script.py'
        executor.write_text('broken', encoding='utf-8')
        monkeypatch.setattr(_gen, 'executor_path', lambda: executor)
        monkeypatch.setattr(_gen, 'verify_executor', lambda *a, **k: (False, 0))
        calls: list = []
        monkeypatch.setattr(_gen, 'cmd_generate', lambda args: calls.append(args) or {'status': 'success'})
        result = _gen.cmd_bootstrap(_ns())
        assert result['status'] == 'success'
        assert result['action'] == 'generated'
        assert result['reason'] == 'executor_invalid'
        assert calls

    def test_template_stale_regenerates(self, tmp_path, monkeypatch):
        executor = tmp_path / 'execute-script.py'
        executor.write_text("TEMPLATE_SHA256 = 'old'\n", encoding='utf-8')
        monkeypatch.setattr(_gen, 'executor_path', lambda: executor)
        monkeypatch.setattr(_gen, 'verify_executor', lambda *a, **k: (True, 165))
        monkeypatch.setattr(_gen, 'read_executor_template_sha', lambda: 'old')
        monkeypatch.setattr(_gen, 'current_template_sha256', lambda: 'new')
        calls: list = []
        monkeypatch.setattr(_gen, 'cmd_generate', lambda args: calls.append(args) or {'status': 'success'})
        result = _gen.cmd_bootstrap(_ns())
        assert result['status'] == 'success'
        assert result['action'] == 'generated'
        assert result['reason'] == 'template_stale'
        assert result['template_status'] == 'stale'
        assert calls

    def test_fresh_executor_refuses_not_needed(self, tmp_path, monkeypatch):
        executor = tmp_path / 'execute-script.py'
        executor.write_text("TEMPLATE_SHA256 = 'same'\n", encoding='utf-8')
        monkeypatch.setattr(_gen, 'executor_path', lambda: executor)
        monkeypatch.setattr(_gen, 'verify_executor', lambda *a, **k: (True, 165))
        monkeypatch.setattr(_gen, 'read_executor_template_sha', lambda: 'same')
        monkeypatch.setattr(_gen, 'current_template_sha256', lambda: 'same')

        def _must_not_generate(args):
            raise AssertionError('bootstrap must not regenerate a fresh executor')

        monkeypatch.setattr(_gen, 'cmd_generate', _must_not_generate)
        result = _gen.cmd_bootstrap(_ns())
        assert result['status'] == 'success'
        assert result['action'] == 'not_needed'
        assert result['reason'] == 'executor_fresh'
        assert result['template_status'] == 'fresh'

    def test_unknown_hash_never_drives_regeneration(self, tmp_path, monkeypatch):
        executor = tmp_path / 'execute-script.py'
        executor.write_text("MARSHALL_VERSION = '0.1.1'\n", encoding='utf-8')
        monkeypatch.setattr(_gen, 'executor_path', lambda: executor)
        monkeypatch.setattr(_gen, 'verify_executor', lambda *a, **k: (True, 165))
        monkeypatch.setattr(_gen, 'read_executor_template_sha', lambda: '')

        def _must_not_generate(args):
            raise AssertionError('unknown staleness must not trigger a regeneration')

        monkeypatch.setattr(_gen, 'cmd_generate', _must_not_generate)
        result = _gen.cmd_bootstrap(_ns())
        assert result['status'] == 'success'
        assert result['action'] == 'not_needed'
        assert result['template_status'] == 'unknown'
        assert 'warning' in result


class TestBootstrapNamespaceContract:
    def test_production_bootstrap_namespace_carries_dry_run(self):
        """The regression the decision-table tests cannot see: they
        monkeypatch cmd_generate, so a bootstrap namespace missing
        ``dry_run`` still passes. Parse a real ``bootstrap`` argv through
        the module's own production parser and assert the field exists —
        ``cmd_generate`` dereferences ``args.dry_run`` directly, and without
        the parser default every regeneration-bound bootstrap run raised
        ``AttributeError`` on the fresh-clone path the verb exists for."""
        args = _gen.build_parser().parse_args(['bootstrap', '--marketplace'])
        assert args.func is _gen.cmd_bootstrap
        assert args.dry_run is False
