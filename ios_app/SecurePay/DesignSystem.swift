import SwiftUI

/// Centralized Design System for the SecurePay Premium UI
enum DesignSystem {
    // MARK: - Colors
    
    enum Colors {
        static let background = Color("BackgroundColor") // Very dark navy/black
        static let card = Color("CardBackground") // Slightly lighter surface
        static let secondaryText = Color("SecondaryText") // Muted text
        
        static let primaryAccent = Color("AccentColor") // Vibrant purple
        static let successAccent = Color.green
        static let warningAccent = Color.orange
        static let errorAccent = Color.red
        static let solanaAccent = Color.teal
        
        /// Dynamic mesh gradient background commonly used in hero sections
        static var meshBackground: some View {
            LinearGradient(
                colors: [background, Color(red: 0.1, green: 0.1, blue: 0.15)],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .ignoresSafeArea()
        }
    }
    
    // MARK: - Typography
    
    enum Typography {
        /// Large, friendly, rounded title font
        static func heroTitle(size: CGFloat = 34) -> Font {
            .system(size: size, weight: .bold, design: .rounded)
        }
        
        /// Sleek monospaced font for currency and IDs
        static func monospacedData(size: CGFloat) -> Font {
            .system(size: size, weight: .medium, design: .monospaced)
        }
        
        /// Standard label font
        static func label(size: CGFloat = 14, weight: Font.Weight = .medium) -> Font {
            .system(size: size, weight: weight, design: .default)
        }
    }
    
    // MARK: - Glassmorphism & Materials
    
    struct GlassmorphicPanel: ViewModifier {
        var cornerRadius: CGFloat
        var isHighlighted: Bool
        
        func body(content: Content) -> some View {
            content
                .padding()
                .background(.ultraThinMaterial)
                .environment(\.colorScheme, .dark)
                .cornerRadius(cornerRadius)
                .overlay(
                    RoundedRectangle(cornerRadius: cornerRadius)
                        .stroke(
                            isHighlighted ? Colors.primaryAccent.opacity(0.5) : Color.white.opacity(0.1),
                            lineWidth: isHighlighted ? 1.5 : 1
                        )
                )
                .shadow(color: Color.black.opacity(0.2), radius: 10, x: 0, y: 5)
        }
    }
    
    /// Gives any view a sleek frosted glass look
    static func glassPanel(cornerRadius: CGFloat = 20, isHighlighted: Bool = false) -> GlassmorphicPanel {
        GlassmorphicPanel(cornerRadius: cornerRadius, isHighlighted: isHighlighted)
    }
    
    // MARK: - Buttons
    
    struct GlowButtonModifier: ViewModifier {
        var color: Color
        var isPulsing: Bool
        
        @State private var pulseState = false
        
        func body(content: Content) -> some View {
            content
                .fontWeight(.bold)
                .foregroundColor(.white)
                .padding(.vertical, 16)
                .frame(maxWidth: .infinity)
                .background(
                    RoundedRectangle(cornerRadius: 16)
                        .fill(LinearGradient(colors: [color, color.opacity(0.8)], startPoint: .topLeading, endPoint: .bottomTrailing))
                )
                .shadow(color: color.opacity(pulseState ? 0.6 : 0.2), radius: pulseState ? 15 : 5, x: 0, y: pulseState ? 5 : 2)
                .scaleEffect(pulseState ? 1.02 : 1.0)
                .onAppear {
                    if isPulsing {
                        withAnimation(.easeInOut(duration: 1.5).repeatForever(autoreverses: true)) {
                            pulseState = true
                        }
                    }
                }
        }
    }
    
    // MARK: - Haptics
    
    enum Haptics {
        /// Light tap for interactive elements (e.g. toggles, segmented controls)
        static func tap() {
            let generator = UIImpactFeedbackGenerator(style: .light)
            generator.prepare()
            generator.impactOccurred()
        }
        
        /// Strong tap for major actions (e.g. submit button)
        static func heavyTap() {
            let generator = UIImpactFeedbackGenerator(style: .rigid)
            generator.prepare()
            generator.impactOccurred()
        }
        
        /// Soft pulse for continuous actions (e.g. scanning)
        static func softPulse() {
            let generator = UIImpactFeedbackGenerator(style: .soft)
            generator.prepare()
            generator.impactOccurred()
        }
        
        /// Success notification (e.g. payment approved)
        static func success() {
            let generator = UINotificationFeedbackGenerator()
            generator.prepare()
            generator.notificationOccurred(.success)
        }
        
        /// Error notification (e.g. payment rejected)
        static func error() {
            let generator = UINotificationFeedbackGenerator()
            generator.prepare()
            generator.notificationOccurred(.error)
        }
        
        /// Warning notification (e.g. retry challenge)
        static func warning() {
            let generator = UINotificationFeedbackGenerator()
            generator.prepare()
            generator.notificationOccurred(.warning)
        }
    }
}

// MARK: - View Extensions

extension View {
    func glassCard(cornerRadius: CGFloat = 20, isHighlighted: Bool = false) -> some View {
        self.modifier(DesignSystem.GlassmorphicPanel(cornerRadius: cornerRadius, isHighlighted: isHighlighted))
    }
    
    func glowingButton(color: Color = DesignSystem.Colors.primaryAccent, isPulsing: Bool = false) -> some View {
        self.modifier(DesignSystem.GlowButtonModifier(color: color, isPulsing: isPulsing))
    }
}
