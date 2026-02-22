import Swift
import Foundation
import AVFoundation
import UIKit
import Vision

/// Embedded backend that runs entirely on-device.
/// Calls the Gemini API directly for risk assessment and simulates liveness verification.
/// No external server required.
class EmbeddedBackend {
    
    static let shared = EmbeddedBackend()
    
    // Gemini API config
    private let geminiAPIKey = "AIzaSyDuLLbJ-BfCeQmzy4A-CnkkgQazLGSenxE"
    private let geminiModel = "gemini-1.5-flash"
    private let geminiEndpoint = "https://generativelanguage.googleapis.com/v1beta/models"
    
    // OpenRouter API config
    private let openRouterAPIKey = "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"
    private let openRouterURL = "https://openrouter.ai/api/v1/chat/completions"
    
    // In-memory challenge store
    private var challenges: [String: ChallengeStore] = [:]
    private var auditLog: [AuditEntry] = []
    
    // MARK: - Data Structures
    
    struct ChallengeStore {
        let challengeId: String
        let paymentId: String
        let userId: String
        let amount: Double
        let rail: String
        let recipientId: String?
        let recipientAddress: String?
        let note: String?
        let triggers: [String]
        let createdAt: Date
        let expiresAt: Date
    }
    
    struct AuditEntry: Codable, Identifiable {
        let id: String
        let challengeId: String
        let paymentId: String
        let userId: String
        let amount: Double
        let rail: String
        let decision: String
        let reasons: [String]
        let createdAt: Date
    }
    
    // MARK: - Payment Initiation
    
    func initiatePayment(request: InitiatePaymentRequest) async throws -> PaymentInitiateResult {
        let paymentId = "pay_\(UUID().uuidString.replacingOccurrences(of: "-", with: "").prefix(32))"
        let amount = request.amount
        
        // Step 1: Call Gemini for transaction risk scoring
        let riskResult = await evaluateTransactionRisk(
            userId: request.user_id,
            recipientId: request.recipient_id ?? request.recipient_address ?? "unknown",
            amount: amount,
            transactionId: paymentId
        )
        
        let riskLevel = riskResult["risk_level"] as? String ?? "MEDIUM"
        let riskPercentage = riskResult["risk_percentage"] as? Int ?? 50
        let riskExplanation = riskResult["explanation"] as? String ?? riskResult["fraud_explanation"] as? String ?? "Unusual transaction profile detected."
        
        // Step 2: Determine if challenge is needed
        // Low risk (< 30%) and LOW level → APPROVED
        if riskLevel == "LOW" && riskPercentage < 30 {
            let response = ApprovedPaymentResponse(
                status: "APPROVED",
                payment_id: paymentId,
                payment_status: "EXECUTED",
                rail: request.rail.uppercased(),
                solana_tx: request.rail.uppercased() == "SOLANA" ? "sim_\(UUID().uuidString.prefix(16))" : nil
            )
            return .approved(response)
        }
        
        // Step 3: High/Medium risk → Challenge Required
        let challengeId = "chg_\(UUID().uuidString.replacingOccurrences(of: "-", with: "").prefix(32))"
        let expiresAt = Date().addingTimeInterval(120)
        
        // Generate triggers
        var triggers: [String] = []
        if riskPercentage >= 60 { triggers.append("high_fraud_score") }
        if amount > 1000 { triggers.append("high_amount") }
        
        // Store challenge locally
        challenges[challengeId] = ChallengeStore(
            challengeId: challengeId,
            paymentId: paymentId,
            userId: request.user_id,
            amount: amount,
            rail: request.rail.uppercased(),
            recipientId: request.recipient_id,
            recipientAddress: request.recipient_address,
            note: request.note,
            triggers: triggers,
            createdAt: Date(),
            expiresAt: expiresAt
        )
        
        // Generate security message using OpenRouter
        let securityMessage = await generateSecurityMessage(
            amount: amount,
            riskLevel: riskLevel,
            triggers: triggers,
            riskExplanation: riskExplanation
        )
        
        let iso8601 = ISO8601DateFormatter()
        iso8601.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        
        let response = ChallengeRequiredResponse(
            status: "CHALLENGE_REQUIRED",
            challenge_id: challengeId,
            prompt: "Please record a clear 3-second face video for identity verification.",
            security_message: securityMessage,
            expires_at: iso8601.string(from: expiresAt),
            payment_id: paymentId,
            payment_status: "HELD",
            rail: request.rail.uppercased(),
            solana_tx: nil
        )
        return .challengeRequired(response)
    }
    
    // MARK: - Liveness Verification
    
    func uploadLivenessVideo(challengeId: String, videoURL: URL) async throws -> VerificationResponse {
        guard let challenge = challenges[challengeId] else {
            throw NetworkError.serverError("Challenge not found or expired")
        }
        
        guard Date() < challenge.expiresAt else {
            throw NetworkError.serverError("Challenge expired")
        }
        
        // Extract frame
        guard let cgImage = extractFirstFrame(from: videoURL) else {
            throw NetworkError.serverError("Could not extract frame from video.")
        }
        
        // Detect face natively using Apple Vision framework
        let hasFace = detectFace(in: cgImage)
        
        var scores: [String: Double] = [:]
        var signals: [String] = []
        
        if !hasFace {
            print("🚫 VISION: No Face Detected in Video")
            scores = [
                "deepfake_mean": 0.0, "deepfake_var": 0.0,
                "liveness": 0.0, "quality": 0.0,
                "presage": 0.0, "qwen_spoof_confidence": 0.0
            ]
            signals = ["no_face_detected_in_video"]
        } else {
            print("✅ VISION: Face Detected successfully")
            
            // --- REAL ML BACKEND INTEGRATION OVER LOCAL WIFI ---
            print("⏳ Uploading video to Python Backend for true Deepfake and rPPG analysis...")
            if let realData = await fetchRealScores(videoURL: videoURL),
               let realScoresAny = realData["scores"] as? [String: Any],
               let realSignals = realData["signals"] as? [String] {
                
                print("✅ Received REAL ML Scores: \\(realScoresAny)")
                scores = [
                    "deepfake_mean": realScoresAny["deepfake_mean"] as? Double ?? 0.0,
                    "deepfake_var": realScoresAny["deepfake_var"] as? Double ?? 0.0,
                    "liveness": realScoresAny["liveness"] as? Double ?? 0.0,
                    "quality": realScoresAny["quality"] as? Double ?? 0.0,
                    "presage": realScoresAny["presage"] as? Double ?? 0.0,
                    "qwen_spoof_confidence": realScoresAny["qwen_spoof_confidence"] as? Double ?? 0.0
                ]
                signals = realSignals
            } else {
                print("⚠️ ML Backend call failed. Falling back to local failure decision.")
                scores = [
                    "deepfake_mean": 0.0, "deepfake_var": 0.0,
                    "liveness": 0.0, "quality": 0.0,
                    "presage": 0.0, "qwen_spoof_confidence": 0.0
                ]
                signals = ["ml_backend_unreachable"]
            }
        }
        
        let finalScores = scores
        
        // Call Gemini for final liveness decision
        let decision = await evaluateLivenessRisk(scores: finalScores, signals: signals, retryCount: 0)
        let finalDecision = decision["action"] as? String ?? "PASS"
        let reasons = decision["reasons"] as? [String] ?? ["Verification complete"]
        
        // Determine payment status based on decision
        let paymentStatus: String
        switch finalDecision {
        case "PASS": paymentStatus = "EXECUTED"
        case "FAIL": paymentStatus = "BLOCKED"
        case "RETRY": paymentStatus = "RETRY"
        default: paymentStatus = "HELD"
        }
        
        // Generate receipt
        let receiptTx = finalDecision == "PASS" ? "sim_receipt_\(UUID().uuidString.prefix(12))" : nil
        
        // Save to audit log
        let entry = AuditEntry(
            id: UUID().uuidString,
            challengeId: challengeId,
            paymentId: challenge.paymentId,
            userId: challenge.userId,
            amount: challenge.amount,
            rail: challenge.rail,
            decision: finalDecision,
            reasons: reasons,
            createdAt: Date()
        )
        auditLog.insert(entry, at: 0)
        
        // Clean up challenge
        challenges.removeValue(forKey: challengeId)
        
        let vScores = VerificationScores(
            deepfake_mean: finalScores["deepfake_mean"] ?? 0,
            deepfake_var: finalScores["deepfake_var"] ?? 0,
            liveness: finalScores["liveness"] ?? 0,
            quality: finalScores["quality"] ?? 0,
            presage: finalScores["presage"] ?? 0
        )
        
        return VerificationResponse(
            status: "VERIFIED",
            decision: finalDecision,
            scores: vScores,
            reasons: reasons,
            challenge_id: challengeId,
            payment_id: challenge.paymentId,
            payment_status: paymentStatus,
            rail: challenge.rail,
            solana_tx: nil,
            verification_receipt_tx: receiptTx
        )
    }
    
    // MARK: - Audit
    
    func getChallenges() -> [Challenge] {
        return auditLog.map { entry in
            Challenge(
                id: entry.challengeId,
                user_id: entry.userId,
                created_at: ISO8601DateFormatter().string(from: entry.createdAt),
                prompt: "Please record a clear 3-second face video for identity verification.",
                decision: entry.decision,
                payment_id: entry.paymentId,
                rail: entry.rail
            )
        }
    }
    
    // MARK: - Risk Evaluation
    
    private func evaluateTransactionRisk(userId: String, recipientId: String, amount: Double, transactionId: String) async -> [String: Any] {
        let systemPrompt = """
        You are a financial fraud risk scoring engine.
        RISK SCORING HEURISTICS:
        - Amount < 100 → base risk 10
        - Amount 100–1000 → base risk 30
        - Amount > 1000 → base risk 60
        - If prior_interaction is false → add 15
        RISK LEVEL: 0–29 → LOW, 30–69 → MEDIUM, 70–100 → HIGH
        OUTPUT STRICT JSON: {"risk_percentage": int, "risk_level": "LOW"|"MEDIUM"|"HIGH", "fraud_explanation": "string"}
        """
        
        let userMessage = """
        {"transaction_id":"\(transactionId)","user_id":"\(userId)","recipient_id":"\(recipientId)","amount":\(amount),"prior_interaction":false}
        """
        
        if let result = await callGemini(systemPrompt: systemPrompt, userMessage: userMessage) {
            return result
        }
        
        // Fallback to OpenRouter (Gemini 2.0 Pro Exp)
        if let fallbackResult = await callOpenRouterRiskAPI(systemPrompt: systemPrompt, userMessage: userMessage) {
            return fallbackResult
        }
        
        return deterministicTransactionRisk(amount: amount)
    }
    
    private func evaluateLivenessRisk(scores: [String: Double], signals: [String], retryCount: Int) async -> [String: Any] {
        let systemPrompt = """
        You are a security decision engine. Evaluate liveness using numerical scores.
        PASS if: quality >= 0.4, (liveness >= 0.4 OR presage >= 0.2), deepfake_mean < 0.3, deepfake_var < 0.05, qwen_spoof_confidence < 0.5
        RETRY if conditions borderline and first try.
        FAIL if deepfake score high.
        OUTPUT STRICT JSON: {"final_decision":"PASS"|"FAIL"|"RETRY","risk_level":"LOW"|"HIGH"|"CRITICAL","reason":"explanation"}
        """
        
        let userMessage = """
        {"scores":{"deepfake_mean":\(scores["deepfake_mean"] ?? 0),"deepfake_var":\(scores["deepfake_var"] ?? 0),"liveness":\(scores["liveness"] ?? 0),"quality":\(scores["quality"] ?? 0),"presage":\(scores["presage"] ?? 0),"qwen_spoof_confidence":\(scores["qwen_spoof_confidence"] ?? 0)},"retry_count":\(retryCount)}
        """
        
        let result: [String: Any]?
        if let gResult = await callGemini(systemPrompt: systemPrompt, userMessage: userMessage) {
            result = gResult
        } else if let oResult = await callOpenRouterRiskAPI(systemPrompt: systemPrompt, userMessage: userMessage) {
            result = oResult
        } else {
            result = nil
        }
        
        guard let finalResult = result else {
            return deterministicLivenessRisk(scores: scores, retryCount: retryCount)
        }
        
        let finalDecision = finalResult["final_decision"] as? String ?? finalResult["action"] as? String ?? "PASS"
        return [
            "action": finalDecision,
            "risk_level": finalResult["risk_level"] as? String ?? "LOW",
            "reasons": [finalResult["reason"] as? String ?? finalResult["fraud_explanation"] as? String ?? "Verification complete"]
        ]
    }
    
    // MARK: - OpenRouter API (Security Message)
    
    private func generateSecurityMessage(amount: Double, riskLevel: String, triggers: [String], riskExplanation: String) async -> String {
        let triggerText = triggers.isEmpty ? "General Anomaly" : triggers.joined(separator: ", ")
        let prompt = """
        You are a friendly but professional banking security assistant.
        A user just tried to send an unusual transaction that our fraud engine flagged and paused.
        
        Details:
        - Amount: $\(String(format: "%.2f", amount))
        - Risk Level: \(riskLevel)
        - Internal Fraud Engine Reason: \(riskExplanation)
        - Alert Triggers: \(triggerText)
        
        Write EXACTLY ONE short, friendly sentence (maximum 20 words) explaining to the user why we paused it, and asking them to complete a quick biometric face scan to unlock the funds.
        Use a warm, protective tone. Do not include quotes or any standard AI greetings like 'Here is your sentence'.
        """
        
        let requestBody: [String: Any] = [
            "model": "arcee-ai/trinity-large-preview:free",
            "messages": [["role": "user", "content": prompt]],
            "temperature": 0.7,
            "max_tokens": 60
        ]
        
        guard let url = URL(string: openRouterURL) else { return fallbackSecurityMessage(amount: amount, triggers: triggerText) }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("Bearer \(openRouterAPIKey)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("https://hackhers.demo", forHTTPHeaderField: "HTTP-Referer")
        request.setValue("DeepfakeGate", forHTTPHeaderField: "X-Title")
        request.timeoutInterval = 10
        request.httpBody = try? JSONSerialization.data(withJSONObject: requestBody)
        
        do {
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let httpResp = response as? HTTPURLResponse, httpResp.statusCode == 200,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let choices = json["choices"] as? [[String: Any]],
                  let message = choices.first?["message"] as? [String: Any],
                  let content = message["content"] as? String else {
                return fallbackSecurityMessage(amount: amount, triggers: triggerText)
            }
            return content.trimmingCharacters(in: CharacterSet(charactersIn: "\" \n"))
        } catch {
            return fallbackSecurityMessage(amount: amount, triggers: triggerText)
        }
    }
    
    // MARK: - OpenRouter API (Fallback for Risk JSON)
    
    private func callOpenRouterRiskAPI(systemPrompt: String, userMessage: String) async -> [String: Any]? {
        let requestBody: [String: Any] = [
            "model": "google/gemini-2.0-pro-exp-0205:free",
            "messages": [
                ["role": "system", "content": systemPrompt],
                ["role": "user", "content": userMessage]
            ],
            "temperature": 0.1,
            "max_tokens": 1000,
            "response_format": ["type": "json_object"]
        ]
        
        guard let url = URL(string: openRouterURL) else { return nil }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("Bearer \(openRouterAPIKey)", forHTTPHeaderField: "Authorization")
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("https://hackhers.demo", forHTTPHeaderField: "HTTP-Referer")
        request.setValue("DeepfakeGate", forHTTPHeaderField: "X-Title")
        request.timeoutInterval = 15
        request.httpBody = try? JSONSerialization.data(withJSONObject: requestBody)
        
        do {
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let httpResp = response as? HTTPURLResponse, httpResp.statusCode == 200,
                  let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let choices = json["choices"] as? [[String: Any]],
                  let message = choices.first?["message"] as? [String: Any],
                  let content = message["content"] as? String else { 
                print("❌ OPENROUTER Missing specific keys in response")
                return nil 
            }
            
            print("👁️ OPENROUTER Raw Response: \\(content)")
            
            var cleanedContent = content.trimmingCharacters(in: .whitespacesAndNewlines)
            if cleanedContent.hasPrefix("```json") {
                cleanedContent = String(cleanedContent.dropFirst(7).dropLast(3)).trimmingCharacters(in: .whitespacesAndNewlines)
            } else if cleanedContent.hasPrefix("```") {
                cleanedContent = String(cleanedContent.dropFirst(3).dropLast(3)).trimmingCharacters(in: .whitespacesAndNewlines)
            }
            
            guard let textData = cleanedContent.data(using: .utf8),
                  let parsed = try? JSONSerialization.jsonObject(with: textData) as? [String: Any] else { 
                print("❌ OPENROUTER JSON Parse Failed: \\(cleanedContent)")
                return nil 
            }
            print("✅ OPENROUTER Parsed: \\(parsed)")
            return parsed
        } catch {
            print("❌ OPENROUTER Network/Decode Error: \\(error.localizedDescription)")
            return nil
        }
    }
    
    // MARK: - Native Face Detection Helper
    
    private func extractFirstFrame(from videoURL: URL) -> CGImage? {
        let asset = AVAsset(url: videoURL)
        let generator = AVAssetImageGenerator(asset: asset)
        generator.appliesPreferredTrackTransform = true
        return try? generator.copyCGImage(at: .zero, actualTime: nil)
    }
    
    private func detectFace(in cgImage: CGImage) -> Bool {
        let request = VNDetectFaceRectanglesRequest()
        let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
        do {
            try handler.perform([request])
            return !(request.results?.isEmpty ?? true)
        } catch {
            print("❌ Vision Face Detection Failed: \\(error)")
            return false
        }
    }
    
    // MARK: - Python Backend ML Helper
    
    // Remote connection to Mac Host via LAN IP for physical iOS device testing
    private let pythonBackendURL = "http://172.25.199.172:8000"
    
    private func fetchRealScores(videoURL: URL) async -> [String: Any]? {
        guard let url = URL(string: "\\(pythonBackendURL)/liveness/score") else { return nil }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        
        let boundary = "Boundary-\\(UUID().uuidString)"
        request.setValue("multipart/form-data; boundary=\\(boundary)", forHTTPHeaderField: "Content-Type")
        
        guard let videoData = try? Data(contentsOf: videoURL) else { return nil }
        
        var body = Data()
        body.append("--\\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"video\"; filename=\"video.mov\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: video/quicktime\r\n\r\n".data(using: .utf8)!)
        body.append(videoData)
        body.append("\r\n".data(using: .utf8)!)
        body.append("--\\(boundary)--\r\n".data(using: .utf8)!)
        
        request.httpBody = body
        request.timeoutInterval = 60
        
        do {
            let (data, response) = try await URLSession.shared.data(for: request)
            guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
                print("❌ Backend HTTP Error: \\((response as? HTTPURLResponse)?.statusCode ?? 0)")
                return nil
            }
            guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
                print("❌ Backend JSON Parse Failed")
                return nil
            }
            return json
        } catch {
            print("❌ Backend Network Error: \\(error.localizedDescription)")
            return nil
        }
    }
    
    // MARK: - Gemini API Call
    
    private func callGemini(systemPrompt: String, userMessage: String) async -> [String: Any]? {
        let urlString = "\(geminiEndpoint)/\(geminiModel):generateContent?key=\(geminiAPIKey)"
        guard let url = URL(string: urlString) else { return nil }
        
        let requestBody: [String: Any] = [
            "system_instruction": ["parts": [["text": systemPrompt]]],
            "contents": [["parts": [["text": userMessage]]]],
            "generationConfig": ["responseMimeType": "application/json"]
        ]
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.timeoutInterval = 30
        request.httpBody = try? JSONSerialization.data(withJSONObject: requestBody)
        
        do {
            let (data, response) = try await URLSession.shared.data(for: request)
            
            guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else { return nil }
            guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let candidates = json["candidates"] as? [[String: Any]],
                  let content = candidates.first?["content"] as? [String: Any],
                  let parts = content["parts"] as? [[String: Any]],
                  let text = parts.first?["text"] as? String else { 
                print("❌ GEMINI Missing specific keys in response")
                return nil 
            }
            
            print("🤖 GEMINI Raw Response: \\(text)")
            
            var cleanedContent = text.trimmingCharacters(in: .whitespacesAndNewlines)
            if cleanedContent.hasPrefix("```json") {
                cleanedContent = String(cleanedContent.dropFirst(7).dropLast(3)).trimmingCharacters(in: .whitespacesAndNewlines)
            } else if cleanedContent.hasPrefix("```") {
                cleanedContent = String(cleanedContent.dropFirst(3).dropLast(3)).trimmingCharacters(in: .whitespacesAndNewlines)
            }
            
            guard let textData = cleanedContent.data(using: .utf8),
                  let parsed = try? JSONSerialization.jsonObject(with: textData) as? [String: Any] else { 
                print("❌ GEMINI JSON Parse Failed on cleaned content: \\(cleanedContent)")
                return nil 
            }
            print("✅ GEMINI Parsed: \\(parsed)")
            return parsed
        } catch {
            print("❌ GEMINI Network/Decode Error: \\(error.localizedDescription)")
            return nil
        }
    }
    
    // MARK: - Deterministic Fallbacks
    
    private func deterministicTransactionRisk(amount: Double) -> [String: Any] {
        let risk: Int
        let level: String
        if amount < 100 {
            risk = 15; level = "LOW"
        } else if amount <= 1000 {
            risk = 45; level = "MEDIUM"
        } else {
            risk = 75; level = "HIGH"
        }
        return ["risk_percentage": risk, "risk_level": level, "fraud_explanation": "Amount-based risk assessment"]
    }
    
    private func deterministicLivenessRisk(scores: [String: Double], retryCount: Int) -> [String: Any] {
        let dfMean = scores["deepfake_mean"] ?? 0
        let dfVar = scores["deepfake_var"] ?? 0
        let liveness = scores["liveness"] ?? 1.0
        let quality = scores["quality"] ?? 1.0
        let presage = scores["presage"] ?? 1.0
        let qwen = scores["qwen_spoof_confidence"] ?? 0
        
        if dfMean >= 0.5 || dfVar >= 0.05 || qwen >= 0.5 {
            return ["action": "FAIL", "risk_level": "CRITICAL", "reasons": ["High deepfake/spoof score detected"]]
        }
        
        if liveness < 0.4 || quality < 0.4 || presage < 0.2 {
            if retryCount == 0 {
                return ["action": "RETRY", "risk_level": "MEDIUM", "reasons": ["Poor biometric quality, please try again"]]
            }
            return ["action": "FAIL", "risk_level": "HIGH", "reasons": ["Biometric verification failed after retry"]]
        }
        
        return ["action": "PASS", "risk_level": "LOW", "reasons": ["Biometric verification passed — face detected, natural motion confirmed"]]
    }
    
    private func fallbackSecurityMessage(amount: Double, triggers: String) -> String {
        return "We've paused your $\(String(format: "%.2f", amount)) transaction due to \(triggers). Please complete a quick face scan to verify your identity and unlock your funds."
    }
}
