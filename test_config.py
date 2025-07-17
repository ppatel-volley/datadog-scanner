"""Unit tests for config.py module."""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

from config import (
    ScanConfig, GitHubConfig, OutputConfig, AppConfig, ConfigManager
)


class TestScanConfig:
    """Test ScanConfig dataclass."""
    
    def test_default_values(self):
        """Test default values for ScanConfig."""
        config = ScanConfig()
        
        assert config.target_directories == []
        assert config.file_extensions == ['.ts', '.tsx', '.js', '.jsx']
        assert config.ignore_patterns == []
        assert config.context_lines == 3
    
    def test_custom_values(self):
        """Test ScanConfig with custom values."""
        config = ScanConfig(
            target_directories=['/test/dir'],
            file_extensions=['.py', '.js'],
            ignore_patterns=['*.test.js'],
            context_lines=5
        )
        
        assert config.target_directories == ['/test/dir']
        assert config.file_extensions == ['.py', '.js']
        assert config.ignore_patterns == ['*.test.js']
        assert config.context_lines == 5


class TestGitHubConfig:
    """Test GitHubConfig dataclass."""
    
    def test_default_values(self):
        """Test default values for GitHubConfig."""
        config = GitHubConfig()
        
        assert config.base_url == "https://github.com/Volley-Inc"
        assert config.default_branch == "main"
        assert config.custom_path_mappings == {}
    
    def test_custom_values(self):
        """Test GitHubConfig with custom values."""
        config = GitHubConfig(
            base_url="https://github.com/custom-org",
            default_branch="develop",
            custom_path_mappings={"old": "new"}
        )
        
        assert config.base_url == "https://github.com/custom-org"
        assert config.default_branch == "develop"
        assert config.custom_path_mappings == {"old": "new"}


class TestOutputConfig:
    """Test OutputConfig dataclass."""
    
    def test_default_values(self):
        """Test default values for OutputConfig."""
        config = OutputConfig()
        
        assert config.output_dir == "./reports"
        assert config.data_extraction_detailed == False
        assert config.grouping_by == "project"
    
    def test_custom_values(self):
        """Test OutputConfig with custom values."""
        config = OutputConfig(
            output_dir="./custom_reports",
            data_extraction_detailed=True,
            grouping_by="data_type"
        )
        
        assert config.output_dir == "./custom_reports"
        assert config.data_extraction_detailed == True
        assert config.grouping_by == "data_type"


class TestAppConfig:
    """Test AppConfig dataclass."""
    
    def test_default_values(self):
        """Test default values for AppConfig."""
        config = AppConfig()
        
        assert isinstance(config.scan, ScanConfig)
        assert isinstance(config.github, GitHubConfig)
        assert isinstance(config.output, OutputConfig)
    
    def test_custom_configs(self):
        """Test AppConfig with custom configurations."""
        scan_config = ScanConfig(context_lines=5)
        github_config = GitHubConfig(default_branch="develop")
        output_config = OutputConfig(data_extraction_detailed=True)
        
        config = AppConfig(
            scan=scan_config,
            github=github_config,
            output=output_config
        )
        
        assert config.scan.context_lines == 5
        assert config.github.default_branch == "develop"
        assert config.output.data_extraction_detailed == True


class TestConfigManager:
    """Test ConfigManager class."""
    
    def test_detect_project_type_react(self):
        """Test detecting React project type."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create package.json with React dependency
            package_json = {
                "name": "test-project",
                "dependencies": {
                    "react": "^18.0.0"
                }
            }
            
            with open(temp_path / "package.json", "w") as f:
                json.dump(package_json, f)
            
            project_type = ConfigManager.detect_project_type(temp_path)
            assert project_type == "react"
    
    def test_detect_project_type_nextjs(self):
        """Test detecting Next.js project type."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create package.json with Next.js dependency
            package_json = {
                "name": "test-project",
                "dependencies": {
                    "next": "^13.0.0",
                    "react": "^18.0.0"
                }
            }
            
            with open(temp_path / "package.json", "w") as f:
                json.dump(package_json, f)
            
            project_type = ConfigManager.detect_project_type(temp_path)
            assert project_type == "nextjs"
    
    def test_detect_project_type_node(self):
        """Test detecting Node.js project type."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create package.json without React/Next.js
            package_json = {
                "name": "test-project",
                "dependencies": {
                    "express": "^4.18.0"
                }
            }
            
            with open(temp_path / "package.json", "w") as f:
                json.dump(package_json, f)
            
            project_type = ConfigManager.detect_project_type(temp_path)
            assert project_type == "node"
    
    def test_detect_project_type_unity(self):
        """Test detecting Unity project type."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create Unity project structure
            (temp_path / "Assets").mkdir()
            (temp_path / "ProjectSettings").mkdir()
            
            project_type = ConfigManager.detect_project_type(temp_path)
            assert project_type == "unity"
    
    def test_detect_project_type_unity_csproj(self):
        """Test detecting Unity project type with .csproj file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create .csproj file
            (temp_path / "TestProject.csproj").touch()
            
            project_type = ConfigManager.detect_project_type(temp_path)
            assert project_type == "unity"
    
    def test_detect_project_type_unknown(self):
        """Test detecting unknown project type."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            project_type = ConfigManager.detect_project_type(temp_path)
            assert project_type == "unknown"
    
    def test_detect_project_type_invalid_package_json(self):
        """Test handling invalid package.json."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create invalid package.json
            with open(temp_path / "package.json", "w") as f:
                f.write("invalid json content")
            
            project_type = ConfigManager.detect_project_type(temp_path)
            assert project_type == "node"
    
    def test_get_ignore_patterns_for_project(self):
        """Test getting ignore patterns for different project types."""
        react_patterns = ConfigManager.get_ignore_patterns_for_project("react")
        unity_patterns = ConfigManager.get_ignore_patterns_for_project("unity")
        unknown_patterns = ConfigManager.get_ignore_patterns_for_project("unknown")
        
        assert "node_modules/**" in react_patterns
        assert "build/**" in react_patterns
        assert "Library/**" in unity_patterns
        assert "Temp/**" in unity_patterns
        assert unknown_patterns == []
    
    def test_load_config_default(self):
        """Test loading default configuration."""
        config = ConfigManager.load_config()
        
        assert isinstance(config, AppConfig)
        assert config.scan.context_lines == 3
        assert config.github.base_url == "https://github.com/Volley-Inc"
        assert config.output.output_dir == "./reports"
    
    def test_load_config_from_file(self):
        """Test loading configuration from file."""
        config_data = {
            "scan": {
                "context_lines": 5,
                "file_extensions": [".py", ".js"]
            },
            "github": {
                "base_url": "https://github.com/custom-org",
                "default_branch": "develop"
            },
            "output": {
                "output_dir": "./custom_reports",
                "data_extraction_detailed": True
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_path = f.name
        
        try:
            config = ConfigManager.load_config(config_path)
            
            assert config.scan.context_lines == 5
            assert config.scan.file_extensions == [".py", ".js"]
            assert config.github.base_url == "https://github.com/custom-org"
            assert config.github.default_branch == "develop"
            assert config.output.output_dir == "./custom_reports"
            assert config.output.data_extraction_detailed == True
        finally:
            Path(config_path).unlink()
    
    def test_load_config_invalid_file(self):
        """Test loading configuration from invalid file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("invalid json")
            config_path = f.name
        
        try:
            config = ConfigManager.load_config(config_path)
            
            # Should return default config
            assert isinstance(config, AppConfig)
            assert config.scan.context_lines == 3
        finally:
            Path(config_path).unlink()
    
    def test_load_config_nonexistent_file(self):
        """Test loading configuration from nonexistent file."""
        config = ConfigManager.load_config("/nonexistent/path.json")
        
        # Should return default config
        assert isinstance(config, AppConfig)
        assert config.scan.context_lines == 3
    
    def test_save_config(self):
        """Test saving configuration to file."""
        config = AppConfig()
        config.scan.context_lines = 5
        config.github.default_branch = "develop"
        config.output.data_extraction_detailed = True
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_path = f.name
        
        try:
            ConfigManager.save_config(config, config_path)
            
            # Read back and verify
            with open(config_path, 'r') as f:
                saved_data = json.load(f)
            
            assert saved_data['scan']['context_lines'] == 5
            assert saved_data['github']['default_branch'] == "develop"
            assert saved_data['output']['data_extraction_detailed'] == True
        finally:
            Path(config_path).unlink()
    
    def test_generate_github_url(self):
        """Test generating GitHub URL for a project."""
        url = ConfigManager.generate_github_url("test-project")
        assert url == "https://github.com/Volley-Inc/test-project"
        
        url = ConfigManager.generate_github_url("test-project", "https://github.com/custom-org")
        assert url == "https://github.com/custom-org/test-project"
    
    def test_setup_ignore_patterns(self):
        """Test setting up ignore patterns based on project types."""
        scan_config = ScanConfig(ignore_patterns=["custom-pattern"])
        projects = [
            {"type": "react"},
            {"type": "unity"},
            {"type": "unknown"}
        ]
        
        ConfigManager.setup_ignore_patterns(scan_config, projects)
        
        # Should include custom pattern plus patterns from detected project types
        assert "custom-pattern" in scan_config.ignore_patterns
        assert "node_modules/**" in scan_config.ignore_patterns  # from react
        assert "Library/**" in scan_config.ignore_patterns  # from unity
        
        # Should not have duplicates
        pattern_counts = {}
        for pattern in scan_config.ignore_patterns:
            pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        
        for pattern, count in pattern_counts.items():
            assert count == 1, f"Pattern '{pattern}' appears {count} times"


if __name__ == "__main__":
    pytest.main([__file__])