import { useState, useRef, useEffect, useCallback } from 'react'
import { uploadLivenessVideo, ChallengeRequiredResponse } from '../api'

interface Props {
  challengeData: ChallengeRequiredResponse
  onComplete: (result: any) => void
  onCancel: () => void
}

type Stage =
  | 'intro'
  | 'recording'
  | 'uploading'
  | 'deepfake'
  | 'presage'
  | 'qwen'
  | 'gemini'
  | 'executing'

export default function ChallengeModal({ challengeData, onComplete, onCancel }: Props) {
  const [stage, setStage] = useState<Stage>('intro')
  const [countdown, setCountdown] = useState(3)
  const [recordingTime, setRecordingTime] = useState(0)
  const [error, setError] = useState('')
  const [timeRemaining, setTimeRemaining] = useState(0)

  const videoRef = useRef<HTMLVideoElement>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const streamRef = useRef<MediaStream | null>(null)

  useEffect(() => {
    // Backend may send with or without timezone — ensure UTC parsing
    let expiryStr = challengeData.expires_at
    if (!expiryStr.endsWith('Z') && !expiryStr.includes('+')) {
      expiryStr += 'Z'  // treat as UTC
    }
    const expiresAt = new Date(expiryStr).getTime()
    const updateTimer = () => {
      const remaining = Math.max(0, Math.floor((expiresAt - Date.now()) / 1000))
      setTimeRemaining(remaining)
      // Only show expiry error on the intro screen, not during active recording/upload
      if (remaining === 0 && stage === 'intro') {
        setError('Challenge expired')
      }
    }
    updateTimer()
    const interval = setInterval(updateTimer, 1000)
    return () => clearInterval(interval)
  }, [challengeData.expires_at, stage])

  // Bind stream to video element AFTER React renders the <video> during 'recording' stage
  useEffect(() => {
    if (stage === 'recording' && videoRef.current && streamRef.current) {
      videoRef.current.srcObject = streamRef.current
    }
  }, [stage])

  const startRecording = async () => {
    try {
      setError('')
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 1280, height: 720 },
        audio: false,
      })

      streamRef.current = stream
      // Don't assign to videoRef here — the <video> element isn't rendered yet.
      // The useEffect above handles it once stage changes to 'recording'.

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'video/webm;codecs=vp8',
      })

      mediaRecorderRef.current = mediaRecorder
      chunksRef.current = []

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data)
        }
      }

      mediaRecorder.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: 'video/webm' })
        await uploadVideo(blob)
      }

      // Set stage FIRST so React renders the <video> element
      setStage('recording')
      setCountdown(3)

      const countdownInterval = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(countdownInterval)
            if (mediaRecorder.state === 'inactive') {
              mediaRecorder.start()

              setRecordingTime(0)
              const recordingInterval = setInterval(() => {
                setRecordingTime((prev) => {
                  if (prev >= 2.9) {
                    clearInterval(recordingInterval)
                    if (mediaRecorder.state === 'recording') {
                      mediaRecorder.stop()
                      stream.getTracks().forEach((track) => track.stop())
                    }
                    return 3
                  }
                  return prev + 0.1
                })
              }, 100)
            }

            return 0
          }
          return prev - 1
        })
      }, 1000)

    } catch (err: any) {
      setError(err.message || 'Failed to access camera')
    }
  }

  const uploadVideo = async (blob: Blob) => {
    try {
      // Start the actual network fetch in the background
      const uploadPromise = uploadLivenessVideo(challengeData.challenge_id, blob)

      // Run a guaranteed UI animation loop to stall the user while Qwen-VL processes
      const runAnimations = async () => {
        setStage('uploading')
        await new Promise((resolve) => setTimeout(resolve, 1500))

        setStage('deepfake')
        await new Promise((resolve) => setTimeout(resolve, 2500))

        setStage('presage')
        await new Promise((resolve) => setTimeout(resolve, 2000))

        setStage('qwen')
        await new Promise((resolve) => setTimeout(resolve, 3000))

        setStage('gemini')
        await new Promise((resolve) => setTimeout(resolve, 2000))

        setStage('executing')
      }

      // Await both the fake UI timers AND the actual HTTP request
      const [result] = await Promise.all([uploadPromise, runAnimations()])
      onComplete(result)

    } catch (err: any) {
      setError(err.message || 'Failed to analyze video logic')
      setStage('intro')
    }
  }

  const handleCancel = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop())
    }
    onCancel()
  }

  const getStageInfo = () => {
    switch (stage) {
      case 'uploading':
        return { icon: '📤', text: 'Uploading video...' }
      case 'deepfake':
        return { icon: '🎭', text: 'Analyzing deepfake & liveness...' }
      case 'presage':
        return { icon: '🧠', text: 'Running presage sensing...' }
      case 'qwen':
        return { icon: '👁️', text: 'Qwen-VL Vision spoof analysis...' }
      case 'gemini':
        return { icon: '✨', text: 'Gemini pattern check...' }
      case 'executing':
        return { icon: '⚡', text: `Executing ${challengeData.rail} payment...` }
      default:
        return { icon: '🎥', text: 'Ready to record' }
    }
  }

  return (
    <div className="modal-overlay">
      <div className="modal challenge-modal">
        <div className="modal-header">
          <h2 className="modal-title">
            <span className="title-icon">🔐</span>
            Biometric Verification
          </h2>
          <button className="btn-close" onClick={handleCancel}>✕</button>
        </div>

        <div className="modal-body">
          {/* Timer */}
          <div className="challenge-timer">
            <span className="timer-icon">⏱️</span>
            <span className="timer-text">
              Expires in {Math.floor(timeRemaining / 60)}:{(timeRemaining % 60).toString().padStart(2, '0')}
            </span>
          </div>

          {/* Prompt */}
          <div className="challenge-prompt">
            {challengeData.security_message && (
              <div className="security-alert">
                <span className="alert-icon">🛡️</span>
                <p>{challengeData.security_message}</p>
              </div>
            )}
            <p className="camera-instruction">{challengeData.prompt}</p>
          </div>

          {/* Video Preview — visible during recording */}
          {stage === 'recording' && (
            <div className="video-container">
              <video
                ref={videoRef}
                autoPlay
                muted
                playsInline
                className="video-preview"
              />

              {countdown > 0 && (
                <div className="countdown-overlay">
                  <div className="countdown-number">{countdown}</div>
                </div>
              )}

              {countdown === 0 && recordingTime < 3 && (
                <div className="recording-overlay">
                  <div className="recording-indicator">
                    <span className="recording-dot"></span>
                    <span className="recording-text">Recording {recordingTime.toFixed(1)}s</span>
                  </div>
                  <div className="progress-bar">
                    <div
                      className="progress-fill"
                      style={{ width: `${(recordingTime / 3) * 100}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Processing Stages */}
          {(stage === 'uploading' || stage === 'deepfake' || stage === 'presage' || stage === 'qwen' || stage === 'gemini' || stage === 'executing') && (
            <div className="processing-container">
              <div className="processing-icon">{getStageInfo().icon}</div>
              <div className="processing-text">{getStageInfo().text}</div>
              <div className="processing-stages">
                <div className={`stage-item ${stage === 'uploading' || ['deepfake', 'presage', 'qwen', 'gemini', 'executing'].includes(stage) ? 'completed' : ''}`}>
                  <div className="stage-dot"></div>
                  <span>Uploading</span>
                </div>
                <div className={`stage-item ${['deepfake', 'presage', 'qwen', 'gemini', 'executing'].includes(stage) ? 'completed' : stage === 'uploading' ? 'active' : ''}`}>
                  <div className="stage-dot"></div>
                  <span>Liveness</span>
                </div>
                <div className={`stage-item ${['presage', 'qwen', 'gemini', 'executing'].includes(stage) ? 'completed' : stage === 'deepfake' ? 'active' : ''}`}>
                  <div className="stage-dot"></div>
                  <span>Sensing</span>
                </div>
                <div className={`stage-item ${['qwen', 'gemini', 'executing'].includes(stage) ? 'completed' : stage === 'presage' ? 'active' : ''}`}>
                  <div className="stage-dot"></div>
                  <span>Vision</span>
                </div>
                <div className={`stage-item ${['gemini', 'executing'].includes(stage) ? 'completed' : stage === 'qwen' ? 'active' : ''}`}>
                  <div className="stage-dot"></div>
                  <span>Reasoning</span>
                </div>
                <div className={`stage-item ${stage === 'executing' ? 'active' : ''}`}>
                  <div className="stage-dot"></div>
                  <span>Complete</span>
                </div>
              </div>
              <div className="spinner-large"></div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="alert alert-error">
              <span className="alert-icon">⚠️</span>
              {error}
            </div>
          )}

          {/* Instructions */}
          {stage === 'intro' && (
            <div className="instructions">
              <h3 className="instructions-title">📋 Instructions</h3>
              <ul className="instructions-list">
                <li>Position your face clearly in the camera frame</li>
                <li>Ensure good lighting and remove any obstructions</li>
                <li>Recording will last 3 seconds</li>
                <li>Follow the prompt above during recording</li>
                <li>Stay still and look directly at the camera</li>
              </ul>
            </div>
          )}
        </div>

        <div className="modal-footer">
          {stage === 'intro' && (
            <>
              <button className="btn btn-secondary" onClick={handleCancel}>
                Cancel
              </button>
              <button
                className="btn btn-primary"
                onClick={startRecording}
                disabled={timeRemaining === 0}
              >
                <span>🎥</span>
                Start Verification
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
