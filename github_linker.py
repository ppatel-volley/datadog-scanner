"""GitHub URL generation for file locations."""

import subprocess
from pathlib import Path
from typing import Optional
from urllib.parse import quote


class GitHubLinker:
    """Handles GitHub URL generation for file locations."""
    
    def __init__(self, base_url: str = "https://github.com/Volley-Inc", 
                 default_branch: str = "main"):
        self.base_url = base_url
        self.default_branch = default_branch
        self._branch_cache = {}
    
    def get_project_name_from_path(self, file_path: str, scan_root: str) -> str:
        """Extract project name from file path."""
        file_path_obj = Path(file_path)
        scan_root_obj = Path(scan_root)
        
        try:
            relative_path = file_path_obj.relative_to(scan_root_obj)
            return relative_path.parts[0]
        except ValueError:
            # If file_path is not relative to scan_root, try to extract from path
            return file_path_obj.parts[-3] if len(file_path_obj.parts) >= 3 else "unknown"
    
    def get_branch_for_project(self, project_path: str) -> str:
        """Get the current branch for a project."""
        if project_path in self._branch_cache:
            return self._branch_cache[project_path]
        
        try:
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                branch = result.stdout.strip()
                self._branch_cache[project_path] = branch
                return branch
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            pass
        
        # Try to get default branch from remote
        try:
            result = subprocess.run(
                ['git', 'symbolic-ref', 'refs/remotes/origin/HEAD'],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                branch = result.stdout.strip().split('/')[-1]
                self._branch_cache[project_path] = branch
                return branch
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            pass
        
        # Fallback to default branch
        self._branch_cache[project_path] = self.default_branch
        return self.default_branch
    
    def generate_file_url(self, file_path: str, line_number: int, 
                         scan_root: str, project_path: Optional[str] = None) -> str:
        """Generate GitHub URL for a specific file and line number."""
        project_name = self.get_project_name_from_path(file_path, scan_root)
        
        # Get relative path within the project
        file_path_obj = Path(file_path)
        scan_root_obj = Path(scan_root)
        
        try:
            relative_path = file_path_obj.relative_to(scan_root_obj)
            # Remove the project name from the path
            project_relative_path = Path(*relative_path.parts[1:])
        except ValueError:
            # Fallback: use the file path as-is
            project_relative_path = file_path_obj.name
        
        # Determine branch
        if project_path:
            branch = self.get_branch_for_project(project_path)
        else:
            branch = self.default_branch
        
        # Construct GitHub URL
        repo_url = f"{self.base_url}/{project_name}"
        file_url = f"{repo_url}/blob/{branch}/{project_relative_path}"
        
        # Add line number anchor
        if line_number > 0:
            file_url += f"#L{line_number}"
        
        return file_url
    
    def generate_project_url(self, project_name: str) -> str:
        """Generate GitHub URL for a project."""
        return f"{self.base_url}/{project_name}"
    
    def validate_github_url(self, url: str) -> bool:
        """Validate if a GitHub URL is properly formatted."""
        try:
            import urllib.request
            # Just check if URL is well-formed, don't actually fetch
            parsed = urllib.parse.urlparse(url)
            return (parsed.scheme in ['http', 'https'] and 
                   'github.com' in parsed.netloc)
        except:
            return False
    
    def get_repository_info(self, project_path: str) -> dict:
        """Get repository information from git."""
        info = {
            'branch': self.get_branch_for_project(project_path),
            'remote_url': None,
            'commit_hash': None
        }
        
        try:
            # Get remote URL
            result = subprocess.run(
                ['git', 'remote', 'get-url', 'origin'],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                info['remote_url'] = result.stdout.strip()
            
            # Get current commit hash
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                info['commit_hash'] = result.stdout.strip()[:7]  # Short hash
                
        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
            pass
        
        return info