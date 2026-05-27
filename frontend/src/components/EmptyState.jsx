export default function EmptyState({ title, description, action, actions }) {
  return (
    <div className="empty-state">
      <div className="empty-state-mark" />
      <h3>{title}</h3>
      <p>{description}</p>
      {actions || action}
    </div>
  );
}
