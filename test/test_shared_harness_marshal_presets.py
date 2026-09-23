# SPDX-License-Identifier: FSL-1.1-ALv2
"""The marshal presets stay distinct.

:func:`conftest.create_marshal_json`'s named presets produce genuinely distinct
baselines, so collapsing three builders into one did not average two different
fixtures into a third that serves neither.
"""

from conftest import (
    MARSHAL_PRESET_JAVA,
    MARSHAL_PRESET_MINIMAL,
    MARSHAL_PRESETS,
    create_marshal_json,
)


def test_marshal_presets_are_not_averaged_into_one(tmp_path):
    """The two named baselines produce different configs, each with its own shape."""
    import json

    minimal = json.loads(create_marshal_json(tmp_path / 'a', preset=MARSHAL_PRESET_MINIMAL).read_text())
    java = json.loads(create_marshal_json(tmp_path / 'b', preset=MARSHAL_PRESET_JAVA).read_text())

    assert minimal != java

    # The minimal baseline carries no language domain and no providers.
    assert set(minimal['skill_domains']) == {'system'}
    assert 'providers' not in minimal

    # The java baseline carries its domains, its branch-cleanup params and a provider.
    assert 'java' in java['skill_domains']
    assert java['plan']['phase-6-finalize']['steps']['default:branch-cleanup']['pr_merge_strategy'] == 'squash'
    assert java['providers'][0]['provider'] == 'github'


def test_every_registered_preset_is_reachable_by_name(tmp_path):
    """Each name in the preset table builds; the table is the contract."""
    import json

    assert set(MARSHAL_PRESETS) == {MARSHAL_PRESET_MINIMAL, MARSHAL_PRESET_JAVA}
    for name in MARSHAL_PRESETS:
        written = json.loads(create_marshal_json(tmp_path / name, preset=name).read_text())
        assert written == MARSHAL_PRESETS[name]


def test_building_a_fixture_leaves_the_shared_baseline_untouched(tmp_path):
    """Building fixtures does not rewrite the module-level baseline.

    Scope, stated honestly: the builder applies ``skill_domains`` and ``extra``
    at the TOP level only, so today no code path reaches a nested object and this
    assertion cannot fail. It is a pin, not a detector — it fixes the invariant
    now, so that an override path which later merges nested keys has to keep it.
    The builder deep-copies its baseline for the same forward-looking reason.
    """
    import copy
    import json

    before = copy.deepcopy(MARSHAL_PRESETS[MARSHAL_PRESET_MINIMAL])

    create_marshal_json(tmp_path / 'one', preset=MARSHAL_PRESET_MINIMAL, skill_domains={'replaced': {}})
    create_marshal_json(tmp_path / 'two', preset=MARSHAL_PRESET_MINIMAL, extra={'added': 1})

    assert MARSHAL_PRESETS[MARSHAL_PRESET_MINIMAL] == before

    # And a later build still reproduces the pristine baseline.
    third = json.loads(create_marshal_json(tmp_path / 'three', preset=MARSHAL_PRESET_MINIMAL).read_text())
    assert third == before


def test_full_config_form_is_written_verbatim(tmp_path):
    """The full-config form writes what it was given, ignoring every baseline."""
    import json

    written = create_marshal_json(tmp_path, {'skill_domains': {}, 'marker': 'verbatim'})
    assert json.loads(written.read_text()) == {'skill_domains': {}, 'marker': 'verbatim'}


def test_the_two_call_forms_may_not_be_combined(tmp_path):
    """Passing both forms is refused rather than silently resolved one way."""
    import pytest

    with pytest.raises(ValueError, match='not both'):
        create_marshal_json(tmp_path, {'skill_domains': {}}, extra={'x': 1})


def test_an_unknown_preset_is_refused(tmp_path):
    """A misspelled preset name fails loudly instead of falling back to a default."""
    import pytest

    with pytest.raises(ValueError, match='unknown preset'):
        create_marshal_json(tmp_path, preset='no-such-preset')


def test_the_destination_is_explicit(tmp_path):
    """Nesting under .plan/ is a stated argument, not an inherited surprise."""
    nested = create_marshal_json(tmp_path / 'n', preset=MARSHAL_PRESET_MINIMAL, nest_in_plan_dir=True)
    flat = create_marshal_json(tmp_path / 'f', preset=MARSHAL_PRESET_MINIMAL, nest_in_plan_dir=False)

    assert nested.parent.name == '.plan'
    assert flat.parent.name == 'f'


def test_the_project_data_companion_is_opt_in(tmp_path):
    """raw-project-data.json is written only when asked for."""
    with_data = create_marshal_json(tmp_path / 'w', preset=MARSHAL_PRESET_JAVA, with_project_data=True)
    without = create_marshal_json(tmp_path / 'o', preset=MARSHAL_PRESET_JAVA)

    assert (with_data.parent / 'raw-project-data.json').is_file()
    assert not (without.parent / 'raw-project-data.json').exists()
