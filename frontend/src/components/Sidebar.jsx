import { Link, useLocation } from "react-router-dom";

const navItems = [
  { to: "/dashboard", label: "자소서 홈" },
  { to: "/reviews/new", label: "새 문서" },
  { to: "/reviews/history", label: "첨삭 히스토리" },
  { to: "/templates", label: "템플릿" },
  { to: "/admin/data-sources", label: "데이터 소스" },
  { to: "/admin/training-samples", label: "학습 샘플 검토" },
  { to: "/admin/training-export", label: "학습 데이터" },
];

export default function Sidebar({ open, onClose, onLogout }) {
  const location = useLocation();

  return (
    <>
      <div className={open ? "sidebar-overlay visible" : "sidebar-overlay"} onClick={onClose} />
      <aside className={open ? "sidebar sidebar-open" : "sidebar"}>
        <div className="sidebar-top">
          <div className="sidebar-brand-block">
            <div className="brand-mark">CF</div>
            <div>
              <div className="brand">CoverFit AI</div>
              <p className="muted sidebar-copy">지원 직무에 맞게 자기소개서를 다듬는 AI 커리어 코치</p>
            </div>
          </div>
          <nav className="nav">
            {navItems.map((item) => {
              const active = location.pathname === item.to || location.pathname.startsWith(`${item.to}/`);
              return (
                <Link key={item.to} to={item.to} className={active ? "nav-link active" : "nav-link"} onClick={onClose}>
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>
        <div className="sidebar-bottom">
          <div className="user-card">
            <div className="user-avatar">U</div>
            <div>
              <strong>워크스페이스 사용자</strong>
              <p className="muted">문안 저장과 첨삭 히스토리 관리</p>
            </div>
          </div>
          <button className="button button-secondary" onClick={onLogout}>
            로그아웃
          </button>
        </div>
      </aside>
    </>
  );
}
