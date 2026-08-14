# Contributing to UniFi People Pointer

Thank you for your interest in contributing! 🎉

## How to Contribute

### Reporting Bugs

1. Check if the bug is already reported in [Issues](https://github.com/thelad-dev/unifi-people-pointer/issues)
2. If not, create a new issue with:
   - Clear title
   - Steps to reproduce
   - Expected vs actual behavior
   - Your environment (HA version, UniFi controller type, etc.)
   - Relevant logs (from Home Assistant)

### Suggesting Features

1. Check [Discussions](https://github.com/thelad-dev/unifi-people-pointer/discussions) first
2. Open a new Discussion or Issue describing:
   - Use case
   - Why it's needed
   - How it should work

### Code Contributions

#### Setup Development Environment

1. Fork the repository
2. Clone your fork
3. Create a feature branch: `git checkout -b feature/my-feature`

#### For Home Assistant Integration

```bash
# Link to HA config directory for testing
ln -s $(pwd)/custom_components/unifi_people_pointer ~/.homeassistant/custom_components/

# Restart Home Assistant
# Test your changes
```

#### For Backend

```bash
cd backend
npm install
cp .env.example .env
# Edit .env with your settings
npm run dev
```

#### Code Style

- **Python**: Follow PEP 8, use `black` for formatting
- **TypeScript**: Follow ESLint rules
- **Commits**: Use conventional commits (feat:, fix:, docs:, etc.)

#### Testing

- Test manually in Home Assistant
- Verify services work via Developer Tools
- Check logs for errors
- Test with both real and mock UniFi data

#### Pull Request Process

1. Update README.md if needed
2. Update CHANGELOG.md under `[Unreleased]`
3. Ensure your code works with current HA stable
4. Create PR with clear description
5. Link related issues
6. Wait for review

### Documentation

Help improve docs by:
- Fixing typos
- Adding examples
- Translating (we support DE/EN)
- Writing guides

## Development Roadmap

See [Issues](https://github.com/thelad-dev/unifi-people-pointer/issues) for planned features.

**Priority for v1.1.0:**
- Device Tracker platform implementation
- Sensor platform
- Frontend UI

## Questions?

- [GitHub Discussions](https://github.com/thelad-dev/unifi-people-pointer/discussions)
- [Issues](https://github.com/thelad-dev/unifi-people-pointer/issues)

## Code of Conduct

Be respectful, constructive, and helpful. We're all here to make this project better!

## License

By contributing, you agree your contributions will be licensed under the MIT License.

---

Thank you for contributing! 🙏
