#!/usr/bin/env python3
"""Test script to verify multi-language DataDog detection."""

import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from detectors.detector_factory import DataDogDetectorFactory

def test_typescript_detection():
    """Test TypeScript detection."""
    print("=== Testing TypeScript Detection ===")
    
    typescript_code = '''
import { datadogRum } from '@datadog/browser-rum';
import { datadogLogs } from '@datadog/browser-logs';

// Initialize DataDog
datadogRum.init({
    applicationId: 'xxx',
    clientToken: 'xxx'
});

// Track user action
datadogRum.addAction('button-click', { buttonId: 'submit' });

// Log info
datadogLogs.logger.info('User clicked submit', { userId: 123 });
'''
    
    factory = DataDogDetectorFactory()
    detector = factory.get_detector_for_file('test.ts')
    
    if detector:
        findings = detector.detect_datadog_usage(
            'test.ts', typescript_code, 'test-project', 'https://github.com/test/repo'
        )
        print(f"Found {len(findings)} TypeScript findings:")
        for finding in findings:
            print(f"  Line {finding.line_number}: {finding.operation_type.value} - {finding.code_snippet.strip()}")
    else:
        print("No TypeScript detector found!")
    
    print()

def test_csharp_detection():
    """Test C# detection."""
    print("=== Testing C# Detection ===")
    
    csharp_code = '''
using Datadog.Unity;
using Datadog.Unity.Rum;

public class TestClass 
{
    void Start() 
    {
        DatadogSdk.Instance.SetTrackingConsent(TrackingConsent.Granted);
        DatadogSdk.Instance.Rum.StartAction(RumUserActionType.Tap, "Button");
        
        var logger = DatadogSdk.Instance.CreateLogger(new DatadogLoggingOptions());
        logger.Info("Test message");
        logger.Error("Error occurred");
    }
}
'''
    
    factory = DataDogDetectorFactory()
    detector = factory.get_detector_for_file('Test.cs')
    
    if detector:
        findings = detector.detect_datadog_usage(
            'Test.cs', csharp_code, 'unity-project', 'https://github.com/test/unity'
        )
        print(f"Found {len(findings)} C# findings:")
        for finding in findings:
            print(f"  Line {finding.line_number}: {finding.operation_type.value} - {finding.code_snippet.strip()}")
    else:
        print("No C# detector found!")
    
    print()

def test_detector_info():
    """Test detector information."""
    print("=== Detector Information ===")
    
    factory = DataDogDetectorFactory()
    
    print("Supported extensions:", factory.get_supported_extensions())
    print("\nAvailable detectors:")
    for info in factory.get_detector_info():
        print(f"  {info['language']}: {info['extensions']} ({info['class_name']})")
    
    print()

if __name__ == "__main__":
    test_detector_info()
    test_typescript_detection() 
    test_csharp_detection()
    print("✅ Multi-language detection testing complete!")