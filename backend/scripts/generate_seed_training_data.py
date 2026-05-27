from argparse import ArgumentParser
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.seed_data_generator import SeedDataGenerator


def main() -> None:
    parser = ArgumentParser(description="Generate fictional seed training data for Korean resume/cover-letter review.")
    parser.add_argument("--count-per-role", type=int, default=50, help="Number of fictional samples to generate per job role")
    args = parser.parse_args()

    generator = SeedDataGenerator()
    samples = generator.generate_dataset(count_per_role=args.count_per_role)
    validation = generator.validate_samples(samples)

    if validation["duplicate_count"] > 0:
        raise SystemExit(f"Duplicate cover letters detected: {validation['duplicate_count']}")
    if validation["pii_issues"] > 0:
        raise SystemExit(f"PII issues detected: {validation['pii_issues']}")
    if validation["schema_errors"] > 0 or validation["assistant_json_errors"] > 0 or validation["score_errors"] > 0:
        raise SystemExit(
            "Validation failed: "
            f"schema_errors={validation['schema_errors']}, "
            f"assistant_json_errors={validation['assistant_json_errors']}, "
            f"score_errors={validation['score_errors']}"
        )

    output_path = Path(__file__).resolve().parents[2] / "data" / "seed" / "generated_seed_samples.jsonl"
    generator.export(samples, output_path)

    print(f"Generated {validation['total_samples']} fictional seed samples")
    print(f"Output: {output_path}")
    for role, count in validation["job_role_counts"].items():
        print(f"  {role}: {count}")


if __name__ == "__main__":
    main()
