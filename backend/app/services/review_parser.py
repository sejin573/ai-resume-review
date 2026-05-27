import json
import re
from typing import Any

from pydantic import ValidationError

from app.prompts.review_prompts import SCORING_RUBRIC
from app.schemas.review import AIReviewResponse, ReviewRefinementResponse


class ReviewResponseParser:
    REQUIRED_SCORE_KEYS = tuple(SCORING_RUBRIC.keys())
    REQUIRED_LIST_FIELDS = (
        "problems",
        "improvement_strategy",
        "interview_questions",
        "missing_keywords",
        "strengths",
        "job_keywords",
        "rewritten_structure",
        "evidence_suggestions",
        "ats_keyword_notes",
        "final_review_checklist",
    )

    def parse(self, raw_content: str) -> AIReviewResponse:
        last_error: Exception | None = None
        for candidate in self._candidate_payloads(raw_content):
            try:
                payload = self.parse_json_object(candidate)
                repaired = self._repair_payload(payload)
                return AIReviewResponse.model_validate(repaired)
            except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
                last_error = exc
        raise ValueError(f"Invalid AI review response after repair attempts: {last_error}")

    def parse_refinement(self, raw_content: str) -> ReviewRefinementResponse:
        last_error: Exception | None = None
        for candidate in self._candidate_payloads(raw_content):
            try:
                payload = self.parse_json_object(candidate)
                payload["refined_text"] = str(payload.get("refined_text", "")).strip()
                payload["change_summary"] = str(payload.get("change_summary", "")).strip() or "요청 방향에 맞게 문안을 정리했습니다."
                payload["warnings"] = self._ensure_list(payload.get("warnings", []))
                if not payload["refined_text"]:
                    raise ValueError("refined_text is empty")
                return ReviewRefinementResponse.model_validate(payload)
            except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
                last_error = exc
        raise ValueError(f"Invalid refinement response after repair attempts: {last_error}")

    def parse_json_object(self, raw: str) -> dict[str, Any]:
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise TypeError("JSON payload must be an object")
        return payload

    def compute_total_score(self, scores: dict[str, float]) -> float:
        total = sum(scores[key] * SCORING_RUBRIC[key]["weight"] for key in self.REQUIRED_SCORE_KEYS)
        return round(total, 1)

    def _candidate_payloads(self, raw_content: str) -> list[str]:
        text = raw_content.strip()
        candidates = [text]

        fenced = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
        candidates.extend(fenced)

        brace_match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if brace_match:
            candidates.append(brace_match.group(0))

        cleaned = text.replace("\u201c", '"').replace("\u201d", '"').replace("\u2018", "'").replace("\u2019", "'")
        cleaned = cleaned.replace("\\'", "'")
        cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
        cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", cleaned)
        candidates.append(cleaned)

        cleaned_brace_match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if cleaned_brace_match:
            candidates.append(cleaned_brace_match.group(0))

        unique: list[str] = []
        seen = set()
        for item in candidates:
            if item and item not in seen:
                unique.append(item)
                seen.add(item)
        return unique

    def _repair_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        scores = payload.get("scores") or {}
        if not isinstance(scores, dict):
            scores = {}

        alias_map = {
            "jobFit": "job_fit",
            "specificity_score": "specificity",
            "achievement_score": "achievement",
            "writing": "writing_quality",
            "difference": "uniqueness",
            "logic": "structure",
            "keyword": "keyword_match",
        }
        for source_key, target_key in alias_map.items():
            if source_key in scores and target_key not in scores:
                scores[target_key] = scores[source_key]

        repaired_scores: dict[str, float] = {}
        for key in self.REQUIRED_SCORE_KEYS:
            repaired_scores[key] = self._clamp_score(scores.get(key, 0))
        payload["scores"] = repaired_scores

        computed_total = self.compute_total_score(repaired_scores)
        existing_total = payload.get("total_score")
        if existing_total in (None, ""):
            payload["total_score"] = computed_total
        else:
            payload["total_score"] = round(self._clamp_score(existing_total), 1)
            if abs(payload["total_score"] - computed_total) > 5:
                payload["total_score"] = computed_total

        payload["summary"] = str(payload.get("summary", "")).strip() or "현재 문안은 직무 적합성과 근거 표현을 더 보강할 필요가 있습니다."
        payload["improved_cover_letter"] = str(payload.get("improved_cover_letter", "")).strip()
        if not payload["improved_cover_letter"]:
            payload["improved_cover_letter"] = (
                "지원 직무와 연결되는 경험을 상황, 역할, 행동, 결과 순서로 다시 정리해 제출용 문안으로 보완해 주세요."
            )

        for field in self.REQUIRED_LIST_FIELDS:
            payload[field] = self._ensure_list(payload.get(field, []))

        suggestion_items = payload.get("suggestions", [])
        if not isinstance(suggestion_items, list):
            suggestion_items = []
        normalized_suggestions = []
        for item in suggestion_items:
            if not isinstance(item, dict):
                continue
            normalized_suggestions.append(
                {
                    "id": str(item.get("id", "") or ""),
                    "severity": str(item.get("severity", "medium") or "medium"),
                    "category": str(item.get("category", "specificity") or "specificity"),
                    "original_text": str(item.get("original_text", "") or ""),
                    "start_index": item.get("start_index"),
                    "end_index": item.get("end_index"),
                    "issue": str(item.get("issue", "") or ""),
                    "reason": str(item.get("reason", "") or ""),
                    "suggested_text": str(item.get("suggested_text", "") or ""),
                    "apply_type": str(item.get("apply_type", "replace") or "replace"),
                    "confidence": item.get("confidence", 0.5),
                }
            )
        payload["suggestions"] = normalized_suggestions

        sentence_review_items = payload.get("sentence_reviews", [])
        if not isinstance(sentence_review_items, list):
            sentence_review_items = []
        normalized_sentence_reviews = []
        for item in sentence_review_items:
            if not isinstance(item, dict):
                continue
            normalized_sentence_reviews.append(
                {
                    "id": str(item.get("id", "") or ""),
                    "sentence_text": str(item.get("sentence_text", "") or ""),
                    "start_index": item.get("start_index"),
                    "end_index": item.get("end_index"),
                    "status": str(item.get("status", "okay") or "okay"),
                    "category": str(item.get("category", "clarity") or "clarity"),
                    "label": str(item.get("label", "") or ""),
                    "good_point": item.get("good_point"),
                    "comment": str(item.get("comment", "") or ""),
                    "suggested_text": item.get("suggested_text"),
                    "can_apply": bool(item.get("can_apply", False)),
                    "context_before": item.get("context_before"),
                    "context_after": item.get("context_after"),
                    "edit_type": str(item.get("edit_type", "replace_sentence") or "replace_sentence"),
                    "expected_effect": item.get("expected_effect"),
                    "quality_warning": item.get("quality_warning"),
                    "confidence": item.get("confidence", 0.5),
                }
            )
        payload["sentence_reviews"] = normalized_sentence_reviews

        if not payload["improvement_strategy"]:
            payload["improvement_strategy"] = [
                "핵심 경험을 상황, 역할, 행동, 결과 순서로 다시 정리하고 빠진 근거를 보강하세요."
            ]
        if not payload["interview_questions"]:
            payload["interview_questions"] = [
                "지원 직무와 가장 관련 있는 경험 하나를 골라 본인의 역할과 결과를 구체적으로 설명해 주세요."
            ]

        return payload

    def _ensure_list(self, value: Any) -> list[str]:
        if isinstance(value, str):
            items = [line.strip("- ").strip() for line in re.split(r"[\n;]+", value) if line.strip()]
        elif isinstance(value, list):
            items = [str(item).strip() for item in value if str(item).strip()]
        else:
            items = []
        return items

    def _clamp_score(self, value: Any) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = 0.0
        return round(max(0.0, min(100.0, numeric)), 1)
