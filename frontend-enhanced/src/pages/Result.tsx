import { useLocation, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import ScoreCard from '../components/ScoreCard'
import AudioPlayer from '../components/AudioPlayer'
import ChallengeModal from '../components/ChallengeModal'
import { VerificationResponse, ApprovedResponse } from '../api'

export default function Result() {
  const location = useLocation()
  const navigate = useNavigate()
  const data = location.state as VerificationResponse | ApprovedResponse | null
  const [showRetryModal, setShowRetryModal] = useState(false)
  const [retryCount, setRetryCount] = useState(0)

  if (!data) {
    return (
      <div className="page-container">
        <div className="alert alert-error">
          <span className="alert-icon">⚠️</span>
          No payment data found. Please initiate a payment first.
        </div>
        <button className="btn btn-primary" onClick={() => navigate('/')}>
          Go to Home
        </button>
      </div>
    )
  }

  const isVerificationResponse = 'decision' in data
  const decision = isVerificationResponse ? data.decision : 'APPROVED'
  const scores = isVerificationResponse ? data.scores : null
  const reasons = isVerificationResponse ? data.reasons : []

  const getDecisionColor = () => {
    switch (decision) {
      case 'APPROVED':
        return 'success'
      case 'REJECTED':
        return 'error'
      case 'RETRY':
        return 'warning'
      default:
        return 'info'
    }
  }

  const getDecisionIcon = () => {
    switch (decision) {
      case 'APPROVED':
        return '✅'
      case 'REJECTED':
        return '❌'
      case 'RETRY':
        return '🔄'
      default:
        return 'ℹ️'
    }
  }

  const handleRetry = () => {
    if (retryCount < 1 && isVerificationResponse) {
      setShowRetryModal(true)
      setRetryCount(1)
    }
  }

  const handleRetryComplete = (result: any) => {
    setShowRetryModal(false)
    navigate('/result', { state: result, replace: true })
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">
          <span className="title-icon">📄</span>
          Payment Result
        </h1>
      </div>

      {/* Decision Banner */}
      <div className={`decision-banner decision-${getDecisionColor()}`}>
        <span className="decision-icon">{getDecisionIcon()}</span>
        <div className="decision-content">
          <h2 className="decision-title">{decision}</h2>
          <p className="decision-subtitle">
            {decision === 'APPROVED' && 'Payment processed successfully'}
            {decision === 'REJECTED' && 'Payment verification failed'}
            {decision === 'RETRY' && 'Please retry verification'}
          </p>
        </div>
      </div>

      {/* Payment Details */}
      <div className="card">
        <h3 className="card-title">
          <span className="title-icon">💳</span>
          Payment Details
        </h3>
        <div className="details-grid">
          <div className="detail-item">
            <span className="detail-label">Payment ID</span>
            <span className="detail-value">{data.payment_id}</span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Status</span>
            <span className={`badge badge-${data.payment_status === 'COMPLETED' ? 'success' : 'warning'}`}>
              {data.payment_status}
            </span>
          </div>
          <div className="detail-item">
            <span className="detail-label">Rail</span>
            <span className="detail-value">
              {data.rail === 'BANK' ? '🏦 Bank' : '⚡ Solana'}
            </span>
          </div>
        </div>
      </div>

      {/* Blockchain Transactions */}
      {data.rail === 'SOLANA' && (data.solana_tx || (isVerificationResponse && data.verification_receipt_tx)) && (
        <div className="card">
          <h3 className="card-title">
            <span className="title-icon">⛓️</span>
            Blockchain Transactions
          </h3>
          <div className="transaction-list">
            {data.solana_tx && (
              <div className="transaction-item">
                <div className="transaction-header">
                  <span className="transaction-label">💸 Payment Transfer</span>
                  <span className="transaction-badge">Solana</span>
                </div>
                <div className="transaction-hash">
                  <code>{data.solana_tx}</code>
                  <button
                    className="btn-copy"
                    onClick={() => navigator.clipboard.writeText(data.solana_tx!)}
                    title="Copy to clipboard"
                  >
                    📋
                  </button>
                </div>
              </div>
            )}
            {isVerificationResponse && data.verification_receipt_tx && (
              <div className="transaction-item">
                <div className="transaction-header">
                  <span className="transaction-label">📜 Verification Receipt</span>
                  <span className="transaction-badge">On-Chain Proof</span>
                </div>
                <div className="transaction-hash">
                  <code>{data.verification_receipt_tx}</code>
                  <button
                    className="btn-copy"
                    onClick={() => navigator.clipboard.writeText(data.verification_receipt_tx!)}
                    title="Copy to clipboard"
                  >
                    📋
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Verification Scores */}
      {scores && (
        <div className="scores-section">
          <h3 className="section-title">
            <span className="title-icon">📊</span>
            Verification Scores
          </h3>
          <div className="scores-grid">
            <ScoreCard
              title="Deepfake Mean"
              score={scores.deepfake_mean}
              icon="🎭"
              description="Average deepfake probability"
            />
            <ScoreCard
              title="Deepfake Variance"
              score={scores.deepfake_var}
              icon="📈"
              description="Consistency of deepfake detection"
            />
            <ScoreCard
              title="Liveness"
              score={scores.liveness}
              icon="👁️"
              description="Real person detection"
            />
            <ScoreCard
              title="Quality"
              score={scores.quality}
              icon="✨"
              description="Video quality score"
            />
            <ScoreCard
              title="Presage"
              score={scores.presage}
              icon="🧠"
              description="Behavioral analysis"
            />
          </div>
        </div>
      )}

      {/* Reasons */}
      {reasons && reasons.length > 0 && (
        <div className="card">
          <h3 className="card-title">
            <span className="title-icon">📋</span>
            Analysis Details
          </h3>
          <ul className="reasons-list">
            {reasons.map((reason, idx) => (
              <li key={idx} className="reason-item">
                <span className="reason-bullet">•</span>
                {reason}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Voice Audio */}
      {data.voice_audio && (
        <div className="card">
          <h3 className="card-title">
            <span className="title-icon">🔊</span>
            Voice Confirmation
          </h3>
          <AudioPlayer voiceAudio={data.voice_audio} />
        </div>
      )}

      {/* Actions */}
      <div className="actions-row">
        <button
          className="btn btn-secondary"
          onClick={() => navigate('/')}
        >
          ← New Payment
        </button>
        <button
          className="btn btn-secondary"
          onClick={() => navigate('/audit')}
        >
          📊 View Audit Log
        </button>
        {decision === 'RETRY' && retryCount < 1 && (
          <button
            className="btn btn-warning"
            onClick={handleRetry}
          >
            🔄 Retry Verification
          </button>
        )}
      </div>

      {/* Retry Modal */}
      {showRetryModal && isVerificationResponse && (
        <ChallengeModal
          challengeData={{
            status: 'CHALLENGE_REQUIRED',
            challenge_id: data.payment_id,
            prompt: 'Please retry your verification',
            expires_at: new Date(Date.now() + 60000).toISOString(),
            payment_id: data.payment_id,
            payment_status: data.payment_status,
            rail: data.rail,
          }}
          onComplete={handleRetryComplete}
          onCancel={() => setShowRetryModal(false)}
        />
      )}
    </div>
  )
}
