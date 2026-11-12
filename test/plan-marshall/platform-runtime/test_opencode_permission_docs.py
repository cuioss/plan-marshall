#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The permission documents and the code state the same error vocabulary.

An operator reads ``doc/developer/opencode.adoc``, ``standards/contract.md`` and
``SKILL.md`` to decide what an error means. A code the operations return but a
document omits (or the other way round) turns that reading into a guess, so the
three surfaces are compared against the runtime's own declaration — and the
base policy every one of them states is the one OBSERVED on the client, not the
retired "no match means ask" model.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from opencode_runtime import OPENCODE_PERMISSION_ERROR_CODES

from conftest import PROJECT_ROOT

SKILL_DIR = Path(PROJECT_ROOT) / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'platform-runtime'
DOCUMENTS = {
    'SKILL.md': SKILL_DIR / 'SKILL.md',
    'contract.md': SKILL_DIR / 'standards' / 'contract.md',
}
ADOC = Path(PROJECT_ROOT) / 'doc' / 'developer' / 'opencode.adoc'

#: The base policy OBSERVED at this version: the ruleset begins allow-all.
BASE_POLICY_STATEMENT = '{action: "*", resource: "*", effect: "allow"}'
OBSERVED_VERSION = 'v2.2.7'

_CODE_ROW = re.compile(r'^\|\s*`([a-z_]+)`\s*\|', re.MULTILINE)
_RETIRED_ASK_MODEL = re.compile(r'no match (?:means|is)\s*`?ask`?', re.IGNORECASE)


def _documented_codes(path: Path) -> set[str]:
    """The codes a document's error-code table declares."""
    return set(_CODE_ROW.findall(path.read_text(encoding='utf-8')))


def test_the_declared_code_set_is_not_empty() -> None:
    """Guard on the guard: an empty set would make every subset check vacuous."""
    assert OPENCODE_PERMISSION_ERROR_CODES


@pytest.mark.parametrize('name', sorted(DOCUMENTS))
def test_every_code_the_operations_return_is_listed(name: str) -> None:
    missing = OPENCODE_PERMISSION_ERROR_CODES - _documented_codes(DOCUMENTS[name])
    assert not missing, f'{name} omits the error code(s) {sorted(missing)}'


@pytest.mark.parametrize('name', sorted(DOCUMENTS))
def test_the_retired_save_code_is_gone(name: str) -> None:
    """``save_error`` was never in the contract; a failed save is ``io_error``."""
    assert 'save_error' not in _documented_codes(DOCUMENTS[name])
    assert 'save_error' not in DOCUMENTS[name].read_text(encoding='utf-8')


#: Every prose surface the run must keep honest: the documents with an
#: error-code table, plus the developer adoc. Derived from ``DOCUMENTS`` so a
#: document added there is swept by every test below.
ALL_DOCUMENTS = {**DOCUMENTS, 'opencode.adoc': ADOC}


@pytest.mark.parametrize('name', sorted(ALL_DOCUMENTS))
def test_no_document_states_an_unmatched_action_is_ask(name: str) -> None:
    offenders = _RETIRED_ASK_MODEL.findall(ALL_DOCUMENTS[name].read_text(encoding='utf-8'))
    assert not offenders, f'{name} still documents the retired base policy: {offenders}'


#: The two surfaces that state the agent base policy (the developer adoc and the
#: skill body). ``contract.md`` documents operation error codes, not the base
#: policy, so it is not in this population.
_BASE_POLICY_DOCUMENTS = ('opencode.adoc', 'SKILL.md')


@pytest.mark.parametrize('name', _BASE_POLICY_DOCUMENTS)
def test_the_observed_base_policy_is_stated_with_its_source(name: str) -> None:
    normalized = ' '.join(ALL_DOCUMENTS[name].read_text(encoding='utf-8').split())
    assert BASE_POLICY_STATEMENT in normalized, f'{name} does not state the observed base policy'
    assert OBSERVED_VERSION in normalized, f'{name} does not name the version the base policy was observed at'


#: The agent ``"*"`` fallback in the shape the client reads: a rule in the
#: ordered ``permissions`` list, never an OpenCode 1 ``permission`` map entry.
ASK_FALLBACK_RULE = '{action: "*", resource: "*", effect: "ask"}'


def test_the_role_matrix_describes_the_agent_fallback_as_a_list_rule() -> None:
    """The fallback is a list rule, not OpenCode 1 ``"*": "ask"`` map notation."""
    normalized = ' '.join(ADOC.read_text(encoding='utf-8').split())

    assert ASK_FALLBACK_RULE in normalized, 'opencode.adoc never spells the fallback as a list rule'
    assert '"*": "ask"' not in normalized, 'opencode.adoc still spells the fallback as a permission map entry'


def test_every_cited_test_module_exists() -> None:
    """Every test module the developer document cites exists in the tree."""
    cited = set(re.findall(r'(test_[a-z0-9_]+\.py)', ADOC.read_text(encoding='utf-8')))
    assert cited, 'the document cites no test module'

    present = {path.name for path in (Path(PROJECT_ROOT) / 'test').rglob('*.py')}
    missing = sorted(cited - present)

    assert not missing, f'opencode.adoc cites test module(s) that do not exist: {missing}'
