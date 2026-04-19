"""Vision-RCP Agent Adapters."""

from .base import AgentAdapter
from .registry import AdapterRegistry
from .antigravity import AntigravityAdapter

__all__ = ["AgentAdapter", "AdapterRegistry", "AntigravityAdapter"]
