//
//  ModelManagerView.swift
//  LocalFlowApp
//
//  Model manager for downloading and switching models
//

import SwiftUI

struct ModelManagerView: View {
    @StateObject private var backendService = BackendService()
    @StateObject private var websocketService = WebSocketService()
    @State private var models: [String: ModelInfo] = [:]
    @State private var activeModel: String = ""
    @State private var isLoading = true
    @State private var downloadingVariants: Set<String> = []
    @State private var downloadProgress: [String: Double] = [:]
    
    var body: some View {
        VStack(spacing: 20) {
            if isLoading {
                ProgressView()
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                ScrollView {
                    VStack(alignment: .leading, spacing: 15) {
                        // Title
                        Text("Whisper Models")
                            .font(.system(size: 24, weight: .bold))
                            .padding(.bottom, 10)
                        
                        // Model list
                        ForEach(Array(models.keys.sorted()), id: \.self) { variant in
                            ModelRowView(
                                variant: variant,
                                modelInfo: models[variant]!,
                                isActive: variant == activeModel,
                                isDownloading: downloadingVariants.contains(variant),
                                downloadProgress: downloadProgress[variant] ?? 0,
                                onDownload: {
                                    downloadModel(variant: variant)
                                },
                                onSwitch: {
                                    switchModel(variant: variant)
                                }
                            )
                        }
                    }
                    .padding(20)
                }
            }
        }
        .frame(width: 600, height: 500)
        .onAppear {
            loadModels()
        }
        .onChange(of: websocketService.modelDownloadProgress) { progress in
            if let progress = progress {
                downloadProgress[progress.variant] = progress.progress
                if progress.progress >= 1.0 {
                    downloadingVariants.remove(progress.variant)
                    downloadProgress.removeValue(forKey: progress.variant)
                    loadModels() // Refresh list
                }
            }
        }
    }
    
    private func loadModels() {
        Task {
            do {
                let response = try await backendService.listModels()
                await MainActor.run {
                    self.models = response.models
                    self.activeModel = response.activeModel
                    self.isLoading = false
                }
            } catch {
                print("Error loading models: \(error)")
                await MainActor.run {
                    self.isLoading = false
                }
            }
        }
    }
    
    private func downloadModel(variant: String) {
        downloadingVariants.insert(variant)
        downloadProgress[variant] = 0.0
        
        Task {
            let success = await backendService.downloadModel(variant: variant)
            await MainActor.run {
                downloadingVariants.remove(variant)
                downloadProgress.removeValue(forKey: variant)
                if success {
                    loadModels() // Refresh list
                }
            }
        }
    }
    
    private func switchModel(variant: String) {
        Task {
            let success = await backendService.switchModel(variant: variant)
            if success {
                await MainActor.run {
                    activeModel = variant
                    loadModels() // Refresh list
                }
            }
        }
    }
}

struct ModelRowView: View {
    let variant: String
    let modelInfo: ModelInfo
    let isActive: Bool
    let isDownloading: Bool
    let downloadProgress: Double
    let onDownload: () -> Void
    let onSwitch: () -> Void
    
    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 5) {
                Text(variant.capitalized)
                    .font(.system(size: 14, weight: .bold))
                
                HStack {
                    if modelInfo.downloaded {
                        Label("Downloaded", systemImage: "checkmark.circle.fill")
                            .foregroundColor(.green)
                            .font(.system(size: 12))
                    } else {
                        Label("Not downloaded", systemImage: "xmark.circle")
                            .foregroundColor(.gray)
                            .font(.system(size: 12))
                    }
                    
                    if isActive {
                        Text("(Active)")
                            .foregroundColor(.blue)
                            .font(.system(size: 12))
                    }
                }
            }
            
            Spacer()
            
            if isDownloading {
                VStack {
                    ProgressView(value: downloadProgress)
                        .frame(width: 150)
                    Text("\(Int(downloadProgress * 100))%")
                        .font(.system(size: 10))
                        .foregroundColor(.secondary)
                }
            } else if modelInfo.downloaded {
                Button(isActive ? "Active" : "Switch") {
                    onSwitch()
                }
                .disabled(isActive)
                .buttonStyle(.bordered)
            } else {
                Button("Download") {
                    onDownload()
                }
                .buttonStyle(.borderedProminent)
            }
        }
        .padding()
        .background(Color(NSColor.controlBackgroundColor))
        .cornerRadius(8)
    }
}

