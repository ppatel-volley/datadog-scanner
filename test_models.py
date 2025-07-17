"""Unit tests for models.py module."""

import pytest
from dataclasses import dataclass
from typing import List

from models import (
    DataDogOperationType, DataCategory, DataDogFinding, 
    ProjectInfo, ScanResults
)


class TestDataDogOperationType:
    """Test DataDogOperationType enum."""
    
    def test_enum_values(self):
        """Test that all expected enum values exist."""
        expected_values = [
            "import", "initialisation", "rum_action", "rum_error", 
            "rum_timing", "log_info", "log_error", "log_warn", 
            "log_debug", "custom_attribute", "configuration"
        ]
        
        actual_values = [op.value for op in DataDogOperationType]
        
        for expected in expected_values:
            assert expected in actual_values
    
    def test_enum_uniqueness(self):
        """Test that all enum values are unique."""
        values = [op.value for op in DataDogOperationType]
        assert len(values) == len(set(values))


class TestDataCategory:
    """Test DataCategory enum."""
    
    def test_enum_values(self):
        """Test that all expected enum values exist."""
        expected_values = [
            "user_data", "system_data", "error_data", 
            "performance_data", "configuration_data", "unknown"
        ]
        
        actual_values = [cat.value for cat in DataCategory]
        
        for expected in expected_values:
            assert expected in actual_values
    
    def test_enum_uniqueness(self):
        """Test that all enum values are unique."""
        values = [cat.value for cat in DataCategory]
        assert len(values) == len(set(values))


class TestDataDogFinding:
    """Test DataDogFinding dataclass."""
    
    @pytest.fixture
    def sample_finding(self):
        """Create a sample DataDogFinding for testing."""
        return DataDogFinding(
            file_path="/test/file.ts",
            line_number=42,
            code_snippet="datadogRum.addAction('test')",
            operation_type=DataDogOperationType.RUM_ACTION,
            data_being_sent={"action_name": "test"},
            data_category=DataCategory.USER_DATA,
            context_lines=["// before", "datadogRum.addAction('test')", "// after"],
            github_url="https://github.com/test/repo/blob/main/file.ts#L42",
            project_name="test-project",
            extracted_parameters={"param1": "value1"}
        )
    
    def test_finding_creation(self, sample_finding):
        """Test DataDogFinding creation."""
        assert sample_finding.file_path == "/test/file.ts"
        assert sample_finding.line_number == 42
        assert sample_finding.operation_type == DataDogOperationType.RUM_ACTION
        assert sample_finding.data_category == DataCategory.USER_DATA
        assert sample_finding.project_name == "test-project"
    
    def test_to_dict(self, sample_finding):
        """Test to_dict method."""
        result = sample_finding.to_dict()
        
        assert isinstance(result, dict)
        assert result["file_path"] == "/test/file.ts"
        assert result["line_number"] == 42
        assert result["operation_type"] == "rum_action"
        assert result["data_category"] == "user_data"
        assert result["project_name"] == "test-project"
        assert result["data_being_sent"] == {"action_name": "test"}
        assert result["extracted_parameters"] == {"param1": "value1"}
    
    def test_to_dict_with_none_parameters(self):
        """Test to_dict with None extracted_parameters."""
        finding = DataDogFinding(
            file_path="/test/file.ts",
            line_number=42,
            code_snippet="import { datadogRum } from '@datadog/browser-rum'",
            operation_type=DataDogOperationType.IMPORT,
            data_being_sent={},
            data_category=DataCategory.CONFIGURATION_DATA,
            context_lines=["import { datadogRum } from '@datadog/browser-rum'"],
            github_url="https://github.com/test/repo/blob/main/file.ts#L42",
            project_name="test-project",
            extracted_parameters=None
        )
        
        result = finding.to_dict()
        assert result["extracted_parameters"] is None
    
    def test_required_fields(self):
        """Test that required fields are enforced."""
        # This will work because dataclasses don't enforce required fields at runtime
        # but we can test that all expected fields are present
        finding = DataDogFinding(
            file_path="/test/file.ts",
            line_number=42,
            code_snippet="test",
            operation_type=DataDogOperationType.IMPORT,
            data_being_sent={},
            data_category=DataCategory.UNKNOWN,
            context_lines=[],
            github_url="https://github.com/test",
            project_name="test"
        )
        
        assert hasattr(finding, 'file_path')
        assert hasattr(finding, 'line_number')
        assert hasattr(finding, 'code_snippet')
        assert hasattr(finding, 'operation_type')
        assert hasattr(finding, 'data_being_sent')
        assert hasattr(finding, 'data_category')
        assert hasattr(finding, 'context_lines')
        assert hasattr(finding, 'github_url')
        assert hasattr(finding, 'project_name')
        assert hasattr(finding, 'extracted_parameters')


class TestProjectInfo:
    """Test ProjectInfo dataclass."""
    
    @pytest.fixture
    def sample_project(self):
        """Create a sample ProjectInfo for testing."""
        return ProjectInfo(
            name="test-project",
            path="/path/to/project",
            project_type="react",
            github_url="https://github.com/test/repo",
            findings_count=5
        )
    
    def test_project_creation(self, sample_project):
        """Test ProjectInfo creation."""
        assert sample_project.name == "test-project"
        assert sample_project.path == "/path/to/project"
        assert sample_project.project_type == "react"
        assert sample_project.github_url == "https://github.com/test/repo"
        assert sample_project.findings_count == 5
    
    def test_to_dict(self, sample_project):
        """Test to_dict method."""
        result = sample_project.to_dict()
        
        assert isinstance(result, dict)
        assert result["name"] == "test-project"
        assert result["path"] == "/path/to/project"
        assert result["project_type"] == "react"
        assert result["github_url"] == "https://github.com/test/repo"
        assert result["findings_count"] == 5
    
    def test_default_findings_count(self):
        """Test default findings_count value."""
        project = ProjectInfo(
            name="test-project",
            path="/path/to/project",
            project_type="react",
            github_url="https://github.com/test/repo"
        )
        
        assert project.findings_count == 0


class TestScanResults:
    """Test ScanResults dataclass."""
    
    @pytest.fixture
    def sample_findings(self):
        """Create sample findings for testing."""
        return [
            DataDogFinding(
                file_path="/test/file1.ts",
                line_number=10,
                code_snippet="datadogRum.addAction('action1')",
                operation_type=DataDogOperationType.RUM_ACTION,
                data_being_sent={"action_name": "action1"},
                data_category=DataCategory.USER_DATA,
                context_lines=["datadogRum.addAction('action1')"],
                github_url="https://github.com/test/repo/blob/main/file1.ts#L10",
                project_name="project1"
            ),
            DataDogFinding(
                file_path="/test/file2.ts",
                line_number=20,
                code_snippet="datadogRum.addError(error)",
                operation_type=DataDogOperationType.RUM_ERROR,
                data_being_sent={"error_message": "test error"},
                data_category=DataCategory.ERROR_DATA,
                context_lines=["datadogRum.addError(error)"],
                github_url="https://github.com/test/repo/blob/main/file2.ts#L20",
                project_name="project2"
            ),
            DataDogFinding(
                file_path="/test/file3.ts",
                line_number=30,
                code_snippet="logger.info('test')",
                operation_type=DataDogOperationType.LOG_INFO,
                data_being_sent={"log_message": "test"},
                data_category=DataCategory.SYSTEM_DATA,
                context_lines=["logger.info('test')"],
                github_url="https://github.com/test/repo/blob/main/file3.ts#L30",
                project_name="project1"
            )
        ]
    
    @pytest.fixture
    def sample_projects(self):
        """Create sample projects for testing."""
        return [
            ProjectInfo(
                name="project1",
                path="/path/to/project1",
                project_type="react",
                github_url="https://github.com/test/project1",
                findings_count=2
            ),
            ProjectInfo(
                name="project2",
                path="/path/to/project2",
                project_type="unity",
                github_url="https://github.com/test/project2",
                findings_count=1
            )
        ]
    
    @pytest.fixture
    def sample_scan_results(self, sample_projects, sample_findings):
        """Create sample ScanResults for testing."""
        return ScanResults(
            projects=sample_projects,
            findings=sample_findings,
            total_files_scanned=100,
            scan_duration=5.5
        )
    
    def test_scan_results_creation(self, sample_scan_results):
        """Test ScanResults creation."""
        assert len(sample_scan_results.projects) == 2
        assert len(sample_scan_results.findings) == 3
        assert sample_scan_results.total_files_scanned == 100
        assert sample_scan_results.scan_duration == 5.5
    
    def test_to_dict(self, sample_scan_results):
        """Test to_dict method."""
        result = sample_scan_results.to_dict()
        
        assert isinstance(result, dict)
        assert "projects" in result
        assert "findings" in result
        assert "total_files_scanned" in result
        assert "scan_duration" in result
        
        assert len(result["projects"]) == 2
        assert len(result["findings"]) == 3
        assert result["total_files_scanned"] == 100
        assert result["scan_duration"] == 5.5
    
    def test_get_findings_by_project(self, sample_scan_results):
        """Test get_findings_by_project method."""
        project1_findings = sample_scan_results.get_findings_by_project("project1")
        project2_findings = sample_scan_results.get_findings_by_project("project2")
        nonexistent_findings = sample_scan_results.get_findings_by_project("nonexistent")
        
        assert len(project1_findings) == 2
        assert len(project2_findings) == 1
        assert len(nonexistent_findings) == 0
        
        # Check that findings belong to correct project
        for finding in project1_findings:
            assert finding.project_name == "project1"
        
        for finding in project2_findings:
            assert finding.project_name == "project2"
    
    def test_get_findings_by_category(self, sample_scan_results):
        """Test get_findings_by_category method."""
        user_data_findings = sample_scan_results.get_findings_by_category(DataCategory.USER_DATA)
        error_data_findings = sample_scan_results.get_findings_by_category(DataCategory.ERROR_DATA)
        system_data_findings = sample_scan_results.get_findings_by_category(DataCategory.SYSTEM_DATA)
        
        assert len(user_data_findings) == 1
        assert len(error_data_findings) == 1
        assert len(system_data_findings) == 1
        
        # Check that findings belong to correct category
        for finding in user_data_findings:
            assert finding.data_category == DataCategory.USER_DATA
        
        for finding in error_data_findings:
            assert finding.data_category == DataCategory.ERROR_DATA
        
        for finding in system_data_findings:
            assert finding.data_category == DataCategory.SYSTEM_DATA
    
    def test_get_findings_by_operation(self, sample_scan_results):
        """Test get_findings_by_operation method."""
        rum_action_findings = sample_scan_results.get_findings_by_operation(DataDogOperationType.RUM_ACTION)
        rum_error_findings = sample_scan_results.get_findings_by_operation(DataDogOperationType.RUM_ERROR)
        log_info_findings = sample_scan_results.get_findings_by_operation(DataDogOperationType.LOG_INFO)
        
        assert len(rum_action_findings) == 1
        assert len(rum_error_findings) == 1
        assert len(log_info_findings) == 1
        
        # Check that findings belong to correct operation
        for finding in rum_action_findings:
            assert finding.operation_type == DataDogOperationType.RUM_ACTION
        
        for finding in rum_error_findings:
            assert finding.operation_type == DataDogOperationType.RUM_ERROR
        
        for finding in log_info_findings:
            assert finding.operation_type == DataDogOperationType.LOG_INFO
    
    def test_empty_scan_results(self):
        """Test ScanResults with empty data."""
        empty_results = ScanResults(
            projects=[],
            findings=[],
            total_files_scanned=0,
            scan_duration=0.0
        )
        
        assert len(empty_results.projects) == 0
        assert len(empty_results.findings) == 0
        assert empty_results.get_findings_by_project("any") == []
        assert empty_results.get_findings_by_category(DataCategory.USER_DATA) == []
        assert empty_results.get_findings_by_operation(DataDogOperationType.RUM_ACTION) == []


if __name__ == "__main__":
    pytest.main([__file__])