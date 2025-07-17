"""Unit tests for datadog_detector.py module."""

import pytest
from unittest.mock import patch, MagicMock

from datadog_detector import DataDogDetector
from models import DataDogFinding, DataDogOperationType, DataCategory


class TestDataDogDetector:
    """Test DataDogDetector class."""
    
    @pytest.fixture
    def detector(self):
        """Create a DataDogDetector instance for testing."""
        return DataDogDetector(context_lines=3, detailed_extraction=False)
    
    @pytest.fixture
    def detailed_detector(self):
        """Create a DataDogDetector instance with detailed extraction."""
        return DataDogDetector(context_lines=3, detailed_extraction=True)
    
    def test_init(self, detector):
        """Test DataDogDetector initialisation."""
        assert detector.context_lines == 3
        assert detector.detailed_extraction == False
        assert hasattr(detector, 'patterns')
        assert 'imports' in detector.patterns
        assert 'rum_action' in detector.patterns
        assert 'log_info' in detector.patterns
    
    def test_detect_import_statements(self, detector):
        """Test detecting DataDog import statements."""
        test_cases = [
            "import { datadogRum } from '@datadog/browser-rum';",
            "import { datadogLogs } from '@datadog/browser-logs';",
            "import '@datadog/browser-rum-react';",
            "const { datadogRum } = require('@datadog/browser-rum');",
            "from '@datadog/browser-rum' import datadogRum",
        ]
        
        for code in test_cases:
            content = f"// Test file\n{code}\n// End"
            findings = detector.detect_datadog_usage(
                "/test/file.ts", content, "test-project", "https://github.com/test/repo"
            )
            
            assert len(findings) == 1
            assert findings[0].operation_type == DataDogOperationType.IMPORT
            assert findings[0].data_category == DataCategory.CONFIGURATION_DATA
            assert code.strip() in findings[0].code_snippet
    
    def test_detect_rum_actions(self, detector):
        """Test detecting RUM action calls."""
        test_cases = [
            "datadogRum.addAction('button-click', { userId: '123' });",
            "DD_RUM.addAction('page-view');",
            "datadogRum.addAction('form-submit', context);",
        ]
        
        for code in test_cases:
            content = f"// Test file\n{code}\n// End"
            findings = detector.detect_datadog_usage(
                "/test/file.ts", content, "test-project", "https://github.com/test/repo"
            )
            
            assert len(findings) == 1
            assert findings[0].operation_type == DataDogOperationType.RUM_ACTION
            assert 'action_name' in findings[0].data_being_sent or 'parameters' in findings[0].data_being_sent
    
    def test_detect_rum_errors(self, detector):
        """Test detecting RUM error calls."""
        test_cases = [
            "datadogRum.addError(new Error('Test error'));",
            "DD_RUM.addError(error, { context: 'test' });",
            "datadogRum.addError('Error message');",
        ]
        
        for code in test_cases:
            content = f"// Test file\n{code}\n// End"
            findings = detector.detect_datadog_usage(
                "/test/file.ts", content, "test-project", "https://github.com/test/repo"
            )
            
            assert len(findings) == 1
            assert findings[0].operation_type == DataDogOperationType.RUM_ERROR
            assert findings[0].data_category == DataCategory.ERROR_DATA
    
    def test_detect_log_statements(self, detector):
        """Test detecting log statements."""
        test_cases = [
            ("logger.info('User logged in');", DataDogOperationType.LOG_INFO),
            ("logger.error('Database connection failed');", DataDogOperationType.LOG_ERROR),
            ("logger.warn('Deprecated API usage');", DataDogOperationType.LOG_WARN),
            ("logger.debug('Debug information');", DataDogOperationType.LOG_DEBUG),
            ("datadogLogs.logger.info('Application started');", DataDogOperationType.LOG_INFO),
        ]
        
        for code, expected_type in test_cases:
            content = f"// Test file\n{code}\n// End"
            findings = detector.detect_datadog_usage(
                "/test/file.ts", content, "test-project", "https://github.com/test/repo"
            )
            
            assert len(findings) == 1
            assert findings[0].operation_type == expected_type
            assert 'log_message' in findings[0].data_being_sent or 'parameters' in findings[0].data_being_sent
    
    def test_detect_initialisation(self, detector):
        """Test detecting DataDog initialisation calls."""
        test_cases = [
            """datadogRum.init({
                applicationId: 'abc123',
                clientToken: 'def456',
                site: 'datadoghq.com'
            });""",
            "datadogLogs.createLogger({ name: 'test-logger' });",
            "DD_RUM.init({ applicationId: 'test-app' });",
        ]
        
        for code in test_cases:
            content = f"// Test file\n{code}\n// End"
            findings = detector.detect_datadog_usage(
                "/test/file.ts", content, "test-project", "https://github.com/test/repo"
            )
            
            assert len(findings) >= 1  # May match multiple lines for multiline code
            init_finding = next(f for f in findings if f.operation_type == DataDogOperationType.INIT)
            assert init_finding.data_category == DataCategory.CONFIGURATION_DATA
    
    def test_context_lines_extraction(self, detector):
        """Test context lines extraction."""
        content = """// Line 1
// Line 2
// Line 3
datadogRum.addAction('test');
// Line 5
// Line 6
// Line 7"""
        
        findings = detector.detect_datadog_usage(
            "/test/file.ts", content, "test-project", "https://github.com/test/repo"
        )
        
        assert len(findings) == 1
        finding = findings[0]
        
        # Should include 3 lines before, the target line, and 3 lines after
        assert len(finding.context_lines) == 7
        assert "// Line 1" in finding.context_lines
        assert "datadogRum.addAction('test');" in finding.context_lines
        assert "// Line 7" in finding.context_lines
    
    def test_data_categorisation_user_actions(self, detector):
        """Test data categorisation for user actions."""
        user_action_cases = [
            "datadogRum.addAction('button-click');",
            "datadogRum.addAction('user-tap');",
            "datadogRum.addAction('form-submit');",
            "datadogRum.addAction('scroll-event');",
        ]
        
        for code in user_action_cases:
            content = f"// Test file\n{code}\n// End"
            findings = detector.detect_datadog_usage(
                "/test/file.ts", content, "test-project", "https://github.com/test/repo"
            )
            
            assert len(findings) == 1
            assert findings[0].data_category == DataCategory.USER_DATA
    
    def test_data_categorisation_system_actions(self, detector):
        """Test data categorisation for system actions."""
        system_action_cases = [
            "datadogRum.addAction('api-call');",
            "datadogRum.addAction('system-startup');",
            "datadogRum.addAction('background-process');",
        ]
        
        for code in system_action_cases:
            content = f"// Test file\n{code}\n// End"
            findings = detector.detect_datadog_usage(
                "/test/file.ts", content, "test-project", "https://github.com/test/repo"
            )
            
            assert len(findings) == 1
            assert findings[0].data_category == DataCategory.SYSTEM_DATA
    
    def test_detailed_parameter_extraction(self, detailed_detector):
        """Test detailed parameter extraction."""
        code = "datadogRum.addAction('test-action', { userId: '123', sessionId: 'abc' });"
        content = f"// Test file\n{code}\n// End"
        
        findings = detailed_detector.detect_datadog_usage(
            "/test/file.ts", content, "test-project", "https://github.com/test/repo"
        )
        
        assert len(findings) == 1
        finding = findings[0]
        
        assert finding.extracted_parameters is not None
        assert len(finding.extracted_parameters) > 0
    
    def test_detailed_parameter_extraction_disabled(self, detector):
        """Test that detailed parameter extraction is disabled by default."""
        code = "datadogRum.addAction('test-action', { userId: '123' });"
        content = f"// Test file\n{code}\n// End"
        
        findings = detector.detect_datadog_usage(
            "/test/file.ts", content, "test-project", "https://github.com/test/repo"
        )
        
        assert len(findings) == 1
        finding = findings[0]
        
        assert finding.extracted_parameters is None
    
    def test_extract_data_from_import(self, detector):
        """Test data extraction from import statements."""
        code = "import { datadogRum, datadogLogs } from '@datadog/browser-rum';"
        
        data = detector._extract_data_from_line(code, 'imports')
        
        assert 'imported_items' in data
        assert 'package' in data
        assert data['package'] == '@datadog/browser-rum'
    
    def test_extract_data_from_init(self, detector):
        """Test data extraction from initialisation calls."""
        code = "datadogRum.init({ applicationId: 'abc123', clientToken: 'def456', site: 'datadoghq.com' });"
        
        data = detector._extract_data_from_line(code, 'init')
        
        assert 'configuration' in data
        assert 'application_id' in data
        assert 'client_token' in data
        assert 'site' in data
        assert data['application_id'] == 'abc123'
        assert data['client_token'].endswith('...')  # Should be truncated
        assert data['site'] == 'datadoghq.com'
    
    def test_extract_data_from_rum_action(self, detector):
        """Test data extraction from RUM action calls."""
        code = "datadogRum.addAction('button-click', { userId: '123' });"
        
        data = detector._extract_data_from_line(code, 'rum_action')
        
        assert 'parameters' in data
        assert 'action_name' in data
        assert data['action_name'] == 'button-click'
    
    def test_extract_data_from_log(self, detector):
        """Test data extraction from log calls."""
        code = "logger.info('User logged in successfully');"
        
        data = detector._extract_data_from_line(code, 'log_info')
        
        assert 'parameters' in data
        assert 'log_message' in data
        assert data['log_message'] == 'User logged in successfully'
    
    def test_is_datadog_related_file(self, detector):
        """Test file filtering logic."""
        # Should scan these files
        valid_files = [
            "/path/to/app.js",
            "/path/to/component.jsx",
            "/path/to/service.ts",
            "/path/to/utils.tsx",
            "/path/to/datadog-config.js",
            "/path/to/analytics.ts",
        ]
        
        for file_path in valid_files:
            assert detector.is_datadog_related_file(file_path) == True
        
        # Should not scan these files
        invalid_files = [
            "/path/to/styles.css",
            "/path/to/image.png",
            "/path/to/data.json",
            "/path/to/readme.md",
        ]
        
        for file_path in invalid_files:
            assert detector.is_datadog_related_file(file_path) == False
    
    def test_get_statistics(self, detector):
        """Test statistics generation."""
        # Create mock findings
        findings = [
            DataDogFinding(
                file_path="/test/file1.ts",
                line_number=10,
                code_snippet="datadogRum.addAction('test1')",
                operation_type=DataDogOperationType.RUM_ACTION,
                data_being_sent={},
                data_category=DataCategory.USER_DATA,
                context_lines=[],
                github_url="https://github.com/test/repo",
                project_name="project1"
            ),
            DataDogFinding(
                file_path="/test/file2.ts",
                line_number=20,
                code_snippet="logger.error('test error')",
                operation_type=DataDogOperationType.LOG_ERROR,
                data_being_sent={},
                data_category=DataCategory.ERROR_DATA,
                context_lines=[],
                github_url="https://github.com/test/repo",
                project_name="project1"
            ),
            DataDogFinding(
                file_path="/test/file3.ts",
                line_number=30,
                code_snippet="datadogRum.addAction('test2')",
                operation_type=DataDogOperationType.RUM_ACTION,
                data_being_sent={},
                data_category=DataCategory.USER_DATA,
                context_lines=[],
                github_url="https://github.com/test/repo",
                project_name="project2"
            ),
        ]
        
        stats = detector.get_statistics(findings)
        
        assert stats['total_findings'] == 3
        assert stats['by_operation_type']['rum_action'] == 2
        assert stats['by_operation_type']['log_error'] == 1
        assert stats['by_data_category']['user_data'] == 2
        assert stats['by_data_category']['error_data'] == 1
        assert stats['by_project']['project1'] == 2
        assert stats['by_project']['project2'] == 1
        assert stats['files_with_datadog'] == 3
    
    def test_multiple_matches_same_line(self, detector):
        """Test handling multiple matches on the same line."""
        code = "datadogRum.addAction('test'); logger.info('test');"
        content = f"// Test file\n{code}\n// End"
        
        findings = detector.detect_datadog_usage(
            "/test/file.ts", content, "test-project", "https://github.com/test/repo"
        )
        
        # Should find both matches
        assert len(findings) == 2
        
        operation_types = [f.operation_type for f in findings]
        assert DataDogOperationType.RUM_ACTION in operation_types
        assert DataDogOperationType.LOG_INFO in operation_types
    
    def test_case_insensitive_matching(self, detector):
        """Test case insensitive pattern matching."""
        test_cases = [
            "DATADOGRUM.addAction('test');",
            "DatadogRum.addAction('test');",
            "datadogrum.addaction('test');",
        ]
        
        for code in test_cases:
            content = f"// Test file\n{code}\n// End"
            findings = detector.detect_datadog_usage(
                "/test/file.ts", content, "test-project", "https://github.com/test/repo"
            )
            
            assert len(findings) == 1
            assert findings[0].operation_type == DataDogOperationType.RUM_ACTION
    
    def test_empty_file_content(self, detector):
        """Test handling empty file content."""
        findings = detector.detect_datadog_usage(
            "/test/empty.ts", "", "test-project", "https://github.com/test/repo"
        )
        
        assert len(findings) == 0
    
    def test_file_with_no_matches(self, detector):
        """Test handling file with no DataDog usage."""
        content = """// This is a regular file
function add(a, b) {
    return a + b;
}

const result = add(1, 2);
console.log(result);
"""
        
        findings = detector.detect_datadog_usage(
            "/test/regular.ts", content, "test-project", "https://github.com/test/repo"
        )
        
        assert len(findings) == 0
    
    def test_multiline_code_detection(self, detector):
        """Test detection of multiline DataDog code."""
        content = """// Test file
datadogRum.init({
    applicationId: 'abc123',
    clientToken: 'def456',
    site: 'datadoghq.com'
});
// End"""
        
        findings = detector.detect_datadog_usage(
            "/test/file.ts", content, "test-project", "https://github.com/test/repo"
        )
        
        # Should find the init call
        assert len(findings) >= 1
        init_finding = next(f for f in findings if f.operation_type == DataDogOperationType.INIT)
        assert init_finding is not None


if __name__ == "__main__":
    pytest.main([__file__])