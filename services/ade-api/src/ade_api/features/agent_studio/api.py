from fastapi import APIRouter

from .agents_api import router as agents_router
from .lifecycle_api import router as lifecycle_router
from .messages_api import router as messages_router
from .runtime_api import router as runtime_router
from .state_api import router as state_router


router = APIRouter()
router.include_router(agents_router)
router.include_router(lifecycle_router)
router.include_router(messages_router)
router.include_router(runtime_router)
router.include_router(state_router)
