import { useState, useRef, useEffect } from 'react'
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
    const expiresAt = new Date(challengeData.expires_at).getTime()
    const updateTimer = () => {
      const remaining = Math.max(0, Math.floor((expiresAt - Date.now()) / 1000))
      setTimeRemaining(remaining)
      if (remaining === 0 && stage === 'intro') {
        setError('Challenge expired')
      }
    }
    updateTimer()
    const interval = setInterval(updateTimer, 1000)
    return () => clearInterval(interval)
  }, [challengeData.expires_at, stage])

  const startRecording = async () => {
    try {
      setError('')
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 1280, height: 720 },
        audio: false,
      })

      streamRef.current = stream

      if (videoRef.current) {
        videoRef.current.srcObject = stream
      }

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

      setStage('recording')
      setCountdown(3)

      const countdownInterval = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(countdownInterval)
            mediaRecorder.start()

            setRecordingTime(0)
            const recordingInterval = setInterval(() => {
              setRecordingTime((prev) => {
                if (prev >= 2.9) {
                  clearInterval(recordingInterval)
                  mediaRecorder.stop()
                  stream.getTracks().forEach((track) => track.stop())
                  return 3
                }
                return prev + 0.1
              })
            }, 100)

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
      setStage('uploading')
      await new Promise((resolve) => setTimeout(resolve, 500))

      setStage('deepfake')
      await new Promise((resolve) => setTimeout(resolve, 800))

      setStage('presage')
      await new Promise((resolve) => setTimeout(resolve, 800))

      setStage('gemini')
      await new Promise((resolve) => setTimeout(resolve, 800))

      setStage('executing')

      const result = await uploadLivenessVideo(challengeData.challenge_id, blob)
      onComplete(result)

    } catch (err: any) {
      setError(err.message || 'Failed to upload video')
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
            <p>{challengeData.prompt}</p>
          </div>

          {/* Video Preview */}
          {stage !== 'intro' && stage !== 'uploading' && stage !== 'deepfake' && stage !== 'presage' && stage !== 'gemini' && stage !== 'executing' && (
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
          {(stage === 'uploading' || stage === 'deepfake' || stage === 'presage' || stage === 'gemini' || stage === 'executing') && (
            <div className="processing-container">
              <div className="processing-icon">{getStageInfo().icon}</div>
              <div className="processing-text">{getStageInfo().text}</div>
              <div className="processing-stages">
                <div className={`stage-item ${stage === 'uploading' || ['deepfake', 'presage', 'gemini', 'executing'].includes(stage) ? 'completed' : ''}`}>
                  <div className="stage-dot"></div>
                  <span>Uploading</span>
                </div>
                <div className={`stage-item ${['deepfake', 'presage', 'gemini', 'executing'].includes(stage) ? 'completed' : stage === 'uploading' ? 'active' : ''}`}>
                  <div className="stage-dot"></div>
                  <span>Deepfake/Liveness</span>
                </div>
                <div className={`stage-item ${['presage', 'gemini', 'executing'].includes(stage) ? 'completed' : stage === 'deepfake' ? 'active' : ''}`}>
                  <div className="stage-dot"></div>
                  <span>Presage Sensing</span>
                </div>
                <div className={`stage-item ${['gemini', 'executing'].includes(stage) ? 'completed' : stage === 'presage' ? 'active' : ''}`}>
                  <div className="stage-dot"></div>
                  <span>Gemini Check</span>
                </div>
                <div className={`stage-item ${stage === 'executing' ? 'active' : ''}`}>
                  <div className="stage-dot"></div>
                  <span>Executing</span>
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
