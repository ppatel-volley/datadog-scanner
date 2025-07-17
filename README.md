# DataDog Analysis Tool

A comprehensive Python tool for analysing DataDog usage across code repositories. This tool scans TypeScript/JavaScript and C# Unity projects to identify where and what data is being sent to DataDog, providing detailed reports with GitHub integration.

## Features

- **Multi-language support**: TypeScript/JavaScript (web) and C# (Unity) DataDog SDK detection
- **Multi-project scanning**: Automatically detects and scans React, Next.js, Unity, and Node.js projects
- **DataDog usage detection**: Identifies imports, initialisation, RUM actions, error tracking, and logging
- **Data extraction**: Extracts and categorises data being sent to DataDog
- **Interactive HTML reports**: Generates searchable, filterable reports with syntax highlighting
- **GitHub integration**: Direct links to code locations in GitHub repositories
- **Export options**: JSON and CSV exports for further analysis
- **Multi-threaded scanning**: Fast scanning with parallel processing
- **Extensible architecture**: Easy to add support for additional languages and DataDog SDKs

## Installation & Setup

### Prerequisites

- Python 3.8 or higher
- Git (for GitHub integration)

### Setup with Virtual Environment

1. **Clone or download the DataDog analyser:**
   ```bash
   cd /Users/pratik/dev/ccm/datadog_analyser
   ```

2. **Create a virtual environment:**
   ```bash
   python3 -m venv venv
   ```

3. **Activate the virtual environment:**
   
   On macOS/Linux:
   ```bash
   source venv/bin/activate
   ```
   
   On Windows:
   ```bash
   venv\Scripts\activate
   ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

5. **Install test dependencies (optional):**
   ```bash
   pip install -r test_requirements.txt
   ```

### Verify Installation

Run the help command to verify everything is working:
```bash
python main.py --help
```

## Usage

### Basic Usage

Scan all projects in the CCM directory:
```bash
python main.py --scan-dir /Users/pratik/dev/ccm
```

### Advanced Usage

**Custom output directory:**
```bash
python main.py --scan-dir /Users/pratik/dev/ccm --output-dir ./my-reports
```

**Filter by data type:**
```bash
python main.py --scan-dir /Users/pratik/dev/ccm --data-type user-data
```

**Enable detailed data extraction:**
```bash
python main.py --scan-dir /Users/pratik/dev/ccm --extract-data-detailed
```

**Scan specific project only:**
```bash
python main.py --scan-dir /Users/pratik/dev/ccm --project cocomelon-mobile
```

**Custom GitHub repository URL:**
```bash
python main.py --scan-dir /Users/pratik/dev/ccm --github-repo https://github.com/Volley-Inc/cocomelon-unity
```

**Custom file extensions:**
```bash
python main.py --scan-dir /Users/pratik/dev/ccm --file-extensions .ts .tsx .js .jsx .vue
```

**Additional ignore patterns:**
```bash
python main.py --scan-dir /Users/pratik/dev/ccm --ignore-patterns "*.test.js" "*.spec.ts"
```

**Dry run (see what would be scanned):**
```bash
python main.py --scan-dir /Users/pratik/dev/ccm --dry-run
```

**Verbose output:**
```bash
python main.py --scan-dir /Users/pratik/dev/ccm --verbose
```

### Configuration File

You can use a configuration file instead of command-line arguments:

1. **Create a config file** (`config.json`):
   ```json
   {
     "scan": {
       "file_extensions": [".ts", ".tsx", ".js", ".jsx"],
       "ignore_patterns": ["node_modules/**", "build/**", "dist/**"],
       "context_lines": 3
     },
     "github": {
       "base_url": "https://github.com/Volley-Inc",
       "default_branch": "main"
     },
     "output": {
       "output_dir": "./reports",
       "data_extraction_detailed": true,
       "grouping_by": "project"
     }
   }
   ```

2. **Use the config file:**
   ```bash
   python main.py --scan-dir /Users/pratik/dev/ccm --config config.json
   ```

## Output

The tool generates several output files in the reports directory:

### HTML Report (`datadog_analysis_report.html`)
- Interactive web interface with search and filtering
- Syntax-highlighted code snippets
- Context lines around DataDog usage
- Direct links to GitHub
- Project-based organisation
- Statistics dashboard

### JSON Export (`datadog_findings.json`)
- Machine-readable format
- Complete scan results including metadata
- Suitable for integration with other tools

### CSV Export (`datadog_findings.csv`)
- Spreadsheet-compatible format
- Summary of findings for analysis
- Easy filtering and sorting

## What the Tool Detects

### DataDog Operations
- **Imports**: `import { datadogRum } from '@datadog/browser-rum'`
- **Initialisation**: `datadogRum.init({ ... })`
- **RUM Actions**: `datadogRum.addAction('button-click')`
- **Error Tracking**: `datadogRum.addError(error)`
- **Performance Timing**: `datadogRum.addTiming('api-call')`
- **Logging**: `logger.info()`, `logger.error()`, etc.

### Data Categories
- **User Data**: User interactions, clicks, form submissions
- **System Data**: Application events, API calls, system status
- **Error Data**: Error messages, stack traces, exception details
- **Performance Data**: Timing metrics, performance measurements
- **Configuration Data**: Setup parameters, environment config

### Project Types
The tool automatically detects and configures ignore patterns for:
- **React**: Detects `react` dependency in package.json
- **Next.js**: Detects `next` dependency in package.json
- **Unity**: Detects `Assets/` and `ProjectSettings/` directories
- **Node.js**: Generic Node.js projects with package.json

## Running Tests

The tool includes comprehensive test suites for all modules.

### Run All Tests
```bash
python -m pytest
```

### Run Tests with Coverage
```bash
python -m pytest --cov=. --cov-report=html
```

### Run Specific Test Module
```bash
python -m pytest test_models.py
python -m pytest test_datadog_detector.py
```

### Run Tests with Verbose Output
```bash
python -m pytest -v
```

## Troubleshooting

### Common Issues

**1. Permission Errors**
```bash
chmod +x main.py
```

**2. Module Not Found**
Make sure you're in the correct directory and virtual environment is activated:
```bash
source venv/bin/activate
pwd  # Should show /Users/pratik/dev/ccm/datadog_analyser
```

**3. Git Command Errors**
Ensure git is installed and accessible:
```bash
git --version
```

**4. File Encoding Issues**
The tool automatically detects file encodings, but for stubborn files, try:
```bash
python main.py --scan-dir /Users/pratik/dev/ccm --verbose
```

### Debug Mode

Enable verbose logging to see detailed operation:
```bash
python main.py --scan-dir /Users/pratik/dev/ccm --verbose
```

Check the log file for detailed information:
```bash
tail -f datadog_analyser.log
```

## Development

### Project Structure
```
datadog_analyser/
├── main.py                 # Entry point and CLI interface
├── code_scanner.py         # Core scanning logic
├── datadog_detector.py     # DataDog usage detection patterns
├── html_generator.py       # HTML report generation
├── github_linker.py        # GitHub URL generation
├── config.py              # Configuration management
├── models.py              # Data models
├── requirements.txt       # Dependencies
├── test_*.py              # Test files
└── README.md             # This file
```

### Adding New Detection Patterns

1. **Edit `datadog_detector.py`**:
   - Add new regex patterns to `_compile_patterns()`
   - Add new operation type to `DataDogOperationType` enum
   - Update `_extract_data_from_line()` method

2. **Update tests**:
   - Add test cases in `test_datadog_detector.py`

3. **Test your changes**:
   ```bash
   python -m pytest test_datadog_detector.py -v
   ```

### Contributing

1. **Follow PEP-8** coding standards
2. **Add tests** for new functionality
3. **Update documentation** for new features
4. **Use type hints** where appropriate

## License

This tool is part of the CoComelon project and is intended for internal use at Volley Inc.

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review the log file (`datadog_analyser.log`)
3. Run with `--verbose` flag for detailed output
4. Contact the development team with specific error messages

---

**Note**: This tool is designed specifically for the CoComelon project structure. Modifications may be needed for other project configurations.