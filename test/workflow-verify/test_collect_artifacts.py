#!/usr/bin/env python3
"""
Tests for collect-artifacts.py script.

Tests the artifact collection functionality that gathers workflow outputs
via manage-* tool interfaces for verification.
"""

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Load script module directly from project-level path
PROJECT_ROOT = Path(__file__).parent.parent.parent
SCRIPT_PATH = PROJECT_ROOT / '.claude' / 'skills' / 'workflow-verify' / 'scripts' / 'collect-artifacts.py'

# Load module from file path
spec = importlib.util.spec_from_file_location('collect_artifacts', SCRIPT_PATH)
assert spec is not None and spec.loader is not None
collect_artifacts = importlib.util.module_from_spec(spec)
sys.modules['collect_artifacts'] = collect_artifacts
spec.loader.exec_module(collect_artifacts)

# Import what we need
ArtifactCollector = collect_artifacts.ArtifactCollector
serialize_toon = collect_artifacts.serialize_toon


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

    @patch('collect_artifacts.run_manage_script')
    def test_collect_solution_outline_success(self, mock_run, output_dir):
        """Test successful solution outline collection."""
        mock_run.return_value = (0, '# Solution Outline\n\nContent here', '')

        collector = ArtifactCollector('test-plan', output_dir)
        result = collector.collect_solution_outline()

        assert result is True
        assert (output_dir / 'solution_outline.md').exists()
        assert len(collector.collected) == 1
        assert collector.collected[0]['status'] == 'success'

    @patch('collect_artifacts.run_manage_script')
    def test_collect_solution_outline_failure(self, mock_run, output_dir):
        """Test failed solution outline collection."""
        mock_run.return_value = (1, '', 'File not found')

        collector = ArtifactCollector('test-plan', output_dir)
        result = collector.collect_solution_outline()

        assert result is False
        assert not (output_dir / 'solution_outline.md').exists()
        assert collector.collected[0]['status'] == 'failed'
        assert len(collector.errors) == 1

    @patch('collect_artifacts.run_manage_script')
    def test_collect_config_success(self, mock_run, output_dir):
        """Test successful config collection."""
        mock_run.return_value = (0, 'plan_type: implementation\ndomains: java,docs', '')

        collector = ArtifactCollector('test-plan', output_dir)
        result = collector.collect_config()

        assert result is True
        assert (output_dir / 'config.toon').exists()
        content = (output_dir / 'config.toon').read_text()
        assert 'plan_type' in content

    @patch('collect_artifacts.run_manage_script')
    def test_collect_references_not_found(self, mock_run, output_dir):
        """Test references collection when file doesn't exist (acceptable)."""
        mock_run.return_value = (1, '', 'Not found')

        collector = ArtifactCollector('test-plan', output_dir)
        result = collector.collect_references()

        # References not existing is not an error
        assert result is False
        assert collector.collected[0]['status'] == 'not_found'
        assert len(collector.errors) == 0  # Not an error

    @patch('collect_artifacts.run_manage_script')
    def test_collect_tasks_creates_subdirectory(self, mock_run, output_dir):
        """Test that task collection creates tasks subdirectory."""
        mock_run.return_value = (0, 'task_count: 2\ntasks[2]:\n  TASK-01\n  TASK-02', '')

        collector = ArtifactCollector('test-plan', output_dir)
        collector.collect_tasks()

        assert (output_dir / 'tasks').exists()
        assert (output_dir / 'tasks-list.toon').exists()

    @patch('collect_artifacts.run_manage_script')
    def test_collect_all_returns_summary(self, mock_run, output_dir):
        """Test that collect_all returns proper summary."""
        # Mock all scripts to succeed
        mock_run.return_value = (0, 'status: success\nexists: true', '')

        collector = ArtifactCollector('test-plan', output_dir)
        results = collector.collect_all()

        assert results['status'] in ['success', 'partial']
        assert results['plan_id'] == 'test-plan'
        assert results['output_dir'] == str(output_dir)
        assert 'collected_count' in results
        assert 'artifacts' in results

    @patch('collect_artifacts.run_manage_script')
    def test_collect_all_includes_tasks_for_plan_phase(self, mock_run, output_dir):
        """Test that tasks are collected when 3-plan phase specified."""
        mock_run.return_value = (0, 'status: success\nexists: true\ntask_count: 1', '')

        collector = ArtifactCollector('test-plan', output_dir)
        collector.collect_all(phases=['3-plan'])

        # Should have called manage-tasks
        call_args = [str(c) for c in mock_run.call_args_list]
        tasks_called = any('manage-tasks' in str(c) for c in call_args)
        assert tasks_called

    @patch('collect_artifacts.run_manage_script')
    def test_collect_all_skips_tasks_for_outline_only(self, mock_run, output_dir):
        """Test that tasks are not collected for outline-only phase."""
        mock_run.return_value = (0, 'status: success\nexists: true', '')

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
        collector = ArtifactCollector('test-plan', output_dir)

        with patch('collect_artifacts.run_manage_script', return_value=(0, 'content', '')):
            collector.collect_all()

        assert output_dir.exists()

    def test_empty_stdout_handled(self, tmp_path):
        """Test that empty stdout is handled gracefully."""
        output_dir = tmp_path / 'artifacts'
        output_dir.mkdir()

        collector = ArtifactCollector('test-plan', output_dir)

        with patch('collect_artifacts.run_manage_script', return_value=(0, '', '')):
            result = collector.collect_solution_outline()

        assert result is False  # Empty content treated as failure
