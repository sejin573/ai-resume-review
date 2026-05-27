import csv
import io
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from urllib import robotparser

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.review import AnonymizedTrainingSample, DataSource, ImportedDocument, TrainingSampleReview
from app.services.anonymization_service import AnonymizationService
from app.services.training_transform_service import TrainingTransformService


class _PlainTextHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        cleaned = data.strip()
        if cleaned:
            self.chunks.append(cleaned)

    def text(self) -> str:
        return "\n".join(self.chunks)


class IngestionService:
    ALLOWED_SOURCE_TYPES = {"user_consent", "admin_upload", "partner_dataset", "public_dataset", "manual_seed", "approved_url_list"}
    ALLOWED_LICENSE_STATUSES = {"unknown", "approved", "rejected", "needs_review"}
    ALLOWED_DOCUMENT_TYPES = {
        "accepted_cover_letter",
        "resume",
        "job_posting",
        "review_feedback",
        "interview_answer",
    }
    ALLOWED_IMPORT_STATUSES = {"imported", "anonymized", "rejected", "curated", "exported"}
    ALLOWED_REVIEW_STATUSES = {"draft", "reviewed", "rejected"}

    def __init__(self) -> None:
        self.anonymizer = AnonymizationService()
        self.transformer = TrainingTransformService()

    def validate_data_source_for_ingestion(self, data_source: DataSource) -> None:
        if data_source.license_status != "approved":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Ingestion blocked until license_status is approved")
        if not data_source.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive data source cannot ingest")
        if data_source.source_type == "approved_url_list":
            if not data_source.source_url or not data_source.license_note:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="approved_url_list requires source_url and license_note",
                )

    def create_data_source(self, db: Session, admin_id: int, payload: dict) -> DataSource:
        self._validate_data_source_payload(payload)
        data_source = DataSource(created_by_admin_id=admin_id, **payload)
        db.add(data_source)
        db.commit()
        db.refresh(data_source)
        return data_source

    def update_data_source(self, db: Session, data_source: DataSource, payload: dict) -> DataSource:
        merged = {
            "source_name": data_source.source_name,
            "source_type": data_source.source_type,
            "license_status": data_source.license_status,
            "license_note": data_source.license_note,
            "source_url": data_source.source_url,
            "permission_document_path": data_source.permission_document_path,
            "is_active": data_source.is_active,
        }
        merged.update(payload)
        self._validate_data_source_payload(merged)
        for key, value in payload.items():
            setattr(data_source, key, value)
        db.add(data_source)
        db.commit()
        db.refresh(data_source)
        return data_source

    def import_csv(self, db: Session, data_source: DataSource, upload: UploadFile) -> list[ImportedDocument]:
        self.validate_data_source_for_ingestion(data_source)
        decoded = upload.file.read().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(decoded))
        documents = []
        for row in reader:
            documents.append(
                self._create_imported_document(
                    db,
                    data_source,
                    {
                        "document_type": row.get("document_type", ""),
                        "job_role": row.get("job_role"),
                        "original_title": row.get("original_title"),
                        "original_text": row.get("original_text", ""),
                        "source_reference": row.get("source_reference"),
                        "license_note": row.get("license_note"),
                    },
                )
            )
        db.commit()
        return documents

    def import_jsonl(self, db: Session, data_source: DataSource, upload: UploadFile) -> list[ImportedDocument]:
        self.validate_data_source_for_ingestion(data_source)
        decoded = upload.file.read().decode("utf-8-sig")
        documents = []
        for line in decoded.splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            documents.append(self._create_imported_document(db, data_source, row))
        db.commit()
        return documents

    def import_approved_urls(self, db: Session, data_source: DataSource, urls: list[str]) -> list[ImportedDocument]:
        self.validate_data_source_for_ingestion(data_source)
        if data_source.source_type != "approved_url_list":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Data source must be approved_url_list")
        documents = []
        for url in urls:
            if not self._robots_allowed(url):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"robots.txt blocks fetch: {url}")
            html = self._fetch_url_text(url)
            documents.append(
                self._create_imported_document(
                    db,
                    data_source,
                    {
                        "document_type": "accepted_cover_letter",
                        "job_role": None,
                        "original_title": url,
                        "original_text": html,
                        "source_reference": url,
                    },
                )
            )
            time.sleep(1.0)
        db.commit()
        return documents

    def list_imported_documents(self, db: Session) -> list[ImportedDocument]:
        stmt = select(ImportedDocument).options(joinedload(ImportedDocument.data_source)).order_by(ImportedDocument.created_at.desc())
        return db.scalars(stmt).unique().all()

    def anonymize_imported_document(self, db: Session, document: ImportedDocument) -> ImportedDocument:
        sanitized = self.anonymizer.anonymize_text(document.original_text_encrypted_or_raw_for_review)
        risk_score = self.anonymizer.pii_risk_score(sanitized)
        document.anonymized_text = sanitized
        document.pii_risk_score = risk_score
        if self.anonymizer.should_reject(sanitized):
            document.import_status = "rejected"
            document.rejection_reason = "High-risk PII remains after anonymization"
        else:
            document.import_status = "anonymized"
            document.rejection_reason = None
        db.add(document)
        db.commit()
        db.refresh(document)
        return document

    def reject_imported_document(self, db: Session, document: ImportedDocument, reason: str) -> ImportedDocument:
        document.import_status = "rejected"
        document.rejection_reason = reason
        db.add(document)
        db.commit()
        db.refresh(document)
        return document

    def create_training_sample_from_document(self, db: Session, document: ImportedDocument) -> AnonymizedTrainingSample:
        data_source = document.data_source
        self.validate_data_source_for_ingestion(data_source)
        if document.document_type != "accepted_cover_letter":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only accepted_cover_letter documents can be transformed into training samples",
            )
        if not document.anonymized_text:
            self.anonymize_imported_document(db, document)
            db.refresh(document)
        if document.import_status == "rejected":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rejected documents cannot create training samples")

        training_record = self.transformer.transform_accepted_cover_letter(
            data_source_id=data_source.id,
            source_type=data_source.source_type,
            job_role=document.job_role or "미지정 직무",
            accepted_cover_letter=document.anonymized_text or "",
            job_keywords=[],
            resume_summary=None,
            contains_real_user_data=data_source.source_type in {"user_consent", "admin_upload", "partner_dataset"},
        )
        sample = document.training_sample
        if sample is None:
            sample = AnonymizedTrainingSample(
                imported_document_id=document.id,
                data_source_id=data_source.id,
                input_payload={"accepted_cover_letter": document.anonymized_text or ""},
                output_payload=json.loads(training_record["messages"][2]["content"]),
                training_record_json=training_record,
                sample_kind="accepted_cover_letter",
                quality_status="draft",
                reviewed_by_human=False,
                contains_real_user_data=training_record["metadata"]["contains_real_user_data"],
                pii_risk_score=document.pii_risk_score,
            )
            db.add(sample)
        else:
            sample.input_payload = {"accepted_cover_letter": document.anonymized_text or ""}
            sample.output_payload = json.loads(training_record["messages"][2]["content"])
            sample.training_record_json = training_record
            sample.sample_kind = "accepted_cover_letter"
            sample.quality_status = "draft"
            sample.reviewed_by_human = False
            sample.contains_real_user_data = training_record["metadata"]["contains_real_user_data"]
            sample.pii_risk_score = document.pii_risk_score
            db.add(sample)

        document.import_status = "curated"
        db.add(document)
        db.commit()
        db.refresh(sample)
        return sample

    def review_training_sample(
        self, db: Session, sample: AnonymizedTrainingSample, reviewer_admin_id: int, status_value: str, quality_score: int | None, notes: str | None
    ) -> TrainingSampleReview:
        if status_value not in self.ALLOWED_REVIEW_STATUSES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid review status")
        if status_value == "reviewed" and quality_score is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="quality_score is required when marking reviewed")
        if status_value == "rejected" and not (notes or "").strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="notes are required when rejecting a sample")
        review = TrainingSampleReview(
            training_sample_id=sample.id,
            reviewer_admin_id=reviewer_admin_id,
            status=status_value,
            quality_score=quality_score,
            notes=notes,
        )
        sample.reviewed_by_human = status_value in {"reviewed", "rejected"}
        sample.quality_status = status_value
        db.add(review)
        db.add(sample)
        db.commit()
        db.refresh(review)
        return review

    def _create_imported_document(self, db: Session, data_source: DataSource, row: dict) -> ImportedDocument:
        document_type = row.get("document_type")
        if document_type not in self.ALLOWED_DOCUMENT_TYPES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid document_type: {document_type}")
        document = ImportedDocument(
            data_source_id=data_source.id,
            original_title=row.get("original_title"),
            original_text_encrypted_or_raw_for_review=row.get("original_text", ""),
            document_type=document_type,
            job_role=row.get("job_role"),
            source_reference=row.get("source_reference"),
            import_status="imported",
        )
        db.add(document)
        db.flush()
        return document

    def _validate_data_source_payload(self, payload: dict) -> None:
        if payload.get("source_type") not in self.ALLOWED_SOURCE_TYPES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid source_type")
        if payload.get("license_status") not in self.ALLOWED_LICENSE_STATUSES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid license_status")
        if payload.get("source_type") == "approved_url_list":
            if not payload.get("source_url") or not payload.get("license_note"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="approved_url_list requires source_url and license_note",
                )

    def _robots_allowed(self, url: str) -> bool:
        parsed = urllib.parse.urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = robotparser.RobotFileParser()
        try:
            rp.set_url(robots_url)
            rp.read()
            return rp.can_fetch("Mozilla/5.0 (compatible; SafeImporter/1.0)", url)
        except Exception:
            return False

    def _fetch_url_text(self, url: str) -> str:
        # WARNING: URL import must only be used for explicitly approved sources with documented permission.
        # This importer does not bypass login, paywalls, captcha, rate limits, or anti-bot controls.
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; SafeImporter/1.0)"})
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                content_type = response.headers.get("Content-Type", "")
                if "text/html" not in content_type and "text/plain" not in content_type:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported content type for {url}")
                body = response.read().decode("utf-8", errors="ignore")
        except urllib.error.URLError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to fetch URL: {exc}") from exc
        parser = _PlainTextHTMLParser()
        parser.feed(body)
        return parser.text()
