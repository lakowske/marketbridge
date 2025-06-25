# marketbridge

A Python IB gateway for web browsers and clients to receive market data and place orders

## Features

- Modern Python project structure
- Comprehensive testing with pytest and coverage reporting
- Code quality tools (Black, Flake8, MyPy, Bandit)
- Pre-commit hooks for automated quality checks
- GitHub Actions CI/CD pipeline
- VS Code tasks integration

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Git

### Installation

1. Clone the repository:
```bash
git clone https://github.com/lakowske/marketbridge.git
cd marketbridge
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install the project in development mode:
```bash
pip install -e ".[dev]"
```

4. Install pre-commit hooks:
```bash
pre-commit install
```

## Development

### Running Tests
```bash
# Run tests with coverage
pytest --cov=. --cov-report=term-missing --cov-fail-under=80 --cov-report=html

# Or use VS Code: Ctrl+Shift+P -> "Tasks: Run Task" -> "Run Tests with Coverage"
```

### Code Quality
```bash
# Format code
black .

# Lint code
flake8

# Run all pre-commit checks
pre-commit run --all-files
```

### VS Code Integration

This project includes VS Code tasks for common operations:
- `Ctrl+Shift+P` -> "Tasks: Run Task" to see all available tasks
- Install the "Task Explorer" extension for a better task management experience

## Project Structure

```
marketbridge/
├── src/marketbridge/     # Main package
├── tests/                          # Test suite
├── .github/workflows/              # GitHub Actions
├── .vscode/                        # VS Code configuration
├── pyproject.toml                  # Project configuration
└── README.md                       # This file
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and run the quality checks
4. Commit your changes: `git commit -m 'Add amazing feature'`
5. Push to the branch: `git push origin feature/amazing-feature`
6. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Author

Seth Lakowske - lakowske@gmail.com
