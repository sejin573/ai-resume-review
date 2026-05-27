REVIEW_PROMPT_VERSION = "coverfit-review-v2"
REFINE_PROMPT_VERSION = "coverfit-refine-v2"

REVIEW_MODE_GUIDANCE = {
    "quick": {
        "label": "quick",
        "instruction": (
            "핵심만 빠르게 진단합니다. 점수와 요약은 유지하되 문제점은 상위 3개 중심으로 간결하게 작성하고, "
            "개선문은 지나치게 길지 않게 정리합니다."
        ),
    },
    "detailed": {
        "label": "detailed",
        "instruction": (
            "균형 잡힌 기본 모드입니다. 강점과 보완점을 모두 설명하고, 지원 직무와 채용공고 연결성을 충분히 다룹니다."
        ),
    },
    "strict": {
        "label": "strict",
        "instruction": (
            "더 엄격하게 평가합니다. 근거가 약하면 점수를 낮게 주고, 추상적 표현과 클리셰를 분명히 지적합니다. "
            "막연한 칭찬은 피하고 제출 전 보완이 필요한 부분을 직접적으로 알려줍니다."
        ),
    },
    "rewrite-focused": {
        "label": "rewrite-focused",
        "instruction": (
            "개선문 완성도를 가장 중요하게 봅니다. 기존 경험을 유지하면서 제출용 문안으로 다듬되, "
            "허위 성과나 없는 자격을 만들지 않습니다."
        ),
    },
}

JOB_CATEGORY_PRESETS = {
    "웹개발자": {
        "core": ["문제 해결", "협업", "API/데이터 흐름 이해", "서비스 개선", "기술 스택 적합성"],
        "watchouts": ["기술 나열만 하고 기여도가 보이지 않는 문장", "프로젝트 결과가 없는 설명"],
    },
    "사무직": {
        "core": ["정확성", "문서 처리", "일정 관리", "협업 커뮤니케이션", "업무 우선순위 조정"],
        "watchouts": ["성실성만 반복하고 실제 업무 성과가 없는 문장", "도구 활용 경험이 빠진 설명"],
    },
    "교육행정": {
        "core": ["행정 정확성", "민원 대응", "운영 지원", "데이터 관리", "교육 현장 이해"],
        "watchouts": ["봉사 경험을 행정 역량과 연결하지 못한 문장", "규정/운영 경험 부재"],
    },
    "마케팅": {
        "core": ["타깃 이해", "콘텐츠 실행", "성과 지표", "실험과 개선", "브랜드 메시지 정리"],
        "watchouts": ["감각적 표현만 있고 수치/성과가 없는 문장", "채널별 전략 차이가 없는 설명"],
    },
    "사회복지사": {
        "core": ["대상자 이해", "사례 관리", "기록 정확성", "관계 형성", "협업 및 연계"],
        "watchouts": ["좋은 마음만 강조하고 실무 대응 경험이 없는 문장", "성과와 개입 과정이 없는 설명"],
    },
}

# Score weights are intentionally conservative. We do not want vague drafts to cluster near 80+.
SCORING_RUBRIC = {
    "job_fit": {
        "label": "직무 적합도",
        "weight": 0.20,
        "description": "지원 직무와 경험 연결성이 명확한가. 직무 역량 언어를 이해하고 있는가.",
    },
    "specificity": {
        "label": "경험의 구체성",
        "weight": 0.14,
        "description": "상황, 역할, 행동, 결과가 드러나는가. 추상적 표현에 머물지 않는가.",
    },
    "achievement": {
        "label": "성과/수치 표현",
        "weight": 0.14,
        "description": "성과 근거, 수치, 기간, 빈도, 개선 결과가 제시되는가.",
    },
    "writing_quality": {
        "label": "문장력",
        "weight": 0.12,
        "description": "문장이 자연스럽고 읽기 쉬운가. 과장되거나 어색한 표현이 적은가.",
    },
    "uniqueness": {
        "label": "차별성",
        "weight": 0.12,
        "description": "남들도 쓸 수 있는 표현을 넘어 지원자만의 구체적 경험과 관점이 있는가.",
    },
    "structure": {
        "label": "논리 구조",
        "weight": 0.14,
        "description": "문단 흐름이 자연스럽고 경험 구조가 정리되어 있는가.",
    },
    "keyword_match": {
        "label": "채용공고 키워드 반영",
        "weight": 0.14,
        "description": "채용공고 핵심 키워드와 요구 역량이 실제 문장에 반영되어 있는가.",
    },
}


def normalize_review_mode(review_mode: str) -> str:
    aliases = {
        "rewrite_focused": "rewrite-focused",
        "rewrite-focused": "rewrite-focused",
    }
    return aliases.get(review_mode, review_mode)


def _format_rubric() -> str:
    return "\n".join(
        f"- {key} ({config['label']}, weight={config['weight']}): {config['description']}"
        for key, config in SCORING_RUBRIC.items()
    )


def _format_preset(job_category_preset: str | None) -> str:
    if not job_category_preset:
        return "- 직군 프리셋 없음"
    preset = JOB_CATEGORY_PRESETS.get(job_category_preset)
    if not preset:
        return f"- 직군 프리셋: {job_category_preset} (사전 정의 없음)"
    core = ", ".join(preset["core"])
    watchouts = ", ".join(preset["watchouts"])
    return (
        f"- 직군 프리셋: {job_category_preset}\n"
        f"- 특히 볼 역량: {core}\n"
        f"- 흔한 약점: {watchouts}"
    )


def _mode_instruction(review_mode: str) -> str:
    normalized = normalize_review_mode(review_mode)
    return REVIEW_MODE_GUIDANCE.get(normalized, REVIEW_MODE_GUIDANCE["detailed"])["instruction"]


def _field_or_placeholder(value: str, empty_message: str) -> str:
    cleaned = (value or "").strip()
    return cleaned if cleaned else empty_message


def build_job_posting_analysis_messages(
    *,
    target_job_role: str,
    job_posting_text: str,
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are a Korean recruiting analyst. Analyze the job posting and return valid JSON only. "
                "Be conservative when the posting is short or vague. "
                "Schema: "
                '{"job_keywords": string[], "required_competencies": string[], '
                '"preferred_experiences": string[], "tone_hint": string, "risk_notes": string[]}'
            ),
        },
        {
            "role": "user",
            "content": (
                f"지원 직무: {_field_or_placeholder(target_job_role, '(미입력 - 일반적 직무 기준으로 해석)')}\n"
                f"채용공고:\n{_field_or_placeholder(job_posting_text, '(미입력 - 채용공고 기반 키워드 분석 제한)')}\n\n"
                "지침:\n"
                "- 채용공고에 실제로 드러난 키워드만 뽑으세요.\n"
                "- 채용공고가 없으면 risk_notes에 '채용공고 미입력으로 키워드 분석 제한'을 반드시 적으세요.\n"
                "- 추론이 필요한 경우 risk_notes에 적으세요.\n"
                "- tone_hint는 조직이 선호할 가능성이 있는 문장 톤을 한국어로 한 문장으로 설명하세요."
            ),
        },
    ]


def build_cover_letter_diagnosis_messages(
    *,
    target_job_role: str,
    resume_text: str,
    cover_letter_text: str,
    job_posting_analysis: dict,
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are a Korean career consultant. Diagnose a resume and cover letter pair and return valid JSON only. "
                "Focus on what is missing, vague, unsupported, or overly generic. "
                "Schema: "
                '{"core_experiences": string[], "weak_points": string[], "missing_evidence": string[], '
                '"overused_expressions": string[], "job_fit_notes": string[], "recommended_structure": string[]}'
            ),
        },
        {
            "role": "user",
            "content": (
                f"지원 직무: {_field_or_placeholder(target_job_role, '(미입력 - 자기소개서 내용 중심으로 해석)')}\n"
                f"이력서/경험 요약:\n{_field_or_placeholder(resume_text, '(미입력 - 자기소개서 내부 근거만으로 진단)')}\n\n"
                f"자기소개서 원문:\n{cover_letter_text}\n\n"
                f"채용공고 분석:\n{job_posting_analysis}\n\n"
                "지침:\n"
                "- 이력서가 없으면 자기소개서 내부 근거만으로 보수적으로 판단하세요.\n"
                "- core_experiences에는 실제로 활용 가능한 경험 축만 남기세요.\n"
                "- weak_points에는 제출용 문안으로 약한 지점을 직접적으로 적으세요.\n"
                "- missing_evidence에는 수치, 기간, 역할, 결과 등 빠진 근거를 적으세요.\n"
                "- overused_expressions에는 흔한 클리셰 표현만 적으세요.\n"
                "- recommended_structure는 STAR 흐름과 직무 연결성을 반영하세요."
            ),
        },
    ]


def build_review_messages(
    *,
    resume_text: str,
    cover_letter_text: str,
    target_job_role: str,
    job_posting_text: str,
    review_mode: str,
    job_category_preset: str | None,
    job_posting_analysis: dict,
    diagnosis: dict,
) -> list[dict[str, str]]:
    normalized_mode = normalize_review_mode(review_mode)
    return [
        {
            "role": "system",
            "content": (
                "You are an expert Korean resume and cover letter coach for job seekers. "
                "You are strict, practical, and job-relevant. Avoid empty praise. "
                "Do not invent company names, certificates, achievements, numbers, or experiences. "
                "If evidence is missing, use placeholders like [기간], [성과 수치], [횟수] instead of fabricating facts. "
                "Write like a Korean career consultant. Return valid JSON only."
            ),
        },
        {
            "role": "user",
            "content": (
                f"prompt_version: {REVIEW_PROMPT_VERSION}\n"
                f"review_mode: {normalized_mode}\n"
                f"mode_guidance: {_mode_instruction(normalized_mode)}\n"
                f"{_format_preset(job_category_preset)}\n\n"
                "채점 기준:\n"
                f"{_format_rubric()}\n\n"
                "점수 규칙:\n"
                "- 추상적이고 근거가 약한 자기소개서는 65점 미만으로 평가하세요.\n"
                "- 괜찮지만 일반적인 자기소개서는 65~78 범위에 두세요.\n"
                "- 직무와 강하게 연결되고 근거가 분명한 문안만 79~90을 주세요.\n"
                "- 90점 초과는 예외적으로 매우 구체적이고 설득력 있는 경우에만 허용하세요.\n"
                "- 채용공고가 약하거나 없으면 keyword_match를 보수적으로 주세요.\n"
                "- 지원 직무가 비어 있으면 일반적인 제출용 자기소개서 기준으로 평가하되, 직무 적합도는 보수적으로 주세요.\n"
                "- 이력서가 비어 있으면 자기소개서 안에서 확인 가능한 근거만 사용하세요.\n"
                "- 성과 수치나 결과가 없으면 achievement를 낮게 주세요.\n"
                "- 너무 짧으면 specificity와 structure를 낮게 주세요.\n"
                "- 과장되거나 허세가 느껴지면 writing_quality와 uniqueness를 낮게 주세요.\n\n"
                f"지원 직무: {_field_or_placeholder(target_job_role, '(미입력)')}\n"
                f"채용공고:\n{_field_or_placeholder(job_posting_text, '(미입력 - 채용공고 기준 분석 제한)')}\n\n"
                f"이력서/경험 요약:\n{_field_or_placeholder(resume_text, '(미입력 - 자기소개서 단독 분석)')}\n\n"
                f"자기소개서 원문:\n{cover_letter_text}\n\n"
                f"채용공고 분석:\n{job_posting_analysis}\n\n"
                f"자기소개서 진단:\n{diagnosis}\n\n"
                "출력 스키마:\n"
                "{\n"
                '  "total_score": number,\n'
                '  "scores": {\n'
                '    "job_fit": number,\n'
                '    "specificity": number,\n'
                '    "achievement": number,\n'
                '    "writing_quality": number,\n'
                '    "uniqueness": number,\n'
                '    "structure": number,\n'
                '    "keyword_match": number\n'
                "  },\n"
                '  "summary": string,\n'
                '  "problems": string[],\n'
                '  "improvement_strategy": string[],\n'
                '  "improved_cover_letter": string,\n'
                '  "interview_questions": string[],\n'
                '  "missing_keywords": string[],\n'
                '  "strengths": string[],\n'
                '  "job_keywords": string[],\n'
                '  "rewritten_structure": string[],\n'
                '  "evidence_suggestions": string[],\n'
                '  "ats_keyword_notes": string[],\n'
                '  "final_review_checklist": string[],\n'
                '  "suggestions": [{"id": string, "severity": "low"|"medium"|"high", "category": "job_fit"|"specificity"|"achievement"|"writing_quality"|"structure"|"keyword_match"|"tone"|"redundancy", "original_text": string, "start_index": number|null, "end_index": number|null, "issue": string, "reason": string, "suggested_text": string, "apply_type": "replace"|"append_after"|"rewrite_paragraph", "confidence": number}],\n'
                '  "sentence_reviews": [{"id": string, "sentence_text": string, "start_index": number|null, "end_index": number|null, "status": "good"|"okay"|"needs_fix"|"risky", "category": "job_fit"|"specificity"|"achievement"|"writing_quality"|"structure"|"keyword_match"|"tone"|"redundancy"|"clarity", "label": string, "good_point": string|null, "comment": string, "suggested_text": string|null, "can_apply": boolean, "context_before": string|null, "context_after": string|null, "edit_type": "replace_sentence"|"rewrite_with_context"|"merge_with_next"|"split_sentence"|"add_evidence_after", "expected_effect": string|null, "quality_warning": string|null, "confidence": number}]\n'
                "}\n\n"
                "작성 지침:\n"
                "- summary는 한 문단으로 작성하되, 현재 수준과 우선 보완점을 분명히 적으세요.\n"
                "- problems는 왜 문제인지 바로 보이게 작성하세요.\n"
                "- improvement_strategy는 실제 수정 방향이 보이도록 예시 수준으로 구체화하세요.\n"
                "- improved_cover_letter는 STAR 흐름을 참고하되 문단 라벨을 기계적으로 붙이지 말고 자연스럽게 쓰세요.\n"
                "- strengths도 근거 기반으로만 적으세요.\n"
                "- 면접 질문은 자기소개서의 주장 검증과 직무 연결성 확인에 도움이 되게 만드세요.\n"
                "- suggestions는 보통 4개 이상 7개 이하를 목표로 작성하세요. 자기소개서가 500자 이상이면 최소 4개 후보를 검토하세요.\n"
                "- 문안이 매우 좋거나 짧으면 1~3개만 작성해도 되지만, 일반적인 초안은 4~6개가 적당합니다.\n"
                "- suggestions.original_text는 사용자의 원문 cover_letter_text에서 정확히 복사 가능한 1~2문장 단위로 작성하세요. 긴 문단 전체를 잡지 마세요.\n"
                "- category는 specificity, achievement, job_fit, structure, writing_quality, keyword_match, tone, redundancy 중에서 가능한 한 다양하게 고르세요.\n"
                "- 모든 문장을 고치려 하지 말고, 영향이 큰 문장만 고르세요.\n"
                "- suggested_text는 원문에 있는 기술명, 경험명, 역할, 도구를 최대한 보존해 자연스럽게 다시 쓰세요.\n"
                "- suggested_text는 전체가 자리표시자만으로 보이면 안 됩니다. 없는 숫자나 검증 불가능한 성과만 [기간], [성과 수치], [횟수], [규모], [도구] 같은 자리표시자로 남기세요.\n"
                "- suggested_text는 직무와 연결되는 문장으로 마무리하되, 면접에서 설명 가능한 수준으로만 쓰고 과장하지 마세요.\n"
                "- suggested_text는 첨삭 설명이나 작성 지시가 아니라 실제 자기소개서에 그대로 들어갈 수 있는 대체 문장이어야 합니다.\n"
                "- '이 경험에서 ~ 구체화했습니다', '~을 추가해 주세요', '~를 작성하세요', '~을 보완하세요' 같은 지시문형 표현은 절대 suggested_text에 쓰지 마세요.\n"
                "- 첫 문장이나 추상적인 주제문은 뒤 문단의 실제 경험 키워드(Java, Python, Git, PHP, MVC, OCR, 관리자 기능, LMS 운영 등 원문에 있는 사실)와 자연스럽게 연결해 쓰세요.\n"
                "- suggested_text는 가능한 한 original_text 주변 문단에서 나온 구체 키워드 1~3개를 자연스럽게 포함하되, 원문에 없는 사실은 만들지 마세요.\n"
                "- reason은 짧고 실무적으로 쓰세요.\n"
                "- sentence_reviews는 자기소개서 전체를 문장 단위로 읽은 첨삭 기록입니다. 최소 6개 이상을 목표로 하되, 짧은 문안은 가능한 문장 수만큼 작성하세요.\n"
                "- 긴 자기소개서는 핵심 문장 8~12개를 반환하세요. 모든 문장을 나쁘게 평가하지 말고 good, okay, needs_fix, risky를 섞어 평가하세요.\n"
                "- 좋은 문장에는 good_point를 작성하고 suggested_text는 null, can_apply는 false로 두세요.\n"
                "- 보완 문장에는 comment와 바로 교체 가능한 suggested_text를 작성하고 can_apply는 true로 두세요.\n"
                "- sentence_reviews.sentence_text는 원문 cover_letter_text에서 정확히 복사 가능한 한 문장이어야 합니다.\n"
                "- sentence_reviews의 needs_fix/risky 항목은 기존 suggestions 생성의 근거로 사용해도 됩니다.\n"
                "- sentence_reviews는 original 문장만 보지 말고 context_before/context_after에 앞뒤 문장 또는 주변 문맥을 넣고, 그 문맥을 반영해 suggested_text를 작성하세요.\n"
                "- edit_type은 교체 방식에 맞게 선택하세요. 한 문장 교체는 replace_sentence, 앞뒤 문맥까지 자연스럽게 다시 쓰면 rewrite_with_context, 다음 문장과 합치면 merge_with_next, 긴 문장을 나누면 split_sentence, 근거 문장을 뒤에 더하면 add_evidence_after입니다.\n"
                "- expected_effect에는 이 수정으로 좋아지는 점을 짧게 쓰세요.\n"
                "- JSON 외의 텍스트를 절대 출력하지 마세요."
            ),
        },
    ]


def build_refinement_messages(
    *,
    instruction: str,
    current_text: str,
    target_job_role: str,
    job_posting_text: str,
) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You are an expert Korean cover letter coach. Follow the user's rewrite instruction while preserving "
                "the current text's core story. Do not invent achievements, organizations, certificates, or numbers. "
                "If more detail is needed but facts are missing, use placeholders like [기간], [성과 수치], [횟수]. "
                f"Return valid JSON only. prompt_version={REFINE_PROMPT_VERSION}. "
                'Schema: {"refined_text": string, "change_summary": string, "warnings": string[]}'
            ),
        },
        {
            "role": "user",
            "content": (
                f"지원 직무: {target_job_role}\n"
                f"채용공고:\n{_field_or_placeholder(job_posting_text, '(미입력 - 일반적 문장 개선 기준 적용)')}\n\n"
                f"현재 문안:\n{current_text}\n\n"
                f"수정 지시: {instruction}\n\n"
                "세부 지침:\n"
                "- '더 구체적으로'면 역할/행동/결과를 보이게 하되 근거 없는 숫자는 만들지 마세요.\n"
                "- '성과 중심으로'면 측정 가능한 결과를 강조하되 없으면 [성과 수치] 자리를 남기세요.\n"
                "- '자연스럽게'면 어색한 한국어와 군더더기를 줄이세요.\n"
                "- '신입답게'면 과도하게 고연차처럼 보이는 표현을 낮추세요.\n"
                "- '700자로 줄이기'면 핵심 경험과 직무 연결성만 남기고 압축하세요.\n"
                "- '면접에서 설명하기 쉽게'면 방어 가능한 표현으로 다듬으세요.\n"
                "- '과장 줄이기'면 단정적이거나 과도한 표현을 줄이세요.\n"
                "- change_summary에는 무엇을 어떻게 바꿨는지 한두 문장으로 적으세요.\n"
                "- warnings에는 과장 위험, 근거 부족, 숫자 보강 필요 같은 경고를 넣으세요."
            ),
        },
    ]


def build_final_quality_check_messages(*, raw_json: str) -> list[dict[str, str]]:
    return [
        {
            "role": "system",
            "content": (
                "You repair malformed JSON outputs for a Korean cover letter review service. "
                "Return valid JSON only. Do not add markdown fences or explanations."
            ),
        },
        {
            "role": "user",
            "content": (
                "아래 출력은 JSON 형식이 깨졌거나 일부 필드가 비어 있습니다. "
                "동일한 의미를 유지하면서 아래 스키마에 맞는 유효한 JSON 객체만 다시 작성하세요.\n\n"
                f"원본 출력:\n{raw_json}\n\n"
                "필수 스키마:\n"
                '{"total_score": number, "scores": {"job_fit": number, "specificity": number, "achievement": number, '
                '"writing_quality": number, "uniqueness": number, "structure": number, "keyword_match": number}, '
                '"summary": string, "problems": string[], "improvement_strategy": string[], '
                '"improved_cover_letter": string, "interview_questions": string[], "missing_keywords": string[], '
                '"strengths": string[], "job_keywords": string[], "rewritten_structure": string[], '
                '"evidence_suggestions": string[], "ats_keyword_notes": string[], "final_review_checklist": string[], '
                '"suggestions": [{"id": string, "severity": "low"|"medium"|"high", '
                '"category": "job_fit"|"specificity"|"achievement"|"writing_quality"|"structure"|"keyword_match"|"tone"|"redundancy", '
                '"original_text": string, "start_index": number|null, "end_index": number|null, '
                '"issue": string, "reason": string, "suggested_text": string, '
                '"apply_type": "replace"|"append_after"|"rewrite_paragraph", "confidence": number}], '
                '"sentence_reviews": [{"id": string, "sentence_text": string, "start_index": number|null, "end_index": number|null, '
                '"status": "good"|"okay"|"needs_fix"|"risky", '
                '"category": "job_fit"|"specificity"|"achievement"|"writing_quality"|"structure"|"keyword_match"|"tone"|"redundancy"|"clarity", '
                '"label": string, "good_point": string|null, "comment": string, "suggested_text": string|null, '
                '"can_apply": boolean, "context_before": string|null, "context_after": string|null, '
                '"edit_type": "replace_sentence"|"rewrite_with_context"|"merge_with_next"|"split_sentence"|"add_evidence_after", '
                '"expected_effect": string|null, "quality_warning": string|null, "confidence": number}]}'
                "\n\n"
                "repair 규칙:\n"
                "- 원본 출력에 suggestions가 있으면 가능한 한 보존하세요.\n"
                "- 원본 출력에 sentence_reviews가 있으면 가능한 한 보존하세요.\n"
                "- suggestions가 없거나 복구할 수 없으면 빈 배열을 사용하세요.\n"
                "- sentence_reviews가 없거나 복구할 수 없으면 빈 배열을 사용하세요.\n"
                "- suggestions.original_text는 사용자의 원문 cover_letter_text에서 온 정확한 문장이어야 합니다.\n"
                "- sentence_reviews.sentence_text는 사용자의 원문 cover_letter_text에서 온 정확한 문장이어야 합니다.\n"
                "- JSON 외의 텍스트를 절대 출력하지 마세요."
            ),
        },
    ]
