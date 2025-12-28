//
//  BackendServerManager.swift
//  LocalFlowApp
//
//  Manages the Python backend server process
//

import Foundation
import AppKit

class BackendServerManager: ObservableObject {
    @Published var isServerRunning = false
    @Published var autoStartEnabled = false
    
    private var serverProcess: Process?
    private var serverMonitorTask: Task<Void, Never>?
    private let notificationService = NotificationService.shared
    
    // Common paths for uv executable
    private let uvPaths = [
        "/opt/homebrew/bin/uv",
        "/usr/local/bin/uv",
        "~/.local/bin/uv",
        "~/.cargo/bin/uv"
    ]
    
    // Default project directory (can be overridden)
    private var projectDirectory: String?
    
    init() {
        // Try to detect project directory from bundle
        if let bundlePath = Bundle.main.bundlePath as String? {
            // If running from built app, look for project directory
            // For development, use current working directory
            let fileManager = FileManager.default
            let currentDir = fileManager.currentDirectoryPath
            
            // Check if we're in a LocalFlow project directory
            if fileManager.fileExists(atPath: "\(currentDir)/backend/main.py") &&
               fileManager.fileExists(atPath: "\(currentDir)/backend/server.py") {
                projectDirectory = currentDir
            } else {
                // Try to find project directory relative to bundle
                // For built apps, project might be in Resources/Python
                if let resourcesPath = Bundle.main.resourcePath {
                    let pythonPath = "\(resourcesPath)/Python"
                    if fileManager.fileExists(atPath: "\(pythonPath)/server.py") {
                        projectDirectory = pythonPath
                    }
                }
            }
        }
        
        // Load auto-start preference
        loadAutoStartPreference()
    }
    
    private func loadAutoStartPreference() {
        // Load from UserDefaults
        autoStartEnabled = UserDefaults.standard.bool(forKey: "autoStartBackendServer")
    }
    
    func setAutoStart(_ enabled: Bool) {
        autoStartEnabled = enabled
        UserDefaults.standard.set(enabled, forKey: "autoStartBackendServer")
        
        if enabled && !isServerRunning {
            startServer()
        } else if !enabled && isServerRunning {
            // Don't stop server if auto-start is disabled
            // User can manually stop it if needed
        }
    }
    
    func setProjectDirectory(_ path: String) {
        projectDirectory = path
        UserDefaults.standard.set(path, forKey: "backendServerPath")
    }
    
    func getProjectDirectory() -> String? {
        if let saved = UserDefaults.standard.string(forKey: "backendServerPath"), !saved.isEmpty {
            return saved
        }
        return projectDirectory
    }
    
    private func findUvExecutable() -> String? {
        let fileManager = FileManager.default
        
        // Check common paths
        for path in uvPaths {
            let expandedPath = (path as NSString).expandingTildeInPath
            if fileManager.fileExists(atPath: expandedPath) {
                return expandedPath
            }
        }
        
        // Try to find uv in PATH
        let process = Process()
        process.launchPath = "/usr/bin/which"
        process.arguments = ["uv"]
        
        let pipe = Pipe()
        process.standardOutput = pipe
        
        do {
            try process.run()
            process.waitUntilExit()
            
            if process.terminationStatus == 0 {
                let data = pipe.fileHandleForReading.readDataToEndOfFile()
                if let path = String(data: data, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines),
                   !path.isEmpty {
                    return path
                }
            }
        } catch {
            // Ignore errors
        }
        
        return nil
    }
    
    func startServer() -> Bool {
        guard !isServerRunning else {
            return true
        }
        
        guard let uvPath = findUvExecutable() else {
            print("Error: Could not find uv executable")
            showErrorAlert(
                title: "Cannot Start Server",
                message: "Could not find 'uv' executable. Please install uv or specify the path in preferences."
            )
            return false
        }
        
        guard let projectDir = getProjectDirectory() else {
            print("Error: Could not determine project directory")
            showErrorAlert(
                title: "Cannot Start Server",
                message: "Could not determine project directory. Please specify it in preferences."
            )
            return false
        }
        
        let fileManager = FileManager.default
        
        // Determine backend directory
        let backendDir: String
        if projectDir.hasSuffix("/backend") {
            backendDir = projectDir
        } else {
            backendDir = "\(projectDir)/backend"
        }
        
        guard fileManager.fileExists(atPath: "\(backendDir)/main.py") else {
            print("Error: main.py not found in \(backendDir)")
            showErrorAlert(
                title: "Cannot Start Server",
                message: "main.py not found in backend directory: \(backendDir)"
            )
            return false
        }
        
        let process = Process()
        process.executableURL = URL(fileURLWithPath: uvPath)
        process.arguments = ["run", "main.py", "--server"]
        process.currentDirectoryURL = URL(fileURLWithPath: backendDir)
        
        // Set up environment
        var environment = ProcessInfo.processInfo.environment
        // Preserve important environment variables
        process.environment = environment
        
        // Set up output pipes (optional - can be used for logging)
        let outputPipe = Pipe()
        let errorPipe = Pipe()
        process.standardOutput = outputPipe
        process.standardError = errorPipe
        
        // Handle process termination
        process.terminationHandler = { [weak self] process in
            DispatchQueue.main.async {
                self?.isServerRunning = false
                self?.serverProcess = nil
                
                // If auto-start is enabled and process didn't exit cleanly, restart after delay
                if let self = self, self.autoStartEnabled && process.terminationStatus != 0 {
                    print("Server process terminated unexpectedly. Will restart in 5 seconds...")
                    DispatchQueue.main.asyncAfter(deadline: .now() + 5) {
                        if self.autoStartEnabled {
                            _ = self.startServer()
                        }
                    }
                }
            }
        }
        
        do {
            try process.run()
            isServerRunning = true
            serverProcess = process
            
            // Start monitoring task
            startMonitoring()
            
            // Send notification
            notificationService.notifyBackendServerStarted()
            
            print("Backend server started successfully (PID: \(process.processIdentifier))")
            return true
        } catch {
            print("Error starting server: \(error)")
            showErrorAlert(
                title: "Failed to Start Server",
                message: "Error: \(error.localizedDescription)"
            )
            return false
        }
    }
    
    func stopServer() {
        guard let process = serverProcess, isServerRunning else {
            return
        }
        
        process.terminate()
        
        // Wait a bit for graceful shutdown
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
            if self.serverProcess?.isRunning == true {
                // Force kill if still running
                self.serverProcess?.terminate()
            }
        }
        
        isServerRunning = false
        serverProcess = nil
        serverMonitorTask?.cancel()
        serverMonitorTask = nil
        
        notificationService.notifyBackendServerStopped()
    }
    
    private func startMonitoring() {
        serverMonitorTask?.cancel()
        
        serverMonitorTask = Task {
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: 5_000_000_000) // Check every 5 seconds
                
                await MainActor.run {
                    if let process = self.serverProcess {
                        if !process.isRunning {
                            self.isServerRunning = false
                            self.serverProcess = nil
                            
                            // Auto-restart if enabled
                            if self.autoStartEnabled {
                                print("Server process stopped. Restarting...")
                                _ = self.startServer()
                            }
                        }
                    }
                }
            }
        }
    }
    
    private func showErrorAlert(title: String, message: String) {
        DispatchQueue.main.async {
            let alert = NSAlert()
            alert.messageText = title
            alert.informativeText = message
            alert.alertStyle = .warning
            alert.addButton(withTitle: "OK")
            alert.runModal()
        }
    }
    
    func checkServerStatus() -> Bool {
        // Simple check: try to connect to the server
        // This is a quick check, actual connection is handled by BackendService
        return isServerRunning && serverProcess?.isRunning == true
    }
}

