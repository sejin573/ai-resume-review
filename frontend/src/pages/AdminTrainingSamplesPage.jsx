import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import Layout from "../components/Layout";

const defaultFilters = {
  sourceType: "all",
  qualityStatus: "all",
  validForExport: "all",
  jobRole: "",
  reviewedByHuman: "all",
  containsRealUserData: "all",
};

export default function AdminTrainingSamplesPage() {
  const [response, setResponse] = useState(null);
  const [filters, setFilters] = useState(defaultFilters);
  const [sortBy, setSortBy] = useState("created_at_desc");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    api
      .getTrainingSamples()
      .then(setResponse)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const samples = response?.samples || [];

  const filteredSamples = useMemo(() => {
    const normalizedJobRole = filters.jobRole.trim().toLowerCase();
    const next = samples.filter((sample) => {
      if (filters.sourceType !== "all" && sample.source_type !== filters.sourceType) return false;
      if (filters.qualityStatus !== "all" && sample.quality_status !== filters.qualityStatus) return false;
      if (filters.validForExport !== "all" && String(sample.valid_for_export) !== filters.validForExport) return false;
      if (filters.reviewedByHuman !== "all" && String(sample.reviewed_by_human) !== filters.reviewedByHuman) return false;
      if (filters.containsRealUserData !== "all" && String(sample.contains_real_user_data) !== filters.containsRealUserData)
        return false;
      if (normalizedJobRole && !sample.job_role.toLowerCase().includes(normalizedJobRole)) return false;
      return true;
    });

    next.sort((a, b) => {
      if (sortBy === "total_score_desc") return b.total_score - a.total_score;
      if (sortBy === "pii_risk_score_desc") return b.pii_risk_score - a.pii_risk_score;
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });
    return next;
  }, [filters, samples, sortBy]);

  const sourceTypeOptions = useMemo(() => {
    const values = new Set(["manual_seed", "user_consent", "admin_upload", "partner_dataset", "public_dataset"]);
    samples.forEach((sample) => {
      if (sample.source_type) values.add(sample.source_type);
    });
    return Array.from(values);
  }, [samples]);

  const updateFilter = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <Layout title="학습 샘플 검토" subtitle="사람이 검토하고 승인한 샘플만 export 대상으로 올립니다.">
      <section className="stats-grid">
        <div className="panel stat-panel">
          <span>전체 샘플</span>
          <strong>{response?.total_samples ?? 0}</strong>
        </div>
        <div className="panel stat-panel">
          <span>Export 가능</span>
          <strong>{response?.exportable_samples ?? 0}</strong>
        </div>
        <div className="panel stat-panel">
          <span>현재 필터 결과</span>
          <strong>{filteredSamples.length}</strong>
        </div>
      </section>

      <section className="panel">
        <div className="section-header">
          <h2>필터</h2>
          <label className="field inline-field narrow-field">
            <span>정렬</span>
            <select value={sortBy} onChange={(event) => setSortBy(event.target.value)}>
              <option value="created_at_desc">created_at desc</option>
              <option value="total_score_desc">total_score desc</option>
              <option value="pii_risk_score_desc">pii_risk_score desc</option>
            </select>
          </label>
        </div>
        <div className="filters-grid">
          <label className="field">
            <span>source_type</span>
            <select value={filters.sourceType} onChange={(event) => updateFilter("sourceType", event.target.value)}>
              <option value="all">all</option>
              {sourceTypeOptions.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>quality_status</span>
            <select value={filters.qualityStatus} onChange={(event) => updateFilter("qualityStatus", event.target.value)}>
              <option value="all">all</option>
              <option value="draft">draft</option>
              <option value="reviewed">reviewed</option>
              <option value="rejected">rejected</option>
            </select>
          </label>
          <label className="field">
            <span>valid_for_export</span>
            <select value={filters.validForExport} onChange={(event) => updateFilter("validForExport", event.target.value)}>
              <option value="all">all</option>
              <option value="true">true</option>
              <option value="false">false</option>
            </select>
          </label>
          <label className="field">
            <span>reviewed_by_human</span>
            <select value={filters.reviewedByHuman} onChange={(event) => updateFilter("reviewedByHuman", event.target.value)}>
              <option value="all">all</option>
              <option value="true">true</option>
              <option value="false">false</option>
            </select>
          </label>
          <label className="field">
            <span>contains_real_user_data</span>
            <select
              value={filters.containsRealUserData}
              onChange={(event) => updateFilter("containsRealUserData", event.target.value)}
            >
              <option value="all">all</option>
              <option value="true">true</option>
              <option value="false">false</option>
            </select>
          </label>
          <label className="field">
            <span>job_role</span>
            <input value={filters.jobRole} onChange={(event) => updateFilter("jobRole", event.target.value)} placeholder="직무명 검색" />
          </label>
        </div>
      </section>

      <section className="panel">
        <div className="section-header">
          <h2>샘플 목록</h2>
          <Link to="/admin/training-export">Export 현황 보기</Link>
        </div>
        {loading ? <p>샘플 목록을 불러오는 중입니다...</p> : null}
        {error ? <div className="error-box">{error}</div> : null}
        {!loading && !error ? (
          <div className="table-shell">
            <table className="data-table">
              <thead>
                <tr>
                  <th>sample_id</th>
                  <th>source_type</th>
                  <th>sample_kind</th>
                  <th>job_role</th>
                  <th>total_score</th>
                  <th>quality_status</th>
                  <th>reviewed_by_human</th>
                  <th>contains_real_user_data</th>
                  <th>pii_risk_score</th>
                  <th>valid_for_export</th>
                  <th>validation_errors</th>
                  <th>created_at</th>
                </tr>
              </thead>
              <tbody>
                {filteredSamples.map((sample) => (
                  <tr key={sample.sample_id}>
                    <td>
                      <Link to={`/admin/training-samples/${sample.sample_id}`}>{sample.sample_id}</Link>
                    </td>
                    <td>{sample.source_type || "-"}</td>
                    <td>{sample.sample_kind}</td>
                    <td>{sample.job_role}</td>
                    <td>{sample.total_score}</td>
                    <td>
                      <span className={`status-pill ${sample.quality_status}`}>{sample.quality_status}</span>
                    </td>
                    <td>{sample.reviewed_by_human ? "true" : "false"}</td>
                    <td>{sample.contains_real_user_data ? "true" : "false"}</td>
                    <td>{sample.pii_risk_score}</td>
                    <td>{sample.valid_for_export ? "true" : "false"}</td>
                    <td>
                      {sample.validation_errors.length > 0 ? (
                        <ul className="compact-list">
                          {sample.validation_errors.map((item) => (
                            <li key={item}>{item}</li>
                          ))}
                        </ul>
                      ) : (
                        <span className="muted">-</span>
                      )}
                    </td>
                    <td>{new Date(sample.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </Layout>
  );
}
