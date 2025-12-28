//
//  LocalFlowApp.swift
//  LocalFlowApp
//
//  Created for LocalFlow SwiftUI app
//

import SwiftUI
import AppKit

@main
struct LocalFlowApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    
    var body: some Scene {
        Settings {
            EmptyView()
        }
    }
}

class AppDelegate: NSObject, NSApplicationDelegate {
    private var statusItem: NSStatusItem?
    private let appState = AppState()
    private let backendService = BackendService()
    private let websocketService = WebSocketService()
    private let notificationService = NotificationService.shared
    private let serverManager = BackendServerManager()
    private var isBackendConnected = false
    private var isCheckingConnection = false
    private var showAlertOnFailure = false  // Only show alert on explicit user action
    
    func applicationDidFinishLaunching(_ notification: Notification) {
        // Setup menubar first (so icon is always visible)
        setupMenubar()
        
        // Use regular activation policy for normal window management
        // LSUIElement in Info.plist still hides the dock icon
        NSApp.setActivationPolicy(.regular)
        
        // Request notification permissions (shows standard macOS system dialog)
        Task {
            // Request permissions - this will show the system permission dialog on first launch
            _ = await notificationService.requestAuthorization()
            
            // Wait a moment to ensure app is fully initialized before showing notification
            try? await Task.sleep(nanoseconds: 1_500_000_000) // 1.5 seconds
            
            // Always send notification that app is ready, regardless of permission status
            // The system will handle whether to display it based on permission status
            await MainActor.run {
                notificationService.notifyAppReady()
            }
        }
        
        // Connect to backend
        backendService.baseURL = "http://127.0.0.1:8000"
        
        // Try to detect project directory
        let fileManager = FileManager.default
        let currentDir = fileManager.currentDirectoryPath
        if fileManager.fileExists(atPath: "\(currentDir)/main.py") {
            serverManager.setProjectDirectory(currentDir)
        }
        
        // Auto-start server if enabled
        if serverManager.autoStartEnabled {
            _ = serverManager.startServer()
            // Wait a moment for server to start before checking connection
            Task {
                try? await Task.sleep(nanoseconds: 2_000_000_000) // 2 seconds
                checkBackendConnection(showAlert: false)
            }
        } else {
            // Check backend connection on startup (with retry, no alert)
            checkBackendConnection(showAlert: false)
        }
        
        // Periodically check backend connection (every 30 seconds)
        startPeriodicBackendCheck()
        
        // Observe connection state changes
        observeConnectionState()
        
        // Attempt WebSocket connection (will retry automatically if fails)
        websocketService.connect(url: URL(string: "ws://127.0.0.1:8000/ws")!)
        
        // Automatically show Preferences window after app initialization
        Task {
            // Wait a moment to ensure app is fully initialized before showing window
            try? await Task.sleep(nanoseconds: 2_000_000_000) // 2 seconds
            
            await MainActor.run {
                showPreferences()
            }
        }
    }
    
    private func startPeriodicBackendCheck() {
        Task {
            while true {
                try? await Task.sleep(nanoseconds: 30_000_000_000) // 30 seconds
                checkBackendConnection()
            }
        }
    }
    
    private func checkBackendConnection(showAlert: Bool = false) {
        guard !isCheckingConnection else { return }
        
        isCheckingConnection = true
        showAlertOnFailure = showAlert
        
        Task {
            let (success, _) = await backendService.getStatusWithRetry()
            
            await MainActor.run {
                let wasConnected = isBackendConnected
                isBackendConnected = success
                isCheckingConnection = false
                
                if success {
                    if !wasConnected {
                        showBackendConnectedNotification()
                    }
                    updateMenuBarTooltip(connected: true)
                } else {
                    if wasConnected {
                        showBackendDisconnectedNotification()
                    } else if showAlertOnFailure {
                        showBackendNotRunningAlert()
                        showAlertOnFailure = false
                    }
                    updateMenuBarTooltip(connected: false)
                }
            }
        }
    }
    
    private func observeConnectionState() {
        // Observe BackendService connection state changes via Combine
        // The connection state is already updated in checkBackendConnection
        // This method is a placeholder for future Combine-based observation if needed
    }
    
    private func showBackendNotRunningAlert() {
        // Send notification
        notificationService.notifyBackendNotRunning()
        
        let alert = NSAlert()
        alert.messageText = "Backend Server Not Running"
        alert.informativeText = """
        LocalFlow requires the Python backend server to be running.
        
        To start the server:
        1. Open Terminal
        2. Navigate to the LocalFlow directory
        3. Run: uv run main.py --server
        
        The app will continue running, but features requiring the backend will be unavailable.
        """
        alert.alertStyle = .warning
        alert.addButton(withTitle: "OK")
        alert.runModal()
    }
    
    private func updateMenuBarTooltip(connected: Bool) {
        if let button = statusItem?.button {
            if connected {
                button.toolTip = "LocalFlow - Backend Connected"
            } else if backendService.connectionState == .connecting {
                button.toolTip = "LocalFlow - Connecting..."
            } else {
                button.toolTip = "LocalFlow - Backend Disconnected"
            }
        }
    }
    
    private func showBackendConnectedNotification() {
        updateMenuBarTooltip(connected: true)
        // Send notification
        notificationService.notifyBackendConnected()
    }
    
    private func showBackendDisconnectedNotification() {
        updateMenuBarTooltip(connected: false)
        // Send notification
        notificationService.notifyBackendDisconnected()
    }
    
    private func setupMenubar() {
        // Always create status item to ensure menu bar icon is visible
        statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
        
        guard let button = statusItem?.button else {
            // Fallback: use text if button creation fails
            statusItem?.title = "🎤"
            statusItem?.toolTip = "LocalFlow"
            return
        }
        
        // Configure icon as template for proper rendering in light/dark mode
        if let icon = NSImage(systemSymbolName: "mic.fill", accessibilityDescription: "LocalFlow") {
            icon.isTemplate = true  // Important for dark mode compatibility
            icon.size = NSSize(width: 18, height: 18)  // Explicit size for menu bar
            
            // Configure button with icon
            button.image = icon
            button.imagePosition = .imageOnly
            button.image?.isTemplate = true  // Ensure template rendering
            
            // Fallback: if icon doesn't render, show text
            button.title = ""
        } else {
            // Fallback: use text if SF Symbol fails to load
            button.title = "🎤"
            button.image = nil
        }
        
        button.action = #selector(showMenu)
        button.target = self
        button.toolTip = "LocalFlow"
        
        // Ensure button is always visible and enabled
        button.appearsDisabled = false
        button.isEnabled = true
        
        // Force button to be visible
        button.isHidden = false
    }
    
    @objc private func showMenu() {
        guard let statusBarItem = statusItem else { return }
        
        let menu = NSMenu()
        
        // Backend connection status
        let statusTitle: String
        if isCheckingConnection || backendService.connectionState == .connecting {
            statusTitle = "⟳ Connecting..."
        } else if isBackendConnected {
            statusTitle = "✓ Backend Connected"
        } else {
            statusTitle = "✗ Backend Disconnected"
        }
        
        let statusMenuItem = NSMenuItem(
            title: statusTitle,
            action: nil,
            keyEquivalent: ""
        )
        statusMenuItem.isEnabled = false
        menu.addItem(statusMenuItem)
        
        if !isBackendConnected {
            let reconnectItem = NSMenuItem(
                title: "Check Backend Connection",
                action: #selector(checkBackendConnectionMenu),
                keyEquivalent: ""
            )
            reconnectItem.target = self
            menu.addItem(reconnectItem)
        }
        
        // Server control items
        menu.addItem(NSMenuItem.separator())
        
        if serverManager.isServerRunning {
            let stopServerItem = NSMenuItem(
                title: "Stop Backend Server",
                action: #selector(stopBackendServer),
                keyEquivalent: ""
            )
            stopServerItem.target = self
            menu.addItem(stopServerItem)
        } else {
            let startServerItem = NSMenuItem(
                title: "Start Backend Server",
                action: #selector(startBackendServer),
                keyEquivalent: ""
            )
            startServerItem.target = self
            menu.addItem(startServerItem)
        }
        
        menu.addItem(NSMenuItem.separator())
        
        // Start/Stop Recording
        let recordingItem = NSMenuItem(
            title: appState.isRecording ? "Stop Recording" : "Start Recording",
            action: #selector(toggleRecording),
            keyEquivalent: ""
        )
        recordingItem.target = self
        recordingItem.isEnabled = isBackendConnected
        menu.addItem(recordingItem)
        
        menu.addItem(NSMenuItem.separator())
        
        // Preferences (always enabled so users can configure auto-start)
        let preferencesItem = NSMenuItem(
            title: "Preferences...",
            action: #selector(showPreferences),
            keyEquivalent: ","
        )
        preferencesItem.target = self
        preferencesItem.isEnabled = true
        menu.addItem(preferencesItem)
        
        // Model Manager
        let modelManagerItem = NSMenuItem(
            title: "Model Manager...",
            action: #selector(showModelManager),
            keyEquivalent: ""
        )
        modelManagerItem.target = self
        modelManagerItem.isEnabled = isBackendConnected
        menu.addItem(modelManagerItem)
        
        menu.addItem(NSMenuItem.separator())
        
        // About
        let aboutItem = NSMenuItem(
            title: "About LocalFlow",
            action: #selector(showAbout),
            keyEquivalent: ""
        )
        aboutItem.target = self
        menu.addItem(aboutItem)
        
        // Quit
        let quitItem = NSMenuItem(
            title: "Quit",
            action: #selector(quitApp),
            keyEquivalent: "q"
        )
        quitItem.target = self
        menu.addItem(quitItem)
        
        statusBarItem.menu = menu
        statusBarItem.button?.performClick(nil)
    }
    
    @objc private func checkBackendConnectionMenu() {
        checkBackendConnection(showAlert: true)
    }
    
    @objc private func startBackendServer() {
        let success = serverManager.startServer()
        if success {
            // Wait a moment then check connection
            Task {
                try? await Task.sleep(nanoseconds: 2_000_000_000) // 2 seconds
                checkBackendConnection(showAlert: false)
            }
        }
    }
    
    @objc private func stopBackendServer() {
        serverManager.stopServer()
        // Update connection status
        isBackendConnected = false
        updateMenuBarTooltip(connected: false)
    }
    
    @objc private func toggleRecording() {
        Task {
            if appState.isRecording {
                let success = await backendService.stopRecording()
                if success {
                    await MainActor.run {
                        appState.isRecording = false
                        notificationService.notifyRecordingStopped()
                    }
                }
            } else {
                let success = await backendService.startRecording()
                if success {
                    await MainActor.run {
                        appState.isRecording = true
                        notificationService.notifyRecordingStarted()
                    }
                } else {
                    await MainActor.run {
                        notificationService.notifyRecordingFailed()
                    }
                }
            }
        }
    }
    
    @objc private func showPreferences() {
        // Activate the app to bring windows to front
        NSApp.activate(ignoringOtherApps: true)
        
        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 500, height: 500),
            styleMask: [.titled, .closable, .miniaturizable],
            backing: .buffered,
            defer: false
        )
        window.title = "LocalFlow Preferences"
        window.center()
        window.contentView = NSHostingView(rootView: PreferencesView(serverManager: serverManager))
        window.makeKeyAndOrderFront(nil)
    }
    
    @objc private func showModelManager() {
        // Activate the app to bring windows to front
        NSApp.activate(ignoringOtherApps: true)
        
        let window = NSWindow(
            contentRect: NSRect(x: 0, y: 0, width: 600, height: 500),
            styleMask: [.titled, .closable, .miniaturizable],
            backing: .buffered,
            defer: false
        )
        window.title = "Model Manager"
        window.center()
        window.contentView = NSHostingView(rootView: ModelManagerView())
        window.makeKeyAndOrderFront(nil)
    }
    
    @objc private func showAbout() {
        let alert = NSAlert()
        alert.messageText = "About LocalFlow"
        alert.informativeText = "LocalFlow - AI Dictation for macOS\n\nA local-first dictation application using MLX-Whisper.\nOptimized for Apple Silicon."
        alert.alertStyle = .informational
        alert.runModal()
    }
    
    @objc private func quitApp() {
        NSApplication.shared.terminate(nil)
    }
}

class AppState: ObservableObject {
    @Published var isRecording = false
}

