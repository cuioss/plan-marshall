# SPDX-License-Identifier: FSL-1.1-ALv2
"""Fixture-driven tests for the plugin pin-trap detector (``_plugin_pin_trap``).

The live plugin cache, registry, and executor are NOT present in a fresh clone —
they live on an operator's machine — so every test here drives the oracle and the
filesystem adapters against constructed observations and ``tmp_path`` fixtures.

Coverage of the plan's D7 test matrix:
  * (a) each of the six failure shapes is detected, and shape 6 is classified
    distinctly from shape 1;
  * (b) a healthy state passes;
  * (c) a dispatched load from a non-pinned version is reported (D2);
  * (d) two disagreeing samples yield ``indeterminate``, not a verdict;
  * (e) the NEGATIVE CONTROL — a tree where two consumers agree and the third
    does not — which a pairwise oracle passes and this one MUST fail;
  * (f) is exercised in the executor's own test module (SystemExit → glob
    fallback keeping ``latest.py``).

Plus the D1 conjunct properties (content as a count not a boolean; the unmarked
set reported as registry-derived; sampling instant / population / marker age
published), the D3 remedy text, the D4 loader-selection model, and the live
adapters.
"""

from datetime import UTC, datetime
from pathlib import Path

from conftest import load_script_module

_ppt = load_script_module('pm-plugin-development', 'plugin-doctor', '_plugin_pin_trap.py', 'plugin_pin_trap')

VersionDir = _ppt.VersionDir
ContentComparison = _ppt.ContentComparison
StoreObservation = _ppt.StoreObservation
evaluate = _ppt.evaluate
assert_loaded_version = _ppt.assert_loaded_version
loader_selected_version = _ppt.loader_selected_version

PASS = _ppt.OUTCOME_PASS
FAIL = _ppt.OUTCOME_FAIL
INDET = _ppt.OUTCOME_INDETERMINATE

SHAPE_1 = _ppt.SHAPE_1_SATURATION
SHAPE_2 = _ppt.SHAPE_2_PIN_MARKED_NEWER_UNMARKED
SHAPE_3 = _ppt.SHAPE_3_STALE_UNMARKED_BESIDE_PIN
SHAPE_4 = _ppt.SHAPE_4_PIN_DIVERGES_FROM_SOURCE
SHAPE_5 = _ppt.SHAPE_5_REGISTRY_SELF_DISAGREES
SHAPE_6 = _ppt.SHAPE_6_DIVERGENCE_NO_GC


# ---------------------------------------------------------------------------
# Fixture builder — a HEALTHY observation, with overrides per test.
# ---------------------------------------------------------------------------
def _obs(**overrides):
    base = {
        'executor_version': '0.1.200',
        'install_path_version': '0.1.200',
        'registry_version': '0.1.200',
        'version_dirs': (VersionDir('0.1.200', marked=False),),
        'content': ContentComparison(matched=360, total=360, diverged=0),
        'newest_marker_age_seconds': None,
    }
    base.update(overrides)
    return StoreObservation(**base)


def _verdict(obs):
    """Double-sample against an identical second sample (the agreeing case)."""
    return evaluate(obs, obs, sampling_instant='2026-08-13T00:00:00Z')


# ---------------------------------------------------------------------------
# (b) A healthy state passes.
# ---------------------------------------------------------------------------
def test_healthy_state_passes():
    verdict = _verdict(_obs())
    assert verdict.outcome == PASS
    assert verdict.shapes == ()
    assert verdict.divergences == ()
    assert verdict.gc_exposures == ()
    assert verdict.remedy == ''


# ---------------------------------------------------------------------------
# (a) Each of the six shapes is detected.
# ---------------------------------------------------------------------------
def test_shape1_empty_unmarked_set_is_fail():
    # Every version dir is orphan-marked (GC saturation) — a naive `unmarked == []`
    # check reads this as "nothing stale"; the oracle reports it as a fail on the
    # GC-exposure axis.
    obs = _obs(version_dirs=(VersionDir('0.1.200', marked=True),))
    verdict = _verdict(obs)
    assert verdict.outcome == FAIL
    assert SHAPE_1 in verdict.shapes
    assert verdict.gc_exposures  # saturation is a GC exposure


def test_shape2_pin_orphan_marked_while_newer_unmarked():
    obs = _obs(
        install_path_version='0.1.100',
        registry_version='0.1.100',
        executor_version='0.1.100',
        version_dirs=(VersionDir('0.1.100', marked=True), VersionDir('0.1.200', marked=False)),
    )
    verdict = _verdict(obs)
    assert verdict.outcome == FAIL
    assert SHAPE_2 in verdict.shapes
    assert verdict.gc_exposures  # the pin dir is marked (scheduled for deletion)


def test_shape3_stale_unmarked_beside_pin_seats_session_backward():
    # Two unmarked dirs: the registry pin (0.1.100) and a stale dir whose NAME
    # sorts higher (0.1.300). The loader follows the higher version-key, seating
    # the session off the pin.
    obs = _obs(
        install_path_version='0.1.100',
        registry_version='0.1.100',
        executor_version='0.1.100',
        version_dirs=(VersionDir('0.1.300', marked=False), VersionDir('0.1.100', marked=False)),
    )
    verdict = _verdict(obs)
    assert verdict.outcome == FAIL
    assert SHAPE_3 in verdict.shapes
    assert verdict.loader_selected_version == '0.1.300'  # NOT the pin
    assert not verdict.gc_exposures  # nothing is marked


def test_shape4_pin_diverges_from_source_while_keepset_and_registry_agree():
    # The only unmarked dir IS the pin, the registry agrees with itself and the
    # executor — yet the pin content diverges from source on 8 of 360 files. The
    # keep-set and registry agree WITH EACH OTHER and say nothing about the repo.
    obs = _obs(
        version_dirs=(VersionDir('0.1.200', marked=False), VersionDir('0.1.100', marked=True)),
        content=ContentComparison(matched=352, total=360, diverged=8),
    )
    verdict = _verdict(obs)
    assert verdict.outcome == FAIL
    assert SHAPE_4 in verdict.shapes
    # Reported as a count, never a boolean.
    assert '352 of 360 files match; 8 diverge' in verdict.content


def test_shape5_registry_two_fields_disagree():
    obs = _obs(install_path_version='0.1.200', registry_version='0.1.199')
    verdict = _verdict(obs)
    assert verdict.outcome == FAIL
    assert SHAPE_5 in verdict.shapes
    assert any('installPath' in d and 'version' in d for d in verdict.divergences)


def test_shape6_divergence_without_gc_exposure():
    # Pure executor drift: one unmarked dir (the pin), registry self-consistent,
    # content matches — but the executor is anchored at a different version. A
    # divergence with NO GC exposure.
    obs = _obs(executor_version='0.1.100')
    verdict = _verdict(obs)
    assert verdict.outcome == FAIL
    assert SHAPE_6 in verdict.shapes
    assert not verdict.gc_exposures


def test_shape6_is_classified_distinctly_from_shape1():
    # The plan's D7(a) sharpest requirement: shape 6 (repair-when-convenient) must
    # NOT be conflated with shape 1 (repair-before-the-fuse-burns).
    shape6 = _verdict(_obs(executor_version='0.1.100'))
    shape1 = _verdict(_obs(version_dirs=(VersionDir('0.1.200', marked=True),)))
    assert SHAPE_6 in shape6.shapes and SHAPE_1 not in shape6.shapes
    assert SHAPE_1 in shape1.shapes and SHAPE_6 not in shape1.shapes
    # Separate axes: shape 6 sits on divergence-only; shape 1 carries GC exposure.
    assert shape6.divergences and not shape6.gc_exposures
    assert shape1.gc_exposures


# ---------------------------------------------------------------------------
# (e) THE NEGATIVE CONTROL — two consumers agree, the third does not.
# A pairwise (executor == installPath) formulation PASSES this; the oracle must
# FAIL it via the separate installPath == version conjunct.
# ---------------------------------------------------------------------------
def test_negative_control_two_agree_third_disagrees_must_fail():
    obs = _obs(
        executor_version='0.1.200',   # agrees with installPath
        install_path_version='0.1.200',
        registry_version='0.1.050',   # the third — disagrees
    )
    verdict = _verdict(obs)
    assert verdict.outcome == FAIL, 'a pairwise executor==installPath oracle would wrongly pass this'
    assert SHAPE_5 in verdict.shapes


def test_negative_control_other_orientation_executor_is_the_odd_one():
    obs = _obs(
        executor_version='0.1.050',   # the odd one out
        install_path_version='0.1.200',
        registry_version='0.1.200',
    )
    verdict = _verdict(obs)
    assert verdict.outcome == FAIL
    assert any('executor' in d for d in verdict.divergences)


# ---------------------------------------------------------------------------
# (d) Two disagreeing samples yield indeterminate.
# ---------------------------------------------------------------------------
def test_disagreeing_samples_yield_indeterminate():
    sample_a = _obs()
    sample_b = _obs(version_dirs=(VersionDir('0.1.200', marked=True),))  # a marker landed between reads
    verdict = evaluate(sample_a, sample_b, sampling_instant='2026-08-13T00:00:00Z')
    assert verdict.outcome == INDET
    assert 'read_during_write' in verdict.reason


def test_could_not_look_is_indeterminate_not_pass():
    # A store that could not be read must be distinguishable from a clean pass.
    obs = _obs(executor_version=None)
    verdict = _verdict(obs)
    assert verdict.outcome == INDET
    assert 'could_not_look' in verdict.reason


def test_content_not_compared_is_indeterminate_not_pass():
    obs = _obs(content=None)
    verdict = _verdict(obs)
    assert verdict.outcome == INDET


# ---------------------------------------------------------------------------
# (c) A dispatched load from a non-pinned version is reported (D2).
# ---------------------------------------------------------------------------
def test_assert_loaded_version_reports_non_pinned_load():
    verdict = assert_loaded_version('/h/.claude/plugins/cache/plan-marshall/0.1.050/skills/persona/x', '0.1.200')
    assert verdict.outcome == FAIL
    assert verdict.got_version == '0.1.050'
    assert verdict.expected_version == '0.1.200'
    assert '0.1.050' in verdict.reason


def test_assert_loaded_version_matches_pin_passes():
    verdict = assert_loaded_version('/h/.claude/plugins/cache/plan-marshall/0.1.200/skills/persona/x', '0.1.200')
    assert verdict.outcome == PASS
    assert verdict.got_version == '0.1.200'


def test_assert_loaded_version_unparseable_is_indeterminate():
    verdict = assert_loaded_version('/opt/somewhere/without/a/version', '0.1.200')
    assert verdict.outcome == INDET
    assert verdict.got_version is None


# ---------------------------------------------------------------------------
# D3 — the operator remedy is stated, not implied.
# ---------------------------------------------------------------------------
def test_fail_verdict_states_operator_remedy_including_no_restart_and_in_run():
    verdict = _verdict(_obs(executor_version='0.1.100'))
    assert 'operator-only' in verdict.remedy
    assert 'restart does NOT fix' in verdict.remedy
    assert 'read the pinned skill file' in verdict.remedy.lower() or 'installPath' in verdict.remedy
    assert 'Do NOT write the plugin registry' in verdict.remedy


# ---------------------------------------------------------------------------
# D4 — loader selection under two unmarked directories (from the selector code).
# ---------------------------------------------------------------------------
def test_loader_follows_highest_version_key_among_unmarked():
    dirs = (VersionDir('0.1.100', marked=False), VersionDir('0.1.300', marked=False))
    assert loader_selected_version(dirs) == '0.1.300'


def test_loader_ignores_marker_on_retention_pinned_newest():
    # The newest-on-disk dir's marker is ignored outright (retention pin).
    dirs = (VersionDir('0.1.300', marked=True), VersionDir('0.1.100', marked=False))
    assert loader_selected_version(dirs) == '0.1.300'


def test_loader_saturation_falls_back_to_newest():
    dirs = (VersionDir('0.1.100', marked=True), VersionDir('0.1.050', marked=True))
    # 0.1.100 is the newest-on-disk pin, so it is treated as live and wins.
    assert loader_selected_version(dirs) == '0.1.100'


def test_loader_empty_is_none():
    assert loader_selected_version(()) is None


# ---------------------------------------------------------------------------
# D1 reporting properties — sampling instant, population, marker age, notes.
# ---------------------------------------------------------------------------
def test_verdict_publishes_sampling_instant_population_and_marker_age():
    obs = _obs(
        version_dirs=(VersionDir('0.1.200', marked=False), VersionDir('0.1.100', marked=True)),
        newest_marker_age_seconds=42.0,
    )
    verdict = _verdict(obs)
    assert verdict.sampling_instant == '2026-08-13T00:00:00Z'
    assert verdict.population_size == 2
    assert verdict.newest_marker_age_seconds == 42.0


def test_verdict_notes_state_unmarked_set_is_registry_derived():
    verdict = _verdict(_obs())
    joined = ' '.join(verdict.notes)
    assert 'REGISTRY-DERIVED' in joined
    assert 'session' in joined.lower()  # the fourth-consumer note
    assert verdict.field_read == 'installPath'  # names the field it read


def test_verdict_to_dict_round_trips_fields():
    payload = _verdict(_obs()).to_dict()
    assert payload['outcome'] == PASS
    assert payload['field_read'] == 'installPath'
    assert 'notes' in payload and isinstance(payload['notes'], list)


# ---------------------------------------------------------------------------
# ContentComparison — count, never boolean; partial scan says so.
# ---------------------------------------------------------------------------
def test_content_comparison_full_scan_render():
    assert ContentComparison(matched=360, total=360, diverged=0).render() == '360 of 360 files match; 0 diverge'


def test_content_comparison_partial_scan_says_so():
    cc = ContentComparison(matched=100, total=360, diverged=10, scanned=110)
    assert cc.partial
    assert 'PARTIAL scan: 110 of 360 scanned' in cc.render()


# ---------------------------------------------------------------------------
# Live filesystem adapters — driven by tmp_path fixtures.
# ---------------------------------------------------------------------------
def _make_version_dir(bundle: Path, name: str, *, marked: bool, files: dict[str, str] | None = None) -> Path:
    vdir = bundle / name
    (vdir / 'skills').mkdir(parents=True, exist_ok=True)
    for rel, content in (files or {}).items():
        target = vdir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding='utf-8')
    if marked:
        (vdir / '.orphaned_at').write_text('2026-08-13T00:00:00Z', encoding='utf-8')
    return vdir


def test_observe_cache_version_dirs_reads_marker_existence(tmp_path):
    bundle = tmp_path / 'plan-marshall'
    _make_version_dir(bundle, '0.1.100', marked=True)
    _make_version_dir(bundle, '0.1.200', marked=False)
    dirs, marker_age = _ppt.observe_cache_version_dirs(bundle, now=datetime.now(UTC))
    by_name = {d.name: d.marked for d in dirs}
    assert by_name == {'0.1.100': True, '0.1.200': False}
    assert marker_age is not None and marker_age >= 0.0


def test_observe_cache_version_dirs_missing_bundle_is_empty(tmp_path):
    dirs, marker_age = _ppt.observe_cache_version_dirs(tmp_path / 'nope')
    assert dirs == ()
    assert marker_age is None


def test_read_registry_entry_top_level_keyed(tmp_path):
    registry = tmp_path / 'config.json'
    registry.write_text(
        '{"plan-marshall": {"installPath": "/c/plan-marshall/0.1.200", "version": "0.1.200"},'
        ' "third-party": {"installPath": "/c/tp/1.0.0", "version": "1.0.0"}}',
        encoding='utf-8',
    )
    assert _ppt.read_registry_entry(registry, 'plan-marshall') == ('0.1.200', '0.1.200')
    assert _ppt.read_registry_entry(registry, 'third-party') == ('1.0.0', '1.0.0')


def test_read_registry_entry_under_plugins_and_list_forms(tmp_path):
    nested = tmp_path / 'nested.json'
    nested.write_text('{"plugins": {"plan-marshall": {"installPath": "/c/pm/0.1.9", "version": "0.1.9"}}}', 'utf-8')
    assert _ppt.read_registry_entry(nested, 'plan-marshall') == ('0.1.9', '0.1.9')

    listed = tmp_path / 'list.json'
    listed.write_text('[{"name": "plan-marshall", "installPath": "/c/pm/0.1.8", "version": "0.1.8"}]', 'utf-8')
    assert _ppt.read_registry_entry(listed, 'plan-marshall') == ('0.1.8', '0.1.8')


def test_read_registry_entry_missing_or_unreadable_is_none(tmp_path):
    assert _ppt.read_registry_entry(tmp_path / 'absent.json', 'plan-marshall') == (None, None)
    bad = tmp_path / 'bad.json'
    bad.write_text('{not json', encoding='utf-8')
    assert _ppt.read_registry_entry(bad, 'plan-marshall') == (None, None)


def test_read_executor_anchored_version_extracts_single_version(tmp_path):
    executor = tmp_path / 'execute-script.py'
    executor.write_text(
        'SCRIPTS = {\n'
        '  "a:b:c": "/h/.claude/plugins/cache/plan-marshall/0.1.200/skills/b/scripts/c.py",\n'
        '  "d:e:f": "/h/.claude/plugins/cache/plan-marshall/0.1.200/skills/e/scripts/f.py",\n'
        '}\n',
        encoding='utf-8',
    )
    assert _ppt.read_executor_anchored_version(executor) == '0.1.200'


def test_read_executor_anchored_version_split_is_none(tmp_path):
    # An internally version-split executor is not a single anchored version.
    executor = tmp_path / 'execute-script.py'
    executor.write_text(
        '"/h/.claude/plugins/cache/plan-marshall/0.1.200/skills/b/scripts/c.py"\n'
        '"/h/.claude/plugins/cache/plan-marshall/0.1.100/skills/e/scripts/f.py"\n',
        encoding='utf-8',
    )
    assert _ppt.read_executor_anchored_version(executor) is None


def test_compare_pin_content_reports_counts(tmp_path):
    source = tmp_path / 'source'
    pin = tmp_path / 'pin'
    for base in (source, pin):
        (base / 'skills' / 's' / 'scripts').mkdir(parents=True)
    (source / 'skills' / 's' / 'scripts' / 'a.py').write_text('print(1)\n', encoding='utf-8')
    (pin / 'skills' / 's' / 'scripts' / 'a.py').write_text('print(1)\n', encoding='utf-8')
    (source / 'skills' / 's' / 'scripts' / 'b.py').write_text('SOURCE\n', encoding='utf-8')
    (pin / 'skills' / 's' / 'scripts' / 'b.py').write_text('STALE\n', encoding='utf-8')
    cc = _ppt.compare_pin_content(pin, source)
    assert cc.total == 2
    assert cc.matched == 1
    assert cc.diverged == 1


def test_observe_assembles_full_observation(tmp_path):
    cache = tmp_path / 'cache'
    bundle = cache / 'plan-marshall'
    _make_version_dir(
        bundle,
        '0.1.200',
        marked=False,
        files={'skills/s/scripts/a.py': 'print(1)\n'},
    )
    source = tmp_path / 'source'
    (source / 'skills' / 's' / 'scripts').mkdir(parents=True)
    (source / 'skills' / 's' / 'scripts' / 'a.py').write_text('print(1)\n', encoding='utf-8')

    registry = tmp_path / 'config.json'
    registry.write_text('{"plan-marshall": {"installPath": "/c/plan-marshall/0.1.200", "version": "0.1.200"}}', 'utf-8')

    executor = tmp_path / 'execute-script.py'
    executor.write_text('"/x/cache/plan-marshall/0.1.200/skills/s/scripts/a.py"\n', encoding='utf-8')

    obs = _ppt.observe(
        cache_bundle_dir=bundle,
        registry_path=registry,
        plugin_name='plan-marshall',
        executor_path=executor,
        source_dir=source,
        now=datetime.now(UTC),
    )
    assert obs.install_path_version == '0.1.200'
    assert obs.registry_version == '0.1.200'
    assert obs.executor_version == '0.1.200'
    assert obs.content is not None and obs.content.diverged == 0
    verdict = evaluate(obs, obs, sampling_instant='2026-08-13T00:00:00Z')
    assert verdict.outcome == PASS
