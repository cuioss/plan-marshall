#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Cross-cutting regression tests for the `project.user_language` knob.

Exercised from the user-visible angle rather than at unit level: every case
drives ``manage-config.py`` ``main()`` in-process with a patched ``sys.argv``, so
the real argparse surface, the noun -> handler routing, and the TOON output are
all on the path. The unit-level seed and validator assertions live beside their
siblings in ``test_config_defaults.py``; what is covered here is the operator's
own sequence — seed, read, pin, back-fill, and the coercion rejection.

The bool-coercion case is the load-bearing one: ``cmd_project``'s ``set`` branch
routes ``--value`` through ``_coerce_value``, which turns ``false`` into a Python
``bool`` and a digit string into an ``int``. Every reader of the knob expects a
string, so the guard is what keeps a coerced non-string off disk.

Isolation: the autouse ``_plan_base_dir_sandbox`` plus the explicit
``plan_context`` fixture redirect ``_config_core.MARSHAL_PATH`` into a per-test
tmp sandbox, so every seed and write lands there, never in the real ``.plan/``.
"""

import json
import sys

import pytest
from toon_parser import parse_toon

from conftest import load_script_module

# Loaded under a unique module name so it does not clash with the other
# manage-config test modules that load the same source file.
_mc = load_script_module(
    'plan-marshall', 'manage-config', 'manage-config.py', 'mc_user_language_under_test'
)

#: The knob's shipped default: follow the language the user is writing in.
_AUTO = 'auto'

#: A representative pin. No tag grammar is enforced, so a bare code is enough.
_PIN = 'de'


def _drive(monkeypatch, capsys, *argv):
    """Run ``main()`` in-process with ``argv`` and return ``(code, parsed_toon)``.

    Patches ``sys.argv`` so the production parser sees the requested tokens, then
    calls the ``@safe_main`` wrapper (which always raises ``SystemExit``).
    """
    monkeypatch.setattr(sys, 'argv', ['manage-config.py', *argv])
    with pytest.raises(SystemExit) as exc:
        _mc.main()
    out = capsys.readouterr().out
    code = exc.value.code if exc.value.code is not None else 0
    return code, parse_toon(out)


def _marshal_path(plan_context):
    return plan_context.fixture_dir / 'marshal.json'


def _read_marshal(plan_context) -> dict:
    data: dict = json.loads(_marshal_path(plan_context).read_text(encoding='utf-8'))
    return data


def _write_marshal(plan_context, config: dict) -> None:
    _marshal_path(plan_context).write_text(json.dumps(config, indent=2), encoding='utf-8')


def _init(plan_context, monkeypatch, capsys) -> None:
    """Seed a fresh marshal.json through the CLI and assert the seed landed."""
    code, data = _drive(monkeypatch, capsys, 'init')

    assert code == 0
    assert data['status'] == 'success'
    assert _marshal_path(plan_context).exists()


def test_init_seeds_user_language_auto(plan_context, monkeypatch, capsys):
    """A fresh `init` seeds project.user_language == 'auto' into marshal.json."""
    _init(plan_context, monkeypatch, capsys)

    config = _read_marshal(plan_context)

    assert config['project']['user_language'] == _AUTO


def test_project_get_returns_auto_when_the_key_is_absent(plan_context, monkeypatch, capsys):
    """`project get --field user_language` falls back to 'auto' on a config that omits it.

    The implicit-default read path: a project block predating the knob must read
    the canonical default rather than erroring or returning an empty value.
    """
    _init(plan_context, monkeypatch, capsys)
    config = _read_marshal(plan_context)
    config['project'].pop('user_language', None)
    _write_marshal(plan_context, config)

    code, data = _drive(monkeypatch, capsys, 'project', 'get', '--field', 'user_language')

    assert code == 0
    assert data['status'] == 'success'
    assert data['field'] == 'user_language'
    assert data['value'] == _AUTO


def test_project_set_then_get_round_trips_a_pinned_language(plan_context, monkeypatch, capsys):
    """`project set --field user_language --value de` persists and round-trips through get."""
    _init(plan_context, monkeypatch, capsys)

    set_code, set_data = _drive(
        monkeypatch, capsys, 'project', 'set', '--field', 'user_language', '--value', _PIN
    )

    assert set_code == 0
    assert set_data['status'] == 'success'
    # persisted on disk, not merely echoed back
    assert _read_marshal(plan_context)['project']['user_language'] == _PIN

    get_code, get_data = _drive(monkeypatch, capsys, 'project', 'get', '--field', 'user_language')

    assert get_code == 0
    assert get_data['value'] == _PIN


def test_sync_defaults_backfills_user_language_into_an_older_config(
    plan_context, monkeypatch, capsys
):
    """`sync-defaults` back-fills the key into a config that predates the knob.

    Existing projects never re-run `init`, so the non-destructive deep-merge is
    the only path by which they pick the knob up.
    """
    _init(plan_context, monkeypatch, capsys)
    config = _read_marshal(plan_context)
    config['project'].pop('user_language', None)
    _write_marshal(plan_context, config)

    code, data = _drive(monkeypatch, capsys, 'sync-defaults')

    assert code == 0
    assert data['status'] == 'success'
    assert _read_marshal(plan_context)['project']['user_language'] == _AUTO


def test_sync_defaults_preserves_an_operator_pin(plan_context, monkeypatch, capsys):
    """The back-fill is non-destructive: an operator's pin survives `sync-defaults`."""
    _init(plan_context, monkeypatch, capsys)
    config = _read_marshal(plan_context)
    config['project']['user_language'] = _PIN
    _write_marshal(plan_context, config)

    code, data = _drive(monkeypatch, capsys, 'sync-defaults')

    assert code == 0
    assert data['status'] == 'success'
    assert _read_marshal(plan_context)['project']['user_language'] == _PIN


#: Values `_coerce_value` converts away from `str` before the knob is validated,
#: plus the two empty forms the non-empty half of the validator rejects.
_REJECTED_VALUES = ['false', 'true', '0', '1', '', '   ']


@pytest.mark.parametrize('value', _REJECTED_VALUES, ids=[f'value={v!r}' for v in _REJECTED_VALUES])
def test_project_set_user_language_rejects_a_non_string_or_empty_value(
    plan_context, monkeypatch, capsys, value
):
    """A coerced non-string (or an empty value) is rejected and never reaches disk.

    Both halves matter: the rejection is reported as `invalid_value`, AND the
    persisted value is still the seeded string. Asserting only the error would
    pass even if the bad value had been written first and the error raised after.
    """
    _init(plan_context, monkeypatch, capsys)

    code, data = _drive(
        monkeypatch, capsys, 'project', 'set', '--field', 'user_language', '--value', value
    )

    assert code == 0
    assert data['status'] == 'error'
    assert data['error_type'] == 'invalid_value'

    persisted = _read_marshal(plan_context)['project']['user_language']
    assert isinstance(persisted, str), f'a non-string reached disk: {persisted!r}'
    assert persisted == _AUTO


def test_project_set_unknown_field_is_still_rejected(plan_context, monkeypatch, capsys):
    """Adding the knob to the whitelist must not open the whitelist itself.

    `DEFAULT_PROJECT` doubles as the fail-closed admitted-field set, so a typo'd
    neighbour of the new key must still be refused rather than persisted.
    """
    _init(plan_context, monkeypatch, capsys)

    code, data = _drive(
        monkeypatch, capsys, 'project', 'set', '--field', 'user_langauge', '--value', _PIN
    )

    assert code == 0
    assert data['status'] == 'error'
    assert data['error_type'] == 'unknown_field'
    assert 'user_langauge' not in _read_marshal(plan_context)['project']
