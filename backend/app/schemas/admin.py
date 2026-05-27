from datetime import datetime

from pydantic import BaseModel, Field


class DataSourceCreateRequest(BaseModel):
    source_name: str
    source_type: str
    license_status: str
    license_note: str | None = None
    source_url: str | None = None
    permission_document_path: str | None = None
    is_active: bool = True


class DataSourceUpdateRequest(BaseModel):
    source_name: str | None = None
    source_type: str | None = None
    license_status: str | None = None
    license_note: str | None = None
    source_url: str | None = None
    permission_document_path: str | None = None
    is_active: bool | None = None


class DataSourceResponse(BaseModel):
    id: int
    source_name: str
    source_type: str
    license_status: str
    license_note: str | None = None
    source_url: str | None = None
    permission_document_path: str | None = None
    created_by_admin_id: int | None = None
    created_at: datetime
    updated_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class ImportedDocumentResponse(BaseModel):
    id: int
    data_source_id: int
    original_title: str | None = None
    document_type: str
    job_role: str | None = None
    company_name_masked: str | None = None
    source_reference: str | None = None
    import_status: str
    rejection_reason: str | None = None
    pii_risk_score: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ImportedDocumentDetailResponse(ImportedDocumentResponse):
    anonymized_text: str | None = None
    original_text_encrypted_or_raw_for_review: str


class RejectImportedDocumentRequest(BaseModel):
    rejection_reason: str = Field(min_length=3)


class ApprovedUrlImportRequest(BaseModel):
    data_source_id: int
    urls: list[str]


class CreateTrainingSampleResponse(BaseModel):
    training_sample_id: int
    quality_status: str
    pii_risk_score: int


class ReviewTrainingSampleRequest(BaseModel):
    status: str
    quality_score: int | None = Field(default=None, ge=0, le=100)
    notes: str | None = None


class TrainingSamplePreview(BaseModel):
    sample_id: int
    review_request_id: int | None = None
    imported_document_id: int | None = None
    data_source_id: int | None = None
    source_type: str | None = None
    sample_kind: str
    job_role: str
    review_mode: str | None = None
    total_score: float
    created_at: datetime
    quality_status: str
    reviewed_by_human: bool
    contains_real_user_data: bool
    pii_risk_score: int
    valid_for_export: bool
    validation_errors: list[str]


class TrainingSampleDataSourceInfo(BaseModel):
    id: int
    source_name: str
    source_type: str
    license_status: str
    license_note: str | None = None
    source_url: str | None = None
    is_active: bool

    class Config:
        from_attributes = True


class TrainingSampleReviewEntry(BaseModel):
    id: int
    reviewer_admin_id: int
    status: str
    quality_score: int | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TrainingSampleDetailResponse(TrainingSamplePreview):
    input_payload: dict
    output_payload: dict
    training_record_json: dict | None = None
    data_source: TrainingSampleDataSourceInfo | None = None
    reviews: list[TrainingSampleReviewEntry]


class TrainingSamplesResponse(BaseModel):
    total_samples: int
    exportable_samples: int
    samples: list[TrainingSamplePreview]


class TrainingExportResponse(BaseModel):
    exported_count: int
    skipped_count: int
    file_path: str
