#!/bin/bash
# Test runner script for UniFi People Pointer

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}UniFi People Pointer Test Suite${NC}"
echo "================================="
echo

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}Error: pytest is not installed${NC}"
    echo "Install test dependencies with: pip install -r requirements-test.txt"
    exit 1
fi

# Parse arguments
RUN_UNIT=false
RUN_INTEGRATION=false
RUN_EDGE_CASE=false
RUN_ALL=true
VERBOSE=false
COVERAGE=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --unit)
            RUN_UNIT=true
            RUN_ALL=false
            shift
            ;;
        --integration)
            RUN_INTEGRATION=true
            RUN_ALL=false
            shift
            ;;
        --edge-case)
            RUN_EDGE_CASE=true
            RUN_ALL=false
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --no-cov)
            COVERAGE=false
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo
            echo "Options:"
            echo "  --unit           Run only unit tests"
            echo "  --integration    Run only integration tests"
            echo "  --edge-case      Run only edge case tests"
            echo "  --verbose, -v    Verbose output"
            echo "  --no-cov         Skip coverage report"
            echo "  --help, -h       Show this help message"
            echo
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Build pytest command
PYTEST_CMD="pytest"

if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=custom_components.unifi_people_pointer --cov-report=term-missing --cov-report=html"
fi

# Add markers based on what to run
if [ "$RUN_ALL" = true ]; then
    echo -e "${YELLOW}Running all tests...${NC}"
elif [ "$RUN_UNIT" = true ]; then
    echo -e "${YELLOW}Running unit tests...${NC}"
    PYTEST_CMD="$PYTEST_CMD -m unit"
elif [ "$RUN_INTEGRATION" = true ]; then
    echo -e "${YELLOW}Running integration tests...${NC}"
    PYTEST_CMD="$PYTEST_CMD -m integration"
elif [ "$RUN_EDGE_CASE" = true ]; then
    echo -e "${YELLOW}Running edge case tests...${NC}"
    PYTEST_CMD="$PYTEST_CMD -m edge_case"
fi

echo

# Run tests
if $PYTEST_CMD; then
    echo
    echo -e "${GREEN}✓ All tests passed!${NC}"
    
    if [ "$COVERAGE" = true ]; then
        echo
        echo -e "${GREEN}Coverage report generated at htmlcov/index.html${NC}"
    fi
    
    exit 0
else
    echo
    echo -e "${RED}✗ Tests failed${NC}"
    exit 1
fi
