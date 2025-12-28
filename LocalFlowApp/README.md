# LocalFlow SwiftUI App

Native macOS SwiftUI application for LocalFlow.

## Building

### Option 1: Using the build script (Recommended)

From the project root:
```bash
./build.sh
```

This will:
- Build the SwiftUI app
- Create a `.app` bundle
- Bundle the Python backend

### Option 2: Using Xcode

1. **Generate Xcode project** (if xcodegen is installed):
   ```bash
   cd LocalFlowApp
   xcodegen generate
   ```

2. **Or create manually:**
   - Open Xcode
   - Create a new macOS App project
   - Name it "LocalFlow"
   - Copy all Swift files from `LocalFlowApp/` into the project
   - Add `Info.plist` and `LocalFlowApp.entitlements` to the project
   - Build and run

### Option 3: Using Swift Package Manager

The `Package.swift` file is provided for Swift Package Manager support, but for a full macOS app with menubar integration, an Xcode project is recommended.

## Running

1. **Start the Python backend server:**
   ```bash
   cd ..
   uv run python main.py --server
   ```

2. **Run the SwiftUI app:**
   ```bash
   open build/LocalFlow.app
   ```

Or build and run from Xcode directly.

## Project Structure

```
LocalFlowApp/
├── LocalFlowApp/
│   ├── LocalFlowApp.swift      # Main app entry
│   ├── Views/                   # SwiftUI views
│   ├── Services/                # Backend communication
│   ├── Models/                  # Data models
│   └── Info.plist              # App configuration
├── LocalFlowApp.entitlements   # App entitlements
├── project.yml                  # xcodegen configuration
└── Package.swift               # Swift Package Manager config
```

## Requirements

- macOS 13.0+
- Xcode 15.0+ (for building)
- Python backend server running on `http://127.0.0.1:8000`

