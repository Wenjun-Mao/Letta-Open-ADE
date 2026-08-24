from fastapi import APIRouter

from .metadata_api import router as metadata_router
from .personas_api import router as personas_router
from .prompts_api import router as prompts_router


router = APIRouter()
router.include_router(prompts_router)
router.include_router(personas_router)
router.include_router(metadata_router)
