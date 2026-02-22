import Foundation

// MARK: - Network Errors

enum NetworkError: LocalizedError {
    case invalidURL
    case noData
    case timedOut
    case noInternet
    case serverUnreachable
    case serverError(String)
    case decodingError(String)
    
    var errorDescription: String? {
        switch self {
        case .invalidURL: return "The connection URL is invalid."
        case .noData: return "No data was received from the server."
        case .timedOut: return "The request timed out. Please try again."
        case .noInternet: return "You appear to be offline. Please check your connection."
        case .serverUnreachable: return "The SecurePay server is currently unreachable."
        case .serverError(let msg): return msg
        case .decodingError(let msg): return "Data parsing failed: \(msg)"
        }
    }
}

// MARK: - Network Manager (Embedded Mode — No Server Required)

@MainActor
class NetworkManager: ObservableObject {
    
    static let shared = NetworkManager()
    private let backend = EmbeddedBackend.shared
    
    // MARK: - Device ID
    
    static func getDeviceId() -> String {
        let key = "securepay_device_id"
        if let existing = UserDefaults.standard.string(forKey: key) {
            return existing
        }
        let newId = "ios_device_\(Int(Date().timeIntervalSince1970))_\(UUID().uuidString.prefix(9))"
        UserDefaults.standard.set(newId, forKey: key)
        return newId
    }
    
    // MARK: - Initiate Payment (On-Device)
    
    func initiatePayment(request: InitiatePaymentRequest) async throws -> PaymentInitiateResult {
        return try await backend.initiatePayment(request: request)
    }
    
    // MARK: - Upload Liveness Video (On-Device)
    
    func uploadLivenessVideo(challengeId: String, videoURL: URL) async throws -> VerificationResponse {
        return try await backend.uploadLivenessVideo(challengeId: challengeId, videoURL: videoURL)
    }
    
    // MARK: - Get Challenges (On-Device)
    
    func getChallenges() async throws -> [Challenge] {
        return backend.getChallenges()
    }
    
    // MARK: - Get Challenge Detail (stub)
    
    func getChallengeDetail(id: String) async throws -> ChallengeDetail {
        // For embedded mode, return a minimal detail
        throw NetworkError.serverError("Detail view not available in embedded mode")
    }
}

// MARK: - Payment Result Enum

enum PaymentInitiateResult {
    case approved(ApprovedPaymentResponse)
    case challengeRequired(ChallengeRequiredResponse)
}
