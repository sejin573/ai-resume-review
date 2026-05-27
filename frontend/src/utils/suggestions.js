function extractQuotedCandidate(text) {
  const quotedPatterns = [
    /'([^']{6,})'/,
    /"([^"]{6,})"/,
    /‘([^’]{6,})’/,
    /“([^”]{6,})”/,
  ];

  for (const pattern of quotedPatterns) {
    const match = text.match(pattern);
    if (match?.[1]) return match[1].trim();
  }
  return "";
}

function cleanInstructionalTail(text) {
  let next = text.trim();
  const sentenceMarkers = [
    "추가해 주세요",
    "추가해주세요",
    "적어 주세요",
    "적어주세요",
    "바꿔 주세요",
    "바꿔주세요",
    "써 주세요",
    "써주세요",
    "보완해 주세요",
    "보완해주세요",
  ];

  for (const marker of sentenceMarkers) {
    const index = next.indexOf(marker);
    if (index > 0) {
      next = next.slice(0, index).trim();
      break;
    }
  }

  return next.replace(/^(이 문장 뒤에|문장 뒤에|뒤에|다음 문장을)\s*/g, "").replace(/처럼$/g, "").trim();
}

function normalizeSuggestedText(suggestion, { forAppend = false } = {}) {
  const original = suggestion?.original_text || "";
  const raw = (suggestion?.suggested_text || "").trim();
  if (!raw) return "";

  const quoted = extractQuotedCandidate(raw);
  const asksToAppend = /뒤에|추가|이어|결과 문장/.test(raw);

  if (forAppend) {
    if (quoted && quoted !== original) return quoted;
    if (raw.startsWith(original)) return cleanInstructionalTail(raw.slice(original.length));
    return cleanInstructionalTail(raw);
  }

  if (asksToAppend && quoted && quoted !== original) {
    return `${original} ${quoted}`.trim();
  }

  if (quoted && quoted !== original && raw.length > quoted.length + 12 && !raw.includes(original)) {
    return quoted;
  }

  if (raw.startsWith(original) && raw.length > original.length + 8) {
    return cleanInstructionalTail(raw.slice(original.length));
  }

  return cleanInstructionalTail(raw);
}

function hasInstructionalRewrite(text) {
  return /작성하세요|작성해 주세요|작성해주세요|추가해 주세요|추가해주세요|구체화하세요|구체화해 주세요|구체화했습니다|보완하세요|보완해 주세요|보완해주세요|적어 주세요|적어주세요|넣어 주세요|넣어주세요|기준으로 구체화|이 경험에서 맡은 역할/.test(
    text || "",
  );
}

function hasExcessivePlaceholders(text) {
  const matches = text.match(/\[[^\]]+\]/g) || [];
  const placeholderChars = matches.reduce((sum, item) => sum + item.length, 0);
  return placeholderChars / Math.max(text.length, 1) > 0.28 || /저는\s*\[[^\]]+\]/.test(text);
}

function buildResult({ text, applied, warning = null, appliedRange = null }) {
  const message = applied ? warning || "적용되었습니다." : warning || "적용할 문장을 찾지 못했습니다.";
  return {
    text,
    updatedText: text,
    applied,
    warning,
    message,
    appliedRange,
  };
}

function findExactRange(currentText, suggestion, original) {
  const start = suggestion?.start_index;
  const end = suggestion?.end_index;
  if (
    Number.isInteger(start) &&
    Number.isInteger(end) &&
    start >= 0 &&
    end > start &&
    end <= currentText.length &&
    currentText.slice(start, end) === original
  ) {
    return { start, end, warning: null };
  }
  return null;
}

function findClosestOriginalRange(currentText, suggestion, original) {
  const matches = [];
  let index = currentText.indexOf(original);
  while (index >= 0) {
    matches.push({ start: index, end: index + original.length });
    index = currentText.indexOf(original, index + Math.max(original.length, 1));
  }

  if (!matches.length) return null;
  if (matches.length === 1) return { ...matches[0], warning: null };

  if (Number.isInteger(suggestion?.start_index)) {
    const target = suggestion.start_index;
    const closest = matches.reduce((best, item) =>
      Math.abs(item.start - target) < Math.abs(best.start - target) ? item : best,
    );
    return {
      ...closest,
      warning: "같은 원문이 여러 번 있어 AI가 표시한 위치와 가장 가까운 문장을 수정했습니다.",
    };
  }

  return {
    ...matches[0],
    warning: "같은 원문이 여러 번 있어 첫 번째 문장을 수정했습니다.",
  };
}

function findTargetRange(currentText, suggestion, original) {
  return findExactRange(currentText, suggestion, original) || findClosestOriginalRange(currentText, suggestion, original);
}

function expandToParagraphRange(currentText, range) {
  const before = currentText.slice(0, range.start);
  const after = currentText.slice(range.end);
  const beforeMatch = before.match(/\n\s*\n[^\n]*$/);
  const start = beforeMatch ? before.length - beforeMatch[0].length + beforeMatch[0].match(/^\n\s*\n/)[0].length : 0;
  const afterMatch = after.match(/\n\s*\n/);
  const end = afterMatch ? range.end + afterMatch.index : currentText.length;
  return { start, end };
}

export function resolveSuggestionRange(text, suggestion) {
  if (!text || !suggestion?.original_text) return null;
  return findTargetRange(text, suggestion, suggestion.original_text.trim());
}

export function applySuggestionToText(currentText, suggestion) {
  if (!currentText || !suggestion) {
    return buildResult({ text: currentText, applied: false, warning: "적용할 문장을 찾지 못했습니다." });
  }

  if (suggestion.can_apply === false) {
    return buildResult({
      text: currentText,
      applied: false,
      warning: "이 추천문은 바로 적용하기 어렵습니다. 내용을 참고해 직접 수정해 주세요.",
    });
  }

  const original = (suggestion.original_text || "").trim();
  if (!original) {
    return buildResult({ text: currentText, applied: false, warning: "원문 문장이 비어 있습니다." });
  }

  const applyType = suggestion.apply_type || "replace";
  const targetRange = findTargetRange(currentText, suggestion, original);
  if (!targetRange) {
    return buildResult({
      text: currentText,
      applied: false,
      warning: "원문에서 해당 문장을 찾지 못했습니다. 직접 확인해 주세요.",
    });
  }

  const suggested = normalizeSuggestedText(suggestion, { forAppend: applyType === "append_after" });
  if (!suggested.trim()) {
    return buildResult({ text: currentText, applied: false, warning: "제안 문장이 비어 있습니다." });
  }
  if (hasInstructionalRewrite(suggested) || hasExcessivePlaceholders(suggested)) {
    return buildResult({
      text: currentText,
      applied: false,
      warning: "이 추천문은 바로 적용하기 어렵습니다. 내용을 참고해 직접 수정해 주세요.",
    });
  }
  if (suggested.trim().length < 12) {
    return buildResult({
      text: currentText,
      applied: false,
      warning: "추천 문장이 너무 짧아 바로 적용하기 어렵습니다.",
    });
  }

  if (applyType === "append_after") {
    const insertion = `${currentText[targetRange.end] === "\n" ? "" : "\n"}${suggested}`;
    const text = currentText.slice(0, targetRange.end) + insertion + currentText.slice(targetRange.end);
    return buildResult({
      text,
      applied: true,
      warning: targetRange.warning,
      appliedRange: { start: targetRange.end, end: targetRange.end + insertion.length },
    });
  }

  if (applyType === "rewrite_paragraph") {
    const paragraphRange = expandToParagraphRange(currentText, targetRange);
    const text = currentText.slice(0, paragraphRange.start) + suggested + currentText.slice(paragraphRange.end);
    return buildResult({
      text,
      applied: true,
      warning: targetRange.warning,
      appliedRange: paragraphRange,
    });
  }

  const text = currentText.slice(0, targetRange.start) + suggested + currentText.slice(targetRange.end);
  return buildResult({
    text,
    applied: true,
    warning: targetRange.warning,
    appliedRange: { start: targetRange.start, end: targetRange.start + suggested.length },
  });
}

export const suggestionCategoryLabels = {
  job_fit: "직무 연결",
  specificity: "구체성",
  achievement: "성과 표현",
  writing_quality: "문장력",
  structure: "구조",
  keyword_match: "키워드",
  tone: "톤",
  redundancy: "중복 표현",
  clarity: "명확성",
};

export const suggestionSeverityLabels = {
  high: "우선 보완",
  medium: "보완 권장",
  low: "가벼운 수정",
};
