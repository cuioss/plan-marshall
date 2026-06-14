#!/usr/bin/env python3
"""Malformed-config-block robustness regression for the Pattern B2 guards.

A hand-edited ``marshal.json`` can carry a non-dict value at a key the code
consumes as a dict. Four sites read such a block and treat it as a dict before
mutating it:

- ``cmd_system`` reads ``config['system']`` (item-assignment on the ``set``
  path);
- ``cmd_system`` reads ``config['system']['retention']`` (item-assignment on
  the ``set`` path);
- ``cmd_project`` reads ``config['project']`` (item-assignment on the ``set``
  path);
- ``cmd_finalize_steps_apply_preset`` reads ``config['plan']`` (chained
  ``setdefault`` in the preset writer).

The Pattern B2 ``isinstance(..., dict)`` guard at each site must turn a non-dict
block into a structured ``status: error`` (not an ``AttributeError`` /
``TypeError``). This cross-cutting regression parametrizes the four sites over
several off-type shapes and asserts every invocation returns a structured error
with a non-empty message instead of raising — distinct from, and complementary
to, the per-site unit assertions in ``test_cmd_system_plan.py`` and
``test_cmd_finalize_steps.py``.
"""

import importlib.util
import sys
from argparse import Namespace
from pathlib import Path

import pytest

from test_helpers import create_marshal_json

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-config'
    / 'scripts'
)

# `_cmd_finalize_steps` imports `finalize_step_presets` and `_config_defaults`
# at module level — make the scripts dir importable before loading handlers.
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_cmd_system_plan = _load_module('_cmd_system_plan', '_cmd_system_plan.py')
_cmd_finalize_steps = _load_module('_cmd_finalize_steps', '_cmd_finalize_steps.py')

cmd_system = _cmd_system_plan.cmd_system
cmd_project = _cmd_system_plan.cmd_project
cmd_finalize_steps_apply_preset = _cmd_finalize_steps.cmd_finalize_steps_apply_preset


def _base_config() -> dict:
    """A minimal well-formed marshal.json config the per-case override mutates."""
    return {
        'skill_domains': {},
        'system': {'retention': {'logs_days': 1}},
        'plan': {},
        'project': {'default_base_branch': 'main'},
        'providers': [],
    }


# Off-type shapes a hand edit can produce at a block key. Each must be caught.
_OFFTYPE_VALUES = [
    pytest.param(['not', 'a', 'dict'], id='list'),
    pytest.param('totally-wrong', id='str'),
    pytest.param(42, id='int'),
    pytest.param(None, id='null'),
]


def _config_with(key_path: tuple[str, ...], value) -> dict:
    """Return a base config with the nested ``key_path`` overridden to ``value``."""
    config = _base_config()
    target = config
    for key in key_path[:-1]:
        target = target[key]
    target[key_path[-1]] = value
    return config


# Each site: (key_path to corrupt, handler invocation, substring expected in error).
def _invoke_system_set():
    return cmd_system(Namespace(sub_noun='retention', verb='set', field='logs_days', value='7'))


def _invoke_project_set():
    return cmd_project(Namespace(verb='set', field='default_base_branch', value='develop'))


def _invoke_plan_preset():
    return cmd_finalize_steps_apply_preset(Namespace(preset='local'))


_SITES = [
    pytest.param(('system',), _invoke_system_set, 'system block', id='system'),
    pytest.param(('system', 'retention'), _invoke_system_set, 'retention block', id='retention'),
    pytest.param(('project',), _invoke_project_set, 'project block', id='project'),
    pytest.param(('plan',), _invoke_plan_preset, 'plan block', id='plan'),
]


@pytest.mark.parametrize('key_path,invoke,error_substr', _SITES)
@pytest.mark.parametrize('offtype', _OFFTYPE_VALUES)
def test_malformed_block_returns_structured_error(
    plan_context, key_path, invoke, error_substr, offtype
):
    """Each Pattern B2 site returns a structured error (never raises) for a non-dict block."""
    create_marshal_json(plan_context.fixture_dir, config=_config_with(key_path, offtype))

    # The guard must convert the off-type block into a structured error rather
    # than propagating an AttributeError/TypeError out of the handler.
    try:
        result = invoke()
    except (AttributeError, TypeError) as exc:  # pragma: no cover - failure path
        pytest.fail(
            f'malformed {".".join(key_path)} block ({offtype!r}) raised '
            f'{type(exc).__name__} instead of returning a structured error: {exc}'
        )

    assert result['status'] == 'error'
    assert isinstance(result.get('error'), str) and result['error'], (
        f'malformed {".".join(key_path)} block must yield a non-empty error message'
    )
    assert error_substr in result['error'], (
        f"expected {error_substr!r} in error for malformed {'.'.join(key_path)} "
        f"block; got {result['error']!r}"
    )
