export default function ReviewScoreSummary({ totalScore, summary }) {
  return (
    <section className="panel review-summary-panel">
      <div className="score-badge">
        <span>총점</span>
        <strong>{totalScore}</strong>
      </div>
      <div>
        <h2>핵심 요약</h2>
        <p className="long-text">{summary}</p>
      </div>
    </section>
  );
}
