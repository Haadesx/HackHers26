import SwiftUI

struct AuditView: View {
    @StateObject private var network = NetworkManager.shared
    @State private var challenges: [Challenge] = []
    @State private var isLoading = false
    @State private var errorMessage = ""
    
    var body: some View {
        ZStack {
            DesignSystem.Colors.background.ignoresSafeArea()
            
            if isLoading {
                VStack(spacing: 16) {
                    ProgressView()
                        .tint(DesignSystem.Colors.primaryAccent)
                        .scaleEffect(1.4)
                    Text("Loading audit logs...")
                        .font(DesignSystem.Typography.label(size: 14, weight: .semibold))
                        .foregroundColor(DesignSystem.Colors.secondaryText)
                }
            } else if !errorMessage.isEmpty {
                VStack(spacing: 16) {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .font(.system(size: 40))
                        .foregroundColor(DesignSystem.Colors.errorAccent)
                    Text(errorMessage)
                        .font(DesignSystem.Typography.label(size: 14))
                        .foregroundColor(DesignSystem.Colors.secondaryText)
                        .multilineTextAlignment(.center)
                    
                    Button {
                        DesignSystem.Haptics.tap()
                        Task { await loadChallenges() }
                    } label: {
                        Text("Retry")
                    }
                    .glowingButton(color: DesignSystem.Colors.primaryAccent)
                    .frame(width: 150)
                }
                .padding(32)
            } else if challenges.isEmpty {
                VStack(spacing: 16) {
                    Image(systemName: "tray.fill")
                        .font(.system(size: 50))
                        .foregroundColor(DesignSystem.Colors.secondaryText.opacity(0.5))
                    Text("No logs found")
                        .font(DesignSystem.Typography.label(size: 18, weight: .bold))
                        .foregroundColor(.white)
                    Text("Initiate a payment to see verification challenges here")
                        .font(DesignSystem.Typography.label(size: 14))
                        .foregroundColor(DesignSystem.Colors.secondaryText)
                        .multilineTextAlignment(.center)
                }
                .padding(32)
            } else {
                ScrollView {
                    LazyVStack(spacing: 12) {
                        ForEach(challenges) { challenge in
                            NavigationLink(destination: AuditDetailView(challengeId: challenge.id)) {
                                ChallengeRow(challenge: challenge)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                    .padding(.horizontal, 16)
                    .padding(.top, 16)
                    .padding(.bottom, 100) // Space for floating tab bar
                }
                .refreshable {
                    DesignSystem.Haptics.tap()
                    await loadChallenges()
                }
            }
        }
        .navigationTitle("Audit Log")
        .navigationBarTitleDisplayMode(.large)
        .task { await loadChallenges() }
    }
    
    private func loadChallenges() async {
        isLoading = true
        errorMessage = ""
        do {
            challenges = try await network.getChallenges()
        } catch {
            errorMessage = error.localizedDescription
        }
        isLoading = false
    }
}

struct ChallengeRow: View {
    let challenge: Challenge
    
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                // ID
                HStack(spacing: 4) {
                    Image(systemName: "number")
                        .font(.system(size: 10))
                        .foregroundColor(DesignSystem.Colors.secondaryText)
                    Text(String(challenge.id.prefix(8)) + "...")
                        .font(DesignSystem.Typography.monospacedData(size: 12))
                        .foregroundColor(DesignSystem.Colors.primaryAccent)
                }
                
                Spacer()
                
                // Decision badge
                DecisionBadge(decision: challenge.paymentDecision)
            }
            
            HStack {
                Image(systemName: "person.crop.circle.fill")
                    .foregroundColor(DesignSystem.Colors.secondaryText)
                Text(challenge.user_id)
                    .font(DesignSystem.Typography.label(size: 14, weight: .bold))
                    .foregroundColor(.white)
                
                Spacer()
                
                if let rail = challenge.paymentRail {
                    HStack(spacing: 4) {
                        Text(rail.icon)
                        Text(rail.displayName)
                            .font(DesignSystem.Typography.label(size: 12, weight: .bold))
                    }
                    .foregroundColor(rail == .solana ? DesignSystem.Colors.solanaAccent : DesignSystem.Colors.primaryAccent)
                }
            }
            
            HStack {
                Image(systemName: "clock.fill")
                    .font(.caption2)
                    .foregroundColor(DesignSystem.Colors.secondaryText)
                Text(challenge.formattedDate)
                    .font(DesignSystem.Typography.label(size: 12))
                    .foregroundColor(DesignSystem.Colors.secondaryText)
            }
        }
        .padding(16)
        .background(Color.black.opacity(0.3)) // Darker base for the list item
        .cornerRadius(16)
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .stroke(Color.white.opacity(0.05), lineWidth: 1)
        )
    }
}

struct DecisionBadge: View {
    let decision: PaymentDecision?
    
    var body: some View {
        Group {
            if let decision {
                HStack(spacing: 4) {
                    Text(decision.icon)
                    Text(decision.rawValue.capitalized)
                        .font(DesignSystem.Typography.label(size: 10, weight: .bold))
                }
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(badgeColor.opacity(0.2))
                .foregroundColor(badgeColor)
                .clipShape(Capsule())
            } else {
                Text("Pending")
                    .font(DesignSystem.Typography.label(size: 10, weight: .bold))
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.gray.opacity(0.2))
                    .foregroundColor(.gray)
                    .clipShape(Capsule())
            }
        }
    }
    
    private var badgeColor: Color {
        switch decision {
        case .approved: return DesignSystem.Colors.successAccent
        case .rejected: return DesignSystem.Colors.errorAccent
        case .retry: return DesignSystem.Colors.warningAccent
        case nil: return .gray
        }
    }
}

#Preview {
    NavigationStack {
        AuditView()
    }
    .preferredColorScheme(.dark)
}
