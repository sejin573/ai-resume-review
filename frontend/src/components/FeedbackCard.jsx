import Card from "./Card";

export default function FeedbackCard({ title, description, tone = "neutral" }) {
  return (
    <Card className={`feedback-card feedback-${tone}`}>
      <h3>{title}</h3>
      <p>{description}</p>
    </Card>
  );
}
