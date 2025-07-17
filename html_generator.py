"""HTML report generation for DataDog analysis results."""

import json
import os
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
from jinja2 import Template, Environment, FileSystemLoader
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

from models import ScanResults, DataDogFinding, DataCategory, DataDogOperationType


class HtmlGenerator:
    """Generates HTML reports from DataDog scan results."""
    
    def __init__(self, output_dir: str = "./reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup Jinja2 environment
        template_dir = Path(__file__).parent / "templates"
        self.env = Environment(loader=FileSystemLoader(str(template_dir)))
        
        # Setup Pygments
        self.formatter = HtmlFormatter(style='github-dark', linenos=False)
    
    def generate_report(self, scan_results: ScanResults, 
                       title: str = "DataDog Usage Analysis") -> str:
        """Generate complete HTML report from scan results."""
        
        # Prepare data for template
        template_data = self._prepare_template_data(scan_results, title)
        
        # Generate main report
        report_html = self._generate_main_report(template_data)
        
        # Write report to file
        report_path = self.output_dir / "datadog_analysis_report.html"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report_html)
        
        # Generate additional files
        self._generate_json_export(scan_results)
        self._generate_csv_export(scan_results)
        
        return str(report_path)
    
    def _prepare_template_data(self, scan_results: ScanResults, title: str) -> Dict[str, Any]:
        """Prepare data for HTML template."""
        
        # Calculate statistics
        stats = self._calculate_statistics(scan_results)
        
        # Group findings
        findings_by_project = self._group_findings_by_project(scan_results.findings)
        findings_by_category = self._group_findings_by_category(scan_results.findings)
        findings_by_operation = self._group_findings_by_operation(scan_results.findings)
        
        # Process findings with syntax highlighting
        processed_findings = self._process_findings_for_display(scan_results.findings)
        
        return {
            'title': title,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'scan_results': scan_results,
            'statistics': stats,
            'findings_by_project': findings_by_project,
            'findings_by_category': findings_by_category,
            'findings_by_operation': findings_by_operation,
            'processed_findings': processed_findings,
            'projects': scan_results.projects,
            'total_findings': len(scan_results.findings)
        }
    
    def _generate_main_report(self, template_data: Dict[str, Any]) -> str:
        """Generate the main HTML report."""
        
        # Create embedded template if template file doesn't exist
        template_content = self._get_main_template()
        template = Template(template_content)
        
        return template.render(**template_data)
    
    def _get_main_template(self) -> str:
        """Get the main HTML template content."""
        return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f5f5f5;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 2rem;
            border-radius: 10px;
            margin-bottom: 2rem;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
        }
        
        .header p {
            font-size: 1.1rem;
            opacity: 0.9;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        
        .stat-card {
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
        }
        
        .stat-card h3 {
            color: #667eea;
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }
        
        .stat-card p {
            color: #666;
            font-size: 0.9rem;
        }
        
        .controls {
            background: white;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 2rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        
        .controls input, .controls select {
            padding: 0.5rem;
            margin: 0.25rem;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 0.9rem;
        }
        
        .controls input[type="search"] {
            min-width: 300px;
        }
        
        .findings-container {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        
        .project-section {
            border-bottom: 1px solid #eee;
        }
        
        .project-header {
            background: #f8f9fa;
            padding: 1rem;
            cursor: pointer;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .project-header:hover {
            background: #e9ecef;
        }
        
        .project-header h2 {
            color: #495057;
            font-size: 1.2rem;
        }
        
        .project-badge {
            background: #667eea;
            color: white;
            padding: 0.25rem 0.75rem;
            border-radius: 15px;
            font-size: 0.8rem;
        }
        
        .project-content {
            display: none;
        }
        
        .project-content.active {
            display: block;
        }
        
        .finding-item {
            border-bottom: 1px solid #f0f0f0;
            padding: 1rem;
        }
        
        .finding-item:last-child {
            border-bottom: none;
        }
        
        .finding-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
        }
        
        .finding-title {
            font-weight: bold;
            color: #333;
        }
        
        .finding-meta {
            font-size: 0.8rem;
            color: #666;
        }
        
        .operation-badge {
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: bold;
            text-transform: uppercase;
        }
        
        .operation-badge.import { background: #e3f2fd; color: #1976d2; }
        .operation-badge.init { background: #f3e5f5; color: #7b1fa2; }
        .operation-badge.rum_action { background: #e8f5e8; color: #388e3c; }
        .operation-badge.rum_error { background: #ffebee; color: #d32f2f; }
        .operation-badge.log_info { background: #fff3e0; color: #f57c00; }
        .operation-badge.method_call { background: #f0f4ff; color: #5b21b6; }
        .operation-badge.configuration { background: #fdf2f8; color: #be185d; }
        
        .code-snippet {
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 4px;
            padding: 1rem;
            margin: 0.5rem 0;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.85rem;
            overflow-x: auto;
        }
        
        .context-lines {
            color: #6c757d;
            font-style: italic;
        }
        
        .main-line {
            background: #fff3cd;
            font-weight: bold;
        }
        
        .data-extracted {
            background: #d4edda;
            border: 1px solid #c3e6cb;
            border-radius: 4px;
            padding: 0.75rem;
            margin: 0.5rem 0;
        }
        
        .data-extracted h4 {
            color: #155724;
            margin-bottom: 0.5rem;
        }
        
        .data-extracted pre {
            background: #f8f9fa;
            padding: 0.5rem;
            border-radius: 4px;
            font-size: 0.8rem;
            overflow-x: auto;
        }
        
        .github-link {
            display: inline-block;
            background: #24292e;
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            text-decoration: none;
            font-size: 0.8rem;
            margin-top: 0.5rem;
        }
        
        .github-link:hover {
            background: #0366d6;
        }
        
        .copy-btn {
            background: #6c757d;
            color: white;
            border: none;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.7rem;
            margin-left: 0.5rem;
        }
        
        .copy-btn:hover {
            background: #5a6268;
        }
        
        .export-links {
            text-align: center;
            margin-top: 2rem;
            padding-top: 2rem;
            border-top: 1px solid #eee;
        }
        
        .export-links a {
            display: inline-block;
            background: #28a745;
            color: white;
            padding: 0.75rem 1.5rem;
            border-radius: 4px;
            text-decoration: none;
            margin: 0 0.5rem;
        }
        
        .export-links a:hover {
            background: #218838;
        }
        
        .hidden {
            display: none;
        }
        
        @media (max-width: 768px) {
            .container {
                padding: 10px;
            }
            
            .header h1 {
                font-size: 2rem;
            }
            
            .stats-grid {
                grid-template-columns: 1fr;
            }
            
            .controls input[type="search"] {
                min-width: 200px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ title }}</h1>
            <p>Generated on {{ generated_at }}</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>{{ total_findings }}</h3>
                <p>Total DataDog Usages</p>
            </div>
            <div class="stat-card">
                <h3>{{ projects|length }}</h3>
                <p>Projects Scanned</p>
            </div>
            <div class="stat-card">
                <h3>{{ scan_results.total_files_scanned }}</h3>
                <p>Files Scanned</p>
            </div>
            <div class="stat-card">
                <h3>{{ "%.2f"|format(scan_results.scan_duration) }}s</h3>
                <p>Scan Duration</p>
            </div>
        </div>
        
        <div class="controls">
            <input type="search" id="search" placeholder="Search findings...">
            <select id="projectFilter">
                <option value="">All Projects</option>
                {% for project in projects %}
                <option value="{{ project.name }}">{{ project.name }}</option>
                {% endfor %}
            </select>
            <select id="categoryFilter">
                <option value="">All Categories</option>
                <option value="user_data">User Data</option>
                <option value="system_data">System Data</option>
                <option value="error_data">Error Data</option>
                <option value="performance_data">Performance Data</option>
                <option value="configuration_data">Configuration Data</option>
            </select>
            <select id="operationFilter">
                <option value="">All Operations</option>
                <option value="import">Import</option>
                <option value="init">Initialisation</option>
                <option value="rum_action">RUM Action</option>
                <option value="rum_error">RUM Error</option>
                <option value="log_info">Log Info</option>
            </select>
        </div>
        
        <div class="findings-container">
            {% for project in projects %}
            <div class="project-section" data-project="{{ project.name }}">
                <div class="project-header" onclick="toggleProject('{{ project.name }}')">
                    <h2>{{ project.name }}</h2>
                    <div>
                        <span class="project-badge">{{ project.project_type }}</span>
                        <span class="project-badge">{{ project.findings_count }} findings</span>
                    </div>
                </div>
                <div class="project-content" id="project-{{ project.name }}">
                    {% for finding in processed_findings %}
                    {% if finding.project_name == project.name %}
                    <div class="finding-item" 
                         data-project="{{ finding.project_name }}"
                         data-category="{{ finding.data_category.value }}"
                         data-operation="{{ finding.operation_type.value }}">
                        
                        <div class="finding-header">
                            <div class="finding-title">{{ finding.file_path.split('/')[-1] }}</div>
                            <div class="finding-meta">
                                <span class="operation-badge {{ finding.operation_type.value }}">
                                    {{ finding.operation_type.value }}
                                </span>
                                Line {{ finding.line_number }}
                            </div>
                        </div>
                        
                        <div class="code-snippet">
                            <div class="context-lines">
                                {% for line in finding.context_lines[:-1] %}
                                <div>{{ line }}</div>
                                {% endfor %}
                            </div>
                            <div class="main-line">{{ finding.code_snippet }}</div>
                        </div>
                        
                        {% if finding.data_being_sent %}
                        <div class="data-extracted">
                            <h4>Data Being Sent:</h4>
                            <pre>{{ finding.data_being_sent|tojson(indent=2) }}</pre>
                        </div>
                        {% endif %}
                        
                        <a href="{{ finding.github_url }}" target="_blank" class="github-link">
                            View on GitHub
                        </a>
                        <button class="copy-btn" onclick="copyToClipboard('{{ finding.code_snippet|e }}')">
                            Copy Code
                        </button>
                    </div>
                    {% endif %}
                    {% endfor %}
                </div>
            </div>
            {% endfor %}
        </div>
        
        <div class="export-links">
            <a href="datadog_findings.json" download>Download JSON</a>
            <a href="datadog_findings.csv" download>Download CSV</a>
        </div>
    </div>
    
    <script>
        // Project toggle functionality
        function toggleProject(projectName) {
            const content = document.getElementById('project-' + projectName);
            content.classList.toggle('active');
        }
        
        // Copy to clipboard functionality
        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                alert('Code copied to clipboard!');
            });
        }
        
        // Filter functionality
        document.addEventListener('DOMContentLoaded', function() {
            const searchInput = document.getElementById('search');
            const projectFilter = document.getElementById('projectFilter');
            const categoryFilter = document.getElementById('categoryFilter');
            const operationFilter = document.getElementById('operationFilter');
            
            function filterFindings() {
                const searchTerm = searchInput.value.toLowerCase();
                const selectedProject = projectFilter.value;
                const selectedCategory = categoryFilter.value;
                const selectedOperation = operationFilter.value;
                
                const findings = document.querySelectorAll('.finding-item');
                
                findings.forEach(finding => {
                    const project = finding.getAttribute('data-project');
                    const category = finding.getAttribute('data-category');
                    const operation = finding.getAttribute('data-operation');
                    const text = finding.textContent.toLowerCase();
                    
                    const matchesSearch = !searchTerm || text.includes(searchTerm);
                    const matchesProject = !selectedProject || project === selectedProject;
                    const matchesCategory = !selectedCategory || category === selectedCategory;
                    const matchesOperation = !selectedOperation || operation === selectedOperation;
                    
                    if (matchesSearch && matchesProject && matchesCategory && matchesOperation) {
                        finding.style.display = 'block';
                    } else {
                        finding.style.display = 'none';
                    }
                });
            }
            
            searchInput.addEventListener('input', filterFindings);
            projectFilter.addEventListener('change', filterFindings);
            categoryFilter.addEventListener('change', filterFindings);
            operationFilter.addEventListener('change', filterFindings);
        });
    </script>
</body>
</html>'''
    
    def _calculate_statistics(self, scan_results: ScanResults) -> Dict[str, Any]:
        """Calculate statistics from scan results."""
        stats = {
            'total_findings': len(scan_results.findings),
            'by_project': {},
            'by_category': {},
            'by_operation': {},
            'files_with_datadog': set()
        }
        
        for finding in scan_results.findings:
            # Count by project
            project = finding.project_name
            stats['by_project'][project] = stats['by_project'].get(project, 0) + 1
            
            # Count by category
            category = finding.data_category.value
            stats['by_category'][category] = stats['by_category'].get(category, 0) + 1
            
            # Count by operation
            operation = finding.operation_type.value
            stats['by_operation'][operation] = stats['by_operation'].get(operation, 0) + 1
            
            # Track files with DataDog
            stats['files_with_datadog'].add(finding.file_path)
        
        stats['files_with_datadog'] = len(stats['files_with_datadog'])
        
        return stats
    
    def _group_findings_by_project(self, findings: List[DataDogFinding]) -> Dict[str, List[DataDogFinding]]:
        """Group findings by project."""
        grouped = {}
        for finding in findings:
            project = finding.project_name
            if project not in grouped:
                grouped[project] = []
            grouped[project].append(finding)
        return grouped
    
    def _group_findings_by_category(self, findings: List[DataDogFinding]) -> Dict[str, List[DataDogFinding]]:
        """Group findings by data category."""
        grouped = {}
        for finding in findings:
            category = finding.data_category.value
            if category not in grouped:
                grouped[category] = []
            grouped[category].append(finding)
        return grouped
    
    def _group_findings_by_operation(self, findings: List[DataDogFinding]) -> Dict[str, List[DataDogFinding]]:
        """Group findings by operation type."""
        grouped = {}
        for finding in findings:
            operation = finding.operation_type.value
            if operation not in grouped:
                grouped[operation] = []
            grouped[operation].append(finding)
        return grouped
    
    def _process_findings_for_display(self, findings: List[DataDogFinding]) -> List[DataDogFinding]:
        """Process findings for display with syntax highlighting."""
        # For now, return as-is. Could add syntax highlighting here
        return findings
    
    def _generate_json_export(self, scan_results: ScanResults) -> None:
        """Generate JSON export of scan results."""
        json_path = self.output_dir / "datadog_findings.json"
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(scan_results.to_dict(), f, indent=2, ensure_ascii=False)
    
    def _generate_csv_export(self, scan_results: ScanResults) -> None:
        """Generate CSV export of scan results."""
        csv_path = self.output_dir / "datadog_findings.csv"
        
        import csv
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Write header
            writer.writerow([
                'Project', 'File Path', 'Line Number', 'Operation Type',
                'Data Category', 'Code Snippet', 'Data Being Sent', 'GitHub URL'
            ])
            
            # Write findings
            for finding in scan_results.findings:
                writer.writerow([
                    finding.project_name,
                    finding.file_path,
                    finding.line_number,
                    finding.operation_type.value,
                    finding.data_category.value,
                    finding.code_snippet,
                    json.dumps(finding.data_being_sent),
                    finding.github_url
                ])
    
    def _get_file_extension(self, file_path: str) -> str:
        """Get file extension to determine lexer."""
        return Path(file_path).suffix.lower()
    
    def _highlight_code(self, code: str, file_path: str) -> str:
        """Apply syntax highlighting to code."""
        try:
            ext = self._get_file_extension(file_path)
            
            if ext in ['.ts', '.tsx']:
                lexer = get_lexer_by_name('typescript')
            elif ext in ['.js', '.jsx']:
                lexer = get_lexer_by_name('javascript')
            else:
                lexer = get_lexer_by_name('text')
            
            return highlight(code, lexer, self.formatter)
        except:
            # Fallback to plain text
            return f"<pre>{code}</pre>"