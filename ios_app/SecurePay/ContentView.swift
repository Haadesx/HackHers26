import SwiftUI

struct ContentView: View {
    @StateObject private var network = NetworkManager.shared
    @State private var isAuthenticated = false
    
    var body: some View {
        Group {
            if isAuthenticated {
                // The new dashboard-driven home
                HomeView()
            } else {
                // Simple Login view mirroring original api.ts
                LoginView(onAuthSuccess: {
                    isAuthenticated = true
                })
            }
        }
    }
}

// Simple mock login keeping with the new dark aesthetic
struct LoginView: View {
    var onAuthSuccess: () -> Void
    @State private var isSpinning = false
    
    var body: some View {
        ZStack {
            DesignSystem.Colors.meshBackground
            
            VStack(spacing: 40) {
                Spacer()
                
                // Logo placeholder
                ZStack {
                    Circle()
                        .fill(DesignSystem.Colors.primaryAccent.opacity(0.2))
                        .frame(width: 120, height: 120)
                    
                    Image(systemName: "lock.shield.fill")
                        .font(.system(size: 60))
                        .foregroundColor(DesignSystem.Colors.primaryAccent)
                }
                
                VStack(spacing: 8) {
                    Text("SecurePay")
                        .font(DesignSystem.Typography.heroTitle(size: 36))
                        .foregroundColor(.white)
                    
                    Text("AI-Verified Payments")
                        .font(DesignSystem.Typography.label(size: 16))
                        .foregroundColor(DesignSystem.Colors.secondaryText)
                }
                
                Spacer()
                
                Button {
                    DesignSystem.Haptics.heavyTap()
                    isSpinning = true
                    DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                        DesignSystem.Haptics.success()
                        onAuthSuccess()
                    }
                } label: {
                    HStack {
                        if isSpinning {
                            ProgressView().tint(.white)
                        } else {
                            Text("Unlock")
                        }
                    }
                    .font(DesignSystem.Typography.label(size: 18, weight: .bold))
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 18)
                    .background(DesignSystem.Colors.primaryAccent)
                    .foregroundColor(.white)
                    .clipShape(Capsule())
                    .shadow(color: DesignSystem.Colors.primaryAccent.opacity(0.4), radius: 15)
                }
                .disabled(isSpinning)
                .padding(.horizontal, 30)
                .padding(.bottom, 60)
            }
        }
        .onAppear {
            _ = NetworkManager.getDeviceId() // trigger generation
        }
    }
}

#Preview {
    ContentView()
        .preferredColorScheme(.dark)
}
