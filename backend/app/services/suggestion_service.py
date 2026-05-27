import re
from difflib import SequenceMatcher

from app.schemas.review import CoverLetterSuggestion
from app.services.anonymization_service import AnonymizationService


class SuggestionService:
    MAX_SUGGESTIONS = 7
    SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
    SENTENCE_PATTERN = re.compile(r"[^.!?\n。！？]+(?:[.!?。！？]+|$)")

    def __init__(self) -> None:
        self.anonymizer = AnonymizationService()

    def process(self, suggestions: list[CoverLetterSuggestion], cover_letter_text: str) -> list[CoverLetterSuggestion]:
        processed: list[CoverLetterSuggestion] = []
        seen_targets: set[tuple[str, str]] = set()

        for suggestion in suggestions:
            original_text = (suggestion.original_text or "").strip()
            suggested_text = self._normalize_suggested_text((suggestion.suggested_text or "").strip(), original_text)
            suggested_text = self.anonymizer.anonymize_text(suggested_text)
            issue = (suggestion.issue or "").strip()
            reason = (suggestion.reason or "").strip()
            if not suggested_text:
                continue

            match = self._resolve_match(cover_letter_text, original_text, suggestion.start_index, suggestion.end_index)
            matched_original = match["text"] if match else original_text
            dedupe_key = (self._compact(matched_original), self._compact(suggested_text))
            if dedupe_key in seen_targets:
                continue

            confidence = self._clamp_confidence(suggestion.confidence)
            if match:
                start_index = match["start"]
                end_index = match["end"]
                if match["source"] != "exact":
                    confidence = min(confidence, 0.74)
            else:
                start_index = None
                end_index = None
                confidence = min(confidence, 0.45)

            if self.anonymizer.detect_remaining_pii(suggested_text):
                suggested_text = self.anonymizer.anonymize_text(suggested_text)

            processed.append(
                CoverLetterSuggestion(
                    id="",
                    severity=suggestion.severity,
                    category=suggestion.category,
                    original_text=matched_original,
                    start_index=start_index,
                    end_index=end_index,
                    issue=issue or "문장 보완 필요",
                    reason=reason or "직무 적합성과 설득력을 높이기 위해 문장을 더 구체화할 필요가 있습니다.",
                    suggested_text=suggested_text,
                    apply_type=suggestion.apply_type,
                    confidence=confidence,
                )
            )
            seen_targets.add(dedupe_key)

        processed.sort(
            key=lambda item: (
                item.start_index is None,
                self.SEVERITY_ORDER.get(item.severity, 9),
                -(item.confidence or 0),
                item.start_index if item.start_index is not None else 10**9,
            )
        )
        limited = processed[: self.MAX_SUGGESTIONS]
        return [item.model_copy(update={"id": f"sug-{index}"}) for index, item in enumerate(limited, start=1)]

    def _resolve_match(
        self,
        cover_letter_text: str,
        original_text: str,
        start_index: int | None,
        end_index: int | None,
    ) -> dict[str, int | str] | None:
        if not cover_letter_text or not original_text:
            return None

        if (
            start_index is not None
            and end_index is not None
            and 0 <= start_index < end_index <= len(cover_letter_text)
            and cover_letter_text[start_index:end_index] == original_text
        ):
            return {"start": start_index, "end": end_index, "text": original_text, "source": "exact"}

        exact_matches = self._find_all(cover_letter_text, original_text)
        if exact_matches:
            start, end = self._pick_nearest(exact_matches, start_index)
            return {"start": start, "end": end, "text": cover_letter_text[start:end], "source": "exact"}

        for candidate in self._extract_sentences(original_text):
            if len(self._compact(candidate)) < 8:
                continue
            matches = self._find_all(cover_letter_text, candidate)
            if matches:
                start, end = self._pick_nearest(matches, start_index)
                return {"start": start, "end": end, "text": cover_letter_text[start:end], "source": "sentence"}

        close_sentence = self._find_close_sentence(cover_letter_text, original_text, start_index)
        if close_sentence:
            start, end, text = close_sentence
            return {"start": start, "end": end, "text": text, "source": "fuzzy"}

        return None

    def _find_close_sentence(
        self, cover_letter_text: str, original_text: str, start_index: int | None
    ) -> tuple[int, int, str] | None:
        candidates = self._extract_sentences_with_positions(cover_letter_text)
        source_candidates = self._extract_sentences(original_text) or [original_text]
        best: tuple[float, int, int, str] | None = None

        for start, end, sentence in candidates:
            for source in source_candidates:
                score = self._similarity(sentence, source)
                if start_index is not None:
                    distance_penalty = min(abs(start - start_index) / max(len(cover_letter_text), 1), 0.2)
                    score -= distance_penalty
                if best is None or score > best[0]:
                    best = (score, start, end, sentence)

        if best and best[0] >= 0.5:
            return best[1], best[2], best[3]
        return None

    def _extract_sentences(self, text: str) -> list[str]:
        return [
            match.group(0).strip()
            for match in self.SENTENCE_PATTERN.finditer(text or "")
            if match.group(0).strip() and len(self._compact(match.group(0))) >= 4
        ]

    def _extract_sentences_with_positions(self, text: str) -> list[tuple[int, int, str]]:
        sentences: list[tuple[int, int, str]] = []
        for match in self.SENTENCE_PATTERN.finditer(text or ""):
            sentence = match.group(0).strip()
            if not sentence or len(self._compact(sentence)) < 4:
                continue
            offset = len(match.group(0)) - len(match.group(0).lstrip())
            start = match.start() + offset
            sentences.append((start, start + len(sentence), sentence))
        return sentences

    def _find_all(self, text: str, target: str) -> list[tuple[int, int]]:
        matches: list[tuple[int, int]] = []
        cursor = 0
        while target:
            index = text.find(target, cursor)
            if index == -1:
                break
            matches.append((index, index + len(target)))
            cursor = index + max(len(target), 1)
        return matches

    def _pick_nearest(self, matches: list[tuple[int, int]], start_index: int | None) -> tuple[int, int]:
        if start_index is None:
            return matches[0]
        return min(matches, key=lambda item: abs(item[0] - start_index))

    def _similarity(self, left: str, right: str) -> float:
        left_compact = self._compact(left)
        right_compact = self._compact(right)
        if not left_compact or not right_compact:
            return 0.0
        sequence_score = SequenceMatcher(None, left_compact, right_compact).ratio()
        left_tokens = set(re.findall(r"[\w가-힣]+", left_compact))
        right_tokens = set(re.findall(r"[\w가-힣]+", right_compact))
        token_score = len(left_tokens & right_tokens) / max(len(left_tokens | right_tokens), 1)
        if token_score == 0 and sequence_score < 0.62:
            return 0.0
        return max(sequence_score, token_score)

    def _compact(self, text: str) -> str:
        return re.sub(r"\s+", "", (text or "").strip()).lower()

    def _clamp_confidence(self, value: float) -> float:
        return round(max(0.0, min(1.0, float(value))), 2)

    def _normalize_suggested_text(self, suggested_text: str, original_text: str) -> str:
        text = suggested_text.strip()
        if not text:
            return ""

        quoted_match = None
        for pattern in (r"'([^']{6,})'", r'"([^"]{6,})"', r"“([^”]{6,})”", r"‘([^’]{6,})’"):
            quoted_match = re.search(pattern, text)
            if quoted_match:
                break

        if quoted_match:
            candidate = quoted_match.group(1).strip()
            if candidate and candidate != original_text:
                return candidate

        cleanup_markers = [
            "처럼",
            "추가해 주세요",
            "추가해주세요",
            "적어 주세요",
            "적어주세요",
            "바꿔 주세요",
            "바꿔주세요",
            "써 주세요",
            "써주세요",
            "넣어 주세요",
            "넣어주세요",
        ]
        for marker in cleanup_markers:
            index = text.find(marker)
            if index > 0:
                text = text[:index].strip(" .,:;\n")
                break

        if text.startswith(original_text) and len(text) > len(original_text) + 8:
            text = text[len(original_text) :].strip(" .,:;\n")

        return text.strip()
