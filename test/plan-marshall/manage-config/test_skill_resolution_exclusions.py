#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The manage-config skill verbs honour the repository's ``excluded_skills`` veto.

PLAN-LB-80 D4. ``resolve-domain-skills`` feeds the recipe selection flow (its
defaults are presented pre-checked) and ``get-skills-by-profile`` feeds the
finalize code-review rulebook, so both are paths to a task's skills and both must
apply the repository veto the resolver and the architecture path already apply.
"""

import json
from argparse import Namespace

from _manage_config_fixtures import create_nested_marshal_json

from conftest import load_script_module

_cmd_skill_resolution = load_script_module(
    'plan-marshall', 'manage-config', '_cmd_skill_resolution.py', module_name='_cmd_skill_resolution_lb80'
)

cmd_get_skills_by_profile = _cmd_skill_resolution.cmd_get_skills_by_profile
cmd_resolve_domain_skills = _cmd_skill_resolution.cmd_resolve_domain_skills

JAVA_CORE = 'pm-dev-java:java-core'


def _seed_config(plan_context, excluded_skills: list[str] | None = None):
    """Write the nested marshal fixture, optionally adding a java exclusion."""
    path = create_nested_marshal_json(plan_context.fixture_dir)
    if excluded_skills is not None:
        config = json.loads(path.read_text(encoding='utf-8'))
        config['skill_domains']['java']['excluded_skills'] = list(excluded_skills)
        path.write_text(json.dumps(config, indent=2), encoding='utf-8')
    return path


def test_resolve_domain_skills_drops_an_excluded_default(plan_context):
    """An excluded default is not offered as a pre-checked recipe default."""
    _seed_config(plan_context, ['java-core'])

    result = cmd_resolve_domain_skills(Namespace(domain='java', profile='implementation'))

    assert result['status'] == 'success'
    assert JAVA_CORE not in str(result['defaults'])


def test_resolve_domain_skills_keeps_a_default_without_an_exclusion(plan_context):
    """Matched negative control: the same cell keeps the default unexcluded."""
    _seed_config(plan_context, [])

    result = cmd_resolve_domain_skills(Namespace(domain='java', profile='implementation'))

    assert JAVA_CORE in str(result['defaults'])


def test_get_skills_by_profile_drops_an_excluded_skill(plan_context):
    """An excluded skill never reaches the finalize code-review rulebook."""
    _seed_config(plan_context, ['java-core'])

    result = cmd_get_skills_by_profile(Namespace(domain='java'))

    assert result['status'] == 'success'
    assert JAVA_CORE not in str(result['skills_by_profile'])


def test_get_skills_by_profile_keeps_a_skill_without_an_exclusion(plan_context):
    """Matched negative control: the profile sets keep the skill unexcluded."""
    _seed_config(plan_context, [])

    result = cmd_get_skills_by_profile(Namespace(domain='java'))

    assert JAVA_CORE in str(result['skills_by_profile'])
