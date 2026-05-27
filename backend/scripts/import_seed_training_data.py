from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.bootstrap import ensure_schema_updates
from app.db.session import Base, SessionLocal, engine
from app.services.seed_ingestion_service import SeedIngestionService


def main() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_schema_updates(engine)

    root_dir = Path(__file__).resolve().parents[2]
    jsonl_path = root_dir / "data" / "seed" / "generated_seed_samples.jsonl"
    if not jsonl_path.exists():
        raise SystemExit(f"Seed dataset file not found: {jsonl_path}")

    db = SessionLocal()
    try:
        service = SeedIngestionService()
        summary = service.import_seed_jsonl(db, jsonl_path=jsonl_path)
        print("Seed import completed")
        print(f"data_source_id={summary['data_source_id']}")
        print(f"imported_count={summary['imported_count']}")
        print(f"skipped_duplicates={summary['skipped_duplicates']}")
        print(f"rejected_count={summary['rejected_count']}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
