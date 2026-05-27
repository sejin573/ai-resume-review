from io import BytesIO
import re
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.review import (
    AnonymizedTrainingSample,
    ReviewFeedback,
    ReviewFinalDocument,
    ReviewRefinement,
    ReviewRequest,
    ReviewResult,
    TrainingConsent,
)
from app.models.user import User
from app.schemas.review import (
    AIReviewResponse,
    ConsentRequest,
    ConsentResponse,
    ReviewCreateRequest,
    ReviewDetailResponse,
    ReviewFeedbackRequest,
    ReviewFeedbackResponse,
    ReviewFinalDocumentRequest,
    ReviewFinalDocumentResponse,
    ReviewRefinementHistoryEntry,
    ReviewRefinementRequest,
    ReviewRefinementResponse,
    ReviewSummaryResponse,
)
from app.services.ai_client import AIReviewService
from app.services.anonymizer import build_anonymized_payload
from app.services.pdf_exporter import build_review_pdf
from app.services.usage_service import PDF_EXPORT, REFINEMENT_CREATE, REVIEW_CREATE, assert_usage_available, record_usage_event

router = APIRouter()
ai_service = AIReviewService()


def _count_sentences(text: str) -> int:
    return len([item.strip() for item in re.findall(r"[^.!?\n。！？]+(?:[.!?。！？]+|$)", text or "") if item.strip()])


def _build_review_result_response(result_json: dict, cover_letter_text: str) -> AIReviewResponse:
    result = AIReviewResponse.model_validate(result_json)
    target_min = min(6, _count_sentences(cover_letter_text))
    if len(result.sentence_reviews) < target_min or not result.suggestions:
        return ai_service._attach_processed_review_details(result, cover_letter_text)
    return result


def _build_final_document_response(final_document: ReviewFinalDocument | None, review_id: int) -> ReviewFinalDocumentResponse | None:
    if final_document is None:
        return None
    return ReviewFinalDocumentResponse(
        review_id=review_id,
        final_text=final_document.final_text,
        source=final_document.source,
        updated_at=final_document.updated_at,
    )


@router.post("", response_model=ReviewDetailResponse, status_code=status.HTTP_201_CREATED)
def create_review(
    payload: ReviewCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReviewDetailResponse:
    assert_usage_available(db, current_user, REVIEW_CREATE)
    review_request = ReviewRequest(
        user_id=current_user.id,
        resume_text=payload.resume_text,
        cover_letter_text=payload.cover_letter_text,
        target_job_role=payload.target_job_role,
        job_posting_text=payload.job_posting_text,
        source_file_type=payload.source_file_type,
        review_mode=payload.review_mode,
        job_category_preset=payload.job_category_preset,
    )
    db.add(review_request)
    db.flush()

    review_result, provider_name, model_name = ai_service.review(
        resume_text=payload.resume_text,
        cover_letter_text=payload.cover_letter_text,
        target_job_role=payload.target_job_role,
        job_posting_text=payload.job_posting_text,
        review_mode=payload.review_mode,
        job_category_preset=payload.job_category_preset,
    )

    result = ReviewResult(
        review_request_id=review_request.id,
        result_json=review_result.model_dump(),
        provider_name=provider_name,
        model_name=model_name,
        prompt_version=ai_service.last_review_metadata["prompt_version"],
        pipeline_version=ai_service.last_review_metadata["pipeline_version"],
    )
    db.add(result)
    record_usage_event(db, user=current_user, event_type=REVIEW_CREATE, review_request_id=review_request.id)
    db.commit()
    db.refresh(review_request)
    db.refresh(result)

    return ReviewDetailResponse(
        id=review_request.id,
        created_at=review_request.created_at,
        target_job_role=review_request.target_job_role,
        source_file_type=review_request.source_file_type,
        review_mode=review_request.review_mode,
        job_category_preset=review_request.job_category_preset,
        resume_text=review_request.resume_text,
        cover_letter_text=review_request.cover_letter_text,
        job_posting_text=review_request.job_posting_text,
        review_result=_build_review_result_response(result.result_json, review_request.cover_letter_text),
        refinements=[],
        final_document=None,
        consent_given=False,
    )


@router.get("", response_model=list[ReviewSummaryResponse])
def list_reviews(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ReviewSummaryResponse]:
    stmt = (
        select(ReviewRequest)
        .where(ReviewRequest.user_id == current_user.id)
        .options(joinedload(ReviewRequest.review_result))
        .order_by(ReviewRequest.created_at.desc())
    )
    reviews = db.scalars(stmt).unique().all()
    return [
        ReviewSummaryResponse(
            id=review.id,
            target_job_role=review.target_job_role,
            total_score=review.review_result.result_json["total_score"],
            summary=review.review_result.result_json["summary"],
            review_mode=review.review_mode,
            created_at=review.created_at,
        )
        for review in reviews
        if review.review_result
    ]


@router.get("/{review_id}", response_model=ReviewDetailResponse)
def get_review(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReviewDetailResponse:
    stmt = (
        select(ReviewRequest)
        .where(ReviewRequest.id == review_id, ReviewRequest.user_id == current_user.id)
        .options(
            joinedload(ReviewRequest.review_result),
            joinedload(ReviewRequest.training_consent),
            joinedload(ReviewRequest.refinements),
            joinedload(ReviewRequest.final_document),
        )
    )
    review = db.scalar(stmt)
    if not review or not review.review_result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    return ReviewDetailResponse(
        id=review.id,
        created_at=review.created_at,
        target_job_role=review.target_job_role,
        source_file_type=review.source_file_type,
        review_mode=review.review_mode,
        job_category_preset=review.job_category_preset,
        resume_text=review.resume_text,
        cover_letter_text=review.cover_letter_text,
        job_posting_text=review.job_posting_text,
        review_result=_build_review_result_response(review.review_result.result_json, review.cover_letter_text),
        refinements=[
            ReviewRefinementHistoryEntry(
                id=refinement.id,
                instruction=refinement.instruction,
                current_text=refinement.current_text,
                refined_text=refinement.refined_text,
                change_summary=refinement.change_summary,
                warnings=refinement.warnings_json,
                created_at=refinement.created_at,
            )
            for refinement in sorted(review.refinements, key=lambda item: item.created_at)
        ],
        final_document=_build_final_document_response(review.final_document, review.id),
        consent_given=bool(review.training_consent and review.training_consent.consent_given),
    )


@router.get("/{review_id}/final-document", response_model=ReviewFinalDocumentResponse)
def get_final_document(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReviewFinalDocumentResponse:
    stmt = (
        select(ReviewRequest)
        .where(ReviewRequest.id == review_id, ReviewRequest.user_id == current_user.id)
        .options(joinedload(ReviewRequest.final_document))
    )
    review = db.scalar(stmt)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    if not review.final_document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Final document not found")
    return _build_final_document_response(review.final_document, review.id)


@router.put("/{review_id}/final-document", response_model=ReviewFinalDocumentResponse)
def upsert_final_document(
    review_id: int,
    payload: ReviewFinalDocumentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReviewFinalDocumentResponse:
    stmt = (
        select(ReviewRequest)
        .where(ReviewRequest.id == review_id, ReviewRequest.user_id == current_user.id)
        .options(joinedload(ReviewRequest.final_document))
    )
    review = db.scalar(stmt)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    final_document = review.final_document
    if final_document is None:
        final_document = ReviewFinalDocument(
            review_request_id=review.id,
            final_text=payload.final_text,
            source=payload.source,
        )
        db.add(final_document)
    else:
        final_document.final_text = payload.final_text
        final_document.source = payload.source
        db.add(final_document)

    db.commit()
    db.refresh(final_document)
    return _build_final_document_response(final_document, review.id)


@router.get("/{review_id}/export/pdf")
def export_final_document_pdf(
    review_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> StreamingResponse:
    stmt = (
        select(ReviewRequest)
        .where(ReviewRequest.id == review_id, ReviewRequest.user_id == current_user.id)
        .options(joinedload(ReviewRequest.review_result), joinedload(ReviewRequest.final_document))
    )
    review = db.scalar(stmt)
    if not review or not review.review_result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    assert_usage_available(db, current_user, PDF_EXPORT)
    result = _build_review_result_response(review.review_result.result_json, review.cover_letter_text)
    final_text = review.final_document.final_text if review.final_document else result.improved_cover_letter
    pdf_bytes = build_review_pdf(
        job_role=review.target_job_role,
        review_created_at=review.created_at,
        review_mode=review.review_mode,
        final_text=final_text,
        ai_summary=result.summary,
        scores=result.scores.model_dump(),
        strengths=result.strengths,
        problems=result.problems,
        interview_questions=result.interview_questions,
    )
    safe_job = quote(review.target_job_role.replace(" ", "_"))
    filename = f"coverfit_final_{safe_job}_{review.created_at.strftime('%Y%m%d')}.pdf"
    record_usage_event(db, user=current_user, event_type=PDF_EXPORT, review_request_id=review.id)
    db.commit()
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@router.post("/{review_id}/refine", response_model=ReviewRefinementResponse)
def refine_review_text(
    review_id: int,
    payload: ReviewRefinementRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReviewRefinementResponse:
    stmt = select(ReviewRequest).where(ReviewRequest.id == review_id, ReviewRequest.user_id == current_user.id)
    review = db.scalar(stmt)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    assert_usage_available(db, current_user, REFINEMENT_CREATE)
    refinement_result, _provider_name, _model_name = ai_service.refine_cover_letter(
        instruction=payload.instruction,
        current_text=payload.current_text,
        target_job_role=payload.target_job_role,
        job_posting_text=payload.job_posting_text,
    )
    refinement = ReviewRefinement(
        review_request_id=review.id,
        instruction=payload.instruction,
        current_text=payload.current_text,
        refined_text=refinement_result.refined_text,
        change_summary=refinement_result.change_summary,
        warnings_json=refinement_result.warnings,
    )
    db.add(refinement)
    record_usage_event(db, user=current_user, event_type=REFINEMENT_CREATE, review_request_id=review.id)
    db.commit()
    return refinement_result


@router.post("/{review_id}/consent-training", response_model=ConsentResponse)
def consent_training(
    review_id: int,
    payload: ConsentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ConsentResponse:
    stmt = (
        select(ReviewRequest)
        .where(ReviewRequest.id == review_id, ReviewRequest.user_id == current_user.id)
        .options(joinedload(ReviewRequest.review_result), joinedload(ReviewRequest.training_consent))
    )
    review = db.scalar(stmt)
    if not review or not review.review_result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    consent = review.training_consent
    if consent:
        consent.consent_given = payload.consent_given
    else:
        consent = TrainingConsent(
            user_id=current_user.id,
            review_request_id=review.id,
            consent_given=payload.consent_given,
        )
        db.add(consent)
        db.flush()

    anonymized_created = False
    if payload.consent_given:
        if not consent.training_sample:
            sample = AnonymizedTrainingSample(
                training_consent_id=consent.id,
                input_payload=build_anonymized_payload(
                    resume_text=review.resume_text,
                    cover_letter_text=review.cover_letter_text,
                    target_job_role=review.target_job_role,
                    job_posting_text=review.job_posting_text,
                ),
                output_payload=review.review_result.result_json,
            )
            db.add(sample)
            anonymized_created = True
    else:
        if consent.training_sample:
            db.delete(consent.training_sample)

    db.commit()
    return ConsentResponse(
        review_id=review.id,
        consent_given=payload.consent_given,
        anonymized_sample_created=anonymized_created,
    )


@router.post("/{review_id}/feedback", response_model=ReviewFeedbackResponse, status_code=status.HTTP_201_CREATED)
def submit_review_feedback(
    review_id: int,
    payload: ReviewFeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReviewFeedbackResponse:
    review = db.scalar(select(ReviewRequest).where(ReviewRequest.id == review_id, ReviewRequest.user_id == current_user.id))
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    feedback = db.scalar(
        select(ReviewFeedback).where(
            ReviewFeedback.review_request_id == review.id,
            ReviewFeedback.user_id == current_user.id,
        )
    )
    if feedback is None:
        feedback = ReviewFeedback(
            review_request_id=review.id,
            user_id=current_user.id,
            rating=payload.rating,
            reason=payload.reason,
        )
        db.add(feedback)
    else:
        feedback.rating = payload.rating
        feedback.reason = payload.reason
        db.add(feedback)

    db.commit()
    db.refresh(feedback)
    return ReviewFeedbackResponse(
        review_id=review.id,
        rating=feedback.rating,
        reason=feedback.reason,
        created_at=feedback.created_at,
    )
