import { Fragment, useMemo } from "react";
import Badge from "./Badge";
import Button from "./Button";
import { resolveSuggestionRange, suggestionCategoryLabels } from "../utils/suggestions";

const statusLabels = {
  good: "좋음",
  okay: "보통",
  needs_fix: "보완 필요",
  risky: "위험/과장",
};

const statusBadgeTone = {
  good: "success",
  okay: "neutral",
  needs_fix: "warning",
  risky: "warning",
};

function sentenceReviewToSuggestion(item) {
  return {
    original_text: item.sentence_text,
    start_index: item.start_index,
    end_index: item.end_index,
    suggested_text: item.suggested_text || "",
    apply_type: "replace",
  };
}

function suggestionsToSentenceReviews(suggestions = []) {
  return suggestions.map((suggestion, index) => ({
    id: suggestion.id || `fallback-sent-${index + 1}`,
    sentence_text: suggestion.original_text,
    start_index: suggestion.start_index,
    end_index: suggestion.end_index,
    status: suggestion.severity === "high" && suggestion.category === "tone" ? "risky" : "needs_fix",
    category: suggestion.category || "clarity",
    label: suggestion.issue || "문장 보완 필요",
    good_point: null,
    comment: suggestion.reason || "구체성과 직무 연결성을 보완하면 더 설득력 있게 읽힙니다.",
    suggested_text: suggestion.suggested_text || null,
    can_apply: Boolean(suggestion.suggested_text),
    confidence: suggestion.confidence || 0.5,
  }));
}

function splitSentences(text = "") {
  const pattern = /[^.!?\n。！？]+(?:[.!?。！？]+|$)/g;
  const sentences = [];
  let match;
  while ((match = pattern.exec(text))) {
    const raw = match[0];
    const sentence = raw.trim();
    if (!sentence) continue;
    const leading = raw.length - raw.trimStart().length;
    const start = match.index + leading;
    sentences.push({ sentence, start, end: start + sentence.length });
  }
  return sentences;
}

function compact(text = "") {
  return text.replace(/\s+/g, "").toLowerCase();
}

function extractFactKeywords(text = "") {
  const candidates = [
    "Java",
    "Python",
    "Git",
    "PHP",
    "MVC",
    "OCR",
    "Spring",
    "JSP",
    "MySQL",
    "ASP",
    "Open API",
    "네이버 뉴스 API",
    "OpenAI Codex",
    "사내 홈페이지",
    "계약서 자동 검토 웹서비스",
    "전자계약",
    "정보 추출",
    "관리자 기능",
    "LMS",
    "운영",
    "유지보수",
    "기능 개선",
    "수강신청",
    "온라인 강의",
    "출석",
    "시험",
    "문제 분석",
    "기능 구현",
    "구조 이해",
    "서비스 개선",
  ];
  const lowered = text.toLowerCase();
  return candidates.filter((candidate, index) => lowered.includes(candidate.toLowerCase()) && candidates.indexOf(candidate) === index);
}

function joinKeywords(keywords = []) {
  if (!keywords.length) return "";
  if (keywords.length === 1) return keywords[0];
  return `${keywords.slice(0, -1).join(", ")}와 ${keywords[keywords.length - 1]}`;
}

function contextAround(sentences, current) {
  const index = sentences.findIndex((item) => item.start === current.start && item.end === current.end);
  return {
    before: index > 0 ? sentences[index - 1].sentence : "",
    after: index >= 0 && index + 1 < sentences.length ? sentences[index + 1].sentence : "",
  };
}

function buildContextualRewrite(sentence, category, fullText, current, sentences) {
  const { before, after } = contextAround(sentences, current);
  const context = `${before} ${sentence} ${after}`;
  const keywords = extractFactKeywords(context);
  const fallbackKeywords = keywords.length ? keywords : extractFactKeywords(fullText);
  const joined = joinKeywords(fallbackKeywords.slice(0, 4));

  if (/새로운 환경|익숙하지 않은 기술|빠르게 적응/.test(sentence)) {
    if (joined) {
      return `새로운 기술을 빠르게 익히고 실제 서비스 흐름에 적용하는 과정에서 성장해왔습니다. ${joined} 경험을 통해 낯선 환경에서도 구조를 이해하고 필요한 기능을 구현하는 역량을 쌓았습니다.`;
    }
    return "새로운 기술을 빠르게 익히고 실제 업무 흐름에 적용하며, 낯선 환경에서도 구조를 이해해 필요한 기능을 구현하는 개발자로 성장해왔습니다.";
  }

  if (category === "achievement") {
    if (joined) {
      return `${sentence} 특히 ${joined} 과정에서 맡은 역할과 처리 흐름을 정리하며 실제 운영에 필요한 개선 경험을 쌓았습니다.`;
    }
    return `${sentence} 이 과정에서 맡은 역할과 처리 흐름을 정리하며 실제 업무 개선으로 이어지는 경험을 쌓았습니다.`;
  }

  if (joined) {
    return `${sentence} 이 경험은 ${joined}를 바탕으로 문제를 구조화하고 실제 기능으로 연결한 과정이라는 점에서 강점으로 제시할 수 있습니다.`;
  }
  return "";
}

function classifyFallbackSentence(sentence, index, fullText, current, sentences) {
  if (/최고|완벽|무조건|누구보다|압도적/.test(sentence)) {
    return {
      status: "risky",
      category: "tone",
      label: "과장 위험",
      good_point: null,
      comment: "근거를 묻기 쉬운 강한 표현이 있어 검증 가능한 표현으로 낮추는 편이 안전합니다.",
      suggested_text: sentence.replace(/최고|완벽|무조건|누구보다|압도적/g, "검증 가능한 방식으로"),
      can_apply: true,
      confidence: 0.56,
    };
  }
  if (/열심히|성실|책임감|최선|노력|익숙하지 않은/.test(sentence)) {
    const suggested = buildContextualRewrite(sentence, "specificity", fullText, current, sentences);
    return {
      status: "needs_fix",
      category: "specificity",
      label: "구체성 보완",
      good_point: null,
      comment: "태도와 적응력은 보이지만, 역할과 행동이 더 구체적으로 이어지면 설득력이 올라갑니다.",
      suggested_text: suggested || null,
      can_apply: Boolean(suggested),
      quality_warning: suggested ? null : "원문 키워드가 부족해 바로 적용하기보다는 직접 수정이 필요합니다.",
      expected_effect: "추상적인 태도 표현을 실제 경험 기반 강점으로 바꿉니다.",
      confidence: 0.58,
    };
  }
  if (/구현|개발|운영|유지보수|분석|수정|연동|협업|관리|프로젝트/.test(sentence)) {
    return {
      status: "good",
      category: "clarity",
      label: "경험 근거 좋음",
      good_point: "실제 수행한 업무와 기술 키워드가 보여 경험의 기반이 좋습니다.",
      comment: "성과 수치나 개선 전후 변화가 추가되면 더 강한 문장이 됩니다.",
      suggested_text: null,
      can_apply: false,
      confidence: 0.62,
    };
  }
  if (index % 3 === 1) {
    const suggested = buildContextualRewrite(sentence, "achievement", fullText, current, sentences);
    return {
      status: "needs_fix",
      category: "achievement",
      label: "성과 근거 보완",
      good_point: null,
      comment: "행동 이후 어떤 변화가 있었는지 보강하면 경험의 신뢰도가 올라갑니다.",
      suggested_text: suggested || null,
      can_apply: Boolean(suggested),
      quality_warning: suggested ? null : "추천 문장을 자동 생성하기 어려워 직접 수정이 필요합니다.",
      expected_effect: "행동과 결과의 연결이 분명해져 경험의 신뢰도가 올라갑니다.",
      confidence: 0.54,
    };
  }
  return {
    status: "okay",
    category: "clarity",
    label: "흐름 무난",
    good_point: "문장 흐름이 크게 어색하지 않아 앞뒤 문장과 연결해 다듬기 좋습니다.",
    comment: "지원 직무와의 연결이 더 직접적으로 보이면 완성도가 올라갑니다.",
    suggested_text: null,
    can_apply: false,
    confidence: 0.58,
  };
}

function enrichReviewsWithLocalFallback(text, reviews) {
  const sentences = splitSentences(text);
  const targetMin = Math.min(8, Math.max(0, sentences.length));
  if (reviews.length >= Math.min(6, targetMin) || sentences.length <= reviews.length) return reviews;

  const seen = new Set(reviews.map((item) => compact(item.sentence_text)));
  const enriched = [...reviews];
  for (const item of sentences) {
    if (enriched.length >= targetMin) break;
    if (seen.has(compact(item.sentence))) continue;
    const fallback = classifyFallbackSentence(item.sentence, enriched.length, text, item, sentences);
    enriched.push({
      id: `local-sent-${enriched.length + 1}`,
      sentence_text: item.sentence,
      start_index: item.start,
      end_index: item.end,
      ...fallback,
    });
    seen.add(compact(item.sentence));
  }
  return enriched;
}

function buildSegments(text, reviews) {
  const ranges = reviews
    .map((review) => ({
      review,
      range: resolveSuggestionRange(text, sentenceReviewToSuggestion(review)),
    }))
    .filter((item) => item.range)
    .sort((a, b) => a.range.start - b.range.start || b.range.end - a.range.end);

  const segments = [];
  let cursor = 0;

  ranges.forEach(({ review, range }) => {
    if (range.start < cursor) return;
    if (cursor < range.start) {
      segments.push({ type: "text", text: text.slice(cursor, range.start) });
    }
    segments.push({ type: "review", text: text.slice(range.start, range.end), review });
    cursor = range.end;
  });

  if (cursor < text.length) {
    segments.push({ type: "text", text: text.slice(cursor) });
  }
  return segments;
}

export default function SentenceReviewPreview({
  text,
  sentenceReviews = [],
  suggestions = [],
  activeReviewId,
  onSelectReview,
  onApply,
  onSkip,
  appliedReviewIds,
  skippedReviewIds,
  feedbackMessage,
}) {
  const allReviews = useMemo(
    () => {
      const sourceReviews = sentenceReviews?.length ? sentenceReviews : suggestionsToSentenceReviews(suggestions);
      return enrichReviewsWithLocalFallback(text || "", sourceReviews);
    },
    [text, sentenceReviews, suggestions],
  );
  const visibleReviews = allReviews.filter((item) => !appliedReviewIds?.has(item.id) && !skippedReviewIds?.has(item.id));
  const segments = buildSegments(text || "", visibleReviews);
  const counts = allReviews.reduce(
    (acc, item) => {
      acc.total += 1;
      acc[item.status] = (acc[item.status] || 0) + 1;
      if (item.status === "needs_fix" || item.status === "risky") acc.fixable += 1;
      return acc;
    },
    { total: 0, good: 0, okay: 0, needs_fix: 0, risky: 0, fixable: 0 },
  );
  const appliedCount = appliedReviewIds?.size || 0;
  const remainingFixCount = visibleReviews.filter((item) => item.status === "needs_fix" || item.status === "risky").length;

  if (!text?.trim()) return null;

  const renderNote = (review) => {
    const canApply = review.can_apply && review.suggested_text && ["needs_fix", "risky"].includes(review.status);
    return (
      <div className={`sentence-review-note ${review.status}`} role="region" aria-label="문장 첨삭 메모">
        <div className="sentence-review-note-head">
          <div className="sentence-review-badges">
            <Badge tone={statusBadgeTone[review.status] || "neutral"}>{statusLabels[review.status] || "문장 검토"}</Badge>
            <Badge tone="brand">{suggestionCategoryLabels[review.category] || "문장"}</Badge>
          </div>
          <strong>{review.label || statusLabels[review.status]}</strong>
        </div>
        {review.good_point ? <p className="sentence-review-good">{review.good_point}</p> : null}
        <p>{review.comment}</p>
        {review.quality_warning || (!canApply && ["needs_fix", "risky"].includes(review.status)) ? (
          <p className="sentence-review-warning">
            {review.quality_warning || "바로 적용하기보다는 내용을 참고해 직접 수정하는 편이 안전합니다."}
          </p>
        ) : null}
        {review.suggested_text ? (
          <button
            type="button"
            className={`sentence-review-rewrite ${canApply ? "clickable" : ""}`}
            onClick={() => {
              if (canApply) onApply?.(review);
            }}
            disabled={!canApply}
          >
            <span>추천 문장</span>
            {review.suggested_text}
          </button>
        ) : null}
        {review.expected_effect ? (
          <p className="sentence-review-effect">
            <span>기대 효과</span>
            {review.expected_effect}
          </p>
        ) : null}
        <div className="sentence-review-actions">
          {onSkip ? (
            <Button variant="ghost" className="sentence-review-skip-button" onClick={() => onSkip(review.id)}>
              건너뛰기
            </Button>
          ) : null}
          {canApply ? (
            <Button className="sentence-review-apply-button" onClick={() => onApply?.(review)}>
              이 문장 적용
            </Button>
          ) : ["needs_fix", "risky"].includes(review.status) ? (
            <span className="sentence-review-manual-label">직접 수정 권장</span>
          ) : null}
        </div>
      </div>
    );
  };

  return (
    <section className="sentence-review-sheet">
      <div className="sentence-review-head">
        <div>
          <strong>문장 첨삭</strong>
          <span>좋은 문장은 근거를 확인하고, 보완이 필요한 문장은 바로 교체할 수 있습니다.</span>
        </div>
        <div className="sentence-review-summary" aria-label="문장 첨삭 요약">
          <span>
            <strong>{counts.total}</strong>
            전체 검토
          </span>
          <span>
            <strong>{counts.good}</strong>
            좋음
          </span>
          <span>
            <strong>{counts.needs_fix + counts.risky}</strong>
            보완 필요
          </span>
          <span>
            <strong>{appliedCount}</strong>
            적용
          </span>
          <span>
            <strong>{remainingFixCount}</strong>
            남은 제안
          </span>
        </div>
      </div>

      <div className="sentence-review-body">
        {segments.length ? (
          segments.map((segment, index) => {
            if (segment.type === "text") return <span key={`text-${index}`}>{segment.text}</span>;
            const review = segment.review;
            const isActive = activeReviewId === review.id;
            return (
              <Fragment key={review.id}>
                <span
                  role="button"
                  tabIndex={0}
                  className={`sentence-review-line ${review.status} ${isActive ? "active" : ""}`}
                  onClick={() => onSelectReview?.(isActive ? "" : review.id)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      onSelectReview?.(isActive ? "" : review.id);
                    }
                  }}
                >
                  {segment.text}
                </span>
                {isActive ? renderNote(review) : null}
              </Fragment>
            );
          })
        ) : (
          <span>{text}</span>
        )}
      </div>

      <div className="sentence-review-foot">
        <span>적용하거나 건너뛴 보완 문장은 본문 첨삭 표시에서 제외됩니다.</span>
        {feedbackMessage ? <strong>{feedbackMessage}</strong> : null}
      </div>
    </section>
  );
}
