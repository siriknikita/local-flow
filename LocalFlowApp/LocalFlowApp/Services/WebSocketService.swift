//
//  WebSocketService.swift
//  LocalFlowApp
//
//  WebSocket client for real-time updates
//

import Foundation

class WebSocketService: ObservableObject {
    @Published var isConnected = false
    @Published var waveformData: [Float] = []
    @Published var lastTranscription: String?
    @Published var modelDownloadProgress: ModelDownloadProgress?
    
    private var task: URLSessionWebSocketTask?
    private var url: URL?
    private let notificationService = NotificationService.shared
    private var lastDownloadProgress: [String: Double] = [:] // Track progress per variant
    
    func connect(url: URL) {
        self.url = url
        let session = URLSession(configuration: .default)
        task = session.webSocketTask(with: url)
        task?.resume()
        isConnected = true
        
        // Send notification when connected
        notificationService.notifyWebSocketConnected()
        
        receiveMessage()
    }
    
    func disconnect() {
        task?.cancel(with: .goingAway, reason: nil)
        task = nil
        isConnected = false
        
        // Send notification when disconnected
        notificationService.notifyWebSocketDisconnected()
    }
    
    private func receiveMessage() {
        task?.receive { [weak self] result in
            guard let self = self else { return }
            
            switch result {
            case .success(let message):
                switch message {
                case .string(let text):
                    self.handleMessage(text)
                case .data(let data):
                    if let text = String(data: data, encoding: .utf8) {
                        self.handleMessage(text)
                    }
                @unknown default:
                    break
                }
                
                // Continue receiving
                self.receiveMessage()
                
            case .failure(let error):
                print("WebSocket receive error: \(error)")
                let wasConnected = self.isConnected
                self.isConnected = false
                
                // Send notification if we were connected
                if wasConnected {
                    DispatchQueue.main.async {
                        self.notificationService.notifyWebSocketDisconnected()
                    }
                }
                
                // Attempt to reconnect after delay
                DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                    if let url = self.url {
                        self.connect(url: url)
                    }
                }
            }
        }
    }
    
    private func handleMessage(_ text: String) {
        guard let data = text.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let type = json["type"] as? String else {
            return
        }
        
        switch type {
        case "waveform":
            if let waveformArray = json["data"] as? [Double] {
                DispatchQueue.main.async {
                    self.waveformData = waveformArray.map { Float($0) }
                }
            }
            
        case "transcription":
            if let transcription = json["text"] as? String {
                DispatchQueue.main.async {
                    self.lastTranscription = transcription
                    // Send notification for transcription completion
                    self.notificationService.notifyTranscriptionComplete(text: transcription)
                }
            }
            
        case "model_download_progress":
            if let variant = json["variant"] as? String,
               let progress = json["progress"] as? Double {
                DispatchQueue.main.async {
                    self.modelDownloadProgress = ModelDownloadProgress(variant: variant, progress: progress)
                    
                    // Track progress and send notifications
                    let lastProgress = self.lastDownloadProgress[variant] ?? 0.0
                    
                    // Notify when download starts (first time we see progress > 0)
                    if lastProgress == 0.0 && progress > 0.0 {
                        self.notificationService.notifyModelDownloadStarted(variant: variant)
                    }
                    
                    // Notify on progress milestones
                    self.notificationService.notifyModelDownloadProgress(variant: variant, progress: progress)
                    
                    // Notify when download completes
                    if progress >= 1.0 && lastProgress < 1.0 {
                        self.notificationService.notifyModelDownloadCompleted(variant: variant)
                        self.lastDownloadProgress.removeValue(forKey: variant)
                    } else {
                        self.lastDownloadProgress[variant] = progress
                    }
                }
            }
            
        case "error":
            if let message = json["message"] as? String {
                print("WebSocket error: \(message)")
            }
            
        default:
            break
        }
    }
}

