import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import Badge from "../components/Badge";
import Button from "../components/Button";
import DocumentCard from "../components/DocumentCard";
import Layout from "../components/Layout";

export default function DashboardPage() {
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [profile, setProfile] = useState(null);

  useEffect(() => {
    api
      .getReviews()
      .then(setReviews)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
    api.me().then(setProfile).catch(() => setProfile(null));
  }, []);

  const homeSummary = useMemo(() => {
    const averageScore = reviews.length
      ? Math.round(reviews.reduce((sum, item) => sum + item.total_score, 0) / reviews.length)
      : 0;
    const latest = reviews[0];
    const best = reviews.length ? reviews.reduce((max, item) => (item.total_score > max.total_score ? item : max), reviews[0]) : null;
    return { averageScore, latest, best };
  }, [reviews]);

  return (
    <Layout title="자기소개서 홈" subtitle="최근 작성한 문안과 첨삭 결과를 다시 열어 최종본까지 이어갑니다.">
      <section className="file-desk-hero">
        <div className="file-desk-copy">
          <Badge tone="brand">CoverFit 작성함</Badge>
          <h2>작성 중인 자기소개서를 다시 꺼내 이어서 다듬어보세요.</h2>
          <p>
            초안 작성, AI 검토, 문장 수정, 최종본 저장, PDF 내보내기까지 한 흐름으로 이어집니다.
            최근 문안을 열어 보완점과 개선문을 차분히 비교해보세요.
          </p>
          <div className="button-row">
            <Link to="/reviews/new">
              <Button>새 첨삭 시작</Button>
            </Link>
            <Link to="/templates">
              <Button variant="secondary">문항 템플릿 보기</Button>
            </Link>
          </div>
        </div>

        <aside className="file-drawer-preview" aria-label="최근 첨삭 요약">
          <div className="drawer-label-row">
            <span>최근 작업</span>
            <em>{reviews.length}건 저장</em>
          </div>
          {profile?.usage ? (
            <div className="usage-sheet">
              <span>오늘 남은 첨삭</span>
              <strong>
                {profile.usage.review_daily.unlimited
                  ? "무제한"
                  : `${profile.usage.review_daily.remaining}/${profile.usage.review_daily.limit}`}
              </strong>
              <em>PDF {profile.usage.pdf_monthly.unlimited ? "무제한" : `${profile.usage.pdf_monthly.used}/${profile.usage.pdf_monthly.limit}`}</em>
            </div>
          ) : null}
          <div className="drawer-folder-stack">
            <div className="mini-folder folder-a">
              <span>최근 직무</span>
              <strong>{homeSummary.latest?.target_job_role || "첫 첨삭을 기다리는 중"}</strong>
            </div>
            <div className="mini-folder folder-b">
              <span>평균 점수</span>
              <strong>{homeSummary.averageScore || "-"}</strong>
            </div>
            <div className="mini-folder folder-c">
              <span>최고 점수</span>
              <strong>{homeSummary.best ? `${homeSummary.best.total_score}점` : "-"}</strong>
            </div>
          </div>
        </aside>
      </section>

      <div className="file-home-layout">
        <section className="file-cabinet-section">
          <div className="file-section-title">
            <div>
              <span>Recent drafts</span>
              <h2>최근 첨삭한 자기소개서</h2>
              <p>저장된 문안을 다시 열어 리파인 기록, 최종본, PDF 내보내기까지 이어서 확인하세요.</p>
            </div>
            <Link to="/reviews/history" className="file-text-link">전체 첨삭 기록 보기</Link>
          </div>

          {loading ? <div className="folder-empty-state">최근 첨삭 기록을 불러오는 중입니다...</div> : null}
          {error ? <div className="error-box">{error}</div> : null}
          {!loading && !error && reviews.length === 0 ? (
            <div className="folder-empty-state">
              <span className="empty-folder-icon" aria-hidden="true">▱</span>
              <h3>아직 첨삭한 자기소개서가 없습니다.</h3>
              <p>채용공고와 초안을 붙여 넣고 첫 번째 AI 검토를 시작해보세요.</p>
              <Link to="/reviews/new">
                <Button>첫 첨삭 시작</Button>
              </Link>
            </div>
          ) : null}

          <div className="folder-grid shelf-view">
            {reviews.slice(0, 5).map((review) => (
              <DocumentCard key={review.id} review={review} />
            ))}
          </div>
        </section>

        <aside className="guide-file-box">
          <div className="guide-file-tab">작성 가이드</div>
          <div className="guide-file-body">
            <h2>AI 검토 전에 준비할 것</h2>
            <ol className="guide-list file-guide-list">
              <li>
                <strong>공고 키워드 먼저 확인</strong>
                <span>지원 직무의 요구 역량을 자기소개서 문장과 연결하면 검토 결과가 더 정확해집니다.</span>
              </li>
              <li>
                <strong>경험은 역할과 결과로 분리</strong>
                <span>무엇을 했는지보다 어떤 역할로 어떤 결과를 만들었는지부터 적어보세요.</span>
              </li>
              <li>
                <strong>최종본은 직접 한 번 더 수정</strong>
                <span>AI 개선문을 그대로 쓰기보다 최종본 탭에서 직접 다듬은 뒤 PDF로 저장하세요.</span>
              </li>
            </ol>
          </div>
        </aside>
      </div>
    </Layout>
  );
}
