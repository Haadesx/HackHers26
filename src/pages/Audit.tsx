import { useEffect, useState } from 'react';
import { getChallenges, getChallenge, Challenge } from '../api';

export function Audit() {
  const [challenges, setChallenges] = useState<Challenge[]>([]);
  const [selectedChallenge, setSelectedChallenge] = useState<Challenge | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadChallenges();
  }, []);

  const loadChallenges = async () => {
    try {
      setLoading(true);
      const data = await getChallenges();
      setChallenges(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load challenges');
    } finally {
      setLoading(false);
    }
  };

  const handleRowClick = async (id: string) => {
    try {
      const challenge = await getChallenge(id);
      setSelectedChallenge(challenge);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load challenge details');
    }
  };

  if (loading) {
    return (
      <div className="page">
        <h1>Audit Log</h1>
        <p>Loading...</p>
      </div>
    );
  }

  return (
    <div className="page">
      <h1>Audit Log</h1>

      <div className="nav-links">
        <a href="/">Back to Home</a>
      </div>

      {error && <div className="error-message">{error}</div>}

      {challenges.length === 0 ? (
        <p>No challenges found</p>
      ) : (
        <table className="audit-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>User ID</th>
              <th>Prompt</th>
              <th>Created At</th>
              <th>Decision</th>
            </tr>
          </thead>
          <tbody>
            {challenges.map((challenge) => (
              <tr
                key={challenge.id}
                onClick={() => handleRowClick(challenge.id)}
                className="clickable-row"
              >
                <td>{challenge.id}</td>
                <td>{challenge.user_id}</td>
                <td>{challenge.prompt}</td>
                <td>{new Date(challenge.created_at).toLocaleString()}</td>
                <td>
                  {challenge.decision ? (
                    <span className={`status-cell ${challenge.decision === "APPROVED" ? "badge-approved" : challenge.decision === "RETRY" ? "badge-retry" : "badge-denied"}`}>
                      {challenge.decision}
                    </span>
                  ) : (
                    '-'
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {selectedChallenge && (
        <div className="modal-overlay" onClick={() => setSelectedChallenge(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setSelectedChallenge(null)}>
              ×
            </button>

            <h2>Challenge Details</h2>

            <div className="detail-grid">
              <div className="detail-item">
                <span className="detail-label">ID:</span>
                <span className="detail-value">{selectedChallenge.id}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">User ID:</span>
                <span className="detail-value">{selectedChallenge.user_id}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Prompt:</span>
                <span className="detail-value">{selectedChallenge.prompt}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Created At:</span>
                <span className="detail-value">
                  {new Date(selectedChallenge.created_at).toLocaleString()}
                </span>
              </div>
              {selectedChallenge.decision && (
                <div className="detail-item">
                  <span className="detail-label">Decision:</span>
                  <span className="detail-value">{selectedChallenge.decision}</span>
                </div>
              )}
            </div>

            {selectedChallenge.scores && (
              <div className="scores-section">
                <h3>Scores</h3>
                <div className="scores-grid">
                  <div className="score-card">
                    <div className="score-label">Deepfake Mean</div>
                    <div className="score-value">
                      {(selectedChallenge.scores.deepfake_mean * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div className="score-card">
                    <div className="score-label">Deepfake Var</div>
                    <div className="score-value">
                      {(selectedChallenge.scores.deepfake_var * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div className="score-card">
                    <div className="score-label">Liveness</div>
                    <div className="score-value">
                      {(selectedChallenge.scores.liveness * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div className="score-card">
                    <div className="score-label">Quality</div>
                    <div className="score-value">
                      {(selectedChallenge.scores.quality * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div className="score-card">
                    <div className="score-label">Presage</div>
                    <div className="score-value">
                      {(selectedChallenge.scores.presage * 100).toFixed(1)}%
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
