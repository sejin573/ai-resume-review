import { useEffect, useState } from "react";
import { api } from "../api/client";
import Button from "./Button";
import CopyButton from "./CopyButton";

function downloadTextFile(filename, text) {
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function safeFileName(value) {
  return String(value || "coverfit")
    .replace(/[\\/:*?"<>|]/g, "")
    .replace(/\s+/g, "_")
    .slice(0, 40);
}

export default function FinalDocumentPanel({
  reviewId,
  jobRole,
  initialText,
  savedDocument,
  onSave,
  onApplyToEditor,
}) {
  const [text, setText] = useState(initialText || "");
  const [source, setSource] = useState(savedDocument?.source || "manual_edit");
  const [saving, setSaving] = useState(false);
  const [exportingPdf, setExportingPdf] = useState(false);
  const [status, setStatus] = useState(savedDocument ? "최종본 저장 완료" : "AI 검토 후 최종본으로 저장하세요.");

  useEffect(() => {
    setText(savedDocument?.final_text || initialText || "");
    setSource(savedDocument?.source || "manual_edit");
    setStatus(savedDocument ? "최종본 저장 완료" : "AI 검토 후 최종본으로 저장하세요.");
  }, [initialText, savedDocument]);

  const txtFileName = `coverfit_final_${safeFileName(jobRole)}_${new Date().toISOString().slice(0, 10).replaceAll("-", "")}.txt`;
  const pdfFileName = txtFileName.replace(".txt", ".pdf");

  const handleSave = async () => {
    if (!reviewId || !text.trim()) return null;
    setSaving(true);
    setStatus("최종본 저장 중...");
    try {
      const saved = await onSave({ final_text: text, source });
      setStatus(saved?.updated_at ? `최종본 저장 완료 · ${new Date(saved.updated_at).toLocaleString()}` : "최종본 저장 완료");
      return saved;
    } catch (err) {
      setStatus(err.message || "저장 중 오류가 발생했습니다.");
      throw err;
    } finally {
      setSaving(false);
    }
  };

  const handleExportPdf = async () => {
    if (!reviewId || text.trim().length < 20) return;
    setExportingPdf(true);
    setStatus("PDF 준비 중...");
    try {
      await handleSave();
      await api.exportReviewPdf(reviewId, pdfFileName);
      setStatus("PDF 내보내기 완료");
    } catch (err) {
      setStatus(err.message || "PDF 내보내기 중 오류가 발생했습니다.");
    } finally {
      setExportingPdf(false);
    }
  };

  return (
    <section className="final-document-panel final-submit-panel">
      <div className="final-document-head">
        <div>
          <span className="file-kicker">FINAL STEP</span>
          <h3>완성본 만들기</h3>
          <p>AI 검토 결과를 반영해 마지막 문장을 직접 다듬고, 저장 후 PDF로 내려받을 수 있습니다.</p>
        </div>
        <div className="final-save-status">{status}</div>
      </div>

      <div className="final-flow-strip" aria-label="최종본 완성 흐름">
        <span>1. AI 검토</span>
        <span>2. 문장 수정</span>
        <span>3. 최종본 저장</span>
        <span>4. PDF 내보내기</span>
      </div>

      <label className="final-source-select">
        <span>현재 문안 기준</span>
        <select value={source} onChange={(event) => setSource(event.target.value)}>
          <option value="ai_improved">AI 개선문</option>
          <option value="refinement">리파인 결과</option>
          <option value="manual_edit">직접 수정</option>
        </select>
      </label>

      <textarea
        className="final-document-textarea"
        value={text}
        onChange={(event) => {
          setText(event.target.value);
          setSource("manual_edit");
          setStatus("수정 중 · 저장 필요");
        }}
        placeholder="제출용 자기소개서를 마지막으로 정리하세요."
      />

      <div className="final-document-actions">
        <Button type="button" onClick={handleSave} disabled={saving || text.trim().length < 20}>
          {saving ? "저장 중" : "최종본 저장"}
        </Button>
        <Button type="button" onClick={handleExportPdf} disabled={exportingPdf || text.trim().length < 20}>
          {exportingPdf ? "PDF 준비 중" : "PDF 내보내기"}
        </Button>
        <CopyButton text={text} label="문안 복사" />
        <Button type="button" variant="ghost" onClick={() => downloadTextFile(txtFileName, text)} disabled={!text.trim()}>
          TXT 저장
        </Button>
        {onApplyToEditor ? (
          <Button type="button" variant="secondary" onClick={() => onApplyToEditor(text)} disabled={!text.trim()}>
            에디터에 반영
          </Button>
        ) : null}
      </div>
    </section>
  );
}
