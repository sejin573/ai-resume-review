from app.schemas.review import AIReviewResponse
from app.services.anonymization_service import AnonymizationService
from app.services.ai_client import AIReviewService
from app.services.anonymizer import anonymize_text


def test_anonymize_text_masks_basic_pii():
    text = "홍길동님 연락처는 010-1234-5678, 이메일은 test@example.com, 생년월일은 1999-02-03, 주소는 서울시 강남구입니다."
    masked = anonymize_text(text)
    assert "[PHONE]" in masked
    assert "[EMAIL]" in masked
    assert "[BIRTH_DATE]" in masked
    assert "[ADDRESS]" in masked
    assert "[NAME]" in masked


def test_anonymization_service_masks_extended_patterns():
    service = AnonymizationService()
    text = (
        "가나다대학교 졸업 후 브라이트소프트에서 인턴을 했고, "
        "홈페이지는 https://fictional.example/test 이며 계좌는 123-456-789012, "
        "학번 20240001, 주민번호 비슷한 값은 900101-2345678 입니다."
    )
    masked = service.anonymize_text(text)
    assert "[URL]" in masked
    assert "[ACCOUNT]" in masked
    assert "[RRN]" in masked
    assert "[ID]" in masked


def test_mock_ai_response_matches_schema():
    service = AIReviewService()
    result, provider, model = service.review(
        resume_text="경력과 프로젝트 내용을 충분히 길게 적은 이력서 텍스트입니다." * 3,
        cover_letter_text="지원 동기와 문제 해결 경험을 충분히 길게 적은 자기소개서 텍스트입니다." * 3,
        target_job_role="백엔드 개발자",
        job_posting_text="Python, FastAPI, PostgreSQL 경험을 요구하는 채용공고 내용입니다." * 2,
        review_mode="strict",
        job_category_preset="웹개발자",
    )
    assert isinstance(result, AIReviewResponse)
    assert provider in {"mock", "openai"}
    assert model
    assert result.total_score <= 82
