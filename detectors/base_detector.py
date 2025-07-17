"""Base detector interface for DataDog usage detection."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path

from models import DataDogFinding


class BaseDataDogDetector(ABC):
    """Abstract base class for DataDog usage detectors."""
    
    def __init__(self, context_lines: int = 3, detailed_extraction: bool = False):
        self.context_lines = context_lines
        self.detailed_extraction = detailed_extraction
        self._compile_patterns()
    
    @abstractmethod
    def _compile_patterns(self) -> None:
        """Compile language-specific regex patterns for DataDog detection."""
        pass
    
    @abstractmethod
    def get_supported_extensions(self) -> List[str]:
        """Return list of file extensions this detector supports."""
        pass
    
    @abstractmethod
    def get_language_name(self) -> str:
        """Return the name of the programming language this detector handles."""
        pass
    
    @abstractmethod
    def detect_datadog_usage(self, file_path: str, content: str, 
                           project_name: str, github_url: str) -> List[DataDogFinding]:
        """Detect DataDog usage in file content."""
        pass
    
    def can_handle_file(self, file_path: str) -> bool:
        """Check if this detector can handle the given file."""
        file_ext = Path(file_path).suffix.lower()
        return file_ext in self.get_supported_extensions()
    
    def _get_context_lines(self, all_lines: List[str], line_num: int) -> List[str]:
        """Extract context lines around the target line."""
        context_start = max(0, line_num - self.context_lines - 1)
        context_end = min(len(all_lines), line_num + self.context_lines)
        return all_lines[context_start:context_end]
    
    def _deduplicate_findings(self, findings: List[DataDogFinding]) -> List[DataDogFinding]:
        """Remove duplicate findings based on file_path and line_number only."""
        seen = set()
        deduplicated = []
        
        for finding in findings:
            # Create a unique key based on file and line only
            key = (finding.file_path, finding.line_number)
            
            if key not in seen:
                seen.add(key)
                # Prefer the finding with more detailed data (imported method detection)
                deduplicated.append(finding)
            else:
                # If we already have a finding for this line, check if the new one has better data
                existing_idx = None
                for i, existing in enumerate(deduplicated):
                    if (existing.file_path, existing.line_number) == key:
                        existing_idx = i
                        break
                
                if existing_idx is not None:
                    existing_finding = deduplicated[existing_idx]
                    # Prefer findings with more detailed data_being_sent
                    if (len(str(finding.data_being_sent)) > len(str(existing_finding.data_being_sent)) or
                        ('method_name' in finding.data_being_sent and 'method_name' not in existing_finding.data_being_sent)):
                        deduplicated[existing_idx] = finding
        
        return deduplicated