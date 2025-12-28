#!/bin/bash
# run-backend.sh - Run LocalFlow Python backend server
#
# This script runs the Python backend server with proper working directory

set -e

# Get the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting LocalFlow Backend Server${NC}"
echo ""

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: uv not found. Please install uv.${NC}"
    echo "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check if backend directory exists
if [ ! -d "${BACKEND_DIR}" ]; then
    echo -e "${RED}Error: Backend directory not found at ${BACKEND_DIR}${NC}"
    exit 1
fi

# Check if main.py exists
if [ ! -f "${BACKEND_DIR}/main.py" ]; then
    echo -e "${RED}Error: main.py not found in ${BACKEND_DIR}${NC}"
    exit 1
fi

# Change to backend directory and run the server
cd "${BACKEND_DIR}"

echo "Running backend server from: ${BACKEND_DIR}"
echo "Server will be available at http://127.0.0.1:8000"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

# Run the server
uv run python main.py --server --host 127.0.0.1 --port 8000

