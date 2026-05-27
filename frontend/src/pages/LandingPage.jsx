import { useState } from "react";
import { Link } from "react-router-dom";
import { isAuthenticated } from "../api/client";
import Badge from "../components/Badge";
import Button from "../components/Button";

const sampleReview = {
  improved_cover_letter:
    "저는 가상의 콘텐츠 서비스 프로젝트에서 사용자 피드백을 정리하고 주간 업데이트 문서를 관리하며 메시지 우선순위를 조정한 경험이 있습니다. 여러 요청을 분류하고 전달 흐름을 정리해 팀이 같은 방향으로 실행할 수 있도록 지원했고, 이 과정에서 캠페인 실행 전 필요한 자료 정리와 일정 조율 역량을 키웠습니다.",
  problems: [
    "성과를 결과 중심 문장으로 다시 정리할 필요가 있습니다.",
    "채용공고 키워드와 경험 연결이 아직 약합니다.",
    "마지막 문단의 직무 기여 표현이 더 선명해질 수 있습니다.",
  ],
  strengths: [
    "문장 톤이 차분하고 과장되지 않습니다.",
    "협업 경험을 직무 역량으로 연결할 수 있는 재료가 있습니다.",
    "지원 동기가 어색하지 않게 드러납니다.",
  ],
  questions: [
    "사용자 피드백을 정리할 때 어떤 기준으로 우선순위를 정했나요?",
    "이 경험이 마케팅 직무에서 어떻게 이어질 수 있다고 생각하나요?",
  ],
};

const workflowSteps = [
  {
    label: "초안 정리",
    description: "자기소개서, 이력 요약, 채용공고를 한 작업대에 올립니다.",
  },
  {
    label: "보완 메모",
    description: "직무 적합도, 구체성, 성과 표현을 문장 단위로 점검합니다.",
  },
  {
    label: "최종본 완성",
    description: "개선문 적용과 리파인 후 제출용 최종본을 저장합니다.",
  },
];

const featureColumns = [
  {
    title: "검토",
    items: ["직무 적합도 분석", "채용공고 키워드 점검", "문장 구조 보완 메모"],
  },
  {
    title: "수정",
    items: ["개선문 생성", "수정 전/후 비교", "리파인 히스토리"],
  },
  {
    title: "정리",
    items: ["면접 예상질문", "최종본 저장", "TXT/PDF 내보내기"],
  },
];

export default function LandingPage() {
  const ctaHref = isAuthenticated() ? "/reviews/new" : "/signup";

  return (
    <div className="landing-shell retro-landing">
      <header className="landing-header retro-header">
        <div className="landing-header-brand">
          <div className="brand-mark">CF</div>
          <div>
            <div className="landing-brand">CoverFit AI</div>
            <p className="muted">자기소개서 첨삭 파일</p>
          </div>
        </div>
        <nav className="landing-nav">
          <a href="#workflow">작업 흐름</a>
          <a href="#sample-result">첨삭 예시</a>
          <a href="#privacy">개인정보 안내</a>
          <Link to="/login">로그인</Link>
          <Link to={ctaHref}>
            <Button>무료로 시작하기</Button>
          </Link>
        </nav>
      </header>

      <main className="landing-main retro-main">
        <section className="file-desk-hero landing-file-hero">
          <div className="file-desk-copy landing-file-copy">
            <Badge tone="brand">CoverFit 작성함</Badge>
            <h1>자기소개서, 이제 직무에 맞게 첨삭하세요</h1>
            <p>
              채용공고와 이력서를 함께 분석해 직무 적합도, 구체성, 성과 표현, 키워드 반영도를 점검하고,
              제출용 개선문까지 한 흐름으로 정리합니다.
            </p>
            <div className="button-row">
              <Link to={ctaHref}>
                <Button>무료로 첨삭 시작하기</Button>
              </Link>
              <a href="#sample-result">
                <Button variant="secondary">첨삭 예시 보기</Button>
              </a>
            </div>
            <div className="landing-note-strip">
              <span>문서 검토 7개 항목</span>
              <span>리파인 + 최종본 저장</span>
              <span>학습 데이터 동의는 선택</span>
            </div>
          </div>

          <aside className="file-drawer-preview landing-drawer-preview" aria-label="랜딩 미리보기">
            <div className="drawer-label-row">
              <span>첨삭 파일 묶음</span>
              <em>fictional preview</em>
            </div>
            <div className="drawer-folder-stack">
              <div className="mini-folder folder-a">
                <span>직무 적합도</span>
                <strong>81점</strong>
              </div>
              <div className="mini-folder folder-b">
                <span>누락 키워드</span>
                <strong>캠페인 운영</strong>
              </div>
              <div className="mini-folder folder-c">
                <span>최종본 단계</span>
                <strong>PDF 저장 가능</strong>
              </div>
            </div>
          </aside>
        </section>

        <section className="landing-section retro-section">
          <div className="retro-browser-band">
            <article className="retro-browser-card">
              <div className="retro-browser-bar">
                <div className="retro-browser-dots">
                  <span />
                  <span />
                  <span />
                </div>
                <div className="retro-browser-address">coverfit://review-workspace/intro</div>
              </div>
              <div className="retro-browser-body">
                <div className="retro-browser-note">
                  <strong>문서 워크스페이스 미리보기</strong>
                  <p>채용공고, 자소서, 개선문이 한 창 안에서 이어지는 흐름을 먼저 보여줍니다.</p>
                </div>
                <div className="retro-browser-columns">
                  <div className="retro-browser-panel">
                    <span>입력</span>
                    <p>자기소개서 초안, 이력 요약, 채용공고</p>
                  </div>
                  <div className="retro-browser-panel">
                    <span>분석</span>
                    <p>직무 적합도, 성과 표현, 보완 메모</p>
                  </div>
                  <div className="retro-browser-panel">
                    <span>완성</span>
                    <p>리파인, 최종본 저장, PDF 내보내기</p>
                  </div>
                </div>
              </div>
            </article>
          </div>
        </section>

        <section className="landing-section retro-section">
          <div className="landing-paper-band">
            <article className="paper-empty-card intro-paper-card">
              <span className="paper-label">서비스 성격</span>
              <h2>대시보드보다, 문서 작업대에 가깝게 만들었습니다</h2>
              <p>
                점수표만 보여주는 도구가 아니라, 초안을 열고 보완 메모를 읽고 최종본까지 직접 다듬는 작업 흐름을
                중심에 둡니다.
              </p>
            </article>
            <article className="paper-empty-card intro-paper-card warm-note">
              <span className="paper-label">데이터 원칙</span>
              <h2>학습 데이터 활용은 서비스 이용과 분리합니다</h2>
              <p>
                원본 문서에는 개인정보가 들어갈 수 있으므로, 학습 목적 저장은 사용자가 명시적으로 동의한 경우에만
                별도로 처리합니다.
              </p>
            </article>
          </div>
        </section>

        <section id="workflow" className="landing-section retro-section">
          <div className="section-heading">
            <h2>파일을 꺼내고, 읽고, 고치고, 제출하는 흐름</h2>
            <p>취준생이 실제로 하는 순서에 맞춰 랜딩부터 문서 작업의 리듬을 보여줍니다.</p>
          </div>
          <div className="folder-grid landing-workflow-grid">
            {workflowSteps.map((item, index) => (
              <article key={item.label} className="folder-document-card landing-folder-card">
                <div className="folder-card-tab">
                  <span>step {index + 1}</span>
                </div>
                <div className="folder-card-body">
                  <div className="folder-card-topline">
                    <span className="folder-card-date">workflow</span>
                  </div>
                  <h3>{item.label}</h3>
                  <p>{item.description}</p>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section id="sample-result" className="landing-section retro-section">
          <div className="section-heading">
            <h2>첨삭 예시를 파일철처럼 펼쳐봅니다</h2>
            <p>실제 사용자 문서가 아닌 fictional 예시로 제품 흐름만 보여줍니다.</p>
          </div>
          <div className="sample-editor-layout retro-sample-layout">
            <article className="sample-paper-card">
              <div className="retro-browser-bar inset">
                <div className="retro-browser-dots">
                  <span />
                  <span />
                  <span />
                </div>
                <div className="retro-browser-address">sample://improved-cover-letter.txt</div>
              </div>
              <span className="paper-label">개선문 미리보기</span>
              <p>{sampleReview.improved_cover_letter}</p>
              <CopyPreviewButton />
            </article>
            <aside className="sample-comment-card retro-comment-card">
              <div className="retro-browser-bar inset">
                <div className="retro-browser-dots">
                  <span />
                  <span />
                  <span />
                </div>
                <div className="retro-browser-address">sample://coach-notes/feedback</div>
              </div>
              <div className="sample-block">
                <h3>강점 메모</h3>
                <ul>
                  {sampleReview.strengths.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
              <div className="sample-block">
                <h3>보완 메모</h3>
                <ul>
                  {sampleReview.problems.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
              <div className="sample-block">
                <h3>면접 질문</h3>
                <ul>
                  {sampleReview.questions.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            </aside>
          </div>
        </section>

        <section className="landing-section retro-section">
          <div className="section-heading">
            <h2>핵심 기능도 같은 톤으로 묶어 보여줍니다</h2>
            <p>기능 소개도 카드 나열보다 서류 분류함처럼 읽히도록 정리했습니다.</p>
          </div>
          <div className="practical-template-grid landing-feature-folder-grid">
            {featureColumns.map((group, index) => (
              <article key={group.title} className={`template-folder-card practical-template-card folder-tone-${(index % 4) + 1}`}>
                <div className="template-folder-tab">
                  <span>{group.title}</span>
                </div>
                <div className="template-folder-body">
                  <div className="template-folder-number">0{index + 1}</div>
                  <h3>{group.title} 단계에서 하는 일</h3>
                  <ul>
                    {group.items.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section id="privacy" className="landing-section retro-section">
          <div className="section-heading">
            <h2>개인정보와 학습 데이터는 분리합니다</h2>
            <p>동의하지 않아도 첨삭 기능은 그대로 사용할 수 있습니다.</p>
          </div>
          <div className="privacy-card editorial-card retro-privacy-card">
            <ul className="feature-list">
              <li>원본 이력서와 자기소개서에는 개인정보가 포함될 수 있습니다.</li>
              <li>학습 데이터 활용은 사용자가 명시적으로 동의한 경우에만 진행됩니다.</li>
              <li>학습용 데이터는 개인정보 제거 후 별도 저장됩니다.</li>
              <li>동의하지 않아도 첨삭 서비스 이용은 가능합니다.</li>
            </ul>
          </div>
        </section>

        <section className="cta-band editorial-cta retro-cta-band">
          <h2>지금 쓰고 있는 문항부터 파일에 올려보세요</h2>
          <p>채용공고와 자기소개서를 붙여 넣으면, 보완 메모와 개선문을 같은 작업 화면에서 바로 확인할 수 있습니다.</p>
          <div className="button-row">
            <Link to={ctaHref}>
              <Button>무료로 첨삭 시작하기</Button>
            </Link>
          </div>
        </section>
      </main>
    </div>
  );
}

function CopyPreviewButton() {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(sampleReview.improved_cover_letter);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  };

  return (
    <button type="button" className="button button-ghost" onClick={handleCopy}>
      {copied ? "복사됨" : "개선문 복사"}
    </button>
  );
}
