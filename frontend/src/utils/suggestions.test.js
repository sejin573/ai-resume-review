import assert from "node:assert/strict";
import test from "node:test";

import { applySuggestionToText } from "./suggestions.js";

test("replace applies suggested text to the target range", () => {
  const text = "저는 열심히 노력했습니다.";
  const result = applySuggestionToText(text, {
    original_text: "열심히 노력했습니다.",
    suggested_text: "고객 문의 30건을 유형별로 정리했습니다.",
    apply_type: "replace",
    start_index: 3,
    end_index: 13,
  });

  assert.equal(result.applied, true);
  assert.equal(result.text, "저는 고객 문의 30건을 유형별로 정리했습니다.");
});

test("append_after inserts the usable suggested sentence after original text", () => {
  const text = "문제를 정리했습니다.";
  const result = applySuggestionToText(text, {
    original_text: "문제를 정리했습니다.",
    suggested_text: "이 문장 뒤에 '반복 문의를 5개 유형으로 나눠 처리 시간을 줄였습니다.' 추가해 주세요",
    apply_type: "append_after",
  });

  assert.equal(result.applied, true);
  assert.equal(result.text, "문제를 정리했습니다.\n반복 문의를 5개 유형으로 나눠 처리 시간을 줄였습니다.");
});

test("rewrite_paragraph replaces the paragraph containing original text", () => {
  const text = "첫 문단입니다.\n\n문제를 정리했습니다. 더 노력했습니다.\n\n마지막 문단입니다.";
  const result = applySuggestionToText(text, {
    original_text: "문제를 정리했습니다.",
    suggested_text: "반복 문의를 분석하고 처리 기준을 문서화했습니다.",
    apply_type: "rewrite_paragraph",
  });

  assert.equal(result.applied, true);
  assert.equal(result.text, "첫 문단입니다.\n\n반복 문의를 분석하고 처리 기준을 문서화했습니다.\n\n마지막 문단입니다.");
});

test("duplicate original_text uses the match closest to start_index", () => {
  const text = "문제를 정리했습니다.\n다른 경험입니다.\n문제를 정리했습니다.";
  const start = text.lastIndexOf("문제를 정리했습니다.");
  const result = applySuggestionToText(text, {
    original_text: "문제를 정리했습니다.",
    suggested_text: "두 번째 문제를 기준표로 정리했습니다.",
    apply_type: "replace",
    start_index: start,
    end_index: start + "문제를 정리했습니다.".length,
  });

  assert.equal(result.applied, true);
  assert.equal(result.text, "문제를 정리했습니다.\n다른 경험입니다.\n두 번째 문제를 기준표로 정리했습니다.");
});

test("failed match returns applied false", () => {
  const result = applySuggestionToText("원문입니다.", {
    original_text: "없는 문장입니다.",
    suggested_text: "수정 문장입니다.",
    apply_type: "replace",
  });

  assert.equal(result.applied, false);
  assert.equal(result.text, "원문입니다.");
});

test("empty suggested_text is not applied", () => {
  const result = applySuggestionToText("원문입니다.", {
    original_text: "원문입니다.",
    suggested_text: "",
    apply_type: "replace",
  });

  assert.equal(result.applied, false);
  assert.equal(result.text, "원문입니다.");
});

test("instruction-like suggested_text is not applied", () => {
  const result = applySuggestionToText("저는 새로운 환경에 적응했습니다.", {
    original_text: "저는 새로운 환경에 적응했습니다.",
    suggested_text: "이 경험에서 맡은 역할과 사용한 방법, 결과를 [기간]과 [성과 수치] 기준으로 구체화했습니다.",
    apply_type: "replace",
  });

  assert.equal(result.applied, false);
  assert.match(result.message, /직접 수정/);
});

test("can_apply false is not applied", () => {
  const result = applySuggestionToText("문제를 분석했습니다.", {
    original_text: "문제를 분석했습니다.",
    suggested_text: "문제를 분석하고 처리 기준을 정리했습니다.",
    apply_type: "replace",
    can_apply: false,
  });

  assert.equal(result.applied, false);
  assert.equal(result.text, "문제를 분석했습니다.");
});
