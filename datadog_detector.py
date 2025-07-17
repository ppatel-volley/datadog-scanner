"""DataDog usage detection and data extraction."""

import re
import json
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from models import DataDogFinding, DataDogOperationType, DataCategory


class DataDogDetector:
    """Detects DataDog usage patterns and extracts data being sent."""
    
    def __init__(self, context_lines: int = 3, detailed_extraction: bool = False):
        self.context_lines = context_lines
        self.detailed_extraction = detailed_extraction
        self.imported_datadog_methods = {}  # Track imported methods per file
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for DataDog detection."""
        self.patterns = {
            # Import patterns
            'imports': [
                re.compile(r'import\s+.*@datadog/browser-rum', re.IGNORECASE),
                re.compile(r'import\s+.*@datadog/browser-logs', re.IGNORECASE),
                re.compile(r'import\s+.*@datadog/browser-rum-react', re.IGNORECASE),
                re.compile(r'from\s+[\'"]@datadog/browser-rum[\'"]', re.IGNORECASE),
                re.compile(r'from\s+[\'"]@datadog/browser-logs[\'"]', re.IGNORECASE),
                re.compile(r'require\s*\(\s*[\'"]@datadog/browser-rum[\'"]', re.IGNORECASE),
                re.compile(r'require\s*\(\s*[\'"]@datadog/browser-logs[\'"]', re.IGNORECASE),
            ],
            
            # Initialisation patterns
            'init': [
                re.compile(r'datadogRum\.init\s*\(', re.IGNORECASE),
                re.compile(r'datadogLogs\.createLogger\s*\(', re.IGNORECASE),
                re.compile(r'DD_RUM\.init\s*\(', re.IGNORECASE),
            ],
            
            # RUM patterns
            'rum_action': [
                re.compile(r'datadogRum\.addAction\s*\(', re.IGNORECASE),
                re.compile(r'DD_RUM\.addAction\s*\(', re.IGNORECASE),
            ],
            
            'rum_error': [
                re.compile(r'datadogRum\.addError\s*\(', re.IGNORECASE),
                re.compile(r'DD_RUM\.addError\s*\(', re.IGNORECASE),
            ],
            
            'rum_timing': [
                re.compile(r'datadogRum\.addTiming\s*\(', re.IGNORECASE),
                re.compile(r'DD_RUM\.addTiming\s*\(', re.IGNORECASE),
            ],
            
            # Logging patterns
            'log_info': [
                re.compile(r'logger\.info\s*\(', re.IGNORECASE),
                re.compile(r'datadogLogs\.logger\.info\s*\(', re.IGNORECASE),
            ],
            
            'log_error': [
                re.compile(r'logger\.error\s*\(', re.IGNORECASE),
                re.compile(r'datadogLogs\.logger\.error\s*\(', re.IGNORECASE),
            ],
            
            'log_warn': [
                re.compile(r'logger\.warn\s*\(', re.IGNORECASE),
                re.compile(r'datadogLogs\.logger\.warn\s*\(', re.IGNORECASE),
            ],
            
            'log_debug': [
                re.compile(r'logger\.debug\s*\(', re.IGNORECASE),
                re.compile(r'datadogLogs\.logger\.debug\s*\(', re.IGNORECASE),
            ],
        }
    
    def detect_datadog_usage(self, file_path: str, content: str, 
                           project_name: str, github_url: str) -> List[DataDogFinding]:
        """Detect DataDog usage in file content."""
        findings = []
        lines = content.split('\n')
        
        # Track processed lines to avoid duplicates
        processed_lines = set()
        
        # First pass: Extract imported DataDog methods
        imported_methods = self._extract_imported_methods(content, file_path)
        
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
            
            # Check for imported method calls (only if not already processed)
            if line_key not in processed_lines:
                for method_name in imported_methods:
                    method_calls = self._find_method_calls(line, method_name, imported_methods[method_name])
                    for call_info in method_calls:
                        finding = self._create_method_call_finding(
                            file_path, line_num, line, lines, call_info,
                            project_name, github_url
                        )
                        if finding:
                            findings.append(finding)
                            processed_lines.add(line_key)
        
        # Deduplicate findings by file_path, line_number, and operation_type
        return self._deduplicate_findings(findings)
    
    def _create_finding(self, file_path: str, line_num: int, line: str, 
                       all_lines: List[str], pattern_type: str, 
                       project_name: str, github_url: str) -> Optional[DataDogFinding]:
        """Create a DataDog finding from a matched pattern."""
        # Get context lines
        context_start = max(0, line_num - self.context_lines - 1)
        context_end = min(len(all_lines), line_num + self.context_lines)
        context_lines = all_lines[context_start:context_end]
        
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
    
    def _get_operation_type(self, pattern_type: str) -> DataDogOperationType:
        """Map pattern type to operation type."""
        mapping = {
            'imports': DataDogOperationType.IMPORT,
            'init': DataDogOperationType.INIT,
            'rum_action': DataDogOperationType.RUM_ACTION,
            'rum_error': DataDogOperationType.RUM_ERROR,
            'rum_timing': DataDogOperationType.RUM_TIMING,
            'log_info': DataDogOperationType.LOG_INFO,
            'log_error': DataDogOperationType.LOG_ERROR,
            'log_warn': DataDogOperationType.LOG_WARN,
            'log_debug': DataDogOperationType.LOG_DEBUG,
        }
        return mapping.get(pattern_type, DataDogOperationType.CUSTOM_ATTRIBUTE)
    
    def _extract_data_from_line(self, line: str, pattern_type: str) -> Dict[str, Any]:
        """Extract data being sent from the code line."""
        data = {}
        
        if pattern_type == 'imports':
            # Extract import details
            import_match = re.search(r'import\s+({[^}]+}|\w+)', line)
            if import_match:
                data['imported_items'] = import_match.group(1)
            
            package_match = re.search(r'[\'"](@datadog/[^\'"]+)[\'"]', line)
            if package_match:
                data['package'] = package_match.group(1)
        
        elif pattern_type == 'init':
            # Extract configuration data
            config_match = re.search(r'\(\s*({[^}]+})', line)
            if config_match:
                try:
                    # Try to parse as JSON-like structure
                    config_str = config_match.group(1)
                    data['configuration'] = config_str
                    
                    # Extract specific config values
                    app_id_match = re.search(r'applicationId\s*:\s*[\'"]([^\'"]+)[\'"]', config_str)
                    if app_id_match:
                        data['application_id'] = app_id_match.group(1)
                    
                    client_token_match = re.search(r'clientToken\s*:\s*[\'"]([^\'"]+)[\'"]', config_str)
                    if client_token_match:
                        data['client_token'] = client_token_match.group(1)[:10] + "..."  # Truncate for security
                    
                    site_match = re.search(r'site\s*:\s*[\'"]([^\'"]+)[\'"]', config_str)
                    if site_match:
                        data['site'] = site_match.group(1)
                        
                except:
                    data['configuration'] = 'Could not parse configuration'
        
        elif pattern_type.startswith('rum_'):
            # Extract RUM data
            params_match = re.search(r'\(\s*([^)]+)\)', line)
            if params_match:
                params = params_match.group(1)
                data['parameters'] = params
                
                # Extract specific values
                if pattern_type == 'rum_action':
                    action_match = re.search(r'[\'"]([^\'"]+)[\'"]', params)
                    if action_match:
                        data['action_name'] = action_match.group(1)
                
                elif pattern_type == 'rum_error':
                    error_match = re.search(r'[\'"]([^\'"]+)[\'"]', params)
                    if error_match:
                        data['error_message'] = error_match.group(1)
        
        elif pattern_type.startswith('log_'):
            # Extract log data
            params_match = re.search(r'\(\s*([^)]+)\)', line)
            if params_match:
                params = params_match.group(1)
                data['parameters'] = params
                
                # Extract log message
                message_match = re.search(r'[\'"]([^\'"]+)[\'"]', params)
                if message_match:
                    data['log_message'] = message_match.group(1)
        
        return data
    
    def _categorise_data(self, data: Dict[str, Any], pattern_type: str) -> DataCategory:
        """Categorise the type of data being sent."""
        if pattern_type == 'imports':
            return DataCategory.CONFIGURATION_DATA
        
        elif pattern_type == 'init':
            return DataCategory.CONFIGURATION_DATA
        
        elif pattern_type == 'rum_error':
            return DataCategory.ERROR_DATA
        
        elif pattern_type == 'rum_timing':
            return DataCategory.PERFORMANCE_DATA
        
        elif pattern_type.startswith('log_error'):
            return DataCategory.ERROR_DATA
        
        elif pattern_type.startswith('log_'):
            return DataCategory.SYSTEM_DATA
        
        elif pattern_type == 'rum_action':
            # Try to determine if it's user action or system action
            action_name = data.get('action_name', '').lower()
            user_action_keywords = ['click', 'tap', 'swipe', 'scroll', 'input', 'select', 'submit']
            
            if any(keyword in action_name for keyword in user_action_keywords):
                return DataCategory.USER_DATA
            else:
                return DataCategory.SYSTEM_DATA
        
        return DataCategory.UNKNOWN
    
    def _extract_detailed_parameters(self, line: str, pattern_type: str) -> Optional[Dict[str, str]]:
        """Extract detailed parameter information for advanced analysis."""
        if not self.detailed_extraction:
            return None
        
        params = {}
        
        # Extract function call parameters
        func_match = re.search(r'\w+\s*\(\s*([^)]+)\)', line)
        if func_match:
            param_str = func_match.group(1)
            
            # Try to extract key-value pairs
            kv_matches = re.findall(r'(\w+)\s*:\s*([^,}]+)', param_str)
            for key, value in kv_matches:
                params[key] = value.strip()
            
            # Extract string literals
            string_matches = re.findall(r'[\'"]([^\'"]+)[\'"]', param_str)
            if string_matches:
                params['string_literals'] = string_matches
        
        return params if params else None
    
    def is_datadog_related_file(self, file_path: str) -> bool:
        """Check if a file is likely to contain DataDog usage."""
        path = Path(file_path)
        
        # Check file extension
        if path.suffix not in ['.js', '.jsx', '.ts', '.tsx', '.vue', '.svelte']:
            return False
        
        # Check for DataDog-related file names
        datadog_keywords = ['datadog', 'dd-rum', 'analytics', 'telemetry', 'monitoring']
        filename_lower = path.name.lower()
        
        if any(keyword in filename_lower for keyword in datadog_keywords):
            return True
        
        return True  # Default to scanning all eligible files
    
    def get_statistics(self, findings: List[DataDogFinding]) -> Dict[str, Any]:
        """Generate statistics from findings."""
        stats = {
            'total_findings': len(findings),
            'by_operation_type': {},
            'by_data_category': {},
            'by_project': {},
            'files_with_datadog': set()
        }
        
        for finding in findings:
            # Count by operation type
            op_type = finding.operation_type.value
            stats['by_operation_type'][op_type] = stats['by_operation_type'].get(op_type, 0) + 1
            
            # Count by data category
            data_cat = finding.data_category.value
            stats['by_data_category'][data_cat] = stats['by_data_category'].get(data_cat, 0) + 1
            
            # Count by project
            project = finding.project_name
            stats['by_project'][project] = stats['by_project'].get(project, 0) + 1
            
            # Track files with DataDog usage
            stats['files_with_datadog'].add(finding.file_path)
        
        # Convert set to count
        stats['files_with_datadog'] = len(stats['files_with_datadog'])
        
        return stats
    
    def _extract_imported_methods(self, content: str, file_path: str) -> Dict[str, Dict[str, str]]:
        """Extract imported DataDog methods from file content."""
        imported_methods = {}
        lines = content.split('\n')
        
        for line in lines:
            # Match various import patterns
            import_patterns = [
                # Named imports: import { method1, method2 } from '@datadog/package'
                r'import\s+\{\s*([^}]+)\s*\}\s+from\s+[\'"](@datadog/[^\'"]+)[\'"]',
                # Default imports: import method from '@datadog/package'
                r'import\s+(\w+)\s+from\s+[\'"](@datadog/[^\'"]+)[\'"]',
                # Namespace imports: import * as dd from '@datadog/package'
                r'import\s+\*\s+as\s+(\w+)\s+from\s+[\'"](@datadog/[^\'"]+)[\'"]',
            ]
            
            for pattern in import_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    imported_items = match.group(1).strip()
                    package = match.group(2)
                    
                    # Handle named imports (comma-separated)
                    if '{' not in line or '}' not in line:
                        # Single import or namespace import
                        methods = [imported_items.strip()]
                    else:
                        # Named imports - split by comma
                        methods = [method.strip() for method in imported_items.split(',')]
                    
                    for method in methods:
                        # Clean up method name (remove aliases, etc.)
                        clean_method = method.split(' as ')[0].strip()
                        if clean_method:
                            imported_methods[clean_method] = {
                                'package': package,
                                'import_type': 'named' if '{' in line else 'default',
                                'original_line': line.strip()
                            }
        
        return imported_methods
    
    def _find_method_calls(self, line: str, method_name: str, method_info: Dict[str, str]) -> List[Dict[str, str]]:
        """Find calls to imported DataDog methods in a line."""
        calls = []
        
        # Pattern to match method calls: methodName(...) or object.methodName(...)
        patterns = [
            # Direct method call: methodName(...)
            rf'\b{re.escape(method_name)}\s*\(',
            # Object method call: obj.methodName(...)
            rf'\.\s*{re.escape(method_name)}\s*\(',
            # Assignment or other usage: var = methodName
            rf'\b{re.escape(method_name)}\b(?!\s*:)',  # Not followed by colon (object property)
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, line, re.IGNORECASE)
            for match in matches:
                # Extract the full call context
                call_context = self._extract_call_context(line, match.start(), method_name)
                
                calls.append({
                    'method_name': method_name,
                    'package': method_info['package'],
                    'call_context': call_context,
                    'match_start': match.start(),
                    'match_end': match.end(),
                    'call_type': self._determine_call_type(line, match.start())
                })
        
        return calls
    
    def _extract_call_context(self, line: str, start_pos: int, method_name: str) -> str:
        """Extract the context around a method call."""
        # Try to extract the full function call including parameters
        try:
            # Find the opening parenthesis
            paren_start = line.find('(', start_pos)
            if paren_start == -1:
                return line.strip()
            
            # Find the matching closing parenthesis
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
            
            # Extract from start of method name to end of call
            method_start = max(0, start_pos - 10)  # Include some context before
            call_end = min(len(line), paren_end + 1)
            
            return line[method_start:call_end].strip()
        except:
            return line.strip()
    
    def _determine_call_type(self, line: str, match_start: int) -> str:
        """Determine the type of method call."""
        # Look at context before the match
        before_match = line[:match_start].strip()
        
        if before_match.endswith('.'):
            return 'method_call'
        elif '=' in before_match and before_match.split('=')[-1].strip() == '':
            return 'assignment'
        elif 'new ' in before_match[-10:]:
            return 'constructor'
        else:
            return 'function_call'
    
    def _create_method_call_finding(self, file_path: str, line_num: int, line: str,
                                  all_lines: List[str], call_info: Dict[str, str],
                                  project_name: str, github_url: str) -> Optional[DataDogFinding]:
        """Create a finding for an imported method call."""
        # Get context lines
        context_start = max(0, line_num - self.context_lines - 1)
        context_end = min(len(all_lines), line_num + self.context_lines)
        context_lines = all_lines[context_start:context_end]
        
        # Determine operation type based on method name and package
        operation_type = self._get_method_operation_type(call_info['method_name'], call_info['package'])
        
        # Extract data being sent
        data_being_sent = {
            'method_name': call_info['method_name'],
            'package': call_info['package'],
            'call_context': call_info['call_context'],
            'call_type': call_info['call_type']
        }
        
        # Try to extract parameters if it's a function call
        if call_info['call_type'] == 'function_call' or call_info['call_type'] == 'method_call':
            parameters = self._extract_parameters_from_call(call_info['call_context'])
            if parameters:
                data_being_sent['parameters'] = parameters
        
        # Categorise data
        data_category = self._categorise_method_call(call_info['method_name'], call_info['package'])
        
        # Extract detailed parameters if enabled
        extracted_params = None
        if self.detailed_extraction:
            extracted_params = self._extract_detailed_parameters(line, 'method_call')
        
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
    
    def _get_method_operation_type(self, method_name: str, package: str) -> DataDogOperationType:
        """Get operation type for imported method calls."""
        method_lower = method_name.lower()
        
        # RUM-related methods
        if 'rum' in package.lower() or method_name in ['addAction', 'addError', 'addTiming']:
            if 'action' in method_lower:
                return DataDogOperationType.RUM_ACTION
            elif 'error' in method_lower:
                return DataDogOperationType.RUM_ERROR
            elif 'timing' in method_lower:
                return DataDogOperationType.RUM_TIMING
            else:
                return DataDogOperationType.CUSTOM_ATTRIBUTE
        
        # Log-related methods
        elif 'log' in package.lower() or method_name in ['logger', 'createLogger']:
            if 'error' in method_lower:
                return DataDogOperationType.LOG_ERROR
            elif 'warn' in method_lower:
                return DataDogOperationType.LOG_WARN
            elif 'debug' in method_lower:
                return DataDogOperationType.LOG_DEBUG
            elif 'info' in method_lower:
                return DataDogOperationType.LOG_INFO
            else:
                return DataDogOperationType.LOG_INFO
        
        # React plugin or other framework integrations
        elif 'react' in package.lower() or method_name in ['reactPlugin', 'createBrowserRouter']:
            return DataDogOperationType.CONFIGURATION
        
        # Default to custom attribute
        return DataDogOperationType.CUSTOM_ATTRIBUTE
    
    def _categorise_method_call(self, method_name: str, package: str) -> DataCategory:
        """Categorise data for imported method calls."""
        method_lower = method_name.lower()
        package_lower = package.lower()
        
        if 'error' in method_lower or 'error' in package_lower:
            return DataCategory.ERROR_DATA
        elif 'timing' in method_lower or 'performance' in method_lower:
            return DataCategory.PERFORMANCE_DATA
        elif 'action' in method_lower and any(keyword in method_lower for keyword in ['click', 'tap', 'swipe', 'scroll', 'input']):
            return DataCategory.USER_DATA
        elif 'react' in package_lower or 'plugin' in method_lower:
            return DataCategory.CONFIGURATION_DATA
        else:
            return DataCategory.SYSTEM_DATA
    
    def _extract_parameters_from_call(self, call_context: str) -> Optional[str]:
        """Extract parameters from a function call."""
        try:
            # Find the parameters inside parentheses
            start = call_context.find('(')
            end = call_context.rfind(')')
            
            if start != -1 and end != -1 and end > start:
                params = call_context[start+1:end].strip()
                return params if params else None
            
            return None
        except:
            return None
    
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