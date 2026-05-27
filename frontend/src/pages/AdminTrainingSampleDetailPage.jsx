import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import Layout from "../components/Layout";

function WarningBanner({ kind, children }) {
  return <div className={`warning-banner ${kind}`}>{children}</div>;
}

function JsonPanel({ title, data, raw = false }) {
  const content = raw ? data : JSON.stringify(data, null, 2);
  return (
    <section className="panel">
      <h2>{title}</h2>
      <pre className="json-block">{typeof content === "string" ? content : JSON.stringify(content, null, 2)}</pre>
    </section>
  );
}

export default function AdminTrainingSampleDetailPage() {
  const { id } = useParams();
  const [sample, setSample] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [action, setAction] = useState("reviewed");
  const [qualityScore, setQualityScore] = useState("85");
  const [notes, setNotes] = useState("");
  const [rawAssistantView, setRawAssistantView] = useState(false);

  const loadSample = async () => {
    setLoading(true);
    try {
      const data = await api.getTrainingSample(id);
      setSample(data);
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSample();
  }, [id]);

  const assistantPayload = useMemo(() => {
    const assistantContent = sample?.training_record_json?.messages?.[2]?.content;
    if (!assistantContent) return null;
    try {
      return JSON.parse(assistantContent);
    } catch {
      return null;
    }
  }, [sample]);

  const blockedBulkReview = sample?.reviews?.some((review) =>
    (review.notes || "").includes("Bulk reviewed for local pipeline testing"),
  );

  const submitReview = async (nextStatus) => {
    if (nextStatus === "reviewed" && !qualityScore) {
      setError("Reviewed 상태로 저장하려면 quality_score가 필요합니다.");
      return;
    }
    if (nextStatus === "rejected" && !notes.trim()) {
      setError("Reject 하려면 reviewer note를 입력해야 합니다.");
      return;
    }

    setSaving(true);
    setError("");
    try {
      await api.reviewTrainingSample(id, {
        status: nextStatus,
        quality_score: nextStatus === "reviewed" ? Number(qualityScore) : null,
        notes,
      });
      await loadSample();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Layout title="학습 샘플 상세" subtitle="메시지, 점수, 검토 이력을 보고 승인 여부를 결정합니다.">
      <div className="actions-row page-actions">
        <Link to="/admin/training-samples">목록으로 돌아가기</Link>
      </div>
      {loading ? <p>샘플 상세를 불러오는 중입니다...</p> : null}
      {error ? <div className="error-box">{error}</div> : null}
      {!loading && sample ? (
        <div className="results-layout">
          {sample.source_type === "manual_seed" ? (
            <WarningBanner kind="info">
              manual_seed samples are fictional and useful for pipeline testing, but they are not enough to train a
              high-quality production model.
            </WarningBanner>
          ) : null}
          {sample.source_type === "user_consent" ? (
            <WarningBanner kind="warning">
              User-consented samples may contain sensitive content. Review anonymization and PII risk before approving.
            </WarningBanner>
          ) : null}
          {blockedBulkReview ? (
            <WarningBanner kind="danger">
              This sample was bulk-reviewed for local testing. Do not use as production-quality reviewed data without
              manual inspection.
            </WarningBanner>
          ) : null}

          <section className="panel">
            <div className="section-header">
              <h2>기본 정보</h2>
              <span className={`status-pill ${sample.quality_status}`}>{sample.quality_status}</span>
            </div>
            <div className="detail-grid">
              <div>
                <span className="detail-label">sample_id</span>
                <strong>{sample.sample_id}</strong>
              </div>
              <div>
                <span className="detail-label">job_role</span>
                <strong>{sample.job_role}</strong>
              </div>
              <div>
                <span className="detail-label">source_type</span>
                <strong>{sample.source_type || "-"}</strong>
              </div>
              <div>
                <span className="detail-label">sample_kind</span>
                <strong>{sample.sample_kind}</strong>
              </div>
              <div>
                <span className="detail-label">total_score</span>
                <strong>{sample.total_score}</strong>
              </div>
              <div>
                <span className="detail-label">pii_risk_score</span>
                <strong>{sample.pii_risk_score}</strong>
              </div>
              <div>
                <span className="detail-label">reviewed_by_human</span>
                <strong>{sample.reviewed_by_human ? "true" : "false"}</strong>
              </div>
              <div>
                <span className="detail-label">contains_real_user_data</span>
                <strong>{sample.contains_real_user_data ? "true" : "false"}</strong>
              </div>
              <div>
                <span className="detail-label">valid_for_export</span>
                <strong>{sample.valid_for_export ? "true" : "false"}</strong>
              </div>
              <div>
                <span className="detail-label">created_at</span>
                <strong>{new Date(sample.created_at).toLocaleString()}</strong>
              </div>
            </div>
            {sample.validation_errors.length > 0 ? (
              <div className="validation-box">
                <strong>validation_errors</strong>
                <ul className="compact-list">
                  {sample.validation_errors.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </section>

          <section className="panel">
            <h2>Source 정보</h2>
            {sample.data_source ? (
              <div className="detail-grid">
                <div>
                  <span className="detail-label">source_name</span>
                  <strong>{sample.data_source.source_name}</strong>
                </div>
                <div>
                  <span className="detail-label">license_status</span>
                  <strong>{sample.data_source.license_status}</strong>
                </div>
                <div>
                  <span className="detail-label">source_type</span>
                  <strong>{sample.data_source.source_type}</strong>
                </div>
                <div>
                  <span className="detail-label">is_active</span>
                  <strong>{sample.data_source.is_active ? "true" : "false"}</strong>
                </div>
                <div className="full-width">
                  <span className="detail-label">license_note</span>
                  <p className="long-text">{sample.data_source.license_note || "-"}</p>
                </div>
                <div className="full-width">
                  <span className="detail-label">source_url</span>
                  <p className="long-text">{sample.data_source.source_url || "-"}</p>
                </div>
              </div>
            ) : (
              <p className="muted">연결된 data source 정보가 없습니다.</p>
            )}
          </section>

          <section className="panel">
            <h2>Review actions</h2>
            <div className="review-form-grid">
              <label className="field">
                <span>action</span>
                <select value={action} onChange={(event) => setAction(event.target.value)}>
                  <option value="reviewed">Mark as reviewed</option>
                  <option value="rejected">Reject</option>
                </select>
              </label>
              <label className="field">
                <span>quality_score</span>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={qualityScore}
                  onChange={(event) => setQualityScore(event.target.value)}
                  placeholder="0-100"
                />
              </label>
            </div>
            <label className="field">
              <span>reviewer note</span>
              <textarea
                rows={5}
                value={notes}
                onChange={(event) => setNotes(event.target.value)}
                placeholder="검토 의견을 남겨주세요. reject 시 note가 필수입니다."
              />
            </label>
            <div className="actions-row">
              <button className="primary-button" disabled={saving} onClick={() => submitReview("reviewed")}>
                {saving && action === "reviewed" ? "저장 중..." : "Mark as reviewed"}
              </button>
              <button className="secondary-button danger-button" disabled={saving} onClick={() => submitReview("rejected")}>
                Reject
              </button>
            </div>
          </section>

          <JsonPanel title="input_payload" data={sample.input_payload} />
          <JsonPanel title="output_payload" data={sample.output_payload} />

          <section className="panel">
            <div className="section-header">
              <h2>training_record_json</h2>
              <label className="checkbox-row compact-checkbox">
                <input
                  type="checkbox"
                  checked={rawAssistantView}
                  onChange={(event) => setRawAssistantView(event.target.checked)}
                />
                <span>assistant raw JSON view</span>
              </label>
            </div>
            {sample.training_record_json?.messages?.map((message) => (
              <div key={`${message.role}-${message.content.slice(0, 20)}`} className="message-card">
                <div className="message-role">{message.role}</div>
                {message.role === "assistant" && assistantPayload && !rawAssistantView ? (
                  <pre className="json-block">{JSON.stringify(assistantPayload, null, 2)}</pre>
                ) : (
                  <pre className="json-block">{message.content}</pre>
                )}
              </div>
            ))}
            <div className="top-gap">
              <strong>raw training_record_json</strong>
              <pre className="json-block">{JSON.stringify(sample.training_record_json, null, 2)}</pre>
            </div>
          </section>

          <section className="panel">
            <h2>Previous review notes</h2>
            {sample.reviews.length === 0 ? <p className="muted">아직 기록된 review note가 없습니다.</p> : null}
            <div className="history-list">
              {sample.reviews.map((review) => (
                <div className="history-item review-item" key={review.id}>
                  <div>
                    <strong>{review.status}</strong>
                    <p>{review.notes || "메모 없음"}</p>
                  </div>
                  <div className="review-meta">
                    <span>quality_score: {review.quality_score ?? "-"}</span>
                    <span>{new Date(review.created_at).toLocaleString()}</span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      ) : null}
    </Layout>
  );
}
