"""Code scanning functionality for DataDog usage detection."""

import os
import time
from pathlib import Path
from typing import List, Dict, Generator, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import fnmatch
import chardet

from models import DataDogFinding, ProjectInfo, ScanResults
from datadog_detector import DataDogDetector
from github_linker import GitHubLinker
from config import ConfigManager


class CodeScanner:
    """Scans code repositories for DataDog usage."""
    
    def __init__(self, config, github_linker: GitHubLinker):
        self.config = config
        self.github_linker = github_linker
        self.detector = DataDogDetector(
            context_lines=config.scan.context_lines,
            detailed_extraction=config.output.data_extraction_detailed
        )
        self.files_scanned = 0
        self.start_time = None
    
    def scan_directories(self, target_dirs: List[str]) -> ScanResults:
        """Scan multiple directories for DataDog usage."""
        self.start_time = time.time()
        self.files_scanned = 0
        
        # Discover projects
        projects = self._discover_projects(target_dirs)
        
        # Setup ignore patterns based on detected project types
        ConfigManager.setup_ignore_patterns(
            self.config.scan, 
            [{'type': p.project_type} for p in projects]
        )
        
        # Scan all projects
        all_findings = []
        
        for project in projects:
            print(f"Scanning project: {project.name} ({project.project_type})")
            
            project_findings = self._scan_project(project)
            all_findings.extend(project_findings)
            project.findings_count = len(project_findings)
            
            print(f"Found {len(project_findings)} DataDog usages in {project.name}")
        
        scan_duration = time.time() - self.start_time
        
        return ScanResults(
            projects=projects,
            findings=all_findings,
            total_files_scanned=self.files_scanned,
            scan_duration=scan_duration
        )
    
    def _discover_projects(self, target_dirs: List[str]) -> List[ProjectInfo]:
        """Discover projects in target directories."""
        projects = []
        
        for target_dir in target_dirs:
            target_path = Path(target_dir)
            
            if not target_path.exists():
                print(f"Warning: Directory {target_dir} does not exist")
                continue
            
            # Check if target_dir itself is a project
            if self._is_project_root(target_path):
                project_type = ConfigManager.detect_project_type(target_path)
                github_url = self.github_linker.generate_project_url(target_path.name)
                
                projects.append(ProjectInfo(
                    name=target_path.name,
                    path=str(target_path),
                    project_type=project_type,
                    github_url=github_url
                ))
            else:
                # Look for projects in subdirectories
                for item in target_path.iterdir():
                    if item.is_dir() and not item.name.startswith('.'):
                        if self._is_project_root(item):
                            project_type = ConfigManager.detect_project_type(item)
                            github_url = self.github_linker.generate_project_url(item.name)
                            
                            projects.append(ProjectInfo(
                                name=item.name,
                                path=str(item),
                                project_type=project_type,
                                github_url=github_url
                            ))
        
        return projects
    
    def _is_project_root(self, path: Path) -> bool:
        """Check if a directory is a project root."""
        # Check for common project indicators
        indicators = [
            'package.json',  # Node.js projects
            'Assets',        # Unity projects
            'ProjectSettings',  # Unity projects
            '*.csproj',      # C# projects
            'src',           # Common source directory
            'tsconfig.json', # TypeScript projects
            'next.config.js', # Next.js projects
        ]
        
        for indicator in indicators:
            if '*' in indicator:
                if list(path.glob(indicator)):
                    return True
            else:
                if (path / indicator).exists():
                    return True
        
        return False
    
    def _scan_project(self, project: ProjectInfo) -> List[DataDogFinding]:
        """Scan a single project for DataDog usage."""
        project_path = Path(project.path)
        findings = []
        
        # Get all files to scan
        files_to_scan = list(self._get_files_to_scan(project_path))
        
        # Use thread pool for parallel scanning
        max_workers = min(8, max(1, len(files_to_scan)))  # Ensure at least 1 worker
        
        # Skip threading if no files to scan
        if len(files_to_scan) == 0:
            return findings
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit file scanning tasks
            future_to_file = {
                executor.submit(self._scan_file, file_path, project): file_path
                for file_path in files_to_scan
            }
            
            # Collect results
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    file_findings = future.result()
                    findings.extend(file_findings)
                    self.files_scanned += 1
                except Exception as e:
                    print(f"Error scanning {file_path}: {e}")
        
        return findings
    
    def _get_files_to_scan(self, project_path: Path) -> Generator[Path, None, None]:
        """Get all files to scan in a project."""
        for file_path in project_path.rglob('*'):
            if not file_path.is_file():
                continue
            
            # Check file extension
            if file_path.suffix not in self.config.scan.file_extensions:
                continue
            
            # Check ignore patterns
            if self._should_ignore_file(file_path, project_path):
                continue
            
            # Check if file is likely to contain DataDog usage
            if not self.detector.is_datadog_related_file(str(file_path)):
                continue
            
            yield file_path
    
    def _should_ignore_file(self, file_path: Path, project_root: Path) -> bool:
        """Check if a file should be ignored based on patterns."""
        try:
            relative_path = file_path.relative_to(project_root)
            relative_path_str = str(relative_path)
            
            for pattern in self.config.scan.ignore_patterns:
                if fnmatch.fnmatch(relative_path_str, pattern):
                    return True
                
                # Also check directory patterns
                for part in relative_path.parts:
                    if fnmatch.fnmatch(part, pattern.rstrip('/**')):
                        return True
            
            return False
        except ValueError:
            # File is not relative to project root
            return True
    
    def _scan_file(self, file_path: Path, project: ProjectInfo) -> List[DataDogFinding]:
        """Scan a single file for DataDog usage."""
        try:
            # Read file content with encoding detection
            content = self._read_file_content(file_path)
            
            if not content:
                return []
            
            # Quick check for DataDog-related content
            if not self._has_datadog_content(content):
                return []
            
            # Generate GitHub URL for this file
            github_url = self.github_linker.generate_file_url(
                str(file_path), 
                1,  # Line number will be updated per finding
                str(Path(project.path).parent),  # Scan root
                project.path
            )
            
            # Extract base GitHub URL for the file (without line number)
            base_github_url = github_url.split('#')[0]
            
            # Detect DataDog usage
            findings = self.detector.detect_datadog_usage(
                str(file_path),
                content,
                project.name,
                base_github_url
            )
            
            # Update GitHub URLs with correct line numbers
            for finding in findings:
                finding.github_url = self.github_linker.generate_file_url(
                    str(file_path),
                    finding.line_number,
                    str(Path(project.path).parent),
                    project.path
                )
            
            return findings
            
        except Exception as e:
            print(f"Error scanning file {file_path}: {e}")
            return []
    
    def _read_file_content(self, file_path: Path) -> Optional[str]:
        """Read file content with encoding detection."""
        try:
            # Try UTF-8 first
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Detect encoding
            try:
                with open(file_path, 'rb') as f:
                    raw_data = f.read()
                    detected = chardet.detect(raw_data)
                    encoding = detected.get('encoding', 'utf-8')
                
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except:
                print(f"Warning: Could not read file {file_path}")
                return None
        except FileNotFoundError:
            print(f"Warning: File not found {file_path}")
            return None
        except Exception as e:
            print(f"Warning: Could not read file {file_path}: {e}")
            return None
    
    def _has_datadog_content(self, content: str) -> bool:
        """Quick check if content contains DataDog-related keywords."""
        datadog_keywords = [
            'datadog', 'DD_RUM', 'browser-rum', 'browser-logs',
            'addAction', 'addError', 'addTiming', 'datadogRum',
            'datadogLogs', 'logger.info', 'logger.error'
        ]
        
        content_lower = content.lower()
        return any(keyword.lower() in content_lower for keyword in datadog_keywords)
    
    def get_scan_progress(self) -> Dict[str, Any]:
        """Get current scan progress."""
        elapsed_time = time.time() - self.start_time if self.start_time else 0
        
        return {
            'files_scanned': self.files_scanned,
            'elapsed_time': elapsed_time,
            'files_per_second': self.files_scanned / elapsed_time if elapsed_time > 0 else 0
        }