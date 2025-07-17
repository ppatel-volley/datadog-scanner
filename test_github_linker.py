"""Unit tests for github_linker.py module."""

import pytest
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

from github_linker import GitHubLinker


class TestGitHubLinker:
    """Test GitHubLinker class."""
    
    @pytest.fixture
    def linker(self):
        """Create a GitHubLinker instance for testing."""
        return GitHubLinker(
            base_url="https://github.com/Volley-Inc",
            default_branch="main"
        )
    
    def test_init(self, linker):
        """Test GitHubLinker initialisation."""
        assert linker.base_url == "https://github.com/Volley-Inc"
        assert linker.default_branch == "main"
        assert linker._branch_cache == {}
    
    def test_get_project_name_from_path(self, linker):
        """Test extracting project name from file path."""
        # Test with relative path
        project_name = linker.get_project_name_from_path(
            "/Users/pratik/dev/ccm/cocomelon-mobile/src/app.ts",
            "/Users/pratik/dev/ccm"
        )
        assert project_name == "cocomelon-mobile"
        
        # Test with different structure
        project_name = linker.get_project_name_from_path(
            "/Users/pratik/dev/ccm/cocomelon-unity/Assets/Scripts/test.cs",
            "/Users/pratik/dev/ccm"
        )
        assert project_name == "cocomelon-unity"
    
    def test_get_project_name_from_path_invalid(self, linker):
        """Test extracting project name from invalid path."""
        project_name = linker.get_project_name_from_path(
            "/completely/different/path/file.ts",
            "/Users/pratik/dev/ccm"
        )
        assert project_name in ["completely", "different", "path"]  # Fallback behavior
    
    @patch('subprocess.run')
    def test_get_branch_for_project_current_branch(self, mock_run, linker):
        """Test getting current branch for a project."""
        # Mock successful git command
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="feature-branch\n"
        )
        
        branch = linker.get_branch_for_project("/path/to/project")
        
        assert branch == "feature-branch"
        assert linker._branch_cache["/path/to/project"] == "feature-branch"
        
        # Verify git command was called correctly
        mock_run.assert_called_with(
            ['git', 'branch', '--show-current'],
            cwd="/path/to/project",
            capture_output=True,
            text=True,
            timeout=5
        )
    
    @patch('subprocess.run')
    def test_get_branch_for_project_cached(self, mock_run, linker):
        """Test getting branch from cache."""
        # Set up cache
        linker._branch_cache["/path/to/project"] = "cached-branch"
        
        branch = linker.get_branch_for_project("/path/to/project")
        
        assert branch == "cached-branch"
        # Should not call git command
        mock_run.assert_not_called()
    
    @patch('subprocess.run')
    def test_get_branch_for_project_fallback_to_remote(self, mock_run, linker):
        """Test falling back to remote branch when current branch fails."""
        # Mock first command failure, second command success
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout=""),  # git branch --show-current fails
            MagicMock(returncode=0, stdout="refs/remotes/origin/develop\n")  # git symbolic-ref succeeds
        ]
        
        branch = linker.get_branch_for_project("/path/to/project")
        
        assert branch == "develop"
        assert linker._branch_cache["/path/to/project"] == "develop"
    
    @patch('subprocess.run')
    def test_get_branch_for_project_fallback_to_default(self, mock_run, linker):
        """Test falling back to default branch when all git commands fail."""
        # Mock all git commands failing
        mock_run.side_effect = [
            MagicMock(returncode=1, stdout=""),  # git branch --show-current fails
            MagicMock(returncode=1, stdout="")   # git symbolic-ref fails
        ]
        
        branch = linker.get_branch_for_project("/path/to/project")
        
        assert branch == "main"  # Default branch
        assert linker._branch_cache["/path/to/project"] == "main"
    
    @patch('subprocess.run')
    def test_get_branch_for_project_timeout(self, mock_run, linker):
        """Test handling subprocess timeout."""
        # Mock timeout exception
        mock_run.side_effect = subprocess.TimeoutExpired(['git'], 5)
        
        branch = linker.get_branch_for_project("/path/to/project")
        
        assert branch == "main"  # Should fallback to default
    
    @patch('subprocess.run')
    def test_get_branch_for_project_subprocess_error(self, mock_run, linker):
        """Test handling subprocess error."""
        # Mock subprocess error
        mock_run.side_effect = subprocess.SubprocessError("Git not found")
        
        branch = linker.get_branch_for_project("/path/to/project")
        
        assert branch == "main"  # Should fallback to default
    
    @patch('subprocess.run')
    def test_get_branch_for_project_file_not_found(self, mock_run, linker):
        """Test handling FileNotFoundError."""
        # Mock file not found error
        mock_run.side_effect = FileNotFoundError("git command not found")
        
        branch = linker.get_branch_for_project("/path/to/project")
        
        assert branch == "main"  # Should fallback to default
    
    def test_generate_file_url(self, linker):
        """Test generating GitHub URL for a file."""
        url = linker.generate_file_url(
            "/Users/pratik/dev/ccm/cocomelon-mobile/src/app.ts",
            42,
            "/Users/pratik/dev/ccm"
        )
        
        expected = "https://github.com/Volley-Inc/cocomelon-mobile/blob/main/src/app.ts#L42"
        assert url == expected
    
    @patch('subprocess.run')
    def test_generate_file_url_with_project_path(self, mock_run, linker):
        """Test generating GitHub URL with project path for branch detection."""
        # Mock git command to return specific branch
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="feature-branch\n"
        )
        
        url = linker.generate_file_url(
            "/Users/pratik/dev/ccm/cocomelon-mobile/src/app.ts",
            42,
            "/Users/pratik/dev/ccm",
            "/Users/pratik/dev/ccm/cocomelon-mobile"
        )
        
        expected = "https://github.com/Volley-Inc/cocomelon-mobile/blob/feature-branch/src/app.ts#L42"
        assert url == expected
    
    def test_generate_file_url_no_line_number(self, linker):
        """Test generating GitHub URL without line number."""
        url = linker.generate_file_url(
            "/Users/pratik/dev/ccm/cocomelon-mobile/src/app.ts",
            0,
            "/Users/pratik/dev/ccm"
        )
        
        expected = "https://github.com/Volley-Inc/cocomelon-mobile/blob/main/src/app.ts"
        assert url == expected
    
    def test_generate_file_url_invalid_path(self, linker):
        """Test generating GitHub URL with invalid path."""
        url = linker.generate_file_url(
            "/completely/different/path/file.ts",
            42,
            "/Users/pratik/dev/ccm"
        )
        
        # Should still generate a URL, even if path is invalid
        assert "https://github.com/Volley-Inc/" in url
        assert "#L42" in url
    
    def test_generate_project_url(self, linker):
        """Test generating project URL."""
        url = linker.generate_project_url("cocomelon-mobile")
        
        expected = "https://github.com/Volley-Inc/cocomelon-mobile"
        assert url == expected
    
    def test_validate_github_url_valid(self, linker):
        """Test validating valid GitHub URLs."""
        valid_urls = [
            "https://github.com/Volley-Inc/cocomelon-mobile",
            "http://github.com/user/repo",
            "https://github.com/org/repo/blob/main/file.ts#L42"
        ]
        
        for url in valid_urls:
            assert linker.validate_github_url(url) == True
    
    def test_validate_github_url_invalid(self, linker):
        """Test validating invalid GitHub URLs."""
        invalid_urls = [
            "not-a-url",
            "https://gitlab.com/user/repo",
            "ftp://github.com/user/repo",
            ""
        ]
        
        for url in invalid_urls:
            assert linker.validate_github_url(url) == False
    
    @patch('subprocess.run')
    def test_get_repository_info(self, mock_run, linker):
        """Test getting repository information."""
        # Mock git commands
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="feature-branch\n"),  # branch
            MagicMock(returncode=0, stdout="https://github.com/Volley-Inc/test-repo.git\n"),  # remote
            MagicMock(returncode=0, stdout="abcdef1234567890abcdef1234567890abcdef12\n")  # commit
        ]
        
        info = linker.get_repository_info("/path/to/project")
        
        assert info['branch'] == "feature-branch"
        assert info['remote_url'] == "https://github.com/Volley-Inc/test-repo.git"
        assert info['commit_hash'] == "abcdef1"  # Should be truncated to 7 chars
    
    @patch('subprocess.run')
    def test_get_repository_info_partial_failure(self, mock_run, linker):
        """Test getting repository information with partial command failures."""
        # Mock git commands with some failures
        mock_run.side_effect = [
            MagicMock(returncode=0, stdout="feature-branch\n"),  # branch succeeds
            MagicMock(returncode=1, stdout=""),  # remote fails
            MagicMock(returncode=0, stdout="abcdef1234567890abcdef1234567890abcdef12\n")  # commit succeeds
        ]
        
        info = linker.get_repository_info("/path/to/project")
        
        assert info['branch'] == "feature-branch"
        assert info['remote_url'] is None
        assert info['commit_hash'] == "abcdef1"
    
    @patch('subprocess.run')
    def test_get_repository_info_all_failures(self, mock_run, linker):
        """Test getting repository information with all command failures."""
        # Mock all git commands failing
        mock_run.side_effect = subprocess.SubprocessError("Git not available")
        
        info = linker.get_repository_info("/path/to/project")
        
        assert info['branch'] == "main"  # Should fallback to default
        assert info['remote_url'] is None
        assert info['commit_hash'] is None
    
    def test_custom_base_url(self):
        """Test GitHubLinker with custom base URL."""
        linker = GitHubLinker(
            base_url="https://github.com/custom-org",
            default_branch="develop"
        )
        
        assert linker.base_url == "https://github.com/custom-org"
        assert linker.default_branch == "develop"
        
        url = linker.generate_project_url("test-project")
        assert url == "https://github.com/custom-org/test-project"


if __name__ == "__main__":
    pytest.main([__file__])