"""TypeScript/JavaScript DataDog usage detection."""

import re
import json
from typing import List, Dict, Any, Optional

from models import DataDogFinding, DataDogOperationType, DataCategory
from .base_detector import BaseDataDogDetector


class TypeScriptDataDogDetector(BaseDataDogDetector):
    """Detects DataDog usage patterns in TypeScript/JavaScript files."""
    
    def get_supported_extensions(self) -> List[str]:
        """Return supported file extensions for TypeScript/JavaScript."""
        return ['.ts', '.tsx', '.js', '.jsx']
    
    def get_language_name(self) -> str:
        """Return the language name."""
        return "TypeScript/JavaScript"
    
    def _compile_patterns(self):
        """Compile regex patterns for TypeScript/JavaScript DataDog detection."""
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
        """Detect DataDog usage in TypeScript/JavaScript file content."""
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
    
    def _extract_imported_methods(self, content: str, file_path: str) -> Dict[str, Dict[str, str]]:
        """Extract imported DataDog methods from file content."""
        imported_methods = {}
        
        # Match various import patterns
        import_patterns = [
            r'import\s+\{\s*([^}]+)\s*\}\s+from\s+[\'"](@datadog/[^\'"]+)[\'"]',
            r'import\s+(\w+)\s+from\s+[\'"](@datadog/[^\'"]+)[\'"]',
        ]
        
        for pattern in import_patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                imported_items = match.group(1).strip()
                package = match.group(2)
                
                # Handle destructured imports like { datadogRum, datadogLogs }
                if '{' not in imported_items:  # Single import
                    imported_methods[imported_items] = {
                        'package': package,
                        'import_type': 'default'
                    }
                else:  # Multiple imports in braces
                    # Clean up the import list
                    items = [item.strip() for item in imported_items.split(',')]
                    for item in items:
                        if item:  # Skip empty strings
                            imported_methods[item] = {
                                'package': package,
                                'import_type': 'destructured'
                            }
        
        return imported_methods
    
    def _find_method_calls(self, line: str, method_name: str, method_info: Dict[str, str]) -> List[Dict[str, Any]]:
        """Find calls to imported DataDog methods in a line."""
        calls = []
        
        # Create patterns to find method usage
        patterns = [
            # Direct function call: methodName(
            rf'\b{re.escape(method_name)}\s*\(',
            # Object method call: obj.methodName(
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
    
    def _determine_call_type(self, line: str, start_pos: int) -> str:
        """Determine the type of method call."""
        line_before = line[:start_pos].strip()
        
        if '=' in line_before and line_before.endswith('='):
            return 'assignment'
        elif '.' in line_before:
            return 'method_call'
        elif '(' in line[start_pos:start_pos+20]:
            return 'function_call'
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
    
    def _create_method_call_finding(self, file_path: str, line_num: int, line: str, 
                                   all_lines: List[str], call_info: Dict[str, Any],
                                   project_name: str, github_url: str) -> Optional[DataDogFinding]:
        """Create a DataDog finding from an imported method call."""
        # Get context lines
        context_lines = self._get_context_lines(all_lines, line_num)
        
        # Determine operation type based on method and package
        operation_type = self._get_method_operation_type(call_info['method_name'], call_info['package'])
        
        # Create data being sent structure
        data_being_sent = {
            'method_name': call_info['method_name'],
            'package': call_info['package'],
            'call_context': call_info['call_context'],
            'call_type': call_info['call_type']
        }
        
        # Extract parameters if available
        params = self._extract_parameters_from_call(call_info['call_context'])
        if params:
            data_being_sent['parameters'] = params
        
        # Categorise data
        data_category = self._categorise_method_call(call_info['method_name'], call_info['package'])
        
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
            'log_info': DataDogOperationType.LOG_INFO,
            'log_error': DataDogOperationType.LOG_ERROR,
            'log_warn': DataDogOperationType.LOG_WARN,
            'log_debug': DataDogOperationType.LOG_DEBUG,
        }
        return mapping.get(pattern_type, DataDogOperationType.CUSTOM_ATTRIBUTE)
    
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
        
        elif pattern_type in ['log_info', 'log_error', 'log_warn', 'log_debug']:
            # Extract log message and parameters
            log_match = re.search(r'\.(?:info|error|warn|debug)\s*\(\s*[\'"]([^\'"]*)[\'"]', line)
            if log_match:
                data['log_message'] = log_match.group(1)
            
            # Extract parameters (everything after the message)
            params_match = re.search(r'\.(?:info|error|warn|debug)\s*\(\s*([^)]+)\)', line)
            if params_match:
                data['parameters'] = params_match.group(1)
        
        elif pattern_type in ['rum_action', 'rum_error', 'rum_timing']:
            # Extract RUM action name and data
            action_match = re.search(r'\.(?:addAction|addError|addTiming)\s*\(\s*[\'"]([^\'"]*)[\'"]', line)
            if action_match:
                data['action_name'] = action_match.group(1)
            
            # Extract parameters
            params_match = re.search(r'\.(?:addAction|addError|addTiming)\s*\(\s*([^)]+)\)', line)
            if params_match:
                data['parameters'] = params_match.group(1)
        
        return data
    
    def _categorise_data(self, data_being_sent: Dict[str, Any], pattern_type: str) -> DataCategory:
        """Categorise data based on content and pattern type."""
        if pattern_type == 'imports':
            return DataCategory.CONFIGURATION_DATA
        elif pattern_type == 'init':
            return DataCategory.CONFIGURATION_DATA
        elif pattern_type in ['log_error', 'rum_error']:
            return DataCategory.ERROR_DATA
        elif pattern_type in ['rum_timing']:
            return DataCategory.PERFORMANCE_DATA
        elif pattern_type in ['rum_action'] and any(keyword in str(data_being_sent).lower() 
                                                   for keyword in ['click', 'tap', 'input', 'select']):
            return DataCategory.USER_DATA
        else:
            return DataCategory.SYSTEM_DATA
    
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
    
    def _extract_detailed_parameters(self, line: str, pattern_type: str) -> Optional[Dict[str, str]]:
        """Extract detailed parameters if detailed extraction is enabled."""
        # Implement detailed parameter extraction based on pattern type
        return None
    
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