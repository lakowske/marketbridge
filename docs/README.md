# MarketBridge Documentation

Welcome to the MarketBridge documentation directory. This contains comprehensive guides for all MarketBridge features and components.

## 📚 Documentation Index

### Core Features

- **[Browser Sessions](./BROWSER_SESSIONS.md)** - Persistent browser automation with Playwright integration
  - Browser-bunny inspired architecture
  - Session management and persistence
  - MarketBridge-specific automation
  - RESTful API for browser control

### Getting Started

1. **Installation**: Follow the setup instructions in the main README.md
1. **Quick Start**: See individual feature documentation for quick start guides
1. **Examples**: Check the `examples/` directory for working code samples

### Architecture Overview

MarketBridge consists of several key components:

```
┌─────────────────┐    WebSocket     ┌──────────────────┐    IB API       ┌─────────────────┐
│   Web Client    │◀──────────────▶│   MarketBridge   │◀───────────────▶│  Interactive    │
│   (Browser)     │                │     Server       │                 │   Brokers       │
└─────────────────┘                └──────────────────┘                 └─────────────────┘
         │                                    │                                    │
         ▼                                    ▼                                    ▼
┌─────────────────┐                ┌──────────────────┐                 ┌─────────────────┐
│ Browser Session │                │   Data Bridge    │                 │  Market Data &  │
│   Automation    │                │   & WebSocket    │                 │   Order APIs    │
└─────────────────┘                └──────────────────┘                 └─────────────────┘
```

### Additional Resources

- **API Reference**: See individual component documentation
- **Troubleshooting**: Common issues and solutions in each guide
- **Examples**: Working code samples in the `examples/` directory
- **Scripts**: Utility scripts in the `scripts/` directory

## 🔧 Development

### Code Quality

MarketBridge follows clean code practices:

- Comprehensive logging with file/line information
- 80% minimum test coverage
- Automated formatting (Black) and linting (Flake8)
- Pre-commit hooks for quality assurance

### Testing

```bash
# Run tests with coverage
pytest --cov=. --cov-report=term-missing --cov-fail-under=80 --cov-report=html

# Run specific test types
pytest tests/unit/
pytest tests/integration/
```

### Contributing

1. Follow the existing code style and logging patterns
1. Add comprehensive tests for new features
1. Update documentation for any API changes
1. Ensure all quality gates pass before submitting

## 📞 Support

- **Issues**: Report bugs and feature requests via GitHub issues
- **Examples**: Check the `examples/` directory for working code
- **Logs**: Server logs are in the `logs/` directory
- **Configuration**: See individual component documentation for config options

______________________________________________________________________

*This documentation is automatically updated with each release.*
