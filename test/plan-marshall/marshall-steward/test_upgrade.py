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
from typing import cast

# ``upgrade`` pulls in ``file_ops`` and the ``script-shared`` library at module
# scope, and ``bot_registry`` supplies the live reviewer-kind set the bot-list
# assertions check against. Under the executor those arrive on one injected
# PYTHONPATH; under pytest the root conftest puts every marketplace ``scripts/``
# directory on ``sys.path``, so no bootstrap is needed here.
import bot_registry
import pytest
import upgrade
from toon_parser import parse_toon

from conftest import load_script_module, parse_ns

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
_EXPECTED_STAGE_2_SUB_STEPS = [
    'reconcile-marshal-json',
    'review-held-defaults',
    'migrate-bot-lists',
    'validate-bot-lists',
    'migrate-architecture-descriptors',
]
_EXPECTED_SUB_STEPS = {
    'meta': {
        'regenerate-targets': ['regenerate-target-tree', 'regenerate-executor', 'cache-retention-sweep'],
        'reconcile-config': _EXPECTED_STAGE_2_SUB_STEPS,
        'verify': ['executor-preflight', 'content-drift-report'],
        'land': ['run-landing-cycle'],
    },
    'consumer': {
        'regenerate-targets': ['cache-freshness-check', 'regenerate-executor', 'cache-retention-sweep'],
        'reconcile-config': _EXPECTED_STAGE_2_SUB_STEPS,
        'verify': ['executor-preflight'],
        'land': ['run-landing-cycle'],
    },
}


# Hermetic executor-bootstrap report for ``_run``. The real
# ``bootstrap_executor`` reads the serving executor and the live plugin cache —
# state the planner-matrix tests must never depend on. Wiring tests that need the
# real seam monkeypatch ``upgrade.bootstrap_executor`` themselves and pass
# ``bootstrap=True`` to ``_run``.
_FRESH_BOOTSTRAP_STUB: dict = {
    'status': 'success',
    'action': 'fresh',
    'executor_version': '',
    'newest_cache_version': '',
    'executor_path': '',
    'cache_root': '',
    'generator': '',
    'warning': '',
    'detail': 'hermetic test stub',
}


def _run(
    argv: list[str],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    bootstrap: bool = False,
) -> tuple[int, dict]:
    """Drive ``upgrade.main`` with constructed argv, returning ``(exit_code, parsed_toon)``.

    ``main`` is wrapped in ``file_ops.safe_main``, which reads ``sys.argv``
    itself and terminates via ``sys.exit`` rather than returning — the wrapper is
    what guarantees stdout carries parseable TOON even when the body raises. The
    argv is therefore installed on ``sys.argv`` and the exit code read off the
    ``SystemExit`` it raises. This is the ONLY seam in this module that reaches
    the CLI entry point, so every argv-driven case below goes through it.

    Every ``plan`` invocation runs the executor bootstrap — the missing-or-broken
    recovery is ungated, and a merely-stale executor is reported unless
    ``--bootstrap true`` consents to a rewrite. By default ``_run`` replaces the
    bootstrap with a hermetic ``fresh`` stub, so the planner-matrix tests never
    read the live executor or plugin cache. Pass ``bootstrap=True`` to leave the
    bootstrap seam to the caller: the bootstrap-wiring tests monkeypatch
    ``upgrade.bootstrap_executor`` themselves and set ``--bootstrap`` in ``argv``
    to exercise the ``allow_regenerate`` wiring. Non-``plan`` verbs never
    bootstrap.
    """
    if argv and argv[0] == 'plan' and not bootstrap:
        monkeypatch.setattr(upgrade, 'bootstrap_executor', lambda **kwargs: dict(_FRESH_BOOTSTRAP_STUB))
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


def test_nested_gates_are_integrate_invariant(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
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


def test_toon_carries_documented_keys(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
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
# Project-kind detection and the kind-aware sub-step matrix
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


@pytest.mark.parametrize('project_kind', ['meta', 'consumer'])
@pytest.mark.parametrize('integrate', [True, False])
def test_migrate_architecture_descriptors_is_the_last_stage_2_sub_step(project_kind: str, integrate: bool):
    """The descriptor migration runs after every config reconcile sub-step, for both kinds.

    It follows ``validate-bot-lists`` so the migration it writes is the last Stage 2
    mutation before the build-map gate, and it is kind-invariant because every
    discovered project carries descriptors an older tool version may have written.
    """
    by_key = {s['key']: s['sub_steps'] for s in upgrade.build_plan(integrate, project_kind)['stages']}

    stage_2 = by_key['reconcile-config']
    assert stage_2[-1] == 'migrate-architecture-descriptors'
    assert stage_2.count('migrate-architecture-descriptors') == 1
    assert stage_2 == _EXPECTED_STAGE_2_SUB_STEPS


@pytest.mark.parametrize('project_kind', ['meta', 'consumer'])
@pytest.mark.parametrize('integrate', [True, False])
def test_review_held_defaults_follows_reconcile_marshal_json(project_kind: str, integrate: bool):
    """D3: the operator-intent ask step runs immediately after reconcile, for both kinds.

    `reconcile-marshal-json` (sync-defaults, atomic-once-present) preserves a
    prior removal structurally; `review-held-defaults` then surfaces the held
    `held_for_ask` / `re_added` buckets with the sync-identical `re-add` vs
    `new default` wording, asking once per newly-discovered step and never
    auto-adding.
    """
    by_key = {s['key']: s['sub_steps'] for s in upgrade.build_plan(integrate, project_kind)['stages']}

    stage_2 = by_key['reconcile-config']
    assert stage_2.index('review-held-defaults') == stage_2.index('reconcile-marshal-json') + 1
    assert stage_2.count('review-held-defaults') == 1


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
    """State 1 — legacy alone seeds the standard roster (not verbatim).

    The legacy-only config lands valid without hand repair: required carries
    ``cuioss-review-bot,coderabbit``, optional carries ``sourcery``, each dropped
    legacy bot is named in ``discarded_legacy`` so no name disappears silently,
    and provenance records ``migrated``. Unknown legacy names are reported by
    ``validate_bot_lists`` rather than copied. (Function name is historical: it
    predates the standard-roster contract and is kept so the five migrated
    test ids stay stable.)
    """
    params = {'enabled_bots': 'coderabbit,sourcery', 'review_bot_buffer_seconds': 180}

    report = upgrade.migrate_bot_lists(params)

    assert report['state'] == 'migrated'
    assert report['required_bots'] == 'cuioss-review-bot,coderabbit'
    assert report['optional_bots'] == 'sourcery'
    assert report['discarded_legacy'] == ['coderabbit', 'sourcery']
    assert params['required_bots'] == 'cuioss-review-bot,coderabbit'
    assert params['optional_bots'] == 'sourcery'
    assert params['bot_lists_provenance'] == 'migrated'
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
    provenance is not downgraded from ``answered`` to ``migrated``. Each
    discarded bot is reported by name so the operator can see what was dropped.
    """
    params = {
        'enabled_bots': 'coderabbit,sourcery',
        'required_bots': 'cuioss-review-bot',
        'optional_bots': 'sourcery',
        'bot_lists_provenance': 'answered',
    }

    report = upgrade.migrate_bot_lists(params)

    assert report['state'] == 'operator_answer_kept'
    assert report['discarded_legacy'] == ['coderabbit', 'sourcery']
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
    or clobbering the standard-roster values it produced on the first run.
    """
    params = {'enabled_bots': 'coderabbit,sourcery'}

    first = upgrade.migrate_bot_lists(params)
    after_first = dict(params)
    second = upgrade.migrate_bot_lists(params)

    assert first['state'] == 'migrated'
    assert first['discarded_legacy'] == ['coderabbit', 'sourcery']
    assert second['state'] == 'noop'
    assert params == after_first
    assert second['required_bots'] == 'cuioss-review-bot,coderabbit'
    assert second['optional_bots'] == 'sourcery'


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

    def test_verb_reports_the_unknown_token_read_from_disk(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """End to end from the staged file, not from a hand-built param dict."""
        self._stage(tmp_path, monkeypatch, self._config({'required_bots': _UNREGISTERED_TOKEN}))

        result = upgrade.cmd_validate_bot_lists(argparse.Namespace())

        assert result['status'] == 'success'
        assert result['operation'] == 'validate-bot-lists'
        assert result['state'] == 'unknown_tokens'
        assert result['unknown_tokens'] == [_UNREGISTERED_TOKEN]
        assert result['known_bot_kinds'] == bot_registry.bot_kinds()

    def test_verb_never_rewrites_marshal_json(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """Reports and never rewrites — asserted on the FILE.

        Run against the state most likely to tempt a fix-up — a config carrying an
        unknown token — so a verb that "helpfully" dropped or corrected it would
        fail here rather than on a case with nothing to change.
        """
        marshal = self._stage(tmp_path, monkeypatch, self._config({'required_bots': _UNREGISTERED_TOKEN}))
        before = marshal.read_bytes()

        upgrade.cmd_validate_bot_lists(argparse.Namespace())

        assert marshal.read_bytes() == before

    def test_verb_reports_clean_over_a_stated_population(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """The negative control at the verb layer, not just the pure function."""
        params = _valid_params()
        self._stage(tmp_path, monkeypatch, self._config(params))

        result = upgrade.cmd_validate_bot_lists(argparse.Namespace())

        assert result['state'] == 'clean'
        assert result['unknown_tokens'] == []
        assert result['checked_count'] == len(_configured_tokens(params))
        assert result['checked_count'] > 0

    def test_verb_is_a_noop_on_a_project_without_the_step(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        """State 4 — an absent step is a typed no-op, never a traceback."""
        self._stage(tmp_path, monkeypatch, {'plan': {}})

        result = upgrade.cmd_validate_bot_lists(argparse.Namespace())

        assert result['status'] == 'success'
        assert result['state'] == 'noop'
        assert _STEP_ID in result['detail']

    def test_verb_is_a_noop_on_an_uninitialized_project(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
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

        self._stage(tmp_path, monkeypatch, self._config({'required_bots': '', 'optional_bots': ''}))
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


# =============================================================================
# Stage 2 order roster preservation — seeded roster survives the full order
# =============================================================================
#
# The three verbs run in Stage 2 order (migrate-bot-lists, reconcile via the
# sync-defaults back-fill, validate-bot-lists). These tests drive that order as
# pure functions — migrate, then back-fill, then validate — so a roster seeded
# at the top still validates clean at the bottom with no hand repair, and an
# operator answer survives all three without being overwritten.


def _merged_with_params(params: dict) -> dict:
    """Wrap step ``params`` in the merged-config shape the back-fill reads."""
    return {'plan': {'phase-6-finalize': {'steps': {upgrade._AUTOMATIC_REVIEW_STEP_ID: params}}}}


def _params_of(merged: dict) -> dict:
    """Read the automatic-review params back out of a merged config."""
    return dict(merged['plan']['phase-6-finalize']['steps'][upgrade._AUTOMATIC_REVIEW_STEP_ID])


def test_stage2_order_seeded_roster_survives_merge_and_validates_clean():
    """Legacy-only config seeds the standard roster, survives the merge, validates clean.

    The full Stage 2 order in one test: migrate seeds
    ``required_bots=cuioss-review-bot,coderabbit`` + ``optional_bots=sourcery``,
    the sync-defaults back-fill must not clobber the seeded values, and validate
    reports clean over the three seeded tokens with the live kind set.
    """
    import _cmd_sync_defaults

    params: dict = {'enabled_bots': 'coderabbit,sourcery'}

    report = upgrade.migrate_bot_lists(params)

    assert report['state'] == 'migrated'
    merged = _merged_with_params(params)
    _cmd_sync_defaults._backfill_standard_roster(merged, enabled=True)
    kept = _params_of(merged)

    assert kept['required_bots'] == 'cuioss-review-bot,coderabbit'
    assert kept['optional_bots'] == 'sourcery'
    validation = upgrade.validate_bot_lists(kept)
    assert validation['state'] == 'clean'
    assert validation['unknown_tokens'] == []
    assert validation['known_bot_kinds'] == bot_registry.bot_kinds()
    assert validation['checked_count'] == 3


def test_stage2_order_operator_answer_survives_merge_and_validates_clean():
    """An operator answer survives migrate AND the merge, then validates clean.

    The operator's explicit roster is never overwritten — not by the auto-map
    (state 2 keeps it), not by the back-fill (a present value is an answer) —
    and the surviving roster validates clean over its own population.
    """
    import _cmd_sync_defaults

    kinds = _live_kinds()
    params: dict = {
        'enabled_bots': 'coderabbit,sourcery',
        'required_bots': kinds[0],
        'optional_bots': ','.join(kinds[1:]),
        'bot_lists_provenance': 'answered',
    }
    configured = _configured_tokens(params)

    report = upgrade.migrate_bot_lists(params)

    assert report['state'] == 'operator_answer_kept'
    merged = _merged_with_params(params)
    _cmd_sync_defaults._backfill_standard_roster(merged, enabled=True)
    kept = _params_of(merged)

    assert kept['required_bots'] == kinds[0]
    assert kept['optional_bots'] == ','.join(kinds[1:])
    assert kept['bot_lists_provenance'] == 'answered'
    validation = upgrade.validate_bot_lists(kept)
    assert validation['state'] == 'clean'
    assert validation['checked_count'] == len(configured)


def test_sync_backfill_fills_absent_roster_and_never_clobbers_operator_answer():
    """The merge back-fills an absent roster and never clobbers an answer.

    Three cases in one pin: absent keys are filled with the standard roster, a
    present operator roster is left untouched, and an answered provenance with
    empty values is still an answer and stays untouched.
    """
    import _cmd_sync_defaults

    absent = _merged_with_params({})
    _cmd_sync_defaults._backfill_standard_roster(absent, enabled=True)
    filled = _params_of(absent)
    assert filled['required_bots'] == 'cuioss-review-bot,coderabbit'
    assert filled['optional_bots'] == 'sourcery'

    kinds = _live_kinds()
    operator = _merged_with_params({'required_bots': kinds[0], 'optional_bots': kinds[1]})
    _cmd_sync_defaults._backfill_standard_roster(operator, enabled=True)
    kept = _params_of(operator)
    assert kept['required_bots'] == kinds[0]
    assert kept['optional_bots'] == kinds[1]

    answered_empty = _merged_with_params({'required_bots': '', 'optional_bots': '', 'bot_lists_provenance': 'answered'})
    _cmd_sync_defaults._backfill_standard_roster(answered_empty, enabled=True)
    assert _params_of(answered_empty) == {
        'required_bots': '',
        'optional_bots': '',
        'bot_lists_provenance': 'answered',
    }


# =============================================================================
# Cleaned-dead-step order — the reconcile clears the dead id, then add-step works
# =============================================================================
#
# A configured phase-6 step id with no resolvable order blocks the step-map
# writers: `_resolve_step_orders` iterates EVERY configured id and fails
# `missing_order` on the first one it cannot order. The upgrade's Stage-2
# reconcile runs the shared dead-id resolver first, so a dead id is gone before
# the operator's next `add-step`. These tests drive that real order on a live
# marshal.json — reconcile, then `plan phase-6-finalize add-step` — so the ORDER
# is pinned rather than only the end state.


def _manage_config_add_step(step: str) -> dict:
    """Drive the real ``plan phase-6-finalize add-step`` handler on the staged config.

    ``_cmd_system_plan`` is loaded under a test-local name (never imported
    plainly — a sibling suite file-loads it, and a plain import here would put
    two copies in play, reachable by different routes and differing by
    collection order).
    """
    sys_plan = load_script_module(
        'plan-marshall',
        'manage-config',
        '_cmd_system_plan.py',
        module_name='_cmd_system_plan_for_cleaned_step_test',
    )
    return cast(
        dict,
        sys_plan.cmd_plan(argparse.Namespace(sub_noun='phase-6-finalize', verb='add-step', step=step, position=None)),
    )


def test_add_step_succeeds_on_a_config_the_upgrade_cleaned_of_a_dead_step(plan_context):
    """Prove the cleaned-dead-step order through the real command sequence.

    The dead id blocks ``add-step`` first (the matched negative control), the
    upgrade's Stage-2 reconcile clears it, and only then does ``add-step``
    succeed — the order the fix exists to guarantee.
    """
    import _cmd_sync_defaults

    marshal = plan_context.fixture_dir / 'marshal.json'
    marshal.write_text(
        json.dumps({'plan': {'phase-6-finalize': {'steps': {'default:push': {}, 'default:stale-step': {}}}}}),
        encoding='utf-8',
    )

    # Negative control: the dead id blocks order resolution, so add-step fails.
    blocked = _manage_config_add_step('default:create-pr')
    assert blocked['status'] == 'error'
    assert blocked['error'] == 'missing_order'

    # The upgrade's Stage-2 reconcile clears the dead id, leaving the live one.
    synced = _cmd_sync_defaults.cmd_sync_defaults(
        parse_ns('plan-marshall', 'manage-config', 'manage-config.py', 'sync-defaults', register=False)
    )
    assert synced['status'] == 'success'
    steps = json.loads(marshal.read_text(encoding='utf-8'))['plan']['phase-6-finalize']['steps']
    assert 'default:stale-step' not in steps
    assert 'default:push' in steps

    # ... and add-step now succeeds on the cleaned config.
    result = _manage_config_add_step('default:create-pr')
    assert result['status'] == 'success'
    assert 'default:create-pr' in json.loads(marshal.read_text(encoding='utf-8'))['plan']['phase-6-finalize']['steps']


# =============================================================================
# D4 executor bootstrap — validate against the newest cache before the plan
# =============================================================================
#
# ``upgrade.py plan`` bootstraps the serving executor (validate against the
# newest plugin-cache version, regenerate from that cache when stale) before
# emitting the stage plan, and reports a skill/planner version-split warning
# instead of a silently stale run. These tests drive the bootstrap against
# fixture cache roots and fixture executors — never the live environment — and
# pin the ``plan`` wiring through a monkeypatched bootstrap.


def _fixture_cache(root: Path, versions: list[str]) -> Path:
    """Build a fixture plugin-cache root carrying ``versions`` of plan-marshall."""
    cache = root / 'cache'
    for version in versions:
        (cache / 'plan-marshall' / version).mkdir(parents=True)
    return cache


def _fixture_executor(project_dir: Path, version: str) -> Path:
    """Write a fixture serving executor stamped ``version`` under ``project_dir``."""
    executor = project_dir / '.plan' / 'execute-script.py'
    executor.parent.mkdir(parents=True, exist_ok=True)
    executor.write_text(f"MARSHALL_VERSION = '{version}'\n", encoding='utf-8')
    return executor


def _fixture_meta_generator(clone_root: Path) -> Path:
    """Plant a fixture marketplace-source generator stub under ``clone_root``.

    Only its presence matters — regeneration itself is always faked in these
    tests, so the stub is never executed.
    """
    generator = (
        clone_root
        / 'marketplace'
        / 'bundles'
        / 'plan-marshall'
        / 'skills'
        / 'tools-script-executor'
        / 'scripts'
        / 'generate_executor.py'
    )
    generator.parent.mkdir(parents=True, exist_ok=True)
    generator.write_text('# fixture generator stub\n', encoding='utf-8')
    return generator


def _fixture_cache_generator(cache_root: Path, version: str) -> Path:
    """Plant a fixture newest-cache generator stub for ``version``."""
    generator = (
        cache_root / 'plan-marshall' / version / 'skills' / 'tools-script-executor' / 'scripts' / 'generate_executor.py'
    )
    generator.parent.mkdir(parents=True, exist_ok=True)
    generator.write_text('# fixture generator stub\n', encoding='utf-8')
    return generator


class _RegenerateFake:
    """Injectable regeneration seam: records calls, optionally rewrites the stamp."""

    def __init__(self, executor: Path, new_version: str, rc: int = 0):
        self._executor = executor
        self._new_version = new_version
        self._rc = rc
        self.calls: list[dict] = []

    def __call__(self, generator: Path, anchor: Path, project_dir: Path) -> tuple[int, str, str]:
        self.calls.append({'generator': generator, 'anchor': anchor, 'project_dir': project_dir})
        if self._rc == 0:
            self._executor.write_text(f"MARSHALL_VERSION = '{self._new_version}'\n", encoding='utf-8')
            return 0, 'status: success', ''
        return self._rc, '', 'fixture generation failure'


def test_plan_carries_bootstrap_block_by_default(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
    """A bare ``plan`` runs the bootstrap and merges its report into the output.

    The bootstrap itself is monkeypatched — this pins the WIRING (the consent
    flag is threaded as ``allow_regenerate``; the report merges beside the
    stages), not the bootstrap logic, which the fixture tests below cover.
    """
    sentinel = {
        'status': 'success',
        'action': 'fresh',
        'executor_version': '0.1.10',
        'newest_cache_version': '0.1.10',
        'executor_path': '/fixture/.plan/execute-script.py',
        'cache_root': '/fixture/cache',
        'generator': '',
        'warning': '',
        'detail': 'sentinel bootstrap',
    }
    seen: dict = {}
    monkeypatch.setattr(upgrade, 'bootstrap_executor', lambda **kwargs: seen.update(kwargs) or sentinel)

    exit_code, parsed = _run(
        ['plan', '--project-kind', 'meta', '--bootstrap', 'true'], capsys, monkeypatch, bootstrap=True
    )

    assert exit_code == 0
    assert parsed['bootstrap'] == sentinel
    assert seen == {'project_kind': 'meta', 'allow_regenerate': True}
    assert [stage['key'] for stage in parsed['stages']] == _EXPECTED_STAGE_KEYS


def test_plan_bootstrap_false_validates_without_regenerating(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    """``--bootstrap false`` (the default) validates and REPORTS, never rewrites.

    The bootstrap always runs — a missing executor must still be recovered — but
    the consent flag reaches it as ``allow_regenerate=False``, so a merely-stale
    executor is reported rather than rewritten unasked.
    """
    seen: dict = {}

    def _report(**kwargs):
        seen.update(kwargs)
        return dict(_FRESH_BOOTSTRAP_STUB)

    monkeypatch.setattr(upgrade, 'bootstrap_executor', _report)

    exit_code, parsed = _run(['plan', '--bootstrap', 'false'], capsys, monkeypatch, bootstrap=True)

    assert exit_code == 0
    assert seen['allow_regenerate'] is False
    assert [stage['key'] for stage in parsed['stages']] == _EXPECTED_STAGE_KEYS


def test_plan_default_does_not_authorise_regeneration(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
):
    """A bare ``plan`` passes ``allow_regenerate=False`` — the ask-first default."""
    seen: dict = {}

    monkeypatch.setattr(
        upgrade, 'bootstrap_executor', lambda **kwargs: seen.update(kwargs) or dict(_FRESH_BOOTSTRAP_STUB)
    )

    exit_code, _parsed = _run(['plan'], capsys, monkeypatch, bootstrap=True)

    assert exit_code == 0
    assert seen['allow_regenerate'] is False


def test_plan_propagates_bootstrap_error(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch):
    """A bootstrap ``status: error`` fails closed with no stage plan emitted."""
    monkeypatch.setattr(
        upgrade,
        'bootstrap_executor',
        lambda **kwargs: {'status': 'error', 'error': 'fixture bootstrap failure'},
    )

    exit_code, parsed = _run(['plan'], capsys, monkeypatch, bootstrap=True)

    assert exit_code == 0
    assert parsed['status'] == 'error'
    assert 'stages' not in parsed


def test_bootstrap_regenerates_stale_executor_from_newest_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """A stale fixture executor is regenerated from the newest cache version.

    The cache carries two versions (``0.1.9`` < ``0.1.10`` — the ordering the
    companion test below pins as numeric, never lexical); the executor sits at
    the older one. Regeneration is faked but OBSERVED: the fake rewrites the
    fixture stamp, and the report names the generator, the anchor, and the
    project dir it ran against.
    """
    cache = _fixture_cache(tmp_path, ['0.1.9', '0.1.10'])
    clone = tmp_path / 'clone'
    generator = _fixture_meta_generator(clone)
    executor = _fixture_executor(clone, '0.1.9')
    fake = _RegenerateFake(executor, '0.1.10')
    monkeypatch.chdir(clone)

    report = upgrade.bootstrap_executor(
        project_kind='meta', cache_root=cache, executor_path=executor, _run_generate=fake
    )

    assert report['status'] == 'success'
    assert report['action'] == 'regenerated'
    assert report['executor_version'] == '0.1.10'
    assert report['newest_cache_version'] == '0.1.10'
    assert report['warning'] == ''
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call['generator'] == generator
    assert call['anchor'] == clone
    assert call['project_dir'] == clone


def test_bootstrap_picks_the_numeric_newest_cache_version(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """``0.1.10`` beats ``0.1.9`` — the newest-cache choice is numeric, never lexical.

    A lexical max would crown ``0.1.9`` (``'9' > '1'``) and the stale executor
    at ``0.1.9`` would read ``fresh`` against it. The numeric choice reports
    ``0.1.10`` and regenerates.
    """
    cache = _fixture_cache(tmp_path, ['0.1.9', '0.1.10'])
    clone = tmp_path / 'clone'
    _fixture_meta_generator(clone)
    executor = _fixture_executor(clone, '0.1.9')
    fake = _RegenerateFake(executor, '0.1.10')
    monkeypatch.chdir(clone)

    report = upgrade.bootstrap_executor(
        project_kind='meta', cache_root=cache, executor_path=executor, _run_generate=fake
    )

    assert report['newest_cache_version'] == '0.1.10'
    assert report['action'] == 'regenerated'


def test_bootstrap_consumer_uses_the_newest_cache_generator(tmp_path: Path):
    """On ``consumer`` the generator resolves under the newest cache version dir."""
    cache = _fixture_cache(tmp_path, ['0.1.9', '0.1.10'])
    generator = _fixture_cache_generator(cache, '0.1.10')
    project = tmp_path / 'project'
    executor = _fixture_executor(project, '0.1.9')
    fake = _RegenerateFake(executor, '0.1.10')

    report = upgrade.bootstrap_executor(
        project_kind='consumer', cache_root=cache, executor_path=executor, _run_generate=fake
    )

    assert report['status'] == 'success'
    assert report['action'] == 'regenerated'
    assert len(fake.calls) == 1
    call = fake.calls[0]
    assert call['generator'] == generator
    assert call['anchor'] == cache / 'plan-marshall' / '0.1.10'
    assert call['project_dir'] == project


def test_bootstrap_fresh_executor_regenerates_nothing(tmp_path: Path):
    """An executor AT the newest cache version reports ``fresh`` and never regenerates."""
    cache = _fixture_cache(tmp_path, ['0.1.10'])
    project = tmp_path / 'project'
    executor = _fixture_executor(project, '0.1.10')
    fake = _RegenerateFake(executor, '0.1.10')

    report = upgrade.bootstrap_executor(
        project_kind='consumer', cache_root=cache, executor_path=executor, _run_generate=fake
    )

    assert report['status'] == 'success'
    assert report['action'] == 'fresh'
    assert report['warning'] == ''
    assert fake.calls == []


def test_bootstrap_no_cache_is_a_noop(tmp_path: Path):
    """A missing cache root reports ``no_cache`` — the fresh-install boundary, never a failure."""
    project = tmp_path / 'project'
    executor = _fixture_executor(project, '0.1.10')
    fake = _RegenerateFake(executor, '0.1.10')

    report = upgrade.bootstrap_executor(
        project_kind='consumer',
        cache_root=tmp_path / 'no-such-cache',
        executor_path=executor,
        _run_generate=fake,
    )

    assert report['status'] == 'success'
    assert report['action'] == 'no_cache'
    assert report['warning'] == ''
    assert fake.calls == []


def test_bootstrap_ahead_executor_warns_split_without_regenerating(tmp_path: Path):
    """A planner AHEAD of the newest cache warns the split and regenerates nothing.

    The installed skill surface lags the planner, so the router docs may
    describe stages the planner no longer emits. The warning names the split
    and the remedy; nothing is regenerated because there is nothing newer to
    regenerate from.
    """
    cache = _fixture_cache(tmp_path, ['0.1.10'])
    project = tmp_path / 'project'
    executor = _fixture_executor(project, '0.1.11')
    fake = _RegenerateFake(executor, '0.1.11')

    report = upgrade.bootstrap_executor(
        project_kind='consumer', cache_root=cache, executor_path=executor, _run_generate=fake
    )

    assert report['status'] == 'success'
    assert report['action'] == 'fresh'
    assert 'version split' in report['warning']
    assert '/plugin update plan-marshall' in report['warning']
    assert fake.calls == []


def test_bootstrap_missing_executor_recovers_without_consent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """A MISSING executor is restored even without consent — the recovery is ungated.

    Nothing can run against an absent executor, so consent to restore one is
    meaningless: the recovery path always regenerates from the newest cache,
    whatever ``allow_regenerate`` says.
    """
    cache = _fixture_cache(tmp_path, ['0.1.10'])
    clone = tmp_path / 'clone'
    _fixture_meta_generator(clone)
    (clone / '.plan').mkdir(parents=True, exist_ok=True)
    executor = clone / '.plan' / 'execute-script.py'  # never written — absent
    fake = _RegenerateFake(executor, '0.1.10')
    monkeypatch.chdir(clone)

    report = upgrade.bootstrap_executor(
        project_kind='meta',
        cache_root=cache,
        executor_path=executor,
        _run_generate=fake,
        allow_regenerate=False,
    )

    assert report['status'] == 'success'
    assert report['action'] == 'regenerated'
    assert len(fake.calls) == 1


def test_bootstrap_stale_executor_without_consent_is_reported_not_rewritten(tmp_path: Path):
    """A merely-STALE executor without consent is reported, never rewritten unasked."""
    cache = _fixture_cache(tmp_path, ['0.1.9', '0.1.10'])
    project = tmp_path / 'project'
    executor = _fixture_executor(project, '0.1.9')
    fake = _RegenerateFake(executor, '0.1.10')

    report = upgrade.bootstrap_executor(
        project_kind='consumer',
        cache_root=cache,
        executor_path=executor,
        _run_generate=fake,
        allow_regenerate=False,
    )

    assert report['status'] == 'success'
    assert report['action'] == 'regenerate_required'
    assert 'bootstrap true' in report['warning']
    assert fake.calls == []


def test_bootstrap_missing_generator_is_unknown(tmp_path: Path):
    """A stale executor with no resolvable generator reports ``unknown``, never a vacuous ``fresh``."""
    cache = _fixture_cache(tmp_path, ['0.1.10'])
    project = tmp_path / 'project'
    executor = _fixture_executor(project, '0.1.9')
    fake = _RegenerateFake(executor, '0.1.10')

    report = upgrade.bootstrap_executor(
        project_kind='consumer', cache_root=cache, executor_path=executor, _run_generate=fake
    )

    assert report['status'] == 'success'
    assert report['action'] == 'unknown'
    assert report['warning'] != ''
    assert fake.calls == []


def test_bootstrap_regenerate_failure_reports_split(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """A failed regeneration reports ``regenerate_failed`` with the split warning.

    The plan is still emitted downstream (Stage 1's ``regenerate-executor``
    remains the repair) — the failure is reported, never fatal and never
    silent.
    """
    cache = _fixture_cache(tmp_path, ['0.1.10'])
    clone = tmp_path / 'clone'
    _fixture_meta_generator(clone)
    executor = _fixture_executor(clone, '0.1.9')
    fake = _RegenerateFake(executor, '0.1.10', rc=1)
    monkeypatch.chdir(clone)

    report = upgrade.bootstrap_executor(
        project_kind='meta', cache_root=cache, executor_path=executor, _run_generate=fake
    )

    assert report['status'] == 'success'
    assert report['action'] == 'regenerate_failed'
    assert 'version split' in report['warning']
    assert '/plugin update plan-marshall' in report['warning']


def test_bootstrap_regenerate_success_with_missing_stamp_warns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Generator success with a missing stamp reports ``regenerated`` with a warning, never the stale version.

    The fake succeeds (rc=0) but leaves no stamp behind, so the reread is
    ``unreadable``. The report must carry the reread fact — empty version plus
    a non-empty warning — rather than retaining the stale pre-regeneration
    version as if it had been re-observed.
    """
    cache = _fixture_cache(tmp_path, ['0.1.10'])
    clone = tmp_path / 'clone'
    _fixture_meta_generator(clone)
    executor = _fixture_executor(clone, '0.1.9')
    calls: list[dict] = []

    def _vanishing_generate(generator: Path, anchor: Path, project_dir: Path) -> tuple[int, str, str]:
        calls.append({'generator': generator, 'anchor': anchor, 'project_dir': project_dir})
        executor.unlink()
        return 0, 'status: success', ''

    monkeypatch.chdir(clone)

    report = upgrade.bootstrap_executor(
        project_kind='meta', cache_root=cache, executor_path=executor, _run_generate=_vanishing_generate
    )

    assert report['status'] == 'success'
    assert report['action'] == 'regenerated'
    assert report['executor_version'] == ''
    assert report['warning'] != ''
    assert 'unreadable' in report['warning']
    assert len(calls) == 1


def test_bootstrap_regenerate_success_with_empty_stamp_warns(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Generator success with an empty stamp reports ``regenerated`` with a warning, never silent.

    The fake succeeds (rc=0) but writes an empty ``MARSHALL_VERSION``, so the
    reread is ``empty``. An empty version with no warning would read as a clean
    regeneration of nothing — the warning names the unconfirmed version.
    """
    cache = _fixture_cache(tmp_path, ['0.1.10'])
    clone = tmp_path / 'clone'
    _fixture_meta_generator(clone)
    executor = _fixture_executor(clone, '0.1.9')

    def _empty_generate(generator: Path, anchor: Path, project_dir: Path) -> tuple[int, str, str]:
        executor.write_text("MARSHALL_VERSION = ''\n", encoding='utf-8')
        return 0, 'status: success', ''

    monkeypatch.chdir(clone)

    report = upgrade.bootstrap_executor(
        project_kind='meta', cache_root=cache, executor_path=executor, _run_generate=_empty_generate
    )

    assert report['status'] == 'success'
    assert report['action'] == 'regenerated'
    assert report['executor_version'] == ''
    assert report['warning'] != ''
    assert 'empty' in report['warning']


def test_resolve_bootstrap_action_table():
    """The pure decision table: equal, behind, unreadable, absent, split."""
    assert upgrade.resolve_bootstrap_action('0.1.10', '0.1.10') == ('fresh', '')
    assert upgrade.resolve_bootstrap_action('0.1.9', '0.1.10') == ('regenerate_required', '')
    # An unreadable or non-numeric stamp regenerates rather than reading fresh.
    assert upgrade.resolve_bootstrap_action(None, '0.1.10') == ('regenerate_required', '')
    assert upgrade.resolve_bootstrap_action('bogus', '0.1.10') == ('regenerate_required', '')
    assert upgrade.resolve_bootstrap_action('0.1.9', None) == ('no_cache', '')
    action, warning = upgrade.resolve_bootstrap_action('0.1.11', '0.1.10')
    assert action == 'fresh'
    assert 'version split' in warning


def test_bootstrap_generate_anchors_discovery_via_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """The regeneration subprocess pins discovery via ``PM_MARKETPLACE_ROOT``.

    ``discover_scripts`` propagates the marketplace root to its scan subprocess
    only through that env anchor — a bare flag degrades to the version-unaware
    glob fallback. The captured subprocess invocation proves the anchor, the
    generator argv, and the pinned cwd.
    """
    import subprocess

    seen: dict = {}

    def _fake_run(argv, cwd, capture_output, text, timeout, env):
        seen['argv'] = argv
        seen['cwd'] = cwd
        seen['env_anchor'] = env.get('PM_MARKETPLACE_ROOT')

        class _Result:
            returncode = 0
            stdout = 'status: success'
            stderr = ''

        return _Result()

    monkeypatch.setattr(subprocess, 'run', _fake_run)
    generator = tmp_path / 'generate_executor.py'
    generator.write_text('# fixture\n', encoding='utf-8')
    anchor = tmp_path / 'anchor'
    project = tmp_path / 'project'

    rc, _out, _err = upgrade._run_bootstrap_generate(generator, anchor, project)

    assert rc == 0
    assert seen['argv'] == ['python3', str(generator), 'generate']
    assert seen['env_anchor'] == str(anchor)
    assert seen['cwd'] == str(project)
