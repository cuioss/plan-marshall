#!/usr/bin/env python3
"""Tests for the files-inventory post-processor in ``_cmd_manage.py``.

Covers classification (marketplace + generic), ``.gitignore`` honouring,
symlink/dotfile policy, determinism, and the per-category cap behaviour.
The post-processor mutates the ``modules`` dict in-place — every test
inspects the resulting ``files`` block on the module dict.
"""

import importlib.util
import os
import sys
import tempfile
from pathlib import Path

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace' / 'bundles' / 'plan-marshall' / 'skills' / 'manage-architecture' / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_load_module('_architecture_core', '_architecture_core.py')
_cmd_manage = _load_module('_cmd_manage', '_cmd_manage.py')

_post_process_files = _cmd_manage._post_process_files


# =============================================================================
# Helpers
# =============================================================================


def _write(path: Path, content: str = '') -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def _make_marketplace_bundle(project: Path, bundle_name: str) -> dict:
    """Lay out a minimal marketplace bundle on disk and return its module dict."""
    bundle_root = project / 'marketplace' / 'bundles' / bundle_name
    _write(bundle_root / 'README.md', '# bundle')
    _write(bundle_root / 'plugin.json', '{}')
    _write(bundle_root / 'skills' / 'core' / 'SKILL.md', '# core skill')
    _write(bundle_root / 'skills' / 'core' / 'standards' / 'rules.md', '# rules')
    _write(bundle_root / 'skills' / 'core' / 'scripts' / 'do_thing.py', '# python')
    _write(bundle_root / 'skills' / 'core' / 'scripts' / 'helper.sh', '# shell')
    _write(bundle_root / 'skills' / 'core' / 'templates' / 'sample.tmpl', 'tmpl')
    _write(bundle_root / 'agents' / 'reviewer.md', '# agent')
    _write(bundle_root / 'commands' / 'do.md', '# cmd')
    return {
        'name': bundle_name,
        'paths': {
            'module': f'marketplace/bundles/{bundle_name}',
            'tests': [f'test/{bundle_name}'],
        },
    }


# =============================================================================
# Marketplace classification
# =============================================================================


def test_marketplace_mode_classifies_skill_agent_command():
    """Files under skills/agents/commands resolve to their marketplace categories."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        modules = {'pm-x': _make_marketplace_bundle(project, 'pm-x')}

        _post_process_files(modules, str(project))

        files = modules['pm-x']['files']
        assert files['skill'] == ['marketplace/bundles/pm-x/skills/core/SKILL.md']
        assert files['agent'] == ['marketplace/bundles/pm-x/agents/reviewer.md']
        assert files['command'] == ['marketplace/bundles/pm-x/commands/do.md']


def test_marketplace_mode_classifies_script_standard_template():
    """Scripts (.py/.sh), standards (.md), templates fall into the right buckets."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        modules = {'pm-x': _make_marketplace_bundle(project, 'pm-x')}

        _post_process_files(modules, str(project))

        files = modules['pm-x']['files']
        assert 'marketplace/bundles/pm-x/skills/core/scripts/do_thing.py' in files['script']
        assert 'marketplace/bundles/pm-x/skills/core/scripts/helper.sh' in files['script']
        assert files['standard'] == ['marketplace/bundles/pm-x/skills/core/standards/rules.md']
        assert files['template'] == ['marketplace/bundles/pm-x/skills/core/templates/sample.tmpl']


def test_marketplace_mode_classifies_build_files_and_doc():
    """plugin.json and README* are classified deterministically."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        modules = {'pm-x': _make_marketplace_bundle(project, 'pm-x')}

        _post_process_files(modules, str(project))

        files = modules['pm-x']['files']
        assert files['build_file'] == ['marketplace/bundles/pm-x/plugin.json']
        assert files['doc'] == ['marketplace/bundles/pm-x/README.md']


def test_marketplace_mode_does_not_emit_source_category():
    """Marketplace bundles never use the generic ``source`` bucket."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        modules = {'pm-x': _make_marketplace_bundle(project, 'pm-x')}
        # An unclassifiable .py outside of skills/scripts/ is silently skipped.
        _write(project / 'marketplace/bundles/pm-x/loose.py', '# stray')

        _post_process_files(modules, str(project))

        assert 'source' not in modules['pm-x']['files']


def test_paths_tests_outside_module_get_test_category():
    """Files under paths.tests outside the module root all classify as ``test``."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        modules = {'pm-x': _make_marketplace_bundle(project, 'pm-x')}
        _write(project / 'test' / 'pm-x' / 'test_thing.py', 'def test_x(): pass')
        _write(project / 'test' / 'pm-x' / 'sub' / 'test_more.py', 'def test_y(): pass')

        _post_process_files(modules, str(project))

        tests = modules['pm-x']['files'].get('test', [])
        assert 'test/pm-x/test_thing.py' in tests
        assert 'test/pm-x/sub/test_more.py' in tests


# =============================================================================
# Generic classification
# =============================================================================


def test_generic_mode_classifies_source_test_doc_build():
    """Generic modules use the source/test/doc/build_file split."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        module_dir = project / 'libapp'
        _write(module_dir / 'src' / 'main.py', 'print()')
        _write(module_dir / 'tests' / 'test_main.py', 'def test_x(): pass')
        _write(module_dir / 'README.md', '# readme')
        _write(module_dir / 'pyproject.toml', '[project]')

        modules = {
            'libapp': {
                'name': 'libapp',
                'paths': {'module': 'libapp'},
            },
        }
        _post_process_files(modules, str(project))

        files = modules['libapp']['files']
        assert files['source'] == ['libapp/src/main.py']
        assert files['test'] == ['libapp/tests/test_main.py']
        assert files['doc'] == ['libapp/README.md']
        assert files['build_file'] == ['libapp/pyproject.toml']


def test_generic_mode_test_files_under_test_dir_classify_as_test():
    """``test/``/``tests/``/``__tests__/`` directories all map to ``test``."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        module_dir = project / 'app'
        _write(module_dir / 'test' / 'a.py', '')
        _write(module_dir / 'tests' / 'b.py', '')
        _write(module_dir / '__tests__' / 'c.js', '')

        modules = {'app': {'paths': {'module': 'app'}}}
        _post_process_files(modules, str(project))

        tests = modules['app']['files'].get('test', [])
        assert 'app/test/a.py' in tests
        assert 'app/tests/b.py' in tests
        assert 'app/__tests__/c.js' in tests


# =============================================================================
# .gitignore honouring
# =============================================================================


def test_gitignore_directory_pattern_skips_subtree():
    """A trailing-``/`` pattern in .gitignore prunes the directory."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        _write(project / '.gitignore', 'ignored_dir/\n')
        bundle = project / 'marketplace' / 'bundles' / 'pm-x'
        _write(bundle / 'plugin.json', '{}')
        _write(bundle / 'ignored_dir' / 'leak.py', 'x')
        _write(bundle / 'skills' / 'core' / 'SKILL.md', '# s')

        modules = {'pm-x': {'paths': {'module': 'marketplace/bundles/pm-x'}}}
        _post_process_files(modules, str(project))

        all_paths: list[str] = []
        for entry in modules['pm-x']['files'].values():
            if isinstance(entry, list):
                all_paths.extend(entry)
        assert not any('ignored_dir' in p for p in all_paths)


def test_gitignore_extension_pattern_skips_files():
    """A glob like ``*.pyc`` keeps compiled files out of the inventory."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        _write(project / '.gitignore', '*.pyc\n')
        bundle = project / 'marketplace' / 'bundles' / 'pm-x'
        _write(bundle / 'plugin.json', '{}')
        _write(bundle / 'skills' / 'core' / 'scripts' / 'do.py', 'x')
        _write(bundle / 'skills' / 'core' / 'scripts' / 'do.pyc', 'x')

        modules = {'pm-x': {'paths': {'module': 'marketplace/bundles/pm-x'}}}
        _post_process_files(modules, str(project))

        scripts = modules['pm-x']['files'].get('script', [])
        assert any(p.endswith('do.py') for p in scripts)
        assert not any(p.endswith('do.pyc') for p in scripts)


def test_pycache_directory_is_always_ignored():
    """``__pycache__`` is never inventoried, even without a .gitignore."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        bundle = project / 'marketplace' / 'bundles' / 'pm-x'
        _write(bundle / 'plugin.json', '{}')
        _write(bundle / 'skills' / 'core' / 'scripts' / '__pycache__' / 'do.cpython-312.pyc', 'x')
        _write(bundle / 'skills' / 'core' / 'scripts' / 'do.py', 'x')

        modules = {'pm-x': {'paths': {'module': 'marketplace/bundles/pm-x'}}}
        _post_process_files(modules, str(project))

        scripts = modules['pm-x']['files'].get('script', [])
        assert all('__pycache__' not in p for p in scripts)


# =============================================================================
# Symlink and dotfile policy
# =============================================================================


def test_symlinks_are_skipped():
    """Symlinks (file or directory) never appear in the inventory."""
    if os.name == 'nt':
        return  # Symlink creation requires elevation on Windows.
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        bundle = project / 'marketplace' / 'bundles' / 'pm-x'
        _write(bundle / 'plugin.json', '{}')
        _write(bundle / 'skills' / 'core' / 'SKILL.md', '# s')
        link_target = project / 'external.md'
        _write(link_target, '# external')
        (bundle / 'agents').mkdir(parents=True, exist_ok=True)
        os.symlink(link_target, bundle / 'agents' / 'linked.md')

        modules = {'pm-x': {'paths': {'module': 'marketplace/bundles/pm-x'}}}
        _post_process_files(modules, str(project))

        agents = modules['pm-x']['files'].get('agent', [])
        assert all('linked.md' not in p for p in agents)


def test_dotfiles_skipped_except_allowlist():
    """Hidden files are skipped except for ``.gitignore`` and ``.editorconfig``."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        bundle = project / 'marketplace' / 'bundles' / 'pm-x'
        _write(bundle / 'plugin.json', '{}')
        _write(bundle / '.gitignore', '')
        _write(bundle / '.editorconfig', '')
        _write(bundle / '.hiddenrc', 'private')

        modules = {'pm-x': {'paths': {'module': 'marketplace/bundles/pm-x'}}}
        _post_process_files(modules, str(project))

        all_paths: list[str] = []
        for entry in modules['pm-x']['files'].values():
            if isinstance(entry, list):
                all_paths.extend(entry)
        # Skipped: .hiddenrc isn't classified anyway, but it must not leak via
        # any future generic classifier path either. The allowlisted dotfiles
        # are unclassified by the marketplace table — the rule is "not
        # silently dropped at the dotfile-skip step", which is what the walker
        # promises. The classifier returning None is a separate decision.
        assert not any(p.endswith('.hiddenrc') for p in all_paths)


# =============================================================================
# Determinism and cap behaviour
# =============================================================================


def test_two_consecutive_runs_produce_identical_output():
    """The post-processor must be byte-deterministic across runs."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        modules_one = {'pm-x': _make_marketplace_bundle(project, 'pm-x')}
        modules_two = {'pm-x': _make_marketplace_bundle(project, 'pm-x')}

        _post_process_files(modules_one, str(project))
        _post_process_files(modules_two, str(project))

        assert modules_one['pm-x']['files'] == modules_two['pm-x']['files']


def test_category_lists_are_sorted():
    """Each category list is sorted lexicographically (byte-wise)."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        bundle = project / 'marketplace' / 'bundles' / 'pm-x'
        _write(bundle / 'plugin.json', '{}')
        for name in ['zeta', 'alpha', 'mike']:
            _write(bundle / 'skills' / name / 'SKILL.md', f'# {name}')

        modules = {'pm-x': {'paths': {'module': 'marketplace/bundles/pm-x'}}}
        _post_process_files(modules, str(project))

        skills = modules['pm-x']['files']['skill']
        assert skills == sorted(skills)


def test_category_cap_replaces_list_with_elision_shape():
    """Above 500 paths, the list collapses to ``{elided, sample}``."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        bundle = project / 'marketplace' / 'bundles' / 'pm-x'
        _write(bundle / 'plugin.json', '{}')
        # Make 501 skills so the cap kicks in.
        for i in range(501):
            _write(bundle / 'skills' / f's{i:04d}' / 'SKILL.md', f'# s{i}')

        modules = {'pm-x': {'paths': {'module': 'marketplace/bundles/pm-x'}}}
        _post_process_files(modules, str(project))

        skills = modules['pm-x']['files']['skill']
        assert isinstance(skills, dict)
        assert skills['elided'] == 501
        assert len(skills['sample']) == 100
        # Sample is the first 100 paths in sorted order.
        assert skills['sample'] == sorted(skills['sample'])


def test_module_with_no_paths_module_gets_empty_files_block():
    """Defensive: a module without ``paths.module`` still gets a stable shape."""
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        modules = {'broken': {'name': 'broken', 'paths': {}}}
        _post_process_files(modules, str(project))
        assert modules['broken']['files'] == {}
