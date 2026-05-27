import Badge from "./Badge";
import Button from "./Button";
import { suggestionCategoryLabels, suggestionSeverityLabels } from "../utils/suggestions";

export default function SuggestionList({
  suggestions,
  appliedSuggestionIds,
  skippedSuggestionIds,
  activeSuggestionId,
  onApply,
  onSkip,
  onSelect,
  feedbackMessage,
}) {
  if (!suggestions?.length) return null;

  return (
    <section className="suggestion-slip-section">
      <div className="section-header">
        <div>
          <h2>문장별 보완 제안</h2>
          <p className="muted">영향이 큰 문장만 골라 제안합니다. 원클릭 적용 후에도 최종 제출 전에는 직접 확인해 주세요.</p>
        </div>
        {feedbackMessage ? <span className="suggestion-inline-feedback">{feedbackMessage}</span> : null}
      </div>
      <div className="suggestion-slip-list">
        {suggestions.map((suggestion) => {
          const isApplied = appliedSuggestionIds.has(suggestion.id);
          const isSkipped = skippedSuggestionIds.has(suggestion.id);
          const severityTone =
            suggestion.severity === "high" ? "warning" : suggestion.severity === "medium" ? "brand" : "neutral";

          return (
            <article
              key={suggestion.id}
              className={`suggestion-slip ${suggestion.id === activeSuggestionId ? "active" : ""} ${isApplied ? "applied" : ""}`}
              onClick={() => onSelect?.(suggestion.id)}
            >
              <div className="suggestion-slip-top">
                <div className="keyword-chip-row">
                  <Badge tone={severityTone}>{suggestionSeverityLabels[suggestion.severity] || suggestion.severity}</Badge>
                  <Badge tone="neutral">{suggestionCategoryLabels[suggestion.category] || suggestion.category}</Badge>
                  {isApplied ? <Badge tone="success">적용됨</Badge> : null}
                  {isSkipped ? <Badge tone="neutral">건너뜀</Badge> : null}
                </div>
                <span className="suggestion-confidence">신뢰도 {Math.round((suggestion.confidence || 0) * 100)}%</span>
              </div>

              <div className="suggestion-original-quote">“{suggestion.original_text || "원문 매칭 실패"}”</div>

              <div className="suggestion-meta-block">
                <strong>{suggestion.issue}</strong>
                <p>{suggestion.reason}</p>
              </div>

              <div className="suggestion-rewrite-block">
                <span>추천 문장</span>
                <p>{suggestion.suggested_text}</p>
              </div>

              <div className="button-row">
                <Button type="button" onClick={(event) => { event.stopPropagation(); onApply?.(suggestion); }} disabled={isApplied}>
                  이 문장 적용
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={(event) => {
                    event.stopPropagation();
                    onSkip?.(suggestion.id);
                  }}
                >
                  건너뛰기
                </Button>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
