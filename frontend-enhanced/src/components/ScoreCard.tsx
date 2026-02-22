interface Props {
  title: string
  score: number
  icon: string
  description: string
}

export default function ScoreCard({ title, score, icon, description }: Props) {
  const percentage = Math.round(score * 100)

  const getScoreColor = () => {
    if (percentage >= 80) return 'success'
    if (percentage >= 60) return 'warning'
    return 'error'
  }

  const getScoreGrade = () => {
    if (percentage >= 90) return 'A+'
    if (percentage >= 80) return 'A'
    if (percentage >= 70) return 'B'
    if (percentage >= 60) return 'C'
    if (percentage >= 50) return 'D'
    return 'F'
  }

  return (
    <div className={`score-card score-${getScoreColor()}`}>
      <div className="score-header">
        <span className="score-icon">{icon}</span>
        <h4 className="score-title">{title}</h4>
      </div>

      <div className="score-display">
        <div className="score-percentage">{percentage}%</div>
        <div className="score-grade">{getScoreGrade()}</div>
      </div>

      <div className="score-bar">
        <div
          className="score-bar-fill"
          style={{ width: `${percentage}%` }}
        />
      </div>

      <p className="score-description">{description}</p>
    </div>
  )
}
