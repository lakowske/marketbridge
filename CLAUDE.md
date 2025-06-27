# Clean Python Project Template

## Project Purpose

This is a template for creating clean, professional Python projects that incorporate industry best practices from the start. It serves as a foundation for new Python projects with all the essential development tools and quality assurance measures pre-configured.

## Clean Code Practices Implemented

### Code Quality & Standards

- **Black** - Automatic code formatting with 88 character line length
- **Flake8** - Comprehensive linting with Google docstring conventions
- **mdformat** - Markdown formatting with GitHub Flavored Markdown support
- **Pre-commit hooks** - Automated quality checks before every commit

### Testing & Coverage

- **Pytest** - Modern testing framework with proper project structure
- **Coverage reporting** - Minimum 80% code coverage required
- **HTML coverage reports** - Generated in `htmlcov/` directory
- **Integration testing** - Structured test organization

### Git Workflow

- **Pre-commit configuration** - Ensures code quality on every commit
- **Automated checks** for:
  - Trailing whitespace removal
  - End-of-file fixing
  - YAML validation
  - Large file detection
  - Code formatting (Black)
  - Linting (Flake8)
  - Markdown formatting (mdformat with GFM support)
  - Test coverage (Pytest with 80% minimum)

## Project Structure

```text
clean-python/
├── actions/          # Project build and automation scripts
├── tests/           # Test suite with pytest configuration
├── build/           # Build artifacts (auto-generated)
├── htmlcov/         # HTML coverage reports
├── .pre-commit-config.yaml  # Pre-commit hook configuration
├── .flake8          # Flake8 linting configuration
├── setup.cfg        # Project metadata and configuration
└── requirements.txt # Project dependencies
```

## Development Commands

- `pytest --cov=. --cov-report=term-missing --cov-fail-under=80 --cov-report=html` - Run tests with coverage
- `black .` - Format code
- `flake8` - Run linting
- `pre-commit install` - Install pre-commit hooks
- `pre-commit run --all-files` - Run all pre-commit checks

## Server Management Commands

Use the professional CLI server management tool for running MarketBridge:

- `python scripts/manage_server.py start` - Start server in background
- `python scripts/manage_server.py stop` - Stop server gracefully
- `python scripts/manage_server.py restart` - Restart server
- `python scripts/manage_server.py status` - Show server status
- `python scripts/manage_server.py -v status` - Show detailed status with memory usage
- `python scripts/manage_server.py logs` - Show recent logs (last 50 lines)
- `python scripts/manage_server.py logs -n 100` - Show last 100 lines of logs
- `python scripts/manage_server.py logs --follow` - Follow logs in real-time
- `python scripts/manage_server.py logs --error` - Show error logs
- `python scripts/manage_server.py --help` - Show all available options

### Server Management Features

- **Background process management** with PID file tracking
- **Graceful shutdown** handling (SIGTERM → SIGKILL if needed)
- **Automatic log redirection** to `logs/marketbridge.log` and `logs/marketbridge_error.log`
- **Colorized CLI output** for better user experience
- **Process monitoring** with memory usage and status information

## Logging Standards

All code should implement comprehensive logging with the following requirements:

- **Severity levels** - Use appropriate levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **File location** - Include `__name__` or explicit file path in logger configuration
- **Line numbers** - Use `%(lineno)d` in formatter to capture line numbers
- **Operation context** - Log the operation being performed with descriptive messages
- **Variable tracking** - Include relevant variable names and their values in log messages

### Example Logging Configuration

```python
import logging

# Configure logger with comprehensive formatting
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
)
logger = logging.getLogger(__name__)

# Example usage
def process_data(data_id, data_content):
    logger.info(f"Starting data processing - data_id: {data_id}, content_length: {len(data_content)}")
    try:
        # Process data
        result = transform_data(data_content)
        logger.debug(f"Data transformation successful - result_type: {type(result)}, result_size: {len(result)}")
        return result
    except Exception as e:
        logger.error(f"Data processing failed - data_id: {data_id}, error: {str(e)}", exc_info=True)
        raise
```

## Quality Gates

Every commit must pass:

1. Code formatting (Black)
1. Linting checks (Flake8)
1. Markdown formatting (mdformat)
1. All tests passing
1. Minimum 80% code coverage
1. No trailing whitespace
1. Proper file endings
1. Valid YAML syntax

This template ensures that code quality, testing, and documentation standards are maintained throughout the development lifecycle.
