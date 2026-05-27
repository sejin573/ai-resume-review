import FeedbackSection from "./FeedbackSection";

export default function MissingKeywords({ keywords }) {
  return <FeedbackSection title="보완이 필요한 키워드" items={keywords} emptyText="누락 키워드가 없습니다." />;
}
