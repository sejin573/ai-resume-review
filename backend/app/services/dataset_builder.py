import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.review import AnonymizedTrainingSample, ImportedDocument, ReviewRequest, TrainingConsent
from app.prompts.review_prompts import SCORING_RUBRIC
from app.schemas.review import AIReviewResponse
from app.services.anonymization_service import AnonymizationService

SYSTEM_TRAINING_PROMPT = "You are an expert Korean resume and cover letter coach."


class DatasetBuilderService:
    def __init__(self) -> None:
        self.anonymizer = AnonymizationService()

    def list_training_samples(self, db: Session) -> list[dict]:
        stmt = (
            select(AnonymizedTrainingSample)
            .options(
                joinedload(AnonymizedTrainingSample.training_consent).joinedload(TrainingConsent.review_request).joinedload(
                    ReviewRequest.review_result
                ),
                joinedload(AnonymizedTrainingSample.imported_document).joinedload(ImportedDocument.data_source),
                joinedload(AnonymizedTrainingSample.data_source),
                joinedload(AnonymizedTrainingSample.reviews),
            )
            .order_by(AnonymizedTrainingSample.created_at.desc())
        )
        samples = db.scalars(stmt).unique().all()
        return [self.build_training_sample_preview(db, sample) for sample in samples]

    def build_training_sample_preview(self, db: Session, sample: AnonymizedTrainingSample) -> dict:
        record = self.ensure_training_record(db, sample)
        errors = self.validate_training_record(record, sample)
        metadata = record.get("metadata", {})
        source_type = (
            metadata.get("source_type")
            or metadata.get("data_source")
            or (sample.data_source.source_type if sample.data_source else None)
            or (sample.imported_document.data_source.source_type if sample.imported_document else None)
        )
        return {
            "sample_id": sample.id,
            "review_request_id": sample.training_consent.review_request_id if sample.training_consent else None,
            "imported_document_id": sample.imported_document_id,
            "data_source_id": sample.data_source_id,
            "source_type": source_type,
            "sample_kind": sample.sample_kind,
            "job_role": metadata.get("job_role", sample.input_payload.get("job_role", "Unknown role")),
            "review_mode": metadata.get("review_mode"),
            "total_score": metadata.get("score", sample.output_payload.get("total_score", 0.0)),
            "created_at": sample.created_at,
            "quality_status": sample.quality_status,
            "reviewed_by_human": sample.reviewed_by_human,
            "contains_real_user_data": sample.contains_real_user_data,
            "pii_risk_score": sample.pii_risk_score,
            "valid_for_export": not errors,
            "validation_errors": errors,
        }

    def export_training_jsonl(self, db: Session) -> tuple[Path, int, int]:
        stmt = (
            select(AnonymizedTrainingSample)
            .options(
                joinedload(AnonymizedTrainingSample.training_consent).joinedload(TrainingConsent.review_request).joinedload(
                    ReviewRequest.review_result
                ),
                joinedload(AnonymizedTrainingSample.imported_document).joinedload(ImportedDocument.data_source),
                joinedload(AnonymizedTrainingSample.data_source),
            )
            .where(
                AnonymizedTrainingSample.reviewed_by_human.is_(True),
                AnonymizedTrainingSample.quality_status == "reviewed",
                AnonymizedTrainingSample.pii_risk_score < self.anonymizer.HIGH_RISK_THRESHOLD,
            )
            .order_by(AnonymizedTrainingSample.created_at.asc())
        )
        samples = db.scalars(stmt).unique().all()
        export_records: list[str] = []
        skipped_count = 0

        for sample in samples:
            record = self.ensure_training_record(db, sample)
            errors = self.validate_training_record(record, sample)
            if errors:
                skipped_count += 1
                continue
            export_records.append(json.dumps(record, ensure_ascii=False))
            if sample.imported_document:
                sample.imported_document.import_status = "exported"
                db.add(sample.imported_document)

        export_dir = Path(__file__).resolve().parents[3] / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        export_path = export_dir / f"curated_training_samples_{timestamp}.jsonl"
        export_path.write_text("\n".join(export_records), encoding="utf-8")
        return export_path, len(export_records), skipped_count

    def ensure_training_record(self, db: Session, sample: AnonymizedTrainingSample) -> dict:
        if sample.training_record_json:
            return sample.training_record_json

        if sample.training_consent:
            review = sample.training_consent.review_request
            record = self._build_user_consent_training_record(review=review, sample=sample)
            sample.training_record_json = record
            sample.sample_kind = "user_review"
            sample.contains_real_user_data = True
            sample.pii_risk_score = self._compute_record_pii_risk(record)
            db.add(sample)
            db.flush()
            return record

        raise ValueError("Training sample is missing a buildable training record")

    def validate_training_record(self, payload: dict, sample: AnonymizedTrainingSample | None = None) -> list[str]:
        errors: list[str] = []
        messages = payload.get("messages")
        metadata = payload.get("metadata")
        if not isinstance(messages, list) or len(messages) != 3:
            errors.append("messages must contain exactly 3 chat messages")
            return errors
        if not isinstance(metadata, dict):
            errors.append("metadata must be an object")

        for message in messages:
            if message.get("role") not in {"system", "user", "assistant"}:
                errors.append("invalid message role")
            content = str(message.get("content", ""))
            remaining = self.anonymizer.detect_remaining_pii(content)
            if remaining:
                errors.append(f"remaining PII detected in {message.get('role')} message")

        assistant_content = str(messages[2].get("content", ""))
        try:
            assistant_payload = json.loads(assistant_content)
            AIReviewResponse.model_validate(assistant_payload)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"assistant content is not valid review JSON: {exc}")

        if sample is not None:
            if sample.pii_risk_score >= self.anonymizer.HIGH_RISK_THRESHOLD:
                errors.append("sample pii_risk_score is above threshold")
            data_source = sample.data_source or (sample.imported_document.data_source if sample.imported_document else None)
            if data_source and data_source.license_status != "approved":
                errors.append("data source license_status is not approved")
            if not sample.reviewed_by_human or sample.quality_status != "reviewed":
                errors.append("sample is not human-reviewed and approved for export")
        return errors

    def _build_user_consent_training_record(self, *, review: ReviewRequest, sample: AnonymizedTrainingSample) -> dict:
        sanitized_input = self.anonymizer.build_anonymized_payload(
            resume_text=sample.input_payload.get("resume_text", review.resume_text),
            cover_letter_text=sample.input_payload.get("cover_letter_text", review.cover_letter_text),
            target_job_role=sample.input_payload.get("target_job_role", review.target_job_role),
            job_posting_text=sample.input_payload.get("job_posting_text", review.job_posting_text),
        )
        assistant_content = json.dumps(sample.output_payload, ensure_ascii=False)
        score = sample.output_payload.get("total_score", self._fallback_score(sample.output_payload.get("scores", {})))
        return {
            "messages": [
                {"role": "system", "content": SYSTEM_TRAINING_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Target role: {sanitized_input['target_job_role']}\n"
                        f"Job posting: {sanitized_input['job_posting_text']}\n"
                        f"Resume: {sanitized_input['resume_text']}\n"
                        f"Cover letter: {sanitized_input['cover_letter_text']}"
                    ),
                },
                {"role": "assistant", "content": assistant_content},
            ],
            "metadata": {
                "job_role": review.target_job_role,
                "review_mode": review.review_mode,
                "score": score,
                "source_type": "user_consent",
                "quality_status": sample.quality_status,
                "reviewed_by_human": sample.reviewed_by_human,
                "contains_real_user_data": True,
            },
        }

    def _compute_record_pii_risk(self, record: dict) -> int:
        return sum(self.anonymizer.pii_risk_score(str(message.get("content", ""))) for message in record.get("messages", []))

    def _fallback_score(self, scores: dict) -> float:
        total = 0.0
        for key, rubric in SCORING_RUBRIC.items():
            total += float(scores.get(key, 0)) * rubric["weight"]
        return round(total, 1)
