"""Data models for DataDog findings."""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum


class DataDogOperationType(Enum):
    """Types of DataDog operations."""
    IMPORT = "import"
    INIT = "initialisation"
    RUM_ACTION = "rum_action"
    RUM_ERROR = "rum_error"
    RUM_TIMING = "rum_timing"
    LOG_INFO = "log_info"
    LOG_ERROR = "log_error"
    LOG_WARN = "log_warn"
    LOG_DEBUG = "log_debug"
    CUSTOM_ATTRIBUTE = "custom_attribute"
    CONFIGURATION = "configuration"
    METHOD_CALL = "method_call"


class DataCategory(Enum):
    """Categories of data being sent to DataDog."""
    USER_DATA = "user_data"
    SYSTEM_DATA = "system_data"
    ERROR_DATA = "error_data"
    PERFORMANCE_DATA = "performance_data"
    CONFIGURATION_DATA = "configuration_data"
    UNKNOWN = "unknown"


@dataclass
class DataDogFinding:
    """Represents a DataDog usage finding in code."""
    file_path: str
    line_number: int
    code_snippet: str
    operation_type: DataDogOperationType
    data_being_sent: Dict[str, Any]
    data_category: DataCategory
    context_lines: List[str]
    github_url: str
    project_name: str
    extracted_parameters: Optional[Dict[str, str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert finding to dictionary for JSON serialisation."""
        return {
            'file_path': self.file_path,
            'line_number': self.line_number,
            'code_snippet': self.code_snippet,
            'operation_type': self.operation_type.value,
            'data_being_sent': self.data_being_sent,
            'data_category': self.data_category.value,
            'context_lines': self.context_lines,
            'github_url': self.github_url,
            'project_name': self.project_name,
            'extracted_parameters': self.extracted_parameters
        }


@dataclass
class ProjectInfo:
    """Information about a scanned project."""
    name: str
    path: str
    project_type: str  # 'react', 'unity', 'nextjs', 'node'
    github_url: str
    findings_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert project info to dictionary."""
        return {
            'name': self.name,
            'path': self.path,
            'project_type': self.project_type,
            'github_url': self.github_url,
            'findings_count': self.findings_count
        }


@dataclass
class ScanResults:
    """Results of the DataDog scan."""
    projects: List[ProjectInfo]
    findings: List[DataDogFinding]
    total_files_scanned: int
    scan_duration: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert scan results to dictionary."""
        return {
            'projects': [p.to_dict() for p in self.projects],
            'findings': [f.to_dict() for f in self.findings],
            'total_files_scanned': self.total_files_scanned,
            'scan_duration': self.scan_duration
        }
    
    def get_findings_by_project(self, project_name: str) -> List[DataDogFinding]:
        """Get all findings for a specific project."""
        return [f for f in self.findings if f.project_name == project_name]
    
    def get_findings_by_category(self, category: DataCategory) -> List[DataDogFinding]:
        """Get all findings for a specific data category."""
        return [f for f in self.findings if f.data_category == category]
    
    def get_findings_by_operation(self, operation: DataDogOperationType) -> List[DataDogFinding]:
        """Get all findings for a specific operation type."""
        return [f for f in self.findings if f.operation_type == operation]