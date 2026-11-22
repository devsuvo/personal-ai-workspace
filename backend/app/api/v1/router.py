from fastapi import APIRouter

from app.api.v1.endpoints import (
    analytics,
    artifacts,
    backups,
    chat,
    conversations,
    files,
    health,
    messages,
    projects,
    prompts,
    providers,
    settings,
    system,
    tools,
)

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(system.router)
api_v1_router.include_router(backups.router)
api_v1_router.include_router(settings.router)
api_v1_router.include_router(providers.router)
api_v1_router.include_router(projects.router)
api_v1_router.include_router(files.router)
api_v1_router.include_router(artifacts.router)
api_v1_router.include_router(conversations.router)
api_v1_router.include_router(messages.router)
api_v1_router.include_router(chat.router)
api_v1_router.include_router(tools.router)
api_v1_router.include_router(prompts.router)
api_v1_router.include_router(analytics.router)
