import { Fragment } from "react";
import Badge from "./Badge";
import Button from "./Button";
import { resolveSuggestionRange, suggestionCategoryLabels, suggestionSeverityLabels } from "../utils/suggestions";

function buildPreviewSegments(text, suggestions) {
  const ranges = [...(suggestions || [])]
    .map((suggestion) => ({
      suggestion,
      range: resolveSuggestionRange(text, suggestion),
    }))
    .filter((item) => item.range)
    .sort((a, b) => a.range.start - b.range.start || b.range.end - a.range.end);

  const segments = [];
  let cursor = 0;

  ranges.forEach(({ suggestion, range }) => {
    if (range.start < cursor) return;

    if (cursor < range.start) {
      segments.push({ type: "text", text: text.slice(cursor, range.start) });
    }

    segments.push({
      type: "highlight",
      text: text.slice(range.start, range.end),
      suggestion,
    });
    cursor = range.end;
  });

  if (cursor < text.length) {
    segments.push({ type: "text", text: text.slice(cursor) });
  }

  return segments;
}

export default function SuggestionPreview({
  text,
  suggestions,
  activeSuggestionId,
  onSelectSuggestion,
  onApply,
  onSkip,
  onClose,
  appliedSuggestionIds,
  totalCount,
  appliedCount = 0,
  skippedCount = 0,
  feedbackMessage,
}) {
  if (!text?.trim()) return null;

  const visibleSuggestions = (suggestions || []).filter((item) => !appliedSuggestionIds?.has(item.id));
  const segments = buildPreviewSegments(text, visibleSuggestions);
  const totalSuggestions = totalCount ?? visibleSuggestions.length + appliedCount + skippedCount;
  const remainingCount = visibleSuggestions.length;

  const renderNote = (suggestion) => (
    <div className="inline-suggestion-note" role="region" aria-label="선택한 문장 첨삭 메모">
      <div className="suggestion-note-pin">보완 메모</div>
      <div className="suggestion-popover-meta">
        <Badge tone={suggestion.severity === "high" ? "warning" : "neutral"}>
          {suggestionSeverityLabels[suggestion.severity] || "보완 제안"}
        </Badge>
        <Badge tone="brand">{suggestionCategoryLabels[suggestion.category] || "문장"}</Badge>
      </div>
      <strong>{suggestion.issue}</strong>
      <p>{suggestion.reason}</p>
      <div className="suggestion-popover-text">
        <span>추천</span>
        {suggestion.suggested_text}
      </div>
      <div className="suggestion-popover-actions">
        {onSkip ? (
          <Button variant="ghost" className="suggestion-popover-button" onClick={() => onSkip(suggestion.id)}>
            건너뛰기
          </Button>
        ) : null}
        <Button
          className="suggestion-popover-button"
          onClick={() => {
            onApply?.(suggestion);
            onClose?.();
          }}
        >
          이 문장 적용
        </Button>
      </div>
    </div>
  );

  return (
    <section className="suggestion-preview-sheet">
      <div className="suggestion-preview-head">
        <div>
          <strong>문장 첨삭</strong>
          <span>본문의 표시 문장을 누르면 바로 아래에 교정 메모가 열립니다.</span>
        </div>
        <div className="suggestion-progress-strip" aria-label="문장 첨삭 진행률">
          <span>
            <strong>{totalSuggestions}</strong>
            보완 제안
          </span>
          <span>
            <strong>{appliedCount}</strong>
            적용
          </span>
          <span>
            <strong>{remainingCount}</strong>
            남음
          </span>
        </div>
      </div>

      <div className="suggestion-preview-body">
        {segments.length ? (
          segments.map((segment, index) => {
            if (segment.type === "text") {
              return <span key={`text-${index}`}>{segment.text}</span>;
            }

            const suggestion = segment.suggestion;
            const isActive = suggestion.id === activeSuggestionId;

            return (
              <Fragment key={suggestion.id}>
                <button
                  type="button"
                  className={`suggestion-highlight ${isActive ? "active" : ""}`}
                  onClick={() => onSelectSuggestion?.(isActive ? "" : suggestion.id)}
                >
                  {segment.text}
                </button>
                {isActive ? renderNote(suggestion) : null}
              </Fragment>
            );
          })
        ) : (
          <span>{text}</span>
        )}
      </div>

      <div className="suggestion-preview-foot">
        <span>
          {visibleSuggestions.length
            ? `문장 수정 후 적용한 제안은 본문에서 사라집니다. 건너뛴 제안도 다시 표시하지 않습니다.`
            : "처리할 문장 첨삭 제안이 없습니다."}
        </span>
        {feedbackMessage ? <strong>{feedbackMessage}</strong> : null}
      </div>
    </section>
  );
}
