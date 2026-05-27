import json
from collections import Counter
from pathlib import Path

from app.schemas.review import AIReviewResponse
from app.services.anonymization_service import AnonymizationService


class SeedDataGenerator:
    ROLE_CONFIGS = {
        "웹개발자 신입": {
            "posting_keywords": ["문제 해결", "협업", "API", "테스트", "배포"],
            "posting_summary": "가상의 SaaS 팀에서 웹 서비스 기능 개발, API 연동, 협업 기반 개선 경험을 중요하게 보는 신입 채용 공고",
            "experience_pool": [
                "가상의 과제 프로젝트에서 일정 관리 화면을 구현하며 API 응답 구조를 정리했다",
                "팀 프로젝트에서 게시판 성능 문제를 분석하고 불필요한 요청 흐름을 줄였다",
                "사용자 피드백을 반영해 검색 화면의 필터 동선을 다시 설계했다",
                "프론트와 백엔드 연결 과정에서 에러 재현 조건을 문서화했다",
            ],
        },
        "사무직": {
            "posting_keywords": ["문서 작성", "정확성", "일정 관리", "협업", "업무 효율"],
            "posting_summary": "가상의 운영지원 조직에서 문서 정리, 일정 조율, 반복 업무 정확도를 중시하는 사무직 채용 공고",
            "experience_pool": [
                "가상의 운영 지원 업무에서 신청 서류 누락 항목을 점검하는 체크리스트를 만들었다",
                "회의 준비 자료를 부서별로 정리해 일정 변경 시 전달 속도를 높였다",
                "반복 보고서 양식을 표준화해 담당자 간 작성 편차를 줄였다",
                "업무 요청 접수 기록을 정리해 누락 가능성을 낮췄다",
            ],
        },
        "교육행정": {
            "posting_keywords": ["행정 처리", "민원 응대", "정확성", "문서 관리", "조율"],
            "posting_summary": "가상의 교육 운영팀에서 학사 안내, 민원 응대, 일정 조율, 공지 정확성을 중시하는 교육행정 채용 공고",
            "experience_pool": [
                "가상의 교육 프로그램에서 안내 문안을 정리해 반복 문의를 줄였다",
                "수강 일정 변경 내역을 문서화해 담당자 간 혼선을 줄였다",
                "문의 유형별 응대 기준을 정리해 응답 속도를 높였다",
                "운영 자료 배포 순서를 체크리스트화해 누락을 방지했다",
            ],
        },
        "마케팅": {
            "posting_keywords": ["성과 지표", "콘텐츠", "캠페인", "타깃", "분석"],
            "posting_summary": "가상의 브랜드 마케팅팀에서 콘텐츠 실험, 반응 분석, 캠페인 운영 경험을 중시하는 마케팅 채용 공고",
            "experience_pool": [
                "가상의 브랜드 과제에서 문구 버전을 나눠 반응 차이를 비교했다",
                "콘텐츠 업로드 일정과 채널별 메시지를 분리해 운영 효율을 높였다",
                "캠페인 회고 문서를 만들어 다음 실행 시 수정 포인트를 정리했다",
                "타깃별 반응을 비교하며 메시지 우선순위를 조정했다",
            ],
        },
        "사회복지사": {
            "posting_keywords": ["사례관리", "대상자 지원", "기록", "프로그램 운영", "위기 대응"],
            "posting_summary": "가상의 복지기관에서 사례관리, 프로그램 운영 기록, 대상자 지원 연계 역량을 중요하게 보는 사회복지사 채용 공고",
            "experience_pool": [
                "가상의 지역 프로그램에서 참여자 활동 기록 양식을 정리했다",
                "상담 내용을 기준별로 정리해 후속 지원 방향을 공유했다",
                "운영 일정과 참여자 문의를 함께 관리하며 누락 없는 대응 흐름을 만들었다",
                "협력기관 전달 내용을 문서화해 지원 연계 과정을 정리했다",
            ],
        },
    }

    SCENARIOS = [
        "too_abstract",
        "too_short",
        "too_long",
        "no_numbers",
        "weak_job_relevance",
        "poor_structure",
        "strong_needs_polishing",
        "career_changer",
        "no_experience",
        "project_experience",
    ]

    def __init__(self) -> None:
        self.anonymizer = AnonymizationService()

    def generate_dataset(self, count_per_role: int) -> list[dict]:
        samples: list[dict] = []
        for role, config in self.ROLE_CONFIGS.items():
            for index in range(count_per_role):
                scenario = self.SCENARIOS[index % len(self.SCENARIOS)]
                sample = self._build_sample(
                    job_role=role,
                    role_config=config,
                    scenario=scenario,
                    sequence=index + 1,
                )
                samples.append(sample)
        return samples

    def export(self, samples: list[dict], output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(json.dumps(sample, ensure_ascii=False) for sample in samples), encoding="utf-8")

    def validate_samples(self, samples: list[dict]) -> dict:
        seen_cover_letters = set()
        duplicate_count = 0
        pii_issues = 0
        schema_errors = 0
        assistant_json_errors = 0
        score_errors = 0

        for sample in samples:
            cover_letter = sample["original_cover_letter"]
            if cover_letter in seen_cover_letters:
                duplicate_count += 1
            seen_cover_letters.add(cover_letter)

            text_bundle = "\n".join(
                [
                    sample["fictional_job_posting_summary"],
                    sample["resume_summary"],
                    sample["original_cover_letter"],
                    sample["training_record"]["messages"][1]["content"],
                    sample["training_record"]["messages"][2]["content"],
                ]
            )
            if self.anonymizer.detect_remaining_pii(text_bundle):
                pii_issues += 1

            try:
                AIReviewResponse.model_validate(sample["review_result"])
            except Exception:  # noqa: BLE001
                schema_errors += 1

            try:
                assistant_payload = json.loads(sample["training_record"]["messages"][2]["content"])
                AIReviewResponse.model_validate(assistant_payload)
            except Exception:  # noqa: BLE001
                assistant_json_errors += 1

            if not self._scores_valid(sample["review_result"]):
                score_errors += 1

        return {
            "total_samples": len(samples),
            "duplicate_count": duplicate_count,
            "pii_issues": pii_issues,
            "schema_errors": schema_errors,
            "assistant_json_errors": assistant_json_errors,
            "score_errors": score_errors,
            "job_role_counts": Counter(sample["job_role"] for sample in samples),
        }

    def _build_sample(self, *, job_role: str, role_config: dict, scenario: str, sequence: int) -> dict:
        experience = role_config["experience_pool"][sequence % len(role_config["experience_pool"])]
        posting_summary = role_config["posting_summary"]
        resume_summary = self._build_resume_summary(job_role, experience, scenario, sequence)
        original_cover_letter = self._build_cover_letter(job_role, experience, scenario, sequence)
        review_result = self._build_review_result(job_role, original_cover_letter, role_config["posting_keywords"], scenario)
        training_record = {
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert Korean resume and cover letter coach. You provide strict, practical, job-relevant feedback.",
                },
                {
                    "role": "user",
                    "content": (
                        f"지원 직무: {job_role}\n"
                        f"채용공고: {posting_summary}\n"
                        f"이력서 요약: {resume_summary}\n"
                        f"자기소개서 원문: {original_cover_letter}"
                    ),
                },
                {"role": "assistant", "content": json.dumps(review_result, ensure_ascii=False)},
            ],
            "metadata": {
                "job_role": job_role,
                "data_source": "manual_seed",
                "quality_status": "draft",
            },
        }
        return {
            "job_role": job_role,
            "fictional_job_posting_summary": posting_summary,
            "resume_summary": resume_summary,
            "original_cover_letter": original_cover_letter,
            "review_result": review_result,
            "data_source": "manual_seed",
            "quality_status": "draft",
            "training_record": training_record,
        }

    def _build_resume_summary(self, job_role: str, experience: str, scenario: str, sequence: int) -> str:
        scenario_hint = {
            "career_changer": "다른 직무 경험을 바탕으로 전환을 준비 중",
            "no_experience": "직무 관련 실무 경험은 없지만 과제와 활동을 정리 중",
            "project_experience": "프로젝트 중심 경험을 이력서에 정리함",
        }.get(scenario, "가상의 프로젝트 및 활동 경험을 정리함")
        return f"{job_role} 지원자 {sequence}번. {experience}. {scenario_hint}."

    def _build_cover_letter(self, job_role: str, experience: str, scenario: str, sequence: int) -> str:
        base = {
            "too_abstract": f"저는 {job_role} 직무에 필요한 책임감과 성실함을 갖추고 있다고 생각합니다. {experience} 경험이 있었지만, 무엇보다 중요한 것은 배우려는 태도라고 믿습니다. 조직에 빠르게 적응하며 맡은 일을 열심히 수행하겠습니다.",
            "too_short": f"{job_role}로 성장하고 싶습니다. {experience}. 더 배우겠습니다.",
            "too_long": f"저는 {job_role}에 지원하며 준비 과정에서 다양한 활동을 돌아보았습니다. {experience}. 이 과정에서 협업의 중요성을 느꼈고, 작은 기능 하나를 만들더라도 사용자 입장에서 다시 점검하는 습관을 들였습니다. 또한 일정이 바뀔 때마다 우선순위를 다시 정리하며 해야 할 일과 미뤄도 되는 일을 구분했습니다. 다만 이런 경험을 한 번에 너무 많이 설명하려다 보니 핵심 문장이 길어지는 편이 있었고, 실제 성과를 한 줄로 정리하는 습관은 아직 부족했습니다. 그럼에도 저는 정리된 기록을 남기고, 다음 개선 포인트를 문서화하며 꾸준히 발전해 왔습니다. 입사 후에도 같은 태도로 배우고 기여하겠습니다.",
            "no_numbers": f"{experience}. 저는 이 경험을 통해 협업과 실행의 중요성을 배웠고, 맡은 역할을 끝까지 책임지는 태도를 갖추게 되었습니다. 다만 성과를 수치로 표현한 적은 많지 않지만, 실제로 팀의 작업 흐름이 더 매끄러워졌다는 평가를 받았습니다.",
            "weak_job_relevance": f"저는 다양한 활동을 경험하며 사람들과 소통하는 법을 배웠습니다. 학교 행사 준비와 동아리 운영을 하면서 성실하게 역할을 해냈고, 주어진 일을 꼼꼼히 처리했습니다. {experience}. 아직 {job_role}와 직접 연결된 문장은 많지 않지만 빠르게 적응할 수 있다고 생각합니다.",
            "poor_structure": f"저는 맡은 일을 끝까지 하는 편입니다. {experience}. 협업도 중요했고 그래서 저는 소통을 잘하려고 했습니다. 그리고 배우는 것도 중요합니다. 입사 후에도 열심히 하겠습니다. 특히 직무에 필요한 역량을 키우려고 했고 그래서 프로젝트도 했습니다. 정리하면 저는 성장 가능성이 있습니다.",
            "strong_needs_polishing": f"{experience}. 저는 이 경험을 통해 문제를 발견하면 바로 실행으로 옮기기보다 먼저 원인을 정리하는 습관을 갖게 되었습니다. 협업 과정에서는 작업 기준을 문서로 남겨 팀이 같은 방향으로 움직일 수 있도록 했고, 사용자의 불편을 줄이기 위한 수정 포인트를 우선순위에 따라 반영했습니다. 전체적으로 방향은 맞지만 문장 연결을 더 다듬으면 강점이 더 선명하게 드러날 수 있다고 생각합니다.",
            "career_changer": f"저는 다른 분야에서 일하며 쌓은 정리 습관과 커뮤니케이션 경험을 바탕으로 {job_role}로 전환하고자 합니다. {experience}. 처음에는 용어와 업무 흐름이 낯설었지만, 과제를 수행하며 필요한 기준을 정리하고 부족한 부분을 스스로 학습했습니다. 전환 과정이기 때문에 직접 경험은 짧지만 학습 속도와 실행력을 강점으로 생각합니다.",
            "no_experience": f"직접적인 실무 경험은 없지만, {job_role}에 필요한 기본 역량을 갖추기 위해 과제와 팀 활동을 꾸준히 정리했습니다. {experience}. 아직 현업 수준의 경험은 부족하지만, 배운 내용을 빠르게 적용하고 피드백을 반영하는 태도는 강점이라고 생각합니다.",
            "project_experience": f"{experience}. 프로젝트를 진행하면서 요구사항을 나눠 보고, 내가 맡은 역할을 분명히 한 뒤 결과물을 개선하는 과정을 반복했습니다. 그 과정에서 협업과 일정 관리의 중요성을 배웠고, 사용자의 입장에서 어떤 부분이 불편한지 먼저 생각하는 습관을 갖게 됐습니다. 직무와 직접 연결되는 경험을 계속 쌓아가고 싶습니다.",
        }[scenario]
        return f"{base} 이 예시는 가상의 합격 문안 {sequence}번입니다."

    def _build_review_result(self, job_role: str, original_cover_letter: str, keywords: list[str], scenario: str) -> dict:
        score_map = {
            "too_abstract": (64, 58, 52, 72, 60, 65, 55),
            "too_short": (55, 42, 35, 61, 50, 48, 40),
            "too_long": (71, 68, 58, 64, 70, 60, 66),
            "no_numbers": (72, 69, 49, 74, 71, 73, 67),
            "weak_job_relevance": (57, 63, 54, 72, 60, 68, 45),
            "poor_structure": (68, 66, 58, 63, 69, 52, 64),
            "strong_needs_polishing": (82, 78, 71, 79, 80, 77, 75),
            "career_changer": (63, 70, 56, 76, 69, 72, 58),
            "no_experience": (59, 62, 44, 74, 61, 69, 57),
            "project_experience": (79, 76, 68, 78, 77, 76, 73),
        }[scenario]
        scores = {
            "job_fit": score_map[0],
            "specificity": score_map[1],
            "achievement": score_map[2],
            "writing_quality": score_map[3],
            "uniqueness": score_map[4],
            "structure": score_map[5],
            "keyword_match": score_map[6],
        }
        total_score = round(sum(scores.values()) / len(scores), 1)
        missing_keywords = [keyword for keyword in keywords if keyword not in original_cover_letter][:3]
        payload = {
            "total_score": total_score,
            "scores": scores,
            "summary": f"{job_role} 지원서로서 기본 방향은 보이지만, {scenario.replace('_', ' ')} 유형의 약점이 있어 수정 전에는 경쟁력이 제한적입니다.",
            "problems": [
                "핵심 경험은 있으나 직무와 직접 연결되는 문장이 더 필요합니다.",
                "성과 근거나 구체적 역할 설명이 약해 설득력이 충분하지 않습니다.",
                "문장 배열 또는 길이 조절을 통해 읽는 흐름을 더 매끄럽게 만들 필요가 있습니다.",
            ],
            "improvement_strategy": [
                "경험마다 상황, 역할, 행동, 결과 순서로 다시 정리합니다.",
                "가능한 부분에는 수치, 빈도, 개선 폭 중 하나 이상을 붙입니다.",
                "채용 키워드를 행동과 결과 문장에 직접 연결합니다.",
            ],
            "improved_cover_letter": (
                f"저는 {job_role} 직무에 맞는 경험을 단순 나열하지 않고, 실제로 어떤 역할을 맡아 무엇을 개선했는지 분명하게 설명하고자 합니다. "
                f"{original_cover_letter[:220]} "
                "기존 문안의 방향은 유지하되, 직무 관련성과 성과 근거가 더 선명하게 드러나도록 다듬었습니다."
            ),
            "interview_questions": [
                "이 경험에서 본인이 맡은 역할을 가장 구체적으로 설명해 주세요.",
                "성과를 수치로 제시하지 못한 이유와 보완 방법은 무엇인가요?",
                "채용공고의 요구 역량과 연결되는 경험을 하나만 골라 설명해 주세요.",
            ],
            "missing_keywords": missing_keywords,
            "strengths": [
                "지원 동기와 성장 의지는 문안 안에서 확인됩니다.",
                "가상의 경험이라도 실무에 연결하려는 방향성은 보입니다.",
                "전체 톤은 과장보다 안정적인 편입니다.",
            ],
        }
        return AIReviewResponse.model_validate(payload).model_dump()

    def _scores_valid(self, review_result: dict) -> bool:
        try:
            AIReviewResponse.model_validate(review_result)
            return True
        except Exception:  # noqa: BLE001
            return False
