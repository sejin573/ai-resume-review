from app.schemas.review import AIReviewResponse, CoverLetterSuggestion, SentenceReview
from app.services.ai_client import AIReviewService
from app.services.sentence_review_service import SentenceReviewService
from app.services.suggestion_service import SuggestionService


def test_ai_review_response_accepts_suggestions():
    payload = {
        "total_score": 70,
        "scores": {
            "job_fit": 70,
            "specificity": 68,
            "achievement": 64,
            "writing_quality": 72,
            "uniqueness": 66,
            "structure": 71,
            "keyword_match": 69,
        },
        "summary": "요약",
        "problems": ["문제"],
        "improvement_strategy": ["전략"],
        "improved_cover_letter": "개선문",
        "interview_questions": ["질문"],
        "missing_keywords": ["키워드"],
        "strengths": ["강점"],
        "suggestions": [
            {
                "id": "sug-1",
                "severity": "high",
                "category": "achievement",
                "original_text": "맡은 일을 열심히 수행했습니다.",
                "start_index": None,
                "end_index": None,
                "issue": "성과 근거 부족",
                "reason": "무엇을 했는지와 결과가 부족합니다.",
                "suggested_text": "[프로젝트]에서 [역할]을 맡아 [행동]을 수행했고 [성과 수치]를 만들었습니다.",
                "apply_type": "replace",
                "confidence": 0.86,
            }
        ],
    }
    result = AIReviewResponse.model_validate(payload)
    assert result.suggestions[0].issue == "성과 근거 부족"


def test_ai_review_response_accepts_sentence_reviews():
    payload = {
        "total_score": 70,
        "scores": {
            "job_fit": 70,
            "specificity": 68,
            "achievement": 64,
            "writing_quality": 72,
            "uniqueness": 66,
            "structure": 71,
            "keyword_match": 69,
        },
        "summary": "요약",
        "problems": ["문제"],
        "improvement_strategy": ["전략"],
        "improved_cover_letter": "개선문",
        "interview_questions": ["질문"],
        "missing_keywords": ["키워드"],
        "strengths": ["강점"],
        "sentence_reviews": [
            {
                "id": "sent-1",
                "sentence_text": "프로젝트에서 API를 구현했습니다.",
                "start_index": 0,
                "end_index": 18,
                "status": "good",
                "category": "clarity",
                "label": "경험 근거 좋음",
                "good_point": "행동이 드러납니다.",
                "comment": "좋은 문장입니다.",
                "suggested_text": None,
                "can_apply": False,
                "context_before": None,
                "context_after": None,
                "edit_type": "replace_sentence",
                "expected_effect": "강점을 유지합니다.",
                "confidence": 0.8,
            }
        ],
    }
    result = AIReviewResponse.model_validate(payload)
    assert result.sentence_reviews[0].status == "good"
    assert result.sentence_reviews[0].expected_effect == "강점을 유지합니다."


def test_suggestion_post_processing_computes_indexes_and_removes_duplicates():
    service = SuggestionService()
    text = "맡은 일을 열심히 수행했습니다. 이후 문서를 정리했습니다."
    suggestions = [
        CoverLetterSuggestion(
            severity="high",
            category="specificity",
            original_text="맡은 일을 열심히 수행했습니다.",
            issue="표현이 추상적입니다",
            reason="행동과 결과가 보이지 않습니다.",
            suggested_text="[업무]에서 [역할]을 맡아 [행동]을 수행했고 [성과 수치]를 만들었습니다.",
            apply_type="replace",
            confidence=1.2,
        ),
        CoverLetterSuggestion(
            severity="medium",
            category="specificity",
            original_text="맡은 일을 열심히 수행했습니다.",
            issue="중복",
            reason="중복",
            suggested_text="[업무]에서 [역할]을 맡아 [행동]을 수행했고 [성과 수치]를 만들었습니다.",
            apply_type="replace",
            confidence=0.7,
        ),
    ]
    processed = service.process(suggestions, text)
    assert len(processed) == 1
    assert processed[0].start_index == 0
    assert processed[0].end_index == len("맡은 일을 열심히 수행했습니다.")
    assert processed[0].confidence == 1.0
    assert processed[0].id == "sug-1"


def test_missing_original_text_does_not_crash():
    service = SuggestionService()
    processed = service.process(
        [
            CoverLetterSuggestion(
                severity="medium",
                category="job_fit",
                original_text="없는 문장입니다.",
                issue="직무 연결 부족",
                reason="원문에서 직접 찾기 어렵습니다.",
                suggested_text="지원 직무와 연결되는 문장을 덧붙여 주세요.",
                apply_type="append_after",
                confidence=0.8,
            )
        ],
        "실제 원문에는 다른 문장만 있습니다.",
    )
    assert len(processed) == 1
    assert processed[0].start_index is None
    assert processed[0].end_index is None
    assert processed[0].confidence <= 0.45


def test_suggestion_post_processing_falls_back_to_close_sentence():
    service = SuggestionService()
    text = "PHP 기반 사내 홈페이지 개발 과정에서 계약서 자동 검토 기능을 구현했습니다. OCR 결과를 문서와 연결했습니다."
    processed = service.process(
        [
            CoverLetterSuggestion(
                severity="high",
                category="specificity",
                original_text="PHP 기반 홈페이지 개발에서 계약서 자동 검토 기능을 구현했습니다.",
                issue="구체성 보완",
                reason="원문과 거의 같은 문장을 찾아 적용해야 합니다.",
                suggested_text="PHP 기반 사내 홈페이지 개발 과정에서 계약서 자동 검토 기능과 OCR 정보 추출 흐름을 연결했습니다.",
                apply_type="replace",
                confidence=0.9,
            )
        ],
        text,
    )
    assert len(processed) == 1
    assert processed[0].original_text == "PHP 기반 사내 홈페이지 개발 과정에서 계약서 자동 검토 기능을 구현했습니다."
    assert processed[0].start_index == 0
    assert processed[0].confidence <= 0.74


def test_suggestion_post_processing_uses_start_index_for_duplicate_text():
    service = SuggestionService()
    text = "문서를 정리했습니다. 다른 업무를 했습니다. 문서를 정리했습니다."
    second_index = text.rfind("문서를 정리했습니다.")
    processed = service.process(
        [
            CoverLetterSuggestion(
                severity="medium",
                category="achievement",
                original_text="문서를 정리했습니다.",
                start_index=second_index,
                end_index=second_index + len("문서를 정리했습니다."),
                issue="성과 근거 부족",
                reason="두 번째 문장을 대상으로 잡아야 합니다.",
                suggested_text="문서를 정리하고 [처리 시간/오류 감소율] 기준으로 개선 효과를 확인했습니다.",
                apply_type="replace",
                confidence=0.82,
            )
        ],
        text,
    )
    assert processed[0].start_index == second_index


def test_sentence_review_service_computes_indexes_and_fallbacks():
    service = SentenceReviewService()
    text = (
        "저는 프로젝트를 열심히 수행했습니다. "
        "API 구현과 문서 정리를 맡았습니다. "
        "협업 과정에서 문제를 분석했습니다. "
        "최고의 결과를 만들었습니다. "
        "앞으로도 직무에 기여하고 싶습니다. "
        "테스트와 배포 과정을 정리했습니다."
    )
    processed = service.process(
        [
            SentenceReview(
                sentence_text="API 구현과 문서 정리를 담당했습니다.",
                status="needs_fix",
                category="achievement",
                label="성과 근거 부족",
                comment="결과가 더 필요합니다.",
                suggested_text="API 구현과 문서 정리를 맡아 [기간] 동안 [성과 수치] 기준으로 개선 효과를 정리했습니다.",
                can_apply=True,
                confidence=0.8,
            )
        ],
        text,
        problems=["성과 근거가 부족합니다."],
    )
    assert len(processed) >= 6
    assert processed[0].id == "sent-1"
    assert any(item.start_index is not None for item in processed)
    assert any(item.status in {"needs_fix", "risky"} for item in processed)


def test_sentence_review_service_creates_suggestions_from_reviews():
    service = SentenceReviewService()
    reviews = [
        SentenceReview(
            id="sent-1",
            sentence_text="열심히 수행했습니다.",
            start_index=0,
            end_index=10,
            status="needs_fix",
            category="specificity",
            label="구체성 부족",
            comment="행동이 필요합니다.",
            suggested_text="담당 역할과 실행 행동을 구체적으로 설명했습니다.",
            can_apply=True,
            confidence=0.8,
        )
    ]
    suggestions = service.suggestions_from_sentence_reviews(reviews)
    assert suggestions[0].original_text == "열심히 수행했습니다."
    assert suggestions[0].apply_type == "replace"


def test_sentence_review_service_blocks_instruction_like_suggested_text():
    service = SentenceReviewService()
    text = "저는 새로운 환경에 빠르게 적응하는 개발자입니다. Java와 Python을 학습했고 PHP 기반 사내 홈페이지를 개발했습니다."
    processed = service.process(
        [
            SentenceReview(
                sentence_text="저는 새로운 환경에 빠르게 적응하는 개발자입니다.",
                status="needs_fix",
                category="specificity",
                label="구체성 보완",
                comment="추상적인 문장입니다.",
                suggested_text="이 경험에서 맡은 역할과 사용한 방법, 결과를 [기간]과 [성과 수치] 기준으로 구체화했습니다.",
                can_apply=True,
                confidence=0.8,
            )
        ],
        text,
        problems=[],
    )
    target = processed[0]
    assert target.can_apply is True
    assert "구체화했습니다" not in (target.suggested_text or "")
    assert any(keyword in (target.suggested_text or "") for keyword in ("Java", "Python", "PHP", "사내 홈페이지"))
    assert target.quality_warning


def test_sentence_review_service_marks_placeholder_heavy_text_manual():
    service = SentenceReviewService()
    quality = service.suggested_text_quality_check("저는 [역할]로 [행동]을 수행해 [성과 수치]를 만들었습니다.", "원문")
    assert quality["ok"] is False
    assert "자리표시자" in quality["warning"]


def test_mock_review_includes_suggestions():
    service = AIReviewService()
    result, provider, _model = service.review(
        resume_text="프로젝트 경험과 협업 경험을 포함한 이력서 요약입니다." * 3,
        cover_letter_text="맡은 일을 열심히 수행했습니다. 저는 책임감을 바탕으로 업무를 진행했습니다. 직무에 잘 맞는 인재가 되고 싶습니다.",
        target_job_role="사무직",
        job_posting_text="문서 관리와 일정 조율, 엑셀 활용 역량을 요구합니다.",
        review_mode="strict",
        job_category_preset="사무직",
    )
    assert provider in {"mock", "openai"}
    assert result.suggestions
    assert 3 <= len(result.suggestions) <= 7
    assert result.sentence_reviews
    assert all(item.suggested_text for item in result.suggestions)


def test_long_mock_review_returns_at_least_three_suggestions():
    service = AIReviewService()
    long_cover_letter = (
        "저는 프로젝트를 열심히 수행했습니다. "
        "PHP 기반 사내 홈페이지 개발 과정에서 계약서 자동 검토 기능을 구현했습니다. "
        "OCR 결과를 문서와 연결하고 팀원들과 업무를 정리했습니다. "
        "책임감을 바탕으로 맡은 일을 끝까지 처리했습니다. "
        "앞으로도 배우고 성장하며 직무에 기여하고 싶습니다. "
    ) * 8
    result, provider, _model = service.review(
        resume_text="웹 개발 프로젝트와 협업 경험이 있습니다." * 5,
        cover_letter_text=long_cover_letter,
        target_job_role="웹개발자",
        job_posting_text="PHP, OCR, 전자계약, 데이터 처리, 협업 역량을 요구합니다.",
        review_mode="strict",
        job_category_preset="웹개발자",
    )
    assert provider in {"mock", "openai"}
    assert len(result.suggestions) >= 3
    assert len(result.sentence_reviews) >= 6


def test_mock_review_first_sentence_rewrite_uses_context_keywords():
    service = AIReviewService()
    cover_letter = (
        "저는 새로운 환경에 빠르게 적응하고, 익숙하지 않은 기술도 직접 부딪히며 결과로 연결하는 개발자입니다. "
        "인제대학교에서 Java와 Python으로 프로그래밍 기초를 다졌고 Git을 활용한 협업도 익혔습니다. "
        "실무에서는 PHP를 활용해 사내 홈페이지를 MVC 구조로 개발했고, 계약서 자동 검토 웹서비스에서 OCR 기반 정보 추출과 관리자 기능 구현에 참여했습니다. "
        "현재는 ASP와 MySQL 기반 LMS 운영 및 기능 개선 업무를 담당하고 있습니다. "
        "운영 이슈를 분석하고 수정하며 서비스 개선 경험을 쌓았습니다. "
        "이러한 경험을 바탕으로 안정적인 서비스 운영과 기능 개선에 기여하고 싶습니다."
    )
    result, _provider, _model = service.review(
        resume_text="",
        cover_letter_text=cover_letter,
        target_job_role="웹개발자",
        job_posting_text="",
        review_mode="strict",
    )
    first_fix = next(item for item in result.sentence_reviews if item.status in {"needs_fix", "risky"})
    assert first_fix.suggested_text
    assert "구체화했습니다" not in first_fix.suggested_text
    assert any(keyword in first_fix.suggested_text for keyword in ("Java", "Python", "PHP", "OCR", "MVC", "LMS"))
