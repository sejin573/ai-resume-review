import Badge from "../components/Badge";
import Button from "../components/Button";
import Layout from "../components/Layout";

const templates = [
  {
    title: "신입 지원형",
    tag: "기본 문항",
    description: "프로젝트 경험, 학습 과정, 직무 관심도를 순서대로 정리하는 기본 구조입니다.",
    lines: ["지원 동기", "학습 과정", "프로젝트 경험", "입사 후 기여"],
  },
  {
    title: "직무 전환형",
    tag: "전환 지원",
    description: "이전 경험에서 옮겨올 수 있는 역량을 현재 직무와 연결하는 구조입니다.",
    lines: ["기존 경험", "공통 역량", "전환 이유", "보완 학습"],
  },
  {
    title: "성과 강조형",
    tag: "경력/프로젝트",
    description: "역할, 행동, 결과를 짧고 선명하게 드러내고 면접 질문까지 이어가는 구조입니다.",
    lines: ["문제 상황", "나의 역할", "실행 방법", "결과와 배운 점"],
  },
  {
    title: "교육행정형",
    tag: "운영/행정",
    description: "문서 관리, 민원 응대, 일정 조율 경험을 차분하게 보여주는 문항 흐름입니다.",
    lines: ["업무 정확성", "응대 경험", "일정 조율", "운영 개선"],
  },
];

export default function TemplatesPage() {
  return (
    <Layout title="문항 템플릿" subtitle="완성 문장을 복사하기보다, 내 경험을 어떤 순서로 쓸지 먼저 잡아보는 가이드입니다.">
      <section className="template-cabinet-hero">
        <div>
          <Badge tone="warning">작성 가이드</Badge>
          <h2>문항별 작성 흐름</h2>
          <p>
            자기소개서 문항은 정답 문장을 외우는 것보다, 내 경험을 꺼내는 순서가 중요합니다. 지원 상황에
            맞는 흐름을 고른 뒤 새 첨삭 화면에서 초안을 작성하고 AI 검토를 받아보세요.
          </p>
        </div>
        <div className="template-index-card">
          <span>GUIDE</span>
          <strong>04</strong>
          <em>기본 템플릿</em>
        </div>
      </section>

      <section className="template-folder-board">
        {templates.map((template, index) => (
          <article key={template.title} className={`template-folder-card folder-tone-${index + 1}`}>
            <div className="template-folder-tab">
              <span>{template.tag}</span>
            </div>
            <div className="template-folder-body">
              <div className="template-folder-number">0{index + 1}</div>
              <h3>{template.title}</h3>
              <p>{template.description}</p>
              <ul>
                {template.lines.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
              <Button variant="secondary" disabled>
                새 첨삭에 적용 준비 중
              </Button>
            </div>
          </article>
        ))}
      </section>
    </Layout>
  );
}
