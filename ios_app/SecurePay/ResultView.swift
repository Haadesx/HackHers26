import SwiftUI

struct ResultView: View {
    // One of these will be set
    var verificationResponse: VerificationResponse?
    var approvedResponse: ApprovedPaymentResponse?
    var onGoHome: (() -> Void)? = nil
    
    @Environment(\.dismiss) private var dismiss
    @State private var showHeroAnimation = false
    @State private var backgroundPulse = false
    
    private var decision: PaymentDecision {
        if let v = verificationResponse { return v.paymentDecision }
        return .approved
    }
    
    private var paymentId: String {
        verificationResponse?.payment_id ?? approvedResponse?.payment_id ?? "-"
    }
    
    private var paymentStatus: String {
        verificationResponse?.payment_status ?? approvedResponse?.payment_status ?? "-"
    }
    
    private var rail: String {
        verificationResponse?.rail ?? approvedResponse?.rail ?? "-"
    }
    
    private var solanaTx: String? {
        verificationResponse?.solana_tx ?? approvedResponse?.solana_tx
    }
    
    private var verificationReceiptTx: String? {
        verificationResponse?.verification_receipt_tx
    }
    
    private var scores: VerificationScores? { verificationResponse?.scores }
    private var reasons: [String] { verificationResponse?.reasons ?? [] }
    
    var body: some View {
        ZStack {
            DesignSystem.Colors.background.ignoresSafeArea()
            
            // Dynamic Premium Background
            RadialGradient(
                colors: [decisionColor.opacity(0.3), .clear],
                center: .top,
                startRadius: 50,
                endRadius: backgroundPulse ? 600 : 400
            )
            .ignoresSafeArea()
            .animation(.easeInOut(duration: 3.0).repeatForever(autoreverses: true), value: backgroundPulse)
            
            // Subtle noise texture or mesh
            DesignSystem.Colors.meshBackground.opacity(0.5)
            
            ScrollView(showsIndicators: false) {
                VStack(spacing: 24) {
                    
                    // Animated Hero Section
                    heroSection
                        .padding(.top, 20)
                        .padding(.bottom, 10)
                    
                    // Payment Details
                    paymentDetailsCard
                    
                    // Blockchain TXs (Solana only)
                    if rail == "SOLANA" && (solanaTx != nil || verificationReceiptTx != nil) {
                        blockchainCard
                    }
                    
                    // Scores Grid
                    if let scores {
                        scoresSection(scores)
                    }
                    
                    // Reasons
                    if !reasons.isEmpty {
                        reasonsCard
                    }
                    
                    // Action Buttons
                    actionButtons
                        .padding(.top, 20)
                }
                .padding(.horizontal, 20)
                .padding(.bottom, 40)
            }
        }
        .navigationTitle("Receipt")
        .navigationBarTitleDisplayMode(.inline)
        .navigationBarBackButtonHidden(true)
        .onAppear {
            withAnimation(.spring(response: 0.6, dampingFraction: 0.6)) {
                showHeroAnimation = true
            }
            backgroundPulse = true
            triggerDecisionHaptic()
        }
    }
    
    // MARK: - Subviews
    
    private var heroSection: some View {
        VStack(spacing: 16) {
            ZStack {
                Circle()
                    .fill(decisionColor.opacity(0.15))
                    .frame(width: 100, height: 100)
                    .scaleEffect(showHeroAnimation ? 1 : 0.5)
                
                Circle()
                    .fill(decisionColor.opacity(0.25))
                    .frame(width: 70, height: 70)
                    .scaleEffect(showHeroAnimation ? 1 : 0)
                    .animation(.spring(response: 0.6, dampingFraction: 0.6).delay(0.1), value: showHeroAnimation)
                
                Image(systemName: decisionIconName)
                    .font(.system(size: 44, weight: .bold))
                    .foregroundColor(decisionColor)
                    .scaleEffect(showHeroAnimation ? 1 : 0)
                    .animation(.spring(response: 0.5, dampingFraction: 0.5).delay(0.2), value: showHeroAnimation)
            }
            .shadow(color: decisionColor.opacity(0.4), radius: 20, x: 0, y: 10)
            
            VStack(spacing: 6) {
                Text(decision.rawValue)
                    .font(DesignSystem.Typography.heroTitle(size: 32))
                    .foregroundColor(.white)
                    .opacity(showHeroAnimation ? 1 : 0)
                    .offset(y: showHeroAnimation ? 0 : 20)
                
                Text(decision.subtitle)
                    .font(DesignSystem.Typography.label(size: 16))
                    .foregroundColor(DesignSystem.Colors.secondaryText)
                    .multilineTextAlignment(.center)
                    .opacity(showHeroAnimation ? 1 : 0)
                    .offset(y: showHeroAnimation ? 0 : 20)
                    .animation(.easeOut(duration: 0.5).delay(0.3), value: showHeroAnimation)
            }
        }
    }
    
    private var decisionColor: Color {
        switch decision {
        case .approved: return DesignSystem.Colors.successAccent
        case .rejected: return DesignSystem.Colors.errorAccent
        case .retry: return DesignSystem.Colors.warningAccent
        }
    }
    
    private var decisionIconName: String {
        switch decision {
        case .approved: return "checkmark"
        case .rejected: return "xmark"
        case .retry: return "exclamationmark.triangle"
        }
    }
    
    private func triggerDecisionHaptic() {
        switch decision {
        case .approved: DesignSystem.Haptics.success()
        case .rejected: DesignSystem.Haptics.error()
        case .retry: DesignSystem.Haptics.warning()
        }
    }
    
    private var paymentDetailsCard: some View {
        GlassCard(title: "Payment Details", icon: "creditcard.fill") {
            VStack(spacing: 16) {
                DetailRow(label: "Payment ID", value: paymentId, isCode: true)
                Divider().background(Color.white.opacity(0.1))
                DetailRow(label: "Status", value: paymentStatus)
                Divider().background(Color.white.opacity(0.1))
                DetailRow(label: "Rail", value: rail == "BANK" ? "🏦 Bank Transfer" : "⚡ Solana")
            }
        }
    }
    
    private var blockchainCard: some View {
        GlassCard(title: "Blockchain Log", icon: "link.circle.fill") {
            VStack(spacing: 16) {
                if let tx = solanaTx {
                    TransactionRow(label: "Payment Transfer", hash: tx, badge: "Solana")
                }
                if solanaTx != nil && verificationReceiptTx != nil {
                    Divider().background(Color.white.opacity(0.1))
                }
                if let receipt = verificationReceiptTx {
                    TransactionRow(label: "Verification Receipt", hash: receipt, badge: "On-Chain")
                }
            }
        }
    }
    
    private func scoresSection(_ scores: VerificationScores) -> some View {
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
    
    private var reasonsCard: some View {
        GlassCard(title: "Analysis Details", icon: "list.clipboard.fill") {
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
    
    private var actionButtons: some View {
        Button {
            DesignSystem.Haptics.heavyTap()
            if let onGoHome = onGoHome {
                onGoHome()
            } else {
                dismiss()
            }
        } label: {
            HStack(spacing: 8) {
                Image(systemName: "house.fill")
                Text("Return to Home")
                    .font(DesignSystem.Typography.label(size: 18, weight: .bold))
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 18)
            .background(DesignSystem.Colors.primaryAccent)
            .foregroundColor(.white)
            .clipShape(RoundedRectangle(cornerRadius: 16))
            .shadow(color: DesignSystem.Colors.primaryAccent.opacity(0.4), radius: 15, x: 0, y: 8)
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Helper Views

struct GlassCard<Content: View>: View {
    let title: String
    let icon: String
    @ViewBuilder let content: () -> Content
    
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Image(systemName: icon)
                    .foregroundColor(DesignSystem.Colors.primaryAccent)
                Text(title)
                    .font(DesignSystem.Typography.label(size: 16, weight: .bold))
                    .foregroundColor(.white)
            }
            
            content()
        }
        .padding(20)
        .glassCard()
    }
}

struct DetailRow: View {
    let label: String
    let value: String
    var isCode = false
    
    var body: some View {
        HStack {
            Text(label)
                .font(DesignSystem.Typography.label(size: 14))
                .foregroundColor(DesignSystem.Colors.secondaryText)
            
            Spacer()
            
            if isCode {
                Text(value.prefix(12) + "...")
                    .font(DesignSystem.Typography.monospacedData(size: 14))
                    .foregroundColor(.white)
            } else {
                Text(value)
                    .font(DesignSystem.Typography.label(size: 14, weight: .bold))
                    .foregroundColor(.white)
            }
        }
    }
}

struct TransactionRow: View {
    let label: String
    let hash: String
    let badge: String
    
    @State private var copied = false
    
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text(label)
                    .font(DesignSystem.Typography.label(size: 14, weight: .semibold))
                    .foregroundColor(.white)
                Spacer()
                Text(badge)
                    .font(DesignSystem.Typography.label(size: 10, weight: .bold))
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(DesignSystem.Colors.primaryAccent.opacity(0.2))
                    .foregroundColor(DesignSystem.Colors.primaryAccent)
                    .clipShape(Capsule())
            }
            
            HStack(spacing: 8) {
                Text(hash.prefix(20) + "...")
                    .font(DesignSystem.Typography.monospacedData(size: 12))
                    .foregroundColor(DesignSystem.Colors.secondaryText)
                    .lineLimit(1)
                
                Spacer()
                
                Button {
                    DesignSystem.Haptics.tap()
                    UIPasteboard.general.string = hash
                    copied = true
                    DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) { copied = false }
                } label: {
                    Image(systemName: copied ? "checkmark.circle.fill" : "doc.on.doc")
                        .font(.system(size: 14))
                        .foregroundColor(copied ? DesignSystem.Colors.successAccent : DesignSystem.Colors.primaryAccent)
                        .scaleEffect(copied ? 1.2 : 1.0)
                        .animation(.spring(), value: copied)
                }
            }
            .padding(12)
            .background(Color.black.opacity(0.3))
            .cornerRadius(8)
        }
    }
}

#Preview {
    NavigationStack {
        ResultView(
            verificationResponse: VerificationResponse(
                status: "VERIFIED",
                decision: "APPROVED",
                scores: VerificationScores(deepfake_mean: 0.12, deepfake_var: 0.03, liveness: 0.94, quality: 0.87, presage: 0.91),
                reasons: ["High liveness confidence", "Low deepfake probability"],
                challenge_id: "ch_abc",
                payment_id: "pay_xyz",
                payment_status: "COMPLETED",
                rail: "BANK",
                solana_tx: "sol_tx_hash_1234567890abcdef",
                verification_receipt_tx: "receipt_hash_0987654321"
            ),
            onGoHome: {}
        )
    }
    .preferredColorScheme(.dark)
}
