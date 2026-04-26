"""Registry for Agent Adapters."""

from typing import Dict, Type, Optional, Callable, Coroutine
from .base import AgentAdapter
from .antigravity import AntigravityAdapter
from src.models import LogEntry

class AdapterRegistry:
    """Stores available adapter classes and handles instantiation."""
    
    _adapters: Dict[str, Type[AgentAdapter]] = {}

    @classmethod
    def register(cls, name: str, adapter_cls: Type[AgentAdapter]) -> None:
        """Register a new adapter class."""
        cls._adapters[name] = adapter_cls

    @classmethod
    def get(cls, name: str, emit_callback: Callable[[LogEntry], Coroutine]) -> AgentAdapter:
        """Instantiate an adapter by name."""
        adapter_cls = cls._adapters.get(name)
        if not adapter_cls:
            raise ValueError(f"No adapter registered for name: {name}")
        return adapter_cls(name, emit_callback)

# Pre-register built-in adapters
AdapterRegistry.register("antigravity", AntigravityAdapter)
AdapterRegistry.register("antigravity_pty", AntigravityAdapter)
