import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import Badge from "../components/Badge";
import Button from "../components/Button";
import DocumentCard from "../components/DocumentCard";
import Layout from "../components/Layout";

export default function ReviewHistoryPage() {
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [modeFilter, setModeFilter] = useState("all");
  const [sortBy, setSortBy] = useState("date_desc");

  useEffect(() => {
    api
      .getReviews()
      .then(setReviews)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const filteredReviews = useMemo(() => {
    const next = reviews.filter((review) => {
      const normalizedQuery = query.trim().toLowerCase();
      const queryMatch =
        !normalizedQuery ||
        review.target_job_role.toLowerCase().includes(normalizedQuery) ||
        review.summary.toLowerCase().includes(normalizedQuery);
      const modeMatch = modeFilter === "all" || review.review_mode === modeFilter;
      return queryMatch && modeMatch;
    });

    next.sort((a, b) => {
      if (sortBy === "score_desc") return b.total_score - a.total_score;
      if (sortBy === "score_asc") return a.total_score - b.total_score;
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });
    return next;
  }, [modeFilter, query, reviews, sortBy]);

  return (
    <Layout title="내 첨삭 기록" subtitle="저장한 자기소개서와 AI 검토 결과를 지원 직무별로 다시 확인합니다.">
      <section className="archive-hero">
        <div>
          <Badge tone="brand">Review archive</Badge>
          <h2>저장한 자기소개서</h2>
          <p>지원 직무마다 남겨둔 초안, 개선문, 면접 질문, 최종본을 한 곳에서 다시 열어봅니다.</p>
        </div>
        <div className="archive-stamp">
          <span>총 검토</span>
          <strong>{reviews.length}</strong>
          <em>현재 {filteredReviews.length}건 표시</em>
        </div>
      </section>

      <section className="archive-filter-strip">
        <label>
          <span>직무 / 요약 검색</span>
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="예: 백엔드, 교육행정, 마케팅" />
        </label>
        <label>
          <span>첨삭 방식</span>
          <select value={modeFilter} onChange={(event) => setModeFilter(event.target.value)}>
            <option value="all">전체</option>
            <option value="quick">빠른 첨삭</option>
            <option value="detailed">상세 첨삭</option>
            <option value="strict">꼼꼼한 첨삭</option>
            <option value="rewrite-focused">개선문 중심</option>
            <option value="rewrite_focused">개선문 중심</option>
          </select>
        </label>
        <label>
          <span>정렬</span>
          <select value={sortBy} onChange={(event) => setSortBy(event.target.value)}>
            <option value="date_desc">최근 검토순</option>
            <option value="score_desc">점수 높은 순</option>
            <option value="score_asc">점수 낮은 순</option>
          </select>
        </label>
      </section>

      {loading ? <div className="folder-empty-state">첨삭 기록을 불러오는 중입니다...</div> : null}
      {error ? <div className="error-box">{error}</div> : null}
      {!loading && !error && filteredReviews.length === 0 ? (
        <div className="folder-empty-state">
          <span className="empty-folder-icon" aria-hidden="true">▱</span>
          <h3>조건에 맞는 첨삭 기록이 없습니다.</h3>
          <p>검색어를 지우거나 새 자기소개서를 검토해보세요.</p>
          <Link to="/reviews/new">
            <Button>새 첨삭 시작</Button>
          </Link>
        </div>
      ) : null}

      <section className="archive-shelf">
        <div className="archive-shelf-top" aria-hidden="true">
          <span>검토 기록</span>
          <span>최종본 저장 / PDF 내보내기 가능</span>
        </div>
        <div className="folder-grid archive-folder-grid">
          {filteredReviews.map((review) => (
            <DocumentCard key={review.id} review={review} />
          ))}
        </div>
      </section>
    </Layout>
  );
}
