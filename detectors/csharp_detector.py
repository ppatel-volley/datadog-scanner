"""C# DataDog usage detection for Unity projects."""

import re
import json
from typing import List, Dict, Any, Optional

from models import DataDogFinding, DataDogOperationType, DataCategory
from .base_detector import BaseDataDogDetector


class CSharpDataDogDetector(BaseDataDogDetector):
    """Detects DataDog usage patterns in C# Unity files."""
    
    def get_supported_extensions(self) -> List[str]:
        """Return supported file extensions for C#."""
        return ['.cs']
    
    def get_language_name(self) -> str:
        """Return the language name."""
        return "C#"
    
    def _compile_patterns(self):
        """Compile regex patterns for C# Unity DataDog detection."""
        self.patterns = {
            # Using statements for DataDog
            'imports': [
                re.compile(r'using\s+Datadog\.Unity', re.IGNORECASE),
                re.compile(r'using\s+Datadog\.Unity\.Rum', re.IGNORECASE),
                re.compile(r'using\s+Datadog\.Unity\.Logs', re.IGNORECASE),
                re.compile(r'using\s+Datadog\.Unity\.Core', re.IGNORECASE),
            ],
            
            # SDK Initialization patterns
            'init': [
                re.compile(r'DatadogSdk\.InitWithPlatform\s*\(', re.IGNORECASE),
                re.compile(r'DatadogSdk\.Instance\.SetTrackingConsent\s*\(', re.IGNORECASE),
                re.compile(r'DatadogSdk\.Instance\.SetSdkVerbosity\s*\(', re.IGNORECASE),
            ],
            
            # RUM patterns
            'rum_action': [
                re.compile(r'DatadogSdk\.Instance\.Rum\.(?:Add|Start)Action\s*\(', re.IGNORECASE),
                re.compile(r'DatadogSdk\.Instance\.Rum\.StopAction\s*\(', re.IGNORECASE),
                re.compile(r'\.Rum\.(?:Add|Start)Action\s*\(', re.IGNORECASE),
                re.compile(r'\.Rum\.StopAction\s*\(', re.IGNORECASE),
            ],
            
            'rum_error': [
                re.compile(r'DatadogSdk\.Instance\.Rum\.AddError\s*\(', re.IGNORECASE),
                re.compile(r'\.Rum\.AddError\s*\(', re.IGNORECASE),
            ],
            
            'rum_timing': [
                re.compile(r'DatadogSdk\.Instance\.Rum\.AddTiming\s*\(', re.IGNORECASE),
                re.compile(r'\.Rum\.AddTiming\s*\(', re.IGNORECASE),
            ],
            
            'rum_view': [
                re.compile(r'DatadogSdk\.Instance\.Rum\.StartView\s*\(', re.IGNORECASE),
                re.compile(r'DatadogSdk\.Instance\.Rum\.StopView\s*\(', re.IGNORECASE),
                re.compile(r'\.Rum\.(?:Start|Stop)View\s*\(', re.IGNORECASE),
            ],
            
            'rum_attribute': [
                re.compile(r'DatadogSdk\.Instance\.Rum\.AddAttribute\s*\(', re.IGNORECASE),
                re.compile(r'DatadogSdk\.Instance\.Rum\.RemoveAttribute\s*\(', re.IGNORECASE),
                re.compile(r'\.Rum\.(?:Add|Remove)Attribute\s*\(', re.IGNORECASE),
            ],
            
            # Logging patterns
            'log_create': [
                re.compile(r'DatadogSdk\.Instance\.CreateLogger\s*\(', re.IGNORECASE),
                re.compile(r'\.CreateLogger\s*\(', re.IGNORECASE),
            ],
            
            'log_info': [
                re.compile(r'\.Log\s*\(\s*DdLogLevel\.Info', re.IGNORECASE),
                re.compile(r'\.Info\s*\(', re.IGNORECASE),
            ],
            
            'log_error': [
                re.compile(r'\.Log\s*\(\s*DdLogLevel\.Error', re.IGNORECASE),
                re.compile(r'\.Error\s*\(', re.IGNORECASE),
            ],
            
            'log_warn': [
                re.compile(r'\.Log\s*\(\s*DdLogLevel\.Warn', re.IGNORECASE),
                re.compile(r'\.Warn\s*\(', re.IGNORECASE),
            ],
            
            'log_debug': [
                re.compile(r'\.Log\s*\(\s*DdLogLevel\.Debug', re.IGNORECASE),
                re.compile(r'\.Debug\s*\(', re.IGNORECASE),
            ],
            
            # User and attribute management
            'user_info': [
                re.compile(r'DatadogSdk\.Instance\.SetUserInfo\s*\(', re.IGNORECASE),
                re.compile(r'DatadogSdk\.Instance\.AddUserExtraInfo\s*\(', re.IGNORECASE),
                re.compile(r'\.SetUserInfo\s*\(', re.IGNORECASE),
                re.compile(r'\.AddUserExtraInfo\s*\(', re.IGNORECASE),
            ],
            
            'global_attributes': [
                re.compile(r'DatadogSdk\.Instance\.AddLogsAttribute\s*\(', re.IGNORECASE),
                re.compile(r'DatadogSdk\.Instance\.AddLogsAttributes\s*\(', re.IGNORECASE),
                re.compile(r'DatadogSdk\.Instance\.RemoveLogsAttribute\s*\(', re.IGNORECASE),
                re.compile(r'\.(?:Add|Remove)LogsAttribute\s*\(', re.IGNORECASE),
            ],
            
            # Utilities
            'clear_data': [
                re.compile(r'DatadogSdk\.Instance\.ClearAllData\s*\(', re.IGNORECASE),
                re.compile(r'\.ClearAllData\s*\(', re.IGNORECASE),
            ],
        }
    
    def detect_datadog_usage(self, file_path: str, content: str, 
                           project_name: str, github_url: str) -> List[DataDogFinding]:
        """Detect DataDog usage in C# Unity file content."""
        findings = []
        lines = content.split('\n')
        
        # Track processed lines to avoid duplicates
        processed_lines = set()
        
        # First pass: Extract imported DataDog namespaces and types
        imported_types = self._extract_imported_types(content, file_path)
        
        # Second pass: Find all DataDog usage patterns
        for line_num, line in enumerate(lines, 1):
            line_key = f"{file_path}:{line_num}"
            
            # Check for direct DataDog patterns
            for pattern_type, patterns in self.patterns.items():
                for pattern in patterns:
                    if pattern.search(line):
                        finding = self._create_finding(
                            file_path, line_num, line, lines, pattern_type,
                            project_name, github_url
                        )
                        if finding:
                            findings.append(finding)
                            processed_lines.add(line_key)
            
            # Check for imported type usage (only if not already processed)
            if line_key not in processed_lines:
                for type_name in imported_types:
                    type_calls = self._find_type_usage(line, type_name, imported_types[type_name])
                    for call_info in type_calls:
                        finding = self._create_type_usage_finding(
                            file_path, line_num, line, lines, call_info,
                            project_name, github_url
                        )
                        if finding:
                            findings.append(finding)
                            processed_lines.add(line_key)
        
        # Deduplicate findings
        return self._deduplicate_findings(findings)
    
    def _extract_imported_types(self, content: str, file_path: str) -> Dict[str, Dict[str, str]]:
        """Extract imported DataDog types and namespaces from file content."""
        imported_types = {}
        
        # Match using statements
        using_patterns = [
            r'using\s+(Datadog\.Unity(?:\.[A-Za-z]+)*)\s*;',
        ]
        
        for pattern in using_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                namespace = match.group(1)
                
                # Extract the type name from the namespace
                type_name = namespace.split('.')[-1] if '.' in namespace else namespace
                
                imported_types[type_name] = {
                    'namespace': namespace,
                    'import_type': 'using'
                }
                
                # Also add common DataDog types
                if 'Rum' in namespace:
                    imported_types['RumUserActionType'] = {
                        'namespace': namespace,
                        'import_type': 'enum'
                    }
                    imported_types['IDdRum'] = {
                        'namespace': namespace,
                        'import_type': 'interface'
                    }
                
                if 'Logs' in namespace:
                    imported_types['DdLogLevel'] = {
                        'namespace': namespace,
                        'import_type': 'enum'
                    }
                    imported_types['DdLogger'] = {
                        'namespace': namespace,
                        'import_type': 'class'
                    }
        
        return imported_types
    
    def _find_type_usage(self, line: str, type_name: str, type_info: Dict[str, str]) -> List[Dict[str, Any]]:
        """Find usage of imported DataDog types in a line."""
        calls = []
        
        # Create patterns to find type usage
        patterns = [
            # Enum usage: RumUserActionType.Tap
            rf'\b{re.escape(type_name)}\.(\w+)',
            # Method calls on types: DatadogSdk.Instance.method()
            rf'\b{re.escape(type_name)}\.(\w+)\s*\(',
            # Variable declarations: DdLogger logger
            rf'\b{re.escape(type_name)}\s+(\w+)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, line, re.IGNORECASE)
            for match in matches:
                # Extract the member or method being accessed
                member_name = match.group(1) if match.groups() else ''
                
                # Extract the full usage context
                usage_context = self._extract_usage_context(line, match.start(), type_name)
                
                calls.append({
                    'type_name': type_name,
                    'member_name': member_name,
                    'namespace': type_info['namespace'],
                    'usage_context': usage_context,
                    'match_start': match.start(),
                    'match_end': match.end(),
                    'usage_type': self._determine_usage_type(line, match.start(), match.group(0))
                })
        
        return calls
    
    def _extract_usage_context(self, line: str, start_pos: int, type_name: str) -> str:
        """Extract the context around a type usage."""
        try:
            # For method calls, find the full method call including parameters
            if '(' in line[start_pos:start_pos+50]:
                paren_start = line.find('(', start_pos)
                if paren_start != -1:
                    # Find matching closing parenthesis
                    paren_count = 0
                    paren_end = paren_start
                    
                    for i in range(paren_start, len(line)):
                        if line[i] == '(':
                            paren_count += 1
                        elif line[i] == ')':
                            paren_count -= 1
                            if paren_count == 0:
                                paren_end = i
                                break
                    
                    # Extract from start of type to end of method call
                    context_start = max(0, start_pos - 10)
                    context_end = min(len(line), paren_end + 1)
                    return line[context_start:context_end].strip()
            
            # For non-method calls, extract a reasonable context
            context_start = max(0, start_pos - 10)
            context_end = min(len(line), start_pos + 50)
            return line[context_start:context_end].strip()
        except:
            return line.strip()
    
    def _determine_usage_type(self, line: str, start_pos: int, matched_text: str) -> str:
        """Determine the type of usage (method call, property access, etc.)."""
        line_after = line[start_pos + len(matched_text):start_pos + len(matched_text) + 10]
        line_before = line[max(0, start_pos - 10):start_pos]
        
        if '(' in line_after:
            return 'method_call'
        elif '.' in matched_text and not '(' in line_after:
            return 'property_access'
        elif any(keyword in line_before for keyword in ['new ', 'var ', 'public ', 'private ']):
            return 'declaration'
        elif '=' in line_before and line_before.strip().endswith('='):
            return 'assignment'
        else:
            return 'reference'
    
    def _create_finding(self, file_path: str, line_num: int, line: str, 
                       all_lines: List[str], pattern_type: str, 
                       project_name: str, github_url: str) -> Optional[DataDogFinding]:
        """Create a DataDog finding from a matched pattern."""
        # Get context lines
        context_lines = self._get_context_lines(all_lines, line_num)
        
        # Determine operation type
        operation_type = self._get_operation_type(pattern_type)
        
        # Extract data being sent
        data_being_sent = self._extract_data_from_line(line, pattern_type)
        
        # Categorise data
        data_category = self._categorise_data(data_being_sent, pattern_type)
        
        # Extract parameters if detailed extraction is enabled
        extracted_params = None
        if self.detailed_extraction:
            extracted_params = self._extract_detailed_parameters(line, pattern_type)
        
        return DataDogFinding(
            file_path=file_path,
            line_number=line_num,
            code_snippet=line.strip(),
            operation_type=operation_type,
            data_being_sent=data_being_sent,
            data_category=data_category,
            context_lines=context_lines,
            github_url=github_url,
            project_name=project_name,
            extracted_parameters=extracted_params
        )
    
    def _create_type_usage_finding(self, file_path: str, line_num: int, line: str, 
                                  all_lines: List[str], call_info: Dict[str, Any],
                                  project_name: str, github_url: str) -> Optional[DataDogFinding]:
        """Create a DataDog finding from a type usage."""
        # Get context lines
        context_lines = self._get_context_lines(all_lines, line_num)
        
        # Determine operation type based on type and member
        operation_type = self._get_type_operation_type(call_info['type_name'], call_info['member_name'])
        
        # Create data being sent structure
        data_being_sent = {
            'type_name': call_info['type_name'],
            'member_name': call_info['member_name'],
            'namespace': call_info['namespace'],
            'usage_context': call_info['usage_context'],
            'usage_type': call_info['usage_type']
        }
        
        # Extract parameters if available
        params = self._extract_parameters_from_usage(call_info['usage_context'])
        if params:
            data_being_sent['parameters'] = params
        
        # Categorise data
        data_category = self._categorise_type_usage(call_info['type_name'], call_info['member_name'])
        
        return DataDogFinding(
            file_path=file_path,
            line_number=line_num,
            code_snippet=line.strip(),
            operation_type=operation_type,
            data_being_sent=data_being_sent,
            data_category=data_category,
            context_lines=context_lines,
            github_url=github_url,
            project_name=project_name,
            extracted_parameters=None
        )
    
    def _get_operation_type(self, pattern_type: str) -> DataDogOperationType:
        """Map pattern type to operation type."""
        mapping = {
            'imports': DataDogOperationType.IMPORT,
            'init': DataDogOperationType.INIT,
            'rum_action': DataDogOperationType.RUM_ACTION,
            'rum_error': DataDogOperationType.RUM_ERROR,
            'rum_timing': DataDogOperationType.RUM_TIMING,
            'rum_view': DataDogOperationType.CUSTOM_ATTRIBUTE,  # Views are custom in Unity
            'rum_attribute': DataDogOperationType.CUSTOM_ATTRIBUTE,
            'log_create': DataDogOperationType.INIT,
            'log_info': DataDogOperationType.LOG_INFO,
            'log_error': DataDogOperationType.LOG_ERROR,
            'log_warn': DataDogOperationType.LOG_WARN,
            'log_debug': DataDogOperationType.LOG_DEBUG,
            'user_info': DataDogOperationType.CONFIGURATION,
            'global_attributes': DataDogOperationType.CUSTOM_ATTRIBUTE,
            'clear_data': DataDogOperationType.CONFIGURATION,
        }
        return mapping.get(pattern_type, DataDogOperationType.CUSTOM_ATTRIBUTE)
    
    def _get_type_operation_type(self, type_name: str, member_name: str) -> DataDogOperationType:
        """Get operation type for type usage."""
        type_lower = type_name.lower()
        member_lower = member_name.lower()
        
        # RUM-related operations
        if 'rum' in type_lower:
            if 'action' in member_lower:
                return DataDogOperationType.RUM_ACTION
            elif 'error' in member_lower:
                return DataDogOperationType.RUM_ERROR
            elif 'timing' in member_lower:
                return DataDogOperationType.RUM_TIMING
            elif 'view' in member_lower:
                return DataDogOperationType.CUSTOM_ATTRIBUTE
            elif 'attribute' in member_lower:
                return DataDogOperationType.CUSTOM_ATTRIBUTE
            else:
                return DataDogOperationType.CUSTOM_ATTRIBUTE
        
        # Logging operations
        elif 'log' in type_lower or 'logger' in type_lower:
            if 'error' in member_lower:
                return DataDogOperationType.LOG_ERROR
            elif 'warn' in member_lower:
                return DataDogOperationType.LOG_WARN
            elif 'debug' in member_lower:
                return DataDogOperationType.LOG_DEBUG
            elif 'info' in member_lower:
                return DataDogOperationType.LOG_INFO
            else:
                return DataDogOperationType.LOG_INFO
        
        # SDK configuration
        elif 'datadog' in type_lower and 'sdk' in type_lower:
            return DataDogOperationType.CONFIGURATION
        
        # Default to custom attribute
        return DataDogOperationType.CUSTOM_ATTRIBUTE
    
    def _extract_data_from_line(self, line: str, pattern_type: str) -> Dict[str, Any]:
        """Extract data being sent from the C# code line."""
        data = {}
        
        if pattern_type == 'imports':
            # Extract using statement details
            using_match = re.search(r'using\s+(Datadog\.[A-Za-z.]+)', line)
            if using_match:
                data['namespace'] = using_match.group(1)
        
        elif pattern_type in ['log_info', 'log_error', 'log_warn', 'log_debug']:
            # Extract log message and parameters
            log_match = re.search(r'\.(?:Log|Info|Error|Warn|Debug)\s*\(\s*(?:DdLogLevel\.\w+,\s*)?["\']([^"\']*)["\']', line)
            if log_match:
                data['log_message'] = log_match.group(1)
            
            # Extract parameters (everything inside parentheses)
            params_match = re.search(r'\.(?:Log|Info|Error|Warn|Debug)\s*\(([^)]+)\)', line)
            if params_match:
                data['parameters'] = params_match.group(1)
        
        elif pattern_type in ['rum_action', 'rum_error', 'rum_timing']:
            # Extract RUM action type and name
            action_match = re.search(r'\.(?:Add|Start|Stop)(?:Action|Error|Timing)\s*\(\s*(?:RumUserActionType\.(\w+),\s*)?["\']([^"\']*)["\']', line)
            if action_match:
                data['action_type'] = action_match.group(1) if action_match.group(1) else 'Custom'
                data['action_name'] = action_match.group(2) if action_match.group(2) else action_match.group(1)
            
            # Extract parameters
            params_match = re.search(r'\.(?:Add|Start|Stop)(?:Action|Error|Timing)\s*\(([^)]+)\)', line)
            if params_match:
                data['parameters'] = params_match.group(1)
        
        elif pattern_type == 'rum_attribute':
            # Extract attribute key and value
            attr_match = re.search(r'\.(?:Add|Remove)Attribute\s*\(\s*["\']([^"\']*)["\'](?:\s*,\s*([^)]+))?', line)
            if attr_match:
                data['attribute_key'] = attr_match.group(1)
                if attr_match.group(2):
                    data['attribute_value'] = attr_match.group(2)
        
        elif pattern_type == 'user_info':
            # Extract user information parameters
            params_match = re.search(r'\.(?:SetUserInfo|AddUserExtraInfo)\s*\(([^)]+)\)', line)
            if params_match:
                data['parameters'] = params_match.group(1)
        
        return data
    
    def _categorise_data(self, data_being_sent: Dict[str, Any], pattern_type: str) -> DataCategory:
        """Categorise data based on content and pattern type."""
        if pattern_type == 'imports':
            return DataCategory.CONFIGURATION_DATA
        elif pattern_type in ['init', 'user_info', 'global_attributes', 'clear_data']:
            return DataCategory.CONFIGURATION_DATA
        elif pattern_type in ['log_error', 'rum_error']:
            return DataCategory.ERROR_DATA
        elif pattern_type in ['rum_timing']:
            return DataCategory.PERFORMANCE_DATA
        elif pattern_type in ['rum_action'] and any(keyword in str(data_being_sent).lower() 
                                                   for keyword in ['tap', 'click', 'swipe', 'scroll', 'touch']):
            return DataCategory.USER_DATA
        else:
            return DataCategory.SYSTEM_DATA
    
    def _categorise_type_usage(self, type_name: str, member_name: str) -> DataCategory:
        """Categorise data for type usage."""
        type_lower = type_name.lower()
        member_lower = member_name.lower()
        
        if 'error' in type_lower or 'error' in member_lower:
            return DataCategory.ERROR_DATA
        elif 'timing' in member_lower or 'performance' in member_lower:
            return DataCategory.PERFORMANCE_DATA
        elif 'action' in member_lower and any(keyword in member_lower for keyword in ['tap', 'click', 'swipe', 'scroll', 'touch']):
            return DataCategory.USER_DATA
        elif 'config' in type_lower or 'init' in member_lower or 'setup' in member_lower:
            return DataCategory.CONFIGURATION_DATA
        else:
            return DataCategory.SYSTEM_DATA
    
    def _extract_detailed_parameters(self, line: str, pattern_type: str) -> Optional[Dict[str, str]]:
        """Extract detailed parameters if detailed extraction is enabled."""
        # Implement detailed parameter extraction based on pattern type
        return None
    
    def _extract_parameters_from_usage(self, usage_context: str) -> Optional[str]:
        """Extract parameters from a method call or usage."""
        try:
            # Find the parameters inside parentheses
            start = usage_context.find('(')
            end = usage_context.rfind(')')
            
            if start != -1 and end != -1 and end > start:
                params = usage_context[start+1:end].strip()
                return params if params else None
            
            return None
        except:
            return None