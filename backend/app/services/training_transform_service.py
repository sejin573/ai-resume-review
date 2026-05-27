import json

from app.prompts.review_prompts import SCORING_RUBRIC
from app.schemas.review import AIReviewResponse
from app.services.anonymization_service import AnonymizationService


class TrainingTransformService:
    SYSTEM_PROMPT = (
        "You are an expert Korean resume and cover letter coach. "
        "You provide strict, practical, job-relevant feedback."
    )

    def __init__(self) -> None:
        self.anonymizer = AnonymizationService()

    def transform_accepted_cover_letter(
        self,
        *,
        data_source_id: int,
        source_type: str,
        job_role: str,
        accepted_cover_letter: str,
        job_keywords: list[str] | None = None,
        resume_summary: str | None = None,
        contains_real_user_data: bool,
    ) -> dict:
        sanitized_cover_letter = self.anonymizer.anonymize_text(accepted_cover_letter)
        sanitized_keywords = [self.anonymizer.anonymize_text(item) for item in (job_keywords or [])]
        sanitized_resume_summary = self.anonymizer.anonymize_text(resume_summary or "")
        review_json = self._build_realistic_review(
            job_role=job_role,
            accepted_cover_letter=sanitized_cover_letter,
            job_keywords=sanitized_keywords,
        )
        user_content = f"지원 직무: {job_role}\n채용 키워드: {', '.join(sanitized_keywords)}\n자기소개서 원문: {sanitized_cover_letter}"
        if sanitized_resume_summary:
            user_content += f"\n이력서 요약: {sanitized_resume_summary}"
        return {
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": json.dumps(review_json, ensure_ascii=False)},
            ],
            "metadata": {
                "job_role": job_role,
                "data_source_id": str(data_source_id),
                "source_type": source_type,
                "quality_status": "draft",
                "reviewed_by_human": False,
                "contains_real_user_data": contains_real_user_data,
            },
        }

    def _build_realistic_review(self, *, job_role: str, accepted_cover_letter: str, job_keywords: list[str]) -> dict:
        text_length = len(accepted_cover_letter)
        keyword_hits = sum(1 for keyword in job_keywords if keyword and keyword in accepted_cover_letter)
        keyword_total = max(1, len(job_keywords))
        keyword_score = min(96, 70 + round((keyword_hits / keyword_total) * 20))
        specificity = 78 if text_length > 300 else 70
        achievement = 76 if any(token in accepted_cover_letter for token in ["%", "명", "건", "배", "향상", "개선"]) else 68
        writing_quality = 84 if text_length > 250 else 76
        structure = 82 if "\n" in accepted_cover_letter or "첫" in accepted_cover_letter else 75
        uniqueness = 79
        job_fit = 80
        scores = {
            "job_fit": job_fit,
            "specificity": specificity,
            "achievement": achievement,
            "writing_quality": writing_quality,
            "uniqueness": uniqueness,
            "structure": structure,
            "keyword_match": keyword_score,
        }
        total_score = round(sum(scores[key] * SCORING_RUBRIC[key]["weight"] for key in scores), 1)
        improved_cover_letter = self._polish_cover_letter(job_role=job_role, cover_letter=accepted_cover_letter, job_keywords=job_keywords)
        payload = {
            "total_score": total_score,
            "scores": scores,
            "summary": f"{job_role} 기준으로 기본 경쟁력은 갖췄지만, 성과 근거와 직무 키워드 연결을 조금만 더 명확히 하면 완성도가 더 올라갑니다.",
            "problems": [
                "전체적으로 우수하지만 일부 문장은 성과 근거가 약해 설득력이 다소 떨어집니다.",
                "강점이 잘 드러나지만 채용 키워드와 직접 연결되는 문장이 더 있으면 좋습니다.",
                "문단 간 전환을 조금 더 분명히 하면 메시지 집중도가 높아집니다.",
            ],
            "improvement_strategy": [
                "강점 문장 뒤에 실제 결과나 수치를 한 줄씩 덧붙여 근거를 강화합니다.",
                "채용 키워드를 문장 속 행동과 결과에 직접 연결해 직무 적합도를 높입니다.",
                "지원 동기, 핵심 사례, 입사 후 기여를 각각 분리해 문단 구조를 더 선명하게 만듭니다.",
            ],
            "improved_cover_letter": improved_cover_letter,
            "interview_questions": [
                "이 자기소개서에서 가장 강조한 경험을 실제 수치와 함께 설명해 주세요.",
                "직무 키워드 중 본인이 가장 강하게 증명할 수 있는 항목은 무엇인가요?",
                "현재 문안에서 더 보완하고 싶은 부분이 있다면 무엇인가요?",
            ],
            "missing_keywords": [keyword for keyword in job_keywords if keyword and keyword not in accepted_cover_letter][:5],
            "strengths": [
                "핵심 경험의 방향성이 직무와 비교적 잘 맞습니다.",
                "문장 톤이 전반적으로 안정적이고 전문적입니다.",
                "지원자의 기본 스토리가 일관되게 유지됩니다.",
            ],
        }
        return AIReviewResponse.model_validate(payload).model_dump()

    def _polish_cover_letter(self, *, job_role: str, cover_letter: str, job_keywords: list[str]) -> str:
        keywords_fragment = ", ".join(job_keywords[:4]) if job_keywords else "직무 핵심 역량"
        return (
            f"저는 {job_role}에 필요한 {keywords_fragment}을 실제 경험으로 연결해 설명할 수 있는 지원자입니다. "
            f"{cover_letter[:260].strip()} "
            "원문이 가진 경험의 흐름은 유지하되, 각 문장에서 맡은 역할과 결과를 더 분명히 드러내도록 정리했습니다."
        ).strip()
