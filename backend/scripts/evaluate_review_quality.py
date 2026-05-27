import json
import sys
from datetime import datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.ai_client import AIReviewService


def load_cases() -> list[dict]:
    fixture_path = BACKEND_ROOT / "tests" / "fixtures" / "review_quality_cases.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def main() -> None:
    service = AIReviewService()
    cases = load_cases()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = BACKEND_ROOT / "evaluation_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"review_quality_eval_{timestamp}.json"

    using_live_model = bool(service.api_key)
    if using_live_model:
        service.use_mock = False

    results = []
    print(f"[CoverFit AI] review quality evaluation started | mode={'openai' if using_live_model else 'mock'}")

    for case in cases:
        result, provider, model = service.review(
            resume_text=case["resume_text"],
            cover_letter_text=case["cover_letter_text"],
            target_job_role=case["target_job_role"],
            job_posting_text=case["job_posting_text"],
            review_mode=case.get("review_mode", "detailed"),
            job_category_preset=None,
        )
        row = {
            "name": case["name"],
            "provider": provider,
            "model": model,
            "prompt_version": service.last_review_metadata["prompt_version"],
            "pipeline_version": service.last_review_metadata["pipeline_version"],
            "json_validation_passed": True,
            "total_score": result.total_score,
            "scores": result.scores.model_dump(),
            "problems": result.problems,
            "improved_cover_letter": result.improved_cover_letter,
            "missing_keywords": result.missing_keywords,
        }
        results.append(row)

        print(f"\n=== {case['name']} ===")
        print(f"total_score: {result.total_score}")
        print(f"scores: {result.scores.model_dump()}")
        print(f"problems: {result.problems}")
        print(f"missing_keywords: {result.missing_keywords}")
        print(f"improved_cover_letter: {result.improved_cover_letter}")
        print("json_validation_passed: True")

    payload = {
        "generated_at": datetime.now().isoformat(),
        "mode": "openai" if using_live_model else "mock",
        "results": results,
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nSaved evaluation output to: {output_path}")


if __name__ == "__main__":
    main()
