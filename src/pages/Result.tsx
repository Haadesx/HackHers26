import { useLocation, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { ScoreCard } from '../components/ScoreCard';
import { AudioPlayer } from '../components/AudioPlayer';
import { ChallengeModal } from '../components/ChallengeModal';
import { VerificationScores, VoiceAudio, Rail } from '../api';

interface ResultState {
  decision?: string;
  scores?: VerificationScores;
  reasons?: string[];
  paymentId: string;
  paymentStatus: string;
  rail: Rail;
  solanaTx?: string;
  verificationReceiptTx?: string;
  voiceAudio?: VoiceAudio;
}

export function Result() {
  const location = useLocation();
  const navigate = useNavigate();
  const state = location.state as ResultState;

  const [retryAttempted, setRetryAttempted] = useState(false);
  const [showRetryChallenge, setShowRetryChallenge] = useState(false);

  if (!state) {
    return (
      <div className="page">
        <h1>No Result Data</h1>
        <button onClick={() => navigate('/')}>Go Home</button>
      </div>
    );
  }

  const {
    decision,
    scores,
    reasons,
    paymentId,
    paymentStatus,
    rail,
    solanaTx,
    verificationReceiptTx,
    voiceAudio,
  } = state;

  const handleRetry = () => {
    if (!retryAttempted) {
      setRetryAttempted(true);
      setShowRetryChallenge(true);
    }
  };

  const handleRetryComplete = (result: any) => {
    setShowRetryChallenge(false);
    navigate('/result', {
      state: {
        ...result,
        paymentId: result.payment_id,
        paymentStatus: result.payment_status,
        rail: result.rail,
        solanaTx: result.solana_tx,
        verificationReceiptTx: result.verification_receipt_tx,
        voiceAudio: result.voice_audio,
      },
      replace: true,
    });
  };

  const getDecisionBadgeClass = () => {
    if (!decision) return 'badge-approved';
    if (decision === 'APPROVED') return 'badge-approved';
    if (decision === 'RETRY') return 'badge-retry';
    return 'badge-denied';
  };

  return (
    <div className="page">
      <h1>Payment Result</h1>

      {decision && (
        <div className={`decision-badge ${getDecisionBadgeClass()}`}>
          {decision}
        </div>
      )}

      <div className="result-section">
        <h2>Payment Details</h2>
        <div className="info-grid">
          <div className="info-item">
            <span className="info-label">Payment ID:</span>
            <span className="info-value">{paymentId}</span>
          </div>
          <div className="info-item">
            <span className="info-label">Status:</span>
            <span className="info-value">{paymentStatus}</span>
          </div>
          <div className="info-item">
            <span className="info-label">Rail:</span>
            <span className="info-value">{rail}</span>
          </div>
        </div>
      </div>

      {rail === 'SOLANA' && solanaTx && (
        <div className="result-section">
          <h2>Solana Transactions</h2>
          <div className="info-item">
            <span className="info-label">Transfer TX:</span>
            <span className="info-value tx-link">{solanaTx}</span>
          </div>
          {verificationReceiptTx && (
            <div className="info-item">
              <span className="info-label">Receipt TX:</span>
              <span className="info-value tx-link">{verificationReceiptTx}</span>
            </div>
          )}
        </div>
      )}

      {scores && (
        <div className="result-section">
          <h2>Verification Scores</h2>
          <div className="scores-grid">
            <ScoreCard label="Deepfake Mean" value={scores.deepfake_mean} />
            <ScoreCard label="Deepfake Variance" value={scores.deepfake_var} />
            <ScoreCard label="Liveness" value={scores.liveness} />
            <ScoreCard label="Quality" value={scores.quality} />
            <ScoreCard label="Presage" value={scores.presage} />
          </div>
        </div>
      )}

      {reasons && reasons.length > 0 && (
        <div className="result-section">
          <h2>Reasons</h2>
          <ul className="reasons-list">
            {reasons.map((reason, index) => (
              <li key={index}>{reason}</li>
            ))}
          </ul>
        </div>
      )}

      {voiceAudio && (
        <div className="result-section">
          <h2>Voice Authentication</h2>
          <AudioPlayer voiceAudio={voiceAudio} autoplay />
        </div>
      )}

      <div className="action-buttons">
        {decision === 'RETRY' && !retryAttempted && (
          <button onClick={handleRetry} className="retry-button">
            Retry Challenge
          </button>
        )}
        <button onClick={() => navigate('/')} className="home-button">
          New Payment
        </button>
      </div>

      {showRetryChallenge && (
        <ChallengeModal
          challengeId={paymentId}
          prompt="Please complete the liveness challenge again"
          expiresAt={new Date(Date.now() + 5 * 60 * 1000).toISOString()}
          onComplete={handleRetryComplete}
          onClose={() => setShowRetryChallenge(false)}
        />
      )}
    </div>
  );
}
