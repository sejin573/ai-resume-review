from fastapi.testclient import TestClient

from tests.conftest import get_auth_headers


def build_base_payload():
    return {
        "resume_text": "백엔드 개발 프로젝트에서 API 설계와 예외 처리 개선을 맡았고, 협업 과정에서 문서화를 정리한 경험이 있습니다. " * 3,
        "cover_letter_text": "문제를 정리하고 역할을 나누어 해결한 경험을 바탕으로, 지원 직무에서도 필요한 흐름을 빠르게 파악하고 실행하겠습니다. " * 3,
        "target_job_role": "백엔드 개발자",
        "job_posting_text": "FastAPI, PostgreSQL, 협업 경험과 문서화 역량을 갖춘 지원자를 찾습니다. " * 3,
        "source_file_type": "txt",
        "review_mode": "strict",
        "job_category_preset": "웹개발자",
    }


def test_review_flow(client: TestClient):
    headers = get_auth_headers(client)
    payload = build_base_payload()

    create_response = client.post("/reviews", json=payload, headers=headers)
    assert create_response.status_code == 201
    review_id = create_response.json()["id"]
    assert create_response.json()["review_result"]["problems"]
    assert "suggestions" in create_response.json()["review_result"]

    list_response = client.get("/reviews", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    detail_response = client.get(f"/reviews/{review_id}", headers=headers)
    assert detail_response.status_code == 200
    assert detail_response.json()["review_result"]["total_score"] >= 0
    assert detail_response.json()["review_mode"] == "strict"

    refine_response = client.post(
        f"/reviews/{review_id}/refine",
        json={
            "instruction": "더 구체적으로 바꿔줘",
            "current_text": detail_response.json()["review_result"]["improved_cover_letter"],
            "target_job_role": detail_response.json()["target_job_role"],
            "job_posting_text": detail_response.json()["job_posting_text"],
        },
        headers=headers,
    )
    assert refine_response.status_code == 200
    assert refine_response.json()["refined_text"]
    assert "change_summary" in refine_response.json()

    final_response = client.put(
        f"/reviews/{review_id}/final-document",
        json={
            "final_text": refine_response.json()["refined_text"],
            "source": "refinement",
        },
        headers=headers,
    )
    assert final_response.status_code == 200
    assert final_response.json()["final_text"] == refine_response.json()["refined_text"]
    assert final_response.json()["source"] == "refinement"

    final_get_response = client.get(f"/reviews/{review_id}/final-document", headers=headers)
    assert final_get_response.status_code == 200
    assert final_get_response.json()["review_id"] == review_id

    pdf_response = client.get(f"/reviews/{review_id}/export/pdf", headers=headers)
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"] == "application/pdf"
    assert pdf_response.content.startswith(b"%PDF")

    feedback_response = client.post(
        f"/reviews/{review_id}/feedback",
        json={"rating": "helpful", "reason": "개선 방향이 구체적이어서 수정 포인트를 바로 잡을 수 있었습니다."},
        headers=headers,
    )
    assert feedback_response.status_code == 201
    assert feedback_response.json()["rating"] == "helpful"

    detail_with_final_response = client.get(f"/reviews/{review_id}", headers=headers)
    assert detail_with_final_response.status_code == 200
    assert detail_with_final_response.json()["final_document"]["source"] == "refinement"

    consent_response = client.post(
        f"/reviews/{review_id}/consent-training",
        json={"consent_given": True},
        headers=headers,
    )
    assert consent_response.status_code == 200
    assert consent_response.json()["anonymized_sample_created"] is True


def test_review_create_with_cover_letter_only(client: TestClient):
    headers = get_auth_headers(client)
    payload = {
        "cover_letter_text": "사용자 문의를 정리하고 반복되는 문제를 문서화한 경험을 바탕으로, 새로운 환경에서도 빠르게 업무 흐름을 익히고 개선점을 찾겠습니다. " * 2,
        "source_file_type": "txt",
        "review_mode": "detailed",
    }

    response = client.post("/reviews", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["cover_letter_text"]
    assert data["resume_text"] == ""
    assert data["job_posting_text"] == ""
    assert data["target_job_role"] == ""
    assert data["review_result"]["total_score"] >= 0


def test_review_create_with_cover_letter_and_role_only(client: TestClient):
    headers = get_auth_headers(client)
    payload = {
        "cover_letter_text": "프로젝트에서 맡은 역할을 끝까지 책임지고 정리한 경험을 바탕으로, 교육행정 업무에서도 필요한 문서와 일정 흐름을 안정적으로 관리하겠습니다. " * 2,
        "target_job_role": "교육행정",
        "review_mode": "quick",
        "source_file_type": "txt",
    }

    response = client.post("/reviews", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["target_job_role"] == "교육행정"
    assert data["review_result"]["scores"]["keyword_match"] <= 58


def test_review_create_with_all_fields(client: TestClient):
    headers = get_auth_headers(client)
    payload = build_base_payload()

    response = client.post("/reviews", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["resume_text"]
    assert data["job_posting_text"]
    assert data["review_result"]["suggestions"] is not None


def test_me_endpoint_returns_usage_summary(client: TestClient):
    headers = get_auth_headers(client)
    response = client.get("/auth/me", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["email"] == "test@example.com"
    assert payload["is_admin"] is True
    assert "usage" in payload
    assert "review_daily" in payload["usage"]
