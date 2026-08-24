from fastapi import APIRouter

from .authoring_api import router as authoring_router
from .catalog_api import router as catalog_router
from .lifecycle_api import router as lifecycle_router
from .runtime_api import router as runtime_router


router = APIRouter()
router.include_router(catalog_router)
router.include_router(authoring_router)
router.include_router(lifecycle_router)
router.include_router(runtime_router)
