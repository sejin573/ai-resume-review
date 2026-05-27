import json
import re
from typing import Any

from openai import OpenAI

from app.core.config import settings
from app.prompts import (
    REFINE_PROMPT_VERSION,
    REVIEW_PROMPT_VERSION,
    SCORING_RUBRIC,
    build_cover_letter_diagnosis_messages,
    build_final_quality_check_messages,
    build_job_posting_analysis_messages,
    build_refinement_messages,
    build_review_messages,
    normalize_review_mode,
)
from app.schemas.review import (
    AIReviewResponse,
    CoverLetterDiagnosisResult,
    JobPostingAnalysisResult,
    ReviewRefinementResponse,
)
from app.services.review_parser import ReviewResponseParser
from app.services.sentence_review_service import SentenceReviewService
from app.services.suggestion_service import SuggestionService

REVIEW_PIPELINE_VERSION = "coverfit-pipeline-v2"


class AIReviewService:
    def __init__(self) -> None:
        self.api_key = settings.openai_api_key
        self.model = settings.openai_model
        self.use_mock = settings.mock_ai_mode or not self.api_key
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
        self.parser = ReviewResponseParser()
        self.suggestion_service = SuggestionService()
        self.sentence_review_service = SentenceReviewService()
        self.last_review_metadata = self._build_metadata(
            provider_name="mock",
            model_name="mock-v1",
            prompt_version=REVIEW_PROMPT_VERSION,
            pipeline_version=REVIEW_PIPELINE_VERSION,
        )
        self.last_refine_metadata = self._build_metadata(
            provider_name="mock",
            model_name="mock-v1",
            prompt_version=REFINE_PROMPT_VERSION,
            pipeline_version=REVIEW_PIPELINE_VERSION,
        )

    def review(
        self,
        resume_text: str,
        cover_letter_text: str,
        target_job_role: str,
        job_posting_text: str,
        review_mode: str = "detailed",
        job_category_preset: str | None = None,
    ) -> tuple[AIReviewResponse, str, str]:
        normalized_mode = normalize_review_mode(review_mode)
        if self.use_mock or not self.client:
            job_posting_analysis = self._mock_job_posting_analysis(
                target_job_role=target_job_role,
                job_posting_text=job_posting_text,
            )
            diagnosis = self._mock_cover_letter_diagnosis(
                target_job_role=target_job_role,
                resume_text=resume_text,
                cover_letter_text=cover_letter_text,
                job_posting_analysis=job_posting_analysis,
            )
            response = self._mock_response(
                resume_text=resume_text,
                cover_letter_text=cover_letter_text,
                target_job_role=target_job_role,
                job_posting_text=job_posting_text,
                review_mode=normalized_mode,
                job_posting_analysis=job_posting_analysis,
                diagnosis=diagnosis,
            )
            response = self._attach_processed_review_details(response, cover_letter_text)
            self.last_review_metadata = self._build_metadata(
                provider_name="mock",
                model_name="mock-v2",
                prompt_version=REVIEW_PROMPT_VERSION,
                pipeline_version=REVIEW_PIPELINE_VERSION,
            )
            return response, "mock", "mock-v2"

        provider_name = "openai"
        model_name = self.model
        job_posting_analysis = self._analyze_job_posting(target_job_role=target_job_role, job_posting_text=job_posting_text)
        diagnosis = self._diagnose_cover_letter(
            target_job_role=target_job_role,
            resume_text=resume_text,
            cover_letter_text=cover_letter_text,
            job_posting_analysis=job_posting_analysis,
        )
        messages = build_review_messages(
            resume_text=resume_text,
            cover_letter_text=cover_letter_text,
            target_job_role=target_job_role,
            job_posting_text=job_posting_text,
            review_mode=normalized_mode,
            job_category_preset=job_category_preset,
            job_posting_analysis=job_posting_analysis.model_dump(),
            diagnosis=diagnosis.model_dump(),
        )
        raw_content = self._call_structured_json(messages, temperature=0.15)
        parsed = self._validate_response_with_retry(raw_content)
        parsed = self._attach_processed_review_details(parsed, cover_letter_text)
        self.last_review_metadata = self._build_metadata(
            provider_name=provider_name,
            model_name=model_name,
            prompt_version=REVIEW_PROMPT_VERSION,
            pipeline_version=REVIEW_PIPELINE_VERSION,
        )
        return parsed, provider_name, model_name

    def scoring_rubric(self) -> dict:
        return SCORING_RUBRIC

    def refine_cover_letter(
        self,
        *,
        instruction: str,
        current_text: str,
        target_job_role: str,
        job_posting_text: str,
    ) -> tuple[ReviewRefinementResponse, str, str]:
        if self.use_mock or not self.client:
            response = self._mock_refinement(
                instruction=instruction,
                current_text=current_text,
                target_job_role=target_job_role,
                job_posting_text=job_posting_text,
            )
            self.last_refine_metadata = self._build_metadata(
                provider_name="mock",
                model_name="mock-v2",
                prompt_version=REFINE_PROMPT_VERSION,
                pipeline_version=REVIEW_PIPELINE_VERSION,
            )
            return response, "mock", "mock-v2"

        raw_content = self._call_structured_json(
            build_refinement_messages(
                instruction=instruction,
                current_text=current_text,
                target_job_role=target_job_role,
                job_posting_text=job_posting_text,
            ),
            temperature=0.25,
        )
        try:
            parsed = self.parser.parse_refinement(raw_content)
        except ValueError:
            repair_messages = [
                {
                    "role": "system",
                    "content": "Return valid JSON only with refined_text, change_summary, warnings.",
                },
                {
                    "role": "user",
                    "content": f"Fix this output into valid JSON only:\n{raw_content}",
                },
            ]
            repaired = self._call_structured_json(repair_messages, temperature=0.0)
            parsed = self.parser.parse_refinement(repaired)

        self.last_refine_metadata = self._build_metadata(
            provider_name="openai",
            model_name=self.model,
            prompt_version=REFINE_PROMPT_VERSION,
            pipeline_version=REVIEW_PIPELINE_VERSION,
        )
        return parsed, "openai", self.model

    def _analyze_job_posting(self, *, target_job_role: str, job_posting_text: str) -> JobPostingAnalysisResult:
        raw = self._call_structured_json(
            build_job_posting_analysis_messages(
                target_job_role=target_job_role,
                job_posting_text=job_posting_text,
            ),
            temperature=0.0,
        )
        payload = self._parse_generic_json(raw)
        return JobPostingAnalysisResult.model_validate(payload)

    def _diagnose_cover_letter(
        self,
        *,
        target_job_role: str,
        resume_text: str,
        cover_letter_text: str,
        job_posting_analysis: JobPostingAnalysisResult,
    ) -> CoverLetterDiagnosisResult:
        raw = self._call_structured_json(
            build_cover_letter_diagnosis_messages(
                target_job_role=target_job_role,
                resume_text=resume_text,
                cover_letter_text=cover_letter_text,
                job_posting_analysis=job_posting_analysis.model_dump(),
            ),
            temperature=0.1,
        )
        payload = self._parse_generic_json(raw)
        return CoverLetterDiagnosisResult.model_validate(payload)

    def _validate_response_with_retry(self, raw_content: str) -> AIReviewResponse:
        if not raw_content.strip():
            raise ValueError("Invalid AI review response: empty content")
        try:
            return self.parser.parse(raw_content)
        except ValueError:
            repaired_raw = self._call_structured_json(
                build_final_quality_check_messages(raw_json=raw_content),
                temperature=0.0,
            )
            return self.parser.parse(repaired_raw)

    def _call_structured_json(self, messages: list[dict[str, str]], *, temperature: float) -> str:
        completion = self.client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            response_format={"type": "json_object"},
            messages=messages,
        )
        return completion.choices[0].message.content or "{}"

    def _parse_generic_json(self, raw_content: str) -> dict[str, Any]:
        last_error: Exception | None = None
        for candidate in self.parser._candidate_payloads(raw_content):
            try:
                return self.parser.parse_json_object(candidate)
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                last_error = exc
        raise ValueError(f"Failed to parse JSON object: {last_error}")

    def _mock_job_posting_analysis(self, *, target_job_role: str, job_posting_text: str) -> JobPostingAnalysisResult:
        tokens = self._extract_keywords(f"{target_job_role} {job_posting_text}")
        role_tokens = self._extract_keywords(target_job_role)
        keywords = self._unique(role_tokens + tokens)[:7]
        competencies = [token for token in keywords if len(token) >= 2][:4]
        preferred = []
        if re.search(r"프로젝트|인턴|운영|협업|기획|상담|콘텐츠|행정", job_posting_text):
            preferred.extend(self._extract_keywords(job_posting_text)[:3])
        risk_notes = []
        if len(job_posting_text.strip()) < 30 or "없음" in job_posting_text:
            risk_notes.append("채용공고 정보가 제한적이어서 키워드 반영 점수는 보수적으로 해석해야 합니다.")
        tone_hint = "과장보다 근거 중심으로, 직무 역량과 실제 경험 연결이 보이게 쓰는 톤이 적절합니다."
        return JobPostingAnalysisResult(
            job_keywords=keywords,
            required_competencies=competencies,
            preferred_experiences=preferred,
            tone_hint=tone_hint,
            risk_notes=risk_notes,
        )

    def _mock_cover_letter_diagnosis(
        self,
        *,
        target_job_role: str,
        resume_text: str,
        cover_letter_text: str,
        job_posting_analysis: JobPostingAnalysisResult,
    ) -> CoverLetterDiagnosisResult:
        text = f"{resume_text}\n{cover_letter_text}"
        sentences = self._extract_sentences(text)
        core_experiences = self._extract_core_experiences(sentences)
        weak_points = []
        missing_evidence = []
        overused = self._find_overused_expressions(cover_letter_text)
        job_fit_notes = []

        if len(cover_letter_text.strip()) < 220:
            weak_points.append("자기소개서 분량이 짧아 경험 구조와 직무 연결이 충분히 드러나지 않습니다.")
        if not self._has_metric_evidence(cover_letter_text):
            weak_points.append("성과를 보여 주는 수치, 기간, 빈도 같은 성과 근거가 부족합니다.")
            missing_evidence.extend(["[기간] 또는 [횟수]", "[성과 수치] 또는 개선 결과"])
        if not core_experiences:
            weak_points.append("지원자를 구분해 줄 핵심 경험이 선명하게 드러나지 않습니다.")
        if not any(keyword in text for keyword in job_posting_analysis.job_keywords[:4]):
            weak_points.append("채용공고 핵심 키워드가 문장 속에서 직접적으로 연결되지 않습니다.")
        if overused:
            weak_points.append("클리셰 표현이 많아 실제 역량보다 의지 표현이 앞서 보입니다.")

        if job_posting_analysis.job_keywords:
            for keyword in job_posting_analysis.job_keywords[:4]:
                if keyword in text:
                    job_fit_notes.append(f"'{keyword}' 키워드는 일부 반영되어 있습니다.")
                else:
                    job_fit_notes.append(f"'{keyword}' 키워드를 실제 경험 문장과 연결해 보강할 필요가 있습니다.")

        recommended_structure = [
            "도입에서 지원 직무와 연결되는 문제의식 또는 관심 계기를 한 문단으로 정리",
            "중간 문단에서 핵심 경험을 상황, 역할, 행동, 결과 순서로 설명",
            "마지막 문단에서 배운 점과 지원 직무 역량 연결을 명확히 제시",
        ]
        if target_job_role:
            recommended_structure.append(f"결론에서 {target_job_role} 직무에서의 활용 가능성을 한 문장으로 닫기")

        return CoverLetterDiagnosisResult(
            core_experiences=core_experiences[:4],
            weak_points=self._unique(weak_points)[:5],
            missing_evidence=self._unique(missing_evidence)[:5],
            overused_expressions=overused[:5],
            job_fit_notes=job_fit_notes[:5],
            recommended_structure=recommended_structure[:5],
        )

    def _mock_response(
        self,
        *,
        resume_text: str,
        cover_letter_text: str,
        target_job_role: str,
        job_posting_text: str,
        review_mode: str,
        job_posting_analysis: JobPostingAnalysisResult,
        diagnosis: CoverLetterDiagnosisResult,
    ) -> AIReviewResponse:
        scores = self._heuristic_scores(
            resume_text=resume_text,
            cover_letter_text=cover_letter_text,
            job_posting_text=job_posting_text,
            review_mode=review_mode,
            job_posting_analysis=job_posting_analysis,
            diagnosis=diagnosis,
        )
        total_score = self.parser.compute_total_score(scores)
        problems = self._build_problems(diagnosis=diagnosis, review_mode=review_mode)
        improvement_strategy = self._build_improvement_strategy(diagnosis=diagnosis, job_posting_analysis=job_posting_analysis)
        strengths = self._build_strengths(
            scores=scores,
            diagnosis=diagnosis,
            job_posting_analysis=job_posting_analysis,
        )
        missing_keywords = [
            keyword for keyword in job_posting_analysis.job_keywords if keyword not in cover_letter_text and keyword not in resume_text
        ][:6]
        improved_cover_letter = self._build_improved_cover_letter(
            target_job_role=target_job_role,
            review_mode=review_mode,
            diagnosis=diagnosis,
            job_posting_analysis=job_posting_analysis,
        )
        interview_questions = self._build_interview_questions(
            target_job_role=target_job_role,
            diagnosis=diagnosis,
            missing_keywords=missing_keywords,
            review_mode=review_mode,
        )
        summary = self._build_summary(
            target_job_role=target_job_role,
            total_score=total_score,
            scores=scores,
            diagnosis=diagnosis,
        )

        mock_suggestions = self._build_mock_suggestions(
            cover_letter_text=cover_letter_text,
            target_job_role=target_job_role,
            diagnosis=diagnosis,
            missing_keywords=missing_keywords,
        )
        mock_sentence_reviews = self.sentence_review_service.process(
            [],
            cover_letter_text,
            suggestions=[self._suggestion_from_dict(item) for item in mock_suggestions],
            problems=problems,
        )

        payload = {
            "total_score": total_score,
            "scores": scores,
            "summary": summary,
            "problems": problems,
            "improvement_strategy": improvement_strategy,
            "improved_cover_letter": improved_cover_letter,
            "interview_questions": interview_questions,
            "missing_keywords": missing_keywords,
            "strengths": strengths,
            "job_keywords": job_posting_analysis.job_keywords,
            "rewritten_structure": diagnosis.recommended_structure,
            "evidence_suggestions": diagnosis.missing_evidence,
            "ats_keyword_notes": diagnosis.job_fit_notes,
            "final_review_checklist": self._build_final_checklist(missing_keywords=missing_keywords, diagnosis=diagnosis),
            "suggestions": mock_suggestions,
            "sentence_reviews": [item.model_dump() for item in mock_sentence_reviews],
        }
        return AIReviewResponse.model_validate(payload)

    def _attach_processed_review_details(self, review: AIReviewResponse, cover_letter_text: str) -> AIReviewResponse:
        processed = self.suggestion_service.process(review.suggestions, cover_letter_text)
        processed_sentence_reviews = self.sentence_review_service.process(
            review.sentence_reviews,
            cover_letter_text,
            suggestions=processed,
            problems=review.problems,
        )
        if not processed and processed_sentence_reviews:
            processed = self.suggestion_service.process(
                self.sentence_review_service.suggestions_from_sentence_reviews(processed_sentence_reviews),
                cover_letter_text,
            )
        if not processed_sentence_reviews and processed:
            processed_sentence_reviews = self.sentence_review_service.process(
                self.sentence_review_service.from_suggestions(processed, cover_letter_text),
                cover_letter_text,
                suggestions=processed,
                problems=review.problems,
            )
        return review.model_copy(update={"suggestions": processed, "sentence_reviews": processed_sentence_reviews})

    def _suggestion_from_dict(self, item: dict[str, Any]):
        from app.schemas.review import CoverLetterSuggestion

        return CoverLetterSuggestion.model_validate(item)

    def _heuristic_scores(
        self,
        *,
        resume_text: str,
        cover_letter_text: str,
        job_posting_text: str,
        review_mode: str,
        job_posting_analysis: JobPostingAnalysisResult,
        diagnosis: CoverLetterDiagnosisResult,
    ) -> dict[str, float]:
        text = f"{resume_text}\n{cover_letter_text}"
        length = len(cover_letter_text.strip())
        paragraphs = len([item for item in re.split(r"\n{2,}", cover_letter_text) if item.strip()])
        sentence_count = len(self._extract_sentences(cover_letter_text))
        action_count = self._count_action_verbs(text)
        result_count = self._count_result_signals(text)
        metric_count = len(re.findall(r"\d+(?:\.\d+)?\s*(%|건|명|회|개월|주|년|배|점|시간|개)", text))
        generic_count = len(self._find_overused_expressions(cover_letter_text))
        exaggeration_count = len(self._find_exaggeration_phrases(cover_letter_text))
        keyword_overlap = sum(
            1 for keyword in job_posting_analysis.job_keywords[:6] if keyword and keyword in cover_letter_text
        )
        keyword_base = max(len(job_posting_analysis.job_keywords[:6]), 1)
        keyword_ratio = keyword_overlap / keyword_base
        no_posting_signal = len(job_posting_text.strip()) < 30 or "없음" in job_posting_text

        job_fit = 35 + keyword_ratio * 35 + min(len(diagnosis.core_experiences) * 6, 18)
        if any(token in text for token in self._extract_keywords(job_posting_text)[:3]):
            job_fit += 6
        if diagnosis.job_fit_notes:
            job_fit += 4

        specificity = 32 + min(length / 14, 24) + min(action_count * 4, 20) + min(len(diagnosis.core_experiences) * 3, 12)
        if length < 220:
            specificity -= 18
        specificity -= generic_count * 3

        achievement = 28 + min(metric_count * 18, 42) + min(result_count * 8, 18) + min(action_count * 2, 12)
        if metric_count == 0:
            achievement -= 12
        if any("성과 근거" in item or "[성과 수치]" in item for item in diagnosis.missing_evidence):
            achievement -= 8

        writing_quality = 64 + (6 if 180 <= length <= 1400 else -6) + (4 if paragraphs >= 2 or sentence_count >= 4 else -4)
        writing_quality -= exaggeration_count * 8
        writing_quality -= generic_count * 2

        uniqueness = 34 + min(len(diagnosis.core_experiences) * 8, 24) + min(action_count * 2, 10)
        if any(keyword in text for keyword in ("프로젝트", "캡스톤", "실습", "인턴")):
            uniqueness += 6
        uniqueness -= generic_count * 4
        uniqueness -= exaggeration_count * 5

        structure = 48 + (12 if paragraphs >= 2 else 4) + (8 if sentence_count >= 4 else 0) + min(
            len(diagnosis.recommended_structure) * 3, 12
        )
        if length < 220:
            structure -= 14
        if sentence_count < 4:
            structure -= 6

        keyword_match = 32 + keyword_ratio * 54 + min(result_count * 2, 6) + (4 if metric_count > 0 else 0)
        if no_posting_signal:
            keyword_match = min(keyword_match, 58)
        if keyword_overlap == 0:
            keyword_match -= 10

        scores = {
            "job_fit": job_fit,
            "specificity": specificity,
            "achievement": achievement,
            "writing_quality": writing_quality,
            "uniqueness": uniqueness,
            "structure": structure,
            "keyword_match": keyword_match,
        }

        if review_mode == "strict":
            scores["job_fit"] -= 4
            scores["specificity"] -= 5
            scores["achievement"] -= 6
            scores["writing_quality"] -= 3
            scores["keyword_match"] -= 3
        elif review_mode == "quick":
            scores["writing_quality"] += 1
        elif review_mode == "rewrite-focused":
            scores["writing_quality"] += 2
            scores["structure"] += 1

        # Conservative scoring policy:
        # - vague drafts should stay below mid-60s,
        # - decent but generic drafts should cluster in the 65-78 range,
        # - strong role-aligned drafts can reach 79-90,
        # - exceptional 90+ should be rare and require concrete evidence.
        return {key: max(0.0, min(100.0, round(value, 1))) for key, value in scores.items()}

    def _build_summary(
        self,
        *,
        target_job_role: str,
        total_score: float,
        scores: dict[str, float],
        diagnosis: CoverLetterDiagnosisResult,
    ) -> str:
        if total_score < 65:
            return (
                f"현재 문안은 {target_job_role} 지원용 자기소개서로 쓰기에는 근거와 경험 구조가 부족합니다. "
                f"특히 {self._top_issue(diagnosis)} 보완이 먼저 필요하며, 직무 역량을 뒷받침하는 성과 근거를 넣어야 점수가 올라갑니다."
            )
        if total_score < 79:
            return (
                f"기본 경험은 갖추고 있지만 {target_job_role} 직무에 맞는 설득력은 아직 평이한 수준입니다. "
                f"강점은 살리되 {self._top_issue(diagnosis)} 보강하고, 문항 의도에 맞게 경험 구조를 정리하면 제출용 문안으로 더 좋아집니다."
            )
        return (
            f"{target_job_role} 직무와 연결되는 경험 축은 비교적 잘 잡혀 있습니다. "
            f"다만 더 높은 완성도를 위해 {self._top_issue(diagnosis)}을 보강하고, 면접 연결성이 보이도록 근거 문장을 조금 더 다듬는 것이 좋습니다."
        )

    def _build_problems(self, *, diagnosis: CoverLetterDiagnosisResult, review_mode: str) -> list[str]:
        problems = diagnosis.weak_points[:]
        if review_mode == "strict" and diagnosis.overused_expressions:
            problems.append(f"'{diagnosis.overused_expressions[0]}' 같은 표현은 차별성을 낮추므로 그대로 제출하기 어렵습니다.")
        if not problems:
            problems.append("전반적인 방향은 좋지만, 성과 근거나 직무 연결 문장을 한 단계 더 구체화하면 제출용 완성도가 높아집니다.")
        return self._unique(problems)[: (3 if review_mode == "quick" else 5)]

    def _build_improvement_strategy(
        self,
        *,
        diagnosis: CoverLetterDiagnosisResult,
        job_posting_analysis: JobPostingAnalysisResult,
    ) -> list[str]:
        strategies = []
        if diagnosis.missing_evidence:
            strategies.append(
                f"성과 근거가 약한 문장에는 {', '.join(diagnosis.missing_evidence[:2])}처럼 빠진 정보를 실제 사실 기준으로 보강하세요."
            )
        if diagnosis.core_experiences:
            strategies.append(
                f"핵심 경험은 '{diagnosis.core_experiences[0]}'처럼 한 줄 제목으로 잡고 상황, 역할, 행동, 결과 순서로 다시 쓰세요."
            )
        if job_posting_analysis.job_keywords:
            strategies.append(
                f"채용공고 키워드 {', '.join(job_posting_analysis.job_keywords[:3])}를 경험 문장 속에 직접 연결해 직무 적합도를 높이세요."
            )
        strategies.append("문단 마지막에는 배운 점보다 지원 직무에서 어떻게 활용할지까지 연결해 면접 연결성을 만드세요.")
        return self._unique(strategies)[:4]

    def _build_strengths(
        self,
        *,
        scores: dict[str, float],
        diagnosis: CoverLetterDiagnosisResult,
        job_posting_analysis: JobPostingAnalysisResult,
    ) -> list[str]:
        strengths = []
        if diagnosis.core_experiences:
            strengths.append(f"핵심 경험 축이 완전히 비어 있지는 않아 문안을 다듬을 기반은 있습니다: {diagnosis.core_experiences[0]}")
        if scores["job_fit"] >= 70:
            strengths.append("지원 직무와 연결하려는 방향성이 보여 직무 적합도 개선 여지가 분명합니다.")
        if scores["writing_quality"] >= 70:
            strengths.append("문장 자체의 읽힘은 크게 나쁘지 않아 구조와 근거만 보강하면 완성도가 올라갈 수 있습니다.")
        if job_posting_analysis.job_keywords:
            strengths.append(f"채용공고 핵심 키워드 중 일부는 이미 연결 가능합니다: {', '.join(job_posting_analysis.job_keywords[:2])}")
        return self._unique(strengths)[:4]

    def _build_improved_cover_letter(
        self,
        *,
        target_job_role: str,
        review_mode: str,
        diagnosis: CoverLetterDiagnosisResult,
        job_posting_analysis: JobPostingAnalysisResult,
    ) -> str:
        role_keywords = ", ".join(job_posting_analysis.job_keywords[:3]) or target_job_role
        core = diagnosis.core_experiences[0] if diagnosis.core_experiences else "관련 프로젝트와 실무형 학습 경험"
        second_core = diagnosis.core_experiences[1] if len(diagnosis.core_experiences) > 1 else "협업 과정에서 문제를 정리하고 실행한 경험"
        body = [
            f"저는 {target_job_role} 지원자로서 단순한 참여 경험보다 실제로 맡은 역할과 실행 과정을 분명히 설명하는 문안을 만들고자 합니다. 특히 {core} 경험은 {role_keywords} 역량과 연결해 보여 줄 수 있는 핵심 사례입니다.",
            (
                f"해당 경험에서 저는 먼저 해결해야 할 문제를 정리하고, 제가 맡은 역할을 구체화한 뒤 필요한 작업을 직접 실행했습니다. "
                f"이 과정에서 {second_core}처럼 행동 중심의 근거를 드러내고, 가능하다면 [기간], [횟수], [성과 수치]를 추가해 성과 근거를 분명히 제시하는 것이 좋습니다."
            ),
            (
                f"이 경험을 통해 얻은 강점은 단순히 열심히 했다는 태도가 아니라, 지원 직무에 필요한 역량을 실제 행동과 결과로 설명할 수 있다는 점입니다. "
                f"최종 제출용 문안에서는 배운 점을 한 문장으로 정리한 뒤, 그 역량을 {target_job_role} 업무에서 어떻게 활용할지까지 연결하면 설득력이 높아집니다."
            ),
        ]
        if review_mode == "quick":
            body = body[:2]
        elif review_mode == "rewrite-focused":
            body.append(
                "또한 과장된 표현 대신 검증 가능한 문장을 유지해 면접에서 설명하기 쉬운 수준으로 정리하는 것이 중요합니다."
            )
        return "\n\n".join(body)

    def _build_interview_questions(
        self,
        *,
        target_job_role: str,
        diagnosis: CoverLetterDiagnosisResult,
        missing_keywords: list[str],
        review_mode: str,
    ) -> list[str]:
        questions = [
            f"{target_job_role} 직무와 가장 관련 있는 경험 하나를 골라 본인의 역할과 행동을 구체적으로 설명해 주세요.",
            "자기소개서에서 언급한 경험 중 실제 성과를 가장 잘 보여 줄 수 있는 사례는 무엇이며, 그 근거는 무엇인가요?",
            "문항 의도에 맞게 경험을 다시 정리한다면 어떤 문장을 빼고 어떤 근거를 추가하시겠습니까?",
        ]
        if missing_keywords:
            questions.append(f"채용공고 키워드인 '{missing_keywords[0]}'를 본인의 경험과 연결해 설명할 수 있나요?")
        if review_mode != "quick":
            questions.append("면접에서 수치로 설명하기 어려운 경험이라면 어떤 방식으로 신뢰도를 보완하시겠습니까?")
        return questions[: (3 if review_mode == "quick" else 5)]

    def _build_final_checklist(
        self,
        *,
        missing_keywords: list[str],
        diagnosis: CoverLetterDiagnosisResult,
    ) -> list[str]:
        checklist = [
            "각 문단에 상황, 역할, 행동, 결과 중 최소 3요소가 들어갔는지 확인하기",
            "성과 근거가 없는 문장에는 [기간], [성과 수치], [횟수]를 실제 사실로 채워 넣기",
            "지원 직무와 직접 연결되지 않는 문장은 줄이고 직무 역량 언어로 다시 표현하기",
        ]
        if missing_keywords:
            checklist.append(f"채용공고 키워드 {missing_keywords[0]}를 반영한 문장이 있는지 확인하기")
        if diagnosis.overused_expressions:
            checklist.append(f"'{diagnosis.overused_expressions[0]}' 같은 추상 표현을 구체 문장으로 바꾸기")
        return checklist[:5]

    def _build_mock_suggestions(
        self,
        *,
        cover_letter_text: str,
        target_job_role: str,
        diagnosis: CoverLetterDiagnosisResult,
        missing_keywords: list[str],
    ) -> list[dict[str, Any]]:
        sentences = self._extract_sentences(cover_letter_text)
        suggestions: list[dict[str, Any]] = []
        used: set[tuple[str, str]] = set()

        def pick_sentence(index: int = 0) -> str:
            if not sentences:
                return cover_letter_text.strip()[:80]
            return sentences[min(index, len(sentences) - 1)]

        def add_suggestion(
            *,
            severity: str,
            category: str,
            original_text: str,
            issue: str,
            reason: str,
            suggested_text: str,
            apply_type: str = "replace",
            confidence: float = 0.78,
        ) -> None:
            original = original_text.strip()
            replacement = suggested_text.strip()
            if not original or len(re.sub(r"\s+", "", original)) < 8 or not replacement:
                return
            key = (category, re.sub(r"\s+", "", original))
            if key in used:
                return
            suggestions.append(
                {
                    "severity": severity,
                    "category": category,
                    "original_text": original,
                    "start_index": cover_letter_text.find(original) if original in cover_letter_text else None,
                    "end_index": (
                        cover_letter_text.find(original) + len(original)
                        if original in cover_letter_text
                        else None
                    ),
                    "issue": issue,
                    "reason": reason,
                    "suggested_text": replacement,
                    "apply_type": apply_type,
                    "confidence": confidence,
                }
            )
            used.add(key)

        if sentences:
            vague_sentence = next(
                (sentence for sentence in sentences if any(token in sentence for token in ("열심히", "성실", "책임감", "최선", "노력"))),
                sentences[0],
            )
            add_suggestion(
                severity="high",
                category="specificity",
                original_text=vague_sentence,
                issue="표현이 추상적입니다",
                reason="무엇을 했는지보다 태도 표현이 앞서 있어 경험 구조가 약하게 보입니다.",
                suggested_text=(
                    f"{vague_sentence} 이 경험에서 맡은 역할을 [역할]로 구체화하고, 실제 실행한 행동과 사용한 도구를 "
                    f"{target_job_role} 업무와 연결해 설명했습니다."
                ),
                apply_type="rewrite_paragraph",
                confidence=0.82,
            )

        evidence_target = next((sentence for sentence in sentences if len(sentence) >= 12), pick_sentence(0))
        if diagnosis.missing_evidence or not self._has_metric_evidence(cover_letter_text):
            add_suggestion(
                severity="high",
                category="achievement",
                original_text=evidence_target,
                issue="성과 근거가 부족합니다",
                reason="행동 이후 어떤 변화가 있었는지 보여 주는 근거가 필요합니다.",
                suggested_text=(
                    f"이 과정에서 [기간] 동안 맡은 역할과 실행 결과를 정리했고, [성과 수치] 또는 개선 전후 변화를 기준으로 "
                    f"{target_job_role} 직무에서 활용할 수 있는 성과를 설명할 수 있습니다."
                ),
                apply_type="append_after",
                confidence=0.86,
            )

        if missing_keywords:
            keyword_sentence = sentences[-1] if sentences else cover_letter_text[:80]
            add_suggestion(
                severity="medium",
                category="keyword_match",
                original_text=keyword_sentence,
                issue="직무 키워드 연결이 약합니다",
                reason=f"채용공고 핵심 키워드인 '{missing_keywords[0]}'가 문장 속에서 직접적으로 보이지 않습니다.",
                suggested_text=(
                    f"이 경험은 {target_job_role} 직무에서 요구하는 {missing_keywords[0]} 역량과 연결되며, 실제 업무에서 "
                    "문제를 정리하고 실행으로 옮기는 근거로 제시할 수 있습니다."
                ),
                apply_type="append_after",
                confidence=0.73,
            )

        if len(sentences) >= 2:
            structure_sentence = pick_sentence(1)
            add_suggestion(
                severity="medium",
                category="structure",
                original_text=structure_sentence,
                issue="경험의 흐름이 약합니다",
                reason="상황, 역할, 행동, 결과 중 일부가 빠져 있어 읽는 사람이 경험을 따라가기 어렵습니다.",
                suggested_text=(
                    f"{structure_sentence} 이 경험은 문제 상황을 먼저 밝히고, 제가 맡은 역할과 실행 과정을 이어 설명한 뒤 "
                    "결과와 배운 점을 한 문장으로 정리하면 더 자연스럽습니다."
                ),
                apply_type="rewrite_paragraph",
                confidence=0.76,
            )

        tone_sentence = next(
            (sentence for sentence in sentences if any(token in sentence for token in ("싶습니다", "노력하겠습니다", "배우고 싶"))),
            pick_sentence(-1),
        )
        add_suggestion(
            severity="low",
            category="tone",
            original_text=tone_sentence,
            issue="마무리 표현이 다소 일반적입니다",
            reason="의지 표현만으로 끝나면 지원 직무에서 어떻게 기여할지 약하게 보입니다.",
            suggested_text=(
                f"{target_job_role} 업무에서는 이 경험을 바탕으로 문제를 빠르게 구조화하고, 필요한 자료와 실행 과정을 "
                "끝까지 정리하는 구성원으로 기여하겠습니다."
            ),
            apply_type="replace",
            confidence=0.71,
        )

        if len(sentences) >= 3:
            writing_sentence = pick_sentence(2)
            add_suggestion(
                severity="low",
                category="writing_quality",
                original_text=writing_sentence,
                issue="문장 초점이 흐립니다",
                reason="한 문장 안에 태도와 목표가 섞여 핵심 경험이 덜 선명합니다.",
                suggested_text=(
                    f"{writing_sentence} 이 문장은 핵심 행동을 먼저 제시하고, 그 행동이 {target_job_role} 업무와 어떻게 연결되는지 "
                    "뒤에 붙이면 더 읽기 쉽습니다."
                ),
                apply_type="rewrite_paragraph",
                confidence=0.69,
            )

        return suggestions[:7]

    def _mock_refinement(
        self,
        *,
        instruction: str,
        current_text: str,
        target_job_role: str,
        job_posting_text: str,
    ) -> ReviewRefinementResponse:
        normalized = current_text.strip()
        warnings: list[str] = []
        change_summary = "요청 방향에 맞게 문안을 다시 정리했습니다."

        if "구체" in instruction:
            normalized += (
                "\n\n실제 제출 전에는 본인이 맡은 역할, 사용한 방법, 결과를 [기간], [횟수], [성과 수치] 기준으로 보강하면 더 설득력이 높아집니다."
            )
            change_summary = "역할, 행동, 결과가 더 보이도록 구체 문장을 덧붙였습니다."
        elif "성과" in instruction:
            normalized += "\n\n특히 결과를 설명할 때는 [성과 수치] 또는 개선 전후 차이를 넣어 성과 근거를 분명히 해 주세요."
            change_summary = "성과 중심 문장으로 무게를 옮기고 수치 보강 지점을 드러냈습니다."
            if not self._has_metric_evidence(current_text):
                warnings.append("현재 문안에 검증 가능한 수치가 적어 [성과 수치] 자리를 실제 사실로 채워야 합니다.")
        elif "자연" in instruction:
            normalized = re.sub(r"\s{2,}", " ", normalized)
            normalized = normalized.replace("저는 저는", "저는")
            change_summary = "어색한 반복과 군더더기를 줄여 문장을 더 자연스럽게 다듬었습니다."
        elif "신입" in instruction:
            normalized = normalized.replace("주도했습니다", "담당했습니다").replace("총괄했습니다", "참여하며 이끌었습니다")
            normalized += "\n\n신입 지원자 관점에서 배운 점과 성장 가능성이 자연스럽게 보이도록 톤을 낮췄습니다."
            change_summary = "과도하게 고연차처럼 보이는 표현을 낮추고 신입 지원자 톤으로 조정했습니다."
        elif "700자" in instruction:
            normalized = self._truncate_korean_text(normalized, 700)
            change_summary = "핵심 경험과 직무 연결성만 남기고 700자 안팎으로 압축했습니다."
        elif "면접" in instruction:
            normalized += "\n\n면접에서는 위 문장을 기준으로 본인의 역할과 결과를 먼저 설명하고, 이후 배운 점을 덧붙이면 방어하기가 수월합니다."
            change_summary = "면접에서 설명하기 쉬운 순서와 표현으로 조정했습니다."
        elif "과장" in instruction:
            normalized = self._soften_exaggeration(normalized)
            change_summary = "검증이 어려운 표현을 낮추고 방어 가능한 문장으로 정리했습니다."
            warnings.append("강한 표현을 줄인 만큼 실제 성과 근거를 별도로 보강하는 것이 좋습니다.")
        else:
            normalized += f"\n\n요청한 방향('{instruction}')에 맞게 핵심 경험과 직무 연결 문장을 더 선명하게 다듬었습니다."

        if not job_posting_text or "없음" in job_posting_text:
            warnings.append("채용공고 정보가 제한적이어서 직무 키워드 반영은 보수적으로 조정했습니다.")

        if self._find_exaggeration_phrases(normalized):
            warnings.append("면접에서 설명하기 어려운 단정적 표현이 남아 있는지 한 번 더 점검해 주세요.")

        return ReviewRefinementResponse(
            refined_text=normalized,
            change_summary=change_summary,
            warnings=self._unique(warnings),
        )

    def _extract_keywords(self, text: str) -> list[str]:
        stopwords = {
            "지원",
            "직무",
            "신입",
            "채용공고",
            "채용",
            "업무",
            "경험",
            "역량",
            "이해",
            "자기소개서",
            "이력서",
            "및",
            "또는",
            "관련",
            "우대",
            "필수",
            "담당",
            "가능",
            "이상",
            "능력",
            "수행",
            "통해",
        }
        tokens = re.findall(r"[A-Za-z0-9+#./-]{2,}|[가-힣]{2,}", text)
        return [token for token in tokens if token not in stopwords][:20]

    def _extract_sentences(self, text: str) -> list[str]:
        return [
            sentence.strip()
            for sentence in re.split(r"[.!?\n]+", text)
            if sentence.strip() and len(re.sub(r"\s+", "", sentence.strip())) >= 8
        ]

    def _extract_core_experiences(self, sentences: list[str]) -> list[str]:
        action_keywords = ("프로젝트", "운영", "개선", "개발", "기획", "지원", "상담", "분석", "제작", "관리", "협업")
        selected = [sentence for sentence in sentences if any(keyword in sentence for keyword in action_keywords)]
        return self._unique([self._trim_sentence(sentence) for sentence in selected])[:4]

    def _find_overused_expressions(self, text: str) -> list[str]:
        clichés = ["성실", "최선", "열정", "책임감", "배우고 싶", "도전", "누구보다", "항상", "모든", "완벽"]
        return [phrase for phrase in clichés if phrase in text]

    def _find_exaggeration_phrases(self, text: str) -> list[str]:
        phrases = ["압도적", "완벽", "무조건", "반드시 성공", "최고의", "독보적", "전부 해결"]
        return [phrase for phrase in phrases if phrase in text]

    def _count_action_verbs(self, text: str) -> int:
        verbs = ["개선", "구축", "운영", "분석", "정리", "기획", "지원", "조정", "협업", "개발", "자동화", "대응", "작성"]
        return sum(text.count(verb) for verb in verbs)

    def _count_result_signals(self, text: str) -> int:
        signals = ["줄였", "개선", "향상", "감소", "증가", "안정화", "완료", "공유", "문서화", "정착"]
        return sum(text.count(signal) for signal in signals)

    def _has_metric_evidence(self, text: str) -> bool:
        return bool(re.search(r"\d+(?:\.\d+)?\s*(%|건|명|회|개월|주|년|배|점|시간|개)", text))

    def _soften_exaggeration(self, text: str) -> str:
        replacements = {
            "압도적": "의미 있는",
            "완벽": "안정적",
            "최고의": "적합한",
            "독보적": "차별화된",
            "전부 해결": "우선순위를 정해 개선",
        }
        softened = text
        for before, after in replacements.items():
            softened = softened.replace(before, after)
        return softened

    def _truncate_korean_text(self, text: str, max_chars: int) -> str:
        compact = re.sub(r"\s+", " ", text).strip()
        return compact if len(compact) <= max_chars else compact[: max_chars - 1].rstrip() + "…"

    def _top_issue(self, diagnosis: CoverLetterDiagnosisResult) -> str:
        if diagnosis.weak_points:
            return diagnosis.weak_points[0]
        return "성과 근거와 직무 연결성"

    def _trim_sentence(self, sentence: str, limit: int = 60) -> str:
        text = sentence.strip()
        return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"

    def _unique(self, values: list[str]) -> list[str]:
        seen = set()
        unique_values = []
        for value in values:
            if value and value not in seen:
                seen.add(value)
                unique_values.append(value)
        return unique_values

    def _build_metadata(
        self,
        *,
        provider_name: str,
        model_name: str,
        prompt_version: str,
        pipeline_version: str,
    ) -> dict[str, str]:
        return {
            "provider_name": provider_name,
            "model_name": model_name,
            "prompt_version": prompt_version,
            "pipeline_version": pipeline_version,
        }
