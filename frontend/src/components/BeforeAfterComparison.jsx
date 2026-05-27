function copyText(text) {
  return navigator.clipboard.writeText(text);
}

export default function BeforeAfterComparison({ originalText, improvedText }) {
  return (
    <section className="panel">
      <div className="section-header">
        <h2>수정 전 / 후 비교</h2>
      </div>
      <div className="comparison-grid">
        <div className="comparison-card">
          <div className="section-header">
            <h3>원문</h3>
            <button className="ghost-button" type="button" onClick={() => copyText(originalText)}>
              원문 복사
            </button>
          </div>
          <div className="long-text">{originalText}</div>
        </div>
        <div className="comparison-card">
          <div className="section-header">
            <h3>개선문</h3>
            <button className="ghost-button" type="button" onClick={() => copyText(improvedText)}>
              개선문 복사
            </button>
          </div>
          <div className="long-text">{improvedText}</div>
        </div>
      </div>
    </section>
  );
}
