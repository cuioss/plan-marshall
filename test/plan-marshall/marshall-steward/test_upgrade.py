# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the marshall-steward ``upgrade`` stage-plan / gate-decision emitter.

``upgrade.py`` is a pure deterministic planner: its ``plan`` subcommand emits
the fixed four-stage post-change-reconciliation plan with per-stage gate
dispositions as a function of ``--integrate``. These tests drive the planner's
``main`` entry through the ``_run`` helper — which installs the constructed argv
on ``sys.argv`` because ``main`` is ``safe_main``-wrapped — capture stdout, and
parse the emitted TOON with the canonical parser to assert the stage order, the
top-level-gate suppression semantics, and the ``integrate``-invariance of the
nested gates.

``upgrade.py`` is a marshall-steward skill script, imported by name along with
the shared libraries it pulls in at module scope — the TOON parser, ``file_ops``
(for the ``safe_main`` wrapper), ``bot_registry`` (the live reviewer-kind
registry ``validate_bot_lists`` checks tokens against) and the ``script-shared``
tree ``file_ops`` itself imports from. Under the executor those arrive on one
injected ``PYTHONPATH``; under pytest the root conftest puts every marketplace
``scripts/`` directory on ``sys.path`` before any test module is imported, so no
bootstrap is needed here.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ``upgrade`` pulls in ``file_ops`` and the ``script-shared`` library at module
# scope, and ``bot_registry`` supplies the live reviewer-kind set the bot-list
# assertions check against. Under the executor those arrive on one injected
# PYTHONPATH; under pytest the root conftest puts every marketplace ``scripts/``
# directory on ``sys.path``, so no bootstrap is needed here.
import bot_registry
import pytest
import upgrade
from toon_parser import parse_toon

_EXPECTED_STAGE_KEYS = ['regenerate-targets', 'reconcile-config', 'verify', 'land']
_EXPECTED_STAGE_ORDERS = [1, 2, 3, 4]
_EXPECTED_NESTED_GATES = {
    'regenerate-targets': {'cache-retention-prune'},
    'reconcile-config': {'build-map-reseed'},
    'verify': set(),
    'land': {'land-leave', 'branch-reuse'},
}
_STAGE_ROW_KEYS = {'order', 'key', 'name', 'mutating', 'top_level_gate', 'nested_gates', 'sub_steps'}

# The meta/consumer sub-step matrix (keyed by stage key) — the authoritative
# per-kind end state. Consumer drops the meta-only sub-steps
# (regenerate-target-tree in Stage 1, content-drift-report in Stage 3) and gains
# the consumer-only cache-freshness gate as Stage 1's FIRST sub-step; BOTH kinds
# end Stage 1 with the cache-retention sweep. Stages 2 and 4 are kind-invariant.
_EXPECTED_SUB_STEPS = {
    'meta': {
        'regenerate-targets': ['regenerate-target-tree', 'regenerate-executor', 'cache-retention-sweep'],
        'reconcile-config': ['reconcile-marshal-json', 'migrate-bot-lists', 'validate-bot-lists'],
        'verify': ['executor-preflight', 'content-drift-report'],
        'land': ['run-landing-cycle'],
    },
    'consumer': {
        'regenerate-targets': ['cache-freshness-check', 'regenerate-executor', 'cache-retention-sweep'],
        'reconcile-config': ['reconcile-marshal-json', 'migrate-bot-lists', 'validate-bot-lists'],
        'verify': ['executor-preflight'],
        'land': ['run-landing-cycle'],
    },
}


def _run(
    argv: list[str],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[int, dict]:
    """Drive ``upgrade.main`` with constructed argv, returning ``(exit_code, parsed_toon)``.

    ``main`` is wrapped in ``file_ops.safe_main``, which reads ``sys.argv``
    itself and terminates via ``sys.exit`` rather than returning — the wrapper is
    what guarantees stdout carries parseable TOON even when the body raises. The
    argv is therefore installed on ``sys.argv`` and the exit code read off the
    ``SystemExit`` it raises. This is the ONLY seam in this module that reaches
    the CLI entry point, so every argv-driven case below goes through it.
    """
    monkeypatch.setattr(sys, 'argv', ['upgrade', *argv])
    with pytest.raises(SystemExit) as excinfo:
        upgrade.main()
    captured = capsys.readouterr()
    parsed = parse_toon(captured.out)
    return int(excinfo.value.code or 0), parsed


def test_default_emits_four_stages_in_documented_order(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    """The default invocation exits 0 and emits the four stages in the exact
    documented order (by both ``key`` and ``order``).
    """
    exit_code, parsed = _run(['plan'], capsys, monkeypatch)

    assert exit_code == 0
    assert parsed['integrate'] is False
    stages = parsed['stages']
    assert [stage['key'] for stage in stages] == _EXPECTED_STAGE_KEYS
    assert [stage['order'] for stage in stages] == _EXPECTED_STAGE_ORDERS


def test_integrate_true_suppresses_all_top_level_gates(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    """``--integrate true`` exits 0 and yields ``top_level_gate == suppressed``
    for all four stages.
    """
    exit_code, parsed = _run(['plan', '--integrate', 'true'], capsys, monkeypatch)

    assert exit_code == 0
    assert parsed['integrate'] is True
    assert [stage['top_level_gate'] for stage in parsed['stages']] == ['suppressed'] * 4


@pytest.mark.parametrize('argv', [['plan'], ['plan', '--integrate', 'false']])
def test_plain_mode_prompts_all_top_level_gates(
    argv: list[str], capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    """The default and the explicit ``--integrate false`` both yield
    ``top_level_gate == prompt`` for all four stages.
    """
    exit_code, parsed = _run(argv, capsys, monkeypatch)

    assert exit_code == 0
    assert [stage['top_level_gate'] for stage in parsed['stages']] == ['prompt'] * 4


def test_nested_gates_are_integrate_invariant(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    """The nested-gate sets are identical under ``integrate`` true and false —
    ``integrate`` suppresses only the top-level stage gates, never the nested
    ones — and match the documented mapping.
    """
    _true_exit, true_parsed = _run(['plan', '--integrate', 'true'], capsys, monkeypatch)
    _false_exit, false_parsed = _run(['plan', '--integrate', 'false'], capsys, monkeypatch)

    true_nested = {stage['key']: set(stage['nested_gates']) for stage in true_parsed['stages']}
    false_nested = {stage['key']: set(stage['nested_gates']) for stage in false_parsed['stages']}

    assert true_nested == false_nested
    assert true_nested == _EXPECTED_NESTED_GATES


def test_toon_carries_documented_keys(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    """The emitted TOON parses and carries the documented top-level keys and
    per-stage row keys.
    """
    _exit_code, parsed = _run(['plan', '--integrate', 'true'], capsys, monkeypatch)

    assert {'status', 'integrate', 'project_kind', 'stages'}.issubset(parsed.keys())
    assert parsed['status'] == 'success'
    for stage in parsed['stages']:
        assert _STAGE_ROW_KEYS.issubset(stage.keys())
        assert isinstance(stage['nested_gates'], list)
        assert isinstance(stage['sub_steps'], list)


# ============================================================================
# Deliverable 2: project-kind detection and the kind-aware sub-step matrix
# ============================================================================


@pytest.mark.parametrize('project_kind', ['meta', 'consumer'])
def test_build_plan_sub_steps_match_kind_matrix(project_kind: str):
    """build_plan(integrate, project_kind) emits each stage's per-kind sub_steps:
    consumer drops the meta-only sub-steps (regenerate-target-tree, content-drift-report).
    """
    plan = upgrade.build_plan(False, project_kind)

    assert plan['project_kind'] == project_kind
    actual = {stage['key']: stage['sub_steps'] for stage in plan['stages']}
    assert actual == _EXPECTED_SUB_STEPS[project_kind]


def test_build_plan_consumer_excludes_meta_only_sub_steps():
    """A consumer plan's Stage 3 sub_steps are exactly [executor-preflight] and
    its Stage 1 carries neither meta-only sub-step — the meta-only sub-steps are
    absent."""
    plan = upgrade.build_plan(False, 'consumer')
    by_key = {stage['key']: stage['sub_steps'] for stage in plan['stages']}

    assert by_key['verify'] == ['executor-preflight']
    assert 'regenerate-target-tree' not in by_key['regenerate-targets']
    assert 'content-drift-report' not in by_key['verify']


def test_consumer_stage_1_leads_with_cache_freshness_check():
    """The consumer kind gates on plugin-cache freshness as Stage 1's FIRST
    sub-step, ahead of regenerate-executor — it is regenerate-executor that
    reads the unrefreshed cache."""
    by_key = {s['key']: s['sub_steps'] for s in upgrade.build_plan(False, 'consumer')['stages']}

    stage_1 = by_key['regenerate-targets']
    assert stage_1[0] == 'cache-freshness-check'
    assert stage_1.index('cache-freshness-check') < stage_1.index('regenerate-executor')


def test_meta_stage_1_final_list_includes_cache_retention_sweep():
    """The meta kind's Stage 1 sub_steps reach their final value — the retention
    sweep applies to BOTH kinds because both accumulate version dirs in the same
    cache tree."""
    by_key = {s['key']: s['sub_steps'] for s in upgrade.build_plan(False, 'meta')['stages']}

    assert by_key['regenerate-targets'] == [
        'regenerate-target-tree',
        'regenerate-executor',
        'cache-retention-sweep',
    ]


def test_consumer_stage_1_final_list_includes_cache_retention_sweep():
    """The consumer kind's Stage 1 sub_steps reach their final value."""
    by_key = {s['key']: s['sub_steps'] for s in upgrade.build_plan(False, 'consumer')['stages']}

    assert by_key['regenerate-targets'] == [
        'cache-freshness-check',
        'regenerate-executor',
        'cache-retention-sweep',
    ]


@pytest.mark.parametrize('project_kind', ['meta', 'consumer'])
@pytest.mark.parametrize('integrate', [True, False])
def test_cache_retention_prune_gate_is_integrate_invariant_on_both_kinds(project_kind: str, integrate: bool):
    """Stage 1 carries the cache-retention-prune nested gate for both kinds, and
    the gate is integrate-invariant — the destructive apply still prompts under
    integrate=true."""
    by_key = {s['key']: set(s['nested_gates']) for s in upgrade.build_plan(integrate, project_kind)['stages']}

    assert 'cache-retention-prune' in by_key['regenerate-targets']


def test_meta_kind_does_not_gain_cache_freshness_check():
    """The freshness gate is consumer-scoped: the meta project refreshes its own
    cache via project:finalize-step-sync-plugin-cache, so no meta stage carries
    cache-freshness-check."""
    plan = upgrade.build_plan(False, 'meta')

    for stage in plan['stages']:
        assert 'cache-freshness-check' not in stage['sub_steps']


def test_build_plan_rejects_unknown_project_kind():
    """build_plan raises on a project_kind that is neither meta nor consumer."""
    with pytest.raises(ValueError):
        upgrade.build_plan(False, 'not-a-kind')


def test_build_plan_preserves_stage_order_and_gates_across_kinds():
    """Stage order, keys, top-level-gate suppression, and nested-gate invariance
    are unchanged across both project kinds — the kind only varies sub_steps."""
    for project_kind in ('meta', 'consumer'):
        plain = upgrade.build_plan(False, project_kind)
        integrated = upgrade.build_plan(True, project_kind)

        assert [s['key'] for s in plain['stages']] == _EXPECTED_STAGE_KEYS
        assert [s['order'] for s in plain['stages']] == _EXPECTED_STAGE_ORDERS
        assert [s['top_level_gate'] for s in plain['stages']] == ['prompt'] * 4
        assert [s['top_level_gate'] for s in integrated['stages']] == ['suppressed'] * 4
        nested = {s['key']: set(s['nested_gates']) for s in plain['stages']}
        assert nested == _EXPECTED_NESTED_GATES


def test_detect_project_kind_meta_when_marketplace_tree_present(tmp_path: Path):
    """detect_project_kind classifies a dir WITH marketplace/targets/generate.py
    AND marketplace/bundles/ as meta (the plan-marshall meta-project shape)."""
    (tmp_path / 'marketplace' / 'targets').mkdir(parents=True)
    (tmp_path / 'marketplace' / 'targets' / 'generate.py').write_text('# fixture generator\n', encoding='utf-8')
    (tmp_path / 'marketplace' / 'bundles').mkdir(parents=True)

    assert upgrade.detect_project_kind(tmp_path) == 'meta'


def test_detect_project_kind_consumer_when_marketplace_absent(tmp_path: Path):
    """detect_project_kind classifies a dir WITHOUT the marketplace tree as
    consumer (the downstream-consumer shape) — the Leg A acceptance assertion."""
    (tmp_path / 'src').mkdir()

    assert upgrade.detect_project_kind(tmp_path) == 'consumer'


def test_detect_project_kind_consumer_when_only_one_marker_present(tmp_path: Path):
    """Presence of only ONE of the two markers is still consumer — both the
    generator AND the bundle tree are required for meta."""
    (tmp_path / 'marketplace' / 'bundles').mkdir(parents=True)  # bundles only, no generate.py

    assert upgrade.detect_project_kind(tmp_path) == 'consumer'


@pytest.mark.parametrize('project_kind', ['meta', 'consumer'])
def test_project_kind_flag_honored_verbatim(
    project_kind: str, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    """--project-kind {meta|consumer} is honored verbatim (no cwd detection)."""
    _exit_code, parsed = _run(['plan', '--project-kind', project_kind], capsys, monkeypatch)

    assert parsed['project_kind'] == project_kind
    actual = {stage['key']: stage['sub_steps'] for stage in parsed['stages']}
    assert actual == _EXPECTED_SUB_STEPS[project_kind]


def test_project_kind_auto_invokes_detector(monkeypatch, capsys: pytest.CaptureFixture[str]):
    """--project-kind auto (the default) resolves the kind via detect_project_kind
    against the cwd rather than a hard-coded value."""
    monkeypatch.setattr(upgrade, 'detect_project_kind', lambda root: 'consumer')

    _exit_code, parsed = _run(['plan', '--project-kind', 'auto'], capsys, monkeypatch)

    assert parsed['project_kind'] == 'consumer'
    by_key = {stage['key']: stage['sub_steps'] for stage in parsed['stages']}
    assert by_key['regenerate-targets'] == _EXPECTED_SUB_STEPS['consumer']['regenerate-targets']


# =============================================================================
# migrate-bot-lists — the one-shot legacy auto-map, over its four input states
# =============================================================================
#
# The four states are exhaustive over the presence/absence cross-product of the
# retired ``enabled_bots`` key and the two replacement keys. States (3) and (4)
# are deliberately indistinguishable once the legacy key is gone — that
# collapse is what makes the migration self-disarming and safe to re-run.


def test_migrate_bot_lists_seeds_required_from_legacy_verbatim():
    """State 1 — legacy alone seeds required_bots VERBATIM and empties optional.

    Seeding REQUIRED (not optional) preserves the legacy semantics: every bot on
    the retired list was awaited, and awaiting is precisely what ``required``
    means. Splitting the list across the two new knobs would silently demote a
    previously-awaited bot to a non-blocking one.
    """
    params = {'enabled_bots': 'coderabbit,sourcery', 'review_bot_buffer_seconds': 180}

    report = upgrade.migrate_bot_lists(params)

    assert report['state'] == 'migrated'
    assert params['required_bots'] == 'coderabbit,sourcery'
    assert params['optional_bots'] == ''
    # The legacy key is consumed, and the unrelated knob is untouched.
    assert 'enabled_bots' not in params
    assert params['review_bot_buffer_seconds'] == 180


def test_migrate_bot_lists_records_migrated_provenance_not_answered():
    """State 1 records provenance ``migrated`` — the value was NOT operator-answered.

    The distinction is load-bearing downstream: an auto-mapped value is a
    best-effort guess at the operator's intent, and marking it ``answered`` would
    let the wizard treat a guess as a settled decision and never re-ask.
    """
    params = {'enabled_bots': 'coderabbit'}

    upgrade.migrate_bot_lists(params)

    assert params['bot_lists_provenance'] == 'migrated'


def test_migrate_bot_lists_operator_answer_wins_over_legacy():
    """State 2 — an already-answered new key wins; only the stale legacy is dropped.

    The operator's explicit answer is never overwritten by the auto-map, and the
    provenance is not downgraded from ``answered`` to ``migrated``. The discarded
    legacy value is reported so the operator can see what was dropped.
    """
    params = {
        'enabled_bots': 'coderabbit,sourcery',
        'required_bots': 'cuioss-review-bot',
        'optional_bots': 'sourcery',
        'bot_lists_provenance': 'answered',
    }

    report = upgrade.migrate_bot_lists(params)

    assert report['state'] == 'operator_answer_kept'
    assert report['discarded_legacy'] == 'coderabbit,sourcery'
    assert params['required_bots'] == 'cuioss-review-bot'
    assert params['optional_bots'] == 'sourcery'
    assert params['bot_lists_provenance'] == 'answered'
    assert 'enabled_bots' not in params


def test_migrate_bot_lists_absent_legacy_leaves_never_asked_posture_intact():
    """State 3 — no legacy key: a no-op that must NOT fabricate an answer.

    Writing empty values here would convert a never-asked posture into an
    answered-empty one, which downstream reads as "the operator chose no bots"
    and suppresses review. The no-op must leave the params untouched.
    """
    params = {'review_bot_buffer_seconds': 180}

    report = upgrade.migrate_bot_lists(params)

    assert report['state'] == 'noop'
    assert params == {'review_bot_buffer_seconds': 180}
    assert 'bot_lists_provenance' not in params


def test_migrate_bot_lists_is_self_disarming_on_second_run():
    """State 4 — a second run over already-migrated params changes nothing.

    Once the legacy key is consumed, state (4) collapses onto state (3), so the
    verb can sit permanently in the Stage 2 sub-step list without re-migrating
    or clobbering the values it produced on the first run.
    """
    params = {'enabled_bots': 'coderabbit,sourcery'}

    first = upgrade.migrate_bot_lists(params)
    after_first = dict(params)
    second = upgrade.migrate_bot_lists(params)

    assert first['state'] == 'migrated'
    assert second['state'] == 'noop'
    assert params == after_first
    assert second['required_bots'] == 'coderabbit,sourcery'
    assert second['optional_bots'] == ''


# =============================================================================
# validate-bot-lists — the read-only unknown-token report, over its four input
# states plus the matched negative control
# =============================================================================
#
# The four states mirror the shape the ``migrate_bot_lists`` suite above already
# establishes for this file: every configured token valid, one token unknown, an
# empty list, and an absent step.
#
# The load-bearing addition is the CONTROL. Asserting only that a valid list
# produced no unknown tokens would pass just as happily for a check that examined
# nothing at all, and those are different claims: "none of the three configured
# names is unknown" is a clean bill of health, "no names were configured" is not.
# Every clean assertion below therefore pins the population the verdict was
# computed over (ADR-019's coverage discriminator), and the two no-op states are
# pinned to carry NO count at all.

#: The step whose params both bot-list verbs operate on. Read off the module
#: rather than restated, so a rename of the step id cannot leave this suite
#: staging a config the verb no longer looks at.
_STEP_ID = upgrade._AUTOMATIC_REVIEW_STEP_ID

#: A token deliberately outside the registry — the misspelling shape this verb
#: exists to catch (one letter dropped from a real reviewer name). Its
#: outside-ness is ASSERTED by a test below rather than assumed: a registry that
#: ever adopted this name would otherwise turn every unknown-token case here into
#: a silently-valid one, and the whole section would keep passing.
_UNREGISTERED_TOKEN = 'codrabbit'


def _live_kinds() -> list[str]:
    """The live registry kind set — DERIVED, never a literal reviewer name.

    Deriving is what keeps the negative control honest across a registry rename:
    a hard-coded "valid" token starts reporting unknown the moment its bot is
    renamed, which would make the control a false positive for the very defect it
    exists to rule out.

    The emptiness guard is not defensive noise — it is the anti-vacuity check.
    Every clean-verdict assertion below is computed over this set, so a registry
    that resolved nothing would make them all trivially true.
    """
    kinds = bot_registry.bot_kinds()
    assert kinds, 'registry resolved no bot kinds — every check in this section would be vacuous'
    return kinds


def _valid_params() -> dict:
    """A step param object whose every configured token is registered."""
    kinds = _live_kinds()
    return {'required_bots': kinds[0], 'optional_bots': ','.join(kinds[1:])}


def _configured_tokens(params: dict) -> list[str]:
    """The tokens a param object actually configures across both lists."""
    return [
        token.strip()
        for key in ('required_bots', 'optional_bots')
        for token in str(params.get(key) or '').split(',')
        if token.strip()
    ]


def test_the_unregistered_fixture_token_is_genuinely_outside_the_registry():
    """The premise every unknown-token case below rests on, asserted not assumed.

    Without this, a registry that grew a bot by this name would turn each
    "reports the unknown token" test into a test of nothing, and they would all
    still pass.
    """
    assert _UNREGISTERED_TOKEN not in bot_registry.bot_kinds()


def test_validate_bot_lists_reports_clean_over_a_stated_population():
    """State 1 and the MATCHED NEGATIVE CONTROL: valid tokens report clean AND
    publish how many were checked.

    The count is asserted against the tokens the fixture actually configured — a
    derived number — so a validation that silently examined zero tokens cannot
    pass here as a clean one.
    """
    params = _valid_params()
    configured = _configured_tokens(params)

    report = upgrade.validate_bot_lists(params)

    assert report['state'] == 'clean'
    assert report['unknown_tokens'] == []
    assert report['checked_count'] == len(configured)
    assert report['checked_count'] > 0


def test_a_clean_verdict_over_nothing_is_distinguishable_from_one_over_tokens():
    """State 3 — empty lists. Same ``state``, same empty ``unknown_tokens``.

    The ONLY thing separating "checked three, found none" from "checked nothing"
    is ``checked_count``, which is why that field is the contract rather than a
    convenience: drop it and the two collapse into one reassuring answer.
    """
    empty = upgrade.validate_bot_lists({'required_bots': '', 'optional_bots': ''})
    populated = upgrade.validate_bot_lists(_valid_params())

    assert empty['state'] == populated['state'] == 'clean'
    assert empty['unknown_tokens'] == populated['unknown_tokens'] == []
    assert empty['checked_count'] == 0
    assert populated['checked_count'] > empty['checked_count']


def test_validate_bot_lists_names_the_unknown_token_and_the_live_kind_set():
    """State 2 — one unknown token, reported beside the set it was checked against.

    The kind set is the REMEDY, not decoration: an operator told a name is wrong
    still has to be told which names are right, and that set is where the
    correction is chosen from.
    """
    report = upgrade.validate_bot_lists({'required_bots': _UNREGISTERED_TOKEN, 'optional_bots': ''})

    assert report['state'] == 'unknown_tokens'
    assert report['unknown_tokens'] == [_UNREGISTERED_TOKEN]
    assert report['known_bot_kinds'] == bot_registry.bot_kinds()
    assert report['checked_count'] == 1


def test_validate_bot_lists_checks_the_optional_list_too():
    """A misspelled OPTIONAL name is still a name no reviewer answers to.

    Checking only ``required_bots`` would leave the optional list — where a stale
    token is likelier, because its silence never blocks and so never surfaces —
    permanently unexamined.
    """
    params = {'required_bots': _live_kinds()[0], 'optional_bots': _UNREGISTERED_TOKEN}

    report = upgrade.validate_bot_lists(params)

    assert report['state'] == 'unknown_tokens'
    assert report['unknown_tokens'] == [_UNREGISTERED_TOKEN]
    assert report['checked_count'] == 2


def test_an_unknown_token_configured_in_both_lists_is_reported_once():
    """De-duplication is a property of the reported NAMES, not of the population.

    The operator has one name to fix, so it is named once; the count still
    records both occurrences, because it reports what was examined.
    """
    params = {'required_bots': _UNREGISTERED_TOKEN, 'optional_bots': _UNREGISTERED_TOKEN}

    report = upgrade.validate_bot_lists(params)

    assert report['unknown_tokens'] == [_UNREGISTERED_TOKEN]
    assert report['checked_count'] == 2


def test_validate_bot_lists_drops_no_token_and_rejects_no_list():
    """Report-only, asserted on the input rather than on intent.

    A silent drop is the collapse this plan exists to remove, and a blanket
    rejection would turn a one-token typo into an unstartable finalize. One
    assertion rules out both: the param object is unchanged afterwards, unknown
    token still in place.
    """
    kinds = _live_kinds()
    params = {
        'required_bots': f'{kinds[0]},{_UNREGISTERED_TOKEN}',
        'optional_bots': '',
        'review_bot_buffer_seconds': 180,
    }
    before = dict(params)

    report = upgrade.validate_bot_lists(params)

    assert report['state'] == 'unknown_tokens'
    assert params == before


def test_tokens_are_stripped_and_empty_segments_are_not_counted():
    """A padded token is the same token, and a trailing comma configures nothing.

    Both halves matter: an unstripped token would read as unknown (a false
    positive on a correct config), and counting empty segments would inflate the
    population a clean verdict claims to cover.
    """
    params = {'required_bots': f'  {_live_kinds()[0]} , ,', 'optional_bots': None}

    report = upgrade.validate_bot_lists(params)

    assert report['state'] == 'clean'
    assert report['checked_count'] == 1


class TestValidateBotListsVerb:
    """The CLI verb against a real marshal.json on disk — and it must never write."""

    @staticmethod
    def _stage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, config: dict) -> Path:
        """Write ``config`` to a sandbox marshal.json and point the loader at it.

        ``_config_core.MARSHAL_PATH`` is resolved ONCE at import time, so a bare
        ``chdir`` into a staged project does not redirect the loader — the verb
        would keep reading whatever path the process started with, which for this
        suite is the repository's own config. Re-binding the module attribute is
        what makes the no-write assertion below a statement about the staged file.
        """
        import _config_core

        marshal = tmp_path / '.plan' / 'marshal.json'
        marshal.parent.mkdir(parents=True, exist_ok=True)
        marshal.write_text(json.dumps(config), encoding='utf-8')
        monkeypatch.setattr(_config_core, 'MARSHAL_PATH', marshal)
        return marshal

    @staticmethod
    def _config(params: dict) -> dict:
        """A marshal.json carrying ``params`` on the automatic-review step."""
        return {'plan': {'phase-6-finalize': {'steps': {_STEP_ID: params}}}}

    def test_verb_reports_the_unknown_token_read_from_disk(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """End to end from the staged file, not from a hand-built param dict."""
        self._stage(tmp_path, monkeypatch, self._config({'required_bots': _UNREGISTERED_TOKEN}))

        result = upgrade.cmd_validate_bot_lists(argparse.Namespace())

        assert result['status'] == 'success'
        assert result['operation'] == 'validate-bot-lists'
        assert result['state'] == 'unknown_tokens'
        assert result['unknown_tokens'] == [_UNREGISTERED_TOKEN]
        assert result['known_bot_kinds'] == bot_registry.bot_kinds()

    def test_verb_never_rewrites_marshal_json(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """Reports and never rewrites — asserted on the FILE.

        Run against the state most likely to tempt a fix-up — a config carrying an
        unknown token — so a verb that "helpfully" dropped or corrected it would
        fail here rather than on a case with nothing to change.
        """
        marshal = self._stage(
            tmp_path, monkeypatch, self._config({'required_bots': _UNREGISTERED_TOKEN})
        )
        before = marshal.read_bytes()

        upgrade.cmd_validate_bot_lists(argparse.Namespace())

        assert marshal.read_bytes() == before

    def test_verb_reports_clean_over_a_stated_population(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """The negative control at the verb layer, not just the pure function."""
        params = _valid_params()
        self._stage(tmp_path, monkeypatch, self._config(params))

        result = upgrade.cmd_validate_bot_lists(argparse.Namespace())

        assert result['state'] == 'clean'
        assert result['unknown_tokens'] == []
        assert result['checked_count'] == len(_configured_tokens(params))
        assert result['checked_count'] > 0

    def test_verb_is_a_noop_on_a_project_without_the_step(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """State 4 — an absent step is a typed no-op, never a traceback."""
        self._stage(tmp_path, monkeypatch, {'plan': {}})

        result = upgrade.cmd_validate_bot_lists(argparse.Namespace())

        assert result['status'] == 'success'
        assert result['state'] == 'noop'
        assert _STEP_ID in result['detail']

    def test_verb_is_a_noop_on_an_uninitialized_project(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """No marshal.json at all — the verb runs as an upgrade sub-step, which can
        be pointed at a project that was never initialized."""
        import _config_core

        monkeypatch.setattr(_config_core, 'MARSHAL_PATH', tmp_path / '.plan' / 'marshal.json')

        result = upgrade.cmd_validate_bot_lists(argparse.Namespace())

        assert result['status'] == 'success'
        assert result['state'] == 'noop'
        assert 'marshal.json' in result['detail']

    def test_neither_noop_publishes_a_count_that_could_read_as_a_check(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        """The three "nothing was found" answers are kept apart by the COUNT KEY.

        Two of them examined nothing (no config, no step) and carry no
        ``checked_count`` at all; the third genuinely examined an empty
        configuration and publishes ``0``. A ``0`` on the first two would be
        indistinguishable from the third, which is the exact conflation the
        omission prevents — so the assertion is on the key's ABSENCE, not on its
        value.
        """
        import _config_core

        monkeypatch.setattr(_config_core, 'MARSHAL_PATH', tmp_path / 'absent' / 'marshal.json')
        uninitialized = upgrade.cmd_validate_bot_lists(argparse.Namespace())

        self._stage(tmp_path, monkeypatch, {'plan': {}})
        absent_step = upgrade.cmd_validate_bot_lists(argparse.Namespace())

        self._stage(
            tmp_path, monkeypatch, self._config({'required_bots': '', 'optional_bots': ''})
        )
        configured_but_empty = upgrade.cmd_validate_bot_lists(argparse.Namespace())

        assert uninitialized['state'] == 'noop'
        assert 'checked_count' not in uninitialized
        assert absent_step['state'] == 'noop'
        assert 'checked_count' not in absent_step
        assert configured_but_empty['state'] == 'clean'
        assert configured_but_empty['checked_count'] == 0

    def test_verb_is_reachable_from_the_constructed_argv(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ):
        """The CLI entry point routes ``validate-bot-lists`` to the verb.

        Driven through the same ``_run`` seam every other argv case in this module
        uses, so the subcommand is pinned as reachable rather than only as
        callable — a handler wired into ``main``'s dispatch chain but never
        registered as a subparser would be an argparse rejection here.
        """
        self._stage(tmp_path, monkeypatch, self._config({'required_bots': _UNREGISTERED_TOKEN}))

        exit_code, parsed = _run(['validate-bot-lists'], capsys, monkeypatch)

        assert exit_code == 0
        assert parsed['status'] == 'success'
        assert parsed['operation'] == 'validate-bot-lists'
        assert parsed['state'] == 'unknown_tokens'
        assert parsed['unknown_tokens'] == [_UNREGISTERED_TOKEN]
