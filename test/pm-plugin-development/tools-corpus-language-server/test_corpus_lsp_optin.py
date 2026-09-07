#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""D4: the opt-in gate, verified on an UNCONFIGURED project.

The plan requires that an unconfigured project's behaviour be *verified* rather
than asserted, so the unconfigured path is the subject of these tests: the
server must start, advertise no capabilities, and answer every request emptily.
"""

from __future__ import annotations

import json
from pathlib import Path

from test_corpus_index import build_corpus

from conftest import load_script_module

corpus_lsp = load_script_module(
    'pm-plugin-development', 'tools-corpus-language-server', 'corpus_lsp.py'
)


def _project(root: Path, marshal: dict | None) -> Path:
    """Create a project tree; ``marshal=None`` means no marshal.json at all."""
    (root / 'marketplace').mkdir(parents=True, exist_ok=True)
    corpus_root = build_corpus(root)
    (root / 'marketplace' / 'bundles').mkdir(parents=True, exist_ok=True)
    for child in corpus_root.iterdir():
        child.rename(root / 'marketplace' / 'bundles' / child.name)
    if marshal is not None:
        plan_dir = root / '.plan'
        plan_dir.mkdir(parents=True, exist_ok=True)
        (plan_dir / 'marshal.json').write_text(json.dumps(marshal), encoding='utf-8')
    return root


ENABLED = {'code_intelligence': {'corpus_language_server': {'enabled': True}}}


class TestConfigFailsClosed:
    """Every unreadable or ambiguous configuration must resolve to DISABLED."""

    def test_no_project_root_is_disabled(self) -> None:
        assert corpus_lsp.read_corpus_config(None) == {'enabled': False}

    def test_absent_marshal_is_disabled(self, tmp_path: Path) -> None:
        assert corpus_lsp.read_corpus_config(tmp_path)['enabled'] is False

    def test_malformed_marshal_is_disabled(self, tmp_path: Path) -> None:
        (tmp_path / '.plan').mkdir()
        (tmp_path / '.plan' / 'marshal.json').write_text('{not json', encoding='utf-8')
        assert corpus_lsp.read_corpus_config(tmp_path)['enabled'] is False

    def test_absent_section_is_disabled(self, tmp_path: Path) -> None:
        _project(tmp_path, {'plan': {}})
        assert corpus_lsp.read_corpus_config(tmp_path)['enabled'] is False

    def test_explicit_false_is_disabled(self, tmp_path: Path) -> None:
        _project(tmp_path, {'code_intelligence': {'corpus_language_server': {'enabled': False}}})
        assert corpus_lsp.read_corpus_config(tmp_path)['enabled'] is False

    def test_non_boolean_true_is_disabled(self, tmp_path: Path) -> None:
        """A truthy string must NOT enable the surface — only a real `true` does."""
        _project(tmp_path, {'code_intelligence': {'corpus_language_server': {'enabled': 'yes'}}})
        assert corpus_lsp.read_corpus_config(tmp_path)['enabled'] is False

    def test_explicit_true_enables(self, tmp_path: Path) -> None:
        _project(tmp_path, ENABLED)
        assert corpus_lsp.read_corpus_config(tmp_path)['enabled'] is True


class TestUnconfiguredProjectIsANoOp:
    """The documented no-op path, exercised end to end on an unconfigured tree."""

    def test_advertises_no_capabilities(self, tmp_path: Path) -> None:
        _project(tmp_path, None)
        rpc, _ = corpus_lsp.build_server(None, {'enabled': False})
        response = rpc.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}})
        assert response is not None
        assert response['result']['capabilities'] == {}

    def test_definition_returns_nothing(self, tmp_path: Path) -> None:
        root = _project(tmp_path, None)
        _, corpus = corpus_lsp.build_server(None, {'enabled': False})
        skill = root / 'marketplace' / 'bundles' / 'beta' / 'skills' / 'caller' / 'SKILL.md'
        params = {
            'textDocument': {'uri': skill.as_uri()},
            'position': {'line': 6, 'character': 15},
        }
        assert corpus.on_definition(params) is None

    def test_references_returns_empty(self, tmp_path: Path) -> None:
        root = _project(tmp_path, None)
        _, corpus = corpus_lsp.build_server(None, {'enabled': False})
        skill = root / 'marketplace' / 'bundles' / 'beta' / 'skills' / 'caller' / 'SKILL.md'
        params = {
            'textDocument': {'uri': skill.as_uri()},
            'position': {'line': 6, 'character': 15},
        }
        assert corpus.on_references(params) == []

    def test_hover_returns_nothing(self, tmp_path: Path) -> None:
        root = _project(tmp_path, None)
        _, corpus = corpus_lsp.build_server(None, {'enabled': False})
        skill = root / 'marketplace' / 'bundles' / 'beta' / 'skills' / 'caller' / 'SKILL.md'
        params = {
            'textDocument': {'uri': skill.as_uri()},
            'position': {'line': 6, 'character': 15},
        }
        assert corpus.on_hover(params) is None

    def test_no_index_is_ever_built(self, tmp_path: Path) -> None:
        """The ~1.9 s index cost must not be paid by a project that opted out."""
        _project(tmp_path, None)
        _, corpus = corpus_lsp.build_server(None, {'enabled': False})
        assert corpus.index is None

    def test_preflight_reports_the_opt_out(self, tmp_path: Path) -> None:
        _project(tmp_path, None)
        args = type('A', (), {'project_path': str(tmp_path)})()
        payload = corpus_lsp.cmd_preflight(args)
        assert payload['status'] == 'degraded'
        assert payload['state'] == 'not_configured'
        assert payload['provider_count'] == 0
        assert payload['fallback'] == 'read_grep'

    def test_query_degrades_without_touching_the_corpus(self, tmp_path: Path) -> None:
        _project(tmp_path, None)
        args = type('A', (), {'project_path': str(tmp_path), 'kind': 'definition', 'notation': 'alpha:target-skill'})()
        payload = corpus_lsp.cmd_query(args)
        assert payload['status'] == 'degraded'
        assert payload['provider_count'] == 0
        assert 'definition' not in payload


class TestConfiguredProjectAnswers:
    """The configured path — so an empty answer above is a real opt-out, not a broken build."""

    def test_advertises_capabilities(self, tmp_path: Path) -> None:
        _project(tmp_path, ENABLED)
        rpc, _ = corpus_lsp.build_server(tmp_path, {'enabled': True})
        response = rpc.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}})
        assert response is not None
        capabilities = response['result']['capabilities']
        assert capabilities['definitionProvider'] is True
        assert capabilities['referencesProvider'] is True
        assert capabilities['hoverProvider'] is True

    def test_does_not_advertise_diagnostics(self, tmp_path: Path) -> None:
        """D3 is hard-gated: no diagnostic provider may be advertised yet."""
        _project(tmp_path, ENABLED)
        rpc, _ = corpus_lsp.build_server(tmp_path, {'enabled': True})
        response = rpc.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}})
        assert response is not None
        capabilities = response['result']['capabilities']
        assert 'diagnosticProvider' not in capabilities

    def test_definition_resolves_from_a_cursor(self, tmp_path: Path) -> None:
        root = _project(tmp_path, ENABLED)
        _, corpus = corpus_lsp.build_server(root, {'enabled': True})
        skill = root / 'marketplace' / 'bundles' / 'beta' / 'skills' / 'caller' / 'SKILL.md'
        line_no = skill.read_text(encoding='utf-8').split('\n').index('See Skill: alpha:target-skill for details.')
        params = {
            'textDocument': {'uri': skill.as_uri()},
            'position': {'line': line_no, 'character': 15},
        }
        result = corpus.on_definition(params)
        assert result is not None
        assert result['uri'].endswith('alpha/skills/target-skill/SKILL.md')

    def test_hover_renders_markdown(self, tmp_path: Path) -> None:
        root = _project(tmp_path, ENABLED)
        _, corpus = corpus_lsp.build_server(root, {'enabled': True})
        skill = root / 'marketplace' / 'bundles' / 'beta' / 'skills' / 'caller' / 'SKILL.md'
        line_no = skill.read_text(encoding='utf-8').split('\n').index('See Skill: alpha:target-skill for details.')
        params = {
            'textDocument': {'uri': skill.as_uri()},
            'position': {'line': line_no, 'character': 15},
        }
        result = corpus.on_hover(params)
        assert result is not None
        assert 'The skill under test' in result['contents']['value']

    def test_index_is_built_once_and_reused(self, tmp_path: Path) -> None:
        """Residency is the design — a second query must not rebuild the index."""
        root = _project(tmp_path, ENABLED)
        _, corpus = corpus_lsp.build_server(root, {'enabled': True})
        first = corpus.index
        assert first is not None
        assert corpus.index is first


class TestEnabledCliVerbPayloads:
    """D6-S04 — the ENABLED half of the documented coverage contract.

    ``SKILL.md`` § "The coverage contract (no silent empty result)" publishes a
    three-row table of ``(state, provider_count, status)`` triples, and every
    payload assertion in this module covered exactly ONE row of it: the
    ``not_configured / 0 / degraded`` opt-out. The ``ready`` and ``ok`` rows —
    the ones a consumer routes on when the surface actually answers — had no
    assertion anywhere, so a verb that dropped ``provider_count`` or renamed
    ``state`` on the success path broke the published contract with the suite
    still green.

    The per-kind key sets are asserted as SETS rather than by spot-checking one
    key each: a payload that quietly lost ``completeness_note`` or gained an
    undocumented key is the drift this section exists to catch, and a
    ``key in payload`` assertion cannot see either.
    """

    #: The triple every documented row is keyed on, and the two fields the
    #: enabled rows add. Named once so the per-kind sets below differ only in
    #: their own kind-specific keys.
    _CONTRACT_KEYS = frozenset({'status', 'state', 'provider_count'})
    _QUERY_COMMON_KEYS = _CONTRACT_KEYS | {'kind', 'notation', 'known'}

    @staticmethod
    def _args(root: Path, **extra):
        return type('A', (), {'project_path': str(root), **extra})()

    def test_preflight_ready_row_of_the_documented_contract(self, tmp_path: Path) -> None:
        """The ``ready / 1 / success`` row, plus the capabilities it advertises."""
        _project(tmp_path, ENABLED)
        payload = corpus_lsp.cmd_preflight(self._args(tmp_path))

        assert (payload['state'], payload['provider_count'], payload['status']) == ('ready', 1, 'success')
        assert payload['configured'] is True
        assert set(payload['capabilities']) >= {'definitionProvider', 'referencesProvider', 'hoverProvider'}
        assert 'diagnosticProvider' not in payload['capabilities']
        # "plus index coverage figures" — asserted as the documented CLAIM (there
        # are extra figures) rather than as a hand-copied key list that would
        # freeze the index's own stats surface from here.
        extras = set(payload) - (self._CONTRACT_KEYS | {'configured', 'capabilities'})
        assert extras, 'the ready payload carries no index coverage figures at all'

    def test_query_definition_payload_keys(self, tmp_path: Path) -> None:
        _project(tmp_path, ENABLED)
        payload = corpus_lsp.cmd_query(
            self._args(tmp_path, kind='definition', notation='alpha:target-skill')
        )

        assert (payload['state'], payload['provider_count'], payload['status']) == ('ok', 1, 'success')
        assert set(payload) == self._QUERY_COMMON_KEYS | {'definition'}
        assert payload['known'] is True
        assert payload['definition'] is not None

    def test_query_references_payload_keys_carry_the_completeness_bound(self, tmp_path: Path) -> None:
        """``references`` adds three keys, and the bound is one of them.

        ``completeness_note`` is the field the SKILL's prohibited-actions block
        rests on ("do not read an empty ``references[]`` as 'the corpus contains
        no reference'"). Nothing asserted it was emitted, so the bound could be
        dropped from the payload while the prose kept promising it.

        The documented triple and ``known`` are asserted alongside it, matching
        the ``definition`` sibling above. Without them the three readings below
        say nothing about whether the query SUCCEEDED: they are self-consistent
        within the payload, so an ``ok``-shaped answer for a notation the index
        does not know (``known: False``, an empty ``references[]``, ``0 == 0``,
        the same note) satisfies every one of them.
        """
        _project(tmp_path, ENABLED)
        payload = corpus_lsp.cmd_query(
            self._args(tmp_path, kind='references', notation='alpha:target-skill')
        )

        assert (payload['state'], payload['provider_count'], payload['status']) == ('ok', 1, 'success')
        assert set(payload) == self._QUERY_COMMON_KEYS | {
            'references',
            'reference_count',
            'verified_count',
            'completeness_note',
        }
        assert payload['known'] is True
        assert payload['reference_count'] == len(payload['references'])
        assert payload['verified_count'] <= payload['reference_count']
        assert 'index coverage' in payload['completeness_note']

    def test_query_hover_payload_keys(self, tmp_path: Path) -> None:
        _project(tmp_path, ENABLED)
        payload = corpus_lsp.cmd_query(
            self._args(tmp_path, kind='hover', notation='alpha:target-skill')
        )

        assert set(payload) == self._QUERY_COMMON_KEYS | {'hover'}
        assert payload['hover'] is not None

    def test_unknown_notation_still_answers_on_the_ok_row(self, tmp_path: Path) -> None:
        """An empty answer from an ENABLED surface is a real answer, not a degrade.

        The matched control for every assertion above: without it, a verb that
        returned the degraded shape whenever it found nothing would satisfy the
        opt-out tests and the enabled tests alike, and the ``ok`` row's whole
        point — "an empty result is then a real, positive answer" — would be
        unchecked.
        """
        _project(tmp_path, ENABLED)
        payload = corpus_lsp.cmd_query(
            self._args(tmp_path, kind='definition', notation='alpha:no-such-skill')
        )

        assert (payload['state'], payload['provider_count'], payload['status']) == ('ok', 1, 'success')
        assert payload['known'] is False
        assert payload['definition'] is None


class TestEnabledButCorpusMissingDegrades:
    """D6-S04 — enabled, and the configured corpus path does not exist.

    The documented table gives ``not_configured / 0 / degraded`` two distinct
    causes: "the surface is absent or disabled" (covered above) **or** "the
    configured corpus path does not exist". Only the first had a fixture, so the
    second cause — the one that reaches a project which DID opt in and got the
    path wrong — was never driven. It is the state where a degrade is easiest to
    misread as an opt-out, which is exactly why the payload carries
    ``configured: true`` and a ``reason``.
    """

    _MISSING = {
        'code_intelligence': {
            'corpus_language_server': {'enabled': True, 'corpus_path': 'no/such/corpus'}
        }
    }

    @staticmethod
    def _args(root: Path, **extra):
        return type('A', (), {'project_path': str(root), **extra})()

    def test_preflight_degrades_and_says_it_was_configured(self, tmp_path: Path) -> None:
        _project(tmp_path, self._MISSING)
        payload = corpus_lsp.cmd_preflight(self._args(tmp_path))

        assert (payload['state'], payload['provider_count'], payload['status']) == (
            'not_configured', 0, 'degraded',
        )
        assert payload['configured'] is True, (
            'a project that opted in and mis-set the path must not be reported as '
            'unconfigured — the two states take different remedies'
        )
        assert payload['fallback'] == 'read_grep'
        assert 'corpus path' in payload['reason']

    def test_the_two_degrade_causes_are_distinguishable(self, tmp_path: Path) -> None:
        """Both causes share the triple, so ``configured`` is the discriminator.

        Asserted as a pair. Read alone, either case is satisfied by a payload
        that hard-codes ``configured`` to a constant.
        """
        opted_out = tmp_path / 'opted-out'
        opted_out.mkdir()
        _project(opted_out, None)
        misconfigured = tmp_path / 'misconfigured'
        misconfigured.mkdir()
        _project(misconfigured, self._MISSING)

        out_payload = corpus_lsp.cmd_preflight(self._args(opted_out))
        bad_payload = corpus_lsp.cmd_preflight(self._args(misconfigured))

        assert out_payload['state'] == bad_payload['state'] == 'not_configured'
        assert (out_payload['configured'], bad_payload['configured']) == (False, True)
        assert 'reason' not in out_payload
        assert 'reason' in bad_payload

    def test_query_degrades_on_a_missing_corpus(self, tmp_path: Path) -> None:
        """⚠ Documented asymmetry: this branch carries NO ``notation`` key.

        The disabled-query branch echoes ``notation`` back to the caller; this
        one does not, so a consumer reading ``payload['notation']`` off any
        degraded query answer raises ``KeyError`` on exactly this cause. The
        asymmetry is pinned here and reported as a finding rather than papered
        over, because closing it is a production change this test-only task does
        not own.
        """
        _project(tmp_path, self._MISSING)
        payload = corpus_lsp.cmd_query(
            self._args(tmp_path, kind='definition', notation='alpha:target-skill')
        )

        assert (payload['state'], payload['provider_count'], payload['status']) == (
            'not_configured', 0, 'degraded',
        )
        assert payload['fallback'] == 'read_grep'
        assert 'corpus path' in payload['reason']
        assert 'notation' not in payload
        assert 'definition' not in payload


class TestUnconfiguredTreeDrivesTheWholeChain:
    """The composition, not just its pieces.

    The no-op tests above hand `build_server` a stipulated `{'enabled': False}`.
    That covers the server's behaviour given a disabled config, but not the claim
    the plan actually makes — that an *unconfigured project* produces that
    behaviour. These drive the full chain: tree → `find_project_root` →
    `read_corpus_config` → `build_server` → `initialize`.
    """

    def test_tree_without_marshal_yields_no_capabilities(self, tmp_path: Path) -> None:
        root = _project(tmp_path, None)
        project_root = corpus_lsp.find_project_root(root)
        config = corpus_lsp.read_corpus_config(project_root)
        rpc, corpus = corpus_lsp.build_server(project_root, config)
        response = rpc.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}})
        assert response is not None
        assert response['result']['capabilities'] == {}
        assert corpus.enabled is False
        assert corpus.index is None

    def test_tree_with_disabled_marshal_yields_no_capabilities(self, tmp_path: Path) -> None:
        root = _project(tmp_path, {'code_intelligence': {'corpus_language_server': {'enabled': False}}})
        project_root = corpus_lsp.find_project_root(root)
        config = corpus_lsp.read_corpus_config(project_root)
        rpc, corpus = corpus_lsp.build_server(project_root, config)
        response = rpc.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}})
        assert response is not None
        assert response['result']['capabilities'] == {}
        assert corpus.index is None

    def test_enabled_tree_drives_the_same_chain_to_a_working_server(self, tmp_path: Path) -> None:
        """So an empty result above is a real opt-out, not a broken chain."""
        root = _project(tmp_path, ENABLED)
        project_root = corpus_lsp.find_project_root(root)
        config = corpus_lsp.read_corpus_config(project_root)
        rpc, corpus = corpus_lsp.build_server(project_root, config)
        response = rpc.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {}})
        assert response is not None
        assert response['result']['capabilities']['definitionProvider'] is True
        assert corpus.enabled is True
