export default function FeedbackSection({ title, items, ordered = false, emptyText = "표시할 내용이 없습니다." }) {
  const ListTag = ordered ? "ol" : "ul";

  return (
    <section className="panel">
      <h2>{title}</h2>
      {items?.length ? (
        <ListTag className={ordered ? "ordered-list" : "list"}>
          {items.map((item, index) => (
            <li key={`${title}-${index}`}>{item}</li>
          ))}
        </ListTag>
      ) : (
        <p className="muted">{emptyText}</p>
      )}
    </section>
  );
}
