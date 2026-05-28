"""
main.py — FastAPI application factory.
Configures CORS middleware and mounts all API routers under /api/v1.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import admin, auth, billing, blocks, branching, clerk_webhook, design_sheet, discovery, exports, inbox, integrations, library, market, meta, module_pathway, modules, pathways, pipeline, projects, prompts, sharing, sprints, templates, webhooks


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    is_production = settings.ENVIRONMENT == "production"
    app = FastAPI(
        title=settings.APP_NAME,
        version="0.1.0",
        docs_url=None if is_production else "/api/docs",
        redoc_url=None if is_production else "/api/redoc",
        openapi_url=None if is_production else "/api/openapi.json",
        redirect_slashes=False,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    prefix = "/api/v1"
    app.include_router(auth.router, prefix=prefix)
    app.include_router(projects.router, prefix=prefix)
    app.include_router(discovery.router, prefix=prefix)
    app.include_router(design_sheet.router, prefix=prefix)
    app.include_router(blocks.router, prefix=prefix)
    app.include_router(pipeline.router, prefix=prefix)
    app.include_router(prompts.router, prefix=prefix)
    app.include_router(market.router, prefix=prefix)
    app.include_router(exports.router, prefix=prefix)
    app.include_router(exports.versions_router, prefix=prefix)
    app.include_router(library.router, prefix=prefix)
    app.include_router(sharing.router, prefix=prefix)
    app.include_router(sprints.router, prefix=prefix)
    app.include_router(pathways.router, prefix=prefix)
    app.include_router(module_pathway.router, prefix=prefix)
    app.include_router(modules.router, prefix=prefix)
    app.include_router(meta.router, prefix=prefix)
    app.include_router(inbox.router, prefix=prefix)
    app.include_router(templates.router, prefix=prefix)
    app.include_router(branching.router, prefix=prefix)
    app.include_router(integrations.router, prefix=prefix)
    app.include_router(webhooks.router, prefix=prefix)
    app.include_router(billing.router, prefix=prefix)
    app.include_router(clerk_webhook.router, prefix=prefix)
    app.include_router(admin.router, prefix=prefix)

    @app.get("/api/v1/health")
    async def health():
        """Health check endpoint."""
        return {"status": "ok"}

    return app


app = create_app()
