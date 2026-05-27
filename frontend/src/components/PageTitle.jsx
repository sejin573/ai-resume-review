import Badge from "./Badge";

export default function PageTitle({ title, subtitle, badge }) {
  return (
    <div className="page-title-block">
      <div className="page-title-row">
        <h1>{title}</h1>
        {badge ? <Badge tone={badge.tone || "brand"}>{badge.label}</Badge> : null}
      </div>
      {subtitle ? <p>{subtitle}</p> : null}
    </div>
  );
}
