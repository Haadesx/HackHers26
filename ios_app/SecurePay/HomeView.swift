import SwiftUI

struct HomeView: View {
    @StateObject private var network = NetworkManager.shared
    @State private var showSendFlow = false
    @State private var challenges: [Challenge] = []
    
    var body: some View {
        NavigationStack {
            ZStack {
                DesignSystem.Colors.meshBackground
                
                ScrollView(showsIndicators: false) {
                    VStack(spacing: 30) {
                        
                        // User Header
                        headerSection
                        
                        // Fake Digital Card + Balance
                        secureCardSection
                        
                        // Actions
                        actionButtonsSection
                        
                        // Integrated Feed
                        transactionsFeed
                    }
                    .padding(.horizontal, 24)
                    .padding(.bottom, 100)
                }
                .refreshable {
                    DesignSystem.Haptics.tap()
                    await loadFeed()
                }
            }
            .navigationBarHidden(true)
            .task {
                await loadFeed()
            }
            .fullScreenCover(isPresented: $showSendFlow) {
                SendMoneyView(onDismiss: {
                    showSendFlow = false
                    Task { await loadFeed() } // Refresh log when they come back
                })
            }
        }
    }
    
    // MARK: - Subviews
    
    private var headerSection: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text("Good evening,")
                    .font(DesignSystem.Typography.label(size: 16))
                    .foregroundColor(DesignSystem.Colors.secondaryText)
                Text("SecurePay User")
                    .font(DesignSystem.Typography.heroTitle(size: 24))
                    .foregroundColor(.white)
            }
            Spacer()
            
            // Avatar
            Circle()
                .fill(DesignSystem.Colors.primaryAccent.opacity(0.3))
                .frame(width: 48, height: 48)
                .overlay(
                    Image(systemName: "person.fill")
                        .foregroundColor(DesignSystem.Colors.primaryAccent)
                )
                .overlay(Circle().stroke(Color.white.opacity(0.1), lineWidth: 1))
        }
        .padding(.top, 20)
    }
    
    private var secureCardSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Image(systemName: "shield.checkered")
                    .font(.system(size: 20))
                Text("SecureCard")
                    .font(DesignSystem.Typography.label(size: 16, weight: .bold))
                Spacer()
                Image(systemName: "wave.3.right")
            }
            .foregroundColor(.white)
            
            Spacer()
            
            VStack(alignment: .leading, spacing: 4) {
                Text("Balance")
                    .font(DesignSystem.Typography.label(size: 14))
                    .foregroundColor(.white.opacity(0.8))
                
                Text("$12,450.00")
                    .font(.system(size: 40, weight: .bold, design: .rounded))
                    .foregroundColor(.white)
                    .shadow(color: .white.opacity(0.3), radius: 10, x: 0, y: 0)
            }
            
            HStack {
                Text("•••• 4092")
                    .font(DesignSystem.Typography.monospacedData(size: 14))
                    .foregroundColor(.white.opacity(0.8))
                Spacer()
                Image(systemName: "applelogo")
                    .font(.system(size: 18))
                    .foregroundColor(.white)
            }
            .padding(.top, 10)
        }
        .padding(24)
        .frame(height: 220)
        .background(
            ZStack {
                DesignSystem.Colors.card
                LinearGradient(
                    colors: [DesignSystem.Colors.primaryAccent.opacity(0.6), DesignSystem.Colors.solanaAccent.opacity(0.3)],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
                .opacity(0.5)
            }
        )
        .clipShape(RoundedRectangle(cornerRadius: 24))
        .shadow(color: DesignSystem.Colors.primaryAccent.opacity(0.4), radius: 20, x: 0, y: 10)
        .overlay(
            RoundedRectangle(cornerRadius: 24)
                .stroke(Color.white.opacity(0.15), lineWidth: 1)
        )
        .onTapGesture {
            DesignSystem.Haptics.tap()
        }
    }
    
    private var actionButtonsSection: some View {
        Button {
            DesignSystem.Haptics.heavyTap()
            showSendFlow = true
        } label: {
            HStack(spacing: 8) {
                Image(systemName: "paperplane.fill")
                    .font(.system(size: 20, weight: .bold))
                Text("Send Secure Payment")
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
    

    
    private var transactionsFeed: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                Text("Recent Activity")
                    .font(DesignSystem.Typography.label(size: 18, weight: .bold))
                    .foregroundColor(.white)
                Spacer()
                Button("View All") { }
                    .font(DesignSystem.Typography.label(size: 14))
                    .foregroundColor(DesignSystem.Colors.primaryAccent)
            }
            
            if challenges.isEmpty {
                VStack(spacing: 12) {
                    Image(systemName: "tray")
                        .font(.system(size: 30))
                    Text("No recent transfers.")
                }
                .foregroundColor(DesignSystem.Colors.secondaryText)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 40)
            } else {
                LazyVStack(spacing: 12) {
                    // Show max 5 on home
                    ForEach(challenges.prefix(5)) { challenge in
                        NavigationLink(destination: AuditDetailView(challengeId: challenge.id)) {
                            FeedItemRow(challenge: challenge)
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
        }
        .padding(.top, 10)
    }
    
    // MARK: - Actions
    
    private func loadFeed() async {
        do {
            challenges = try await network.getChallenges()
        } catch { } // fail silently on home feed
    }
}

// Minimal row for Home Feed
struct FeedItemRow: View {
    let challenge: Challenge
    
    var body: some View {
        HStack(spacing: 16) {
            Circle()
                .fill(Color.black.opacity(0.4))
                .frame(width: 44, height: 44)
                .overlay(
                    Image(systemName: challenge.paymentRail == .bank ? "building.columns.fill" : "bolt.fill")
                        .foregroundColor(challenge.paymentRail == .solana ? DesignSystem.Colors.solanaAccent : DesignSystem.Colors.primaryAccent)
                )
            
            VStack(alignment: .leading, spacing: 4) {
                Text("To \(challenge.user_id)")
                    .font(DesignSystem.Typography.label(size: 15, weight: .bold))
                    .foregroundColor(.white)
                Text(challenge.formattedDate)
                    .font(DesignSystem.Typography.label(size: 12))
                    .foregroundColor(DesignSystem.Colors.secondaryText)
            }
            
            Spacer()
            
            VStack(alignment: .trailing, spacing: 4) {
                Text(challenge.paymentDecision?.rawValue.capitalized ?? "Pending")
                    .font(DesignSystem.Typography.label(size: 14, weight: .bold))
                    .foregroundColor(colorForDecision)
                Text(String(challenge.id.prefix(6)))
                    .font(DesignSystem.Typography.monospacedData(size: 10))
                    .foregroundColor(DesignSystem.Colors.secondaryText)
            }
        }
        .padding(16)
        .glassCard(cornerRadius: 16)
    }
    
    private var colorForDecision: Color {
        switch challenge.paymentDecision {
        case .approved: return DesignSystem.Colors.successAccent
        case .rejected: return DesignSystem.Colors.errorAccent
        case .retry: return DesignSystem.Colors.warningAccent
        case nil: return .gray
        }
    }
}

#Preview {
    HomeView()
        .preferredColorScheme(.dark)
}
