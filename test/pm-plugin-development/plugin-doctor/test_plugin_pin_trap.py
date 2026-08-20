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
SHAPE_3 = _ppt.SHAPE_3_LOADER_FOLLOWS_NON_PIN_DIR
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
def test_shape1_saturation_is_reported_and_is_not_itself_a_failure():
    """Saturation is a GC-exposure OBSERVATION, not a load-safety failure.

    A naive ``unmarked == []`` check reads a fully-marked cache as "nothing
    stale", so the shape is still detected and reported. It no longer FAILS on
    its own: the loader never consults the marker, so every dir being marked
    still resolves to the newest eligible dir and seats no session on the wrong
    body. What remains is a deletion risk from the foreign collector.

    This tree is still a FAIL — and saturation is not why. Every dir being
    marked includes the PIN dir whenever the pin is present, and that exposure
    (the pin scheduled for deletion) does block. Saturation therefore cannot be
    the sole signal in any tree with a readable registry; the case where the
    re-ranking changes the OUTCOME is the next test.
    """
    obs = _obs(version_dirs=(VersionDir('0.1.200', marked=True),))
    verdict = _verdict(obs)
    assert SHAPE_1 in verdict.shapes
    assert SHAPE_1 in _ppt.NON_BLOCKING_SHAPES
    assert any('saturation' in g for g in verdict.gc_exposures)
    assert verdict.outcome == FAIL
    assert any('orphan-marked' in g for g in verdict.gc_exposures)


def test_saturation_with_an_unreadable_registry_is_indeterminate_not_fail():
    """Saturation alone no longer converts a could-not-look into a verdict.

    With the registry unreadable there is no pin dir to be exposed and no
    divergence to compute, so saturation was the only entry on the shape list —
    and it turned "the registry could not be read" into a confident FAIL. The
    honest answer is ``indeterminate``: the shape is still reported, but the
    reason the run cannot issue a verdict is the unreadable store.
    """
    obs = _obs(
        install_path_version=None,
        registry_version=None,
        version_dirs=(VersionDir('0.1.200', marked=True),),
    )
    verdict = _verdict(obs)
    assert verdict.outcome == INDET
    assert 'could_not_look' in verdict.reason
    assert SHAPE_1 in verdict.shapes
    assert any('saturation' in g for g in verdict.gc_exposures)


def test_saturation_alongside_a_real_divergence_still_fails():
    """The control: saturation suppresses nothing else.

    Without it, making saturation non-blocking would be indistinguishable from
    making a saturated observation unfailable.
    """
    obs = _obs(
        executor_version='0.1.100',
        version_dirs=(VersionDir('0.1.200', marked=True),),
    )
    verdict = _verdict(obs)
    assert verdict.outcome == FAIL
    assert SHAPE_1 in verdict.shapes
    assert any('executor' in d for d in verdict.divergences)


def test_a_marked_pin_dir_still_fails():
    """The other GC exposure — the pin dir itself scheduled for deletion — still fails.

    Pins that the non-blocking carve-out is scoped to saturation and did not
    disarm the GC-exposure axis as a whole.
    """
    obs = _obs(version_dirs=(VersionDir('0.1.200', marked=True), VersionDir('0.1.100', marked=False)))
    verdict = _verdict(obs)
    assert verdict.outcome == FAIL
    assert any('orphan-marked' in g for g in verdict.gc_exposures)


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


def test_shape3_loader_follows_a_non_pin_dir_seats_session_backward():
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
    # Step (3) was the bare phrase "regenerate the executor" — a goal, not a
    # command. The surface that performs it is named here as well as in the
    # all-three-steps test below, because this is the test the gap names.
    assert '/marshall-steward' in verdict.remedy


def test_every_operator_repair_step_names_an_invocable_surface():
    """All three repair steps name something the operator can actually run.

    Steps (1) and (2) named ``/sync-plugin-cache`` and the steward's
    ``cache_retention sweep``; step (3) was the bare phrase "regenerate the
    executor" — a goal, not a command, leaving the operator to guess which
    surface performs it.
    """
    remedy = _verdict(_obs(executor_version='0.1.100')).remedy

    assert '/sync-plugin-cache' in remedy
    assert '/marshall-steward' in remedy
    # The retention sweep must be given in the form that actually PRUNES. Without
    # `--apply` it is a read-only dry run, so a remedy naming the bare verb
    # describes a repair that does not happen and reports no error while not
    # happening — the false-clean shape this whole module exists to prevent,
    # committed by its own remedy text.
    assert (
        'python3 .plan/execute-script.py '
        'plan-marshall:marshall-steward:cache_retention sweep --apply' in remedy
    )


# ---------------------------------------------------------------------------
# D4 — loader selection under two unmarked directories (from the selector code).
# ---------------------------------------------------------------------------
def test_loader_follows_highest_version_key_among_unmarked():
    dirs = (VersionDir('0.1.100', marked=False), VersionDir('0.1.300', marked=False))
    assert loader_selected_version(dirs) == '0.1.300'


def test_loader_is_marker_insensitive_when_the_newest_dir_is_marked():
    # The marker is never consulted: the newest dir wins whether or not it carries one.
    dirs = (VersionDir('0.1.300', marked=True), VersionDir('0.1.100', marked=False))
    assert loader_selected_version(dirs) == '0.1.300'


def test_loader_is_marker_insensitive_when_every_dir_is_marked():
    dirs = (VersionDir('0.1.100', marked=True), VersionDir('0.1.050', marked=True))
    # No fallback branch is involved: the newest dir wins, markers unread.
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


def test_compare_pin_content_partial_scan_when_a_source_file_is_unreadable(tmp_path, monkeypatch):
    """An unreadable SOURCE file leaves the scan partial, and ``render()`` says so.

    Driven through ``compare_pin_content`` rather than the dataclass
    constructor: a hand-built ``ContentComparison`` accepts any ``scanned``
    value, so constructing one proves nothing about whether the adapter can ever
    reach a partial state. The distinction is the whole point — a file the pin
    merely LACKS is a divergence (scanned, and reported), while a source file
    that cannot be READ is genuinely unscanned and degrades the comparison.
    """
    source = tmp_path / 'source'
    pin = tmp_path / 'pin'
    for base in (source, pin):
        (base / 'skills' / 's').mkdir(parents=True)
        (base / 'skills' / 's' / 'ok.py').write_text('print(1)\n', encoding='utf-8')
        (base / 'skills' / 's' / 'locked.py').write_text('print(2)\n', encoding='utf-8')

    blocked = (source / 'skills' / 's' / 'locked.py').resolve()
    real_read_bytes = Path.read_bytes

    def _read_bytes(self):
        if self.resolve() == blocked:
            raise PermissionError(13, 'Permission denied', str(self))
        return real_read_bytes(self)

    monkeypatch.setattr(Path, 'read_bytes', _read_bytes)

    cc = _ppt.compare_pin_content(pin, source)

    assert cc.total == 2
    assert cc.partial is True
    assert cc.scanned_count == 1
    assert 'PARTIAL scan: 1 of 2 scanned' in cc.render()


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
    anchor = _ppt.read_executor_anchored_version(executor)
    assert anchor.status == _ppt.EXECUTOR_ANCHORED
    assert anchor.version == '0.1.200'


def test_read_executor_anchored_version_split_names_the_conflicting_versions(tmp_path):
    """A version-split executor is reported as SPLIT, naming every version found.

    It is not "unreadable": the file was read and its embedded paths disagree
    with each other, which is a demonstrated divergence rather than an absence of
    evidence. ``version`` stays ``None`` so the load-safety gate remains
    fail-closed.
    """
    executor = tmp_path / 'execute-script.py'
    executor.write_text(
        '"/h/.claude/plugins/cache/plan-marshall/0.1.200/skills/b/scripts/c.py"\n'
        '"/h/.claude/plugins/cache/plan-marshall/0.1.100/skills/e/scripts/f.py"\n',
        encoding='utf-8',
    )
    anchor = _ppt.read_executor_anchored_version(executor)
    assert anchor.status == _ppt.EXECUTOR_SPLIT
    assert anchor.version is None
    assert anchor.versions == ('0.1.100', '0.1.200')


def test_read_executor_anchor_distinguishes_unreadable_from_unanchored(tmp_path):
    """A missing executor and an anchor-less one are DIFFERENT states.

    Both leave ``version`` at ``None``, and the old reader collapsed them — and
    a split executor — into that single ``None``.
    """
    missing = tmp_path / 'absent' / 'execute-script.py'
    assert _ppt.read_executor_anchored_version(missing).status == _ppt.EXECUTOR_UNREADABLE

    unanchored = tmp_path / 'execute-script.py'
    unanchored.write_text('"marketplace/bundles/b/skills/s/scripts/c.py"\n', encoding='utf-8')
    anchor = _ppt.read_executor_anchored_version(unanchored)
    assert anchor.status == _ppt.EXECUTOR_NO_ANCHOR
    assert anchor.version is None
    assert anchor.versions == ()


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


# ---------------------------------------------------------------------------
# The oracle issues no verdict over an axis it did not read (320/G1, G3, G7, G8).
# ---------------------------------------------------------------------------
def test_zero_file_content_comparison_is_indeterminate_not_pass():
    """A comparison that walked ZERO paths cannot satisfy the pass arm.

    Its ``diverged`` is 0 for the same reason its ``matched`` is 0 — nothing was
    read — so testing ``diverged > 0`` alone let an empty comparison satisfy the
    content conjunct and resolve a healthy-looking observation to ``pass``.
    """
    verdict = _verdict(_obs(content=ContentComparison(matched=0, total=0, diverged=0)))

    assert verdict.outcome == INDET
    assert 'empty_comparison' in verdict.reason


def test_unreadable_source_dir_is_distinguishable_from_an_empty_one(tmp_path):
    """The two unusable causes carry DIFFERENT reasons, and neither is a pass.

    An unreadable directory and a genuinely empty one call for different
    operator action, so collapsing them into one 'nothing to compare' would tell
    the operator nothing about which they have.
    """
    empty_source = tmp_path / 'empty-source'
    empty_pin = tmp_path / 'empty-pin'
    empty_source.mkdir()
    empty_pin.mkdir()

    empty = _ppt.compare_pin_content(empty_pin, empty_source)
    assert empty.usable is False
    assert empty.unusable_because is not None
    assert empty.unusable_because.startswith('empty_comparison')

    unreadable = _ppt.compare_pin_content(empty_pin, tmp_path / 'does-not-exist')
    assert unreadable.usable is False
    assert unreadable.unusable_because is not None
    assert unreadable.unusable_because.startswith('source_unreadable')

    assert _verdict(_obs(content=unreadable)).outcome == INDET
    assert 'source_unreadable' in _verdict(_obs(content=unreadable)).reason


def test_pin_superset_of_source_is_a_divergence(tmp_path):
    """A pin holding a file source does not is retired-file residue, and fails.

    Enumerating only the source side made a strict superset read as a complete
    match — the exact residue the detector exists to catch, invisible because it
    was outside the denominator.
    """
    source = tmp_path / 'source'
    pin = tmp_path / 'pin'
    for base in (source, pin):
        (base / 'skills' / 's').mkdir(parents=True)
        (base / 'skills' / 's' / 'kept.py').write_text('print(1)\n', encoding='utf-8')
    (pin / 'skills' / 's' / 'retired.py').write_text('print(2)\n', encoding='utf-8')

    cc = _ppt.compare_pin_content(pin, source)

    assert cc.total == 2
    assert cc.matched == 1
    assert cc.diverged == 1
    assert cc.extra_in_pin == 1
    assert cc.partial is False
    assert 'ABSENT from source' in cc.render()

    verdict = _verdict(_obs(content=cc))
    assert verdict.outcome == FAIL
    assert any('pin content diverges' in d for d in verdict.divergences)


def test_pin_missing_a_source_file_is_a_scanned_divergence(tmp_path):
    """A file the pin LACKS diverges and counts as scanned — it is not unscanned.

    The distinction is what makes ``partial`` mean something: an absent
    counterpart is a fully-observed disagreement, while an unreadable path is an
    observation that did not happen.
    """
    source = tmp_path / 'source'
    pin = tmp_path / 'pin'
    for base in (source, pin):
        (base / 'skills' / 's').mkdir(parents=True)
        (base / 'skills' / 's' / 'kept.py').write_text('print(1)\n', encoding='utf-8')
    (source / 'skills' / 's' / 'added.py').write_text('print(3)\n', encoding='utf-8')

    cc = _ppt.compare_pin_content(pin, source)

    assert cc.total == 2
    assert cc.matched == 1
    assert cc.diverged == 1
    assert cc.extra_in_pin == 0
    assert cc.partial is False
    assert cc.scanned_count == 2


def test_samples_differing_only_in_content_are_indeterminate():
    """The double-sample guard covers the content axis too.

    The content comparison is the longest read in an observation and therefore
    the one most likely to straddle a write; leaving it out of the volatile
    signature let the guard issue a confident verdict over two samples that
    demonstrably disagreed.
    """
    sample_a = _obs(content=ContentComparison(matched=360, total=360, diverged=0))
    sample_b = _obs(content=ContentComparison(matched=359, total=360, diverged=1))

    verdict = evaluate(sample_a, sample_b, sampling_instant='2026-08-13T00:00:00Z')

    assert verdict.outcome == INDET
    assert 'read_during_write' in verdict.reason


def test_samples_agreeing_on_content_still_reach_a_verdict():
    """The control for the test above: equal content counts do not force indeterminate."""
    sample_a = _obs(content=ContentComparison(matched=360, total=360, diverged=0))
    sample_b = _obs(content=ContentComparison(matched=360, total=360, diverged=0))

    assert evaluate(sample_a, sample_b, sampling_instant='2026-08-13T00:00:00Z').outcome == PASS


def test_version_split_executor_fails_naming_the_conflicting_versions():
    """A split executor is a FAIL on the divergence axis, not a could-not-look.

    It was read successfully; what it says is internally inconsistent. Filing
    that as "could not read the executor" would report a demonstrated
    disagreement as an absence of evidence.
    """
    split = _ppt.ExecutorAnchor(
        status=_ppt.EXECUTOR_SPLIT, version=None, versions=('0.1.100', '0.1.200')
    )

    verdict = _verdict(_obs(executor_version=None, executor_anchor=split))

    assert verdict.outcome == FAIL
    assert any('version-SPLIT' in d for d in verdict.divergences)
    assert any('0.1.100' in d and '0.1.200' in d for d in verdict.divergences)
    assert 'could not read' not in verdict.reason


def test_unreadable_executor_is_still_indeterminate():
    """The control: a genuinely unreadable executor keeps its could-not-look outcome."""
    unreadable = _ppt.ExecutorAnchor(status=_ppt.EXECUTOR_UNREADABLE)

    verdict = _verdict(_obs(executor_version=None, executor_anchor=unreadable))

    assert verdict.outcome == INDET
    assert 'could_not_look' in verdict.reason
    assert 'executor' in verdict.reason


def test_observe_reports_a_split_executor_end_to_end(tmp_path):
    """``observe`` carries the anchor through, so the oracle sees the split."""
    cache = tmp_path / 'cache'
    bundle = cache / 'plan-marshall'
    _make_version_dir(bundle, '0.1.200', marked=False, files={'skills/s/scripts/a.py': 'print(1)\n'})
    source = tmp_path / 'source'
    (source / 'skills' / 's' / 'scripts').mkdir(parents=True)
    (source / 'skills' / 's' / 'scripts' / 'a.py').write_text('print(1)\n', encoding='utf-8')

    registry = tmp_path / 'config.json'
    registry.write_text(
        '{"plan-marshall": {"installPath": "/c/plan-marshall/0.1.200", "version": "0.1.200"}}',
        encoding='utf-8',
    )
    executor = tmp_path / 'execute-script.py'
    executor.write_text(
        '"/x/cache/plan-marshall/0.1.200/skills/s/scripts/a.py"\n'
        '"/x/cache/plan-marshall/0.1.100/skills/s/scripts/b.py"\n',
        encoding='utf-8',
    )

    obs = _ppt.observe(
        cache_bundle_dir=bundle,
        registry_path=registry,
        plugin_name='plan-marshall',
        executor_path=executor,
        source_dir=source,
    )

    assert obs.executor_version is None
    assert obs.executor_anchor is not None
    assert obs.executor_anchor.status == _ppt.EXECUTOR_SPLIT
    assert evaluate(obs, obs, sampling_instant='2026-08-13T00:00:00Z').outcome == FAIL


# ---------------------------------------------------------------------------
# Loader eligibility, and the tree shape 3 was named for.
# ---------------------------------------------------------------------------
def test_loader_returns_an_older_dir_when_the_newest_is_ineligible():
    """Eligibility can send the resolution BACKWARD — the incident's mechanism.

    ``resolve_bundle_path`` supplies a PER-REQUEST predicate
    (``(d / subpath).exists()``), so a request for a subpath present only in an
    older dir resolves to that older dir. A model with no eligibility set can
    only ever resolve forward, and would report this as agreement.
    """
    dirs = (VersionDir('0.1.300', marked=False), VersionDir('0.1.100', marked=False))

    assert loader_selected_version(dirs) == '0.1.300'
    assert loader_selected_version(dirs, frozenset({'0.1.100'})) == '0.1.100'


def test_loader_is_none_when_eligibility_excludes_every_dir():
    """No eligible dir is the selector's own loud failure, not a silent pick."""
    dirs = (VersionDir('0.1.300', marked=False),)

    assert loader_selected_version(dirs, frozenset()) is None


def test_observe_populates_eligibility_from_the_requested_subpath(tmp_path):
    """The adapter derives eligibility from which dirs carry the subpath.

    The fixture puts the requested script ONLY in the older dir, so the observed
    eligibility set excludes the newer one and the loader model resolves
    backward — the state a no-eligibility model reports as clean.
    """
    cache = tmp_path / 'cache'
    bundle = cache / 'plan-marshall'
    subpath = 'skills/s/scripts/a.py'
    _make_version_dir(bundle, '0.1.300', marked=False, files={'skills/s/scripts/other.py': 'x\n'})
    _make_version_dir(bundle, '0.1.100', marked=False, files={subpath: 'print(1)\n'})

    registry = tmp_path / 'config.json'
    registry.write_text(
        '{"plan-marshall": {"installPath": "/c/plan-marshall/0.1.300", "version": "0.1.300"}}',
        encoding='utf-8',
    )
    executor = tmp_path / 'execute-script.py'
    executor.write_text('"/x/cache/plan-marshall/0.1.300/skills/s/scripts/a.py"\n', encoding='utf-8')

    obs = _ppt.observe(
        cache_bundle_dir=bundle,
        registry_path=registry,
        plugin_name='plan-marshall',
        executor_path=executor,
        subpath=subpath,
    )

    assert obs.eligible_versions == frozenset({'0.1.100'})
    verdict = evaluate(obs, obs, sampling_instant='2026-08-13T00:00:00Z')
    assert verdict.loader_selected_version == '0.1.100'
    assert verdict.outcome == FAIL
    assert any('loader_selected' in d for d in verdict.divergences)


def test_observe_without_a_subpath_leaves_every_dir_eligible(tmp_path):
    """The control: omitting ``subpath`` models the directory-existence predicate.

    That is the PYTHONPATH walk's predicate, which is the same for every request
    and therefore always resolves forward.
    """
    cache = tmp_path / 'cache'
    bundle = cache / 'plan-marshall'
    _make_version_dir(bundle, '0.1.300', marked=False, files={'skills/s/scripts/other.py': 'x\n'})
    _make_version_dir(bundle, '0.1.100', marked=False, files={'skills/s/scripts/a.py': 'print(1)\n'})

    registry = tmp_path / 'config.json'
    registry.write_text(
        '{"plan-marshall": {"installPath": "/c/plan-marshall/0.1.300", "version": "0.1.300"}}',
        encoding='utf-8',
    )
    executor = tmp_path / 'execute-script.py'
    executor.write_text('"/x/cache/plan-marshall/0.1.300/skills/s/scripts/a.py"\n', encoding='utf-8')

    obs = _ppt.observe(
        cache_bundle_dir=bundle,
        registry_path=registry,
        plugin_name='plan-marshall',
        executor_path=executor,
    )

    assert obs.eligible_versions is None
    assert evaluate(obs, obs, sampling_instant='2026-08-13T00:00:00Z').loader_selected_version == '0.1.300'


def test_shape3_literal_older_stale_beside_newest_pin_is_a_pass():
    """The tree the plan's "shape 3" named is a PASS — pinned, not argued.

    An older stale UNMARKED dir sitting beside a correct, NEWEST pin: under
    newest-eligible-wins the loader already follows the pin, so nothing is
    mis-seated and the older dir is unreachable. The implemented shape-3
    condition can only fire when a NON-pin dir sorts HIGHER than the pin, which
    this tree does not have.

    Whether such a tree should nonetheless be reported — it is equally the
    benign window right after a sync, before the retention sweep runs — is a
    policy question recorded as a proposal for an operator, not decided here.
    This test exists so the current behaviour is pinned either way.
    """
    obs = _obs(
        install_path_version='0.1.300',
        registry_version='0.1.300',
        executor_version='0.1.300',
        version_dirs=(VersionDir('0.1.300', marked=False), VersionDir('0.1.100', marked=False)),
    )

    verdict = _verdict(obs)

    assert verdict.outcome == PASS
    assert verdict.shapes == ()
    assert verdict.loader_selected_version == '0.1.300'


# ---------------------------------------------------------------------------
# The paired observer — the double-sample guard's missing producer.
# ---------------------------------------------------------------------------
def _pin_trap_fixture(tmp_path):
    """Return the kwargs ``observe`` / ``observe_twice`` take over a fixture tree."""
    bundle = tmp_path / 'cache' / 'plan-marshall'
    _make_version_dir(bundle, '0.1.200', marked=False, files={'skills/s/scripts/a.py': 'print(1)\n'})
    source = tmp_path / 'source'
    (source / 'skills' / 's' / 'scripts').mkdir(parents=True)
    (source / 'skills' / 's' / 'scripts' / 'a.py').write_text('print(1)\n', encoding='utf-8')
    registry = tmp_path / 'config.json'
    registry.write_text(
        '{"plan-marshall": {"installPath": "/c/plan-marshall/0.1.200", "version": "0.1.200"}}',
        encoding='utf-8',
    )
    executor = tmp_path / 'execute-script.py'
    executor.write_text('"/x/cache/plan-marshall/0.1.200/skills/s/scripts/a.py"\n', encoding='utf-8')
    return {
        'cache_bundle_dir': bundle,
        'registry_path': registry,
        'plugin_name': 'plan-marshall',
        'executor_path': executor,
        'source_dir': source,
    }


def test_observe_twice_detects_a_store_that_changed_between_the_two_reads(tmp_path):
    """The paired observer takes two INDEPENDENT reads, so the guard can fire.

    Nothing exported a paired variant, so every caller passed the same
    observation twice — which satisfies the double-sample guard by construction
    and reduces it to asserting that a value equals itself. The injected sleep
    mutates the tree between the reads at no wall-clock cost.
    """
    kwargs = _pin_trap_fixture(tmp_path)
    pin_file = kwargs['cache_bundle_dir'] / '0.1.200' / 'skills' / 's' / 'scripts' / 'a.py'
    slept: list[float] = []

    def _fake_sleep(seconds: float) -> None:
        slept.append(seconds)
        pin_file.write_text('print(2)\n', encoding='utf-8')

    first, second = _ppt.observe_twice(delay_seconds=0.5, sleep=_fake_sleep, **kwargs)

    assert slept == [0.5]
    assert first != second
    verdict = evaluate(first, second, sampling_instant='2026-08-13T00:00:00Z')
    assert verdict.outcome == INDET
    assert 'read_during_write' in verdict.reason


def test_observe_twice_over_a_quiet_tree_reaches_a_verdict(tmp_path):
    """The control: with nothing changing between the reads, the pair agrees."""
    kwargs = _pin_trap_fixture(tmp_path)

    first, second = _ppt.observe_twice(delay_seconds=0.0, sleep=lambda _s: None, **kwargs)

    assert first == second
    assert evaluate(first, second, sampling_instant='2026-08-13T00:00:00Z').outcome == PASS


def test_observe_twice_is_exported():
    """The producer is part of the module's public surface, not an internal helper."""
    assert 'observe_twice' in _ppt.__all__
