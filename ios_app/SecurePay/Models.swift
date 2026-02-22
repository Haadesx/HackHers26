import Foundation

// MARK: - Enums

enum PaymentRail: String, CaseIterable, Codable {
    case bank = "BANK"
    case solana = "SOLANA"
    
    var displayName: String {
        switch self {
        case .bank: return "Bank Transfer"
        case .solana: return "Solana"
        }
    }
    
    var icon: String {
        switch self {
        case .bank: return "🏦"
        case .solana: return "⚡"
        }
    }
    
    var description: String {
        switch self {
        case .bank: return "Traditional banking via Fiserv"
        case .solana: return "On-chain with blockchain receipt"
        }
    }
}

enum PaymentDecision: String, Codable {
    case approved = "APPROVED"
    case rejected = "REJECTED"
    case retry = "RETRY"
    
    var icon: String {
        switch self {
        case .approved: return "✅"
        case .rejected: return "❌"
        case .retry: return "🔄"
        }
    }
    
    var subtitle: String {
        switch self {
        case .approved: return "Payment processed successfully"
        case .rejected: return "Payment verification failed"
        case .retry: return "Please retry verification"
        }
    }
}

// MARK: - Request Models

struct InitiatePaymentRequest: Codable {
    let user_id: String
    let rail: String
    let amount: Double
    let recipient_id: String?
    let recipient_address: String?
    let note: String
    let device_id: String
    let user_agent: String
    let ip: String?
}

// MARK: - Response Models

struct ApprovedPaymentResponse: Codable, Identifiable {
    var id: String { payment_id }
    let status: String
    let payment_id: String
    let payment_status: String
    let rail: String
    let solana_tx: String?
}

struct ChallengeRequiredResponse: Codable {
    let status: String
    let challenge_id: String
    let prompt: String
    let security_message: String?
    let expires_at: String
    let payment_id: String
    let payment_status: String
    let rail: String
    let solana_tx: String?
}

struct VerificationScores: Codable {
    let deepfake_mean: Double
    let deepfake_var: Double
    let liveness: Double
    let quality: Double
    let presage: Double
}

struct VerificationResponse: Codable {
    let status: String
    let decision: String
    let scores: VerificationScores?
    let reasons: [String]?
    let challenge_id: String?
    let payment_id: String
    let payment_status: String
    let rail: String
    let solana_tx: String?
    let verification_receipt_tx: String?
    
    var paymentDecision: PaymentDecision {
        let d = decision.uppercased()
        if d == "PASS" || d == "APPROVED" { return .approved }
        if d == "FAIL" || d == "REJECTED" { return .rejected }
        if d == "RETRY" { return .retry }
        return .rejected
    }
    
    var paymentRail: PaymentRail {
        PaymentRail(rawValue: rail) ?? .bank
    }
}

// MARK: - Audit Models

struct Challenge: Codable, Identifiable {
    let id: String
    let user_id: String
    let created_at: String
    let prompt: String
    let decision: String?
    let payment_id: String?
    let rail: String?
    
    var formattedDate: String {
        let iso = ISO8601DateFormatter()
        iso.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let iso2 = ISO8601DateFormatter()
        if let date = iso.date(from: created_at) ?? iso2.date(from: created_at) {
            let formatter = DateFormatter()
            formatter.dateStyle = .medium
            formatter.timeStyle = .short
            return formatter.string(from: date)
        }
        return created_at
    }
    
    var paymentDecision: PaymentDecision? {
        guard let d = decision?.uppercased() else { return nil }
        if d == "PASS" || d == "APPROVED" { return .approved }
        if d == "FAIL" || d == "REJECTED" { return .rejected }
        if d == "RETRY" { return .retry }
        return nil
    }
    
    var paymentRail: PaymentRail? {
        guard let r = rail else { return nil }
        return PaymentRail(rawValue: r)
    }
    
    // Backend returns challenge_id key
    private enum CodingKeys: String, CodingKey {
        case id = "challenge_id"
        case user_id, created_at, prompt, decision
        case payment_id = "transfer_id"
        case rail
    }
    
    // Explicit memberwise init required because of custom init(from:)
    init(id: String, user_id: String, created_at: String, prompt: String, decision: String?, payment_id: String?, rail: String?) {
        self.id = id
        self.user_id = user_id
        self.created_at = created_at
        self.prompt = prompt
        self.decision = decision
        self.payment_id = payment_id
        self.rail = rail
    }
    
    // Fallback decoding so both key names work
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let rawId: String
        if let v = try? container.decode(String.self, forKey: .id) {
            rawId = v
        } else {
            rawId = UUID().uuidString
        }
        id = rawId
        user_id = (try? container.decode(String.self, forKey: .user_id)) ?? ""
        created_at = (try? container.decode(String.self, forKey: .created_at)) ?? ""
        prompt = (try? container.decode(String.self, forKey: .prompt)) ?? ""
        decision = try? container.decode(String.self, forKey: .decision)
        payment_id = try? container.decode(String.self, forKey: .payment_id)
        rail = try? container.decode(String.self, forKey: .rail)
    }
}

struct ChallengeDetail: Codable {
    let id: String
    let user_id: String
    let created_at: String
    let prompt: String
    let decision: String?
    let payment_id: String?
    let rail: String?
    let scores: VerificationScores?
    let reasons: [String]?
    let payment_status: String?
    let solana_tx: String?
    let verification_receipt_tx: String?
    
    var formattedDate: String {
        let iso = ISO8601DateFormatter()
        iso.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let iso2 = ISO8601DateFormatter()
        if let date = iso.date(from: created_at) ?? iso2.date(from: created_at) {
            let formatter = DateFormatter()
            formatter.dateStyle = .medium
            formatter.timeStyle = .short
            return formatter.string(from: date)
        }
        return created_at
    }
    
    var paymentDecision: PaymentDecision? {
        guard let d = decision?.uppercased() else { return nil }
        if d == "PASS" || d == "APPROVED" { return .approved }
        if d == "FAIL" || d == "REJECTED" { return .rejected }
        if d == "RETRY" { return .retry }
        return nil
    }
    
    var paymentRail: PaymentRail? {
        guard let r = rail else { return nil }
        return PaymentRail(rawValue: r)
    }
    
    private enum CodingKeys: String, CodingKey {
        case id = "challenge_id"
        case user_id, created_at, prompt, decision
        case payment_id = "transfer_id"
        case rail, scores, reasons, payment_status, solana_tx, verification_receipt_tx
    }
    
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = (try? container.decode(String.self, forKey: .id)) ?? UUID().uuidString
        user_id = (try? container.decode(String.self, forKey: .user_id)) ?? ""
        created_at = (try? container.decode(String.self, forKey: .created_at)) ?? ""
        prompt = (try? container.decode(String.self, forKey: .prompt)) ?? ""
        decision = try? container.decode(String.self, forKey: .decision)
        payment_id = try? container.decode(String.self, forKey: .payment_id)
        rail = try? container.decode(String.self, forKey: .rail)
        scores = try? container.decode(VerificationScores.self, forKey: .scores)
        reasons = try? container.decode([String].self, forKey: .reasons)
        payment_status = try? container.decode(String.self, forKey: .payment_status)
        solana_tx = try? container.decode(String.self, forKey: .solana_tx)
        verification_receipt_tx = try? container.decode(String.self, forKey: .verification_receipt_tx)
    }
}

// MARK: - Wrapper for challenges list

struct ChallengesWrapper: Codable {
    let challenges: [Challenge]?
}
