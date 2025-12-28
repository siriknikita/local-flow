//
//  PreferencesView.swift
//  LocalFlowApp
//
//  Preferences window with hotkey configuration
//

import SwiftUI
import AppKit

struct PreferencesView: View {
    @StateObject private var backendService = BackendService()
    @ObservedObject var serverManager: BackendServerManager
    @State private var config: ConfigResponse?
    @State private var hotkey: HotkeyConfig?
    @State private var mode: String = "toggle"
    @State private var isRecordingHotkey = false
    @State private var capturedHotkey: HotkeyConfig?
    @State private var isLoading = true
    @State private var autoStartEnabled: Bool = false
    @State private var projectDirectory: String = ""
    
    var body: some View {
        VStack(spacing: 20) {
            if isLoading {
                ProgressView()
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                ScrollView {
                    VStack(alignment: .leading, spacing: 20) {
                        // Title
                        Text("Preferences")
                            .font(.system(size: 24, weight: .bold))
                            .padding(.bottom, 10)
                        
                        // Hotkey section
                        VStack(alignment: .leading, spacing: 10) {
                            Text("Global Hotkey")
                                .font(.system(size: 16, weight: .bold))
                            
                            Text("Current: \(formatHotkey(hotkey))")
                                .font(.system(size: 14))
                                .foregroundColor(.secondary)
                            
                            Button(isRecordingHotkey ? "Press keys now..." : "Listen for Shortcut") {
                                startRecordingHotkey()
                            }
                            .disabled(isRecordingHotkey)
                        }
                        .padding()
                        .background(Color(NSColor.controlBackgroundColor))
                        .cornerRadius(8)
                        
                        // Mode selection
                        VStack(alignment: .leading, spacing: 10) {
                            Text("Recording Mode")
                                .font(.system(size: 16, weight: .bold))
                            
                            Picker("Mode", selection: $mode) {
                                Text("Toggle (Press to start/stop)").tag("toggle")
                                Text("Hold-to-Talk (Hold while speaking)").tag("hold")
                            }
                            .pickerStyle(.radioGroup)
                        }
                        .padding()
                        .background(Color(NSColor.controlBackgroundColor))
                        .cornerRadius(8)
                        
                        // Backend Server section
                        VStack(alignment: .leading, spacing: 10) {
                            Text("Backend Server")
                                .font(.system(size: 16, weight: .bold))
                            
                            Toggle("Auto-start backend server", isOn: $autoStartEnabled)
                                .onChange(of: autoStartEnabled) { newValue in
                                    serverManager.setAutoStart(newValue)
                                }
                            
                            VStack(alignment: .leading, spacing: 5) {
                                Text("Project Directory")
                                    .font(.system(size: 14))
                                    .foregroundColor(.secondary)
                                
                                HStack {
                                    TextField("Project directory path", text: $projectDirectory)
                                        .textFieldStyle(.roundedBorder)
                                    
                                    Button("Browse...") {
                                        selectProjectDirectory()
                                    }
                                }
                                
                                Text("Leave empty to auto-detect")
                                    .font(.system(size: 12))
                                    .foregroundColor(.secondary)
                            }
                            .padding(.top, 5)
                        }
                        .padding()
                        .background(Color(NSColor.controlBackgroundColor))
                        .cornerRadius(8)
                        
                        // Save button
                        Button("Save Preferences") {
                            savePreferences()
                        }
                        .buttonStyle(.borderedProminent)
                        .controlSize(.large)
                    }
                    .padding(20)
                }
            }
        }
        .frame(width: 500, height: 500)
        .onAppear {
            loadConfig()
            loadServerPreferences()
        }
    }
    
    private func loadConfig() {
        Task {
            do {
                let loadedConfig = try await backendService.getConfig()
                await MainActor.run {
                    self.config = loadedConfig
                    self.hotkey = loadedConfig.hotkey
                    self.mode = loadedConfig.mode
                    self.isLoading = false
                }
            } catch {
                print("Error loading config: \(error)")
                await MainActor.run {
                    self.isLoading = false
                }
            }
        }
    }
    
    private func startRecordingHotkey() {
        isRecordingHotkey = true
        // TODO: Implement hotkey capture using NSEvent
        // For now, this is a placeholder
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
            // Simulate capturing a hotkey
            isRecordingHotkey = false
            // In real implementation, capture actual key combination
        }
    }
    
    private func formatHotkey(_ hotkey: HotkeyConfig?) -> String {
        guard let hotkey = hotkey else {
            return "Not set"
        }
        
        let modNames: [String: String] = [
            "cmd": "Cmd",
            "ctrl": "Ctrl",
            "alt": "Opt",
            "shift": "Shift"
        ]
        
        let modStr = hotkey.modifiers.compactMap { modNames[$0] }.joined(separator: "+")
        let keyStr = hotkey.key.capitalized
        
        if !modStr.isEmpty && !keyStr.isEmpty {
            return "\(modStr)+\(keyStr)"
        } else if !keyStr.isEmpty {
            return keyStr
        } else {
            return "Not set"
        }
    }
    
    private func loadServerPreferences() {
        autoStartEnabled = serverManager.autoStartEnabled
        if let dir = serverManager.getProjectDirectory() {
            projectDirectory = dir
        }
    }
    
    private func selectProjectDirectory() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = false
        panel.canChooseDirectories = true
        panel.allowsMultipleSelection = false
        panel.message = "Select LocalFlow project directory"
        
        if panel.runModal() == .OK {
            if let url = panel.url {
                projectDirectory = url.path
                serverManager.setProjectDirectory(url.path)
            }
        }
    }
    
    private func savePreferences() {
        Task {
            var update = ConfigUpdate()
            
            if let captured = capturedHotkey {
                update.hotkey = captured
            } else if let current = hotkey {
                update.hotkey = current
            }
            
            update.mode = mode
            
            // Save server preferences
            serverManager.setAutoStart(autoStartEnabled)
            if !projectDirectory.isEmpty {
                serverManager.setProjectDirectory(projectDirectory)
            }
            
            let success = await backendService.updateConfig(update)
            if success {
                // Show success message
                print("Preferences saved successfully")
            } else {
                print("Failed to save preferences")
            }
        }
    }
}

