from collections import Counter
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.db.bootstrap import ensure_schema_updates
from app.db.session import Base, SessionLocal, engine
from app.models.review import AnonymizedTrainingSample, ImportedDocument
from app.services.dataset_builder import DatasetBuilderService


def main() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_schema_updates(engine)
    db = SessionLocal()
    try:
        dataset_builder = DatasetBuilderService()
        samples = db.scalars(select(AnonymizedTrainingSample)).all()
        previews = dataset_builder.list_training_samples(db)
        by_job_role = Counter(item["job_role"] for item in previews)
        by_source_type = Counter(item["source_type"] or "unknown" for item in previews)
        duplicate_counter = Counter()
        invalid_count = 0
        pii_count = 0

        for sample in samples:
            record = dataset_builder.ensure_training_record(db, sample)
            user_text = record["messages"][1]["content"]
            duplicate_counter[user_text] += 1
            errors = dataset_builder.validate_training_record(record, sample)
            if errors:
                invalid_count += 1
                if any("PII" in err or "pii" in err for err in errors):
                    pii_count += 1

        duplicate_texts = sum(1 for _text, count in duplicate_counter.items() if count > 1)
        print("Validation Summary")
        print(f"total_samples={len(samples)}")
        print(f"invalid_samples={invalid_count}")
        print(f"samples_with_pii_signals={pii_count}")
        print(f"duplicate_user_texts={duplicate_texts}")
        print("samples_by_job_role")
        for key, value in sorted(by_job_role.items()):
            print(f"  {key}: {value}")
        print("samples_by_source_type")
        for key, value in sorted(by_source_type.items()):
            print(f"  {key}: {value}")

        documents = db.scalars(select(ImportedDocument)).all()
        print(f"imported_documents={len(documents)}")
        exportable = sum(1 for preview in previews if preview["valid_for_export"])
        print(f"export_ready_samples={exportable}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
