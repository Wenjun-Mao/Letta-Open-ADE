"""Thin executor candidates for the ADE-native runtime study."""

from .custom_loop import CustomLoopAdapter
from .pydantic_ai_adapter import PydanticAIAdapter

__all__ = ["CustomLoopAdapter", "PydanticAIAdapter"]
