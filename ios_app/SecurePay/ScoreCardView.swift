import SwiftUI

struct ScoreCardView: View {
    let title: String
    let score: Double
    let icon: String
    let description: String
    
    @State private var animatedPercentage: Double = 0
    
    private var percentage: Double { min(max(score, 0), 1) }
    private var percentText: String { String(format: "%.1f%%", percentage * 100) }
    
    private var barColor: Color {
        if percentage > 0.7 { return DesignSystem.Colors.successAccent }
        if percentage > 0.4 { return DesignSystem.Colors.warningAccent }
        return DesignSystem.Colors.errorAccent
    }
    
    var body: some View {
        VStack(alignment: .center, spacing: 14) {
            
            // Circular Progress Ring
            ZStack {
                // Background Track
                Circle()
                    .stroke(Color.white.opacity(0.1), lineWidth: 8)
                
                // Progress Fill
                Circle()
                    .trim(from: 0, to: CGFloat(animatedPercentage))
                    .stroke(
                        barColor.shadow(.inner(color: .black.opacity(0.3), radius: 2)),
                        style: StrokeStyle(lineWidth: 8, lineCap: .round)
                    )
                    .rotationEffect(.degrees(-90))
                
                // Content inside ring
                VStack(spacing: 2) {
                    Text(icon)
                        .font(.title3)
                    Text(percentText)
                        .font(DesignSystem.Typography.monospacedData(size: 14))
                        .fontWeight(.bold)
                        .foregroundColor(.white)
                }
            }
            .frame(width: 80, height: 80)
            .shadow(color: barColor.opacity(0.3), radius: 8, x: 0, y: 4)
            
            // Text Details
            VStack(spacing: 4) {
                Text(title)
                    .font(DesignSystem.Typography.label(size: 14, weight: .bold))
                    .foregroundColor(.white)
                    .multilineTextAlignment(.center)
                
                Text(description)
                    .font(.system(size: 11))
                    .foregroundColor(DesignSystem.Colors.secondaryText)
                    .multilineTextAlignment(.center)
                    .lineLimit(2)
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity)
        .glassCard()
        .onAppear {
            withAnimation(.spring(response: 1.0, dampingFraction: 0.8).delay(0.1)) {
                animatedPercentage = percentage
            }
        }
    }
}

#Preview {
    HStack {
        ScoreCardView(title: "Liveness", score: 0.87, icon: "👁️", description: "Real person detection")
        ScoreCardView(title: "Deepfake", score: 0.12, icon: "🎭", description: "Generation prob")
    }
    .padding()
    .background(DesignSystem.Colors.background)
    .preferredColorScheme(.dark)
}
