import { useMemo, useState } from "react";

const presetInstructions = [
  "더 구체적으로 바꿔줘",
  "성과 중심으로 바꿔줘",
  "문장을 더 자연스럽게 바꿔줘",
  "신입 지원자답게 바꿔줘",
  "700자로 줄여줘",
  "면접에서 설명하기 쉽게 바꿔줘",
  "너무 과장된 표현은 줄여줘",
];

function copyText(text) {
  return navigator.clipboard.writeText(text);
}

export default function RefinementPanel({ history, onSubmit, onApply, activeText, loading }) {
  const [customInstruction, setCustomInstruction] = useState("");
  const [error, setError] = useState("");

  const orderedHistory = useMemo(() => [...(history || [])].sort((a, b) => new Date(a.created_at) - new Date(b.created_at)), [history]);

  const submitInstruction = async (instruction) => {
    if (!instruction.trim()) {
      setError("리파인 지시를 입력해 주세요.");
      return;
    }
    setError("");
    try {
      await onSubmit(instruction);
      setCustomInstruction("");
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <section className="panel">
      <div className="section-header">
        <h2>채팅형 리파인먼트</h2>
        <button className="ghost-button" type="button" onClick={() => copyText(activeText)}>
          현재 문안 복사
        </button>
      </div>
      <div className="preset-grid">
        {presetInstructions.map((instruction) => (
          <button
            key={instruction}
            className="chip-button"
            type="button"
            disabled={loading}
            onClick={() => submitInstruction(instruction)}
          >
            {instruction}
          </button>
        ))}
      </div>
      <label className="field top-gap">
        <span>직접 지시하기</span>
        <textarea
          rows={3}
          value={customInstruction}
          onChange={(event) => setCustomInstruction(event.target.value)}
          placeholder="예: 마지막 문단을 더 차분한 톤으로 정리해줘"
        />
      </label>
      {error ? <div className="error-box">{error}</div> : null}
      <div className="actions-row top-gap">
        <button className="primary-button" type="button" disabled={loading} onClick={() => submitInstruction(customInstruction)}>
          {loading ? "리파인 중..." : "리파인 요청"}
        </button>
      </div>

      <div className="chat-thread">
        {orderedHistory.length === 0 ? (
          <div className="chat-empty">아직 리파인 요청이 없습니다. 버튼을 눌러 문안을 더 다듬어 보세요.</div>
        ) : null}
        {orderedHistory.map((item) => (
          <div key={`${item.id}-${item.created_at}`} className="chat-group">
            <div className="chat-bubble user-bubble">
              <div className="chat-meta">사용자 요청</div>
              <strong>{item.instruction}</strong>
              <p>{item.current_text}</p>
            </div>
            <div className="chat-bubble assistant-bubble">
              <div className="chat-meta">AI 응답</div>
              <p>{item.change_summary}</p>
              <div className="long-text">{item.refined_text}</div>
              {item.warnings?.length ? (
                <ul className="compact-list">
                  {item.warnings.map((warning) => (
                    <li key={warning}>{warning}</li>
                  ))}
                </ul>
              ) : null}
              <div className="button-row top-gap">
                <button className="ghost-button" type="button" onClick={() => onApply(item.refined_text)}>
                  이 문안 적용
                </button>
                <button className="ghost-button" type="button" onClick={() => copyText(item.refined_text)}>
                  리파인 문안 복사
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
