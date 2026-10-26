# SPDX-License-Identifier: FSL-1.1-ALv2
"""The lane's sibling-skill joins reach their file on a flat deployed tree.

The remaining sibling-skill joins in the measured list are NOT anchored on
``resolve_skills_root``: each walks up from its own ``__file__`` to the skills
directory and then joins a bare skill name. On a nested checkout that lands on
``…/skills/{skill}/…``; on a flat install the skill directory is
``…/skills/{bundle}-{skill}/``, so the join names a path that cannot exist and the
caller silently degrades — a build-queue slot that never loads, a CI log filter
that never finds its parser, a generator path that is not there.

Every case here imports the deployed module from the marker-less flat fixture and
asks the module's OWN constant/function, so the assertion is on the join the
production code makes — not on a re-derivation in the test.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from _flat_install_fixtures import flat_install_tree, run_python_in_flat

#: ``{skill}/{scripts-relative file}/{module name}``. The bundle is always
#: plan-marshall; the skill directory name is prefixed by it on a flat tree.
_MODULES: dict[str, tuple[str, str, str]] = {
    'ci_log_filter': ('tools-integration-ci', '_ci_log_filter.py', 'probe_ci_log_filter'),
    'ci_base': ('tools-integration-ci', 'ci_base.py', 'probe_ci_base'),
    'build_queue_slot': ('script-shared', 'build/_build_queue_slot.py', 'probe_build_queue_slot'),
    'build_execute_factory': ('script-shared', 'build/_build_execute_factory.py', 'probe_build_execute_factory'),
    'integrate_into_main': ('workflow-integration-git', 'integrate_into_main.py', 'probe_integrate_into_main'),
    'git_workflow': ('workflow-integration-git', 'git-workflow.py', 'probe_git_workflow'),
    'prepare_execute': ('workflow-integration-git', 'prepare_execute.py', 'probe_prepare_execute'),
    'determine_mode': ('marshall-steward', 'determine_mode.py', 'probe_determine_mode'),
}


def _program(root: Path) -> str:
    """Return the driver that asks each deployed module where its sibling join landed."""
    loads = '\n'.join(
        f'    {key!r}: load({skill!r}, {relative!r}, {name!r}),' for key, (skill, relative, name) in _MODULES.items()
    )
    return f"""
import importlib.util, json, sys

root = {str(root)!r}
bundle = 'plan-marshall'


def load(skill, relative, name):
    path = f'{{root}}/skills/{{bundle}}-{{skill}}/scripts/{{relative}}'
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


modules = {{
{loads}
}}

results = {{}}
results['build_queue_path'] = str(modules['build_queue_slot']._BUILD_QUEUE_PATH)
results['build_queue_exists'] = modules['build_queue_slot']._BUILD_QUEUE_PATH.is_file()
results['build_queue_dep_dirs'] = {{
    str(path): path.is_dir() for path in modules['build_queue_slot']._BUILD_QUEUE_DEP_DIRS
}}
results['build_server_path'] = str(modules['build_execute_factory']._BUILD_SERVER_CLIENT_PATH)
results['build_server_exists'] = modules['build_execute_factory']._BUILD_SERVER_CLIENT_PATH.is_file()
results['merge_lock_path'] = str(modules['integrate_into_main']._MERGE_LOCK_PATH)
results['merge_lock_exists'] = modules['integrate_into_main']._MERGE_LOCK_PATH.is_file()
results['git_workflow_generator'] = str(modules['git_workflow']._GENERATE_EXECUTOR_PATH)
results['git_workflow_generator_exists'] = modules['git_workflow']._GENERATE_EXECUTOR_PATH.is_file()
results['prepare_execute_generator'] = str(modules['prepare_execute']._GENERATE_EXECUTOR_PATH)
results['prepare_execute_generator_exists'] = modules['prepare_execute']._GENERATE_EXECUTOR_PATH.is_file()
results['determine_mode_generator'] = str(modules['determine_mode']._generate_executor_script())
results['determine_mode_generator_exists'] = modules['determine_mode']._generate_executor_script().is_file()
results['maven_parse_log'] = modules['ci_log_filter']._load_parse_log('maven') is not None
results['ci_persist'] = modules['ci_base']._load_persist() is not None
print(json.dumps(results))
"""


@pytest.fixture(scope='module')
def flat_install(flat_install_tree: Path) -> Path:
    return flat_install_tree


def test_every_lane_sibling_join_reaches_its_file(flat_install: Path, tmp_path: Path) -> None:
    """Each module's own sibling-skill path exists in the flat deployment."""
    project = tmp_path / 'project'
    project.mkdir()
    completed = run_python_in_flat(flat_install, project, _program(flat_install))
    assert completed.returncode == 0, completed.stderr
    results = cast('dict[str, Any]', json.loads(completed.stdout))

    # Asserted individually so a failure names the join that broke.
    assert results['build_queue_exists'], results['build_queue_path']
    assert results['build_server_exists'], results['build_server_path']
    assert results['merge_lock_exists'], results['merge_lock_path']
    assert results['git_workflow_generator_exists'], results['git_workflow_generator']
    assert results['prepare_execute_generator_exists'], results['prepare_execute_generator']
    # The upgrade's own preflight entry point (D1): the generator path the steward
    # resolves must exist in the deployment, or Stage 2 cannot regenerate at all.
    assert results['determine_mode_generator_exists'], results['determine_mode_generator']

    absent_deps = {path: present for path, present in results['build_queue_dep_dirs'].items() if not present}
    assert not absent_deps, absent_deps

    assert results['maven_parse_log'], 'the CI log filter found no build parser on the flat tree'
    assert results['ci_persist'], 'the CI persistence layer did not load on the flat tree'


def test_the_generator_runs_from_the_flat_tree(flat_install: Path, tmp_path: Path) -> None:
    """The executor generator the upgrade invokes loads and parses its surface on a flat tree.

    The generator's own ``sys.path`` bootstrap is nested-only (declared, with its
    reason, in the D2 guard), so this exercises the ONE invocation shape it is
    actually given: a ``python3 <path>`` run inside the deployed tree, with the
    flat PYTHONPATH the executor would pass. ``--help`` stops at argparse, so no
    output tree is touched.
    """
    project = tmp_path / 'project'
    project.mkdir()
    script = flat_install / 'skills' / 'plan-marshall-tools-script-executor' / 'scripts' / 'generate_executor.py'

    completed = run_python_in_flat(
        flat_install,
        project,
        f'import runpy, sys\nsys.argv = [{str(script)!r}, "--help"]\n'
        f'try:\n    runpy.run_path({str(script)!r}, run_name="__main__")\n'
        'except SystemExit as exc:\n    raise SystemExit(int(exc.code or 0))\n',
    )

    assert completed.returncode == 0, completed.stderr
    assert 'generate' in completed.stdout, completed.stdout
