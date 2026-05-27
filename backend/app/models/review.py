from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    source_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    license_status: Mapped[str] = mapped_column(String(50), nullable=False, default="unknown")
    license_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    permission_document_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_admin_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_by_admin = relationship("User")
    imported_documents = relationship("ImportedDocument", back_populates="data_source", cascade="all, delete-orphan")
    training_samples = relationship("AnonymizedTrainingSample", back_populates="data_source")


class ImportedDocument(Base):
    __tablename__ = "imported_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    data_source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"), nullable=False, index=True)
    original_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    # NOTE: Production should encrypt this field or store raw imports in secure object storage with strict access controls.
    original_text_encrypted_or_raw_for_review: Mapped[str] = mapped_column(Text, nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    job_role: Mapped[str | None] = mapped_column(Text, nullable=True)
    company_name_masked: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_reference: Mapped[str | None] = mapped_column(Text, nullable=True)
    import_status: Mapped[str] = mapped_column(String(50), nullable=False, default="imported")
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    anonymized_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    pii_risk_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    data_source = relationship("DataSource", back_populates="imported_documents")
    training_sample = relationship(
        "AnonymizedTrainingSample", back_populates="imported_document", uselist=False, cascade="all, delete-orphan"
    )


class ReviewRequest(Base):
    __tablename__ = "review_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    resume_text: Mapped[str] = mapped_column(Text, nullable=False)
    cover_letter_text: Mapped[str] = mapped_column(Text, nullable=False)
    target_job_role: Mapped[str] = mapped_column(Text, nullable=False)
    job_posting_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_file_type: Mapped[str] = mapped_column(Text, default="txt", nullable=False)
    review_mode: Mapped[str] = mapped_column(Text, default="detailed", nullable=False)
    job_category_preset: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="review_requests")
    review_result = relationship("ReviewResult", back_populates="review_request", uselist=False, cascade="all, delete-orphan")
    training_consent = relationship(
        "TrainingConsent", back_populates="review_request", uselist=False, cascade="all, delete-orphan"
    )
    refinements = relationship("ReviewRefinement", back_populates="review_request", cascade="all, delete-orphan")
    final_document = relationship(
        "ReviewFinalDocument", back_populates="review_request", uselist=False, cascade="all, delete-orphan"
    )
    feedback_items = relationship("ReviewFeedback", back_populates="review_request", cascade="all, delete-orphan")


class ReviewResult(Base):
    __tablename__ = "review_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    review_request_id: Mapped[int] = mapped_column(ForeignKey("review_requests.id"), unique=True, nullable=False)
    result_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    provider_name: Mapped[str] = mapped_column(Text, nullable=False, default="mock")
    model_name: Mapped[str] = mapped_column(Text, nullable=False, default="mock-v1")
    prompt_version: Mapped[str] = mapped_column(Text, nullable=False, default="coverfit-review-v1")
    pipeline_version: Mapped[str] = mapped_column(Text, nullable=False, default="coverfit-pipeline-v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    review_request = relationship("ReviewRequest", back_populates="review_result")


class ReviewRefinement(Base):
    __tablename__ = "review_refinements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    review_request_id: Mapped[int] = mapped_column(ForeignKey("review_requests.id"), nullable=False, index=True)
    instruction: Mapped[str] = mapped_column(Text, nullable=False)
    current_text: Mapped[str] = mapped_column(Text, nullable=False)
    refined_text: Mapped[str] = mapped_column(Text, nullable=False)
    change_summary: Mapped[str] = mapped_column(Text, nullable=False)
    warnings_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    review_request = relationship("ReviewRequest", back_populates="refinements")


class ReviewFinalDocument(Base):
    __tablename__ = "review_final_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    review_request_id: Mapped[int] = mapped_column(ForeignKey("review_requests.id"), unique=True, nullable=False, index=True)
    final_text: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="manual_edit")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    review_request = relationship("ReviewRequest", back_populates="final_document")


class ReviewFeedback(Base):
    __tablename__ = "review_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    review_request_id: Mapped[int] = mapped_column(ForeignKey("review_requests.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    rating: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    review_request = relationship("ReviewRequest", back_populates="feedback_items")
    user = relationship("User", back_populates="review_feedback_items")


class TrainingConsent(Base):
    __tablename__ = "training_consents"
    __table_args__ = (UniqueConstraint("review_request_id", name="uq_training_consent_review_request_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    review_request_id: Mapped[int] = mapped_column(ForeignKey("review_requests.id"), nullable=False, index=True)
    consent_given: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="training_consents")
    review_request = relationship("ReviewRequest", back_populates="training_consent")
    training_sample = relationship(
        "AnonymizedTrainingSample", back_populates="training_consent", uselist=False, cascade="all, delete-orphan"
    )


class AnonymizedTrainingSample(Base):
    __tablename__ = "anonymized_training_samples"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    training_consent_id: Mapped[int | None] = mapped_column(
        ForeignKey("training_consents.id"), nullable=True, index=True, unique=True
    )
    imported_document_id: Mapped[int | None] = mapped_column(
        ForeignKey("imported_documents.id"), nullable=True, index=True, unique=True
    )
    data_source_id: Mapped[int | None] = mapped_column(ForeignKey("data_sources.id"), nullable=True, index=True)
    input_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    output_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    training_record_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sample_kind: Mapped[str] = mapped_column(String(50), nullable=False, default="user_review")
    quality_status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    reviewed_by_human: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    contains_real_user_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pii_risk_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    training_consent = relationship("TrainingConsent", back_populates="training_sample")
    imported_document = relationship("ImportedDocument", back_populates="training_sample")
    data_source = relationship("DataSource", back_populates="training_samples")
    reviews = relationship("TrainingSampleReview", back_populates="training_sample", cascade="all, delete-orphan")


class TrainingSampleReview(Base):
    __tablename__ = "training_sample_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    training_sample_id: Mapped[int] = mapped_column(
        ForeignKey("anonymized_training_samples.id"), nullable=False, index=True
    )
    reviewer_admin_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft")
    quality_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    training_sample = relationship("AnonymizedTrainingSample", back_populates="reviews")
    reviewer_admin = relationship("User")


class UsageEvent(Base):
    __tablename__ = "usage_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    review_request_id: Mapped[int | None] = mapped_column(ForeignKey("review_requests.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    user = relationship("User", back_populates="usage_events")
    review_request = relationship("ReviewRequest")
