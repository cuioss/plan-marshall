# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for body transform rules for the Antigravity target."""

from __future__ import annotations

from pathlib import Path

import pytest

from conftest import PROJECT_ROOT
from marketplace.targets.body_transform_engine import (
    load_transform_rules,
    make_body_transformer,
    rewrite_read_directives,
    rewrite_skill_directives,
)


@pytest.fixture()
def antigravity_mapping_path() -> Path:
    return Path(PROJECT_ROOT) / 'marketplace' / 'targets' / 'antigravity' / 'mapping.json'


@pytest.fixture()
def rules(antigravity_mapping_path: Path):
    return load_transform_rules(antigravity_mapping_path)


def test_rewrite_skill_directive(rules):
    raw = 'Skill: plan-marshall:execute-task\n'
    template = rules.directive_rewrites['skill_directive']['template']
    res = rewrite_skill_directives(raw, template)
    assert 'Call the `view_file` tool on `plan-marshall-execute-task/SKILL.md` before continuing.' in res


def test_rewrite_read_directive(rules):
    raw = 'Read: doc/user/readme.adoc\n'
    template = rules.directive_rewrites['read_directive']['template']
    res = rewrite_read_directives(raw, template)
    assert 'Call the `view_file` tool with `{ AbsolutePath: "doc/user/readme.adoc" }` before continuing.' in res


def test_make_body_transformer_integration(rules):
    user_invocable = {'automatic-review': 'plan-marshall-automatic-review'}
    transformer = make_body_transformer(user_invocable, rules)
    input_text = 'Skill: plan-marshall:execute-task\nRead: doc/file.md\n/automatic-review\n'
    out = transformer(input_text, 'plan-marshall', 'skill')
    assert 'view_file' in out
    assert 'plan-marshall-execute-task/SKILL.md' in out
    assert '/plan-marshall-automatic-review' in out
