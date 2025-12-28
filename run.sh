#!/bin/bash
# run.sh - LocalFlow main menu script
#
# Interactive menu to choose between building the app or running the backend server

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to display menu
show_menu() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║     LocalFlow - Main Menu          ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════╝${NC}"
    echo ""
    echo "What would you like to do?"
    echo ""
    echo "  1) Run the Python backend server"
    echo "  2) Build the application"
    echo "  3) Exit"
    echo ""
    echo -n "Please select an option [1-3]: "
}

# Function to run build script
run_build() {
    echo ""
    echo -e "${GREEN}Building LocalFlow application...${NC}"
    echo ""
    "${SCRIPT_DIR}/scripts/build.sh"
}

# Function to run backend server
run_backend() {
    echo ""
    echo -e "${GREEN}Starting LocalFlow backend server...${NC}"
    echo ""
    "${SCRIPT_DIR}/scripts/run-backend.sh"
}

# Main loop
while true; do
    show_menu
    read -r choice
    
    case $choice in
        1)
            run_backend
            ;;
        2)
            run_build
            ;;
        3)
            echo ""
            echo -e "${GREEN}Goodbye!${NC}"
            exit 0
            ;;
        *)
            echo ""
            echo -e "${RED}Invalid option. Please select 1, 2, or 3.${NC}"
            sleep 1
            ;;
    esac
done

