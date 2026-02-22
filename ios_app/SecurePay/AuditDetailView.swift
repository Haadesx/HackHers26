import SwiftUI

struct AuditDetailView: View {
    let challengeId: String
    
    private let network = NetworkManager.shared
    @State private var detail: ChallengeDetail?
    @State private var isLoading = true
    @State private var errorMessage = ""
    
    var body: some View {
        ZStack {
            DesignSystem.Colors.background.ignoresSafeArea()
            
            if isLoading {
                VStack(spacing: 16) {
                    ProgressView()
                        .tint(DesignSystem.Colors.primaryAccent)
                    Text("Loading details...")
                        .font(DesignSystem.Typography.label(size: 14))
                        .foregroundColor(DesignSystem.Colors.secondaryText)
                }
            } else if let detail {
                ScrollView(showsIndicators: false) {
                    VStack(spacing: 20) {
                        
                        // Decision Banner Header
                        if let decision = detail.paymentDecision {
                            decisionHeader(decision)
                        }
                        
                        // Basic Info
                        GlassCard(title: "Log Metadata", icon: "doc.text.magnifyingglass") {
                            VStack(spacing: 12) {
                                DetailRow(label: "Challenge ID", value: detail.id, isCode: true)
                                Divider().background(Color.white.opacity(0.1))
                                DetailRow(label: "User ID", value: detail.user_id)
                                Divider().background(Color.white.opacity(0.1))
                                DetailRow(label: "Timestamp", value: detail.formattedDate)
                                if let rail = detail.paymentRail {
                                    Divider().background(Color.white.opacity(0.1))
                                    DetailRow(label: "Rail", value: rail.icon + " " + rail.displayName)
                                }
                            }
                        }
                        
                        // Prompt
                        GlassCard(title: "Security Prompt", icon: "text.bubble.fill") {
                            Text(detail.prompt)
                                .font(DesignSystem.Typography.label(size: 15))
                                .foregroundColor(.white)
                                .italic()
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .padding()
                                .background(Color.black.opacity(0.3))
                                .cornerRadius(12)
                        }
                        
                        // Scores
                        if let scores = detail.scores {
                            VStack(alignment: .leading, spacing: 16) {
                                HStack {
                                    Image(systemName: "chart.bar.xaxis")
                                        .foregroundColor(DesignSystem.Colors.primaryAccent)
                                    Text("Verification Analysis")
                                        .font(DesignSystem.Typography.label(size: 16, weight: .bold))
                                        .foregroundColor(.white)
                                }
                                .padding(.horizontal, 4)
                                
                                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 16) {
                                    ScoreCardView(title: "Quality", score: scores.quality, icon: "✨", description: "Camera Quality")
                                    ScoreCardView(title: "Liveness", score: scores.liveness, icon: "👁️", description: "Real Person")
                                    ScoreCardView(title: "Deepfake", score: scores.deepfake_mean, icon: "🎭", description: "Avg Anomaly")
                                    ScoreCardView(title: "Behavior", score: scores.presage, icon: "🧠", description: "Presage DB")
                                }
                            }
                        }
                        
                        // Reasons
                        if let reasons = detail.reasons, !reasons.isEmpty {
                            GlassCard(title: "Analysis Results", icon: "list.clipboard.fill") {
                                VStack(alignment: .leading, spacing: 12) {
                                    ForEach(Array(reasons.enumerated()), id: \.offset) { _, reason in
                                        HStack(alignment: .top, spacing: 12) {
                                            Image(systemName: "circle.fill")
                                                .font(.system(size: 6))
                                                .foregroundColor(DesignSystem.Colors.primaryAccent)
                                                .padding(.top, 6)
                                            Text(reason)
                                                .font(DesignSystem.Typography.label(size: 14))
                                                .foregroundColor(DesignSystem.Colors.secondaryText)
                                                .fixedSize(horizontal: false, vertical: true)
                                        }
                                    }
                                }
                            }
                        }
                        
                        // Payment & Blockchain Info
                        if let paymentId = detail.payment_id {
                            GlassCard(title: "Transaction Records", icon: "link.circle.fill") {
                                VStack(spacing: 16) {
                                    DetailRow(label: "Payment ID", value: paymentId, isCode: true)
                                    Divider().background(Color.white.opacity(0.1))
                                    DetailRow(label: "Status", value: detail.payment_status ?? "-")
                                    
                                    if let tx = detail.solana_tx {
                                        Divider().background(Color.white.opacity(0.1))
                                        TransactionRow(label: "Payment TX", hash: tx, badge: "Solana")
                                    }
                                    
                                    if let receipt = detail.verification_receipt_tx {
                                        Divider().background(Color.white.opacity(0.1))
                                        TransactionRow(label: "Receipt TX", hash: receipt, badge: "On-Chain")
                                    }
                                }
                            }
                        }
                    }
                    .padding(.horizontal, 20)
                    .padding(.bottom, 40)
                    .padding(.top, 20)
                }
            } else if !errorMessage.isEmpty {
                VStack(spacing: 12) {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .font(.largeTitle)
                        .foregroundColor(DesignSystem.Colors.errorAccent)
                    Text(errorMessage)
                        .font(DesignSystem.Typography.label(size: 14))
                        .foregroundColor(DesignSystem.Colors.secondaryText)
                        .multilineTextAlignment(.center)
                }
                .padding(32)
            }
        }
        .navigationTitle("Log Details")
        .navigationBarTitleDisplayMode(.inline)
        .task { await loadDetail() }
    }
    
    private func loadDetail() async {
        isLoading = true
        errorMessage = ""
        do {
            detail = try await network.getChallengeDetail(id: challengeId)
        } catch let netError as NetworkError {
            errorMessage = netError.localizedDescription
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }
    
    private func decisionHeader(_ decision: PaymentDecision) -> some View {
        let colors: [Color]
        switch decision {
        case .approved: colors = [DesignSystem.Colors.successAccent.opacity(0.8), DesignSystem.Colors.successAccent.opacity(0.3)]
        case .rejected: colors = [DesignSystem.Colors.errorAccent.opacity(0.8), DesignSystem.Colors.errorAccent.opacity(0.3)]
        case .retry: colors = [DesignSystem.Colors.warningAccent.opacity(0.8), DesignSystem.Colors.warningAccent.opacity(0.3)]
        }
        
        return HStack(spacing: 16) {
            Text(decision.icon)
                .font(.system(size: 32, weight: .bold))
            
            VStack(alignment: .leading, spacing: 4) {
                Text(decision.rawValue)
                    .font(DesignSystem.Typography.heroTitle(size: 24))
                    .foregroundColor(.white)
                Text(decision.subtitle)
                    .font(DesignSystem.Typography.label(size: 13))
                    .foregroundColor(.white.opacity(0.8))
            }
            Spacer()
        }
        .padding(20)
        .background(
            LinearGradient(colors: colors, startPoint: .topLeading, endPoint: .bottomTrailing)
        )
        .cornerRadius(20)
    }
}

#Preview {
    NavigationStack {
        // Mock data needs to be populated via API for real preview
        AuditDetailView(challengeId: "ch_test")
    }
}
