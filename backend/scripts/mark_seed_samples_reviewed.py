from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings
from app.db.bootstrap import ensure_schema_updates
from app.db.session import Base, SessionLocal, engine
from app.services.seed_ingestion_service import SeedIngestionService


def main() -> None:
    app_env = settings.app_env.lower().strip()
    if app_env not in {"local", "development"}:
        raise SystemExit("This script only runs when APP_ENV is local or development.")
    if not settings.admin_emails:
        raise SystemExit("ADMIN_EMAILS must include at least one admin email for local bulk review.")

    Base.metadata.create_all(bind=engine)
    ensure_schema_updates(engine)

    db = SessionLocal()
    try:
        service = SeedIngestionService()
        reviewer = service.ensure_local_admin_user(db, settings.admin_emails[0])
        updated_count = service.bulk_mark_manual_seed_reviewed(
            db,
            reviewer_admin_id=reviewer.id,
        )
        print("Manual seed bulk review completed")
        print(f"reviewer_email={reviewer.email}")
        print(f"updated_count={updated_count}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
