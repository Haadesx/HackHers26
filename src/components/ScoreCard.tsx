interface ScoreCardProps {
  label: string;
  value: number;
}

export function ScoreCard({ label, value }: ScoreCardProps) {
  const percentage = (value * 100).toFixed(1);

  return (
    <div className="score-card">
      <div className="score-label">{label}</div>
      <div className="score-value">{percentage}%</div>
    </div>
  );
}
