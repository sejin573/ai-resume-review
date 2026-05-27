import json
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.review import AnonymizedTrainingSample, DataSource, TrainingSampleReview
from app.services.dataset_builder import DatasetBuilderService
from app.services.seed_ingestion_service import SeedIngestionService
from tests.conftest import get_auth_headers


def _build_review_result(total_score: float = 74.0) -> dict:
    return {
        "total_score": total_score,
        "scores": {
            "job_fit": 76,
            "specificity": 72,
            "achievement": 68,
            "writing_quality": 79,
            "uniqueness": 71,
            "structure": 75,
            "keyword_match": 77,
        },
        "summary": "The draft shows relevant effort but still needs clearer outcomes and tighter role alignment.",
        "problems": [
            "Experience is present but some outcomes are still broad.",
            "Role keywords are not connected tightly enough to actions.",
            "Sentence flow can be more direct and easier to scan.",
        ],
        "improvement_strategy": [
            "Rewrite each experience in situation-action-result order.",
            "Add one measurable impact or scope detail per example.",
            "Connect each paragraph to the target role more explicitly.",
        ],
        "improved_cover_letter": "This revised draft keeps the same fictional story but states actions, scope, and role fit more clearly.",
        "interview_questions": [
            "What was your exact contribution in the most relevant project?",
            "How did you decide which task to prioritize first?",
            "What result would you measure if this work were repeated?",
        ],
        "missing_keywords": ["collaboration", "execution"],
        "strengths": [
            "The motivation is sincere and role-oriented.",
            "The draft hints at practical learning behavior.",
            "The overall tone is professional and stable.",
        ],
    }


def _build_seed_sample(idx: int, *, role: str = "웹개발자 신입", cover_letter: str | None = None) -> dict:
    review_result = _build_review_result(total_score=70.0 + idx)
    original_cover_letter = cover_letter or (
        f"가상의 지원자 {idx}번은 팀 과제와 프로젝트 경험을 바탕으로 {role} 직무에 맞는 문제 해결 방식과 협업 태도를 설명합니다."
    )
    return {
        "job_role": role,
        "fictional_job_posting_summary": f"가상의 조직에서 {role} 직무에 필요한 기본 역량과 협업 태도를 보는 공고 요약 {idx}",
        "resume_summary": f"가상의 활동 요약 {idx}. 프로젝트 문서 정리와 실행 경험을 중심으로 정리했습니다.",
        "original_cover_letter": original_cover_letter,
        "review_result": review_result,
        "data_source": "manual_seed",
        "quality_status": "draft",
        "training_record": {
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert Korean resume and cover letter coach. You provide strict, practical, job-relevant feedback.",
                },
                {
                    "role": "user",
                    "content": (
                        f"지원 직무: {role}\n"
                        f"채용공고: 가상의 조직 공고 요약 {idx}\n"
                        f"이력서 요약: 가상의 활동 요약 {idx}\n"
                        f"자기소개서 원문: {original_cover_letter}"
                    ),
                },
                {"role": "assistant", "content": json.dumps(review_result, ensure_ascii=False)},
            ],
            "metadata": {
                "job_role": role,
                "data_source": "manual_seed",
                "quality_status": "draft",
            },
        },
    }


def _write_jsonl(tmp_path: Path, name: str, rows: list[dict]) -> Path:
    path = tmp_path / name
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows), encoding="utf-8")
    return path


def _reset_manual_seed_data(db) -> None:
    service = SeedIngestionService()
    source = db.scalar(
        select(DataSource).where(
            DataSource.source_name == service.SOURCE_NAME,
            DataSource.source_type == "manual_seed",
        )
    )
    if source is None:
        return
    for sample in list(source.training_samples):
        for review in list(sample.reviews):
            db.delete(review)
        db.delete(sample)
    db.delete(source)
    db.commit()


def test_seed_jsonl_import_succeeds_and_deduplicates(tmp_path):
    db = SessionLocal()
    try:
        _reset_manual_seed_data(db)
        service = SeedIngestionService()
        jsonl_path = _write_jsonl(tmp_path, "seed.jsonl", [_build_seed_sample(1), _build_seed_sample(2, role="마케팅")])

        first = service.import_seed_jsonl(db, jsonl_path=jsonl_path)
        second = service.import_seed_jsonl(db, jsonl_path=jsonl_path)

        source = db.scalar(select(DataSource).where(DataSource.id == first["data_source_id"]))
        samples = db.scalars(
            select(AnonymizedTrainingSample).where(AnonymizedTrainingSample.data_source_id == first["data_source_id"])
        ).all()

        assert source is not None
        assert source.source_type == "manual_seed"
        assert source.license_status == "approved"
        assert first["imported_count"] == 2
        assert first["skipped_duplicates"] == 0
        assert second["imported_count"] == 0
        assert second["skipped_duplicates"] == 2
        assert len(samples) == 2
        assert all(sample.quality_status == "draft" for sample in samples)
        assert all(sample.reviewed_by_human is False for sample in samples)
    finally:
        db.close()


def test_invalid_assistant_json_is_rejected(tmp_path):
    db = SessionLocal()
    try:
        _reset_manual_seed_data(db)
        service = SeedIngestionService()
        sample = _build_seed_sample(3)
        sample["training_record"]["messages"][2]["content"] = "{not-json}"
        jsonl_path = _write_jsonl(tmp_path, "invalid-assistant.jsonl", [sample])

        try:
            service.import_seed_jsonl(db, jsonl_path=jsonl_path)
        except Exception as exc:  # noqa: BLE001
            assert "invalid assistant JSON" in str(exc)
        else:
            raise AssertionError("Expected invalid assistant JSON to be rejected")
    finally:
        db.close()


def test_seed_sample_with_pii_is_rejected(tmp_path):
    db = SessionLocal()
    try:
        _reset_manual_seed_data(db)
        service = SeedIngestionService()
        sample = _build_seed_sample(4, cover_letter="연락처는 test@example.com 이고 가상의 직무 경험을 설명합니다.")
        sample["training_record"]["messages"][1]["content"] += "\n이메일: test@example.com"
        jsonl_path = _write_jsonl(tmp_path, "pii.jsonl", [sample])

        try:
            service.import_seed_jsonl(db, jsonl_path=jsonl_path)
        except Exception as exc:  # noqa: BLE001
            assert "contains PII" in str(exc) or "PII risk" in str(exc)
        else:
            raise AssertionError("Expected PII sample to be rejected")
    finally:
        db.close()


def test_draft_samples_are_not_exportable_and_reviewed_samples_are_exportable(tmp_path, client):
    headers = get_auth_headers(client)
    db = SessionLocal()
    try:
        _reset_manual_seed_data(db)
        service = SeedIngestionService()
        dataset_builder = DatasetBuilderService()
        jsonl_path = _write_jsonl(tmp_path, "exportable.jsonl", [_build_seed_sample(5)])
        summary = service.import_seed_jsonl(db, jsonl_path=jsonl_path)
        sample = db.scalar(
            select(AnonymizedTrainingSample).where(AnonymizedTrainingSample.data_source_id == summary["data_source_id"])
        )
        assert sample is not None

        draft_preview = dataset_builder.build_training_sample_preview(db, sample)
        assert draft_preview["valid_for_export"] is False

        sample_detail = client.get(f"/admin/training-samples/{sample.id}", headers=headers)
        assert sample_detail.status_code == 200

        review_response = client.post(
            f"/admin/training-samples/{sample.id}/review",
            json={"status": "reviewed", "quality_score": 91, "notes": "ready for export"},
            headers=headers,
        )
        assert review_response.status_code == 201

        db.refresh(sample)
        reviewed_preview = dataset_builder.build_training_sample_preview(db, sample)
        assert reviewed_preview["valid_for_export"] is True

        export_response = client.post("/admin/export/curated-training-jsonl", headers=headers)
        assert export_response.status_code == 200
        export_path = Path(export_response.json()["file_path"])
        lines = [line for line in export_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        assert lines
        exported_records = [json.loads(line) for line in lines]
        assert any(record["metadata"].get("source_type") == "manual_seed" for record in exported_records)
        for record in exported_records:
            assistant_payload = json.loads(record["messages"][2]["content"])
            assert "total_score" in assistant_payload
            assert "scores" in assistant_payload
    finally:
        db.close()


def test_unapproved_data_source_blocks_export_validation(tmp_path):
    db = SessionLocal()
    try:
        _reset_manual_seed_data(db)
        service = SeedIngestionService()
        dataset_builder = DatasetBuilderService()
        jsonl_path = _write_jsonl(tmp_path, "license-block.jsonl", [_build_seed_sample(6)])
        summary = service.import_seed_jsonl(db, jsonl_path=jsonl_path)
        source = db.scalar(select(DataSource).where(DataSource.id == summary["data_source_id"]))
        sample = db.scalar(
            select(AnonymizedTrainingSample).where(AnonymizedTrainingSample.data_source_id == summary["data_source_id"])
        )
        reviewer = service.ensure_local_admin_user(db, "test@example.com")
        service.bulk_mark_manual_seed_reviewed(db, reviewer_admin_id=reviewer.id)

        source.license_status = "needs_review"
        db.add(source)
        db.commit()
        db.refresh(sample)

        errors = dataset_builder.validate_training_record(sample.training_record_json, sample)
        assert any("license_status is not approved" in error for error in errors)
    finally:
        db.close()


def test_bulk_review_helper_marks_manual_seed_samples_reviewed(tmp_path):
    db = SessionLocal()
    try:
        _reset_manual_seed_data(db)
        service = SeedIngestionService()
        jsonl_path = _write_jsonl(tmp_path, "bulk-review.jsonl", [_build_seed_sample(7), _build_seed_sample(8)])
        summary = service.import_seed_jsonl(db, jsonl_path=jsonl_path)
        reviewer = service.ensure_local_admin_user(db, "test@example.com")

        updated_count = service.bulk_mark_manual_seed_reviewed(db, reviewer_admin_id=reviewer.id)
        samples = db.scalars(
            select(AnonymizedTrainingSample).where(AnonymizedTrainingSample.data_source_id == summary["data_source_id"])
        ).all()
        reviews = db.scalars(select(TrainingSampleReview).where(TrainingSampleReview.reviewer_admin_id == reviewer.id)).all()

        assert updated_count == 2
        assert all(sample.reviewed_by_human is True for sample in samples)
        assert all(sample.quality_status == "reviewed" for sample in samples)
        assert any(service.BULK_REVIEW_NOTE in (review.notes or "") for review in reviews)
    finally:
        db.close()


def test_review_endpoint_requires_quality_score_and_reject_note(tmp_path, client):
    headers = get_auth_headers(client)
    db = SessionLocal()
    try:
        _reset_manual_seed_data(db)
        service = SeedIngestionService()
        jsonl_path = _write_jsonl(tmp_path, "review-rules.jsonl", [_build_seed_sample(9)])
        summary = service.import_seed_jsonl(db, jsonl_path=jsonl_path)
        sample = db.scalar(
            select(AnonymizedTrainingSample).where(AnonymizedTrainingSample.data_source_id == summary["data_source_id"])
        )

        missing_score = client.post(
            f"/admin/training-samples/{sample.id}/review",
            json={"status": "reviewed", "notes": "ready"},
            headers=headers,
        )
        assert missing_score.status_code == 400

        missing_note = client.post(
            f"/admin/training-samples/{sample.id}/review",
            json={"status": "rejected", "quality_score": 20, "notes": ""},
            headers=headers,
        )
        assert missing_note.status_code == 400
    finally:
        db.close()
