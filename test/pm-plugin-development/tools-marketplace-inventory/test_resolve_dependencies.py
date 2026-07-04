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
SkillFile = _dep_index_mod.SkillFile
AstCache = _dep_index_mod.AstCache

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
        comp = ComponentId.from_notation('plan-marshall:commands:tools-fix')
        assert comp is not None
        assert comp.bundle == 'plan-marshall'
        assert comp.component_type == 'command'
        assert comp.name == 'tools-fix'

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
