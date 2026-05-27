import { Link } from "react-router-dom";
import Badge from "./Badge";
import Button from "./Button";
import PageTitle from "./PageTitle";

export default function TopBar({ title, subtitle, aiMode, onToggleMenu }) {
  return (
    <header className="topbar">
      <div className="topbar-left">
        <button type="button" className="menu-button" onClick={onToggleMenu}>
          메뉴
        </button>
        <PageTitle
          title={title}
          subtitle={subtitle}
          badge={aiMode ? { label: aiMode === "mock" ? "Mock AI" : "OpenAI Connected", tone: aiMode === "mock" ? "warning" : "success" } : null}
        />
      </div>
      <div className="topbar-actions">
        <Badge tone="neutral">Workspace</Badge>
        <Link to="/reviews/new">
          <Button>새 첨삭</Button>
        </Link>
      </div>
    </header>
  );
}
