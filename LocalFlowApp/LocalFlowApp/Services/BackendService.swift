//
//  BackendService.swift
//  LocalFlowApp
//
//  HTTP client for LocalFlow API
//

import Foundation

enum BackendConnectionState {
    case connecting
    case connected
    case disconnected
}

struct RetryConfig {
    let maxAttempts: Int
    let initialDelay: TimeInterval
    let delayMultiplier: Double
    
    static let `default` = RetryConfig(maxAttempts: 5, initialDelay: 1.0, delayMultiplier: 2.0)
}

enum BackendError: Error, LocalizedError {
    case invalidURL
    case invalidResponse
    case connectionFailed
    case httpError(statusCode: Int)
    case networkError(URLError)
    case decodingError(DecodingError)
    case unknownError(Error)
    
    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid backend URL"
        case .invalidResponse:
            return "Invalid response from backend"
        case .connectionFailed:
            return "Cannot connect to backend server. Make sure the server is running."
        case .httpError(let code):
            return "HTTP error: \(code)"
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        case .decodingError(let error):
            return "Failed to decode response: \(error.localizedDescription)"
        case .unknownError(let error):
            return "Unknown error: \(error.localizedDescription)"
        }
    }
}

class BackendService: ObservableObject {
    var baseURL: String = "http://127.0.0.1:8000"
    
    private var session: URLSession
    private let notificationService = NotificationService.shared
    private var retryConfig: RetryConfig = .default
    @Published var connectionState: BackendConnectionState = .disconnected
    
    init() {
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 60
        self.session = URLSession(configuration: config)
    }
    
    func setRetryConfig(_ config: RetryConfig) {
        self.retryConfig = config
    }
    
    // MARK: - Status
    
    func getStatusWithRetry() async -> (success: Bool, response: StatusResponse?) {
        await MainActor.run {
            connectionState = .connecting
        }
        
        var delay = retryConfig.initialDelay
        
        for attempt in 1...retryConfig.maxAttempts {
            do {
                let response = try await getStatus()
                await MainActor.run {
                    connectionState = .connected
                }
                return (true, response)
            } catch let error as BackendError {
                // Check if this is a connection error that should be retried
                let shouldRetry: Bool
                switch error {
                case .connectionFailed, .networkError:
                    shouldRetry = true
                default:
                    shouldRetry = false
                }
                
                if !shouldRetry || attempt == retryConfig.maxAttempts {
                    // Non-retryable error or max attempts reached
                    await MainActor.run {
                        connectionState = .disconnected
                    }
                    return (false, nil)
                }
                
                // Wait before retrying with exponential backoff
                try? await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))
                delay *= retryConfig.delayMultiplier
            } catch {
                // Unknown error - don't retry
                await MainActor.run {
                    connectionState = .disconnected
                }
                return (false, nil)
            }
        }
        
        await MainActor.run {
            connectionState = .disconnected
        }
        return (false, nil)
    }
    
    func getStatus() async throws -> StatusResponse {
        guard let url = URL(string: "\(baseURL)/api/status") else {
            throw BackendError.invalidURL
        }
        
        do {
            let (data, response) = try await session.data(from: url)
            
            guard let httpResponse = response as? HTTPURLResponse else {
                throw BackendError.invalidResponse
            }
            
            guard httpResponse.statusCode == 200 else {
                throw BackendError.httpError(statusCode: httpResponse.statusCode)
            }
            
            return try JSONDecoder().decode(StatusResponse.self, from: data)
        } catch let error as DecodingError {
            throw BackendError.decodingError(error)
        } catch let error as URLError {
            if error.code == .cannotConnectToHost || error.code == .networkConnectionLost {
                throw BackendError.connectionFailed
            }
            throw BackendError.networkError(error)
        } catch {
            throw BackendError.unknownError(error)
        }
    }
    
    // MARK: - Recording
    
    func startRecording() async -> Bool {
        do {
            let url = URL(string: "\(baseURL)/api/recording/start")!
            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            
            let (data, response) = try await session.data(for: request)
            
            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 200 else {
                return false
            }
            
            let result = try JSONDecoder().decode(APIResponse.self, from: data)
            return result.success
        } catch {
            print("Error starting recording: \(error)")
            return false
        }
    }
    
    func stopRecording() async -> Bool {
        do {
            let url = URL(string: "\(baseURL)/api/recording/stop")!
            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            
            let (data, response) = try await session.data(for: request)
            
            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 200 else {
                return false
            }
            
            let result = try JSONDecoder().decode(APIResponse.self, from: data)
            return result.success
        } catch {
            print("Error stopping recording: \(error)")
            return false
        }
    }
    
    // MARK: - Configuration
    
    func getConfig() async throws -> ConfigResponse {
        let url = URL(string: "\(baseURL)/api/config")!
        let (data, _) = try await session.data(from: url)
        return try JSONDecoder().decode(ConfigResponse.self, from: data)
    }
    
    func updateConfig(_ config: ConfigUpdate) async -> Bool {
        do {
            let url = URL(string: "\(baseURL)/api/config")!
            var request = URLRequest(url: url)
            request.httpMethod = "PUT"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = try JSONEncoder().encode(config)
            
            let (data, response) = try await session.data(for: request)
            
            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 200 else {
                return false
            }
            
            let result = try JSONDecoder().decode(APIResponse.self, from: data)
            return result.success
        } catch {
            print("Error updating config: \(error)")
            return false
        }
    }
    
    // MARK: - Models
    
    func listModels() async throws -> ModelsResponse {
        let url = URL(string: "\(baseURL)/api/models")!
        let (data, _) = try await session.data(from: url)
        return try JSONDecoder().decode(ModelsResponse.self, from: data)
    }
    
    func downloadModel(variant: String) async -> Bool {
        do {
            let url = URL(string: "\(baseURL)/api/models/download")!
            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            
            struct DownloadRequest: Codable {
                let variant: String
            }
            let body = DownloadRequest(variant: variant)
            request.httpBody = try JSONEncoder().encode(body)
            
            let (data, response) = try await session.data(for: request)
            
            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 200 else {
                return false
            }
            
            let result = try JSONDecoder().decode(APIResponse.self, from: data)
            if result.success {
                // Notification for download started is handled by WebSocketService
                // when it receives the first progress update
            }
            return result.success
        } catch {
            print("Error downloading model: \(error)")
            return false
        }
    }
    
    func switchModel(variant: String) async -> Bool {
        do {
            let url = URL(string: "\(baseURL)/api/models/switch")!
            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            
            struct SwitchRequest: Codable {
                let variant: String
            }
            let body = SwitchRequest(variant: variant)
            request.httpBody = try JSONEncoder().encode(body)
            
            let (data, response) = try await session.data(for: request)
            
            guard let httpResponse = response as? HTTPURLResponse,
                  httpResponse.statusCode == 200 else {
                return false
            }
            
            let result = try JSONDecoder().decode(APIResponse.self, from: data)
            if result.success {
                await MainActor.run {
                    notificationService.notifyModelSwitched(variant: variant)
                }
            }
            return result.success
        } catch {
            print("Error switching model: \(error)")
            return false
        }
    }
}

