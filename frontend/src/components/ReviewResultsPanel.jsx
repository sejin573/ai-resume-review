import BeforeAfterComparison from "./BeforeAfterComparison";
import FeedbackSection from "./FeedbackSection";
import ImprovedCoverLetter from "./ImprovedCoverLetter";
import InterviewQuestions from "./InterviewQuestions";
import MissingKeywords from "./MissingKeywords";
import ProblemsList from "./ProblemsList";
import ReviewScoreSummary from "./ReviewScoreSummary";
import ScoreCards from "./ScoreCards";
import StrengthsList from "./StrengthsList";

export default function ReviewResultsPanel({ review, improvedText }) {
  if (!review) {
    return null;
  }

  const result = review.review_result;
  const finalText = improvedText || result.improved_cover_letter;

  return (
    <div className="results-layout">
      <ReviewScoreSummary totalScore={result.total_score} summary={result.summary} />
      <ScoreCards scores={result.scores} />
      <StrengthsList items={result.strengths} />
      <ProblemsList items={result.problems} />
      <FeedbackSection title="개선 전략" items={result.improvement_strategy} />
      <MissingKeywords keywords={result.missing_keywords} />
      <ImprovedCoverLetter text={finalText} />
      <BeforeAfterComparison originalText={review.cover_letter_text} improvedText={finalText} />
      <InterviewQuestions questions={result.interview_questions} />
    </div>
  );
}
