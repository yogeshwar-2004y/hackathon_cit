from fastapi import APIRouter
from api.routers.user import user_router

router = APIRouter()

router.include_router(user_router)


