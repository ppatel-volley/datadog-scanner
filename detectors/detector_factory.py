"""Factory for creating appropriate DataDog detectors based on file types."""

from typing import List, Optional
from pathlib import Path

from .base_detector import BaseDataDogDetector
from .typescript_detector import TypeScriptDataDogDetector
from .csharp_detector import CSharpDataDogDetector


class DataDogDetectorFactory:
    """Factory class for creating appropriate DataDog detectors."""
    
    def __init__(self, context_lines: int = 3, detailed_extraction: bool = False):
        self.context_lines = context_lines
        self.detailed_extraction = detailed_extraction
        
        # Initialize all available detectors
        self.detectors = [
            TypeScriptDataDogDetector(context_lines, detailed_extraction),
            CSharpDataDogDetector(context_lines, detailed_extraction),
        ]
    
    def get_detector_for_file(self, file_path: str) -> Optional[BaseDataDogDetector]:
        """Get the appropriate detector for a given file."""
        for detector in self.detectors:
            if detector.can_handle_file(file_path):
                return detector
        return None
    
    def get_all_detectors(self) -> List[BaseDataDogDetector]:
        """Get all available detectors."""
        return self.detectors
    
    def get_supported_extensions(self) -> List[str]:
        """Get all supported file extensions across all detectors."""
        extensions = []
        for detector in self.detectors:
            extensions.extend(detector.get_supported_extensions())
        return list(set(extensions))  # Remove duplicates
    
    def get_detectors_by_language(self, language: str) -> List[BaseDataDogDetector]:
        """Get detectors for a specific language."""
        language_lower = language.lower()
        matching_detectors = []
        
        for detector in self.detectors:
            detector_language = detector.get_language_name().lower()
            if language_lower in detector_language or detector_language in language_lower:
                matching_detectors.append(detector)
        
        return matching_detectors
    
    def get_detector_info(self) -> List[dict]:
        """Get information about all available detectors."""
        info = []
        for detector in self.detectors:
            info.append({
                'language': detector.get_language_name(),
                'extensions': detector.get_supported_extensions(),
                'class_name': detector.__class__.__name__
            })
        return info