import FeedbackSection from "./FeedbackSection";

export default function InterviewQuestions({ questions }) {
  return <FeedbackSection title="면접 예상 질문" items={questions} ordered />;
}
