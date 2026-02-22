import SwiftUI
import AVFoundation

struct SecurityCheckOverlay: View {
    let challengeData: ChallengeRequiredResponse
    let onComplete: (VerificationResponse) -> Void
    let onRetry: () -> Void
    let onCancel: () -> Void
    
    private let network = NetworkManager.shared
    @StateObject private var camera = CameraManager()
    
    // UI Navigation State
    @State private var hasAcceptedPermissions = false
    
    // Processing State
    @State private var isUploading = false
    @State private var errorMessage = ""
    @State private var recordingProgress: Double = 0
    @State private var recordingTimer: Timer?
    @State private var showSuccessTick = false
    
    @Environment(\.openURL) private var openURL
    
    var body: some View {
        ZStack {
            Rectangle()
                .fill(.ultraThinMaterial)
                .environment(\.colorScheme, .dark)
                .ignoresSafeArea()
            
            if !hasAcceptedPermissions {
                permissionsSplashScreen
            } else {
                verificationFlow
            }
        }
    }
    
    // MARK: - HIG Permissions Splash Screen
    
    private var permissionsSplashScreen: some View {
        VStack(alignment: .leading, spacing: 24) {
            Image(systemName: "faceid")
                .font(.system(size: 60, weight: .light))
                .foregroundColor(DesignSystem.Colors.primaryAccent)
                .padding(.top, 40)
            
            Text("Identity Verification")
                .font(.system(size: 34, weight: .bold, design: .rounded))
                .foregroundColor(.white)
            
            Text("To keep your account secure, SecurePay needs to verify it's really you.")
                .font(DesignSystem.Typography.label(size: 17))
                .foregroundColor(DesignSystem.Colors.secondaryText)
                .padding(.bottom, 20)
            
            // HIG standard list of why
            VStack(alignment: .leading, spacing: 24) {
                FeatureRow(icon: "camera.viewfinder", title: "Face Scan", subtitle: "We will use your TrueDepth camera to perform a brief liveness check.")
                FeatureRow(icon: "lock.shield", title: "Privacy First", subtitle: "Your biometric data is encrypted end-to-end and never stored on our servers.")
                FeatureRow(icon: "checkmark.seal", title: "Compliance", subtitle: "Required by financial regulations for high-risk transactions.")
            }
            
            Spacer()
            
            Button {
                DesignSystem.Haptics.heavyTap()
                withAnimation(.spring(response: 0.4, dampingFraction: 0.8)) {
                    hasAcceptedPermissions = true
                }
            } label: {
                Text("Continue")
                    .font(.system(size: 17, weight: .semibold))
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 16)
                    .background(DesignSystem.Colors.primaryAccent)
                    .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
            }
            .padding(.bottom, 12)
            
            Button("Cancel") {
                onCancel()
            }
            .font(.system(size: 17))
            .foregroundColor(DesignSystem.Colors.secondaryText)
            .frame(maxWidth: .infinity)
            .padding(.bottom, 20)
        }
        .padding(.horizontal, 32)
    }
    
    // MARK: - Active Verification Flow
    
    private var verificationFlow: some View {
        VStack(spacing: 40) {
            // Header
            VStack(spacing: 8) {
                Text("Verification")
                    .font(.system(size: 28, weight: .bold, design: .rounded))
                    .foregroundColor(.white)
                
                Text(challengeData.prompt)
                    .font(.system(size: 15))
                    .foregroundColor(DesignSystem.Colors.secondaryText)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 40)
            }
            .padding(.top, 60)
            
            // Content
            if camera.authorizationStatus == .denied || camera.authorizationStatus == .restricted {
                authorizationDeniedView
            } else {
                ZStack {
                    if showSuccessTick {
                        Image(systemName: "checkmark.circle.fill")
                            .font(.system(size: 120))
                            .foregroundColor(DesignSystem.Colors.successAccent)
                            .transition(.scale.combined(with: .opacity))
                    } else {
                        // iOS 17 Squircle Cutout
                        ZStack {
                            if camera.isReady {
                                CameraPreviewView(session: camera.session)
                            } else {
                                Color.black.opacity(0.3)
                                ProgressView().tint(.white)
                            }
                            
                            // SF Symbols 5 Variable Color Overlay
                            if camera.isRecording {
                                Image(systemName: "faceid")
                                    .font(.system(size: 140, weight: .ultraLight))
                                    .foregroundColor(DesignSystem.Colors.primaryAccent)
                                    .symbolEffect(.variableColor.iterative.dimInactiveLayers.nonReversing, options: .repeating)
                            } else {
                                Image(systemName: "faceid")
                                    .font(.system(size: 140, weight: .ultraLight))
                                    .foregroundColor(.white.opacity(0.2))
                            }
                        }
                        .frame(width: 250, height: 250)
                        .clipShape(RoundedRectangle(cornerRadius: 60, style: .continuous))
                        .overlay(
                            RoundedRectangle(cornerRadius: 60, style: .continuous)
                                .stroke(camera.isRecording ? DesignSystem.Colors.primaryAccent : Color.white.opacity(0.1), lineWidth: 3)
                        )
                        .shadow(color: camera.isRecording ? DesignSystem.Colors.primaryAccent.opacity(0.4) : .clear, radius: 30)
                    }
                }
                
                // Status / Actions
                VStack(spacing: 20) {
                    if isUploading {
                        ProgressView("Analyzing Biometrics...")
                            .tint(.white)
                            .foregroundColor(.white)
                    } else if !errorMessage.isEmpty {
                        ContentUnavailableView(
                            "Verification Failed",
                            systemImage: "exclamationmark.triangle",
                            description: Text(errorMessage)
                        )
                        .frame(height: 150)
                        
                        Button("Try Again") {
                            DesignSystem.Haptics.tap()
                            errorMessage = ""
                            onRetry()
                            camera.restartPreview()
                        }
                        .font(.system(size: 17, weight: .semibold))
                        .foregroundColor(DesignSystem.Colors.primaryAccent)
                    } else if !showSuccessTick {
                        Button {
                            DesignSystem.Haptics.heavyTap()
                            startRecording()
                        } label: {
                            Text(camera.isRecording ? "Scanning..." : "Start Scan")
                                .font(.system(size: 17, weight: .semibold))
                                .foregroundColor(camera.isRecording ? .black : .white)
                                .frame(width: 220, height: 56)
                                .background(camera.isRecording ? Color.white : DesignSystem.Colors.primaryAccent)
                                .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
                        }
                        .disabled(camera.isRecording || !camera.isReady)
                    }
                }
                .frame(height: 150)
            }
            
            Spacer()
            
            if !camera.isRecording && !isUploading && !showSuccessTick {
                Button("Cancel") { onCancel() }
                    .font(.system(size: 17))
                    .foregroundColor(DesignSystem.Colors.secondaryText)
                    .padding(.bottom, 30)
            }
        }
        .onAppear { camera.requestPermissionAndSetup() }
        .onDisappear { camera.stop() }
    }
    
    // MARK: - Subviews
    
    private var authorizationDeniedView: some View {
        ContentUnavailableView(
            "Camera Access Required",
            systemImage: "camera.badge.ellipsis",
            description: Text("SecurePay requires TrueDepth camera access in your device Settings to verify your identity.")
        )
        .overlay(alignment: .bottom) {
            Button("Open Settings") {
                if let url = URL(string: UIApplication.openSettingsURLString) {
                    openURL(url)
                }
            }
            .font(.system(size: 17, weight: .bold))
            .foregroundColor(.white)
            .frame(width: 200, height: 50)
            .background(DesignSystem.Colors.primaryAccent)
            .clipShape(Capsule())
            .padding(.bottom, 20)
        }
    }
    
    // MARK: - Actions
    
    private func startRecording() {
        errorMessage = ""
        camera.startRecording()
        recordingProgress = 0
        
        recordingTimer = Timer.scheduledTimer(withTimeInterval: 0.1, repeats: true) { timer in
            recordingProgress += 0.02
            
            // Haptic heartbeat
            if Int(recordingProgress * 50) % 5 == 0 {
                DesignSystem.Haptics.softPulse()
            }
            
            if recordingProgress >= 1.0 {
                timer.invalidate()
                recordingTimer = nil
                DesignSystem.Haptics.success()
                stopRecordingAndUpload()
            }
        }
    }
    
    private func stopRecordingAndUpload() {
        camera.stopRecording()
        
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            Task { await uploadVideo() }
        }
    }
    
    private func uploadVideo() async {
        guard let videoURL = camera.recordedVideoURL else { return }
        isUploading = true
        errorMessage = ""
        
        do {
            let result = try await network.uploadLivenessVideo(
                challengeId: challengeData.challenge_id,
                videoURL: videoURL
            )
            
            if result.paymentDecision == .approved {
                DesignSystem.Haptics.success()
                withAnimation(.spring(response: 0.5, dampingFraction: 0.6)) {
                    isUploading = false
                    showSuccessTick = true
                }
                
                DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                    onComplete(result)
                }
            } else if result.paymentDecision == .retry {
                DesignSystem.Haptics.error()
                isUploading = false
                errorMessage = result.reasons?.first ?? "Verification unclear. Please scan again in good lighting."
                // Do not dismiss; allow user to tap 'Try Again'
            } else {
                DesignSystem.Haptics.error()
                isUploading = false
                onComplete(result)
            }
        } catch let netError as NetworkError {
            DesignSystem.Haptics.error()
            errorMessage = netError.localizedDescription
            isUploading = false
            camera.recordedVideoURL = nil
            camera.restartPreview()
        } catch {
            DesignSystem.Haptics.error()
            errorMessage = error.localizedDescription
            isUploading = false
            camera.recordedVideoURL = nil
            camera.restartPreview()
        }
    }
}

// Helper for HIG Splash Screen
struct FeatureRow: View {
    let icon: String
    let title: String
    let subtitle: String
    
    var body: some View {
        HStack(alignment: .top, spacing: 16) {
            Image(systemName: icon)
                .font(.system(size: 28, weight: .light))
                .foregroundColor(DesignSystem.Colors.primaryAccent)
                .frame(width: 40)
            
            VStack(alignment: .leading, spacing: 4) {
                Text(title)
                    .font(.system(size: 17, weight: .semibold))
                    .foregroundColor(.white)
                Text(subtitle)
                    .font(.system(size: 15))
                    .foregroundColor(DesignSystem.Colors.secondaryText)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }
}

// MARK: - Camera Manager & Preview
@MainActor
class CameraManager: NSObject, ObservableObject, AVCaptureFileOutputRecordingDelegate {
    @Published var authorizationStatus: AVAuthorizationStatus = .notDetermined
    @Published var isReady = false
    @Published var isRecording = false
    @Published var recordedVideoURL: URL?
    
    let session = AVCaptureSession()
    private var output = AVCaptureMovieFileOutput()
    private var captureDeviceInput: AVCaptureDeviceInput?
    
    func requestPermissionAndSetup() {
        let currentStatus = AVCaptureDevice.authorizationStatus(for: .video)
        self.authorizationStatus = currentStatus
        
        switch currentStatus {
        case .notDetermined:
            Task {
                let granted = await AVCaptureDevice.requestAccess(for: .video)
                await MainActor.run {
                    self.authorizationStatus = granted ? .authorized : .denied
                    if granted { setupSession() }
                }
            }
        case .authorized:
            setupSession()
        case .denied, .restricted:
            break
        @unknown default:
            break
        }
    }
    
    private func setupSession() {
        guard !isReady else { return }
        session.beginConfiguration()
        session.sessionPreset = .high
        
        let deviceType: AVCaptureDevice.DeviceType
        if let _ = AVCaptureDevice.default(.builtInTrueDepthCamera, for: .video, position: .front) {
            deviceType = .builtInTrueDepthCamera
        } else {
            deviceType = .builtInWideAngleCamera
        }
        
        guard let device = AVCaptureDevice.default(deviceType, for: .video, position: .front),
              let input = try? AVCaptureDeviceInput(device: device) else {
            session.commitConfiguration()
            return
        }
        
        if session.canAddInput(input) {
            session.addInput(input)
            captureDeviceInput = input
        }
        if session.canAddOutput(output) { session.addOutput(output) }
        session.commitConfiguration()
        
        let sessionToStart = self.session
        Task.detached {
            sessionToStart.startRunning()
            await MainActor.run { self.isReady = true }
        }
    }
    
    func startRecording() {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("liveness_scan_\(Date().timeIntervalSince1970).mov")
        if let connection = output.connection(with: .video) {
            if connection.isVideoMirroringSupported {
                connection.isVideoMirrored = true
            }
        }
        output.startRecording(to: url, recordingDelegate: self)
        isRecording = true
    }
    
    func stopRecording() {
        output.stopRecording()
    }
    
    func restartPreview() {
        if !session.isRunning {
            let sessionToStart = self.session
            Task.detached { sessionToStart.startRunning() }
        }
    }
    
    func stop() {
        session.stopRunning()
        isReady = false
    }
    
    nonisolated func fileOutput(_ output: AVCaptureFileOutput, didFinishRecordingTo outputFileURL: URL, from connections: [AVCaptureConnection], error: Error?) {
        Task { @MainActor in
            self.isRecording = false
            if error == nil {
                self.recordedVideoURL = outputFileURL
            }
        }
    }
}

struct CameraPreviewView: UIViewRepresentable {
    let session: AVCaptureSession
    
    func makeUIView(context: Context) -> PreviewUIView {
        let view = PreviewUIView()
        view.session = session
        return view
    }
    
    func updateUIView(_ uiView: PreviewUIView, context: Context) {}
    
    class PreviewUIView: UIView {
        override class var layerClass: AnyClass { AVCaptureVideoPreviewLayer.self }
        var previewLayer: AVCaptureVideoPreviewLayer { layer as! AVCaptureVideoPreviewLayer }
        var session: AVCaptureSession? {
            didSet {
                previewLayer.session = session
                previewLayer.videoGravity = .resizeAspectFill
            }
        }
    }
}
