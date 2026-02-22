import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { initiatePayment, getDeviceId, InitiatePaymentResponse } from '../api'
import ChallengeModal from '../components/ChallengeModal'

export default function Home() {
  const navigate = useNavigate()
  const [rail, setRail] = useState<'BANK' | 'SOLANA'>('BANK')
  const [userId, setUserId] = useState('demo_user')
  const [amount, setAmount] = useState('')
  const [recipientId, setRecipientId] = useState('')
  const [recipientAddress, setRecipientAddress] = useState('')
  const [note, setNote] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [challengeData, setChallengeData] = useState<InitiatePaymentResponse | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const payload = {
        user_id: userId,
        rail,
        amount: parseFloat(amount),
        recipient_id: rail === 'BANK' ? recipientId : undefined,
        recipient_address: rail === 'SOLANA' ? recipientAddress : null,
        note,
        device_id: getDeviceId(),
        user_agent: navigator.userAgent,
        ip: null,
      }

      const response = await initiatePayment(payload)

      if (response.status === 'APPROVED') {
        navigate('/result', { state: response })
      } else if (response.status === 'CHALLENGE_REQUIRED') {
        setChallengeData(response)
      }
    } catch (err: any) {
      setError(err.message || 'Failed to initiate payment')
    } finally {
      setLoading(false)
    }
  }

  const handleChallengeComplete = (result: any) => {
    setChallengeData(null)
    navigate('/result', { state: result })
  }

  const handleChallengeCancel = () => {
    setChallengeData(null)
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">
          <span className="title-icon">💳</span>
          Initiate Payment
        </h1>
        <p className="page-subtitle">
          Secure payment processing with biometric verification
        </p>
      </div>

      <div className="card payment-card">
        <form onSubmit={handleSubmit} className="payment-form">
          {/* User ID */}
          <div className="form-group">
            <label className="form-label">
              <span className="label-icon">👤</span>
              User ID
            </label>
            <input
              type="text"
              className="form-input"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              placeholder="Enter user ID"
              required
            />
          </div>

          {/* Rail Selector */}
          <div className="form-group">
            <label className="form-label">
              <span className="label-icon">🛤️</span>
              Payment Rail
            </label>
            <div className="rail-selector">
              <button
                type="button"
                className={`rail-option ${rail === 'BANK' ? 'active' : ''}`}
                onClick={() => setRail('BANK')}
              >
                <span className="rail-icon">🏦</span>
                <span className="rail-name">Bank Transfer</span>
                <span className="rail-desc">Traditional banking via Fiserv</span>
              </button>
              <button
                type="button"
                className={`rail-option ${rail === 'SOLANA' ? 'active' : ''}`}
                onClick={() => setRail('SOLANA')}
              >
                <span className="rail-icon">⚡</span>
                <span className="rail-name">Solana</span>
                <span className="rail-desc">On-chain with blockchain receipt</span>
              </button>
            </div>
          </div>

          {/* Amount */}
          <div className="form-group">
            <label className="form-label">
              <span className="label-icon">💰</span>
              Amount
            </label>
            <div className="amount-input-wrapper">
              <span className="amount-prefix">$</span>
              <input
                type="number"
                className="form-input amount-input"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                placeholder="0.00"
                min="0.01"
                step="0.01"
                required
              />
            </div>
          </div>

          {/* Conditional Recipient Fields */}
          {rail === 'BANK' ? (
            <div className="form-group">
              <label className="form-label">
                <span className="label-icon">🏦</span>
                Recipient ID
              </label>
              <input
                type="text"
                className="form-input"
                value={recipientId}
                onChange={(e) => setRecipientId(e.target.value)}
                placeholder="Enter recipient bank ID"
                required
              />
            </div>
          ) : (
            <div className="form-group">
              <label className="form-label">
                <span className="label-icon">🔑</span>
                Recipient Wallet Address
              </label>
              <input
                type="text"
                className="form-input"
                value={recipientAddress}
                onChange={(e) => setRecipientAddress(e.target.value)}
                placeholder="Enter Solana wallet address"
                required
              />
            </div>
          )}

          {/* Note */}
          <div className="form-group">
            <label className="form-label">
              <span className="label-icon">📝</span>
              Payment Note
            </label>
            <textarea
              className="form-input form-textarea"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Add a note for this payment..."
              rows={3}
            />
          </div>

          {/* Device ID Info */}
          <div className="info-box">
            <span className="info-icon">ℹ️</span>
            <div className="info-content">
              <strong>Device ID:</strong> {getDeviceId()}
              <br />
              <small>Stored locally for fraud detection</small>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="alert alert-error">
              <span className="alert-icon">⚠️</span>
              {error}
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            className="btn btn-primary btn-large"
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="spinner"></span>
                Processing...
              </>
            ) : (
              <>
                <span>🚀</span>
                Initiate Payment
              </>
            )}
          </button>
        </form>
      </div>

      {/* Security Features */}
      <div className="features-grid">
        <div className="feature-card">
          <span className="feature-icon">🎭</span>
          <h3>Deepfake Detection</h3>
          <p>AI-powered analysis to prevent synthetic media attacks</p>
        </div>
        <div className="feature-card">
          <span className="feature-icon">👁️</span>
          <h3>Liveness Check</h3>
          <p>Real-time verification to ensure genuine presence</p>
        </div>
        <div className="feature-card">
          <span className="feature-icon">🧠</span>
          <h3>Behavioral Analysis</h3>
          <p>Pattern recognition with Gemini AI integration</p>
        </div>
        <div className="feature-card">
          <span className="feature-icon">⛓️</span>
          <h3>Blockchain Audit</h3>
          <p>Immutable verification receipts on Solana</p>
        </div>
      </div>

      {/* Challenge Modal */}
      {challengeData && challengeData.status === 'CHALLENGE_REQUIRED' && (
        <ChallengeModal
          challengeData={challengeData}
          onComplete={handleChallengeComplete}
          onCancel={handleChallengeCancel}
        />
      )}
    </div>
  )
}
