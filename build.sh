#!/bin/bash
# build.sh - Build LocalFlow SwiftUI app
#
# This script builds the SwiftUI app and creates a distributable .app bundle

set -e

# Configuration
APP_NAME="LocalFlow"
SCHEME="LocalFlowApp"
CONFIGURATION="${CONFIGURATION:-Release}"  # Release or Debug
OUTPUT_DIR="${OUTPUT_DIR:-build}"
APP_BUNDLE="${OUTPUT_DIR}/${APP_NAME}.app"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SWIFTUI_DIR="${SCRIPT_DIR}/LocalFlowApp"
# Note: Derived data is always cleaned to ensure fresh builds with correct timestamps

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Building LocalFlow SwiftUI App${NC}"
echo "Configuration: ${CONFIGURATION}"
echo "Output directory: ${OUTPUT_DIR}"
echo ""

# Check if Xcode is installed (not just command line tools)
if ! command -v xcodebuild &> /dev/null; then
    echo -e "${RED}Error: xcodebuild not found. Please install Xcode.${NC}"
    exit 1
fi

# Check if full Xcode is installed (not just command line tools)
if [ ! -d "/Applications/Xcode.app" ]; then
    echo -e "${YELLOW}Warning: Full Xcode.app not found. Command line tools may not be sufficient.${NC}"
    echo -e "${YELLOW}Attempting to check xcodebuild availability...${NC}"
    
    # Try to get the developer directory
    DEVELOPER_DIR=$(xcode-select -p 2>/dev/null || echo "")
    if [[ "$DEVELOPER_DIR" == *"CommandLineTools"* ]]; then
        echo -e "${RED}Error: xcodebuild requires full Xcode installation, not just command line tools.${NC}"
        echo -e "${YELLOW}Please install Xcode from the App Store or set the developer directory:${NC}"
        echo -e "${YELLOW}  sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer${NC}"
        exit 1
    fi
fi

# Check if Swift is installed
if ! command -v swift &> /dev/null; then
    echo -e "${RED}Error: Swift not found. Please install Xcode Command Line Tools.${NC}"
    exit 1
fi

# Create output directory
mkdir -p "${OUTPUT_DIR}"

# Stop any running LocalFlow process
echo "Checking for running LocalFlow processes..."
if pgrep -x "${APP_NAME}" > /dev/null; then
    echo -e "${YELLOW}LocalFlow is running. Stopping it...${NC}"
    pkill -x "${APP_NAME}" || true
    # Wait for process to fully terminate
    sleep 2
    # Force kill if still running
    if pgrep -x "${APP_NAME}" > /dev/null; then
        echo -e "${YELLOW}Force killing remaining LocalFlow processes...${NC}"
        pkill -9 -x "${APP_NAME}" || true
        sleep 1
    fi
    echo -e "${GREEN}LocalFlow process stopped.${NC}"
else
    echo "No running LocalFlow process found."
fi
echo ""

# Initialize skip flag
SKIP_XCODEBUILD=false

# Check if we have an Xcode project or need to create one
if [ ! -f "${SWIFTUI_DIR}/${APP_NAME}.xcodeproj/project.pbxproj" ]; then
    echo -e "${YELLOW}No Xcode project found. Creating one...${NC}"
    
    cd "${SWIFTUI_DIR}"
    
    # Try to use xcodegen if available
    if command -v xcodegen &> /dev/null && [ -f "project.yml" ]; then
        echo "Generating Xcode project with xcodegen..."
        xcodegen generate
    else
        echo -e "${YELLOW}xcodegen not found or project.yml missing.${NC}"
        echo "Please either:"
        echo "  1. Install xcodegen: brew install xcodegen"
        echo "  2. Or create the Xcode project manually in Xcode"
        echo ""
        echo "For now, attempting Swift Package Manager build..."
        
        # Fallback to Swift Package Manager
        swift build -c "${CONFIGURATION,,}"  # Convert to lowercase
        
        # Create app bundle structure
        APP_BUNDLE_PATH="${SCRIPT_DIR}/${APP_BUNDLE}"
        mkdir -p "${APP_BUNDLE_PATH}/Contents/MacOS"
        mkdir -p "${APP_BUNDLE_PATH}/Contents/Resources"
        
        # Copy executable
        EXECUTABLE_PATH="${SWIFTUI_DIR}/.build/${CONFIGURATION,,}/LocalFlowApp"
        if [ -f "${EXECUTABLE_PATH}" ]; then
            cp "${EXECUTABLE_PATH}" "${APP_BUNDLE_PATH}/Contents/MacOS/${APP_NAME}"
            chmod +x "${APP_BUNDLE_PATH}/Contents/MacOS/${APP_NAME}"
        else
            echo -e "${RED}Error: Executable not found at ${EXECUTABLE_PATH}${NC}"
            echo -e "${YELLOW}Please create an Xcode project manually or install xcodegen${NC}"
            exit 1
        fi
        
        # Copy Info.plist
        if [ -f "${SWIFTUI_DIR}/LocalFlowApp/Info.plist" ]; then
            cp "${SWIFTUI_DIR}/LocalFlowApp/Info.plist" "${APP_BUNDLE_PATH}/Contents/Info.plist"
        fi
        
        # Copy entitlements
        if [ -f "${SWIFTUI_DIR}/LocalFlowApp.entitlements" ]; then
            cp "${SWIFTUI_DIR}/LocalFlowApp.entitlements" "${APP_BUNDLE_PATH}/Contents/entitlements.plist"
        fi
        
        # Create PkgInfo
        echo "APPL????" > "${APP_BUNDLE_PATH}/Contents/PkgInfo"
        
        cd "${SCRIPT_DIR}"
        # Skip xcodebuild step
        SKIP_XCODEBUILD=true
    fi
    
    cd "${SCRIPT_DIR}"
fi

if [ "${SKIP_XCODEBUILD}" != "true" ]; then
    # Build with xcodebuild
    echo "Building with xcodebuild..."
    cd "${SWIFTUI_DIR}"
    
    # Verify Xcode project exists
    if [ ! -f "${APP_NAME}.xcodeproj/project.pbxproj" ]; then
        echo -e "${RED}Error: Xcode project not found at ${SWIFTUI_DIR}/${APP_NAME}.xcodeproj${NC}"
        exit 1
    fi
    
    # Clean derived data to ensure fresh build (always clean to prevent stale timestamps)
    DERIVED_DATA_PATH="${SCRIPT_DIR}/${OUTPUT_DIR}/DerivedData"
    echo "Cleaning derived data for fresh build..."
    if [ -d "${DERIVED_DATA_PATH}" ]; then
        rm -rf "${DERIVED_DATA_PATH}"
        echo "Derived data removed."
    fi
    
    # Remove old archive and app bundle to ensure fresh build
    ARCHIVE_PATH="${SCRIPT_DIR}/${OUTPUT_DIR}/${APP_NAME}.xcarchive"
    if [ -d "${ARCHIVE_PATH}" ]; then
        echo "Removing old archive..."
        rm -rf "${ARCHIVE_PATH}"
    fi
    if [ -d "${SCRIPT_DIR}/${APP_BUNDLE}" ]; then
        echo "Removing old app bundle..."
        rm -rf "${SCRIPT_DIR}/${APP_BUNDLE}"
    fi
    
    # Clean build to ensure fresh compilation
    echo "Cleaning build artifacts..."
    if ! xcodebuild \
        -scheme "${SCHEME}" \
        -configuration "${CONFIGURATION}" \
        -derivedDataPath "${DERIVED_DATA_PATH}" \
        clean 2>&1; then
        echo -e "${YELLOW}Warning: Clean step failed, continuing with build...${NC}"
    fi
    
    # Build and archive
    echo "Building and archiving..."
    if ! xcodebuild \
        -scheme "${SCHEME}" \
        -configuration "${CONFIGURATION}" \
        -derivedDataPath "${DERIVED_DATA_PATH}" \
        -archivePath "${SCRIPT_DIR}/${OUTPUT_DIR}/${APP_NAME}.xcarchive" \
        -UseModernBuildSystem=YES \
        archive 2>&1; then
        echo -e "${RED}Error: xcodebuild failed.${NC}"
        echo -e "${YELLOW}Make sure:${NC}"
        echo -e "${YELLOW}  1. Xcode is installed (not just command line tools)${NC}"
        echo -e "${YELLOW}  2. Developer directory is set correctly:${NC}"
        echo -e "${YELLOW}     sudo xcode-select --switch /Applications/Xcode.app/Contents/Developer${NC}"
        echo -e "${YELLOW}  3. Xcode license is accepted:${NC}"
        echo -e "${YELLOW}     sudo xcodebuild -license accept${NC}"
        exit 1
    fi
    
    # Extract app from archive
    ARCHIVE_APP_PATH="${SCRIPT_DIR}/${OUTPUT_DIR}/${APP_NAME}.xcarchive/Products/Applications/${APP_NAME}.app"
    if [ -d "${ARCHIVE_APP_PATH}" ]; then
        # Remove old app bundle if it exists
        if [ -d "${SCRIPT_DIR}/${APP_BUNDLE}" ]; then
            rm -rf "${SCRIPT_DIR}/${APP_BUNDLE}"
        fi
        # Copy app bundle (without preserving timestamps)
        cp -R "${ARCHIVE_APP_PATH}" "${SCRIPT_DIR}/${APP_BUNDLE}"
        # Touch the app bundle to ensure current timestamp
        touch "${SCRIPT_DIR}/${APP_BUNDLE}"
    else
        echo -e "${RED}Error: App bundle not found in archive${NC}"
        exit 1
    fi
    
    cd "${SCRIPT_DIR}"
fi

# Copy Python backend files to app bundle
echo "Bundling Python backend..."
PYTHON_DIR="${APP_BUNDLE}/Contents/Resources/Python"
mkdir -p "${PYTHON_DIR}"

# Copy server.py and config files
cp "${SCRIPT_DIR}/server.py" "${PYTHON_DIR}/"
cp "${SCRIPT_DIR}/config.py" "${PYTHON_DIR}/"
if [ -f "${SCRIPT_DIR}/config.json" ]; then
    cp "${SCRIPT_DIR}/config.json" "${PYTHON_DIR}/"
fi

# Copy engine directory
cp -R "${SCRIPT_DIR}/engine" "${PYTHON_DIR}/"

# Create launcher script
cat > "${APP_BUNDLE}/Contents/MacOS/localflow-backend" << 'LAUNCHER_EOF'
#!/bin/bash
# Launcher script for Python backend

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$(dirname "${SCRIPT_DIR}")")"
PYTHON_DIR="${APP_DIR}/Resources/Python"

# Try to find Python with uv
if command -v uv &> /dev/null; then
    cd "${SCRIPT_DIR}/../../.."
    exec uv run python "${PYTHON_DIR}/server.py" --server --host 127.0.0.1 --port 8000
else
    # Fallback to system Python
    exec python3 "${PYTHON_DIR}/server.py" --server --host 127.0.0.1 --port 8000
fi
LAUNCHER_EOF

chmod +x "${APP_BUNDLE}/Contents/MacOS/localflow-backend"

# Code signing (optional - for development)
if [ -n "${CODE_SIGN_IDENTITY}" ]; then
    echo "Code signing app..."
    codesign --force --sign "${CODE_SIGN_IDENTITY}" "${APP_BUNDLE}"
else
    echo -e "${YELLOW}Warning: No CODE_SIGN_IDENTITY set. App will not be signed.${NC}"
    echo "To sign the app, set CODE_SIGN_IDENTITY environment variable:"
    echo "  export CODE_SIGN_IDENTITY='Developer ID Application: Your Name'"
fi

# Replace app in /Applications if it exists
APPLICATIONS_APP="/Applications/${APP_NAME}.app"
if [ -d "${APPLICATIONS_APP}" ]; then
    echo ""
    echo "Replacing existing app in /Applications..."
    # Remove old app
    if rm -rf "${APPLICATIONS_APP}" 2>/dev/null; then
        # Copy new app
        if cp -R "${SCRIPT_DIR}/${APP_BUNDLE}" "${APPLICATIONS_APP}"; then
            echo -e "${GREEN}Successfully replaced ${APPLICATIONS_APP}${NC}"
        else
            echo -e "${RED}Error: Failed to copy app to /Applications${NC}"
            echo -e "${YELLOW}You may need to run with sudo or check permissions.${NC}"
        fi
    else
        echo -e "${RED}Error: Failed to remove old app from /Applications${NC}"
        echo -e "${YELLOW}You may need to run with sudo or check permissions.${NC}"
    fi
else
    echo ""
    echo "No existing app found in /Applications (this is normal if first build)"
fi

echo ""
echo -e "${GREEN}Build complete!${NC}"
echo "App bundle: ${APP_BUNDLE}"
echo ""
echo "To run the app:"
echo "  open ${APP_BUNDLE}"

