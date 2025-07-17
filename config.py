"""Configuration management for DataDog analyser."""

import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class ScanConfig:
    """Configuration for scanning parameters."""
    target_directories: List[str] = field(default_factory=list)
    file_extensions: List[str] = field(default_factory=lambda: ['.ts', '.tsx', '.js', '.jsx', '.cs'])
    ignore_patterns: List[str] = field(default_factory=list)
    context_lines: int = 3
    
    
@dataclass
class GitHubConfig:
    """Configuration for GitHub integration."""
    base_url: str = "https://github.com/Volley-Inc"
    default_branch: str = "main"
    custom_path_mappings: Dict[str, str] = field(default_factory=dict)
    
    
@dataclass
class OutputConfig:
    """Configuration for output generation."""
    output_dir: str = "./reports"
    data_extraction_detailed: bool = False
    grouping_by: str = "project"  # project, data_type, operation
    

@dataclass
class AppConfig:
    """Main application configuration."""
    scan: ScanConfig = field(default_factory=ScanConfig)
    github: GitHubConfig = field(default_factory=GitHubConfig)
    output: OutputConfig = field(default_factory=OutputConfig)
    

class ConfigManager:
    """Manages application configuration."""
    
    # Default ignore patterns for different project types
    DEFAULT_IGNORE_PATTERNS = {
        'react': [
            'node_modules/**',
            'build/**',
            'dist/**',
            '.next/**',
            'coverage/**',
            '*.min.js',
            '*.bundle.js'
        ],
        'nextjs': [
            'node_modules/**',
            'build/**',
            'dist/**',
            '.next/**',
            'out/**',
            'coverage/**',
            '*.min.js',
            '*.bundle.js'
        ],
        'unity': [
            'Library/**',
            'Temp/**',
            'Build/**',
            'Builds/**',
            'obj/**',
            'bin/**',
            '*.meta'
        ],
        'node': [
            'node_modules/**',
            'build/**',
            'dist/**',
            'coverage/**',
            '*.min.js',
            '*.bundle.js'
        ]
    }
    
    @staticmethod
    def detect_project_type(project_path: Path) -> str:
        """Detect project type based on files present."""
        if (project_path / 'package.json').exists():
            # Check for Next.js
            package_json_path = project_path / 'package.json'
            try:
                with open(package_json_path, 'r', encoding='utf-8') as f:
                    package_data = json.load(f)
                    deps = {**package_data.get('dependencies', {}), 
                           **package_data.get('devDependencies', {})}
                    if 'next' in deps:
                        return 'nextjs'
                    elif 'react' in deps:
                        return 'react'
                    else:
                        return 'node'
            except (json.JSONDecodeError, FileNotFoundError):
                return 'node'
        
        # Check for Unity project
        if (project_path / 'Assets').exists() and (project_path / 'ProjectSettings').exists():
            return 'unity'
        
        # Check for .csproj files (C# projects)
        if list(project_path.glob('*.csproj')):
            return 'unity'
        
        return 'unknown'
    
    @staticmethod
    def get_ignore_patterns_for_project(project_type: str) -> List[str]:
        """Get default ignore patterns for a project type."""
        return ConfigManager.DEFAULT_IGNORE_PATTERNS.get(project_type, [])
    
    @staticmethod
    def load_config(config_path: Optional[str] = None) -> AppConfig:
        """Load configuration from file or return default."""
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                return AppConfig(**config_data)
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        
        return AppConfig()
    
    @staticmethod
    def save_config(config: AppConfig, config_path: str) -> None:
        """Save configuration to file."""
        config_dict = {
            'scan': config.scan.__dict__,
            'github': config.github.__dict__,
            'output': config.output.__dict__
        }
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2)
    
    @staticmethod
    def generate_github_url(project_name: str, base_url: str = "https://github.com/Volley-Inc") -> str:
        """Generate GitHub URL for a project."""
        return f"{base_url}/{project_name}"
    
    @staticmethod
    def setup_ignore_patterns(scan_config: ScanConfig, projects: List[Dict[str, str]]) -> None:
        """Setup ignore patterns based on detected project types."""
        all_patterns = set(scan_config.ignore_patterns)
        
        for project in projects:
            project_type = project.get('type', 'unknown')
            patterns = ConfigManager.get_ignore_patterns_for_project(project_type)
            all_patterns.update(patterns)
        
        scan_config.ignore_patterns = list(all_patterns)