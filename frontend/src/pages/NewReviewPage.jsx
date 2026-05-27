import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { api } from "../api/client";
import Badge from "../components/Badge";
import Button from "../components/Button";
import CopyButton from "../components/CopyButton";
import EmptyState from "../components/EmptyState";
import FinalDocumentPanel from "../components/FinalDocumentPanel";
import ProgressBar from "../components/ProgressBar";
import ReviewQualityFeedback from "../components/ReviewQualityFeedback";
import RefinementPanel from "../components/RefinementPanel";
import SentenceReviewPreview from "../components/SentenceReviewPreview";
import Tabs from "../components/Tabs";
import { applySuggestionToText } from "../utils/suggestions";

const initialForm = {
  resume_text: "",
  cover_letter_text: "",
  target_job_role: "",
  job_posting_text: "",
  source_file_type: "txt",
  review_mode: "detailed",
  job_category_preset: "",
  consent_training: false,
};

const editorTabs = [
  { value: "cover_letter", label: "자기소개서" },
  { value: "resume", label: "이력서 요약" },
  { value: "job_posting", label: "채용공고" },
];

const coverLetterViewTabs = [
  { value: "write", label: "작성" },
  { value: "annotated", label: "문장 첨삭" },
];

const coachTabs = [
  { value: "summary", label: "검토 요약" },
  { value: "scores", label: "점수" },
  { value: "problems", label: "보완 포인트" },
  { value: "improved", label: "개선 문안" },
  { value: "interview", label: "면접 질문" },
  { value: "refine", label: "다듬기" },
  { value: "final", label: "최종본" },
];

const reviewModeOptions = [
  { value: "quick", label: "빠른 첨삭" },
  { value: "detailed", label: "상세 첨삭" },
  { value: "strict", label: "엄격한 첨삭" },
  { value: "rewrite-focused", label: "개선문 중심" },
];

const jobPresetOptions = ["웹개발자", "사무직", "교육행정", "마케팅", "사회복지사"];

const scoreLabels = {
  job_fit: "직무 적합도",
  specificity: "구체성",
  achievement: "성과 표현",
  writing_quality: "문장력",
  uniqueness: "차별성",
  structure: "논리 구조",
  keyword_match: "키워드 반영",
};

const loadingSteps = ["채용공고 키워드 분석 중", "자기소개서 구조 분석 중", "지원 직무에 맞춘 개선문 작성 중"];

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

function buildKeywordHints(jobPostingText) {
  const normalized = jobPostingText
    .replace(/[^\p{L}\p{N}\s]/gu, " ")
    .split(/\s+/)
    .map((token) => token.trim())
    .filter((token) => token.length >= 2);

  const ignore = new Set(["관련", "경험", "업무", "지원", "채용", "가능", "이상", "관리", "자기", "소개서", "이해"]);
  const counts = new Map();
  normalized.forEach((token) => {
    if (ignore.has(token)) return;
    counts.set(token, (counts.get(token) || 0) + 1);
  });

  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([token]) => token);
}

function AnalysisMeter({ form }) {
  const requiredReady = form.cover_letter_text.trim().length >= 20;
  const optionalChecks = [
    { label: "지원 직무", done: Boolean(form.target_job_role.trim()) },
    { label: "이력서 요약", done: form.resume_text.trim().length >= 20 },
    { label: "채용공고", done: form.job_posting_text.trim().length >= 20 },
  ];
  const optionalDone = optionalChecks.filter((item) => item.done).length;

  return (
    <div className="workspace-readiness">
      <div className="readiness-top">
        <span>{requiredReady ? "기본 검토 가능" : "자기소개서 필요"}</span>
        <strong>{requiredReady ? "1/1" : "0/1"}</strong>
      </div>
      <div className="readiness-subline">선택 보강 정보 {optionalDone}/3</div>
      <div className="readiness-dots" aria-label="선택 보강 정보 입력 상태">
        <span className={requiredReady ? "ready-dot done" : "ready-dot required"} title="자기소개서 (필수)" />
        {optionalChecks.map((item) => (
          <span key={item.label} className={item.done ? "ready-dot done" : "ready-dot"} title={`${item.label} (선택)`} />
        ))}
      </div>
    </div>
  );
}

function CoachTabContent({
  tab,
  review,
  improvedText,
  finalDocument,
  onApplyImprovedText,
  onRefine,
  refining,
  onSaveFinalDocument,
}) {
  const result = review?.review_result;

  if (!review || !result) return null;

  if (tab === "summary") {
    return (
      <div className="coach-tab-content">
        <section className="coach-score-cover">
          <div className="score-stamp">
            <strong>{result.total_score}</strong>
            <span>점</span>
          </div>
          <div>
            <Badge tone="brand">검토 결과</Badge>
            <h3>이번 문안의 상태</h3>
            <p>{result.summary}</p>
          </div>
        </section>
        <section className="coach-insight-stack">
          <div className="coach-mini-card success-card">
            <span>강점</span>
            <ul>
              {result.strengths.slice(0, 3).map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
          <div className="coach-mini-card warn-card">
            <span>보완</span>
            <ul>
              {result.problems.slice(0, 3).map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </div>
        </section>
      </div>
    );
  }

  if (tab === "scores") {
    return (
      <div className="coach-tab-content">
        <section className="coach-mini-card">
          <h3>항목별 점수</h3>
          <div className="score-progress-list">
            {Object.entries(scoreLabels).map(([key, label]) => (
              <div key={key} className="score-progress-row">
                <div className="score-progress-header">
                  <span>{label}</span>
                  <strong>{result.scores[key]}</strong>
                </div>
                <ProgressBar value={result.scores[key]} max={100} />
              </div>
            ))}
          </div>
        </section>
      </div>
    );
  }

  if (tab === "problems") {
    return (
      <div className="coach-tab-content">
        {result.problems.map((problem, index) => (
          <article key={`${problem}-${index}`} className="coach-feedback-note">
            <span>{String(index + 1).padStart(2, "0")}</span>
            <div>
              <h3>{problem}</h3>
              <p>{result.improvement_strategy[index] || "상황, 역할, 행동, 결과 순서로 다시 정리해 주세요."}</p>
            </div>
          </article>
        ))}
      </div>
    );
  }

  if (tab === "improved") {
    return (
      <div className="coach-tab-content">
        <section className="coach-mini-card">
          <div className="coach-section-head">
            <div>
              <h3>개선된 자기소개서</h3>
              <p>경험은 유지하고, 직무 연결성과 문장 흐름을 다듬었습니다.</p>
            </div>
          </div>
          <div className="coach-improved-text">{improvedText}</div>
          <div className="keyword-chip-row top-gap">
            {result.missing_keywords.map((keyword) => (
              <Badge key={keyword} tone="warning">
                {keyword}
              </Badge>
            ))}
          </div>
          <div className="button-row top-gap">
            <CopyButton text={improvedText} label="복사" />
            <Button variant="secondary" onClick={() => onApplyImprovedText(improvedText)}>
              본문에 반영
            </Button>
            <Button variant="ghost" onClick={() => downloadTextFile("coverfit-improved.txt", improvedText)}>
              TXT 저장
            </Button>
          </div>
        </section>
      </div>
    );
  }

  if (tab === "interview") {
    return (
      <div className="coach-tab-content">
        {result.interview_questions.map((question, index) => (
          <article key={question} className="interview-note-card">
            <span>Q{index + 1}</span>
            <p>{question}</p>
          </article>
        ))}
      </div>
    );
  }

  if (tab === "final") {
    return (
      <FinalDocumentPanel
        reviewId={review.id}
        jobRole={review.target_job_role}
        initialText={improvedText}
        savedDocument={finalDocument}
        onSave={onSaveFinalDocument}
        onApplyToEditor={onApplyImprovedText}
      />
    );
  }

  return (
    <RefinementPanel
      history={review.refinements}
      activeText={improvedText}
      loading={refining}
      onSubmit={onRefine}
      onApply={onApplyImprovedText}
    />
  );
}

export default function NewReviewPage() {
  const location = useLocation();
  const hydratedFromState = useRef(false);
  const [form, setForm] = useState(initialForm);
  const [documentTitle, setDocumentTitle] = useState("새 자기소개서");
  const [editorTab, setEditorTab] = useState("cover_letter");
  const [coverLetterViewMode, setCoverLetterViewMode] = useState("write");
  const [coachTab, setCoachTab] = useState("summary");
  const [review, setReview] = useState(null);
  const [activeImprovedText, setActiveImprovedText] = useState("");
  const [finalDocument, setFinalDocument] = useState(null);
  const [loading, setLoading] = useState(false);
  const [refining, setRefining] = useState(false);
  const [error, setError] = useState("");
  const [loadingStepIndex, setLoadingStepIndex] = useState(0);
  const [profile, setProfile] = useState(null);
  const [activeSentenceReviewId, setActiveSentenceReviewId] = useState("");
  const [appliedSentenceReviewIds, setAppliedSentenceReviewIds] = useState(new Set());
  const [skippedSentenceReviewIds, setSkippedSentenceReviewIds] = useState(new Set());
  const [suggestionFeedback, setSuggestionFeedback] = useState("");
  const [lastSuggestionSnapshot, setLastSuggestionSnapshot] = useState(null);

  useEffect(() => {
    let ignore = false;
    api
      .me()
      .then((data) => {
        if (!ignore) setProfile(data);
      })
      .catch(() => {
        if (!ignore) setProfile(null);
      });
    return () => {
      ignore = true;
    };
  }, []);

  useEffect(() => {
    if (!loading) {
      setLoadingStepIndex(0);
      return undefined;
    }
    const timer = window.setInterval(() => {
      setLoadingStepIndex((prev) => (prev + 1) % loadingSteps.length);
    }, 1200);
    return () => window.clearInterval(timer);
  }, [loading]);

  useEffect(() => {
    if (hydratedFromState.current) return;
    const seeded = location.state?.seedReview;
    if (!seeded) return;
    hydratedFromState.current = true;
    setDocumentTitle(`${seeded.target_job_role || "문서"} 자기소개서`);
    setForm((prev) => ({
      ...prev,
      target_job_role: seeded.target_job_role || "",
      job_posting_text: seeded.job_posting_text || "",
      resume_text: seeded.resume_text || "",
      cover_letter_text: seeded.cover_letter_text || "",
      review_mode: seeded.review_mode || prev.review_mode,
      job_category_preset: seeded.job_category_preset || "",
    }));
  }, [location.state]);

  const keywordHints = useMemo(() => buildKeywordHints(form.job_posting_text), [form.job_posting_text]);
  const result = review?.review_result;
  const suggestions = result?.suggestions || [];
  const sentenceReviews = result?.sentence_reviews || [];
  const unresolvedSentenceReviews = sentenceReviews.filter(
    (item) => !appliedSentenceReviewIds.has(item.id) && !skippedSentenceReviewIds.has(item.id),
  );
  const unresolvedSuggestions = suggestions.filter(
    (item) => !appliedSentenceReviewIds.has(item.id) && !skippedSentenceReviewIds.has(item.id),
  );
  const appliedSuggestionCount = appliedSentenceReviewIds.size;
  const skippedSuggestionCount = skippedSentenceReviewIds.size;
  const reviewableSentenceCount = countReviewableSentences(form.cover_letter_text);
  const sentenceReviewTotal = Math.max(sentenceReviews.length || suggestions.length, Math.min(8, reviewableSentenceCount));
  const sentenceReviewNeedsFix = sentenceReviews.length
    ? sentenceReviews.filter((item) => item.status === "needs_fix" || item.status === "risky").length
    : suggestions.length;
  const remainingSentenceFixCount = sentenceReviews.length
    ? unresolvedSentenceReviews.filter((item) => item.status === "needs_fix" || item.status === "risky").length
    : unresolvedSuggestions.length;
  const isWorkingTextSavedAsFinal = Boolean(finalDocument?.final_text && finalDocument.final_text === activeImprovedText);

  const onChange = (event) => {
    const { name, value, type, checked } = event.target;
    setForm((prev) => ({ ...prev, [name]: type === "checkbox" ? checked : value }));
  };

  const appendResumeChip = (label) => {
    const nextText = form.resume_text ? `${form.resume_text}\n- ${label}: ` : `- ${label}: `;
    setForm((prev) => ({ ...prev, resume_text: nextText }));
    setEditorTab("resume");
  };

  const onSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const payload = {
        resume_text: form.resume_text,
        cover_letter_text: form.cover_letter_text,
        target_job_role: form.target_job_role,
        job_posting_text: form.job_posting_text,
        source_file_type: form.source_file_type,
        review_mode: form.review_mode,
        job_category_preset: form.job_category_preset || null,
      };
      const createdReview = await api.createReview(payload);
      if (form.consent_training) {
        await api.consentTraining(createdReview.id, true);
        createdReview.consent_given = true;
      }
      setReview(createdReview);
      setFinalDocument(createdReview.final_document || null);
      setActiveImprovedText(createdReview.review_result.improved_cover_letter);
      setActiveSentenceReviewId("");
      setAppliedSentenceReviewIds(new Set());
      setSkippedSentenceReviewIds(new Set());
      setSuggestionFeedback("");
      setLastSuggestionSnapshot(null);
      setCoachTab("summary");
      setCoverLetterViewMode(
        createdReview.review_result.sentence_reviews?.length || createdReview.review_result.suggestions?.length ? "annotated" : "write",
      );
      api.me().then(setProfile).catch(() => {});
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

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
      if (latest?.refined_text) setActiveImprovedText(latest.refined_text);
      api.me().then(setProfile).catch(() => {});
    } finally {
      setRefining(false);
    }
  };

  const handleApplyImprovedText = (text) => {
    setActiveImprovedText(text);
    setForm((prev) => ({ ...prev, cover_letter_text: text }));
    setEditorTab("cover_letter");
    setCoverLetterViewMode("write");
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
    const applied = applySuggestionToText(form.cover_letter_text, suggestion);
    setSuggestionFeedback(applied.message);
    if (!applied.applied) return;

    // 문장별 보완 제안은 사용자가 현재 다듬고 있는 작업 문안에 바로 반영한다.
    // 동시에 우측 개선문/최종본 패널의 기준 텍스트도 갱신해서 PDF 저장 시 다른 문안이 들어가는 혼선을 줄인다.
    setLastSuggestionSnapshot({
      text: form.cover_letter_text,
      improvedText: activeImprovedText,
      finalDocument,
      suggestionId: sentenceReview.id,
    });
    setForm((prev) => ({ ...prev, cover_letter_text: applied.updatedText }));
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
    setCoverLetterViewMode(remainingCount > 0 ? "annotated" : "write");
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
    setForm((prev) => ({ ...prev, cover_letter_text: lastSuggestionSnapshot.text }));
    setActiveImprovedText(lastSuggestionSnapshot.improvedText || "");
    setFinalDocument(lastSuggestionSnapshot.finalDocument || null);
    setAppliedSentenceReviewIds((prev) => {
      const next = new Set(prev);
      next.delete(lastSuggestionSnapshot.suggestionId);
      return next;
    });
    setSuggestionFeedback("마지막 적용을 되돌렸습니다.");
    setLastSuggestionSnapshot(null);
    setCoverLetterViewMode("annotated");
  };

  const handleSaveFinalDocument = async (payload) => {
    if (!review) return null;
    const saved = await api.saveFinalDocument(review.id, payload);
    setFinalDocument(saved);
    setActiveImprovedText(saved.final_text);
    return saved;
  };

  const handleSaveWorkingTextAsFinal = async () => {
    if (!review || activeImprovedText.trim().length < 20) return;
    const saved = await api.saveFinalDocument(review.id, {
      final_text: activeImprovedText,
      source: "manual_edit",
    });
    setFinalDocument(saved);
    setSuggestionFeedback("현재 작업 문안을 최종본으로 저장했습니다.");
  };

  const handleWorkspacePdfExport = async () => {
    if (!review) return;
    const textToExport = activeImprovedText || finalDocument?.final_text || form.cover_letter_text;
    if (textToExport.trim().length >= 20) {
      const saved = await api.saveFinalDocument(review.id, {
        final_text: textToExport,
        source: finalDocument?.source || "manual_edit",
      });
      setFinalDocument(saved);
    }
    await api.exportReviewPdf(review.id, `coverfit_final_${review.target_job_role || "cover_letter"}.pdf`);
    api.me().then(setProfile).catch(() => {});
  };

  return (
    <form className="writer-app" onSubmit={onSubmit}>
      <header className="writer-header">
        <div className="writer-brand-area">
          <Link to="/dashboard" className="writer-logo">
            <span>CF</span>
          </Link>
          <div>
            <strong>CoverFit AI</strong>
            <p>AI 검토부터 최종본 작성까지</p>
          </div>
        </div>
        <div className="writer-document-tabs">
          <span className="writer-doc-tab active">{documentTitle || "새 자기소개서"}</span>
          <button type="button" className="writer-doc-add" aria-label="새 문서">
            +
          </button>
        </div>
        <div className="writer-header-actions">
          {profile?.usage ? (
            <span className="writer-usage-note">
              오늘 첨삭 {profile.usage.review_daily.unlimited ? "무제한" : `${profile.usage.review_daily.used}/${profile.usage.review_daily.limit}`}
            </span>
          ) : null}
          {review ? <Link to={`/reviews/${review.id}`}>상세 결과</Link> : null}
          <Link to="/reviews/history">기록</Link>
          <button type="button" className="writer-outline-button" onClick={handleWorkspacePdfExport} disabled={!review}>
            PDF 저장
          </button>
          <button type="submit" className="writer-primary-button" disabled={loading}>
            {loading ? "분석 중" : "AI 첨삭 받기"}
          </button>
        </div>
      </header>

      <div className="writer-formatbar">
        <div className="writer-format-left">
          <button type="button">↶</button>
          <button type="button">↷</button>
          <span className="format-divider" />
          <select value="100%" onChange={() => {}}>
            <option>100%</option>
          </select>
          <select value="Cover Letter" onChange={() => {}}>
            <option>Cover Letter</option>
          </select>
          <span className="format-divider" />
          <button type="button" className="bold-button">B</button>
          <button type="button" className="italic-button">I</button>
          <button type="button">•</button>
          <button type="button">1.</button>
        </div>
        <div className="writer-format-right">
          <Badge tone={form.consent_training ? "success" : "neutral"}>학습 동의 {form.consent_training ? "ON" : "OFF"}</Badge>
          <Badge tone="brand">{form.review_mode}</Badge>
        </div>
      </div>

      <main className="writer-workspace">
        <section className="writer-editor-area">
          <div className="writer-left-rail" aria-label="문서 메뉴">
            {editorTabs.map((tab) => (
              <button
                key={tab.value}
                type="button"
                className={editorTab === tab.value ? "rail-button active" : "rail-button"}
                onClick={() => setEditorTab(tab.value)}
                title={tab.label}
              >
                {tab.label.slice(0, 2)}
              </button>
            ))}
          </div>

          <section className="writer-paper-shell">
            <div className="writer-paper-meta">
              <input
                className="writer-title-input"
                value={documentTitle}
                onChange={(event) => setDocumentTitle(event.target.value)}
                placeholder="문서 제목"
              />
              <div className="writer-meta-grid">
                <label>
                  <span>지원 직무 (선택)</span>
                  <input
                    name="target_job_role"
                    value={form.target_job_role}
                    onChange={onChange}
                    placeholder="예: 백엔드 개발자"
                  />
                  <small>없으면 비워두셔도 됩니다. 자기소개서만으로도 기본 첨삭이 가능합니다.</small>
                </label>
                <label>
                  <span>직무 프리셋</span>
                  <select name="job_category_preset" value={form.job_category_preset} onChange={onChange}>
                    <option value="">선택 안 함</option>
                    {jobPresetOptions.map((option) => (
                      <option key={option} value={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>첨삭 모드</span>
                  <select name="review_mode" value={form.review_mode} onChange={onChange}>
                    {reviewModeOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
            </div>

            <div className="writer-paper">
              <div className="writer-paper-toolbar">
                <Tabs tabs={editorTabs} value={editorTab} onChange={setEditorTab} />
                <span className="writer-character-count">
                  {editorTab === "cover_letter"
                    ? form.cover_letter_text.length
                    : editorTab === "resume"
                      ? form.resume_text.length
                      : form.job_posting_text.length}
                  자
                </span>
              </div>

              {editorTab === "cover_letter" ? (
                <div className="paper-tab-stack">
                  <div className="editor-mode-strip">
                    <Tabs tabs={coverLetterViewTabs} value={coverLetterViewMode} onChange={setCoverLetterViewMode} />
                    <span className="editor-helper-note">개인정보는 가능한 제거하고 입력해 주세요.</span>
                  </div>

                  {coverLetterViewMode === "write" ? (
                    <textarea
                      className="paper-editor-textarea"
                      name="cover_letter_text"
                      value={form.cover_letter_text}
                      onChange={onChange}
                      placeholder="자기소개서를 붙여 넣거나 바로 작성해 보세요. 지원 동기, 경험, 역할, 결과가 드러나면 더 정확하게 첨삭됩니다."
                      required
                    />
                  ) : (
                    <SentenceReviewPreview
                      text={form.cover_letter_text}
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

                  {sentenceReviewTotal ? (
                    <div className="suggestion-inline-footer">
                      <span>
                        {remainingSentenceFixCount
                          ? `남은 보완 문장 ${remainingSentenceFixCount}개가 본문에 표시됩니다.`
                          : "선택한 보완 문장을 모두 처리했습니다."}
                        {review && !isWorkingTextSavedAsFinal ? " 현재 작업 문안은 아직 최종본에 저장되지 않았습니다." : ""}
                      </span>
                      <div className="button-row compact">
                        <button type="button" className="ghost-button" onClick={() => setCoverLetterViewMode("annotated")}>
                          문장 첨삭 보기
                        </button>
                        {review ? (
                          <button
                            type="button"
                            className="ghost-button"
                            onClick={handleSaveWorkingTextAsFinal}
                            disabled={isWorkingTextSavedAsFinal || activeImprovedText.trim().length < 20}
                          >
                            현재 문안 최종본 저장
                          </button>
                        ) : null}
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
                  ) : null}

                  <div className="review-action-bar">
                    <div>
                      <strong>자기소개서만으로도 검토할 수 있습니다.</strong>
                      <p>자기소개서만 입력해도 기본 첨삭이 가능합니다. 이력서와 채용공고를 추가하면 더 정확해집니다.</p>
                    </div>
                    <button type="submit" className="writer-primary-button editor-cta" disabled={loading}>
                      {loading ? "AI 첨삭 중" : "AI 첨삭 받기"}
                    </button>
                  </div>
                </div>
              ) : null}

              {editorTab === "resume" ? (
                <div className="paper-tab-stack">
                  <div className="resume-chip-row">
                    {["프로젝트 경험", "인턴 경험", "교육/수료", "자격증", "기술스택"].map((chip) => (
                      <button key={chip} type="button" onClick={() => appendResumeChip(chip)}>
                        + {chip}
                      </button>
                    ))}
                  </div>
                  <div className="field-helper-block">
                    <strong>이력서 요약 (선택)</strong>
                    <p>없으면 비워두셔도 됩니다. 자기소개서에 적지 못한 역할과 성과를 보완할 때 유용합니다.</p>
                  </div>
                  <textarea
                    className="paper-editor-textarea medium"
                    name="resume_text"
                    value={form.resume_text}
                    onChange={onChange}
                    placeholder="예: 3개월 프로젝트에서 API 연동과 배포를 맡았고, 오류 응답 처리 로직을 개선했습니다."
                  />
                </div>
              ) : null}

              {editorTab === "job_posting" ? (
                <div className="paper-tab-stack">
                  <div className="field-helper-block">
                    <strong>채용공고 (선택)</strong>
                    <p>채용공고를 넣으면 직무 적합도와 키워드 분석이 더 정확해집니다. 없으면 일반적인 기준으로 검토합니다.</p>
                  </div>
                  <textarea
                    className="paper-editor-textarea medium"
                    name="job_posting_text"
                    value={form.job_posting_text}
                    onChange={onChange}
                    placeholder="채용공고를 붙여 넣으면 주요 키워드를 추려서 직무 연결성을 더 정확하게 봅니다."
                  />
                  <div className="writer-keyword-panel">
                    <strong>자동 감지 키워드</strong>
                    {keywordHints.length ? (
                      <div className="keyword-chip-row">
                        {keywordHints.map((keyword) => (
                          <Badge key={keyword} tone="neutral">
                            {keyword}
                          </Badge>
                        ))}
                      </div>
                    ) : (
                      <p>채용공고를 입력하면 주요 키워드가 표시됩니다.</p>
                    )}
                  </div>
                </div>
              ) : null}
            </div>

            <div className="writer-paper-footer">
              <label className="writer-consent">
                <input type="checkbox" name="consent_training" checked={form.consent_training} onChange={onChange} />
                <span>개인정보를 제거한 뒤 첨삭 품질 개선용 학습 데이터로 사용하는 것에 동의합니다.</span>
              </label>
              <p>
                원본 이력서와 자기소개서에는 개인정보가 포함될 수 있습니다. 학습 데이터 활용은 사용자가 명시적으로
                동의한 경우에만 진행되며, 동의하지 않아도 첨삭 서비스 이용은 가능합니다.
              </p>
              {error ? <div className="error-box">{error}</div> : null}
            </div>
          </section>
        </section>

        <aside className="writer-ai-dock">
          <div className="ai-dock-header">
            <div>
              <span className="dock-eyebrow">검토 메모</span>
              <h2>검토 결과</h2>
              {sentenceReviewTotal ? (
                <p className="dock-inline-note">
                  검토 문장 {sentenceReviewTotal}개 · 보완 필요 {sentenceReviewNeedsFix}개 · 적용 {appliedSuggestionCount}개 · 남은 보완 {remainingSentenceFixCount}개 · 문장 첨삭 탭에서 확인
                </p>
              ) : null}
            </div>
            <AnalysisMeter form={form} />
          </div>

          {result ? <Tabs tabs={coachTabs} value={coachTab} onChange={setCoachTab} /> : null}

          <div className="ai-dock-body">
            {!review && !loading ? (
              <EmptyState
                title="문서를 준비하면 바로 첨삭을 시작할 수 있습니다."
                description="자기소개서만 있어도 기본 검토가 가능하고, 추가 정보가 있으면 더 정교하게 분석합니다."
                actions={
                  <ul className="workspace-checklist">
                    <li className={form.cover_letter_text ? "done" : ""}>자기소개서 입력</li>
                    <li className={form.target_job_role ? "done" : ""}>지원 직무 입력 (선택)</li>
                    <li className={form.resume_text ? "done" : ""}>이력서 요약 입력 (선택)</li>
                    <li className={form.job_posting_text ? "done" : ""}>채용공고 입력 (선택)</li>
                  </ul>
                }
              />
            ) : null}

            {loading ? (
              <div className="coach-loading-state">
                <div className="loading-skeleton-block" />
                <div className="loading-skeleton-block short" />
                <div className="loading-skeleton-block" />
                <div className="loading-status-card">
                  <Badge tone="warning">분석 진행 중</Badge>
                  <strong>{loadingSteps[loadingStepIndex]}</strong>
                  <p className="muted">입력된 자기소개서를 기준으로 보완 메모와 개선 문안을 정리하고 있습니다.</p>
                </div>
              </div>
            ) : null}

            {review && result ? (
              <>
                <CoachTabContent
                  tab={coachTab}
                  review={review}
                  improvedText={activeImprovedText || result.improved_cover_letter}
                  finalDocument={finalDocument}
                  onApplyImprovedText={handleApplyImprovedText}
                  onRefine={handleRefine}
                  refining={refining}
                  onSaveFinalDocument={handleSaveFinalDocument}
                />
                <ReviewQualityFeedback reviewId={review.id} />
              </>
            ) : null}
          </div>
        </aside>
      </main>
    </form>
  );
}
