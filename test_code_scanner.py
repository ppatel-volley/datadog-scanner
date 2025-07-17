"""Unit tests for code_scanner.py module."""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

from code_scanner import CodeScanner
from config import AppConfig, ScanConfig, GitHubConfig, OutputConfig
from github_linker import GitHubLinker
from models import ProjectInfo, ScanResults, DataDogFinding, DataDogOperationType, DataCategory


class TestCodeScanner:
    """Test CodeScanner class."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing."""
        config = AppConfig()
        config.scan = ScanConfig(
            target_directories=["/test/dir"],
            file_extensions=['.ts', '.tsx', '.js', '.jsx'],
            ignore_patterns=['node_modules/**', 'build/**'],
            context_lines=3
        )
        config.github = GitHubConfig(
            base_url="https://github.com/Volley-Inc",
            default_branch="main"
        )
        config.output = OutputConfig(
            output_dir="./reports",
            data_extraction_detailed=False
        )
        return config
    
    @pytest.fixture
    def mock_github_linker(self):
        """Create a mock GitHubLinker for testing."""
        linker = MagicMock(spec=GitHubLinker)
        linker.generate_project_url.return_value = "https://github.com/Volley-Inc/test-project"
        linker.generate_file_url.return_value = "https://github.com/Volley-Inc/test-project/blob/main/file.ts#L10"
        return linker
    
    @pytest.fixture
    def scanner(self, mock_config, mock_github_linker):
        """Create a CodeScanner instance for testing."""
        return CodeScanner(mock_config, mock_github_linker)
    
    def test_init(self, scanner, mock_config, mock_github_linker):
        """Test CodeScanner initialisation."""
        assert scanner.config == mock_config
        assert scanner.github_linker == mock_github_linker
        assert scanner.files_scanned == 0
        assert scanner.start_time is None
        assert hasattr(scanner, 'detector')
    
    def test_is_project_root_package_json(self, scanner):
        """Test project root detection with package.json."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create package.json
            (temp_path / "package.json").touch()
            
            assert scanner._is_project_root(temp_path) == True
    
    def test_is_project_root_unity(self, scanner):
        """Test project root detection with Unity structure."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create Unity project structure
            (temp_path / "Assets").mkdir()
            (temp_path / "ProjectSettings").mkdir()
            
            assert scanner._is_project_root(temp_path) == True
    
    def test_is_project_root_csproj(self, scanner):
        """Test project root detection with .csproj file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create .csproj file
            (temp_path / "TestProject.csproj").touch()
            
            assert scanner._is_project_root(temp_path) == True
    
    def test_is_project_root_src_directory(self, scanner):
        """Test project root detection with src directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create src directory
            (temp_path / "src").mkdir()
            
            assert scanner._is_project_root(temp_path) == True
    
    def test_is_project_root_not_project(self, scanner):
        """Test project root detection with non-project directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Empty directory
            assert scanner._is_project_root(temp_path) == False
    
    def test_should_ignore_file_node_modules(self, scanner):
        """Test file ignore logic for node_modules."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            project_root = temp_path / "project"
            project_root.mkdir()
            
            # Create file in node_modules
            node_modules = project_root / "node_modules" / "package"
            node_modules.mkdir(parents=True)
            test_file = node_modules / "test.js"
            test_file.touch()
            
            should_ignore = scanner._should_ignore_file(test_file, project_root)
            assert should_ignore == True
    
    def test_should_ignore_file_build_directory(self, scanner):
        """Test file ignore logic for build directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            project_root = temp_path / "project"
            project_root.mkdir()
            
            # Create file in build directory
            build_dir = project_root / "build"
            build_dir.mkdir()
            test_file = build_dir / "test.js"
            test_file.touch()
            
            should_ignore = scanner._should_ignore_file(test_file, project_root)
            assert should_ignore == True
    
    def test_should_ignore_file_valid_file(self, scanner):
        """Test file ignore logic for valid file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            project_root = temp_path / "project"
            project_root.mkdir()
            
            # Create file in src directory
            src_dir = project_root / "src"
            src_dir.mkdir()
            test_file = src_dir / "test.ts"
            test_file.touch()
            
            should_ignore = scanner._should_ignore_file(test_file, project_root)
            assert should_ignore == False
    
    def test_should_ignore_file_outside_project(self, scanner):
        """Test file ignore logic for file outside project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            project_root = temp_path / "project"
            project_root.mkdir()
            
            # Create file outside project
            outside_file = temp_path / "outside.ts"
            outside_file.touch()
            
            should_ignore = scanner._should_ignore_file(outside_file, project_root)
            assert should_ignore == True
    
    def test_read_file_content_utf8(self, scanner):
        """Test reading file content with UTF-8 encoding."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False, encoding='utf-8') as f:
            f.write("// Test content\nconsole.log('Hello');\n")
            file_path = f.name
        
        try:
            content = scanner._read_file_content(Path(file_path))
            
            assert content is not None
            assert "Test content" in content
            assert "console.log" in content
        finally:
            Path(file_path).unlink()
    
    def test_read_file_content_encoding_detection(self, scanner):
        """Test reading file content with encoding detection."""
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.ts', delete=False) as f:
            # Write content with UTF-8 encoding
            content = "// Test content\nconsole.log('Hello');\n"
            f.write(content.encode('utf-8'))
            file_path = f.name
        
        try:
            with patch('chardet.detect', return_value={'encoding': 'utf-8'}):
                result = scanner._read_file_content(Path(file_path))
                
                assert result is not None
                assert "Test content" in result
        finally:
            Path(file_path).unlink()
    
    def test_read_file_content_failure(self, scanner):
        """Test handling file read failure."""
        # Try to read non-existent file
        content = scanner._read_file_content(Path("/non/existent/file.ts"))
        assert content is None
    
    def test_has_datadog_content_positive(self, scanner):
        """Test detecting DataDog content in file."""
        content = """
        import { datadogRum } from '@datadog/browser-rum';
        
        function trackAction() {
            datadogRum.addAction('test-action');
        }
        """
        
        result = scanner._has_datadog_content(content)
        assert result == True
    
    def test_has_datadog_content_negative(self, scanner):
        """Test detecting no DataDog content in file."""
        content = """
        import React from 'react';
        
        function MyComponent() {
            return <div>Hello World</div>;
        }
        """
        
        result = scanner._has_datadog_content(content)
        assert result == False
    
    def test_has_datadog_content_case_insensitive(self, scanner):
        """Test case insensitive DataDog content detection."""
        content = """
        // Using DATADOG for analytics
        const tracker = new DATADOG.Tracker();
        """
        
        result = scanner._has_datadog_content(content)
        assert result == True
    
    @patch('code_scanner.CodeScanner._read_file_content')
    @patch('code_scanner.CodeScanner._has_datadog_content')
    def test_scan_file_with_datadog_content(self, mock_has_content, mock_read_content, scanner):
        """Test scanning file with DataDog content."""
        # Setup mocks
        mock_read_content.return_value = "datadogRum.addAction('test');"
        mock_has_content.return_value = True
        
        # Mock detector
        mock_finding = DataDogFinding(
            file_path="/test/file.ts",
            line_number=1,
            code_snippet="datadogRum.addAction('test');",
            operation_type=DataDogOperationType.RUM_ACTION,
            data_being_sent={},
            data_category=DataCategory.USER_DATA,
            context_lines=[],
            github_url="https://github.com/test/repo",
            project_name="test-project"
        )
        
        scanner.detector.detect_datadog_usage = MagicMock(return_value=[mock_finding])
        
        # Create project info
        project = ProjectInfo(
            name="test-project",
            path="/test/project",
            project_type="react",
            github_url="https://github.com/test/repo"
        )
        
        # Test scanning
        findings = scanner._scan_file(Path("/test/file.ts"), project)
        
        assert len(findings) == 1
        assert findings[0].operation_type == DataDogOperationType.RUM_ACTION
        
        # Verify mocks were called
        mock_read_content.assert_called_once()
        mock_has_content.assert_called_once()
        scanner.detector.detect_datadog_usage.assert_called_once()
    
    @patch('code_scanner.CodeScanner._read_file_content')
    def test_scan_file_read_failure(self, mock_read_content, scanner):
        """Test scanning file with read failure."""
        # Setup mock to return None (read failure)
        mock_read_content.return_value = None
        
        # Create project info
        project = ProjectInfo(
            name="test-project",
            path="/test/project",
            project_type="react",
            github_url="https://github.com/test/repo"
        )
        
        # Test scanning
        findings = scanner._scan_file(Path("/test/file.ts"), project)
        
        assert len(findings) == 0
    
    @patch('code_scanner.CodeScanner._read_file_content')
    @patch('code_scanner.CodeScanner._has_datadog_content')
    def test_scan_file_no_datadog_content(self, mock_has_content, mock_read_content, scanner):
        """Test scanning file with no DataDog content."""
        # Setup mocks
        mock_read_content.return_value = "console.log('hello');"
        mock_has_content.return_value = False
        
        # Create project info
        project = ProjectInfo(
            name="test-project",
            path="/test/project",
            project_type="react",
            github_url="https://github.com/test/repo"
        )
        
        # Test scanning
        findings = scanner._scan_file(Path("/test/file.ts"), project)
        
        assert len(findings) == 0
    
    def test_get_scan_progress_not_started(self, scanner):
        """Test scan progress when not started."""
        progress = scanner.get_scan_progress()
        
        assert progress['files_scanned'] == 0
        assert progress['elapsed_time'] == 0
        assert progress['files_per_second'] == 0
    
    def test_get_scan_progress_in_progress(self, scanner):
        """Test scan progress during scan."""
        import time
        
        scanner.start_time = time.time() - 10  # 10 seconds ago
        scanner.files_scanned = 50
        
        progress = scanner.get_scan_progress()
        
        assert progress['files_scanned'] == 50
        assert progress['elapsed_time'] > 0
        assert progress['files_per_second'] > 0
    
    @patch('code_scanner.CodeScanner._discover_projects')
    @patch('code_scanner.CodeScanner._scan_project')
    @patch('code_scanner.ConfigManager.setup_ignore_patterns')
    def test_scan_directories(self, mock_setup_patterns, mock_scan_project, mock_discover, scanner):
        """Test scanning directories."""
        # Setup mocks
        mock_projects = [
            ProjectInfo(
                name="project1",
                path="/test/project1",
                project_type="react",
                github_url="https://github.com/test/project1"
            ),
            ProjectInfo(
                name="project2",
                path="/test/project2",
                project_type="unity",
                github_url="https://github.com/test/project2"
            )
        ]
        
        mock_findings = [
            DataDogFinding(
                file_path="/test/file.ts",
                line_number=1,
                code_snippet="datadogRum.addAction('test');",
                operation_type=DataDogOperationType.RUM_ACTION,
                data_being_sent={},
                data_category=DataCategory.USER_DATA,
                context_lines=[],
                github_url="https://github.com/test/repo",
                project_name="project1"
            )
        ]
        
        mock_discover.return_value = mock_projects
        mock_scan_project.return_value = mock_findings
        
        # Test scanning
        results = scanner.scan_directories(["/test/dir"])
        
        assert isinstance(results, ScanResults)
        assert len(results.projects) == 2
        assert len(results.findings) == 2  # One finding per project
        assert results.total_files_scanned == 0  # Updated by scanner
        assert results.scan_duration > 0
        
        # Verify mocks were called
        mock_discover.assert_called_once_with(["/test/dir"])
        mock_setup_patterns.assert_called_once()
        assert mock_scan_project.call_count == 2
    
    @patch('code_scanner.CodeScanner._is_project_root')
    @patch('code_scanner.ConfigManager.detect_project_type')
    def test_discover_projects_single_project(self, mock_detect_type, mock_is_root, scanner):
        """Test discovering single project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Setup mocks
            mock_is_root.return_value = True
            mock_detect_type.return_value = "react"
            
            # Test discovery
            projects = scanner._discover_projects([str(temp_path)])
            
            assert len(projects) == 1
            assert projects[0].name == temp_path.name
            assert projects[0].project_type == "react"
            assert projects[0].path == str(temp_path)
    
    @patch('code_scanner.CodeScanner._is_project_root')
    @patch('code_scanner.ConfigManager.detect_project_type')
    def test_discover_projects_multiple_projects(self, mock_detect_type, mock_is_root, scanner):
        """Test discovering multiple projects in directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create subdirectories
            (temp_path / "project1").mkdir()
            (temp_path / "project2").mkdir()
            (temp_path / ".hidden").mkdir()  # Should be ignored
            
            # Setup mocks
            mock_is_root.side_effect = lambda path: path.name in ["project1", "project2"]
            mock_detect_type.return_value = "react"
            
            # Test discovery
            projects = scanner._discover_projects([str(temp_path)])
            
            assert len(projects) == 2
            project_names = [p.name for p in projects]
            assert "project1" in project_names
            assert "project2" in project_names
            assert ".hidden" not in project_names
    
    @patch('code_scanner.CodeScanner._is_project_root')
    def test_discover_projects_nonexistent_directory(self, mock_is_root, scanner):
        """Test discovering projects in nonexistent directory."""
        projects = scanner._discover_projects(["/nonexistent/directory"])
        
        assert len(projects) == 0
        mock_is_root.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__])