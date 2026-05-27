import json
from pathlib import Path

from app.schemas.review import AIReviewResponse, ReviewCreateRequest
from app.services.ai_client import AIReviewService
from app.services.anonymization_service import AnonymizationService
from app.services.review_parser import ReviewResponseParser


def load_cases() -> list[dict]:
    fixture_path = Path(__file__).parent / "fixtures" / "review_quality_cases.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def test_mock_review_quality_cases_produce_valid_responses():
    service = AIReviewService()
    pii_service = AnonymizationService()

    for case in load_cases():
        result, provider, model = service.review(
            resume_text=case["resume_text"],
            cover_letter_text=case["cover_letter_text"],
            target_job_role=case["target_job_role"],
            job_posting_text=case["job_posting_text"],
            review_mode=case["review_mode"],
            job_category_preset=None,
        )
        assert isinstance(result, AIReviewResponse)
        assert provider in {"mock", "openai"}
        assert model
        assert result.improved_cover_letter.strip()
        assert result.interview_questions
        assert set(result.scores.model_dump().keys()) == {
            "job_fit",
            "specificity",
            "achievement",
            "writing_quality",
            "uniqueness",
            "structure",
            "keyword_match",
        }
        pii_text = "\n".join(
            [
                result.summary,
                result.improved_cover_letter,
                *result.problems,
                *result.interview_questions,
            ]
        )
        assert pii_service.detect_remaining_pii(pii_text) == []

        if "expected_max_score" in case:
            assert result.total_score <= case["expected_max_score"]
        if "expected_min_score" in case:
            assert result.total_score >= case["expected_min_score"]


def test_parser_handles_markdown_json_block():
    parser = ReviewResponseParser()
    payload = {
        "total_score": 71,
        "scores": {
            "job_fit": 72,
            "specificity": 68,
            "achievement": 61,
            "writing_quality": 76,
            "uniqueness": 66,
            "structure": 73,
            "keyword_match": 70,
        },
        "summary": "요약",
        "problems": ["문제 1"],
        "improvement_strategy": ["전략 1"],
        "improved_cover_letter": "개선문",
        "interview_questions": ["질문 1"],
        "missing_keywords": ["키워드"],
        "strengths": ["강점"],
    }
    raw = f"```json\n{json.dumps(payload, ensure_ascii=False)}\n```"
    parsed = parser.parse(raw)
    assert parsed.total_score == 71
    assert parsed.improved_cover_letter == "개선문"


def test_parser_clamps_invalid_scores_and_repairs_lists():
    parser = ReviewResponseParser()
    raw = json.dumps(
        {
            "total_score": 999,
            "scores": {
                "job_fit": 120,
                "specificity": -5,
                "achievement": "88",
                "writing_quality": 77,
                "uniqueness": 65,
                "structure": 73,
                "keyword_match": 200,
            },
            "summary": "요약",
            "problems": "문제 1\n문제 2",
            "improvement_strategy": "전략 1",
            "improved_cover_letter": "개선문",
            "interview_questions": "질문 1",
            "missing_keywords": "키워드 1;키워드 2",
            "strengths": "강점 1",
        },
        ensure_ascii=False,
    )
    parsed = parser.parse(raw)
    assert parsed.scores.job_fit == 100
    assert parsed.scores.specificity == 0
    assert parsed.scores.keyword_match == 100
    assert parsed.problems == ["문제 1", "문제 2"]
    assert parsed.improvement_strategy == ["전략 1"]


def test_review_mode_alias_is_normalized():
    payload = ReviewCreateRequest(
        resume_text="프로젝트 경험과 협업 경험을 포함한 이력서 요약입니다." * 3,
        cover_letter_text="직무와 연결되는 경험을 정리한 자기소개서 초안입니다." * 3,
        target_job_role="웹개발자 신입",
        job_posting_text="FastAPI, 협업, 문제 해결 역량을 요구하는 채용공고입니다." * 2,
        review_mode="rewrite_focused",
    )
    assert payload.review_mode == "rewrite-focused"
