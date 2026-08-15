#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for resolve-dependencies.py script.

Tests dependency resolution including detection of various dependency types,
index building, forward/reverse lookups, and validation.

Two tiers live in this file:

- Detection/parsing units (``TestComponentId``, ``TestFrontmatterExtraction``,
  ``TestScriptNotationDetection``, etc.) — already Tier 2 via direct import of
  the ``_dep_detection`` module. Untouched.
- CLI-subcommand logic (``deps`` / ``rdeps`` / ``tree`` / ``validate`` plus the
  dep-type-filter / output-format / scope branches) — converted from Tier-3
  subprocess scans of the REAL ``marketplace/bundles/`` tree to in-process calls
  against a SMALL synthetic ``marketplace/bundles`` tree built under
  ``tmp_path``. ``build_dependency_index`` is imported directly and driven over
  the synthetic graph; the ``cmd_*`` functions take the resulting
  ``DependencyIndex`` and are exercised without spawning a subprocess.

The previous design ran ``run_script(SCRIPT_PATH, 'validate'/'deps'/...)`` which
re-walked the whole real marketplace on every call. The genuinely
whole-real-graph assertions (``test_full_marketplace_validation`` and the
real-shipped-chain ``test_known_dependency_chain``) were relocated to the
sibling ``integration/test_resolve_dependencies_smoke.py``, excluded from the
default ``module-tests`` run via the root ``test/conftest.py`` ``collect_ignore``
list (mirroring the established ``integration/`` segregation pattern).
"""

from pathlib import Path

import pytest

from conftest import load_script_module


def _load_module(name, filename):
    return load_script_module('pm-plugin-development', 'tools-marketplace-inventory', filename, name)


_dep_detection_mod = _load_module('_dep_detection', '_dep_detection.py')
_dep_index_mod = _load_module('_dep_index', '_dep_index.py')
_resolve_mod = _load_module('resolve_dependencies', 'resolve-dependencies.py')

ComponentId = _dep_detection_mod.ComponentId
DependencyType = _dep_detection_mod.DependencyType
detect_implements = _dep_detection_mod.detect_implements
detect_python_imports = _dep_detection_mod.detect_python_imports
detect_script_notations = _dep_detection_mod.detect_script_notations
detect_skill_references = _dep_detection_mod.detect_skill_references
extract_frontmatter = _dep_detection_mod.extract_frontmatter

build_dependency_index = _dep_index_mod.build_dependency_index
discover_components = _dep_index_mod.discover_components
enumerate_skill_files = _dep_index_mod.enumerate_skill_files
iter_skill_subdoc_edge_sources = _dep_index_mod.iter_skill_subdoc_edge_sources
SKILL_SUBDOC_DIRS = _dep_index_mod.SKILL_SUBDOC_DIRS
SkillFile = _dep_index_mod.SkillFile
AstCache = _dep_index_mod.AstCache

# Repository root, derived from this file's own location
# (``test/pm-plugin-development/tools-marketplace-inventory/`` → three levels up).
_REPO_ROOT = Path(__file__).resolve().parents[3]
_BUNDLES_ROOT = _REPO_ROOT / 'marketplace' / 'bundles'

cmd_deps = _resolve_mod.cmd_deps
cmd_rdeps = _resolve_mod.cmd_rdeps
cmd_tree = _resolve_mod.cmd_tree
cmd_validate = _resolve_mod.cmd_validate
parse_dep_types = _resolve_mod.parse_dep_types
serialize_output = _resolve_mod.serialize_output


# =============================================================================
# Tests - ComponentId
# =============================================================================


class TestComponentId:
    """Tests for ComponentId class."""

    def test_from_notation_skill(self):
        """Test parsing skill notation."""
        comp = ComponentId.from_notation('plan-marshall:manage-files')
        assert comp is not None
        assert comp.bundle == 'plan-marshall'
        assert comp.component_type == 'skill'
        assert comp.name == 'manage-files'
        assert comp.parent_skill is None

    def test_from_notation_script(self):
        """Test parsing script notation."""
        comp = ComponentId.from_notation('plan-marshall:manage-files:manage-files')
        assert comp is not None
        assert comp.bundle == 'plan-marshall'
        assert comp.component_type == 'script'
        assert comp.name == 'manage-files'
        assert comp.parent_skill == 'manage-files'

    def test_from_notation_agent(self):
        """Test parsing agent notation."""
        comp = ComponentId.from_notation('plan-marshall:agents:phase-agent')
        assert comp is not None
        assert comp.bundle == 'plan-marshall'
        assert comp.component_type == 'agent'
        assert comp.name == 'phase-agent'

    def test_from_notation_command(self):
        """Test parsing command notation."""
        comp = ComponentId.from_notation('plan-marshall:commands:tools-sync-agents-file')
        assert comp is not None
        assert comp.bundle == 'plan-marshall'
        assert comp.component_type == 'command'
        assert comp.name == 'tools-sync-agents-file'

    def test_to_notation_skill(self):
        """Test converting skill to notation."""
        comp = ComponentId(bundle='plan-marshall', component_type='skill', name='manage-files')
        assert comp.to_notation() == 'plan-marshall:manage-files'

    def test_to_notation_script(self):
        """Test converting script to notation."""
        comp = ComponentId(
            bundle='plan-marshall',
            component_type='script',
            name='manage-files',
            parent_skill='manage-files',
        )
        assert comp.to_notation() == 'plan-marshall:manage-files:manage-files'


# =============================================================================
# Tests - Frontmatter Extraction
# =============================================================================


class TestFrontmatterExtraction:
    """Tests for the single canonical YAML frontmatter parser.

    ``extract_frontmatter`` is the one marketplace parser. It returns a
    ``Frontmatter`` superset record exposing ``present`` (bool), ``raw`` (the
    raw block text from the single regex ``match.group(1)``), and ``fields``
    (the flat-parsed dict). Raw-text consumers read ``.raw``; index/dict
    consumers read ``.fields`` — both derive from ONE regex match so the two
    views never diverge.
    """

    def test_extract_simple_frontmatter(self):
        """Simple key-value frontmatter parses into ``.fields``."""
        content = """---
name: test-skill
description: A test skill
user-invocable: true
---

# Content here
"""
        record = extract_frontmatter(content)
        assert record.present is True
        assert record.fields['name'] == 'test-skill'
        assert record.fields['description'] == 'A test skill'
        # Scalar values stay strings (no bool/int coercion) — byte-identical to
        # the pre-refactor flat parse the index substrate consumed.
        assert record.fields['user-invocable'] == 'true'

    def test_raw_is_regex_group_one(self):
        """``.raw`` is exactly the block between the ``---`` delimiters.

        This is the byte-identical guarantee the raw-text analyzers
        (_analyze_shared / _doctor_shared / plugin_discover) rely on: ``.raw``
        equals the historical ``re.match(r'^---\\s*\\n(.*?)\\n---', ...)``
        ``group(1)`` they each used before the collapse.
        """
        content = '---\nname: a\ndescription: d\n---\n\n# Body\n'
        record = extract_frontmatter(content)
        assert record.present is True
        assert record.raw == 'name: a\ndescription: d'

    def test_present_raw_and_fields_share_one_match(self):
        """``.present``/``.raw``/``.fields`` are coherent for the same content."""
        content = '---\nname: coherent\n---\n\n# Body\n'
        record = extract_frontmatter(content)
        assert record.present is True
        assert 'name: coherent' in record.raw
        assert record.fields == {'name': 'coherent'}

    def test_extract_list_frontmatter(self):
        """Block-list values parse into a Python list in ``.fields``."""
        content = """---
name: test-skill
skills:
  - plan-marshall:manage-files
  - plan-marshall:ref-toon-format
---

# Content
"""
        record = extract_frontmatter(content)
        assert record.fields['name'] == 'test-skill'
        assert record.fields['skills'] == ['plan-marshall:manage-files', 'plan-marshall:ref-toon-format']

    def test_extract_implements(self):
        """The ``implements`` field is exposed in ``.fields``."""
        content = """---
name: ext-outline-workflow
implements: plan-marshall:extension-api/standards/outline-extension.md
---

# Content
"""
        record = extract_frontmatter(content)
        assert record.fields['implements'] == 'plan-marshall:extension-api/standards/outline-extension.md'

    def test_no_frontmatter(self):
        """Content without a leading ``---`` marker yields an absent record."""
        content = """# Just a heading

No frontmatter here.
"""
        record = extract_frontmatter(content)
        assert record.present is False
        assert record.raw == ''
        assert record.fields == {}

    def test_unterminated_frontmatter_is_absent(self):
        """A frontmatter block without a closing ``---`` is treated as absent."""
        content = '---\nname: a\nno closing marker\n'
        record = extract_frontmatter(content)
        assert record.present is False
        assert record.raw == ''
        assert record.fields == {}

    def test_comment_and_blank_lines_skipped_in_fields(self):
        """``#`` comment lines and blanks are ignored by the flat parse."""
        content = '---\n# a comment\nname: x\n\ndescription: y\n---\n# Body\n'
        record = extract_frontmatter(content)
        assert record.fields == {'name': 'x', 'description': 'y'}


# =============================================================================
# Tests - Script Notation Detection
# =============================================================================


class TestScriptNotationDetection:
    """Tests for script notation detection."""

    def test_detect_execute_script_notation(self):
        """Test detecting python3 .plan/execute-script.py notation."""
        content = """
# Example usage
python3 .plan/execute-script.py plan-marshall:manage-files:manage-files add --plan-id test
"""
        source = ComponentId(bundle='test', component_type='skill', name='test')
        deps = detect_script_notations(content, source)
        assert len(deps) == 1
        assert deps[0].target.bundle == 'plan-marshall'
        assert deps[0].target.parent_skill == 'manage-files'
        assert deps[0].target.name == 'manage-files'
        assert deps[0].dep_type == DependencyType.SCRIPT_NOTATION

    def test_detect_inline_notation(self):
        """Test detecting inline script notation."""
        content = """
Use the `plan-marshall:ref-toon-format:toon_parser` script for parsing.
"""
        source = ComponentId(bundle='test', component_type='skill', name='test')
        deps = detect_script_notations(content, source)
        assert len(deps) == 1
        assert deps[0].target.bundle == 'plan-marshall'
        assert deps[0].target.name == 'toon_parser'

    def test_skip_urls(self):
        """Test that URLs are not detected as notations."""
        content = """
Visit https://example.com:8080:path for more info.
Also see http://localhost:3000:api
"""
        source = ComponentId(bundle='test', component_type='skill', name='test')
        deps = detect_script_notations(content, source)
        assert len(deps) == 0


# =============================================================================
# Tests - Skill Reference Detection
# =============================================================================


class TestSkillReferenceDetection:
    """Tests for skill reference detection."""

    def test_detect_frontmatter_skills(self):
        """Test detecting skills from frontmatter."""
        content = """Content after frontmatter"""
        frontmatter = {
            'skills': ['plan-marshall:manage-files', 'plan-marshall:ref-toon-format'],
        }
        source = ComponentId(bundle='test', component_type='skill', name='test')
        deps = detect_skill_references(content, frontmatter, source)
        assert len(deps) == 2
        assert deps[0].target.bundle == 'plan-marshall'
        assert deps[0].target.name == 'manage-files'
        assert deps[1].target.bundle == 'plan-marshall'
        assert deps[1].target.name == 'ref-toon-format'

    def test_detect_skill_pattern(self):
        """Test detecting Skill: pattern in content."""
        content = """
## Required Skills

Skill: plan-marshall:phase-1-init

This skill depends on the initialization phase.
"""
        source = ComponentId(bundle='test', component_type='skill', name='test')
        deps = detect_skill_references(content, {}, source)
        assert len(deps) == 1
        assert deps[0].target.bundle == 'plan-marshall'
        assert deps[0].target.name == 'phase-1-init'


# =============================================================================
# Tests - Python Import Detection
# =============================================================================


class TestPythonImportDetection:
    """Tests for Python import detection."""

    def test_detect_known_imports(self):
        """Test detecting known module imports."""
        content = """
from toon_parser import parse_toon, serialize_toon
from file_ops import atomic_write_file
"""
        source = ComponentId(bundle='test', component_type='script', name='test', parent_skill='test')
        deps = detect_python_imports(content, source)
        assert len(deps) == 2

        targets = {d.target.to_notation() for d in deps}
        assert 'plan-marshall:ref-toon-format:toon_parser' in targets
        assert 'plan-marshall:tools-file-ops:file_ops' in targets

    def test_skip_unknown_imports(self):
        """Test that unknown imports are not tracked."""
        content = """
from pathlib import Path
from collections import defaultdict
import json
"""
        source = ComponentId(bundle='test', component_type='script', name='test', parent_skill='test')
        deps = detect_python_imports(content, source)
        assert len(deps) == 0

    def test_handle_syntax_error(self):
        """Test handling invalid Python syntax."""
        content = """
def broken(
    # Missing closing paren
"""
        source = ComponentId(bundle='test', component_type='script', name='test', parent_skill='test')
        deps = detect_python_imports(content, source)
        assert len(deps) == 0


# =============================================================================
# Tests - Implements Detection
# =============================================================================


class TestImplementsDetection:
    """Tests for implements detection."""

    def test_detect_implements(self):
        """Test detecting implements field."""
        frontmatter = {
            'implements': 'plan-marshall:extension-api/standards/outline-extension.md',
        }
        source = ComponentId(bundle='pm-plugin-development', component_type='skill', name='ext-outline-workflow')
        deps = detect_implements(frontmatter, source)
        assert len(deps) == 1
        assert deps[0].target.bundle == 'plan-marshall'
        assert deps[0].target.name == 'extension-api'
        assert deps[0].dep_type == DependencyType.IMPLEMENTS

    def test_no_implements(self):
        """Test handling missing implements field."""
        frontmatter = {'name': 'test'}
        source = ComponentId(bundle='test', component_type='skill', name='test')
        deps = detect_implements(frontmatter, source)
        assert len(deps) == 0


# =============================================================================
# Synthetic dependency-graph fixture + in-process index driver
# =============================================================================
#
# A SMALL synthetic ``marketplace/bundles`` tree built under ``tmp_path`` so the
# subcommand-logic tests below exercise ``build_dependency_index`` + the
# ``cmd_*`` functions in-process — no subprocess, no walk of the real
# ``marketplace/bundles/`` tree.
#
# Graph shape (one bundle ``alpha-bundle``):
#
#   alpha-bundle:plan-alpha          (skill) ── Skill: ──▶ alpha-bundle:plan-beta
#                                            └─ Skill: ──▶ alpha-bundle:missing-skill (UNRESOLVED)
#   alpha-bundle:plan-alpha:run-alpha (script) ─ import ─▶ plan-marshall:ref-toon-format:toon_parser (UNRESOLVED)
#   alpha-bundle:plan-beta           (skill, leaf — no outgoing deps)
#
# Resolved-edge count: 1 (plan-alpha ── Skill ──▶ plan-beta).
# Unresolved edges: the missing-skill ref + the toon_parser import (its target
# is not a component in the synthetic tree).


_PLUGIN_JSON = '{\n  "name": "alpha-bundle",\n  "version": "0.1.0"\n}\n'


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _build_synthetic_graph(root: Path) -> Path:
    """Create a minimal synthetic ``marketplace/bundles`` tree under ``root``.

    Returns the ``marketplace/bundles`` directory path. See the module-level
    comment above for the exact graph shape and the edge counts the assertions
    rely on.
    """
    bundles = root / 'marketplace' / 'bundles'
    alpha = bundles / 'alpha-bundle'
    _write(alpha / '.claude-plugin' / 'plugin.json', _PLUGIN_JSON)

    # plan-alpha skill: references plan-beta (resolved) and missing-skill
    # (unresolved), and has a public script that imports a known shared module.
    _write(
        alpha / 'skills' / 'plan-alpha' / 'SKILL.md',
        '---\nname: plan-alpha\ndescription: Plan alpha skill\nuser-invocable: true\n---\n'
        '# Plan Alpha\n\n## Workflow\n\n'
        'Skill: alpha-bundle:plan-beta\n\n'
        'Skill: alpha-bundle:missing-skill\n',
    )
    _write(
        alpha / 'skills' / 'plan-alpha' / 'scripts' / 'run-alpha.py',
        '#!/usr/bin/env python3\n'
        'from toon_parser import serialize_toon  # noqa: F401\n\n\n'
        'def main() -> int:\n    return 0\n',
    )
    # private module — must be excluded from component discovery
    _write(
        alpha / 'skills' / 'plan-alpha' / 'scripts' / '_internal.py',
        '#!/usr/bin/env python3\n"""private helper."""\n',
    )

    # plan-beta skill: leaf, no outgoing dependencies.
    _write(
        alpha / 'skills' / 'plan-beta' / 'SKILL.md',
        '---\nname: plan-beta\ndescription: Plan beta skill\n---\n# Plan Beta\n',
    )

    return bundles


@pytest.fixture
def synthetic_index():
    """Build a ``DependencyIndex`` over the synthetic graph (all dep types)."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        bundles = _build_synthetic_graph(Path(tmp))
        yield build_dependency_index(bundles, set(DependencyType))


_ALPHA = 'alpha-bundle:plan-alpha'
_BETA = 'alpha-bundle:plan-beta'


# =============================================================================
# Tests - deps subcommand logic (in-process)
# =============================================================================


class TestDepsSubcommand:
    """Tests for the ``deps`` command logic against the synthetic graph."""

    def test_deps_known_component(self, synthetic_index):
        """deps for a known component returns success + the component echo."""
        result = cmd_deps(synthetic_index, _ALPHA, depth=10, dep_types=set(DependencyType))
        assert result['status'] == 'success'
        assert result['component'] == _ALPHA
        assert result['statistics']['direct_count'] >= 0

    def test_deps_resolves_skill_edge(self, synthetic_index):
        """deps surfaces the resolved skill edge to plan-beta."""
        result = cmd_deps(synthetic_index, _ALPHA, depth=10, dep_types=set(DependencyType))
        targets = {d['target'] for d in result['direct_dependencies']}
        assert _BETA in targets

    def test_deps_unknown_component(self, synthetic_index):
        """deps for an unknown component returns error status."""
        result = cmd_deps(
            synthetic_index,
            'nonexistent:skill:name',
            depth=10,
            dep_types=set(DependencyType),
        )
        assert result['status'] == 'error'


# =============================================================================
# Tests - rdeps subcommand logic (in-process)
# =============================================================================


class TestRdepsSubcommand:
    """Tests for the ``rdeps`` command logic against the synthetic graph."""

    def test_rdeps_known_component(self, synthetic_index):
        """rdeps for plan-beta finds plan-alpha as a dependent."""
        result = cmd_rdeps(synthetic_index, _BETA, dep_types=set(DependencyType))
        assert result['status'] == 'success'
        dependents = {d['component'] for d in result['dependents']}
        assert _ALPHA in dependents

    def test_rdeps_unknown_component(self, synthetic_index):
        """rdeps for an unknown component returns error status."""
        result = cmd_rdeps(synthetic_index, 'nonexistent:skill:name', dep_types=set(DependencyType))
        assert result['status'] == 'error'


# =============================================================================
# Tests - validate subcommand logic (in-process)
# =============================================================================


class TestValidateSubcommand:
    """Tests for the ``validate`` command logic against the synthetic graph."""

    def test_validate_structured_output(self, synthetic_index):
        """validate returns the structured shape the contract requires."""
        result = cmd_validate(synthetic_index, dep_types=set(DependencyType))
        assert 'status' in result
        assert 'validation_result' in result
        assert 'total_components' in result
        assert 'total_dependencies' in result

    def test_validate_flags_unresolved(self, synthetic_index):
        """The synthetic graph's unresolved edges make validation fail."""
        result = cmd_validate(synthetic_index, dep_types=set(DependencyType))
        assert result['status'] == 'error'
        assert result['validation_result'] == 'failed'
        assert result['unresolved_count'] > 0

    def test_validate_counts_components(self, synthetic_index):
        """validate counts the discovered synthetic components (>0)."""
        result = cmd_validate(synthetic_index, dep_types=set(DependencyType))
        assert result['total_components'] > 0

    def test_validate_clean_graph_passes(self):
        """A graph with only resolvable edges validates as passed."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            bundles = Path(tmp) / 'marketplace' / 'bundles'
            beta = bundles / 'beta-bundle'
            _write(beta / '.claude-plugin' / 'plugin.json', '{\n  "name": "beta-bundle"\n}\n')
            _write(
                beta / 'skills' / 'only-skill' / 'SKILL.md',
                '---\nname: only-skill\ndescription: Standalone skill\n---\n# Only Skill\n',
            )
            index = build_dependency_index(bundles, set(DependencyType))
            result = cmd_validate(index, dep_types=set(DependencyType))

        assert result['status'] == 'success'
        assert result['validation_result'] == 'passed'
        assert result['unresolved_count'] == 0


# =============================================================================
# Tests - tree subcommand logic (in-process)
# =============================================================================


class TestTreeSubcommand:
    """Tests for the ``tree`` command logic against the synthetic graph."""

    def test_tree_produces_output(self, synthetic_index):
        """tree produces visual output rooted at the requested component."""
        result = cmd_tree(synthetic_index, _ALPHA, depth=2, dep_types=set(DependencyType))
        assert result['status'] == 'success'
        assert 'tree' in result
        assert _ALPHA in result['tree']

    def test_tree_includes_child_edge(self, synthetic_index):
        """tree output includes the resolved child edge to plan-beta."""
        result = cmd_tree(synthetic_index, _ALPHA, depth=2, dep_types=set(DependencyType))
        assert _BETA in result['tree']

    def test_tree_unknown_component(self, synthetic_index):
        """tree for an unknown component returns error status."""
        result = cmd_tree(
            synthetic_index,
            'nonexistent:skill:name',
            depth=2,
            dep_types=set(DependencyType),
        )
        assert result['status'] == 'error'


# =============================================================================
# Tests - Dependency Type Filtering (in-process)
# =============================================================================


class TestDepTypeFiltering:
    """Tests for dependency-type filtering of the ``deps`` command."""

    def test_filter_single_type(self, synthetic_index):
        """Filtering to a single dep type only returns that type."""
        result = cmd_deps(
            synthetic_index,
            _ALPHA,
            depth=10,
            dep_types={DependencyType.SKILL_REFERENCE},
        )
        for dep in result['direct_dependencies']:
            assert dep['type'] == DependencyType.SKILL_REFERENCE.value

    def test_filter_multiple_types(self, synthetic_index):
        """Filtering to multiple dep types only returns those types."""
        allowed = {DependencyType.SKILL_REFERENCE.value, DependencyType.PYTHON_IMPORT.value}
        result = cmd_deps(
            synthetic_index,
            _ALPHA,
            depth=10,
            dep_types={DependencyType.SKILL_REFERENCE, DependencyType.PYTHON_IMPORT},
        )
        for dep in result['direct_dependencies']:
            assert dep['type'] in allowed

    def test_parse_dep_types_valid(self):
        """parse_dep_types maps comma-separated names to the enum set."""
        result = parse_dep_types('skill,import')
        assert DependencyType.SKILL_REFERENCE in result
        assert DependencyType.PYTHON_IMPORT in result

    def test_parse_dep_types_invalid(self):
        """parse_dep_types raises ValueError on an unknown type name."""
        with pytest.raises(ValueError):
            parse_dep_types('invalid')


# =============================================================================
# Tests - Output Formats (in-process)
# =============================================================================


class TestOutputFormats:
    """Tests for serialize_output format branches."""

    def test_toon_format(self, synthetic_index):
        """TOON serialization of a validate result is parseable."""
        from toon_parser import parse_toon

        result = cmd_validate(synthetic_index, dep_types=set(DependencyType))
        rendered = serialize_output(result, 'toon')
        data = parse_toon(rendered)
        assert 'status' in data

    def test_json_format(self, synthetic_index):
        """JSON serialization of a validate result is parseable."""
        import json

        result = cmd_validate(synthetic_index, dep_types=set(DependencyType))
        rendered = serialize_output(result, 'json')
        data = json.loads(rendered)
        assert 'status' in data
        assert 'total_components' in data


# =============================================================================
# Tests - SKILL.md → Script Deps Discovery (in-process)
# =============================================================================


class TestSkillToScriptDeps:
    """Tests for SKILL.md -> script dependency discovery against the synthetic graph."""

    def test_skill_filters_to_script_type(self, synthetic_index):
        """--dep-types script only returns script-notation dependencies."""
        result = cmd_deps(
            synthetic_index,
            _ALPHA,
            depth=10,
            dep_types={DependencyType.SCRIPT_NOTATION},
        )
        for dep in result['direct_dependencies']:
            assert dep['type'] == DependencyType.SCRIPT_NOTATION.value

    def test_skill_component_type_is_skill(self, synthetic_index):
        """deps echoes the resolved component_type for a skill component."""
        result = cmd_deps(synthetic_index, _ALPHA, depth=10, dep_types=set(DependencyType))
        assert result['component_type'] == 'skill'


class TestGetBasePathBundleCacheRouting:
    """get_base_path routes deployed-bundle (plugin-cache) discovery through the layout op.

    The plugin-cache / auto fallback scopes resolve their cache root via
    ``_first_existing_bundle_cache_root`` →
    ``marketplace_paths.get_bundle_cache_roots`` (the platform-runtime layout
    op), so the Claude ``~/.claude/plugins/cache/...`` subpath is no longer
    hardcoded. Forcing the roots to a tmp dir proves the routing.
    """

    def test_plugin_cache_scope_uses_layout_op_roots(self, tmp_path, monkeypatch):
        """plugin-cache scope returns the first existing layout-op cache root."""
        cache = tmp_path / "deployed-cache"
        cache.mkdir()
        monkeypatch.setattr(
            _dep_index_mod, "get_bundle_cache_roots", lambda: (str(cache),)
        )
        assert _dep_index_mod.get_base_path("plugin-cache") == cache

    def test_plugin_cache_scope_skips_missing_root(self, tmp_path, monkeypatch):
        """A non-existent first root is skipped in favour of an existing later root."""
        present = tmp_path / "present-cache"
        present.mkdir()
        monkeypatch.setattr(
            _dep_index_mod,
            "get_bundle_cache_roots",
            lambda: (str(tmp_path / "missing"), str(present)),
        )
        assert _dep_index_mod.get_base_path("plugin-cache") == present

    def test_plugin_cache_scope_raises_when_no_root_exists(self, tmp_path, monkeypatch):
        """When no layout-op cache root exists, plugin-cache scope raises."""
        monkeypatch.setattr(
            _dep_index_mod, "get_bundle_cache_roots", lambda: (str(tmp_path / "nope"),)
        )
        with pytest.raises(FileNotFoundError):
            _dep_index_mod.get_base_path("plugin-cache")


# =============================================================================
# Tests - Index substrate file enumeration (enumerate_skill_files)
# =============================================================================
#
# ``enumerate_skill_files`` is the index-substrate primitive that walks each
# bundle's ``skills/`` tree once and returns the FULL file set the plugin-doctor
# framework needs: the skill SKILL.md, its markdown sub-documents (under
# references/standards/workflow/templates), and its scripts — INCLUDING private
# ``_``-prefixed Python modules. Pure enumeration, no parsing.


def _seed_skill_tree(root: Path) -> Path:
    """Build a synthetic ``marketplace/bundles`` tree with one richly-populated skill.

    Layout (bundle ``enum-bundle``):

      skills/full-skill/SKILL.md
      skills/full-skill/references/ref-one.md
      skills/full-skill/standards/std-a.md
      skills/full-skill/standards/nested/std-b.md      (rglob — nested sub-doc)
      skills/full-skill/workflow/flow.md
      skills/full-skill/templates/tmpl.md
      skills/full-skill/scripts/run.py
      skills/full-skill/scripts/_private.py            (private module — included)
      skills/full-skill/scripts/helper.sh
      skills/leaf-skill/SKILL.md                        (no sub-docs / scripts)

    Returns the ``marketplace/bundles`` directory path.
    """
    bundles = root / 'marketplace' / 'bundles'
    bundle = bundles / 'enum-bundle'
    _write(bundle / '.claude-plugin' / 'plugin.json', '{\n  "name": "enum-bundle"\n}\n')

    skill = bundle / 'skills' / 'full-skill'
    _write(skill / 'SKILL.md', '---\nname: full-skill\n---\n# Full Skill\n')
    _write(skill / 'references' / 'ref-one.md', '# Reference One\n')
    _write(skill / 'standards' / 'std-a.md', '# Standard A\n')
    _write(skill / 'standards' / 'nested' / 'std-b.md', '# Standard B\n')
    _write(skill / 'workflow' / 'flow.md', '# Flow\n')
    _write(skill / 'templates' / 'tmpl.md', '# Template\n')
    _write(skill / 'scripts' / 'run.py', '# script\n')
    _write(skill / 'scripts' / '_private.py', '"""private."""\n')
    _write(skill / 'scripts' / 'helper.sh', '#!/usr/bin/env bash\n')

    leaf = bundle / 'skills' / 'leaf-skill'
    _write(leaf / 'SKILL.md', '---\nname: leaf-skill\n---\n# Leaf Skill\n')

    return bundles


class TestEnumerateSkillFiles:
    """Tests for the ``enumerate_skill_files`` index-substrate primitive."""

    def test_enumerates_skill_md_for_each_skill(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            bundles = _seed_skill_tree(Path(tmp))
            files = enumerate_skill_files(bundles)

        skill_mds = {sf.skill for sf in files if sf.kind == 'skill_md'}
        assert skill_mds == {'full-skill', 'leaf-skill'}

    def test_enumerates_subdocs_across_all_four_dirs_recursively(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            bundles = _seed_skill_tree(Path(tmp))
            files = enumerate_skill_files(bundles)

        subdoc_names = {sf.file_path.name for sf in files if sf.kind == 'subdoc'}
        # One per references/standards/workflow/templates, plus the nested standard.
        assert subdoc_names == {'ref-one.md', 'std-a.md', 'std-b.md', 'flow.md', 'tmpl.md'}

    def test_enumerates_scripts_including_private_modules(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            bundles = _seed_skill_tree(Path(tmp))
            files = enumerate_skill_files(bundles)

        script_names = {sf.file_path.name for sf in files if sf.kind == 'script'}
        # Private ``_``-prefixed modules and ``.sh`` scripts are included.
        assert script_names == {'run.py', '_private.py', 'helper.sh'}

    def test_skillfile_carries_bundle_and_skill(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            bundles = _seed_skill_tree(Path(tmp))
            files = enumerate_skill_files(bundles)

        assert all(isinstance(sf, SkillFile) for sf in files)
        assert all(sf.bundle == 'enum-bundle' for sf in files)
        run_py = next(sf for sf in files if sf.file_path.name == 'run.py')
        assert run_py.skill == 'full-skill'
        assert run_py.kind == 'script'

    def test_leaf_skill_yields_only_skill_md(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            bundles = _seed_skill_tree(Path(tmp))
            files = enumerate_skill_files(bundles)

        leaf_files = [sf for sf in files if sf.skill == 'leaf-skill']
        assert len(leaf_files) == 1
        assert leaf_files[0].kind == 'skill_md'

    def test_empty_tree_yields_nothing(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            bundles = Path(tmp) / 'marketplace' / 'bundles'
            bundles.mkdir(parents=True)
            assert enumerate_skill_files(bundles) == []


# =============================================================================
# Tests - Parse-once AST cache (AstCache)
# =============================================================================
#
# ``AstCache`` is the index-substrate AST layer: a memoized ``ast.parse`` so
# each ``.py`` file is read and parsed at most once per scan run. The parse-once
# invariant is what the single-pass runner relies on to avoid the O(rules ×
# files) re-parse cost.


class TestAstCache:
    """Tests for the parse-once AST cache."""

    def test_get_tree_returns_ast_module(self, tmp_path):
        import ast

        script = tmp_path / 'mod.py'
        script.write_text('x = 1\n', encoding='utf-8')
        cache = AstCache()

        tree = cache.get_tree(script)

        assert isinstance(tree, ast.Module)

    def test_repeat_request_returns_identical_object_without_reparsing(self, tmp_path):
        script = tmp_path / 'mod.py'
        script.write_text('x = 1\n', encoding='utf-8')
        cache = AstCache()

        first = cache.get_tree(script)
        second = cache.get_tree(script)

        # Same object identity — the cached tree is handed back, not re-parsed.
        assert first is second
        assert cache.parse_count == 1

    def test_parse_count_counts_distinct_files_once_each(self, tmp_path):
        a = tmp_path / 'a.py'
        a.write_text('a = 1\n', encoding='utf-8')
        b = tmp_path / 'b.py'
        b.write_text('b = 2\n', encoding='utf-8')
        cache = AstCache()

        cache.get_tree(a)
        cache.get_tree(b)
        cache.get_tree(a)
        cache.get_tree(b)

        assert cache.parse_count == 2

    def test_missing_file_returns_none_and_is_cached(self, tmp_path):
        missing = tmp_path / 'gone.py'
        cache = AstCache()

        first = cache.get_tree(missing)
        second = cache.get_tree(missing)

        assert first is None
        assert second is None
        # A failed read never increments parse_count and is not re-attempted.
        assert cache.parse_count == 0

    def test_syntax_error_returns_none_and_is_cached(self, tmp_path):
        broken = tmp_path / 'broken.py'
        broken.write_text('def oops(\n', encoding='utf-8')
        cache = AstCache()

        first = cache.get_tree(broken)
        second = cache.get_tree(broken)

        assert first is None
        assert second is None
        # The unparseable result is cached — parse_count stays at zero (no
        # successful parse) and the file is not re-parsed.
        assert cache.parse_count == 0
        assert str(broken) in cache._trees


# =============================================================================
# Tests - Skill sub-documents as dependency edge sources
# =============================================================================
#
# ``build_dependency_index`` used to read edges ONLY from component definition
# files (SKILL.md, agents/*.md, commands/*.md, scripts/*), so a dependency cited
# in ``workflow/light-lane.md`` or ``standards/agent-behavior-rules.md`` was
# invisible to ``deps`` / ``rdeps`` / ``tree`` / ``validate``.
#
# ``iter_skill_subdoc_edge_sources`` closes that gap with a NAME-FREE walk. The
# coverage test below derives its population from the filesystem — never from a
# directory-name list — so a new sub-directory kind fails the test instead of
# silently re-opening the blind spot.


def _real_subdoc_population() -> set[Path]:
    """Every ``.md`` under a real ``skills/<skill>/**`` outside ``scripts/``.

    Derived by a single glob over the live tree, deliberately expressed
    DIFFERENTLY from the implementation's nested walk so the comparison is a
    genuine cross-check rather than a restatement of the implementation.
    ``SKILL.md`` is excluded — it is scanned as the skill's own definition file.
    """
    population: set[Path] = set()
    for plugin_json in _BUNDLES_ROOT.rglob('.claude-plugin/plugin.json'):
        bundle_dir = plugin_json.parent.parent
        for md_file in bundle_dir.glob('skills/*/**/*.md'):
            rel = md_file.relative_to(bundle_dir)
            # rel is skills/<skill>/<...>; skip the skill's own SKILL.md.
            if len(rel.parts) == 3 and rel.name == 'SKILL.md':
                continue
            if 'scripts' in rel.parts[2:-1]:
                continue
            population.add(md_file)
    return population


def test_subdoc_edge_walk_covers_every_real_skill_markdown():
    """The edge-source walk enumerates the whole real sub-document population.

    Population-derived: a new sub-directory kind appearing on disk is covered
    automatically, and a regression that reintroduces a directory-name allowlist
    fails here instead of silently shrinking the edge graph.
    """
    population = _real_subdoc_population()
    assert population, 'population is empty — the bundle walk found no sub-documents'

    enumerated = {path for _owner, path in iter_skill_subdoc_edge_sources(_BUNDLES_ROOT)}

    missing = sorted(str(p) for p in population - enumerated)
    assert missing == [], f'{len(missing)} sub-document(s) are not edge sources: {missing[:10]}'
    assert enumerated == population


def test_subdoc_edges_are_attributed_to_the_owning_skill():
    """Every edge source is attributed to the skill whose directory contains it."""
    sources = iter_skill_subdoc_edge_sources(_BUNDLES_ROOT)
    assert sources

    for owner, path in sources:
        assert owner.component_type == 'skill'
        # The owning skill's directory is an ancestor of the sub-document.
        assert owner.name in path.parts


def test_subdoc_edge_walk_is_name_free_over_unknown_directories():
    """A sub-directory kind outside ``SKILL_SUBDOC_DIRS`` still contributes edges.

    Pins the residual property directly: ``examples/`` is not a member of the
    lint-population constant, so a name-list implementation would miss it.
    """
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        bundles = _seed_skill_tree(Path(tmp))
        skill_dir = bundles / 'enum-bundle' / 'skills' / 'full-skill'
        _write(skill_dir / 'examples' / 'sample.md', '# Example\n')
        _write(skill_dir / 'knowledge' / 'note.md', '# Knowledge\n')

        enumerated = {path.name for _owner, path in iter_skill_subdoc_edge_sources(bundles)}

    assert 'sample.md' in enumerated
    assert 'note.md' in enumerated
    # SKILL.md is the component's own definition file, never a sub-document.
    assert 'SKILL.md' not in enumerated


def test_subdoc_edge_walk_excludes_scripts_directory_markdown():
    """Markdown under ``scripts/`` is not a sub-document edge source."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        bundles = _seed_skill_tree(Path(tmp))
        skill_dir = bundles / 'enum-bundle' / 'skills' / 'full-skill'
        _write(skill_dir / 'scripts' / 'NOTES.md', '# Script notes\n')

        enumerated = {path.name for _owner, path in iter_skill_subdoc_edge_sources(bundles)}

    assert 'NOTES.md' not in enumerated


def test_subdocuments_are_edge_sources_but_never_components():
    """Sub-documents add edges without entering the component namespace.

    ``ComponentId`` has no sub-document type; registering one would change the
    namespace that ``deps`` / ``rdeps`` / ``tree`` / ``validate`` all key on.
    """
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        bundles = _seed_skill_tree(Path(tmp))
        skill_dir = bundles / 'enum-bundle' / 'skills' / 'full-skill'
        # A sub-document in a non-allowlisted directory citing another skill.
        _write(
            skill_dir / 'examples' / 'usage.md',
            '# Usage\n\nSkill: enum-bundle:leaf-skill\n',
        )

        index = build_dependency_index(bundles)
        component_keys = set(index.components)
        discovered_keys = {c.component_id.to_notation() for c in discover_components(bundles)}

    # The edge pass added no components.
    assert component_keys == discovered_keys
    # ...but the sub-document's edge landed, attributed to the OWNING skill.
    rdeps = index.get_reverse_deps('enum-bundle:leaf-skill')
    assert any(dep.source.to_notation() == 'enum-bundle:full-skill' for dep in rdeps)


def test_live_anchor_persona_agent_subdoc_edge_is_indexed():
    """The verified live anchor: a real edge that only a sub-document carries.

    ``plan-marshall:persona-plan-marshall-agent`` cites
    ``plan-marshall:untrusted-ingestion:validate_struct`` twice — both citations
    live in its ``standards/agent-behavior-rules.md``, never in its ``SKILL.md``
    — so this dependent was absent from ``rdeps`` before the sub-document edge
    pass existed.

    The anchor is asserted against the THREE-part script notation because that
    is what those citations actually are; the two-part skill notation
    ``plan-marshall:untrusted-ingestion`` is a different index key that these
    particular citations do not produce.
    """
    index = build_dependency_index(_BUNDLES_ROOT)

    dependents = {
        dep.source.to_notation()
        for dep in index.get_reverse_deps('plan-marshall:untrusted-ingestion:validate_struct')
    }

    assert 'plan-marshall:persona-plan-marshall-agent' in dependents


def test_skill_subdoc_dirs_constant_is_not_widened():
    """``SKILL_SUBDOC_DIRS`` still holds exactly its four kinds.

    Guards the deliberate non-widening: this constant is the plugin-doctor LINT
    population (via ``enumerate_skill_files``), not the dependency-edge
    population. A "helpful" edit that widens it here would silently expand what
    plugin-doctor lints — a blast radius the edge-source change deliberately
    avoided by walking name-free instead.
    """
    assert SKILL_SUBDOC_DIRS == ('references', 'standards', 'workflow', 'templates')


# =============================================================================
# Tests - Detector precision (the four non-reference colon-triple classes)
# =============================================================================
#
# ``detect_script_notations`` scans for the bare ``a:b:c`` shape, which several
# token families share without referencing any component. Each class below gets
# its OWN case, and the genuinely-broken reference gets a case asserting it is
# STILL reported — a precision fix that also suppressed real findings would have
# made the gate worse rather than better.


class TestNonReferenceColonTriples:
    """Each false-positive class is suppressed, one case per class."""

    @staticmethod
    def _detect(content):
        source = ComponentId(bundle='test', component_type='skill', name='test')
        return detect_script_notations(content, source)

    @classmethod
    def _provisional(cls, content):
        """Every match is flagged provisional — i.e. excluded unless it names a component."""
        deps = cls._detect(content)
        return bool(deps) and all(d.provisional for d in deps)

    def test_documentation_placeholder_is_not_a_reference(self):
        """Prose documenting the notation form produces no finding."""
        content = 'Scripts are referenced as `bundle:skill:script` in documentation.\n'
        assert self._provisional(content)

    def test_maven_placeholder_coordinate_is_not_a_reference(self):
        """``groupId:artifactId:scope`` documents a coordinate, not a script."""
        content = 'Each module names dependencies as `groupId:artifactId:scope`.\n'
        assert self._provisional(content)

    def test_canonical_verification_step_is_not_a_reference(self):
        """``default:verify:{canonical}`` is a build command, not a script."""
        content = 'Set per_deliverable_build to default:verify:quality-gate here.\n'
        assert self._provisional(content)

    def test_decision_log_prefix_is_not_a_reference(self):
        """A parenthesised ``(bundle:skill:step)`` prefix names the emitting step."""
        content = '--message "(plan-marshall:phase-6-finalize:qgate) Finding fixed"\n'
        assert self._provisional(content)

    def test_dotted_build_coordinate_is_not_a_reference(self):
        """A Maven coordinate preceded by its group prefix is not a script."""
        content = 'Depend on "de.cuioss:cui-java-tools:compile" for the utilities.\n'
        assert self._provisional(content)

    def test_gradle_task_path_is_not_a_reference(self):
        """A Gradle task path (leading colon) is not a script notation."""
        content = './gradlew :services:auth-service:build\n'
        assert self._provisional(content)

    def test_subdocument_path_is_not_a_reference(self):
        """``bundle:skill:dir/file.md`` addresses a document, not a script."""
        content = 'Load `plan-marshall:manage-lessons:references/dedup-analysis.md` first.\n'
        assert self._provisional(content)

    def test_dotted_document_suffix_is_not_a_reference(self):
        """``bundle:skill:name.md`` addresses a workflow document, not a script."""
        content = 'See `plan-marshall:plan-marshall:planning.md` for the contract.\n'
        assert self._provisional(content)

    def test_real_notation_at_end_of_sentence_is_still_a_reference(self):
        """A trailing sentence period must NOT be read as a document suffix."""
        deps = self._detect('Run plan-marshall:manage-files:manage-files.\n')
        assert len(deps) == 1
        assert not deps[0].provisional
        assert deps[0].target.to_notation() == 'plan-marshall:manage-files:manage-files'

    def test_genuine_notation_is_still_detected(self):
        """The precision guards leave an ordinary script reference untouched."""
        content = 'python3 .plan/execute-script.py plan-marshall:manage-files:manage-files add\n'
        deps = self._detect(content)
        assert len(deps) == 1
        assert not deps[0].provisional
        assert deps[0].target.to_notation() == 'plan-marshall:manage-files:manage-files'


class TestPlaceholderSkillReferences:
    """Placeholder segments are suppressed on the skill-reference detector too."""

    def test_skill_pattern_placeholder_is_not_a_reference(self):
        source = ComponentId(bundle='test', component_type='skill', name='test')
        deps = detect_skill_references('Skill: bundle:skill-name\n', {}, source)
        assert deps and all(d.provisional for d in deps)

    def test_frontmatter_placeholder_is_not_a_reference(self):
        source = ComponentId(bundle='test', component_type='skill', name='test')
        frontmatter = {'skills': ['bundle-name:skill-name']}
        deps = detect_skill_references('', frontmatter, source)
        assert deps and all(d.provisional for d in deps)

    def test_real_skill_reference_is_still_detected(self):
        source = ComponentId(bundle='test', component_type='skill', name='test')
        deps = detect_skill_references('Skill: plan-marshall:phase-1-init\n', {}, source)
        assert len(deps) == 1
        assert deps[0].target.to_notation() == 'plan-marshall:phase-1-init'


# =============================================================================
# Tests - Precision regression fixture (exact finding count)
# =============================================================================
#
# ONE instance of each false-positive class PLUS ONE genuinely-broken reference,
# asserting EXACTLY ONE finding. The count is the test: an "at least one"
# assertion would pass against a detector that still reported every row.
#
# Graph shape (bundle ``precision-bundle``):
#
#   manage-thing  (skill) + manage-thing.py  (its same-named ENTRY script)
#   (six excluded instances in total, one per documented class)
#   phase-thing   (skill, NO entry script)
#
# ``manage-thing`` having an entry script is what lets the subcommand class
# resolve; ``phase-thing`` having none is what keeps the genuinely-broken
# reference unresolved.

_PRECISION_PLUGIN_JSON = '{\n  "name": "precision-bundle",\n  "version": "0.1.0"\n}\n'


def _build_precision_graph(root: Path) -> Path:
    """Create the precision-fixture ``marketplace/bundles`` tree under ``root``."""
    bundles = root / 'marketplace' / 'bundles'
    pb = bundles / 'precision-bundle'
    _write(pb / '.claude-plugin' / 'plugin.json', _PRECISION_PLUGIN_JSON)

    _write(
        pb / 'skills' / 'manage-thing' / 'SKILL.md',
        '---\nname: manage-thing\ndescription: Entry-script-bearing skill\n---\n'
        '# Manage Thing\n',
    )
    _write(
        pb / 'skills' / 'manage-thing' / 'scripts' / 'manage-thing.py',
        '#!/usr/bin/env python3\n"""Entry script dispatching subcommands."""\n',
    )
    _write(
        pb / 'skills' / 'phase-thing' / 'SKILL.md',
        '---\nname: phase-thing\ndescription: Skill with no entry script\n---\n'
        '# Phase Thing\n\n'
        '## Notation classes\n\n'
        'A script is referenced as `bundle:skill:script` in documentation.\n'
        'The subcommand `precision-bundle:manage-thing:compose` runs the verb.\n'
        'The build step is `default:verify:quality-gate` for this phase.\n'
        '--message "(precision-bundle:phase-thing:qgate) step emitted this"\n'
        'The coordinate is "de.example:example-lib:compile" in the POM.\n'
        'Load `precision-bundle:manage-thing:standards/detail.md` first.\n'
        'python3 .plan/execute-script.py precision-bundle:phase-thing:ghost-script run\n',
    )
    return bundles


@pytest.fixture
def precision_index():
    """Build a ``DependencyIndex`` over the precision fixture (all dep types)."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        bundles = _build_precision_graph(Path(tmp))
        yield build_dependency_index(bundles, set(DependencyType))


class TestPrecisionRegressionFixture:
    """The fixture holds five non-references and one real break; exactly one is reported."""

    def test_exactly_one_finding(self, precision_index):
        """EXACTLY one unresolved dependency — not 'at least one'."""
        result = cmd_validate(precision_index, set(DependencyType))
        assert result['unresolved_count'] == 1

    def test_the_one_finding_is_the_genuinely_broken_reference(self, precision_index):
        """The surviving finding is the ghost script, not a suppressed class."""
        result = cmd_validate(precision_index, set(DependencyType))
        assert result['unresolved'][0]['target'] == 'precision-bundle:phase-thing:ghost-script'

    def test_subcommand_resolves_to_the_entry_script(self, precision_index):
        """The subcommand reference resolves rather than reporting unresolved."""
        targets = {
            dep.target.to_notation()
            for dep in precision_index.get_forward_deps('precision-bundle:phase-thing')
        }
        assert 'precision-bundle:manage-thing:manage-thing' in targets

    def test_validation_fails_while_the_real_break_stands(self, precision_index):
        """The gate still fails closed on the genuinely-broken reference."""
        result = cmd_validate(precision_index, set(DependencyType))
        assert result['validation_result'] == 'failed'


class TestSubcommandResolution:
    """A subcommand resolves only when the skill HAS a same-named entry script."""

    def test_subcommand_without_entry_script_stays_unresolved(self, precision_index):
        """``phase-thing`` has no entry script, so its third segment cannot resolve."""
        result = cmd_validate(precision_index, set(DependencyType))
        unresolved = {row['target'] for row in result['unresolved']}
        assert 'precision-bundle:phase-thing:ghost-script' in unresolved


# =============================================================================
# Tests - Exclusions are provisional (fail-closed)
# =============================================================================
#
# Every exclusion recognises a SHAPE, and a shape is evidence rather than proof:
# a genuine reference can be written parenthetically or with a file extension.
# Dropping on shape alone would put a hole in the gate, so a match on an excluded
# shape is provisional and the index keeps it when it names a real component.


def _probe_reference(tmp_path, line):
    """Index a synthetic bundle whose caller cites `line`; return edges to the real script."""
    root = tmp_path / 'marketplace' / 'bundles' / 'probe-bundle'
    _write(root / '.claude-plugin' / 'plugin.json', '{\n  "name": "probe-bundle"\n}\n')
    _write(
        root / 'skills' / 'real-skill' / 'SKILL.md',
        '---\nname: real-skill\ndescription: Has a same-named entry script\n---\n# Real\n',
    )
    _write(root / 'skills' / 'real-skill' / 'scripts' / 'real-skill.py', '#!/usr/bin/env python3\n')
    _write(
        root / 'skills' / 'caller' / 'SKILL.md',
        '---\nname: caller\ndescription: Cites the probe line\n---\n# Caller\n' + line + '\n',
    )
    index = build_dependency_index(root.parent, set(DependencyType))
    return [
        (dep.target.to_notation(), dep.resolved)
        for deps in index.forward_deps.values()
        for dep in deps
        if 'real-skill' in dep.target.to_notation()
    ]


class TestExclusionsAreProvisional:
    """An excluded shape that names a REAL component is kept, not swallowed."""

    def test_parenthesised_real_reference_is_kept(self, tmp_path):
        """A genuine reference written parenthetically must not vanish."""
        edges = _probe_reference(tmp_path, 'See (probe-bundle:real-skill:real-skill) for details.')
        assert edges == [('probe-bundle:real-skill:real-skill', True)]

    def test_real_reference_with_py_suffix_is_kept(self, tmp_path):
        """A genuine reference carrying a `.py` suffix must not vanish."""
        edges = _probe_reference(tmp_path, 'Run probe-bundle:real-skill:real-skill.py now.')
        assert edges == [('probe-bundle:real-skill:real-skill', True)]

    def test_parenthesised_non_reference_is_still_dropped(self, tmp_path):
        """The decision-log prefix itself stays excluded — the control for the case above."""
        assert _probe_reference(tmp_path, 'Emitted (probe-bundle:real-skill:some-step) here.') == []

    def test_dotted_coordinate_is_still_dropped(self, tmp_path):
        """A build coordinate stays excluded — the control for the `.py` case above."""
        assert _probe_reference(tmp_path, 'Coordinate de.x:real-skill:compile in the POM.') == []


class TestMisspelledScriptSegmentIsNotASubcommand:
    """A script segment that is the skill name in the wrong case style is a defect."""

    def test_underscored_script_segment_stays_unresolved(self, tmp_path):
        """`bundle:skill:skill_name` is a misspelling, not a verb, and must be reported.

        plugin-doctor's `manage-findings-invocation-invalid` rule exists to raise
        exactly this: the executor keys on the third segment literally, so the
        underscored spelling does not resolve. Retargeting it onto the entry
        script would suppress a finding the repository deliberately makes.
        """
        edges = _probe_reference(tmp_path, 'Run probe-bundle:real-skill:real_skill add now.')
        assert edges == [('probe-bundle:real-skill:real_skill', False)]

    def test_genuine_verb_still_resolves_to_the_entry_script(self, tmp_path):
        """The control: an ordinary verb still retargets onto the entry script."""
        edges = _probe_reference(tmp_path, 'Run probe-bundle:real-skill:compose now.')
        assert edges == [('probe-bundle:real-skill:real-skill', True)]
