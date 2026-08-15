# Contributing to UniFi People Pointer

Thank you for your interest in contributing! 🎉

## How to Contribute

### Reporting Issues

- **Check existing issues** first to avoid duplicates
- **Use a clear title** that describes the problem
- **Include details:**
  - Home Assistant version
  - UniFi Controller model and firmware
  - Integration version
  - Relevant logs (Settings → System → Logs)
  - Configuration snippet (sanitize sensitive data!)

### Suggesting Features

- **Search existing feature requests** first
- **Describe the use case** – why is this feature needed?
- **Provide examples** of how it would work
- **Consider alternatives** you've already explored

### Pull Requests

1. **Fork the repository** and create a branch:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes:**
   - Follow existing code style
   - Add/update tests if applicable
   - Update documentation (README, docs/)
   - Update CHANGELOG.md

3. **Test thoroughly:**
   - Test with your own UniFi setup
   - Check for regressions
   - Validate JSON schemas

4. **Commit with clear messages:**
   ```bash
   git commit -m "feat: add support for multiple UniFi sites"
   git commit -m "fix: handle missing hostname gracefully"
   git commit -m "docs: update configuration examples"
   ```

5. **Push and create PR:**
   ```bash
   git push origin feature/your-feature-name
   ```
   - Use a clear PR title and description
   - Reference related issues (#123)
   - Include testing steps

## Development Setup

### Prerequisites

- Python 3.11+
- Home Assistant development environment
- UniFi Network Controller (for testing)

### Local Development

1. **Clone repository:**
   ```bash
   git clone https://github.com/thelad-dev/unifi-people-pointer.git
   cd unifi-people-pointer
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate  # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements_dev.txt
   ```

4. **Configure `.env`:**
   ```bash
   cp .env.example .env
   # Edit .env with your UniFi API token
   ```

5. **Link to HA config:**
   ```bash
   ln -s $(pwd) /config/custom_components/unifi_people_pointer
   ```

6. **Restart Home Assistant**

### Testing

```bash
# Run tests
pytest

# Check code style
black --check .
flake8 .

# Type checking
mypy .
```

### Documentation

- **Use bilingual format** (German/English) for user-facing docs
- **Update examples** when changing functionality
- **Keep CHANGELOG.md** up to date
- **Test documentation links** before submitting

## Code Style

- **Python:** Follow [PEP 8](https://pep8.org/)
- **Use type hints** where applicable
- **Add docstrings** to functions and classes
- **Keep functions focused** – one responsibility per function
- **JSON:** Use 2-space indentation, trailing commas

## Commit Message Format

Use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation only
- `style:` Code style (formatting, no logic change)
- `refactor:` Code restructuring (no functional change)
- `test:` Adding or updating tests
- `chore:` Maintenance tasks

**Examples:**
```
feat: add zone-based presence detection
fix: handle devices with empty hostname
docs: add troubleshooting section to README
```

## Questions?

Feel free to:
- Open a [Discussion](https://github.com/thelad-dev/unifi-people-pointer/discussions)
- Ask in [Issues](https://github.com/thelad-dev/unifi-people-pointer/issues)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
