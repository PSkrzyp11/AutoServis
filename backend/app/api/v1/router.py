from fastapi import APIRouter

from app.api.v1 import (
    admin_users,
    admin_workshops,
    auth,
    users,
    vehicles,
    workshop_resources,
    workshops,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(workshops.router)
api_router.include_router(workshop_resources.router)
api_router.include_router(vehicles.router)
api_router.include_router(admin_users.router)
api_router.include_router(admin_workshops.router)
