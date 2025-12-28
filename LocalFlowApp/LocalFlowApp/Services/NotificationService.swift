//
//  NotificationService.swift
//  LocalFlowApp
//
//  Centralized notification service for LocalFlow app events
//

import Foundation
import UserNotifications

class NotificationService {
    static let shared = NotificationService()
    
    private let notificationCenter = UNUserNotificationCenter.current()
    
    private init() {
        setupNotificationCategories()
    }
    
    // MARK: - Permission Request
    
    func requestAuthorization() async -> Bool {
        do {
            let granted = try await notificationCenter.requestAuthorization(options: [.alert, .sound, .badge])
            return granted
        } catch {
            print("Failed to request notification authorization: \(error)")
            return false
        }
    }
    
    // MARK: - Notification Categories
    
    private func setupNotificationCategories() {
        // Define notification categories for future actionable notifications
        let recordingCategory = UNNotificationCategory(
            identifier: "RECORDING",
            actions: [],
            intentIdentifiers: [],
            options: []
        )
        
        let modelCategory = UNNotificationCategory(
            identifier: "MODEL",
            actions: [],
            intentIdentifiers: [],
            options: []
        )
        
        notificationCenter.setNotificationCategories([recordingCategory, modelCategory])
    }
    
    // MARK: - App Lifecycle Notifications
    
    func notifyAppReady() {
        sendNotification(
            identifier: "app_ready",
            title: "LocalFlow Ready",
            body: "LocalFlow is initialized and ready to use.",
            categoryIdentifier: nil
        )
    }
    
    // MARK: - Backend Connection Notifications
    
    func notifyBackendConnected() {
        sendNotification(
            identifier: "backend_connected",
            title: "Backend Connected",
            body: "Successfully connected to LocalFlow backend server.",
            categoryIdentifier: nil
        )
    }
    
    func notifyBackendDisconnected() {
        sendNotification(
            identifier: "backend_disconnected",
            title: "Backend Disconnected",
            body: "Lost connection to LocalFlow backend server. Some features may be unavailable.",
            categoryIdentifier: nil
        )
    }
    
    func notifyBackendNotRunning() {
        sendNotification(
            identifier: "backend_not_running",
            title: "Backend Server Not Running",
            body: "LocalFlow backend server is not running. Please start the server to use all features.",
            categoryIdentifier: nil
        )
    }
    
    func notifyBackendServerStarted() {
        sendNotification(
            identifier: "backend_server_started",
            title: "Backend Server Started",
            body: "LocalFlow backend server has been started successfully.",
            categoryIdentifier: nil
        )
    }
    
    func notifyBackendServerStopped() {
        sendNotification(
            identifier: "backend_server_stopped",
            title: "Backend Server Stopped",
            body: "LocalFlow backend server has been stopped.",
            categoryIdentifier: nil
        )
    }
    
    // MARK: - Recording Notifications
    
    func notifyRecordingStarted() {
        sendNotification(
            identifier: "recording_started",
            title: "Recording Started",
            body: "Audio recording has started. Speak now.",
            categoryIdentifier: "RECORDING"
        )
    }
    
    func notifyRecordingStopped() {
        sendNotification(
            identifier: "recording_stopped",
            title: "Recording Stopped",
            body: "Audio recording has stopped. Processing transcription...",
            categoryIdentifier: "RECORDING"
        )
    }
    
    func notifyRecordingFailed(error: String? = nil) {
        let body = error != nil ? "Failed to start recording: \(error!)" : "Failed to start recording."
        sendNotification(
            identifier: "recording_failed",
            title: "Recording Failed",
            body: body,
            categoryIdentifier: "RECORDING"
        )
    }
    
    // MARK: - Transcription Notifications
    
    func notifyTranscriptionComplete(text: String) {
        // Truncate text if too long for notification
        let preview = text.count > 100 ? String(text.prefix(100)) + "..." : text
        sendNotification(
            identifier: "transcription_complete",
            title: "Transcription Complete",
            body: preview,
            categoryIdentifier: nil
        )
    }
    
    // MARK: - Model Operation Notifications
    
    func notifyModelDownloadStarted(variant: String) {
        sendNotification(
            identifier: "model_download_started",
            title: "Model Download Started",
            body: "Downloading model: \(variant)",
            categoryIdentifier: "MODEL"
        )
    }
    
    func notifyModelDownloadProgress(variant: String, progress: Double) {
        // Only notify at key milestones to avoid spam
        let percentage = Int(progress * 100)
        if percentage % 25 == 0 || percentage == 100 {
            sendNotification(
                identifier: "model_download_progress_\(variant)",
                title: "Model Download Progress",
                body: "\(variant): \(percentage)%",
                categoryIdentifier: "MODEL"
            )
        }
    }
    
    func notifyModelDownloadCompleted(variant: String) {
        sendNotification(
            identifier: "model_download_completed",
            title: "Model Download Complete",
            body: "Model \(variant) has been downloaded successfully.",
            categoryIdentifier: "MODEL"
        )
    }
    
    func notifyModelSwitched(variant: String) {
        sendNotification(
            identifier: "model_switched",
            title: "Model Switched",
            body: "Switched to model: \(variant)",
            categoryIdentifier: "MODEL"
        )
    }
    
    // MARK: - WebSocket Notifications
    
    func notifyWebSocketConnected() {
        sendNotification(
            identifier: "websocket_connected",
            title: "WebSocket Connected",
            body: "Real-time connection established with backend.",
            categoryIdentifier: nil
        )
    }
    
    func notifyWebSocketDisconnected() {
        sendNotification(
            identifier: "websocket_disconnected",
            title: "WebSocket Disconnected",
            body: "Real-time connection lost. Attempting to reconnect...",
            categoryIdentifier: nil
        )
    }
    
    // MARK: - Private Helper
    
    private func sendNotification(
        identifier: String,
        title: String,
        body: String,
        categoryIdentifier: String?
    ) {
        let content = UNMutableNotificationContent()
        content.title = title
        content.body = body
        content.sound = .default
        
        if let categoryIdentifier = categoryIdentifier {
            content.categoryIdentifier = categoryIdentifier
        }
        
        let request = UNNotificationRequest(
            identifier: identifier,
            content: content,
            trigger: nil // Immediate delivery
        )
        
        notificationCenter.add(request) { error in
            if let error = error {
                print("Failed to send notification: \(error)")
            }
        }
    }
}

