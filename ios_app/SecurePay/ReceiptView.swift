import SwiftUI

struct ReceiptView: View {
    var verificationResponse: VerificationResponse?
    var approvedResponse: ApprovedPaymentResponse?
    
    @Environment(\.dismiss) private var dismiss
    @State private var showSecurityDetails = false
    
    private var decision: PaymentDecision {
        if let v = verificationResponse { return v.paymentDecision }
        return .approved
    }
    
    var body: some View {
        NavigationStack {
            ZStack {
                DesignSystem.Colors.background.ignoresSafeArea()
                
                ScrollView(showsIndicators: false) {
                    VStack(spacing: 24) {
                        
                        // Ticket Style Container
                        VStack(spacing: 0) {
                            
                            // Top Half: Status
                            statusBlock
                            
                            // Ticket Divider
                            ticketDivider
                            
                            // Bottom Half: Details
                            detailsBlock
                        }
                        .background(DesignSystem.Colors.card)
                        .clipShape(RoundedRectangle(cornerRadius: 24))
                        .shadow(color: decisionColor.opacity(0.15), radius: 30, x: 0, y: 15)
                        .padding(.horizontal, 24)
                        .padding(.top, 40)
                        
                        // Expanded Security Dropdown
                        if showSecurityDetails {
                            securityAccordion
                                .transition(.move(edge: .top).combined(with: .opacity))
                        }
                        
                        // Actions
                        Button {
                            DesignSystem.Haptics.heavyTap()
                            NavigationUtil.popToRootView() // Custom utility to reset to HomeView
                        } label: {
                            Text("Done")
                                .font(DesignSystem.Typography.label(size: 18, weight: .bold))
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 16)
                                .background(Color.white.opacity(0.1))
                                .foregroundColor(.white)
                                .clipShape(Capsule())
                        }
                        .padding(.horizontal, 24)
                        .padding(.top, 10)
                        
                    }
                }
            }
            .navigationBarHidden(true)
            .onAppear {
                triggerHaptic()
            }
        }
    }
    
    // MARK: - Subcomponents
    
    private var statusBlock: some View {
        VStack(spacing: 16) {
            ZStack {
                Circle()
                    .fill(decisionColor.opacity(0.15))
                    .frame(width: 80, height: 80)
                
                Image(systemName: decisionIcon)
                    .font(.system(size: 36, weight: .bold))
                    .foregroundColor(decisionColor)
            }
            .padding(.top, 30)
            
            Text(decision.rawValue)
                .font(DesignSystem.Typography.heroTitle(size: 28))
                .foregroundColor(.white)
            
            Text(decision.subtitle)
                .font(DesignSystem.Typography.label(size: 14))
                .foregroundColor(DesignSystem.Colors.secondaryText)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 20)
                .padding(.bottom, 20)
        }
    }
    
    private var ticketDivider: some View {
        HStack {
            Circle()
                .fill(DesignSystem.Colors.background)
                .frame(width: 24, height: 24)
                .offset(x: -12)
            
            Line()
                .stroke(style: StrokeStyle(lineWidth: 1, dash: [5]))
                .frame(height: 1)
                .foregroundColor(Color.white.opacity(0.2))
            
            Circle()
                .fill(DesignSystem.Colors.background)
                .frame(width: 24, height: 24)
                .offset(x: 12)
        }
        .frame(height: 24)
    }
    
    private var detailsBlock: some View {
        VStack(spacing: 16) {
            ReceiptRow(label: "Payment ID", value: paymentId, isData: true)
            ReceiptRow(label: "Rail", value: rail)
            
            if let tx = solanaTx {
                ReceiptRow(label: "Solana TX", value: tx, isData: true)
            }
            if let rx = verificationReceiptTx {
                ReceiptRow(label: "Proof TX", value: rx, isData: true)
            }
            
            Divider().background(Color.white.opacity(0.1)).padding(.vertical, 4)
            
            Button {
                withAnimation(.spring(response: 0.4)) {
                    showSecurityDetails.toggle()
                }
            } label: {
                HStack {
                    Image(systemName: "shield.checkerboard")
                        .foregroundColor(DesignSystem.Colors.primaryAccent)
                    Text("AI Security Report")
                        .font(DesignSystem.Typography.label(size: 14, weight: .medium))
                        .foregroundColor(.white)
                    Spacer()
                    Image(systemName: showSecurityDetails ? "chevron.up" : "chevron.down")
                        .foregroundColor(DesignSystem.Colors.secondaryText)
                }
            }
        }
        .padding(24)
    }
    
    private var securityAccordion: some View {
        VStack(alignment: .leading, spacing: 12) {
            if let scores = verificationResponse?.scores {
                // Mini score cards
                HStack(spacing: 8) {
                    MiniScoreItem(title: "Deepfake", score: scores.deepfake_mean)
                    MiniScoreItem(title: "Liveness", score: scores.liveness)
                    MiniScoreItem(title: "Presage", score: scores.presage)
                }
            }
            
            if let reasons = verificationResponse?.reasons {
                VStack(alignment: .leading, spacing: 6) {
                    ForEach(reasons, id: \.self) { r in
                        HStack(alignment: .top) {
                            Text("•").foregroundColor(DesignSystem.Colors.secondaryText)
                            Text(r)
                                .font(DesignSystem.Typography.label(size: 12))
                                .foregroundColor(DesignSystem.Colors.secondaryText)
                        }
                    }
                }
                .padding(.top, 8)
            }
        }
        .padding(20)
        .background(DesignSystem.Colors.card.opacity(0.5))
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(Color.white.opacity(0.1), lineWidth: 1))
        .padding(.horizontal, 24)
    }
    
    // MARK: - Properties & Helpers
    
    private var decisionColor: Color {
        switch decision {
        case .approved: return DesignSystem.Colors.successAccent
        case .rejected: return DesignSystem.Colors.errorAccent
        case .retry: return DesignSystem.Colors.warningAccent
        }
    }
    
    private var decisionIcon: String {
        switch decision {
        case .approved: return "checkmark"
        case .rejected: return "xmark"
        case .retry: return "exclamationmark.triangle"
        }
    }
    
    private var paymentId: String {
        verificationResponse?.payment_id ?? approvedResponse?.payment_id ?? "-"
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
    
    private func triggerHaptic() {
        switch decision {
        case .approved: DesignSystem.Haptics.success()
        case .rejected: DesignSystem.Haptics.error()
        case .retry: DesignSystem.Haptics.warning()
        }
    }
}

// Custom internal views
struct Line: Shape {
    func path(in rect: CGRect) -> Path {
        var path = Path()
        path.move(to: CGPoint(x: 0, y: 0))
        path.addLine(to: CGPoint(x: rect.width, y: 0))
        return path
    }
}

struct ReceiptRow: View {
    let label: String
    let value: String
    var isData = false
    
    var body: some View {
        HStack {
            Text(label)
                .font(DesignSystem.Typography.label(size: 14))
                .foregroundColor(DesignSystem.Colors.secondaryText)
            Spacer()
            if isData {
                Text(value.prefix(12) + "...")
                    .font(DesignSystem.Typography.monospacedData(size: 13))
                    .foregroundColor(.white)
            } else {
                Text(value)
                    .font(DesignSystem.Typography.label(size: 14, weight: .bold))
                    .foregroundColor(.white)
            }
        }
    }
}

struct MiniScoreItem: View {
    let title: String
    let score: Double
    var body: some View {
        VStack(spacing: 4) {
            Text(title)
                .font(DesignSystem.Typography.label(size: 10))
                .foregroundColor(DesignSystem.Colors.secondaryText)
            Text(String(format: "%.1f%%", score * 100))
                .font(DesignSystem.Typography.monospacedData(size: 12))
                .foregroundColor(.white)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 8)
        .background(Color.white.opacity(0.05))
        .cornerRadius(8)
    }
}

struct NavigationUtil {
    static func popToRootView() {
        guard let windowScene = UIApplication.shared.connectedScenes.first as? UIWindowScene else { return }
        findNavigationController(viewController: windowScene.windows.first?.rootViewController)?.popToRootViewController(animated: true)
    }

    static func findNavigationController(viewController: UIViewController?) -> UINavigationController? {
        guard let viewController = viewController else { return nil }
        
        if let navigationController = viewController as? UINavigationController {
            return navigationController
        }
        
        for childViewController in viewController.children {
            return findNavigationController(viewController: childViewController)
        }
        
        return nil
    }
}
