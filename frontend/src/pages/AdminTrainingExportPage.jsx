import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import Layout from "../components/Layout";

function groupCount(items, keyFn) {
  return items.reduce((acc, item) => {
    const key = keyFn(item);
    acc[key] = (acc[key] || 0) + 1;
    return acc;
  }, {});
}

export default function AdminTrainingExportPage() {
  const [response, setResponse] = useState(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [exportResult, setExportResult] = useState(null);
  const [error, setError] = useState("");

  const loadSamples = async () => {
    setLoading(true);
    try {
      const data = await api.getTrainingSamples();
      setResponse(data);
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSamples();
  }, []);

  const samples = response?.samples || [];

  const summary = useMemo(() => {
    const blockedSamples = samples.filter((sample) => !sample.valid_for_export);
    const blockedReasons = blockedSamples.flatMap((sample) => sample.validation_errors);
    return {
      total: response?.total_samples || 0,
      ready: response?.exportable_samples || 0,
      blocked: blockedSamples.length,
      bySourceType: groupCount(samples, (sample) => sample.source_type || "unknown"),
      byJobRole: groupCount(samples, (sample) => sample.job_role || "unknown"),
      byQualityStatus: groupCount(samples, (sample) => sample.quality_status || "unknown"),
      blockedReasons: groupCount(blockedReasons, (item) => item),
    };
  }, [response, samples]);

  const handleExport = async () => {
    setExporting(true);
    setError("");
    try {
      const result = await api.exportCuratedTrainingJsonl();
      setExportResult(result);
      await loadSamples();
    } catch (err) {
      setError(err.message);
    } finally {
      setExporting(false);
    }
  };

  return (
    <Layout title="학습 데이터 export" subtitle="사람 검토가 끝난 샘플만 curated JSONL로 내보냅니다.">
      <div className="actions-row page-actions">
        <Link to="/admin/training-samples">샘플 검토로 이동</Link>
      </div>
      <section className="stats-grid">
        <div className="panel stat-panel">
          <span>전체 training samples</span>
          <strong>{summary.total}</strong>
        </div>
        <div className="panel stat-panel">
          <span>export-ready samples</span>
          <strong>{summary.ready}</strong>
        </div>
        <div className="panel stat-panel">
          <span>blocked samples</span>
          <strong>{summary.blocked}</strong>
        </div>
      </section>

      {loading ? <p>Export 현황을 불러오는 중입니다...</p> : null}
      {error ? <div className="error-box">{error}</div> : null}

      {!loading ? (
        <>
          <section className="panel">
            <div className="section-header">
              <h2>Export 실행</h2>
              <button className="primary-button" disabled={exporting} onClick={handleExport}>
                {exporting ? "Export 중..." : "Export curated training JSONL"}
              </button>
            </div>
            {exportResult ? (
              <div className="detail-grid top-gap">
                <div>
                  <span className="detail-label">file_path</span>
                  <strong className="text-break">{exportResult.file_path}</strong>
                </div>
                <div>
                  <span className="detail-label">exported_count</span>
                  <strong>{exportResult.exported_count}</strong>
                </div>
                <div>
                  <span className="detail-label">skipped_count</span>
                  <strong>{exportResult.skipped_count}</strong>
                </div>
              </div>
            ) : (
              <p className="muted">아직 export를 실행하지 않았습니다.</p>
            )}
          </section>

          <div className="results-layout">
            <section className="panel">
              <h2>Blocked reasons summary</h2>
              {Object.keys(summary.blockedReasons).length === 0 ? (
                <p className="muted">현재 막힌 샘플이 없습니다.</p>
              ) : (
                <ul className="compact-list">
                  {Object.entries(summary.blockedReasons).map(([reason, count]) => (
                    <li key={reason}>
                      {reason} ({count})
                    </li>
                  ))}
                </ul>
              )}
            </section>

            <section className="panel">
              <h2>Count by source_type</h2>
              <ul className="compact-list">
                {Object.entries(summary.bySourceType).map(([value, count]) => (
                  <li key={value}>
                    {value}: {count}
                  </li>
                ))}
              </ul>
            </section>

            <section className="panel">
              <h2>Count by job_role</h2>
              <ul className="compact-list">
                {Object.entries(summary.byJobRole).map(([value, count]) => (
                  <li key={value}>
                    {value}: {count}
                  </li>
                ))}
              </ul>
            </section>

            <section className="panel">
              <h2>Count by quality_status</h2>
              <ul className="compact-list">
                {Object.entries(summary.byQualityStatus).map(([value, count]) => (
                  <li key={value}>
                    {value}: {count}
                  </li>
                ))}
              </ul>
            </section>
          </div>
        </>
      ) : null}
    </Layout>
  );
}
