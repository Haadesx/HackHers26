import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { initiatePayment, Rail, InitiatePaymentRequest } from '../api';
import { ChallengeModal } from '../components/ChallengeModal';

export function Home() {
  const navigate = useNavigate();

  const [userId, setUserId] = useState('demo_user');
  const [rail, setRail] = useState<Rail>('BANK');
  const [amount, setAmount] = useState('');
  const [note, setNote] = useState('');
  const [recipientId, setRecipientId] = useState('');
  const [recipientAddress, setRecipientAddress] = useState('');
  const [deviceId, setDeviceId] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const [showChallenge, setShowChallenge] = useState(false);
  const [challengeData, setChallengeData] = useState<{
    challengeId: string;
    prompt: string;
    expiresAt: string;
    paymentId: string;
    paymentStatus: string;
    rail: Rail;
    solanaTx?: string;
  } | null>(null);

  useEffect(() => {
    let storedDeviceId = localStorage.getItem('device_id');
    if (!storedDeviceId) {
      storedDeviceId = `device_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      localStorage.setItem('device_id', storedDeviceId);
    }
    setDeviceId(storedDeviceId);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!amount || parseFloat(amount) <= 0) {
      setError('Please enter a valid amount');
      return;
    }

    if (rail === 'BANK' && !recipientId) {
      setError('Recipient ID is required for BANK rail');
      return;
    }

    if (rail === 'SOLANA' && !recipientAddress) {
      setError('Recipient address is required for SOLANA rail');
      return;
    }

    setIsSubmitting(true);

    try {
      const request: InitiatePaymentRequest = {
        user_id: userId,
        rail,
        amount: parseFloat(amount),
        note,
        device_id: deviceId,
        user_agent: navigator.userAgent,
      };

      if (rail === 'BANK') {
        request.recipient_id = recipientId;
      } else {
        request.recipient_address = recipientAddress;
      }

      const response = await initiatePayment(request);

      if (response.status === 'APPROVED') {
        navigate('/result', {
          state: {
            paymentId: response.payment_id,
            paymentStatus: response.payment_status,
            rail: response.rail,
            solanaTx: response.solana_tx,
            voiceAudio: response.voice_audio,
            decision: 'APPROVED',
          },
        });
      } else if (response.status === 'CHALLENGE_REQUIRED') {
        setChallengeData({
          challengeId: response.challenge_id,
          prompt: response.prompt,
          expiresAt: response.expires_at,
          paymentId: response.payment_id,
          paymentStatus: response.payment_status,
          rail: response.rail,
          solanaTx: response.solana_tx,
        });
        setShowChallenge(true);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Payment initiation failed');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleChallengeComplete = (result: any) => {
    setShowChallenge(false);
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
    });
  };

  return (
    <div className="page">
      <h1>Payment Liveness System</h1>

      <form onSubmit={handleSubmit} className="payment-form">
        <div className="form-group">
          <label>User ID</label>
          <input
            type="text"
            value={userId}
            onChange={(e) => setUserId(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label>Payment Rail</label>
          <select value={rail} onChange={(e) => setRail(e.target.value as Rail)}>
            <option value="BANK">BANK</option>
            <option value="SOLANA">SOLANA</option>
          </select>
        </div>

        <div className="form-group">
          <label>Amount</label>
          <input
            type="number"
            step="0.01"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label>Note</label>
          <input
            type="text"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
        </div>

        {rail === 'BANK' && (
          <div className="form-group">
            <label>Recipient ID</label>
            <input
              type="text"
              value={recipientId}
              onChange={(e) => setRecipientId(e.target.value)}
              required
            />
          </div>
        )}

        {rail === 'SOLANA' && (
          <div className="form-group">
            <label>Recipient Address</label>
            <input
              type="text"
              value={recipientAddress}
              onChange={(e) => setRecipientAddress(e.target.value)}
              required
            />
          </div>
        )}

        {error && <div className="error-message">{error}</div>}

        <button type="submit" disabled={isSubmitting} className="submit-button">
          {isSubmitting ? 'Processing...' : 'Submit Payment'}
        </button>
      </form>

      <div className="nav-links">
        <a href="/audit">View Audit Log</a>
      </div>

      {showChallenge && challengeData && (
        <ChallengeModal
          challengeId={challengeData.challengeId}
          prompt={challengeData.prompt}
          expiresAt={challengeData.expiresAt}
          onComplete={handleChallengeComplete}
          onClose={() => setShowChallenge(false)}
        />
      )}
    </div>
  );
}
