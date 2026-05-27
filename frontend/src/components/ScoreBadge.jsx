export default function ScoreBadge({ score, label = "총점" }) {
  return (
    <div className="score-badge-ring">
      <div className="score-badge-inner">
        <span>{label}</span>
        <strong>{score}</strong>
      </div>
    </div>
  );
}
