import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import Badge from "../components/Badge";
import BeforeAfterComparison from "../components/BeforeAfterComparison";
import Button from "../components/Button";
import CopyButton from "../components/CopyButton";
import FinalDocumentPanel from "../components/FinalDocumentPanel";
import Layout from "../components/Layout";
import ProgressBar from "../components/ProgressBar";
import ReviewQualityFeedback from "../components/ReviewQualityFeedback";
import RefinementPanel from "../components/RefinementPanel";
import SentenceReviewPreview from "../components/SentenceReviewPreview";
import Tabs from "../components/Tabs";
import { applySuggestionToText } from "../utils/suggestions";

const scoreLabels = {
  job_fit: "직무 적합도",
  specificity: "구체성",
  achievement: "성과 표현",
  writing_quality: "문장력",
  uniqueness: "차별성",
  structure: "논리 구조",
  keyword_match: "키워드 반영",
};

const documentTabs = [
  { value: "original", label: "원문" },
  { value: "annotated", label: "문장 첨삭" },
];

function countReviewableSentences(text = "") {
  const matches = text.match(/[^.!?\n。！？]+(?:[.!?。！？]+|$)/g) || [];
  return matches.map((item) => item.trim()).filter(Boolean).length;
}

function downloadTextFile(filename, text) {
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export default function ReviewResultPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [review, setReview] = useState(null);
  const [activeImprovedText, setActiveImprovedText] = useState("");
  const [finalDocument, setFinalDocument] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refining, setRefining] = useState(false);
  const [error, setError] = useState("");
  const [documentView, setDocumentView] = useState("original");
  const [workingCoverLetterText, setWorkingCoverLetterText] = useState("");
  const [activeSentenceReviewId, setActiveSentenceReviewId] = useState("");
  const [appliedSentenceReviewIds, setAppliedSentenceReviewIds] = useState(new Set());
  const [skippedSentenceReviewIds, setSkippedSentenceReviewIds] = useState(new Set());
  const [suggestionFeedback, setSuggestionFeedback] = useState("");
  const [lastSuggestionSnapshot, setLastSuggestionSnapshot] = useState(null);

  const loadReview = async () => {
    setLoading(true);
    try {
      const data = await api.getReview(id);
      setReview(data);
      setFinalDocument(data.final_document || null);
      setWorkingCoverLetterText((prev) => prev || data.cover_letter_text || "");
      setActiveImprovedText((prev) => prev || data.final_document?.final_text || data.review_result.improved_cover_letter);
      setActiveSentenceReviewId("");
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReview();
  }, [id]);

  const privacyWarnings = useMemo(
    () => [
      "원본 이력서와 자기소개서에는 개인정보가 포함될 수 있습니다.",
      "학습 데이터 활용은 사용자가 명시적으로 동의한 경우에만 진행됩니다.",
      "학습용 데이터는 개인정보 제거 후 별도 저장됩니다.",
      "동의하지 않아도 첨삭 서비스 이용은 가능합니다.",
    ],
    [],
  );

  const suggestions = review?.review_result?.suggestions || [];
  const sentenceReviews = review?.review_result?.sentence_reviews || [];
  const unresolvedSentenceReviews = sentenceReviews.filter(
    (item) => !appliedSentenceReviewIds.has(item.id) && !skippedSentenceReviewIds.has(item.id),
  );
  const unresolvedSuggestions = suggestions.filter(
    (item) => !appliedSentenceReviewIds.has(item.id) && !skippedSentenceReviewIds.has(item.id),
  );
  const appliedSuggestionCount = appliedSentenceReviewIds.size;
  const skippedSuggestionCount = skippedSentenceReviewIds.size;
  const reviewableSentenceCount = countReviewableSentences(workingCoverLetterText || review?.cover_letter_text || "");
  const sentenceReviewTotal = Math.max(sentenceReviews.length || suggestions.length, Math.min(8, reviewableSentenceCount));
  const remainingSentenceFixCount = sentenceReviews.length
    ? unresolvedSentenceReviews.filter((item) => item.status === "needs_fix" || item.status === "risky").length
    : unresolvedSuggestions.length;
  const isWorkingTextSavedAsFinal = Boolean(finalDocument?.final_text && finalDocument.final_text === activeImprovedText);

  const handleRefine = async (instruction) => {
    if (!review) return;
    setRefining(true);
    try {
      await api.refineReview(review.id, {
        instruction,
        current_text: activeImprovedText,
        target_job_role: review.target_job_role,
        job_posting_text: review.job_posting_text,
      });
      const refreshed = await api.getReview(review.id);
      setReview(refreshed);
      setFinalDocument(refreshed.final_document || null);
      const latest = refreshed.refinements[refreshed.refinements.length - 1];
      if (latest?.refined_text) {
        setActiveImprovedText(latest.refined_text);
      }
    } finally {
      setRefining(false);
    }
  };

  const handleSaveFinalDocument = async (payload) => {
    if (!review) return null;
    const saved = await api.saveFinalDocument(review.id, payload);
    setFinalDocument(saved);
    setActiveImprovedText(saved.final_text);
    setWorkingCoverLetterText(saved.final_text);
    return saved;
  };

  const handleApplySentenceReview = (sentenceReview) => {
    const suggestion = {
      id: sentenceReview.id,
      original_text: sentenceReview.sentence_text || sentenceReview.original_text,
      start_index: sentenceReview.start_index,
      end_index: sentenceReview.end_index,
      suggested_text: sentenceReview.suggested_text,
      apply_type: "replace",
    };
    const targetText = workingCoverLetterText || review?.cover_letter_text || "";
    const applied = applySuggestionToText(targetText, suggestion);
    setSuggestionFeedback(applied.message);
    if (!applied.applied) return;

    // 상세 화면의 문장별 제안은 원문 기반 작업 문안에 먼저 적용한다.
    // 적용된 작업 문안은 개선문/최종본 후보로도 같이 넘겨 PDF 저장 기준이 어긋나지 않게 한다.
    setLastSuggestionSnapshot({
      text: targetText,
      improvedText: activeImprovedText,
      finalDocument,
      suggestionId: sentenceReview.id,
    });

    setWorkingCoverLetterText(applied.updatedText);
    setActiveImprovedText(applied.updatedText);
    setSuggestionFeedback(applied.warning || "현재 작성 문안에 적용되었습니다. 최종본으로 저장하면 PDF에 반영됩니다.");

    setAppliedSentenceReviewIds((prev) => new Set([...prev, sentenceReview.id]));
    setSkippedSentenceReviewIds((prev) => {
      const next = new Set(prev);
      next.delete(sentenceReview.id);
      return next;
    });
    setActiveSentenceReviewId("");
    const remainingCount = sentenceReviews.length
      ? sentenceReviews.filter(
          (item) =>
            item.id !== sentenceReview.id &&
            !skippedSentenceReviewIds.has(item.id) &&
            (item.status === "needs_fix" || item.status === "risky"),
        ).length
      : suggestions.filter((item) => item.id !== sentenceReview.id && !skippedSentenceReviewIds.has(item.id)).length;
    setDocumentView(remainingCount > 0 ? "annotated" : "original");
  };

  const handleSkipSentenceReview = (reviewId) => {
    setSkippedSentenceReviewIds((prev) => new Set([...prev, reviewId]));
    setSuggestionFeedback("건너뛰었습니다.");
    if (activeSentenceReviewId === reviewId) {
      setActiveSentenceReviewId("");
    }
  };

  const handleUndoSuggestion = () => {
    if (!lastSuggestionSnapshot) return;
    setWorkingCoverLetterText(lastSuggestionSnapshot.text);
    setActiveImprovedText(lastSuggestionSnapshot.improvedText || "");
    setFinalDocument(lastSuggestionSnapshot.finalDocument || null);
    setAppliedSentenceReviewIds((prev) => {
      const next = new Set(prev);
      next.delete(lastSuggestionSnapshot.suggestionId);
      return next;
    });
    setSuggestionFeedback("마지막 적용을 되돌렸습니다.");
    setLastSuggestionSnapshot(null);
    setDocumentView("annotated");
  };

  const handleExportPdf = async () => {
    if (!review) return;
    const textToExport = activeImprovedText || finalDocument?.final_text || review.review_result.improved_cover_letter;
    if (textToExport.trim().length >= 20) {
      const saved = await api.saveFinalDocument(review.id, {
        final_text: textToExport,
        source: finalDocument?.source || "manual_edit",
      });
      setFinalDocument(saved);
    }
    await api.exportReviewPdf(review.id, `coverfit_final_${review.target_job_role || "cover_letter"}.pdf`);
  };

  const startNewFromCurrent = () => {
    if (!review) return;
    navigate("/reviews/new", {
      state: {
        seedReview: {
          target_job_role: review.target_job_role,
          job_posting_text: review.job_posting_text,
          resume_text: review.resume_text,
          cover_letter_text: activeImprovedText || review.cover_letter_text,
          review_mode: review.review_mode,
          job_category_preset: review.job_category_preset,
        },
      },
    });
  };

  const handleApplyFinalTextToEditor = (text) => {
    setActiveImprovedText(text);
    setWorkingCoverLetterText(text);
    setSuggestionFeedback("최종본 문안을 현재 작업 문안에 반영했습니다.");
  };

  return (
    <Layout title="저장된 첨삭 결과" subtitle="AI 검토 결과를 다시 읽고 최종 문안을 수정하거나 PDF로 내보낼 수 있습니다.">
      {loading ? <div className="card">리뷰 결과를 불러오는 중입니다...</div> : null}
      {error ? <div className="error-box">{error}</div> : null}
      {!loading && review ? (
        <div className="detail-page">
          <section className="detail-summary-bar card">
            <div className="summary-main">
              <Badge tone="brand">{review.review_mode}</Badge>
              <h2>{review.target_job_role || "직무 미입력 문안"}</h2>
              <p>{new Date(review.created_at).toLocaleString()} 저장</p>
            </div>
            <div className="summary-metrics">
              <div className="summary-metric">
                <span>총점</span>
                <strong>{review.review_result.total_score}</strong>
              </div>
              <div className="summary-metric">
                <span>리파인 횟수</span>
                <strong>{review.refinements.length}</strong>
              </div>
              <div className="summary-metric">
                <span>최종본</span>
                <strong>{finalDocument ? "저장됨" : "미저장"}</strong>
              </div>
            </div>
            <div className="button-row">
              <CopyButton text={activeImprovedText || review.review_result.improved_cover_letter} label="최종 문안 복사" />
              <Button
                variant="ghost"
                onClick={() => downloadTextFile("coverfit-final.txt", activeImprovedText || review.review_result.improved_cover_letter)}
              >
                TXT 저장
              </Button>
              <Button variant="secondary" onClick={handleExportPdf}>
                PDF 내보내기
              </Button>
              <Link to="/reviews/history">
                <Button variant="secondary">히스토리로 돌아가기</Button>
              </Link>
              <Button onClick={startNewFromCurrent}>이 결과로 새 첨삭 시작</Button>
            </div>
          </section>

          <div className="detail-grid-2">
            <div className="detail-main-column">
              <BeforeAfterComparison
                originalText={review.cover_letter_text}
                improvedText={activeImprovedText || review.review_result.improved_cover_letter}
              />

              {sentenceReviewTotal ? (
                <section className="card soft-card">
                  <div className="section-header">
                    <div>
                      <h2>문장 첨삭</h2>
                      <p className="muted">원문 기준 작업 문안을 한 문장씩 확인하고, 적용한 문장은 최종본 후보로 이어갈 수 있습니다.</p>
                    </div>
                    <Tabs tabs={documentTabs} value={documentView} onChange={setDocumentView} />
                  </div>

                  {documentView === "original" ? (
                    <div className="editor-preview compact">{workingCoverLetterText || review.cover_letter_text}</div>
                  ) : (
                    <SentenceReviewPreview
                      text={workingCoverLetterText || review.cover_letter_text}
                      sentenceReviews={sentenceReviews}
                      suggestions={suggestions}
                      activeReviewId={activeSentenceReviewId}
                      onSelectReview={setActiveSentenceReviewId}
                      onApply={handleApplySentenceReview}
                      onSkip={handleSkipSentenceReview}
                      appliedReviewIds={appliedSentenceReviewIds}
                      skippedReviewIds={skippedSentenceReviewIds}
                      appliedCount={appliedSuggestionCount}
                      skippedCount={skippedSuggestionCount}
                      feedbackMessage={suggestionFeedback}
                    />
                  )}

                  <div className="suggestion-inline-footer">
                    <span>
                      {remainingSentenceFixCount
                        ? `남은 보완 문장 ${remainingSentenceFixCount}개가 표시됩니다.`
                        : "선택한 보완 문장을 모두 처리했습니다."}
                      {!isWorkingTextSavedAsFinal ? " 현재 작업 문안은 아직 최종본에 저장되지 않았습니다." : ""}
                    </span>
                    <div className="button-row compact">
                      <button type="button" className="ghost-button" onClick={() => setDocumentView("annotated")}>
                        문장 첨삭 보기
                      </button>
                      {activeSentenceReviewId ? (
                        <button
                          type="button"
                          className="ghost-button"
                          onClick={() => handleSkipSentenceReview(activeSentenceReviewId)}
                        >
                          이 제안 건너뛰기
                        </button>
                      ) : null}
                      {lastSuggestionSnapshot ? (
                        <button type="button" className="ghost-button" onClick={handleUndoSuggestion}>
                          마지막 적용 되돌리기
                        </button>
                      ) : null}
                    </div>
                  </div>
                </section>
              ) : null}

              <FinalDocumentPanel
                reviewId={review.id}
                jobRole={review.target_job_role}
                initialText={activeImprovedText || review.review_result.improved_cover_letter}
                savedDocument={finalDocument}
                onSave={handleSaveFinalDocument}
                onApplyToEditor={handleApplyFinalTextToEditor}
              />

              <section className="card">
                <div className="section-header">
                  <div>
                    <h2>문서 컨텍스트</h2>
                    <p className="muted">AI가 참고한 직무, 이력, 채용공고입니다.</p>
                  </div>
                </div>
                <div className="detail-context-grid">
                  <article className="soft-card">
                    <h3>이력서 요약</h3>
                    <div className="editor-preview compact">
                      {review.resume_text?.trim() || "입력하지 않았습니다. 자기소개서 원문 기준으로 검토했습니다."}
                    </div>
                  </article>
                  <article className="soft-card">
                    <h3>채용공고</h3>
                    <div className="editor-preview compact">
                      {review.job_posting_text?.trim() || "입력하지 않았습니다. 일반적인 직무 기준으로 검토했습니다."}
                    </div>
                  </article>
                </div>
              </section>

              <RefinementPanel
                history={review.refinements}
                activeText={activeImprovedText || review.review_result.improved_cover_letter}
                loading={refining}
                onSubmit={handleRefine}
                onApply={setActiveImprovedText}
              />

              <ReviewQualityFeedback reviewId={review.id} />
            </div>

            <aside className="detail-side-column">
              <section className="card soft-card">
                <h2>검토 요약</h2>
                <p className="long-text">{review.review_result.summary}</p>
              </section>

              <section className="card soft-card">
                <h2>항목별 점수</h2>
                <div className="score-progress-list">
                  {Object.entries(scoreLabels).map(([key, label]) => (
                    <div key={key} className="score-progress-row">
                      <div className="score-progress-header">
                        <span>{label}</span>
                        <strong>{review.review_result.scores[key]}</strong>
                      </div>
                      <ProgressBar value={review.review_result.scores[key]} max={100} />
                    </div>
                  ))}
                </div>
              </section>

              <section className="card soft-card">
                <h2>강점</h2>
                <ul className="feature-list">
                  {review.review_result.strengths.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </section>

              <section className="card soft-card">
                <h2>보완 포인트</h2>
                <ul className="feature-list warning-list">
                  {review.review_result.problems.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </section>

              <section className="card soft-card">
                <h2>개선 전략</h2>
                <ul className="feature-list">
                  {review.review_result.improvement_strategy.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </section>

              <section className="card soft-card">
                <h2>면접 예상 질문</h2>
                <div className="interview-card-list">
                  {review.review_result.interview_questions.map((question, index) => (
                    <article key={question} className="interview-card minimal">
                      <span className="interview-card-step">Q{index + 1}</span>
                      <p>{question}</p>
                    </article>
                  ))}
                </div>
              </section>

              <section className="card soft-card">
                <h2>개인정보 및 학습 데이터 안내</h2>
                <ul className="compact-list">
                  {privacyWarnings.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </section>
            </aside>
          </div>
        </div>
      ) : null}
    </Layout>
  );
}
