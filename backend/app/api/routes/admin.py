from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_admin_user
from app.db.session import get_db
from app.models.review import AnonymizedTrainingSample, DataSource, ImportedDocument
from app.models.user import User
from app.schemas.admin import (
    ApprovedUrlImportRequest,
    CreateTrainingSampleResponse,
    DataSourceCreateRequest,
    DataSourceResponse,
    DataSourceUpdateRequest,
    ImportedDocumentDetailResponse,
    ImportedDocumentResponse,
    RejectImportedDocumentRequest,
    ReviewTrainingSampleRequest,
    TrainingSampleDataSourceInfo,
    TrainingSampleDetailResponse,
    TrainingSampleReviewEntry,
    TrainingExportResponse,
    TrainingSamplePreview,
    TrainingSamplesResponse,
)
from app.services.dataset_builder import DatasetBuilderService
from app.services.ingestion_service import IngestionService

router = APIRouter()
dataset_builder = DatasetBuilderService()
ingestion_service = IngestionService()


@router.post("/data-sources", response_model=DataSourceResponse, status_code=status.HTTP_201_CREATED)
def create_data_source(
    payload: DataSourceCreateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
) -> DataSourceResponse:
    source = ingestion_service.create_data_source(db, admin.id, payload.model_dump())
    return DataSourceResponse.model_validate(source)


@router.get("/data-sources", response_model=list[DataSourceResponse])
def list_data_sources(
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
) -> list[DataSourceResponse]:
    sources = db.scalars(select(DataSource).order_by(DataSource.created_at.desc())).all()
    return [DataSourceResponse.model_validate(source) for source in sources]


@router.patch("/data-sources/{source_id}", response_model=DataSourceResponse)
def update_data_source(
    source_id: int,
    payload: DataSourceUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
) -> DataSourceResponse:
    source = db.get(DataSource, source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found")
    updated = ingestion_service.update_data_source(db, source, payload.model_dump(exclude_none=True))
    return DataSourceResponse.model_validate(updated)


@router.post("/import/csv", response_model=list[ImportedDocumentResponse], status_code=status.HTTP_201_CREATED)
def import_csv(
    data_source_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
) -> list[ImportedDocumentResponse]:
    source = db.get(DataSource, data_source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found")
    documents = ingestion_service.import_csv(db, source, file)
    return [ImportedDocumentResponse.model_validate(document) for document in documents]


@router.post("/import/jsonl", response_model=list[ImportedDocumentResponse], status_code=status.HTTP_201_CREATED)
def import_jsonl(
    data_source_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
) -> list[ImportedDocumentResponse]:
    source = db.get(DataSource, data_source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found")
    documents = ingestion_service.import_jsonl(db, source, file)
    return [ImportedDocumentResponse.model_validate(document) for document in documents]


@router.post("/import/approved-urls", response_model=list[ImportedDocumentResponse], status_code=status.HTTP_201_CREATED)
def import_approved_urls(
    payload: ApprovedUrlImportRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
) -> list[ImportedDocumentResponse]:
    source = db.get(DataSource, payload.data_source_id)
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Data source not found")
    documents = ingestion_service.import_approved_urls(db, source, payload.urls)
    return [ImportedDocumentResponse.model_validate(document) for document in documents]


@router.get("/imported-documents", response_model=list[ImportedDocumentResponse])
def list_imported_documents(
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
) -> list[ImportedDocumentResponse]:
    documents = ingestion_service.list_imported_documents(db)
    return [ImportedDocumentResponse.model_validate(document) for document in documents]


@router.get("/imported-documents/{document_id}", response_model=ImportedDocumentDetailResponse)
def get_imported_document(
    document_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
) -> ImportedDocumentDetailResponse:
    document = db.get(ImportedDocument, document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Imported document not found")
    return ImportedDocumentDetailResponse.model_validate(document)


@router.post("/imported-documents/{document_id}/anonymize", response_model=ImportedDocumentResponse)
def anonymize_imported_document(
    document_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
) -> ImportedDocumentResponse:
    document = db.get(ImportedDocument, document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Imported document not found")
    updated = ingestion_service.anonymize_imported_document(db, document)
    return ImportedDocumentResponse.model_validate(updated)


@router.post("/imported-documents/{document_id}/reject", response_model=ImportedDocumentResponse)
def reject_imported_document(
    document_id: int,
    payload: RejectImportedDocumentRequest,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
) -> ImportedDocumentResponse:
    document = db.get(ImportedDocument, document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Imported document not found")
    updated = ingestion_service.reject_imported_document(db, document, payload.rejection_reason)
    return ImportedDocumentResponse.model_validate(updated)


@router.post("/imported-documents/{document_id}/create-training-sample", response_model=CreateTrainingSampleResponse)
def create_training_sample(
    document_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
) -> CreateTrainingSampleResponse:
    document = db.get(ImportedDocument, document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Imported document not found")
    sample = ingestion_service.create_training_sample_from_document(db, document)
    return CreateTrainingSampleResponse(
        training_sample_id=sample.id,
        quality_status=sample.quality_status,
        pii_risk_score=sample.pii_risk_score,
    )


@router.get("/training-samples", response_model=TrainingSamplesResponse)
def get_training_samples(
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
) -> TrainingSamplesResponse:
    previews = [TrainingSamplePreview.model_validate(item) for item in dataset_builder.list_training_samples(db)]
    exportable_samples = sum(1 for item in previews if item.valid_for_export)
    return TrainingSamplesResponse(total_samples=len(previews), exportable_samples=exportable_samples, samples=previews)


@router.get("/training-samples/{sample_id}", response_model=TrainingSampleDetailResponse)
def get_training_sample(
    sample_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
) -> TrainingSampleDetailResponse:
    sample = db.get(AnonymizedTrainingSample, sample_id)
    if not sample:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training sample not found")
    preview = dataset_builder.build_training_sample_preview(db, sample)
    return TrainingSampleDetailResponse(
        **preview,
        input_payload=sample.input_payload,
        output_payload=sample.output_payload,
        training_record_json=sample.training_record_json,
        data_source=TrainingSampleDataSourceInfo.model_validate(sample.data_source) if sample.data_source else None,
        reviews=[TrainingSampleReviewEntry.model_validate(review) for review in sample.reviews],
    )


@router.post("/training-samples/{sample_id}/review", status_code=status.HTTP_201_CREATED)
def review_training_sample(
    sample_id: int,
    payload: ReviewTrainingSampleRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_admin_user),
) -> dict:
    sample = db.get(AnonymizedTrainingSample, sample_id)
    if not sample:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Training sample not found")
    review = ingestion_service.review_training_sample(
        db,
        sample,
        reviewer_admin_id=admin.id,
        status_value=payload.status,
        quality_score=payload.quality_score,
        notes=payload.notes,
    )
    return {"review_id": review.id, "status": review.status}


@router.post("/export-training-jsonl", response_model=TrainingExportResponse)
def export_training_jsonl(
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
) -> TrainingExportResponse:
    export_path, exported_count, skipped_count = dataset_builder.export_training_jsonl(db)
    db.commit()
    return TrainingExportResponse(exported_count=exported_count, skipped_count=skipped_count, file_path=str(export_path))


@router.post("/export/curated-training-jsonl", response_model=TrainingExportResponse)
def export_curated_training_jsonl(
    db: Session = Depends(get_db),
    _: User = Depends(get_admin_user),
) -> TrainingExportResponse:
    export_path, exported_count, skipped_count = dataset_builder.export_training_jsonl(db)
    db.commit()
    return TrainingExportResponse(exported_count=exported_count, skipped_count=skipped_count, file_path=str(export_path))
