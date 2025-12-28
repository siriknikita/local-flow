//
//  DataModels.swift
//  LocalFlowApp
//
//  Data models for API responses
//

import Foundation

// MARK: - API Response

struct APIResponse: Codable {
    let success: Bool
    let error: String?
}

// MARK: - Status

struct StatusResponse: Codable {
    let isRecording: Bool
    let modelLoaded: String?
    let vadEnabled: Bool
    
    enum CodingKeys: String, CodingKey {
        case isRecording = "is_recording"
        case modelLoaded = "model_loaded"
        case vadEnabled = "vad_enabled"
    }
}

// MARK: - Configuration

struct ConfigResponse: Codable {
    let hotkey: HotkeyConfig?
    let model: String
    let mode: String
    let vadEnabled: Bool?
    let audio: AudioConfig?
    
    enum CodingKeys: String, CodingKey {
        case hotkey, model, mode
        case vadEnabled = "vad_enabled"
        case audio
    }
}

struct HotkeyConfig: Codable {
    let modifiers: [String]
    let key: String
}

struct AudioConfig: Codable {
    let microphoneDevice: Int?
    let systemAudioDevice: Int?
    let mixAudio: Bool?
    let autoDetectDevices: Bool?
    
    enum CodingKeys: String, CodingKey {
        case microphoneDevice = "microphone_device"
        case systemAudioDevice = "system_audio_device"
        case mixAudio = "mix_audio"
        case autoDetectDevices = "auto_detect_devices"
    }
}

struct ConfigUpdate: Codable {
    var hotkey: HotkeyConfig?
    var mode: String?
    var model: String?
    var vadEnabled: Bool?
    var audio: AudioConfig?
    
    enum CodingKeys: String, CodingKey {
        case hotkey, mode, model, audio
        case vadEnabled = "vad_enabled"
    }
}

// MARK: - Models

struct ModelsResponse: Codable {
    let success: Bool
    let models: [String: ModelInfo]
    let activeModel: String
    let error: String?
}

struct ModelInfo: Codable {
    let downloaded: Bool
    let path: String?
    let size: Int64?
}

struct ModelDownloadProgress: Equatable {
    let variant: String
    let progress: Double
}

