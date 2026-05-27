from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, auth, reviews
from app.core.config import settings
from app.db.bootstrap import ensure_schema_updates
from app.db.session import Base, engine


def create_app() -> FastAPI:
    app = FastAPI(
        title="ai 이력서 첨삭",
        version="0.1.0",
        description="Korean AI resume and cover letter review platform MVP.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def on_startup() -> None:
        Base.metadata.create_all(bind=engine)
        ensure_schema_updates(engine)

    @app.get("/health")
    def healthcheck() -> dict[str, str]:
        ai_mode = "mock" if settings.mock_ai_mode or not settings.openai_api_key else "openai"
        return {"status": "ok", "ai_mode": ai_mode}

    app.include_router(auth.router, prefix="/auth", tags=["auth"])
    app.include_router(reviews.router, prefix="/reviews", tags=["reviews"])
    app.include_router(admin.router, prefix="/admin", tags=["admin"])
    return app


app = create_app()
