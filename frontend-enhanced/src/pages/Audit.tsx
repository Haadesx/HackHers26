import { useState, useEffect } from 'react'
import { getChallenges, getChallengeDetail, Challenge, ChallengeDetail } from '../api'

export default function Audit() {
  const [challenges, setChallenges] = useState<Challenge[]>([])
  const [selectedChallenge, setSelectedChallenge] = useState<ChallengeDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [detailLoading, setDetailLoading] = useState(false)

  useEffect(() => {
    loadChallenges()
  }, [])

  const loadChallenges = async () => {
    try {
      setLoading(true)
      setError('')
      const data = await getChallenges()
      setChallenges(data)
    } catch (err: any) {
      setError(err.message || 'Failed to load challenges')
    } finally {
      setLoading(false)
    }
  }

  const handleRowClick = async (id: string) => {
    try {
      setDetailLoading(true)
      const detail = await getChallengeDetail(id)
      setSelectedChallenge(detail)
    } catch (err: any) {
      setError(err.message || 'Failed to load challenge detail')
    } finally {
      setDetailLoading(false)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString()
  }

  const getDecisionBadge = (decision?: string) => {
    if (!decision) return <span className="badge badge-secondary">Pending</span>

    switch (decision) {
      case 'APPROVED':
        return <span className="badge badge-success">✅ Approved</span>
      case 'REJECTED':
        return <span className="badge badge-error">❌ Rejected</span>
      case 'RETRY':
        return <span className="badge badge-warning">🔄 Retry</span>
      default:
        return <span className="badge badge-info">{decision}</span>
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">
          <span className="title-icon">📊</span>
          Audit Log
        </h1>
        <p className="page-subtitle">
          View all verification challenges and their results
        </p>
      </div>

      {error && (
        <div className="alert alert-error">
          <span className="alert-icon">⚠️</span>
          {error}
        </div>
      )}

      <div className="audit-layout">
        {/* Challenges List */}
        <div className="card challenges-card">
          <div className="card-header">
            <h3 className="card-title">
              <span className="title-icon">📋</span>
              Challenges
            </h3>
            <button className="btn btn-small" onClick={loadChallenges} disabled={loading}>
              {loading ? '⏳' : '🔄'} Refresh
            </button>
          </div>

          {loading ? (
            <div className="loading-state">
              <span className="spinner"></span>
              <p>Loading challenges...</p>
            </div>
          ) : challenges.length === 0 ? (
            <div className="empty-state">
              <span className="empty-icon">📭</span>
              <p>No challenges found</p>
            </div>
          ) : (
            <div className="table-wrapper">
              <table className="audit-table">
                <thead>
                  <tr>
                    <th>Challenge ID</th>
                    <th>User</th>
                    <th>Created</th>
                    <th>Decision</th>
                    <th>Rail</th>
                  </tr>
                </thead>
                <tbody>
                  {challenges.map((challenge) => (
                    <tr
                      key={challenge.id}
                      onClick={() => handleRowClick(challenge.id)}
                      className={selectedChallenge?.id === challenge.id ? 'selected' : ''}
                    >
                      <td>
                        <code className="challenge-id">{challenge.id.substring(0, 8)}...</code>
                      </td>
                      <td>{challenge.user_id}</td>
                      <td className="date-cell">{formatDate(challenge.created_at)}</td>
                      <td>{getDecisionBadge(challenge.decision)}</td>
                      <td>
                        {challenge.rail === 'BANK' && '🏦 Bank'}
                        {challenge.rail === 'SOLANA' && '⚡ Solana'}
                        {!challenge.rail && '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Challenge Detail */}
        {selectedChallenge && (
          <div className="card detail-card">
            <div className="card-header">
              <h3 className="card-title">
                <span className="title-icon">🔍</span>
                Challenge Details
              </h3>
              <button
                className="btn-close"
                onClick={() => setSelectedChallenge(null)}
              >
                ✕
              </button>
            </div>

            {detailLoading ? (
              <div className="loading-state">
                <span className="spinner"></span>
                <p>Loading details...</p>
              </div>
            ) : (
              <div className="detail-content">
                <div className="detail-section">
                  <h4 className="detail-section-title">Basic Information</h4>
                  <div className="details-grid">
                    <div className="detail-item">
                      <span className="detail-label">Challenge ID</span>
                      <code className="detail-value">{selectedChallenge.id}</code>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">User ID</span>
                      <span className="detail-value">{selectedChallenge.user_id}</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">Created</span>
                      <span className="detail-value">{formatDate(selectedChallenge.created_at)}</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">Decision</span>
                      {getDecisionBadge(selectedChallenge.decision)}
                    </div>
                  </div>
                </div>

                <div className="detail-section">
                  <h4 className="detail-section-title">Prompt</h4>
                  <div className="prompt-box">
                    {selectedChallenge.prompt}
                  </div>
                </div>

                {selectedChallenge.payment_id && (
                  <div className="detail-section">
                    <h4 className="detail-section-title">Payment Information</h4>
                    <div className="details-grid">
                      <div className="detail-item">
                        <span className="detail-label">Payment ID</span>
                        <code className="detail-value">{selectedChallenge.payment_id}</code>
                      </div>
                      <div className="detail-item">
                        <span className="detail-label">Status</span>
                        <span className="detail-value">{selectedChallenge.payment_status || '-'}</span>
                      </div>
                      <div className="detail-item">
                        <span className="detail-label">Rail</span>
                        <span className="detail-value">
                          {selectedChallenge.rail === 'BANK' && '🏦 Bank'}
                          {selectedChallenge.rail === 'SOLANA' && '⚡ Solana'}
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {selectedChallenge.scores && (
                  <div className="detail-section">
                    <h4 className="detail-section-title">Verification Scores</h4>
                    <div className="scores-list">
                      <div className="score-row">
                        <span className="score-label">🎭 Deepfake Mean</span>
                        <span className="score-value">{(selectedChallenge.scores.deepfake_mean * 100).toFixed(1)}%</span>
                      </div>
                      <div className="score-row">
                        <span className="score-label">📈 Deepfake Variance</span>
                        <span className="score-value">{(selectedChallenge.scores.deepfake_var * 100).toFixed(1)}%</span>
                      </div>
                      <div className="score-row">
                        <span className="score-label">👁️ Liveness</span>
                        <span className="score-value">{(selectedChallenge.scores.liveness * 100).toFixed(1)}%</span>
                      </div>
                      <div className="score-row">
                        <span className="score-label">✨ Quality</span>
                        <span className="score-value">{(selectedChallenge.scores.quality * 100).toFixed(1)}%</span>
                      </div>
                      <div className="score-row">
                        <span className="score-label">🧠 Presage</span>
                        <span className="score-value">{(selectedChallenge.scores.presage * 100).toFixed(1)}%</span>
                      </div>
                    </div>
                  </div>
                )}

                {selectedChallenge.reasons && selectedChallenge.reasons.length > 0 && (
                  <div className="detail-section">
                    <h4 className="detail-section-title">Analysis Reasons</h4>
                    <ul className="reasons-list">
                      {selectedChallenge.reasons.map((reason, idx) => (
                        <li key={idx} className="reason-item">
                          <span className="reason-bullet">•</span>
                          {reason}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {selectedChallenge.solana_tx && (
                  <div className="detail-section">
                    <h4 className="detail-section-title">Blockchain Transactions</h4>
                    <div className="transaction-list">
                      <div className="transaction-item">
                        <span className="transaction-label">Payment TX</span>
                        <code className="detail-value">{selectedChallenge.solana_tx}</code>
                      </div>
                      {selectedChallenge.verification_receipt_tx && (
                        <div className="transaction-item">
                          <span className="transaction-label">Receipt TX</span>
                          <code className="detail-value">{selectedChallenge.verification_receipt_tx}</code>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
