# UniFi People Pointer - Test Suite

Comprehensive test suite for the UniFi People Pointer Home Assistant integration.

## Test Structure

```
tests/
├── conftest.py                      # Shared fixtures and test configuration
├── unit/                            # Unit tests (fast, isolated)
│   ├── test_config_flow.py         # Configuration flow tests
│   ├── test_api_parser.py          # API response parsing tests
│   ├── test_device_matcher.py      # Device matching logic tests
│   └── test_data_loading.py        # Data file loading/validation tests
└── integration/                     # Integration tests (slower, E2E)
    ├── test_fallback_logic.py       # Fallback mechanisms tests
    ├── test_edge_cases.py           # Edge case scenarios
    └── test_presence_tracking.py    # Presence detection tests
```

## Test Coverage

### Unit Tests

#### Config Flow (`test_config_flow.py`)
- ✅ User form display
- ✅ Valid input handling
- ✅ Invalid host validation
- ✅ Connection errors
- ✅ Invalid authentication
- ✅ Request timeouts
- ✅ Duplicate entry prevention
- ✅ Options flow
- ✅ Reauthentication flow

#### API Parser (`test_api_parser.py`)
- ✅ Valid client response parsing
- ✅ Empty response handling
- ✅ Malformed response handling
- ✅ Missing hostname handling
- ✅ MAC address normalization
- ✅ OUI prefix extraction
- ✅ Wired vs wireless filtering
- ✅ Last seen timestamp validation
- ✅ Signal strength categorization
- ✅ Unicode hostname support
- ✅ API error response parsing
- ✅ Sites response parsing
- ✅ Duplicate MAC deduplication
- ✅ Channel/band detection
- ✅ Private MAC detection

#### Device Matcher (`test_device_matcher.py`)
- ✅ Exact MAC matching
- ✅ Hostname matching
- ✅ Case-insensitive hostname matching
- ✅ Unknown device handling
- ✅ Tracked vs untracked devices
- ✅ Null hostname handling
- ✅ Multiple hostname patterns
- ✅ Partial hostname matching
- ✅ MAC priority over hostname
- ✅ OUI manufacturer hints

#### Data Loading (`test_data_loading.py`)
- ✅ Valid data file loading
- ✅ Missing file handling
- ✅ Malformed JSON handling
- ✅ Device schema validation
- ✅ MAC format validation
- ✅ People schema validation
- ✅ HA person entity format validation
- ✅ Device ID reference validation
- ✅ OUI format validation
- ✅ Version compatibility checking
- ✅ Data file reloading

### Integration Tests

#### Fallback Logic (`test_fallback_logic.py`)
- ✅ Cached state fallback
- ✅ Cache expiry
- ✅ SSH + MongoDB fallback
- ✅ Combined fallback failure
- ✅ Last known good state
- ✅ Graceful degradation
- ✅ Retry logic with exponential backoff
- ✅ Circuit breaker pattern
- ✅ State persistence across restarts
- ✅ Mixed data sources

#### Edge Cases (`test_edge_cases.py`)

**UniFi Down Scenarios:**
- ✅ Controller completely offline
- ✅ Network unreachable
- ✅ API timeout
- ✅ Controller restarting
- ✅ Firmware upgrade downtime

**Flapping WiFi:**
- ✅ Rapid connect/disconnect detection
- ✅ Poor signal flapping
- ✅ State change dampening
- ✅ Roaming between APs
- ✅ Channel hopping

**Unknown MACs:**
- ✅ Unrecognized MAC handling
- ✅ Unknown MAC logging
- ✅ Manufacturer hint lookup
- ✅ Known OUI but unknown device
- ✅ Guest network filtering
- ✅ IoT device handling

**Duplicate MACs:**
- ✅ Duplicates on different APs
- ✅ Keep most recent entry
- ✅ Keep strongest signal
- ✅ API bug duplicates
- ✅ Private address rotation
- ✅ Multiple VLANs

#### Presence Tracking (`test_presence_tracking.py`)
- ✅ Single device presence
- ✅ No devices (away)
- ✅ Multiple devices (any online = home)
- ✅ All devices online
- ✅ Untracked device filtering
- ✅ Entity state updates
- ✅ Home to away transition
- ✅ Away to home transition
- ✅ Hostname-only matching
- ✅ Multiple people home
- ✅ Presence attributes
- ✅ History tracking
- ✅ Confidence scoring

## Running Tests

### Install Test Dependencies

```bash
pip install -r requirements-test.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest -m unit

# Integration tests only
pytest -m integration

# Edge case tests only
pytest -m edge_case

# Slow tests excluded
pytest -m "not slow"
```

### Run Specific Test Files

```bash
# Config flow tests
pytest tests/unit/test_config_flow.py

# Edge cases
pytest tests/integration/test_edge_cases.py

# Specific test class
pytest tests/unit/test_api_parser.py::TestAPIParser

# Specific test function
pytest tests/unit/test_api_parser.py::TestAPIParser::test_parse_valid_client_response
```

### Coverage Report

```bash
# Generate HTML coverage report
pytest --cov=custom_components.unifi_people_pointer --cov-report=html

# View report
open htmlcov/index.html
```

### Verbose Output

```bash
pytest -v
```

### Show Print Statements

```bash
pytest -s
```

## Test Data

Test fixtures are defined in `conftest.py` and include:

- **manufacturers_data**: Sample OUI prefixes for Apple, Samsung, Google
- **devices_data**: Sample device configurations matching real devices
- **people_data**: Sample person-to-device mappings
- **mock_unifi_api_clients_online**: Simulated online clients
- **mock_unifi_api_clients_flapping**: Flapping connection simulation
- **mock_unifi_api_unknown_macs**: Unknown MAC addresses
- **mock_unifi_api_duplicate_macs**: Duplicate MAC scenarios
- **mock_unifi_api_empty**: Empty API response

## Continuous Integration

Tests should be run in CI on:
- Pull requests
- Commits to main branch
- Before releases

Recommended CI command:
```bash
pytest --cov=custom_components.unifi_people_pointer --cov-fail-under=80 -m "not slow"
```

## Test Philosophy

- **Unit tests**: Fast, isolated, test single functions/classes
- **Integration tests**: Test component interactions, may use mocks for external APIs
- **Edge case tests**: Specifically test error conditions and unusual scenarios
- **No external dependencies**: All tests use mocks/fixtures, no real UniFi controller required

## Adding New Tests

When adding new functionality:

1. Write unit tests for new functions/classes
2. Write integration tests for new workflows
3. Add edge case tests for error scenarios
4. Update this README with new test descriptions
5. Ensure coverage remains >80%

## Test Maintenance

- Review and update fixtures when data schemas change
- Add new edge cases as bugs are discovered
- Keep tests fast - mock external I/O
- Use descriptive test names that explain what is being tested
