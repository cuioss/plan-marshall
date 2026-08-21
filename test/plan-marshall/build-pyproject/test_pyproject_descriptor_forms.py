#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Descriptor forms the Python discoverer must read, and the ones it must report.

Every gap these pin ends at the same output — ``{'id': 'pyproject', 'status':
'ok', 'edge_count': 0}`` — which the shipped documentation defines as *"N
resolvers ran and found nothing. The empty answer is a real, positive result"*
and the user page renders as *"your modules genuinely declare no dependencies on
each other"*. In each case that is a misreport: a descriptor nobody parsed, or a
requirement spelling the parser mangled.

Both monorepo fixtures are driven through the REAL discovery path and the REAL
resolver, so what is under test is the module dicts production code produces —
not a hand-built sample of them, which would agree with the parser by
construction.
"""

from pathlib import Path

import pytest

from conftest import load_script_module

FIXTURES = Path(__file__).parent / 'fixtures'

_pyproject_cmd_discover = load_script_module(
    'plan-marshall', 'build-pyproject', '_pyproject_cmd_discover.py', '_pyproject_cmd_discover'
)
_extension = load_script_module('plan-marshall', 'build-pyproject', 'extension.py', '_pyproject_extension')

discover_python_modules = _pyproject_cmd_discover.discover_python_modules
requirement_name = _pyproject_cmd_discover.requirement_name


def _edges_for(project_root: Path) -> list[tuple[str, str]]:
    """Discover ``project_root`` and derive its module edges, as production does."""
    modules = {module['name']: module for module in discover_python_modules(str(project_root))}
    edges: list[tuple[str, str]]
    edges, _notes = _extension.BuildExtension().derive_edges(modules, {})
    return edges


def _metadata_for(project_root: Path) -> dict[str, dict]:
    return {module['name']: module['metadata'] for module in discover_python_modules(str(project_root))}


# =============================================================================
# G1 — Poetry
# =============================================================================


def test_a_poetry_only_monorepo_derives_its_internal_edges():
    """No [project] table anywhere; every name and dependency is under [tool.poetry]."""
    edges = _edges_for(FIXTURES / 'poetry-monorepo')
    assert edges, 'a Poetry monorepo derived no edges at all'
    assert ('default', 'core_lib') in edges
    assert ('app', 'core_lib') in edges


def test_a_poetry_dev_group_dependency_is_an_edge():
    """``[tool.poetry.group.dev.dependencies]`` matches the PEP 621 ``dev`` extra."""
    assert ('app', 'default') in _edges_for(FIXTURES / 'poetry-monorepo')


def test_poetry_metadata_is_published_so_the_module_can_be_an_edge_target():
    metadata = _metadata_for(FIXTURES / 'poetry-monorepo')
    assert metadata['core_lib']['name'] == 'poetry-core-lib'
    assert metadata['core_lib']['version'] == '1.0.0'
    assert metadata['default']['name'] == 'poetry-platform'


def test_the_poetry_python_constraint_is_not_a_dependency():
    """``python`` is the interpreter constraint Poetry records beside real packages."""
    modules = {m['name']: m for m in discover_python_modules(str(FIXTURES / 'poetry-monorepo'))}
    assert all(not dep.startswith('python:') for dep in modules['core_lib']['dependencies'])


def test_a_pep621_name_suppresses_the_poetry_table_whole_including_its_dependencies(tmp_path):
    """The all-or-nothing cost of the strict fallback, pinned rather than left latent.

    A hybrid `pyproject.toml` — `[project]` carrying the name, dependencies still
    under `[tool.poetry.dependencies]` — publishes the name and **no**
    dependencies. The module becomes a valid edge target and contributes no
    outbound edges, with nothing in the output saying why.

    That is deliberate: a per-field merge would let one descriptor form silently
    override the other's answer, and `metadata` / `dependencies` are read by
    consumers beyond edge derivation. But it is exactly the silent-empty shape
    this deliverable exists to remove, so it is a **stated** limit — see
    `doc/user/dependency-intelligence.adoc` § Python specifics — and this pins
    it, so a later reader finds a documented contract rather than an accident.
    """
    module = tmp_path / 'hybrid'
    (module / 'tests').mkdir(parents=True)
    (module / 'pyproject.toml').write_text(
        '[project]\nname = "hybrid-dist"\nversion = "1.0.0"\n\n'
        '[tool.poetry]\nname = "hybrid-dist"\n\n'
        '[tool.poetry.dependencies]\npython = "^3.11"\nsibling-core = "^1.0"\n',
        encoding='utf-8',
    )

    modules = {m['name']: m for m in discover_python_modules(str(tmp_path))}

    assert modules['hybrid']['metadata']['name'] == 'hybrid-dist'  # a valid edge TARGET
    assert modules['hybrid']['dependencies'] == []  # ...and no outbound edges at all


def test_the_poetry_fallback_never_overrides_a_pep621_name(tmp_path):
    """A strict fallback: consumers beyond edge derivation read these fields."""
    module = tmp_path / 'both'
    (module / 'tests').mkdir(parents=True)
    (module / 'pyproject.toml').write_text(
        '[project]\nname = "from-pep621"\nversion = "2.0.0"\n'
        'dependencies = ["real-dep>=1.0"]\n\n'
        '[tool.poetry]\nname = "from-poetry"\nversion = "9.9.9"\n\n'
        '[tool.poetry.dependencies]\nshadow-dep = "^1.0"\n',
        encoding='utf-8',
    )
    modules = {m['name']: m for m in discover_python_modules(str(tmp_path))}
    assert modules['both']['metadata']['name'] == 'from-pep621'
    assert modules['both']['metadata']['version'] == '2.0.0'
    assert modules['both']['dependencies'] == ['real-dep:runtime']


# =============================================================================
# G10 — setuptools / setup.cfg
# =============================================================================


def test_a_setup_cfg_only_monorepo_derives_its_internal_edges():
    """These modules are ADMITTED by _find_descriptor_file, then read by nothing."""
    edges = _edges_for(FIXTURES / 'setuptools-monorepo')
    assert edges, 'a setuptools monorepo derived no edges at all'
    assert ('default', 'core_lib') in edges
    assert ('app', 'core_lib') in edges
    assert ('app', 'default') in edges


def test_setup_cfg_metadata_is_published():
    metadata = _metadata_for(FIXTURES / 'setuptools-monorepo')
    assert metadata['core_lib']['name'] == 'setuptools-core-lib'
    assert metadata['default']['description'].startswith('Fixture root')


def test_a_PERCENT_SIGN_in_one_setup_cfg_costs_only_THAT_module(tmp_path):
    """One module's percent sign must not erase the tree.

    `BasicInterpolation` raises from `get()`, not from `read()`. With the reads
    outside the guard that wraps `read()`, `description = 100% pure python` in
    ONE module escaped `discover_python_modules` and took every module with it —
    including the ones whose descriptors parsed perfectly.

    The claim is deliberately about the SIBLINGS, not about the offending value.
    setuptools rejects that descriptor too (it interpolates `setup.cfg` exactly
    as this does), so refusing the module is the correct answer; refusing the
    *whole tree* for it was not. A single-module fixture would pass while the
    whole-tree case still failed, which is why this one has two.
    """
    for name, description in (('core_lib', 'A library'), ('app', '100% pure python')):
        module = tmp_path / name
        (module / 'tests').mkdir(parents=True)
        (module / 'setup.cfg').write_text(
            f'[metadata]\nname = pct-{name}\ndescription = {description}\n'
            '\n[options]\ninstall_requires =\n    requests\n',
            encoding='utf-8',
        )

    modules = {m['name']: m for m in discover_python_modules(str(tmp_path))}

    assert set(modules) >= {'core_lib', 'app'}, 'the percent sign erased the innocent siblings'
    assert modules['core_lib']['metadata']['name'] == 'pct-core_lib'
    assert modules['core_lib']['dependencies'] == ['requests:runtime']
    # The offending module is admitted but publishes nothing — the descriptor is
    # one setuptools refuses, so there is no name to publish and no edge to draw.
    assert modules['app']['metadata'].get('name') is None
    assert modules['app']['dependencies'] == []


def test_setup_cfg_interpolation_MATCHES_setuptools(tmp_path):
    """The name field is what edge derivation joins on, so it must agree.

    setuptools reads `setup.cfg` through `BasicInterpolation`. Turning
    interpolation off here would read `100% pure python` happily — but would
    then publish `acme-%(version)s` where the ecosystem publishes `acme-1.0`,
    making the module an unreachable edge target for a name nothing else uses.
    Agreeing on the resolved value is worth more than reading the value
    setuptools itself rejects.
    """
    module = tmp_path / 'pkg'
    (module / 'tests').mkdir(parents=True)
    (module / 'setup.cfg').write_text(
        '[metadata]\nversion = 1.0\nname = acme-%(version)s\ndescription = 50%% off\n',
        encoding='utf-8',
    )

    modules = {m['name']: m for m in discover_python_modules(str(tmp_path))}

    assert modules['pkg']['metadata']['name'] == 'acme-1.0', 'the join key disagrees with setuptools'
    assert modules['pkg']['metadata']['description'] == '50% off'


def test_a_setup_py_only_module_still_publishes_no_name(tmp_path):
    """setup.py is executable Python; the limit is stated, not silently narrowed."""
    module = tmp_path / 'legacy'
    (module / 'tests').mkdir(parents=True)
    (module / 'setup.py').write_text('from setuptools import setup\nsetup(name="legacy-dist")\n', encoding='utf-8')
    modules = {m['name']: m for m in discover_python_modules(str(tmp_path))}
    assert modules['legacy']['metadata'] == {}
    assert modules['legacy']['paths']['descriptor'].endswith('setup.py')


# =============================================================================
# G2 / G3 — PEP 508 direct references and environment markers
# =============================================================================


@pytest.mark.parametrize('spelling', [
    'sample-core>=1.0.0',
    'sample-core @ file:///./sample_core',
    'sample-core@file:///./sample_core',
    'sample-core@ file:///./sample_core',
    'sample-core; python_version >= "3.11"',
    'sample-core>=1.0.0; python_version >= "3.11"',
    'sample-core[extra]>=1.0.0',
], ids=[
    'plain-specifier', 'direct-reference-spaced', 'direct-reference-bare',
    'direct-reference-trailing-space', 'environment-marker',
    'marker-and-specifier', 'extras',
])
def test_every_pep508_spelling_yields_the_same_edge(tmp_path, spelling):
    """One requirement, seven legal spellings, one edge — or the spelling alone destroys it.

    The bare-``@`` form is the one ``pip freeze`` emits, and PEP 508 spells the
    URL form ``AT wsp* URI_reference``, so the whitespace is optional: a split on
    ``' @ '`` would pass the spaced case and leave this one broken.
    """
    for name, descriptor in (
        ('sample_core', '[project]\nname = "sample-core"\nversion = "1.0.0"\n'),
        # A TOML *literal* string (single quotes, no escape processing) — the
        # marker spellings contain double quotes of their own.
        ('dependent', f"[project]\nname = 'dependent'\nversion = '1.0.0'\ndependencies = ['{spelling}']\n"),
    ):
        module = tmp_path / name
        (module / 'tests').mkdir(parents=True)
        (module / 'pyproject.toml').write_text(descriptor, encoding='utf-8')

    assert _edges_for(tmp_path) == [('dependent', 'sample_core')]


@pytest.mark.parametrize('requirement,expected', [
    ('sample-core', 'sample-core'),
    ('sample-core>=1.0.0', 'sample-core'),
    ('sample-core@file:///./x', 'sample-core'),
    ('sample-core ; python_version >= "3.11"', 'sample-core'),
    ('sample-core[a,b]~=1.0 ; extra == "dev"', 'sample-core'),
    ('', ''),
    ('   ', ''),
])
def test_requirement_name_extracts_the_bare_distribution_name(requirement, expected):
    assert requirement_name(requirement) == expected


# =============================================================================
# G11 — an unreadable descriptor is reported, not absorbed
# =============================================================================


def test_a_malformed_descriptor_emits_a_warning_naming_the_file(tmp_path, monkeypatch):
    """Silence made "declares nothing" and "cannot be parsed" indistinguishable."""
    logged: list[tuple[str, str, str, str]] = []
    monkeypatch.setattr(
        _pyproject_cmd_discover, 'log_entry',
        lambda *args: logged.append(args),
    )
    module = tmp_path / 'broken'
    (module / 'tests').mkdir(parents=True)
    (module / 'pyproject.toml').write_text('[project\nname = "broken"\n', encoding='utf-8')

    modules = {m['name']: m for m in discover_python_modules(str(tmp_path))}

    assert modules['broken']['metadata'] == {}
    warnings = [entry for entry in logged if entry[2] == 'WARNING' and 'broken/pyproject.toml' in entry[3]]
    assert warnings, f'no WARNING named the malformed descriptor; logged={logged}'


def test_an_unexpected_exception_is_not_absorbed(tmp_path, monkeypatch):
    """The catch is narrowed, so a defect in this code propagates rather than reading as empty."""
    module = tmp_path / 'exploding'
    (module / 'tests').mkdir(parents=True)
    (module / 'pyproject.toml').write_text('[project]\nname = "exploding"\n', encoding='utf-8')

    def _boom(_handle):
        raise RuntimeError('a defect in the reader, not in the descriptor')

    monkeypatch.setattr(_pyproject_cmd_discover.tomllib, 'load', _boom)

    with pytest.raises(RuntimeError, match='a defect in the reader'):
        discover_python_modules(str(tmp_path))


def test_a_malformed_target_descriptor_is_visible_rather_than_killing_the_edge_silently(tmp_path, monkeypatch):
    """The dependent's edge is still lost — but the WARNING says why."""
    logged: list[tuple[str, str, str, str]] = []
    monkeypatch.setattr(
        _pyproject_cmd_discover, 'log_entry',
        lambda *args: logged.append(args),
    )
    for name, descriptor in (
        ('sample_core', '[project\nname = "sample-core"\n'),  # unbalanced bracket
        ('dependent', '[project]\nname = "dependent"\ndependencies = ["sample-core>=1.0"]\n'),
    ):
        module = tmp_path / name
        (module / 'tests').mkdir(parents=True)
        (module / 'pyproject.toml').write_text(descriptor, encoding='utf-8')

    edges = _edges_for(tmp_path)

    assert edges == []  # the target published no name, so the edge cannot join
    assert any(entry[2] == 'WARNING' and 'sample_core/pyproject.toml' in entry[3] for entry in logged)
