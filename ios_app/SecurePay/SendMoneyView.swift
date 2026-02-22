import SwiftUI

struct SendMoneyView: View {
    var onDismiss: () -> Void
    
    private let network = NetworkManager.shared
    let deviceId = NetworkManager.getDeviceId()
    
    // Payment Rail
    @State private var rail: PaymentRail = .bank
    
    // Payment Details
    @State private var amountString = ""
    @State private var recipientName = ""
    
    // Bank Details
    @State private var accountNumber = ""
    @State private var routingNumber = ""
    @State private var showAccountNumber = false
    
    // Solana Details
    @State private var recipientAddress = ""
    
    // State
    @State private var isLoading = false
    @State private var errorMessage = ""
    
    // Navigation
    @State private var showChallenge = false
    @State private var challengeData: ChallengeRequiredResponse?
    @State private var approvedData: ApprovedPaymentResponse?
    @State private var showResult = false
    @State private var verificationResult: VerificationResponse?
    
    private var isFormValid: Bool {
        guard let amount = Double(amountString), amount > 0 else { return false }
        if recipientName.isEmpty { return false }
        if rail == .bank {
            return !accountNumber.isEmpty && !routingNumber.isEmpty
        } else {
            return !recipientAddress.isEmpty
        }
    }
    
    var body: some View {
        NavigationStack {
            mainContent
                .navigationTitle("Payment Liveness")
                .navigationBarTitleDisplayMode(.large)
                .toolbar { toolbarContent }
                .fullScreenCover(isPresented: $showChallenge) { challengeOverlay }
                .navigationDestination(isPresented: $showResult) { resultDestination }
                .navigationDestination(isPresented: approvedBinding) { approvedDestination }
        }
    }
    
    private var challengeOverlay: some View {
        Group {
            if let data = challengeData {
                SecurityCheckOverlay(
                    challengeData: data,
                    onComplete: { result in
                        self.verificationResult = result
                        self.showChallenge = false
                        
                        // Use DispatchQueue to avoid NavigationStack transition conflicts
                        DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
                            if result.paymentDecision == .approved {
                                self.approvedData = ApprovedPaymentResponse(
                                    status: result.status,
                                    payment_id: result.payment_id,
                                    payment_status: result.payment_status,
                                    rail: result.rail,
                                    solana_tx: result.solana_tx
                                )
                            } else if result.paymentDecision == .rejected {
                                self.showResult = true
                            }
                            // .retry is handled internally by SecurityCheckOverlay now
                        }
                    },
                    onRetry: {
                        // The camera resets itself inside the overlay. 
                        // We just log that a retry occurred.
                        print("User hit retry inside SecurityCheckOverlay.")
                    },
                    onCancel: {
                        self.showChallenge = false
                        self.errorMessage = "Verification cancelled."
                    }
                )
            } else {
                Text("Error Loading Challenge")
                    .foregroundColor(.white)
            }
        }
    }            
    
    // MARK: - Main Content
    
    private var mainContent: some View {
        ZStack {
            DesignSystem.Colors.background.ignoresSafeArea()
            
            VStack(spacing: 0) {
                // Native iOS custom back button for Swipe Back support
                HStack {
                    Button {
                        onDismiss()
                    } label: {
                        HStack(spacing: 5) {
                            Image(systemName: "chevron.left")
                                .font(.system(size: 20, weight: .semibold))
                            Text("Back")
                                .font(.system(size: 17))
                        }
                        .foregroundColor(DesignSystem.Colors.primaryAccent)
                    }
                    Spacer()
                }
                .padding(.horizontal, 16)
                .padding(.top, 10)
                
                ScrollView(showsIndicators: false) {
                    VStack(spacing: 20) {
                        deviceChip
                        railSection
                        paymentDetailsSection
                        bankOrSolanaSection
                        errorSection
                    }
                    .padding(.horizontal, 20)
                    .padding(.bottom, 20)
                }
                
                // Fixed bottom button — always visible above keyboard
                sendButton
                    .padding(.horizontal, 20)
                    .padding(.bottom, 16)
                    .padding(.top, 8)
                    .background(
                        DesignSystem.Colors.background
                            .shadow(color: .black.opacity(0.5), radius: 10, y: -5)
                            .ignoresSafeArea(.all, edges: .bottom)
                    )
            }
        }
        .onTapGesture { UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder), to: nil, from: nil, for: nil) }
    }
    
    // MARK: - Device Chip
    
    private var deviceChip: some View {
        HStack {
            HStack(spacing: 8) {
                Image(systemName: "cpu")
                    .font(.system(size: 12))
                Text("Device: \(String(deviceId.suffix(10)))...")
                    .font(DesignSystem.Typography.label(size: 13))
            }
            .foregroundColor(DesignSystem.Colors.secondaryText)
            .padding(.horizontal, 14)
            .padding(.vertical, 8)
            .background(DesignSystem.Colors.card)
            .clipShape(Capsule())
            
            Spacer()
        }
        .padding(.top, 8)
    }
    
    // MARK: - Rail Section
    
    private var railSection: some View {
        FormSection(title: "Payment Rail", icon: "arrow.left.arrow.right") {
            HStack(spacing: 0) {
                ForEach(PaymentRail.allCases, id: \.self) { option in
                    Button {
                        withAnimation(.spring(response: 0.3)) { rail = option }
                        DesignSystem.Haptics.tap()
                    } label: {
                        railLabel(for: option)
                    }
                }
            }
            .padding(4)
            .background(Color.black.opacity(0.3))
            .clipShape(Capsule())
        }
    }
    
    private func railLabel(for option: PaymentRail) -> some View {
        HStack(spacing: 6) {
            Text(option.icon)
            Text(option.displayName)
                .font(DesignSystem.Typography.label(size: 14, weight: .bold))
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 12)
        .background(rail == option ? (option == .solana ? DesignSystem.Colors.solanaAccent : DesignSystem.Colors.primaryAccent) : Color.clear)
        .foregroundColor(rail == option ? .white : DesignSystem.Colors.secondaryText)
        .contentShape(Capsule())
        .clipShape(Capsule())
    }
    
    // MARK: - Payment Details
    
    private var paymentDetailsSection: some View {
        FormSection(title: "Payment Details", icon: "dollarsign.circle") {
            VStack(spacing: 16) {
                FormInputField(
                    label: "Amount",
                    text: $amountString,
                    icon: "dollarsign",
                    placeholder: "0.00",
                    keyboardType: .decimalPad
                )
                
                FormInputField(
                    label: "Recipient Name",
                    text: $recipientName,
                    icon: "person",
                    placeholder: "Enter name"
                )
            }
        }
    }
    
    // MARK: - Bank / Solana Section
    
    @ViewBuilder
    private var bankOrSolanaSection: some View {
        if rail == .bank {
            bankDetailsSection
        } else {
            solanaDetailsSection
        }
    }
    
    private var bankDetailsSection: some View {
        FormSection(title: "Bank Details", icon: "building.columns") {
            VStack(spacing: 16) {
                accountNumberField
                
                FormInputField(
                    label: "Routing Number",
                    text: $routingNumber,
                    icon: "building.2",
                    placeholder: "Enter routing number",
                    keyboardType: .numberPad
                )
            }
        }
    }
    
    private var accountNumberField: some View {
        HStack(spacing: 12) {
            Image(systemName: "creditcard")
                .foregroundColor(DesignSystem.Colors.secondaryText)
                .frame(width: 24)
            
            VStack(alignment: .leading, spacing: 4) {
                Text("Account Number")
                    .font(.system(size: 12))
                    .foregroundColor(DesignSystem.Colors.secondaryText)
                
                Group {
                    if showAccountNumber {
                        TextField("Enter account number", text: $accountNumber)
                            .keyboardType(.numberPad)
                    } else {
                        SecureField("Enter account number", text: $accountNumber)
                    }
                }
                .font(DesignSystem.Typography.label(size: 16))
                .foregroundColor(.white)
            }
            
            Button {
                showAccountNumber.toggle()
                DesignSystem.Haptics.tap()
            } label: {
                Image(systemName: showAccountNumber ? "eye" : "eye.slash")
                    .foregroundColor(DesignSystem.Colors.secondaryText)
            }
        }
        .padding(.vertical, 14)
        .padding(.horizontal, 16)
        .background(Color.black.opacity(0.3))
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .stroke(Color.white.opacity(0.08), lineWidth: 1)
        )
    }
    
    private var solanaDetailsSection: some View {
        FormSection(title: "Solana Details", icon: "link") {
            FormInputField(
                label: "Recipient Wallet Address",
                text: $recipientAddress,
                icon: "wallet.pass",
                placeholder: "Enter SOL wallet address"
            )
        }
    }
    
    // MARK: - Error Section
    
    @ViewBuilder
    private var errorSection: some View {
        if !errorMessage.isEmpty {
            Text(errorMessage)
                .font(DesignSystem.Typography.label(size: 14))
                .foregroundColor(DesignSystem.Colors.errorAccent)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 4)
        }
    }
    
    // MARK: - Send Button (Fixed Bottom)
    
    private var sendButton: some View {
        Button {
            UIApplication.shared.sendAction(#selector(UIResponder.resignFirstResponder), to: nil, from: nil, for: nil)
            DesignSystem.Haptics.heavyTap()
            Task { await initiateTransfer() }
        } label: {
            HStack(spacing: 10) {
                if isLoading {
                    ProgressView().tint(.white)
                    Text("Connecting to server...")
                } else {
                    Image(systemName: "paperplane.fill")
                    Text("Send Payment")
                }
            }
            .font(DesignSystem.Typography.label(size: 18, weight: .bold))
            .foregroundColor(.white)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 18)
            .background(
                isFormValid
                    ? LinearGradient(colors: [DesignSystem.Colors.primaryAccent, DesignSystem.Colors.primaryAccent.opacity(0.8)], startPoint: .leading, endPoint: .trailing)
                    : LinearGradient(colors: [DesignSystem.Colors.card, DesignSystem.Colors.card], startPoint: .leading, endPoint: .trailing)
            )
            .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
            .shadow(color: isFormValid ? DesignSystem.Colors.primaryAccent.opacity(0.4) : .clear, radius: 12)
        }
        .disabled(!isFormValid || isLoading)
        .opacity(isFormValid ? 1 : 0.5)
    }
    
    // MARK: - Toolbar
    
    @ToolbarContentBuilder
    private var toolbarContent: some ToolbarContent {
        ToolbarItem(placement: .navigationBarLeading) {
            Button { onDismiss() } label: {
                Image(systemName: "xmark.circle.fill")
                    .foregroundColor(DesignSystem.Colors.secondaryText)
                    .font(.title3)
            }
        }
        ToolbarItem(placement: .navigationBarTrailing) {
            NavigationLink(destination: AuditView()) {
                Image(systemName: "clock.arrow.circlepath")
                    .foregroundColor(DesignSystem.Colors.secondaryText)
            }
        }
    }
    
    // MARK: - Navigation Destinations
    

    
    @ViewBuilder
    private var resultDestination: some View {
        if let result = verificationResult {
            ResultView(verificationResponse: result, onGoHome: {
                onDismiss()
            })
        }
    }
    
    @ViewBuilder
    private var approvedDestination: some View {
        if let approved = approvedData {
            ResultView(approvedResponse: approved, onGoHome: {
                onDismiss()
            })
        }
    }
    
    private var approvedBinding: Binding<Bool> {
        Binding(
            get: { approvedData != nil && !showResult },
            set: { if !$0 { approvedData = nil } }
        )
    }
    
    // MARK: - Network
    
    private func initiateTransfer() async {
        errorMessage = ""
        isLoading = true
        defer { isLoading = false }
        
        let request = InitiatePaymentRequest(
            user_id: recipientName,
            rail: rail.rawValue,
            amount: Double(amountString) ?? 0,
            recipient_id: rail == .bank ? accountNumber : nil,
            recipient_address: rail == .solana ? recipientAddress : nil,
            note: routingNumber,
            device_id: deviceId,
            user_agent: "SecurePay-iOS-Premium/2.0",
            ip: nil
        )
        
        do {
            let result = try await network.initiatePayment(request: request)
            switch result {
            case .approved(let response):
                DesignSystem.Haptics.success()
                approvedData = response
            case .challengeRequired(let response):
                DesignSystem.Haptics.warning()
                challengeData = response
                showChallenge = true
            }
        } catch {
            DesignSystem.Haptics.error()
            errorMessage = error.localizedDescription
        }
    }
}

// MARK: - Form Section Card

struct FormSection<Content: View>: View {
    let title: String
    let icon: String
    @ViewBuilder let content: Content
    
    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack(spacing: 8) {
                Image(systemName: icon)
                    .foregroundColor(DesignSystem.Colors.primaryAccent)
                    .font(.system(size: 14, weight: .semibold))
                Text(title)
                    .font(DesignSystem.Typography.label(size: 16, weight: .bold))
                    .foregroundColor(.white)
            }
            
            content
        }
        .padding(20)
        .background(DesignSystem.Colors.card)
        .clipShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .stroke(Color.white.opacity(0.06), lineWidth: 1)
        )
    }
}

// MARK: - Form Input Field

struct FormInputField: View {
    let label: String
    @Binding var text: String
    let icon: String
    var placeholder: String = ""
    var keyboardType: UIKeyboardType = .default
    
    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .foregroundColor(DesignSystem.Colors.secondaryText)
                .frame(width: 24)
            
            VStack(alignment: .leading, spacing: 4) {
                Text(label)
                    .font(.system(size: 12))
                    .foregroundColor(DesignSystem.Colors.secondaryText)
                
                TextField(placeholder, text: $text)
                    .font(DesignSystem.Typography.label(size: 16))
                    .foregroundColor(.white)
                    .keyboardType(keyboardType)
                    .autocorrectionDisabled()
                    .textInputAutocapitalization(.never)
            }
        }
        .padding(.vertical, 14)
        .padding(.horizontal, 16)
        .background(Color.black.opacity(0.3))
        .clipShape(RoundedRectangle(cornerRadius: 12, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .stroke(Color.white.opacity(0.08), lineWidth: 1)
        )
    }
}
