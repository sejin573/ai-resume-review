import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { api, clearToken } from "../api/client";

const primaryNav = [
  { to: "/dashboard", label: "자소서 홈" },
  { to: "/reviews/new", label: "새 첨삭" },
  { to: "/reviews/history", label: "내 첨삭 기록" },
  { to: "/templates", label: "문항 템플릿" },
];

const adminNav = [
  { to: "/admin/data-sources", label: "데이터 소스" },
  { to: "/admin/training-samples", label: "학습 샘플" },
  { to: "/admin/training-export", label: "데이터 Export" },
];

function usageLabel(usage) {
  if (!usage) return "사용량 확인 중";
  const bucket = usage.review_daily;
  if (bucket.unlimited) return "첨삭 무제한";
  return `오늘 첨삭 ${bucket.used}/${bucket.limit}`;
}

export default function AppShell({ title, subtitle, children }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [profile, setProfile] = useState(null);

  useEffect(() => {
    let ignore = false;
    api
      .me()
      .then((data) => {
        if (!ignore) setProfile(data);
      })
      .catch(() => {
        if (!ignore) setProfile(null);
      });
    return () => {
      ignore = true;
    };
  }, []);

  const handleLogout = () => {
    clearToken();
    navigate("/");
  };

  const isActive = (to) => location.pathname === to || location.pathname.startsWith(`${to}/`);
  const isAdmin = Boolean(profile?.is_admin);

  return (
    <div className="document-app-shell">
      <header className="document-topnav">
        <Link to="/dashboard" className="document-brand" aria-label="CoverFit AI 홈">
          <span className="document-brand-mark">CF</span>
          <span>
            <strong>CoverFit AI</strong>
            <em>자기소개서 검토 · 완성</em>
          </span>
        </Link>

        <nav className="document-nav" aria-label="주요 메뉴">
          {primaryNav.map((item) => (
            <Link key={item.to} to={item.to} className={isActive(item.to) ? "active" : ""}>
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="document-top-actions">
          {profile ? (
            <div className="usage-pill" title="무료 플랜 사용량">
              <span>{profile.plan === "pro" ? "Pro" : profile.is_admin ? "Admin" : "Free"}</span>
              <strong>{usageLabel(profile.usage)}</strong>
            </div>
          ) : null}
          {isAdmin ? (
            <details className="admin-menu">
              <summary>관리</summary>
              <div>
                {adminNav.map((item) => (
                  <Link key={item.to} to={item.to} className={isActive(item.to) ? "active" : ""}>
                    {item.label}
                  </Link>
                ))}
              </div>
            </details>
          ) : null}
          <Link to="/reviews/new" className="nav-primary-link">
            새 첨삭
          </Link>
          <button type="button" onClick={handleLogout} className="nav-logout-button">
            로그아웃
          </button>
        </div>
      </header>

      <main className="document-main">
        {(title || subtitle) && (
          <section className="document-page-title">
            <div>
              {title ? <h1>{title}</h1> : null}
              {subtitle ? <p>{subtitle}</p> : null}
            </div>
          </section>
        )}
        {children}
      </main>
    </div>
  );
}
