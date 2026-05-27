import { useState } from "react";
import { api } from "../api/client";
import Button from "./Button";

export default function ReviewQualityFeedback({ reviewId }) {
  const [submitted, setSubmitted] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async (rating) => {
    setLoading(true);
    setError("");
    try {
      await api.submitReviewFeedback(reviewId, { rating });
      setSubmitted(rating);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="card soft-card">
      <h2>이번 첨삭은 어땠나요?</h2>
      <p className="muted">이 평가는 이후 리뷰 품질 개선에만 활용됩니다.</p>
      <div className="button-row top-gap">
        <Button
          variant={submitted === "helpful" ? "primary" : "secondary"}
          onClick={() => submit("helpful")}
          disabled={loading}
        >
          도움이 됐어요
        </Button>
        <Button
          variant={submitted === "not_helpful" ? "primary" : "ghost"}
          onClick={() => submit("not_helpful")}
          disabled={loading}
        >
          아쉬워요
        </Button>
      </div>
      {submitted ? (
        <p className="muted top-gap">
          {submitted === "helpful"
            ? "도움이 됐다는 피드백이 저장됐습니다."
            : "아쉬웠다는 피드백이 저장됐습니다."}
        </p>
      ) : null}
      {error ? <div className="error-box top-gap">{error}</div> : null}
    </section>
  );
}
