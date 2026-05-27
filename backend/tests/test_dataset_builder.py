from io import BytesIO
import json
from pathlib import Path

from app.db.session import SessionLocal
from app.models.review import AnonymizedTrainingSample
from app.services.anonymization_service import AnonymizationService
from app.services.dataset_builder import DatasetBuilderService
from app.services.training_transform_service import TrainingTransformService
from tests.conftest import get_auth_headers


def test_dataset_builder_rejects_pii_in_messages():
    service = DatasetBuilderService()
    payload = {
        "messages": [
            {"role": "system", "content": "You are an expert Korean resume and cover letter coach."},
            {"role": "user", "content": "이메일: test@example.com"},
            {"role": "assistant", "content": "{}"},
        ],
        "metadata": {"job_role": "웹개발자", "review_mode": "strict", "score": 72, "source_type": "user_consent"},
    }
    errors = service.validate_training_record(payload)
    assert errors


def test_anonymization_service_scores_risk():
    service = AnonymizationService()
    masked = service.anonymize_text("홍길동님 010-1234-5678 test@example.com 서울시 강남구")
    assert "[PHONE]" in masked
    assert "[EMAIL]" in masked
    assert service.pii_risk_score(masked) < service.HIGH_RISK_THRESHOLD


def test_anonymization_service_masks_required_patterns():
    service = AnonymizationService()
    raw = (
        "이메일 user@example.com, 전화 010-5555-6666, 생년월일 1998-03-21, "
        "주민번호 유사 980321-2345678, 주소는 경기 새봄시 은하로 12, "
        "모노학원 출신, 하모니랩 재직, URL https://seed.local, 계좌 111-222-333333, 학번 20231234"
    )
    masked = service.anonymize_text(raw)
    assert "[EMAIL]" in masked
    assert "[PHONE]" in masked
    assert "[BIRTH_DATE]" in masked or "[RRN]" in masked
    assert "[RRN]" in masked
    assert "[ADDRESS]" in masked
    assert "[URL]" in masked
    assert "[ACCOUNT]" in masked
    assert "[ID]" in masked


def test_training_transform_service_outputs_required_review_schema():
    service = TrainingTransformService()
    record = service.transform_accepted_cover_letter(
        data_source_id=1,
        source_type="manual_seed",
        job_role="웹개발자 신입",
        accepted_cover_letter="가상의 프로젝트에서 문제를 분석하고 화면 흐름을 개선한 경험이 있습니다.",
        job_keywords=["문제 해결", "협업"],
        resume_summary="가상의 포트폴리오 프로젝트를 수행했습니다.",
        contains_real_user_data=False,
    )
    assistant_payload = __import__("json").loads(record["messages"][2]["content"])
    for key in [
        "total_score",
        "scores",
        "summary",
        "problems",
        "improvement_strategy",
        "improved_cover_letter",
        "interview_questions",
        "missing_keywords",
        "strengths",
    ]:
        assert key in assistant_payload


def test_dataset_builder_validates_clean_payload(client):
    headers = get_auth_headers(client)
    review_payload = {
        "resume_text": "백엔드 API 개발과 데이터 처리 경험을 충분히 설명한 이력서입니다. " * 4,
        "cover_letter_text": "문제 해결과 협업 경험을 충분히 설명한 자기소개서입니다. " * 4,
        "target_job_role": "백엔드 개발자",
        "job_posting_text": "FastAPI, PostgreSQL, 협업 경험을 요구하는 채용공고입니다. " * 4,
        "source_file_type": "txt",
        "review_mode": "strict",
        "job_category_preset": "웹개발자",
    }
    review = client.post("/reviews", json=review_payload, headers=headers).json()
    client.post(f"/reviews/{review['id']}/consent-training", json={"consent_given": True}, headers=headers)

    source_payload = {
        "source_name": "Manual Seed",
        "source_type": "manual_seed",
        "license_status": "approved",
        "license_note": "Manually created examples with internal rights confirmation.",
    }
    source_response = client.post("/admin/data-sources", json=source_payload, headers=headers)
    assert source_response.status_code == 201
    source_id = source_response.json()["id"]

    csv_body = (
        "document_type,job_role,original_title,original_text,source_reference,license_note\n"
        "accepted_cover_letter,웹개발자 신입,샘플 제목,문제 해결과 협업 경험을 바탕으로 성장한 자기소개서 예시입니다.,seed-1,internal\n"
    )
    files = {"file": ("seed.csv", BytesIO(csv_body.encode("utf-8")), "text/csv")}
    import_response = client.post(f"/admin/import/csv?data_source_id={source_id}", files=files, headers=headers)
    assert import_response.status_code == 201
    imported_document_id = import_response.json()[0]["id"]

    anonymize_response = client.post(f"/admin/imported-documents/{imported_document_id}/anonymize", headers=headers)
    assert anonymize_response.status_code == 200

    sample_response = client.post(
        f"/admin/imported-documents/{imported_document_id}/create-training-sample", headers=headers
    )
    assert sample_response.status_code == 200
    sample_id = sample_response.json()["training_sample_id"]

    review_sample_response = client.post(
        f"/admin/training-samples/{sample_id}/review",
        json={"status": "reviewed", "quality_score": 88, "notes": "ready"},
        headers=headers,
    )
    assert review_sample_response.status_code == 201

    preview_response = client.get("/admin/training-samples", headers=headers)
    assert preview_response.status_code == 200
    assert preview_response.json()["exportable_samples"] >= 1

    export_response = client.post("/admin/export/curated-training-jsonl", headers=headers)
    assert export_response.status_code == 200
    assert export_response.json()["exported_count"] >= 1


def test_unapproved_data_source_is_blocked(client):
    headers = get_auth_headers(client)
    source_payload = {
        "source_name": "Blocked Source",
        "source_type": "admin_upload",
        "license_status": "needs_review",
        "license_note": "Not approved yet.",
    }
    source_response = client.post("/admin/data-sources", json=source_payload, headers=headers)
    assert source_response.status_code == 201
    source_id = source_response.json()["id"]

    jsonl_line = (
        '{"document_type":"accepted_cover_letter","job_role":"사무직","original_title":"x","original_text":"가상의 합격 예시입니다.","source_reference":"blocked"}'
    )
    files = {"file": ("blocked.jsonl", BytesIO(jsonl_line.encode("utf-8")), "application/x-ndjson")}
    import_response = client.post(f"/admin/import/jsonl?data_source_id={source_id}", files=files, headers=headers)
    assert import_response.status_code == 400


def test_high_risk_pii_sample_is_not_exportable(client):
    headers = get_auth_headers(client)
    source_payload = {
        "source_name": "Risky Seed",
        "source_type": "manual_seed",
        "license_status": "approved",
        "license_note": "fictional but used for pii rejection test",
    }
    source = client.post("/admin/data-sources", json=source_payload, headers=headers).json()
    jsonl_line = (
        '{"document_type":"accepted_cover_letter","job_role":"마케팅","original_title":"risk","original_text":"가상의 캠페인 운영 경험을 정리한 합격 예시입니다.","source_reference":"risk-case"}'
    )
    files = {"file": ("risk.jsonl", BytesIO(jsonl_line.encode("utf-8")), "application/x-ndjson")}
    imported = client.post(f"/admin/import/jsonl?data_source_id={source['id']}", files=files, headers=headers).json()[0]
    anonymized = client.post(f"/admin/imported-documents/{imported['id']}/anonymize", headers=headers)
    assert anonymized.status_code == 200
    create_sample = client.post(f"/admin/imported-documents/{imported['id']}/create-training-sample", headers=headers)
    assert create_sample.status_code == 200
    sample_id = create_sample.json()["training_sample_id"]

    db = SessionLocal()
    try:
        sample = db.get(AnonymizedTrainingSample, sample_id)
        training_record = sample.training_record_json
        training_record["messages"][1]["content"] += "\n연락처: user@example.com / 010-9999-8888"
        sample.training_record_json = training_record
        sample.pii_risk_score = 100
        sample.reviewed_by_human = True
        sample.quality_status = "reviewed"
        db.add(sample)
        db.commit()
    finally:
        db.close()

    preview_response = client.get("/admin/training-samples", headers=headers)
    assert preview_response.status_code == 200
    risky_preview = next(item for item in preview_response.json()["samples"] if item["sample_id"] == sample_id)
    assert risky_preview["valid_for_export"] is False
    assert risky_preview["pii_risk_score"] >= 100

    export_response = client.post("/admin/export/curated-training-jsonl", headers=headers)
    assert export_response.status_code == 200
    export_path = Path(export_response.json()["file_path"])
    exported_text = export_path.read_text(encoding="utf-8")
    assert "user@example.com" not in exported_text
    assert "010-9999-8888" not in exported_text
