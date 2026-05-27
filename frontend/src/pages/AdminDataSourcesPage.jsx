import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import Layout from "../components/Layout";

const initialSourceForm = {
  source_name: "",
  source_type: "manual_seed",
  license_status: "approved",
  license_note: "",
  source_url: "",
  permission_document_path: "",
  is_active: true,
};

const sourceTypes = ["manual_seed", "admin_upload", "partner_dataset", "public_dataset", "approved_url_list"];
const licenseStatuses = ["approved", "needs_review", "unknown", "rejected"];

function compactPayload(payload) {
  return Object.fromEntries(
    Object.entries(payload).map(([key, value]) => [key, typeof value === "string" ? value.trim() || null : value]),
  );
}

function statusTone(status) {
  if (status === "approved" || status === "anonymized" || status === "curated" || status === "exported") return "reviewed";
  if (status === "rejected") return "rejected";
  return "draft";
}

export default function AdminDataSourcesPage() {
  const [sources, setSources] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [sourceForm, setSourceForm] = useState(initialSourceForm);
  const [selectedSourceId, setSelectedSourceId] = useState("");
  const [importType, setImportType] = useState("csv");
  const [uploadFile, setUploadFile] = useState(null);
  const [approvedUrls, setApprovedUrls] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [actionMessage, setActionMessage] = useState("");
  const [error, setError] = useState("");
  const [rejectingId, setRejectingId] = useState(null);
  const [rejectReason, setRejectReason] = useState("");

  const loadAdminData = async () => {
    setLoading(true);
    try {
      const [sourceData, documentData] = await Promise.all([api.getDataSources(), api.getImportedDocuments()]);
      setSources(sourceData);
      setDocuments(documentData);
      setSelectedSourceId((current) => current || sourceData.find((source) => source.license_status === "approved")?.id || "");
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAdminData();
  }, []);

  const approvedSources = useMemo(
    () => sources.filter((source) => source.license_status === "approved" && source.is_active),
    [sources],
  );

  const summary = useMemo(
    () => ({
      sources: sources.length,
      approvedSources: approvedSources.length,
      imported: documents.length,
      readyForSample: documents.filter((document) => document.import_status === "anonymized").length,
    }),
    [approvedSources.length, documents],
  );

  const updateSourceForm = (key, value) => {
    setSourceForm((prev) => ({ ...prev, [key]: value }));
  };

  const submitSource = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError("");
    setActionMessage("");
    try {
      const payload = compactPayload(sourceForm);
      await api.createDataSource(payload);
      setSourceForm(initialSourceForm);
      setActionMessage("Data source를 등록했습니다.");
      await loadAdminData();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const submitImport = async (event) => {
    event.preventDefault();
    if (!selectedSourceId) {
      setError("Import할 data source를 선택해 주세요.");
      return;
    }
    if (importType !== "approved_urls" && !uploadFile) {
      setError("업로드할 파일을 선택해 주세요.");
      return;
    }

    setSaving(true);
    setError("");
    setActionMessage("");
    try {
      let imported;
      if (importType === "csv") {
        imported = await api.importCsv(selectedSourceId, uploadFile);
      } else if (importType === "jsonl") {
        imported = await api.importJsonl(selectedSourceId, uploadFile);
      } else {
        const urls = approvedUrls
          .split(/\r?\n/)
          .map((url) => url.trim())
          .filter(Boolean);
        imported = await api.importApprovedUrls({ data_source_id: Number(selectedSourceId), urls });
      }
      setUploadFile(null);
      setApprovedUrls("");
      setActionMessage(`${imported.length}개 문서를 import했습니다.`);
      await loadAdminData();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const runDocumentAction = async (documentId, action) => {
    setSaving(true);
    setError("");
    setActionMessage("");
    try {
      if (action === "anonymize") {
        await api.anonymizeImportedDocument(documentId);
        setActionMessage("문서를 익명화했습니다.");
      }
      if (action === "sample") {
        const result = await api.createTrainingSampleFromDocument(documentId);
        setActionMessage(`Training sample #${result.training_sample_id}을 생성했습니다.`);
      }
      if (action === "reject") {
        await api.rejectImportedDocument(documentId, rejectReason);
        setRejectingId(null);
        setRejectReason("");
        setActionMessage("문서를 reject 처리했습니다.");
      }
      await loadAdminData();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Layout title="데이터 소스 관리" subtitle="허가된 원천만 등록하고, import 문서를 익명화한 뒤 학습 샘플로 보냅니다.">
      <section className="stats-grid">
        <div className="panel stat-panel">
          <span>Data sources</span>
          <strong>{summary.sources}</strong>
        </div>
        <div className="panel stat-panel">
          <span>Approved active</span>
          <strong>{summary.approvedSources}</strong>
        </div>
        <div className="panel stat-panel">
          <span>Imported documents</span>
          <strong>{summary.imported}</strong>
        </div>
        <div className="panel stat-panel">
          <span>Ready for sample</span>
          <strong>{summary.readyForSample}</strong>
        </div>
      </section>

      {loading ? <p>관리자 데이터를 불러오는 중입니다...</p> : null}
      {error ? <div className="error-box">{error}</div> : null}
      {actionMessage ? <div className="success-box">{actionMessage}</div> : null}

      <div className="results-layout">
        <section className="panel">
          <div className="section-header">
            <h2>Data source 등록</h2>
            <Link to="/admin/training-samples">샘플 검토</Link>
          </div>
          <form className="admin-source-form" onSubmit={submitSource}>
            <div className="review-form-grid">
              <label className="field">
                <span>source_name</span>
                <input
                  value={sourceForm.source_name}
                  onChange={(event) => updateSourceForm("source_name", event.target.value)}
                  placeholder="Fictional Manual Seed Dataset"
                  required
                />
              </label>
              <label className="field">
                <span>source_type</span>
                <select value={sourceForm.source_type} onChange={(event) => updateSourceForm("source_type", event.target.value)}>
                  {sourceTypes.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>license_status</span>
                <select
                  value={sourceForm.license_status}
                  onChange={(event) => updateSourceForm("license_status", event.target.value)}
                >
                  {licenseStatuses.map((status) => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>source_url</span>
                <input
                  value={sourceForm.source_url}
                  onChange={(event) => updateSourceForm("source_url", event.target.value)}
                  placeholder="approved_url_list일 때 필수"
                />
              </label>
            </div>
            <label className="field">
              <span>license_note</span>
              <textarea
                rows={4}
                value={sourceForm.license_note}
                onChange={(event) => updateSourceForm("license_note", event.target.value)}
                placeholder="사용 권리, 허가 문서, 생성 방식 등을 남겨주세요."
              />
            </label>
            <label className="checkbox-row compact-checkbox">
              <input
                type="checkbox"
                checked={sourceForm.is_active}
                onChange={(event) => updateSourceForm("is_active", event.target.checked)}
              />
              active
            </label>
            <button className="primary-button" disabled={saving}>
              {saving ? "저장 중..." : "Data source 생성"}
            </button>
          </form>
        </section>

        <section className="panel">
          <h2>Import</h2>
          <form className="admin-source-form" onSubmit={submitImport}>
            <label className="field">
              <span>approved data source</span>
              <select value={selectedSourceId} onChange={(event) => setSelectedSourceId(event.target.value)}>
                <option value="">선택</option>
                {approvedSources.map((source) => (
                  <option key={source.id} value={source.id}>
                    #{source.id} {source.source_name} ({source.source_type})
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              <span>import_type</span>
              <select value={importType} onChange={(event) => setImportType(event.target.value)}>
                <option value="csv">CSV</option>
                <option value="jsonl">JSONL</option>
                <option value="approved_urls">Approved URLs</option>
              </select>
            </label>
            {importType === "approved_urls" ? (
              <label className="field">
                <span>urls</span>
                <textarea
                  rows={8}
                  value={approvedUrls}
                  onChange={(event) => setApprovedUrls(event.target.value)}
                  placeholder="한 줄에 하나씩 입력"
                />
              </label>
            ) : (
              <label className="field">
                <span>file</span>
                <input type="file" accept={importType === "csv" ? ".csv,text/csv" : ".jsonl,.ndjson,application/json"} onChange={(event) => setUploadFile(event.target.files?.[0] || null)} />
              </label>
            )}
            <button className="primary-button" disabled={saving}>
              {saving ? "Import 중..." : "Import 실행"}
            </button>
          </form>
        </section>
      </div>

      <section className="panel">
        <div className="section-header">
          <h2>Data sources</h2>
          <span className="muted">approved 상태만 import 가능합니다.</span>
        </div>
        <div className="table-shell">
          <table className="data-table">
            <thead>
              <tr>
                <th>id</th>
                <th>source_name</th>
                <th>source_type</th>
                <th>license_status</th>
                <th>active</th>
                <th>license_note</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((source) => (
                <tr key={source.id}>
                  <td>{source.id}</td>
                  <td>{source.source_name}</td>
                  <td>{source.source_type}</td>
                  <td>
                    <span className={`status-pill ${statusTone(source.license_status)}`}>{source.license_status}</span>
                  </td>
                  <td>{source.is_active ? "true" : "false"}</td>
                  <td>{source.license_note || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="section-header">
          <h2>Imported documents</h2>
          <span className="muted">익명화 후 accepted_cover_letter만 sample 생성 가능</span>
        </div>
        <div className="table-shell">
          <table className="data-table">
            <thead>
              <tr>
                <th>id</th>
                <th>source</th>
                <th>type</th>
                <th>job_role</th>
                <th>status</th>
                <th>pii</th>
                <th>title</th>
                <th>actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((document) => (
                <tr key={document.id}>
                  <td>{document.id}</td>
                  <td>{document.data_source_id}</td>
                  <td>{document.document_type}</td>
                  <td>{document.job_role || "-"}</td>
                  <td>
                    <span className={`status-pill ${statusTone(document.import_status)}`}>{document.import_status}</span>
                  </td>
                  <td>{document.pii_risk_score}</td>
                  <td>{document.original_title || document.source_reference || "-"}</td>
                  <td>
                    {rejectingId === document.id ? (
                      <div className="inline-action-stack">
                        <input
                          value={rejectReason}
                          onChange={(event) => setRejectReason(event.target.value)}
                          placeholder="reject reason"
                        />
                        <button className="secondary-button danger-button" disabled={saving} onClick={() => runDocumentAction(document.id, "reject")}>
                          Confirm reject
                        </button>
                      </div>
                    ) : (
                      <div className="actions-row compact-actions">
                        <button className="secondary-button" disabled={saving} onClick={() => runDocumentAction(document.id, "anonymize")}>
                          Anonymize
                        </button>
                        <button className="primary-button" disabled={saving || document.import_status === "rejected"} onClick={() => runDocumentAction(document.id, "sample")}>
                          Create sample
                        </button>
                        <button className="ghost-button danger-button" disabled={saving} onClick={() => setRejectingId(document.id)}>
                          Reject
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </Layout>
  );
}
