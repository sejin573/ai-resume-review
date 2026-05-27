import re
from difflib import SequenceMatcher

from app.schemas.review import CoverLetterSuggestion, SentenceReview


class SentenceReviewService:
    MAX_REVIEWS = 12
    MIN_TARGET = 6
    STATUS_ORDER = {"risky": 0, "needs_fix": 1, "okay": 2, "good": 3}
    SENTENCE_PATTERN = re.compile(r"[^.!?\n。！？]+(?:[.!?。！？]+|$)")
    INSTRUCTION_PATTERNS = (
        "작성하세요",
        "작성해 주세요",
        "작성해주세요",
        "추가해 주세요",
        "추가해주세요",
        "구체화하세요",
        "구체화해 주세요",
        "구체화했습니다",
        "보완하세요",
        "보완해 주세요",
        "보완해주세요",
        "적어 주세요",
        "적어주세요",
        "넣어 주세요",
        "넣어주세요",
        "기준으로 구체화",
        "이 경험에서 맡은 역할",
    )

    def process(
        self,
        sentence_reviews: list[SentenceReview],
        cover_letter_text: str,
        *,
        suggestions: list[CoverLetterSuggestion] | None = None,
        problems: list[str] | None = None,
    ) -> list[SentenceReview]:
        suggestions = suggestions or []
        problems = problems or []
        processed: list[SentenceReview] = []
        seen: set[str] = set()

        for review in sentence_reviews:
            normalized = self._normalize_review(review, cover_letter_text)
            if not normalized:
                continue
            key = self._compact(normalized.sentence_text)
            if key in seen:
                continue
            processed.append(normalized)
            seen.add(key)

        if len(processed) < 3 and suggestions:
            for review in self.from_suggestions(suggestions, cover_letter_text):
                normalized = self._normalize_review(review, cover_letter_text)
                if not normalized:
                    continue
                key = self._compact(normalized.sentence_text)
                if key and key not in seen:
                    processed.append(normalized)
                    seen.add(key)

        sentence_count = len(self._extract_sentences_with_positions(cover_letter_text))
        target_min = min(self.MIN_TARGET, sentence_count)
        if len(processed) < target_min:
            for review in self._fallback_reviews(cover_letter_text, suggestions=suggestions, problems=problems):
                normalized = self._normalize_review(review, cover_letter_text)
                if not normalized:
                    continue
                key = self._compact(normalized.sentence_text)
                if key and key not in seen:
                    processed.append(normalized)
                    seen.add(key)
                if len(processed) >= target_min:
                    break

        processed.sort(
            key=lambda item: (
                item.start_index is None,
                item.start_index if item.start_index is not None else 10**9,
                self.STATUS_ORDER.get(item.status, 9),
            )
        )
        limited = processed[: self.MAX_REVIEWS]
        return [item.model_copy(update={"id": f"sent-{index}"}) for index, item in enumerate(limited, start=1)]

    def suggestions_from_sentence_reviews(self, sentence_reviews: list[SentenceReview]) -> list[CoverLetterSuggestion]:
        suggestions: list[CoverLetterSuggestion] = []
        for item in sentence_reviews:
            if item.status not in {"needs_fix", "risky"} or not item.suggested_text:
                continue
            suggestions.append(
                CoverLetterSuggestion(
                    severity="high" if item.status == "risky" else "medium",
                    category=item.category if item.category != "clarity" else "writing_quality",
                    original_text=item.sentence_text,
                    start_index=item.start_index,
                    end_index=item.end_index,
                    issue=item.label or ("위험 표현" if item.status == "risky" else "문장 보완 필요"),
                    reason=item.comment,
                    suggested_text=item.suggested_text,
                    apply_type="replace",
                    confidence=item.confidence,
                )
            )
        return suggestions

    def from_suggestions(self, suggestions: list[CoverLetterSuggestion], cover_letter_text: str) -> list[SentenceReview]:
        reviews: list[SentenceReview] = []
        for suggestion in suggestions:
            sentence_text = suggestion.original_text.strip()
            if not sentence_text:
                continue
            match = self._resolve_match(cover_letter_text, sentence_text, suggestion.start_index, suggestion.end_index)
            if match:
                start, end, sentence_text, source = match
                confidence = min(suggestion.confidence, 0.78) if source != "exact" else suggestion.confidence
            else:
                start = end = None
                confidence = min(suggestion.confidence, 0.45)
            reviews.append(
                SentenceReview(
                    sentence_text=sentence_text,
                    start_index=start,
                    end_index=end,
                    status="risky" if suggestion.severity == "high" and suggestion.category == "tone" else "needs_fix",
                    category=suggestion.category if suggestion.category != "redundancy" else "redundancy",
                    label=suggestion.issue or "문장 보완 필요",
                    good_point=None,
                    comment=suggestion.reason or "이 문장은 직무 연결성과 구체성을 보완하면 더 설득력 있게 읽힙니다.",
                    suggested_text=suggestion.suggested_text or None,
                    can_apply=bool(suggestion.suggested_text),
                    confidence=confidence,
                )
            )
        return [item.model_copy(update={"id": f"sent-{index}"}) for index, item in enumerate(reviews, start=1)]

    def _normalize_review(self, review: SentenceReview, cover_letter_text: str) -> SentenceReview | None:
        sentence_text = (review.sentence_text or "").strip()
        if not sentence_text:
            return None

        match = self._resolve_match(cover_letter_text, sentence_text, review.start_index, review.end_index)
        confidence = self._clamp(review.confidence)
        if match:
            start, end, matched_text, source = match
            sentence_text = matched_text
            if source != "exact":
                confidence = min(confidence, 0.76)
        else:
            start = end = None
            confidence = min(confidence, 0.45)

        status = review.status
        context_before, context_after = self._context_around(cover_letter_text, start, end)
        suggested_text = (review.suggested_text or "").strip() or None
        quality_warning = review.quality_warning
        can_apply = status in {"needs_fix", "risky"} and bool(suggested_text)
        if status in {"good", "okay"}:
            can_apply = False
            suggested_text = None

        if status in {"needs_fix", "risky"}:
            quality = self.suggested_text_quality_check(suggested_text, sentence_text)
            if not quality["ok"]:
                fallback = self._fallback_rewrite(
                    sentence_text,
                    review.category,
                    cover_letter_text,
                    start=start,
                    end=end,
                )
                fallback_quality = self.suggested_text_quality_check(fallback, sentence_text)
                if fallback_quality["ok"]:
                    suggested_text = fallback
                    quality_warning = quality["warning"]
                    can_apply = True
                else:
                    suggested_text = None
                    can_apply = False
                    quality_warning = quality["warning"] or "추천 문장 품질이 낮아 직접 수정이 필요합니다."
            elif not suggested_text:
                can_apply = False

        return SentenceReview(
            sentence_text=sentence_text,
            start_index=start,
            end_index=end,
            status=status,
            category=review.category,
            label=(review.label or self._default_label(status)).strip(),
            good_point=(review.good_point or None) if status in {"good", "okay"} else review.good_point,
            comment=self._with_quality_warning((review.comment or self._default_comment(status)).strip(), quality_warning),
            suggested_text=suggested_text,
            can_apply=can_apply,
            context_before=review.context_before or context_before,
            context_after=review.context_after or context_after,
            edit_type=review.edit_type,
            expected_effect=review.expected_effect or self._default_expected_effect(status, review.category),
            quality_warning=quality_warning,
            confidence=confidence,
        )

    def _fallback_reviews(
        self,
        cover_letter_text: str,
        *,
        suggestions: list[CoverLetterSuggestion],
        problems: list[str],
    ) -> list[SentenceReview]:
        sentences = self._extract_sentences_with_positions(cover_letter_text)
        if not sentences:
            return []

        suggestion_by_start = {
            suggestion.start_index: suggestion
            for suggestion in suggestions
            if suggestion.start_index is not None and suggestion.suggested_text
        }
        fallback: list[SentenceReview] = []
        for index, (start, end, sentence) in enumerate(sentences[: self.MAX_REVIEWS]):
            suggestion = suggestion_by_start.get(start)
            if suggestion:
                fallback.append(
                    SentenceReview(
                        sentence_text=sentence,
                        start_index=start,
                        end_index=end,
                        status="needs_fix",
                        category=suggestion.category,
                        label=suggestion.issue or "문장 보완 필요",
                        good_point=None,
                        comment=suggestion.reason or "구체성과 직무 연결성을 보완하면 더 설득력 있습니다.",
                        suggested_text=suggestion.suggested_text,
                        can_apply=True,
                        context_before=self._context_around(cover_letter_text, start, end)[0],
                        context_after=self._context_around(cover_letter_text, start, end)[1],
                        edit_type="replace_sentence",
                        expected_effect="원문 경험을 더 구체적인 직무 역량으로 연결합니다.",
                        confidence=min(suggestion.confidence, 0.78),
                    )
                )
                continue

            status, category, label, comment, good_point = self._classify_sentence(sentence, index, problems)
            suggested = self._safe_suggest(sentence, category, cover_letter_text=cover_letter_text, start=start, end=end) if status in {"needs_fix", "risky"} else None
            fallback.append(
                SentenceReview(
                    sentence_text=sentence,
                    start_index=start,
                    end_index=end,
                    status=status,
                    category=category,
                    label=label,
                    good_point=good_point,
                    comment=comment,
                    suggested_text=suggested,
                    can_apply=status in {"needs_fix", "risky"} and bool(suggested),
                    context_before=self._context_around(cover_letter_text, start, end)[0],
                    context_after=self._context_around(cover_letter_text, start, end)[1],
                    edit_type="rewrite_with_context" if status in {"needs_fix", "risky"} else "replace_sentence",
                    expected_effect=self._default_expected_effect(status, category),
                    confidence=0.58 if status in {"needs_fix", "risky"} else 0.62,
                )
            )
        return fallback

    def _classify_sentence(
        self, sentence: str, index: int, problems: list[str]
    ) -> tuple[str, str, str, str, str | None]:
        if any(token in sentence for token in ("최고", "완벽", "무조건", "누구보다", "압도적")):
            return (
                "risky",
                "tone",
                "과장 위험",
                "면접에서 근거를 묻기 쉬운 강한 표현이 있어 조금 더 검증 가능한 표현으로 낮추는 편이 안전합니다.",
                None,
            )
        if any(token in sentence for token in ("열심히", "성실", "책임감", "노력", "최선")):
            return (
                "needs_fix",
                "specificity",
                "구체성 부족",
                "태도 표현은 보이지만 실제 맡은 역할과 행동이 덜 드러납니다.",
                None,
            )
        if not re.search(r"\d|%|건|명|회|개월|개선|감소|증가|완료|구현|개발|운영|분석", sentence) and index % 3 == 1:
            return (
                "needs_fix",
                "achievement",
                "성과 근거 부족",
                "행동 이후 어떤 변화가 있었는지 보강하면 경험의 신뢰도가 올라갑니다.",
                None,
            )
        if any(token in sentence for token in ("구현", "개발", "운영", "분석", "협업", "개선", "정리")):
            return (
                "good",
                "clarity",
                "경험 근거 좋음",
                "핵심 행동이 보여 문장의 기반이 좋습니다.",
                "실제 행동을 나타내는 단어가 있어 경험의 방향이 비교적 분명합니다.",
            )
        return (
            "okay",
            "clarity",
            "흐름 무난",
            problems[0] if problems else "큰 문제는 없지만 역할, 행동, 결과 중 빠진 요소를 한 번 더 확인하면 좋습니다.",
            "문장 흐름이 크게 어색하지 않아 앞뒤 문장과 연결해 다듬기 좋습니다.",
        )

    def suggested_text_quality_check(self, suggested_text: str | None, original_text: str = "") -> dict[str, str | bool]:
        text = (suggested_text or "").strip()
        if not text:
            return {"ok": False, "warning": "추천 문장이 비어 있어 직접 수정이 필요합니다."}
        if any(pattern in text for pattern in self.INSTRUCTION_PATTERNS):
            return {"ok": False, "warning": "추천 문장이 첨삭 지시문처럼 보여 바로 적용하기 어렵습니다."}
        placeholders = re.findall(r"\[[^\]]+\]", text)
        placeholder_chars = sum(len(item) for item in placeholders)
        if placeholder_chars / max(len(text), 1) > 0.28 or re.search(r"저는\s*\[[^\]]+\]", text):
            return {"ok": False, "warning": "추천 문장에 자리표시자가 많아 직접 수정이 필요합니다."}
        if len(text) < max(18, len(original_text.strip()) * 0.35):
            return {"ok": False, "warning": "추천 문장이 너무 짧아 원문 맥락을 충분히 반영하지 못했습니다."}
        generic_phrases = ("직무 역량으로 연결", "설득력을 높일 수 있습니다", "구체적으로 작성", "성과를 설명할 수 있습니다")
        if any(phrase in text for phrase in generic_phrases) and not self._extract_fact_keywords(text):
            return {"ok": False, "warning": "추천 문장이 일반론에 가까워 직접 수정이 필요합니다."}
        return {"ok": True, "warning": ""}

    def _safe_suggest(
        self,
        sentence: str,
        category: str,
        *,
        cover_letter_text: str = "",
        start: int | None = None,
        end: int | None = None,
    ) -> str:
        return self._fallback_rewrite(sentence, category, cover_letter_text, start=start, end=end)

    def _fallback_rewrite(
        self,
        sentence: str,
        category: str,
        cover_letter_text: str,
        *,
        start: int | None = None,
        end: int | None = None,
    ) -> str:
        compact = sentence.strip()
        if category == "tone":
            return re.sub(r"최고|완벽|무조건|누구보다|압도적", "꾸준히 검증 가능한 방식으로", compact)

        before, after = self._context_around(cover_letter_text, start, end)
        context = f"{before} {compact} {after}"
        keywords = self._extract_fact_keywords(context) or self._extract_fact_keywords(cover_letter_text)
        joined = self._join_keywords(keywords[:4])

        if "새로운 환경" in compact or "익숙하지 않은 기술" in compact or "빠르게 적응" in compact:
            if joined:
                return (
                    f"새로운 기술을 빠르게 익히고 실제 서비스 흐름에 적용하는 과정에서 성장해왔습니다. "
                    f"{joined} 경험을 통해 낯선 환경에서도 구조를 이해하고 필요한 기능을 구현하는 역량을 쌓았습니다."
                )
            return "새로운 기술을 빠르게 익히고 실제 업무 흐름에 적용하며, 낯선 환경에서도 구조를 이해해 필요한 기능을 구현하는 개발자로 성장해왔습니다."

        if category == "achievement":
            if joined:
                return f"{compact} 특히 {joined} 과정에서 맡은 역할과 처리 흐름을 정리하며 실제 운영에 필요한 개선 경험을 쌓았습니다."
            return f"{compact} 이 과정에서 맡은 역할과 처리 흐름을 정리하며 실제 업무 개선으로 이어지는 경험을 쌓았습니다."

        if joined:
            return f"{compact} 이 경험은 {joined}를 바탕으로 문제를 구조화하고 실제 기능으로 연결한 과정이라는 점에서 강점으로 제시할 수 있습니다."
        return f"{compact} 이 경험을 통해 문제를 구조화하고 필요한 기능을 실제 업무 흐름에 맞게 구현하는 역량을 키웠습니다."

    def _context_around(self, text: str, start: int | None, end: int | None) -> tuple[str | None, str | None]:
        if start is None or end is None:
            return None, None
        sentences = self._extract_sentences_with_positions(text)
        for index, (sent_start, sent_end, _sentence) in enumerate(sentences):
            if sent_start == start and sent_end == end:
                before = sentences[index - 1][2] if index > 0 else None
                after = sentences[index + 1][2] if index + 1 < len(sentences) else None
                return before, after
        before = next((sentence for _s, sent_end, sentence in reversed(sentences) if sent_end <= start), None)
        after = next((sentence for sent_start, _e, sentence in sentences if sent_start >= end), None)
        return before, after

    def _extract_fact_keywords(self, text: str) -> list[str]:
        candidates = [
            "Java",
            "Python",
            "Git",
            "PHP",
            "MVC",
            "OCR",
            "Spring",
            "JSP",
            "MySQL",
            "ASP",
            "Open API",
            "네이버 뉴스 API",
            "OpenAI Codex",
            "사내 홈페이지",
            "계약서 자동 검토 웹서비스",
            "전자계약",
            "정보 추출",
            "관리자 기능",
            "LMS",
            "운영",
            "유지보수",
            "기능 개선",
            "수강신청",
            "온라인 강의",
            "출석",
            "시험",
            "문제 분석",
            "기능 구현",
            "구조 이해",
            "서비스 개선",
        ]
        found: list[str] = []
        lowered = text.lower()
        for candidate in candidates:
            if candidate.lower() in lowered and candidate not in found:
                found.append(candidate)
        return found

    def _join_keywords(self, keywords: list[str]) -> str:
        if not keywords:
            return ""
        if len(keywords) == 1:
            return keywords[0]
        return ", ".join(keywords[:-1]) + f"와 {keywords[-1]}"

    def _with_quality_warning(self, comment: str, warning: str | None) -> str:
        if not warning:
            return comment
        if "직접 수정이 필요" in comment or "바로 적용하기 어렵" in comment:
            return comment
        return f"{comment} {warning}"

    def _default_expected_effect(self, status: str, category: str) -> str | None:
        if status == "good":
            return "현재 문장의 강점을 유지하면서 뒤 문장과 연결하면 좋습니다."
        if status == "okay":
            return "문장 흐름을 유지하되 직무 연결성을 조금 더 분명히 할 수 있습니다."
        if category == "achievement":
            return "행동과 결과의 연결이 분명해져 경험의 신뢰도가 올라갑니다."
        if category == "specificity":
            return "추상적인 태도 표현이 실제 경험 기반 강점으로 바뀝니다."
        if status == "risky":
            return "과장 위험을 줄이고 면접에서 설명 가능한 표현으로 정리됩니다."
        return "원문 경험을 더 구체적인 직무 역량으로 연결합니다."

    def _resolve_match(
        self, text: str, sentence: str, start_index: int | None, end_index: int | None
    ) -> tuple[int | None, int | None, str, str] | None:
        if not text or not sentence:
            return None
        if (
            start_index is not None
            and end_index is not None
            and 0 <= start_index < end_index <= len(text)
            and text[start_index:end_index] == sentence
        ):
            return start_index, end_index, sentence, "exact"

        matches = self._find_all(text, sentence)
        if matches:
            start, end = self._pick_nearest(matches, start_index)
            return start, end, text[start:end], "exact"

        for fragment in self._extract_sentences(sentence):
            if len(self._compact(fragment)) < 8:
                continue
            matches = self._find_all(text, fragment)
            if matches:
                start, end = self._pick_nearest(matches, start_index)
                return start, end, text[start:end], "sentence"

        best: tuple[float, int, int, str] | None = None
        for start, end, candidate in self._extract_sentences_with_positions(text):
            score = self._similarity(candidate, sentence)
            if start_index is not None:
                score -= min(abs(start - start_index) / max(len(text), 1), 0.18)
            if best is None or score > best[0]:
                best = (score, start, end, candidate)
        if best and best[0] >= 0.5:
            return best[1], best[2], best[3], "fuzzy"
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

    def _clamp(self, value: float) -> float:
        return round(max(0.0, min(1.0, float(value))), 2)

    def _default_label(self, status: str) -> str:
        return {"good": "좋은 문장", "okay": "무난한 문장", "needs_fix": "보완 필요", "risky": "위험 표현"}.get(status, "문장 검토")

    def _default_comment(self, status: str) -> str:
        return {
            "good": "경험의 근거가 비교적 분명합니다.",
            "okay": "전체 흐름은 무난하지만 앞뒤 문장과 연결해 한 번 더 다듬어 보세요.",
            "needs_fix": "역할, 행동, 결과 중 부족한 요소를 보완하면 더 설득력 있습니다.",
            "risky": "과장되거나 면접에서 검증받기 쉬운 표현은 낮추는 편이 안전합니다.",
        }.get(status, "문장을 한 번 더 확인해 주세요.")
