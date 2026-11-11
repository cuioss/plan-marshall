# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for body transform rules for the Antigravity target."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from conftest import PROJECT_ROOT
from marketplace.targets.body_transform_engine import (
    load_transform_rules,
    make_body_transformer,
    rewrite_dispatch_blocks,
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


#: A dispatch block as the source corpus writes it: the target-bearing header
#: line plus its indented ``prompt:`` block, inside the fenced block that holds
#: it. ``{target}`` is the value ``manage-config effort resolve-target`` returns.
TARGETED_DISPATCH_BLOCK = (
    '```text\nTask: plan-marshall:{target}\n  prompt: |\n    name: phase-5-execute\n    plan_id: {plan_id}\n```\n'
)

#: The bare header form: the agent is named by the block's own
#: ``subagent_type:`` line instead of on the dispatch line.
BARE_DISPATCH_BLOCK = (
    '```text\n'
    'Task:\n'
    '  subagent_type: pm-dev-builder:maven-builder\n'
    '  prompt: |\n'
    '    Execute mvn clean verify, report results and coverage\n'
    '```\n'
)

_BARE_DISPATCH_RE = re.compile(r'^\s*Task:[ \t]*$', re.MULTILINE)
_TARGETED_DISPATCH_RE = re.compile(r'^\s*Task: plan-marshall:', re.MULTILINE)


def _dispatch_template(rules) -> str:
    return rules.body_idiom_rewrites['Task:']['template']


def test_dispatch_line_records_that_it_is_rewritten_with_a_target(rules):
    """The mapping carries the dispatch-block disposition and its ``{target}`` template."""
    record = rules.body_idiom_rewrites['Task:']
    assert record['disposition'] == 'rewrite_dispatch_block'
    assert '{target}' in record['template'], 'the dispatch instruction must name the resolved target'


def test_targeted_dispatch_block_becomes_an_invoke_subagent_instruction(rules):
    out = rewrite_dispatch_blocks(TARGETED_DISPATCH_BLOCK, _dispatch_template(rules))
    assert not _TARGETED_DISPATCH_RE.search(out), 'the bare Antigravity-meaningless dispatch line survived'
    assert '`invoke_subagent`' in out
    assert 'plan-marshall:{target}' in out
    assert '    name: phase-5-execute\n' in out, 'the prompt body must survive the rewrite'


def test_bare_dispatch_block_is_rewritten_from_its_own_subagent_type(rules):
    """A header with no target takes the agent from the block's ``subagent_type:`` line."""
    out = rewrite_dispatch_blocks(BARE_DISPATCH_BLOCK, _dispatch_template(rules))
    assert not _BARE_DISPATCH_RE.search(out)
    assert '`invoke_subagent`' in out
    assert 'pm-dev-builder:maven-builder' in out
    assert out.count('subagent_type') == 1, 'the agent must be named once, in the instruction'
    assert '    Execute mvn clean verify, report results and coverage\n' in out


def test_a_dispatch_mention_without_a_block_is_left_alone(rules):
    """Prose naming the idiom is not a dispatch header, so it is preserved."""
    raw = 'Task: plan-marshall:{target} is the dispatch idiom the orchestrator follows.\n'
    assert rewrite_dispatch_blocks(raw, _dispatch_template(rules)) == raw


def test_dispatch_block_rewrite_is_idempotent(rules):
    template = _dispatch_template(rules)
    once = rewrite_dispatch_blocks(TARGETED_DISPATCH_BLOCK, template)
    assert rewrite_dispatch_blocks(once, template) == once


def test_the_full_transformer_rewrites_a_dispatch_block(rules):
    """A ``SKILL.md`` body goes through the dispatch applier too."""
    out = make_body_transformer({}, rules)(TARGETED_DISPATCH_BLOCK, 'plan-marshall', 'skill')
    assert not _TARGETED_DISPATCH_RE.search(out)
    assert '`invoke_subagent`' in out
