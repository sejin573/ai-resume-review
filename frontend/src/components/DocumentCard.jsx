import { Link } from "react-router-dom";
import Badge from "./Badge";

const modeLabel = {
  quick: "빠른 첨삭",
  detailed: "상세 첨삭",
  strict: "꼼꼼한 첨삭",
  rewrite_focused: "개선문 중심",
  "rewrite-focused": "개선문 중심",
};

export default function DocumentCard({ review, variant = "folder" }) {
  const dateText = review.created_at ? new Date(review.created_at).toLocaleDateString() : "-";
  const label = modeLabel[review.review_mode] || review.review_mode || "첨삭";

  return (
    <Link to={`/reviews/${review.id}`} className={`folder-document-card ${variant === "compact" ? "compact" : ""}`}>
      <span className="folder-card-tab">{label}</span>
      <div className="folder-card-body">
        <div className="folder-card-topline">
          <span className="folder-card-date">{dateText}</span>
          <Badge tone="brand">{review.total_score}점</Badge>
        </div>
        <h3>{review.target_job_role}</h3>
        <p>{review.summary}</p>
        <div className="folder-card-footer">
          <span>첨삭 결과 열기</span>
          <span aria-hidden="true">→</span>
        </div>
      </div>
    </Link>
  );
}
