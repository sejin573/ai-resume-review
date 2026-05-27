import json
from collections.abc import Iterable
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.review import AnonymizedTrainingSample, DataSource, TrainingSampleReview
from app.models.user import User
from app.schemas.review import AIReviewResponse
from app.services.anonymization_service import AnonymizationService


class SeedIngestionService:
    SOURCE_NAME = "Fictional Manual Seed Dataset"
    LICENSE_NOTE = "Fully fictional dataset generated internally. No real personal data. No external scraping."
    BULK_REVIEW_NOTE = (
        "Bulk reviewed for local pipeline testing. Must not be used for production evaluation without human review."
    )

    def __init__(self) -> None:
        self.anonymizer = AnonymizationService()

    def get_or_create_manual_seed_source(
        self,
        db: Session,
        *,
        created_by_admin_id: int | None = None,
    ) -> DataSource:
        stmt = select(DataSource).where(
            DataSource.source_name == self.SOURCE_NAME,
            DataSource.source_type == "manual_seed",
        )
        source = db.scalar(stmt)
        if source is None:
            source = DataSource(
                source_name=self.SOURCE_NAME,
                source_type="manual_seed",
                license_status="approved",
                license_note=self.LICENSE_NOTE,
                is_active=True,
                created_by_admin_id=created_by_admin_id,
            )
            db.add(source)
            db.flush()
            return source

        source.license_status = "approved"
        source.license_note = self.LICENSE_NOTE
        source.is_active = True
        if created_by_admin_id is not None and source.created_by_admin_id is None:
            source.created_by_admin_id = created_by_admin_id
        db.add(source)
        db.flush()
        return source

    def import_seed_jsonl(
        self,
        db: Session,
        *,
        jsonl_path: Path,
        created_by_admin_id: int | None = None,
    ) -> dict:
        source = self.get_or_create_manual_seed_source(db, created_by_admin_id=created_by_admin_id)
        existing_cover_letters = self._load_existing_cover_letters(db, source.id)
        imported = 0
        skipped_duplicates = 0
        rejected = 0
        seen_in_file: set[str] = set()

        for line_number, raw_line in enumerate(jsonl_path.read_text(encoding="utf-8").splitlines(), start=1):
            if not raw_line.strip():
                continue
            payload = self._load_json_line(raw_line, line_number)
            normalized = self._normalize_seed_sample(payload, line_number)
            cover_letter = normalized["original_cover_letter"]
            if cover_letter in seen_in_file or cover_letter in existing_cover_letters:
                skipped_duplicates += 1
                continue
            self._validate_seed_sample(normalized, line_number)

            training_sample = AnonymizedTrainingSample(
                data_source_id=source.id,
                input_payload={
                    "job_role": normalized["job_role"],
                    "resume_summary": normalized["resume_summary"],
                    "fictional_job_posting_summary": normalized["fictional_job_posting_summary"],
                    "original_cover_letter": normalized["original_cover_letter"],
                    "data_source": "manual_seed",
                },
                output_payload=normalized["review_result"],
                training_record_json=normalized["training_record"],
                sample_kind="manual_seed",
                quality_status="draft",
                reviewed_by_human=False,
                contains_real_user_data=False,
                pii_risk_score=self._record_pii_risk(normalized["training_record"]),
            )
            if training_sample.pii_risk_score >= self.anonymizer.HIGH_RISK_THRESHOLD:
                rejected += 1
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Seed sample line {line_number} exceeds allowed pii_risk_score",
                )

            db.add(training_sample)
            seen_in_file.add(cover_letter)
            existing_cover_letters.add(cover_letter)
            imported += 1

        db.commit()
        return {
            "data_source_id": source.id,
            "imported_count": imported,
            "skipped_duplicates": skipped_duplicates,
            "rejected_count": rejected,
        }

    def bulk_mark_manual_seed_reviewed(
        self,
        db: Session,
        *,
        reviewer_admin_id: int,
        quality_score: int = 85,
        notes: str | None = None,
    ) -> int:
        source = self.get_or_create_manual_seed_source(db, created_by_admin_id=reviewer_admin_id)
        stmt = select(AnonymizedTrainingSample).where(AnonymizedTrainingSample.data_source_id == source.id)
        samples = db.scalars(stmt).all()
        note_text = notes or self.BULK_REVIEW_NOTE
        updated = 0

        for sample in samples:
            sample.quality_status = "reviewed"
            sample.reviewed_by_human = True
            db.add(sample)
            db.add(
                TrainingSampleReview(
                    training_sample_id=sample.id,
                    reviewer_admin_id=reviewer_admin_id,
                    status="reviewed",
                    quality_score=quality_score,
                    notes=note_text,
                )
            )
            updated += 1

        db.commit()
        return updated

    def ensure_local_admin_user(self, db: Session, admin_email: str) -> User:
        stmt = select(User).where(User.email == admin_email)
        user = db.scalar(stmt)
        if user is None:
            from app.core.security import hash_password

            user = User(
                email=admin_email,
                full_name="Local Seed Reviewer",
                password_hash=hash_password("local-seed-reviewer"),
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    def _load_existing_cover_letters(self, db: Session, source_id: int) -> set[str]:
        stmt = select(AnonymizedTrainingSample).where(AnonymizedTrainingSample.data_source_id == source_id)
        samples = db.scalars(stmt).all()
        existing: set[str] = set()
        for sample in samples:
            text = str(sample.input_payload.get("original_cover_letter") or sample.input_payload.get("accepted_cover_letter") or "")
            if text:
                existing.add(text)
        return existing

    def _load_json_line(self, raw_line: str, line_number: int) -> dict:
        try:
            payload = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid JSONL at line {line_number}: {exc}",
            ) from exc
        if not isinstance(payload, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Seed sample line {line_number} must be a JSON object",
            )
        return payload

    def _normalize_seed_sample(self, payload: dict, line_number: int) -> dict:
        required = {
            "job_role",
            "fictional_job_posting_summary",
            "resume_summary",
            "original_cover_letter",
            "review_result",
            "training_record",
        }
        missing = sorted(field for field in required if not payload.get(field))
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Seed sample line {line_number} is missing required fields: {', '.join(missing)}",
            )

        review_result = AIReviewResponse.model_validate(payload["review_result"]).model_dump()
        training_record = payload["training_record"]
        messages = training_record.get("messages")
        if not isinstance(messages, list) or len(messages) != 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Seed sample line {line_number} must contain 3 chat messages",
            )

        assistant_content = messages[2].get("content", "")
        try:
            assistant_payload = AIReviewResponse.model_validate(json.loads(assistant_content)).model_dump()
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Seed sample line {line_number} has invalid assistant JSON: {exc}",
            ) from exc

        if assistant_payload != review_result:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Seed sample line {line_number} review_result does not match assistant JSON",
            )

        metadata = dict(training_record.get("metadata") or {})
        metadata.update(
            {
                "job_role": payload["job_role"],
                "source_type": "manual_seed",
                "data_source": "manual_seed",
                "score": review_result["total_score"],
                "quality_status": "draft",
                "reviewed_by_human": False,
                "contains_real_user_data": False,
            }
        )
        normalized_record = {
            "messages": messages,
            "metadata": metadata,
        }
        return {
            "job_role": str(payload["job_role"]),
            "fictional_job_posting_summary": str(payload["fictional_job_posting_summary"]),
            "resume_summary": str(payload["resume_summary"]),
            "original_cover_letter": str(payload["original_cover_letter"]),
            "review_result": review_result,
            "training_record": normalized_record,
        }

    def _validate_seed_sample(self, payload: dict, line_number: int) -> None:
        combined_text = "\n".join(
            [
                payload["job_role"],
                payload["fictional_job_posting_summary"],
                payload["resume_summary"],
                payload["original_cover_letter"],
                *self._message_contents(payload["training_record"].get("messages", [])),
            ]
        )
        remaining = self.anonymizer.detect_remaining_pii(combined_text)
        if remaining:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Seed sample line {line_number} contains PII placeholders to fix: {', '.join(remaining)}",
            )
        risk_score = self.anonymizer.pii_risk_score(combined_text)
        if risk_score >= self.anonymizer.HIGH_RISK_THRESHOLD:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Seed sample line {line_number} exceeds allowed PII risk score",
            )

    def _message_contents(self, messages: Iterable[dict]) -> list[str]:
        return [str(message.get("content", "")) for message in messages]

    def _record_pii_risk(self, training_record: dict) -> int:
        return sum(self.anonymizer.pii_risk_score(content) for content in self._message_contents(training_record["messages"]))
