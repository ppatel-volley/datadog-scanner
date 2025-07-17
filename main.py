#!/usr/bin/env python3
"""Main entry point for DataDog analyser."""

import argparse
import sys
import logging
from pathlib import Path
from typing import List, Optional

from config import AppConfig, ConfigManager
from code_scanner import CodeScanner
from github_linker import GitHubLinker
from html_generator import HtmlGenerator
from models import DataCategory, DataDogOperationType


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('datadog_analyser.log')
        ]
    )


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description='Analyse DataDog usage across code repositories',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  %(prog)s --scan-dir /Users/pratik/dev/ccm
  %(prog)s --scan-dir /Users/pratik/dev/ccm --github-repo https://github.com/Volley-Inc/cocomelon-unity
  %(prog)s --scan-dir /Users/pratik/dev/ccm --data-type user-data
  %(prog)s --scan-dir /Users/pratik/dev/ccm --extract-data-detailed
        '''
    )
    
    # Required arguments
    parser.add_argument(
        '--scan-dir',
        required=True,
        help='Directory to scan for DataDog usage'
    )
    
    # Optional arguments
    parser.add_argument(
        '--github-repo',
        help='Base GitHub repository URL (default: https://github.com/Volley-Inc)'
    )
    
    parser.add_argument(
        '--output-dir',
        default='./reports',
        help='Output directory for reports (default: ./reports)'
    )
    
    parser.add_argument(
        '--data-type',
        choices=['user-data', 'system-data', 'error-data', 'performance-data', 'configuration-data'],
        help='Filter by data type'
    )
    
    parser.add_argument(
        '--extract-data-detailed',
        action='store_true',
        help='Enable detailed data extraction'
    )
    
    parser.add_argument(
        '--project',
        help='Scan specific project only'
    )
    
    parser.add_argument(
        '--config',
        help='Path to configuration file'
    )
    
    parser.add_argument(
        '--file-extensions',
        nargs='+',
        default=['.ts', '.tsx', '.js', '.jsx'],
        help='File extensions to scan (default: .ts .tsx .js .jsx)'
    )
    
    parser.add_argument(
        '--ignore-patterns',
        nargs='+',
        help='Additional ignore patterns'
    )
    
    parser.add_argument(
        '--context-lines',
        type=int,
        default=3,
        help='Number of context lines to include (default: 3)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be scanned without actually scanning'
    )
    
    return parser


def validate_arguments(args: argparse.Namespace) -> None:
    """Validate command line arguments."""
    # Check if scan directory exists
    scan_dir = Path(args.scan_dir)
    if not scan_dir.exists():
        raise ValueError(f"Scan directory does not exist: {args.scan_dir}")
    
    if not scan_dir.is_dir():
        raise ValueError(f"Scan path is not a directory: {args.scan_dir}")
    
    # Validate output directory
    output_dir = Path(args.output_dir)
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise ValueError(f"Cannot create output directory {args.output_dir}: {e}")


def create_config_from_args(args: argparse.Namespace) -> AppConfig:
    """Create configuration from command line arguments."""
    # Load base config
    config = ConfigManager.load_config(args.config)
    
    # Override with command line arguments
    config.scan.target_directories = [args.scan_dir]
    config.scan.file_extensions = args.file_extensions
    config.scan.context_lines = args.context_lines
    config.output.output_dir = args.output_dir
    config.output.data_extraction_detailed = args.extract_data_detailed
    
    # Add additional ignore patterns
    if args.ignore_patterns:
        config.scan.ignore_patterns.extend(args.ignore_patterns)
    
    # Set GitHub base URL
    if args.github_repo:
        config.github.base_url = args.github_repo
    
    return config


def filter_results_by_data_type(scan_results, data_type: str):
    """Filter scan results by data type."""
    if not data_type:
        return scan_results
    
    # Map CLI data type to enum
    data_type_mapping = {
        'user-data': DataCategory.USER_DATA,
        'system-data': DataCategory.SYSTEM_DATA,
        'error-data': DataCategory.ERROR_DATA,
        'performance-data': DataCategory.PERFORMANCE_DATA,
        'configuration-data': DataCategory.CONFIGURATION_DATA
    }
    
    target_category = data_type_mapping.get(data_type)
    if not target_category:
        return scan_results
    
    # Filter findings
    filtered_findings = [
        finding for finding in scan_results.findings
        if finding.data_category == target_category
    ]
    
    # Update project finding counts
    for project in scan_results.projects:
        project.findings_count = len([
            f for f in filtered_findings if f.project_name == project.name
        ])
    
    scan_results.findings = filtered_findings
    return scan_results


def filter_results_by_project(scan_results, project_name: str):
    """Filter scan results by project."""
    if not project_name:
        return scan_results
    
    # Filter findings
    filtered_findings = [
        finding for finding in scan_results.findings
        if finding.project_name == project_name
    ]
    
    # Filter projects
    filtered_projects = [
        project for project in scan_results.projects
        if project.name == project_name
    ]
    
    # Update finding counts
    for project in filtered_projects:
        project.findings_count = len([
            f for f in filtered_findings if f.project_name == project.name
        ])
    
    scan_results.findings = filtered_findings
    scan_results.projects = filtered_projects
    return scan_results


def print_scan_summary(scan_results):
    """Print a summary of scan results."""
    print("\n" + "="*60)
    print("SCAN SUMMARY")
    print("="*60)
    print(f"Total projects scanned: {len(scan_results.projects)}")
    print(f"Total files scanned: {scan_results.total_files_scanned}")
    print(f"Total DataDog usages found: {len(scan_results.findings)}")
    print(f"Scan duration: {scan_results.scan_duration:.2f} seconds")
    
    if scan_results.projects:
        print(f"\nProjects:")
        for project in scan_results.projects:
            print(f"  - {project.name} ({project.project_type}): {project.findings_count} findings")
    
    if scan_results.findings:
        print(f"\nData categories found:")
        categories = {}
        for finding in scan_results.findings:
            category = finding.data_category.value
            categories[category] = categories.get(category, 0) + 1
        
        for category, count in sorted(categories.items()):
            print(f"  - {category}: {count}")
    
    print("="*60)


def main() -> int:
    """Main entry point."""
    try:
        # Parse arguments
        parser = create_argument_parser()
        args = parser.parse_args()
        
        # Setup logging
        setup_logging(args.verbose)
        logger = logging.getLogger(__name__)
        
        # Validate arguments
        validate_arguments(args)
        
        # Create configuration
        config = create_config_from_args(args)
        
        logger.info(f"Starting DataDog analysis of {args.scan_dir}")
        
        # Dry run mode
        if args.dry_run:
            print(f"DRY RUN: Would scan directory: {args.scan_dir}")
            print(f"Output directory: {args.output_dir}")
            print(f"File extensions: {args.file_extensions}")
            print(f"GitHub base URL: {config.github.base_url}")
            return 0
        
        # Initialize components
        github_linker = GitHubLinker(
            base_url=config.github.base_url,
            default_branch=config.github.default_branch
        )
        
        scanner = CodeScanner(config, github_linker)
        
        # Perform scan
        logger.info("Starting scan...")
        scan_results = scanner.scan_directories(config.scan.target_directories)
        
        # Apply filters
        if args.data_type:
            scan_results = filter_results_by_data_type(scan_results, args.data_type)
            logger.info(f"Filtered by data type: {args.data_type}")
        
        if args.project:
            scan_results = filter_results_by_project(scan_results, args.project)
            logger.info(f"Filtered by project: {args.project}")
        
        # Print summary
        print_scan_summary(scan_results)
        
        # Generate reports
        logger.info("Generating HTML report...")
        html_generator = HtmlGenerator(config.output.output_dir)
        report_path = html_generator.generate_report(scan_results)
        
        print(f"\nHTML report generated: {report_path}")
        print(f"JSON export: {Path(config.output.output_dir) / 'datadog_findings.json'}")
        print(f"CSV export: {Path(config.output.output_dir) / 'datadog_findings.csv'}")
        
        logger.info("Analysis complete")
        return 0
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 1
    except Exception as e:
        print(f"Error: {e}")
        logging.getLogger(__name__).exception("Unexpected error")
        return 1


if __name__ == '__main__':
    sys.exit(main())