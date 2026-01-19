#!/usr/bin/env python3
"""
Tests for collect-artifacts.py script.

Tests the artifact collection functionality that gathers workflow outputs
via manage-* tool interfaces for verification.
"""

from unittest.mock import patch

import pytest

# Import the loaded module from conftest (PYTHONPATH is already set up)
from conftest import collect_artifacts

# Import what we need from the loaded module
ArtifactCollector = collect_artifacts.ArtifactCollector

# Import serialize_toon from toon_parser (same as the script does)
from toon_parser import serialize_toon  # type: ignore[import-not-found]  # noqa: E402


class TestArtifactCollector:
    """Tests for ArtifactCollector class."""

    @pytest.fixture
    def output_dir(self, tmp_path):
        """Create a temporary output directory."""
        out = tmp_path / 'artifacts'
        out.mkdir()
        return out

    def test_collector_initialization(self, output_dir):
        """Test collector initializes correctly."""
        collector = ArtifactCollector('test-plan', output_dir)
        assert collector.plan_id == 'test-plan'
        assert collector.output_dir == output_dir
        assert collector.collected == []
        assert collector.errors == []

    def test_collect_solution_outline_success(self, output_dir, tmp_path):
        """Test successful solution outline collection."""
        # Create mock solution file
        solution_path = tmp_path / 'solution_outline.md'
        solution_path.write_text('# Solution Outline\n\nContent here')

        with patch('collect_artifacts.get_solution_path', return_value=solution_path):
            collector = ArtifactCollector('test-plan', output_dir)
            result = collector.collect_solution_outline()

        assert result is True
        assert (output_dir / 'solution_outline.md').exists()
        assert len(collector.collected) == 1
        assert collector.collected[0]['status'] == 'success'

    def test_collect_solution_outline_failure(self, output_dir, tmp_path):
        """Test failed solution outline collection."""
        # Point to non-existent file
        solution_path = tmp_path / 'nonexistent.md'

        with patch('collect_artifacts.get_solution_path', return_value=solution_path):
            collector = ArtifactCollector('test-plan', output_dir)
            result = collector.collect_solution_outline()

        assert result is False
        assert not (output_dir / 'solution_outline.md').exists()
        assert collector.collected[0]['status'] == 'failed'
        assert len(collector.errors) == 1

    def test_collect_config_success(self, output_dir, tmp_path):
        """Test successful config collection."""
        config_path = tmp_path / 'config.toon'
        config_path.write_text('plan_type: implementation\ndomains: java,docs')

        with patch('collect_artifacts.get_config_path', return_value=config_path):
            collector = ArtifactCollector('test-plan', output_dir)
            result = collector.collect_config()

        assert result is True
        assert (output_dir / 'config.toon').exists()
        content = (output_dir / 'config.toon').read_text()
        assert 'plan_type' in content

    def test_collect_references_not_found(self, output_dir, tmp_path):
        """Test references collection when file doesn't exist (acceptable)."""
        refs_path = tmp_path / 'nonexistent.toon'

        with patch('collect_artifacts.get_references_path', return_value=refs_path):
            collector = ArtifactCollector('test-plan', output_dir)
            result = collector.collect_references()

        # References not existing is not an error
        assert result is False
        assert collector.collected[0]['status'] == 'not_found'
        assert len(collector.errors) == 0  # Not an error

    def test_collect_tasks_creates_subdirectory(self, output_dir, tmp_path):
        """Test that task collection creates tasks subdirectory."""
        # Create mock plan directory with task files
        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        (plan_dir / 'TASK-01.toon').write_text('id: TASK-01')
        (plan_dir / 'TASK-02.toon').write_text('id: TASK-02')

        with patch('collect_artifacts.base_path', return_value=plan_dir):
            collector = ArtifactCollector('test-plan', output_dir)
            collector.collect_tasks()

        assert (output_dir / 'tasks').exists()
        assert (output_dir / 'tasks-list.toon').exists()

    def test_collect_all_returns_summary(self, output_dir, tmp_path):
        """Test that collect_all returns proper summary."""
        # Create mock files
        solution_path = tmp_path / 'solution_outline.md'
        solution_path.write_text('# Solution\n\n## Summary\n\n## Overview\n\n## Deliverables')

        config_path = tmp_path / 'config.toon'
        config_path.write_text('plan_type: test')

        status_path = tmp_path / 'status.toon'
        status_path.write_text('current_phase: execute')

        refs_path = tmp_path / 'references.toon'
        refs_path.write_text('branch: main')

        log_path = tmp_path / 'work.log'
        log_path.write_text('[INFO] Started')

        with (
            patch('collect_artifacts.get_solution_path', return_value=solution_path),
            patch('collect_artifacts.get_config_path', return_value=config_path),
            patch('collect_artifacts.get_status_path', return_value=status_path),
            patch('collect_artifacts.get_references_path', return_value=refs_path),
            patch('collect_artifacts.get_log_path', return_value=log_path),
            patch(
                'collect_artifacts.parse_document_sections',
                return_value={'Deliverables': '### 1. Test\n\n**Metadata:**\n- domain: test'},
            ),
            patch('collect_artifacts.extract_deliverables', return_value=[{'id': '1', 'title': 'Test'}]),
        ):
            collector = ArtifactCollector('test-plan', output_dir)
            results = collector.collect_all()

        assert results['status'] in ['success', 'partial']
        assert results['plan_id'] == 'test-plan'
        assert results['output_dir'] == str(output_dir)
        assert 'collected_count' in results
        assert 'artifacts' in results

    def test_collect_all_includes_tasks_for_plan_phase(self, output_dir, tmp_path):
        """Test that tasks are collected when 3-plan phase specified."""
        # Create mock files
        solution_path = tmp_path / 'solution_outline.md'
        solution_path.write_text('# Solution')

        config_path = tmp_path / 'config.toon'
        config_path.write_text('plan_type: test')

        status_path = tmp_path / 'status.toon'
        status_path.write_text('current_phase: execute')

        refs_path = tmp_path / 'references.toon'
        refs_path.write_text('branch: main')

        log_path = tmp_path / 'work.log'
        log_path.write_text('[INFO] Started')

        plan_dir = tmp_path / 'plan'
        plan_dir.mkdir()
        (plan_dir / 'TASK-01.toon').write_text('id: TASK-01')

        with (
            patch('collect_artifacts.get_solution_path', return_value=solution_path),
            patch('collect_artifacts.get_config_path', return_value=config_path),
            patch('collect_artifacts.get_status_path', return_value=status_path),
            patch('collect_artifacts.get_references_path', return_value=refs_path),
            patch('collect_artifacts.get_log_path', return_value=log_path),
            patch('collect_artifacts.base_path', return_value=plan_dir),
            patch('collect_artifacts.parse_document_sections', return_value={'Deliverables': ''}),
            patch('collect_artifacts.extract_deliverables', return_value=[]),
        ):
            collector = ArtifactCollector('test-plan', output_dir)
            collector.collect_all(phases=['3-plan'])

        assert (output_dir / 'tasks-list.toon').exists()

    def test_collect_all_skips_tasks_for_outline_only(self, output_dir, tmp_path):
        """Test that tasks are not collected for outline-only phase."""
        # Create mock files
        solution_path = tmp_path / 'solution_outline.md'
        solution_path.write_text('# Solution')

        config_path = tmp_path / 'config.toon'
        config_path.write_text('plan_type: test')

        status_path = tmp_path / 'status.toon'
        status_path.write_text('current_phase: execute')

        refs_path = tmp_path / 'references.toon'
        refs_path.write_text('branch: main')

        log_path = tmp_path / 'work.log'
        log_path.write_text('[INFO] Started')

        with (
            patch('collect_artifacts.get_solution_path', return_value=solution_path),
            patch('collect_artifacts.get_config_path', return_value=config_path),
            patch('collect_artifacts.get_status_path', return_value=status_path),
            patch('collect_artifacts.get_references_path', return_value=refs_path),
            patch('collect_artifacts.get_log_path', return_value=log_path),
            patch('collect_artifacts.parse_document_sections', return_value={'Deliverables': ''}),
            patch('collect_artifacts.extract_deliverables', return_value=[]),
        ):
            collector = ArtifactCollector('test-plan', output_dir)
            collector.collect_all(phases=['2-outline'])

        # Should not have tasks-list.toon
        assert not (output_dir / 'tasks-list.toon').exists()


class TestSerializeToon:
    """Tests for TOON serialization in collect_artifacts."""

    def test_filters_none_values(self):
        """Test that None values can be filtered before serialization."""
        data = {'status': 'success', 'errors': None}
        # Filter before serializing
        filtered = {k: v for k, v in data.items() if v is not None}
        result = serialize_toon(filtered)
        assert 'errors' not in result

    def test_handles_artifact_list(self):
        """Test serialization of artifacts list."""
        data = {
            'artifacts': [
                {'artifact': 'file1.md', 'status': 'success'},
                {'artifact': 'file2.md', 'status': 'failed'},
            ]
        }
        result = serialize_toon(data)
        assert 'artifacts[2]' in result
        assert 'file1.md' in result
        assert 'success' in result


class TestEdgeCases:
    """Edge case tests."""

    def test_collector_creates_output_dir(self, tmp_path):
        """Test that collector creates output directory if it doesn't exist."""
        output_dir = tmp_path / 'new' / 'nested' / 'dir'

        # Create mock files
        solution_path = tmp_path / 'solution.md'
        solution_path.write_text('# Solution')

        config_path = tmp_path / 'config.toon'
        config_path.write_text('plan_type: test')

        status_path = tmp_path / 'status.toon'
        status_path.write_text('current_phase: execute')

        refs_path = tmp_path / 'refs.toon'

        log_path = tmp_path / 'work.log'

        collector = ArtifactCollector('test-plan', output_dir)

        with (
            patch('collect_artifacts.get_solution_path', return_value=solution_path),
            patch('collect_artifacts.get_config_path', return_value=config_path),
            patch('collect_artifacts.get_status_path', return_value=status_path),
            patch('collect_artifacts.get_references_path', return_value=refs_path),
            patch('collect_artifacts.get_log_path', return_value=log_path),
            patch('collect_artifacts.parse_document_sections', return_value={'Deliverables': ''}),
            patch('collect_artifacts.extract_deliverables', return_value=[]),
        ):
            collector.collect_all()

        assert output_dir.exists()

    def test_empty_solution_handled(self, tmp_path):
        """Test that empty solution file is handled gracefully."""
        output_dir = tmp_path / 'artifacts'
        output_dir.mkdir()

        # Create empty solution file
        solution_path = tmp_path / 'solution.md'
        solution_path.write_text('')

        collector = ArtifactCollector('test-plan', output_dir)

        with patch('collect_artifacts.get_solution_path', return_value=solution_path):
            result = collector.collect_solution_outline()

        # Empty content is still collected (file exists)
        assert result is True
