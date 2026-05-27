function copyText(text) {
  return navigator.clipboard.writeText(text);
}

function downloadText(text, fileName) {
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  anchor.click();
  URL.revokeObjectURL(url);
}

export default function ImprovedCoverLetter({ text, onCopyLabel = "개선문 복사", onDownloadLabel = "TXT로 저장" }) {
  return (
    <section className="panel">
      <div className="section-header">
        <h2>개선된 자기소개서</h2>
        <div className="button-row">
          <button className="ghost-button" type="button" onClick={() => copyText(text)}>
            {onCopyLabel}
          </button>
          <button className="ghost-button" type="button" onClick={() => downloadText(text, "improved_cover_letter.txt")}>
            {onDownloadLabel}
          </button>
        </div>
      </div>
      <div className="long-text">{text}</div>
    </section>
  );
}
