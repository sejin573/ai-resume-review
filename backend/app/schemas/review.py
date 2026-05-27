from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.prompts import normalize_review_mode


class ReviewScores(BaseModel):
    job_fit: float = Field(ge=0, le=100)
    specificity: float = Field(ge=0, le=100)
    achievement: float = Field(ge=0, le=100)
    writing_quality: float = Field(ge=0, le=100)
    uniqueness: float = Field(ge=0, le=100)
    structure: float = Field(ge=0, le=100)
    keyword_match: float = Field(ge=0, le=100)


class JobPostingAnalysisResult(BaseModel):
    job_keywords: list[str] = Field(default_factory=list)
    required_competencies: list[str] = Field(default_factory=list)
    preferred_experiences: list[str] = Field(default_factory=list)
    tone_hint: str = ""
    risk_notes: list[str] = Field(default_factory=list)


class CoverLetterDiagnosisResult(BaseModel):
    core_experiences: list[str] = Field(default_factory=list)
    weak_points: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    overused_expressions: list[str] = Field(default_factory=list)
    job_fit_notes: list[str] = Field(default_factory=list)
    recommended_structure: list[str] = Field(default_factory=list)


class CoverLetterSuggestion(BaseModel):
    id: str = ""
    severity: str = Field(default="medium")
    category: str = Field(default="specificity")
    original_text: str = ""
    start_index: int | None = None
    end_index: int | None = None
    issue: str = ""
    reason: str = ""
    suggested_text: str = ""
    apply_type: str = Field(default="replace")
    confidence: float = Field(default=0.5)

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, value: str) -> str:
        supported = {"low", "medium", "high"}
        if value not in supported:
            return "medium"
        return value

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        supported = {
            "job_fit",
            "specificity",
            "achievement",
            "writing_quality",
            "structure",
            "keyword_match",
            "tone",
            "redundancy",
        }
        if value not in supported:
            return "specificity"
        return value

    @field_validator("apply_type")
    @classmethod
    def validate_apply_type(cls, value: str) -> str:
        supported = {"replace", "append_after", "rewrite_paragraph"}
        if value not in supported:
            return "replace"
        return value

    @field_validator("confidence")
    @classmethod
    def clamp_confidence(cls, value: float) -> float:
        return max(0.0, min(1.0, float(value)))


class SentenceReview(BaseModel):
    id: str = ""
    sentence_text: str = ""
    start_index: int | None = None
    end_index: int | None = None
    status: str = Field(default="okay")
    category: str = Field(default="clarity")
    label: str = ""
    good_point: str | None = None
    comment: str = ""
    suggested_text: str | None = None
    can_apply: bool = False
    context_before: str | None = None
    context_after: str | None = None
    edit_type: str = Field(default="replace_sentence")
    expected_effect: str | None = None
    quality_warning: str | None = None
    confidence: float = Field(default=0.5)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        supported = {"good", "okay", "needs_fix", "risky"}
        if value not in supported:
            return "okay"
        return value

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        supported = {
            "job_fit",
            "specificity",
            "achievement",
            "writing_quality",
            "structure",
            "keyword_match",
            "tone",
            "redundancy",
            "clarity",
        }
        if value not in supported:
            return "clarity"
        return value

    @field_validator("edit_type")
    @classmethod
    def validate_edit_type(cls, value: str) -> str:
        supported = {"replace_sentence", "rewrite_with_context", "merge_with_next", "split_sentence", "add_evidence_after"}
        if value not in supported:
            return "replace_sentence"
        return value

    @field_validator("confidence")
    @classmethod
    def clamp_confidence(cls, value: float) -> float:
        return max(0.0, min(1.0, float(value)))


class AIReviewResponse(BaseModel):
    total_score: float = Field(ge=0, le=100)
    scores: ReviewScores
    summary: str
    problems: list[str]
    improvement_strategy: list[str]
    improved_cover_letter: str
    interview_questions: list[str]
    missing_keywords: list[str]
    strengths: list[str]
    job_keywords: list[str] = Field(default_factory=list)
    rewritten_structure: list[str] = Field(default_factory=list)
    evidence_suggestions: list[str] = Field(default_factory=list)
    ats_keyword_notes: list[str] = Field(default_factory=list)
    final_review_checklist: list[str] = Field(default_factory=list)
    suggestions: list[CoverLetterSuggestion] = Field(default_factory=list)
    sentence_reviews: list[SentenceReview] = Field(default_factory=list)


class ReviewCreateRequest(BaseModel):
    resume_text: str = Field(default="")
    cover_letter_text: str = Field(min_length=20)
    target_job_role: str = Field(default="")
    job_posting_text: str = Field(default="")
    source_file_type: str = Field(default="txt")
    review_mode: str = Field(default="detailed")
    job_category_preset: str | None = None

    @field_validator("source_file_type")
    @classmethod
    def validate_file_type(cls, value: str) -> str:
        supported = {"txt", "pdf", "docx"}
        if value not in supported:
            raise ValueError(f"source_file_type must be one of: {', '.join(sorted(supported))}")
        return value

    @field_validator("review_mode")
    @classmethod
    def validate_review_mode(cls, value: str) -> str:
        normalized = normalize_review_mode(value)
        supported = {"quick", "detailed", "strict", "rewrite-focused"}
        if normalized not in supported:
            raise ValueError(f"review_mode must be one of: {', '.join(sorted(supported))}")
        return normalized

    @field_validator("job_category_preset")
    @classmethod
    def validate_job_category_preset(cls, value: str | None) -> str | None:
        if value is None:
            return value
        supported = {"웹개발자", "사무직", "교육행정", "마케팅", "사회복지사"}
        if value not in supported:
            raise ValueError(f"job_category_preset must be one of: {', '.join(sorted(supported))}")
        return value


class ReviewSummaryResponse(BaseModel):
    id: int
    target_job_role: str
    total_score: float
    summary: str
    review_mode: str
    created_at: datetime


class ReviewRefinementRequest(BaseModel):
    instruction: str = Field(min_length=2)
    current_text: str = Field(min_length=20)
    target_job_role: str = Field(default="")
    job_posting_text: str = Field(default="")


class ReviewRefinementResponse(BaseModel):
    refined_text: str
    change_summary: str
    warnings: list[str]


class ReviewRefinementHistoryEntry(ReviewRefinementResponse):
    id: int
    instruction: str
    current_text: str
    created_at: datetime


class ReviewFinalDocumentRequest(BaseModel):
    final_text: str = Field(min_length=20)
    source: str = Field(default="manual_edit")

    @field_validator("source")
    @classmethod
    def validate_source(cls, value: str) -> str:
        supported = {"ai_improved", "refinement", "manual_edit"}
        if value not in supported:
            raise ValueError(f"source must be one of: {', '.join(sorted(supported))}")
        return value


class ReviewFinalDocumentResponse(BaseModel):
    review_id: int
    final_text: str
    source: str
    updated_at: datetime


class ReviewDetailResponse(BaseModel):
    id: int
    created_at: datetime
    target_job_role: str
    source_file_type: str
    review_mode: str
    job_category_preset: str | None = None
    resume_text: str
    cover_letter_text: str
    job_posting_text: str
    review_result: AIReviewResponse
    refinements: list[ReviewRefinementHistoryEntry] = Field(default_factory=list)
    final_document: ReviewFinalDocumentResponse | None = None
    consent_given: bool = False


class ConsentRequest(BaseModel):
    consent_given: bool


class ConsentResponse(BaseModel):
    review_id: int
    consent_given: bool
    anonymized_sample_created: bool


class ReviewFeedbackRequest(BaseModel):
    rating: str
    reason: str | None = Field(default=None, max_length=500)

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, value: str) -> str:
        supported = {"helpful", "not_helpful"}
        if value not in supported:
            raise ValueError(f"rating must be one of: {', '.join(sorted(supported))}")
        return value


class ReviewFeedbackResponse(BaseModel):
    review_id: int
    rating: str
    reason: str | None = None
    created_at: datetime
