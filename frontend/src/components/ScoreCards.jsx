const SCORE_LABELS = {
  job_fit: "직무 적합도",
  specificity: "구체성",
  achievement: "성과 표현",
  writing_quality: "문장력",
  uniqueness: "차별성",
  structure: "논리 구조",
  keyword_match: "키워드 반영",
};

export default function ScoreCards({ scores }) {
  return (
    <section className="score-grid">
      {Object.entries(SCORE_LABELS).map(([key, label]) => (
        <div key={key} className="score-card">
          <span>{label}</span>
          <strong>{scores?.[key] ?? "-"}</strong>
        </div>
      ))}
    </section>
  );
}
