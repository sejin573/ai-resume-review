from app.services.review_parser import ReviewResponseParser
from app.prompts.review_prompts import build_final_quality_check_messages


def test_parser_accepts_fenced_json():
    parser = ReviewResponseParser()
    raw = """
    ```json
    {
      "total_score": 81,
      "scores": {
        "job_fit": 80,
        "specificity": 78,
        "achievement": 76,
        "writing_quality": 83,
        "uniqueness": 79,
        "structure": 84,
        "keyword_match": 82
      },
      "summary": "강점과 약점이 함께 보입니다.",
      "problems": ["성과 수치 부족"],
      "improvement_strategy": ["성과를 수치화합니다."],
      "improved_cover_letter": "개선 문안",
      "interview_questions": ["성과를 어떻게 검증할 수 있나요?"],
      "missing_keywords": ["성과 지표"],
      "strengths": ["직무 연결 의도는 보입니다."]
    }
    ```
    """
    parsed = parser.parse(raw)
    assert parsed.total_score == 81
    assert parsed.scores.keyword_match == 82


def test_parser_repairs_trailing_comma_and_string_lists():
    parser = ReviewResponseParser()
    raw = """
    안내 문구
    {
      "scores": {
        "job_fit": 70,
        "specificity": 68,
        "achievement": 64,
        "writing_quality": 75,
        "uniqueness": 66,
        "structure": 71,
        "keyword_match": 69,
      },
      "summary": "약점이 더 큽니다.",
      "problems": "수치가 부족함; 키워드 연결 부족",
      "improvement_strategy": "성과 수치를 추가함\\n직무 키워드 문장 삽입",
      "improved_cover_letter": "개선 문안",
      "interview_questions": "가장 큰 성과는 무엇인가요?",
      "missing_keywords": "성과 지표\\n직무 키워드",
      "strengths": "지원 의도는 드러남"
    }
    """
    parsed = parser.parse(raw)
    assert parsed.total_score > 0
    assert len(parsed.problems) == 2
    assert "직무 키워드" in parsed.missing_keywords


def test_parser_computes_total_when_missing():
    parser = ReviewResponseParser()
    raw = """
    {
      "scores": {
        "job_fit": 80,
        "specificity": 70,
        "achievement": 60,
        "writing_quality": 90,
        "uniqueness": 75,
        "structure": 85,
        "keyword_match": 65
      },
      "summary": "요약",
      "problems": ["문제"],
      "improvement_strategy": ["개선"],
      "improved_cover_letter": "문안",
      "interview_questions": ["질문"],
      "missing_keywords": ["키워드"],
      "strengths": ["강점"]
    }
    """
    parsed = parser.parse(raw)
    assert parsed.total_score == parser.compute_total_score(parsed.scores.model_dump())


def test_final_quality_repair_prompt_preserves_suggestions_schema():
    messages = build_final_quality_check_messages(raw_json="{}")
    content = messages[1]["content"]
    assert '"suggestions"' in content
    assert '"sentence_reviews"' in content
    assert '"original_text": string' in content
    assert '"sentence_text": string' in content
    assert '"apply_type": "replace"|"append_after"|"rewrite_paragraph"' in content
    assert "suggestions가 없거나 복구할 수 없으면 빈 배열" in content
    assert "sentence_reviews가 없거나 복구할 수 없으면 빈 배열" in content
