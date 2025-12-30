"""Crucible integration adapter for Synapse.

Handles Crucible engine lifecycle and router configuration.
"""

import os
from typing import Optional

try:
    from crucible import Crucible, EngineConfig
    from crucible.config import RoutingMode
    from crucible.routing import RoleSpecializedRouter, CostAwareRouter
    from crucible.routing.defaults import DEFAULT_ROLE_POOLS

    CRUCIBLE_AVAILABLE = True
except ImportError:
    CRUCIBLE_AVAILABLE = False
    Crucible = None
    EngineConfig = None
    RoutingMode = None
    RoleSpecializedRouter = None
    CostAwareRouter = None
    DEFAULT_ROLE_POOLS = None


class CrucibleAdapter:
    """Adapter for Crucible deliberative council engine.

    Manages engine lifecycle, router configuration, and async execution.
    Returns only final deliberated responses (observability disabled).
    """

    def __init__(self) -> None:
        """Initialize adapter with OpenRouter API key from environment."""
        if not CRUCIBLE_AVAILABLE:
            raise ImportError(
                "Crucible module not found. "
                "Install with: pip install -e C:\\Users\\erick\\projects\\Crucible"
            )

        self._key = os.environ.get("OPENROUTER_KEY")
        if not self._key:
            raise ValueError(
                "OPENROUTER_KEY environment variable not set. "
                "Crucible requires OpenRouter API access."
            )
        self._engine: Optional[Crucible] = None
        self._current_mode: Optional[str] = None

    def get_engine(self, router_mode: str) -> Crucible:
        """Get or create Crucible engine with specified router.

        Engine is recreated if router mode changes to ensure correct configuration.

        Args:
            router_mode: "Auto", "Custom-Role", or "Custom-Cost"

        Returns:
            Configured Crucible engine instance

        Raises:
            ValueError: If router_mode is invalid
        """
        if self._engine is None or self._current_mode != router_mode:
            config = self._build_config(router_mode)
            self._engine = Crucible(config=config)
            self._current_mode = router_mode
        return self._engine

    def _build_config(self, router_mode: str) -> EngineConfig:
        """Build EngineConfig based on router mode selection.

        Args:
            router_mode: Router mode string

        Returns:
            Configured EngineConfig
        """
        if router_mode == "Auto":
            return EngineConfig(
                openrouter_api_key=self._key,
                routing_mode=RoutingMode.AUTO,
                observability=False,  # Final answer only
            )
        elif router_mode == "Custom-Role":
            return EngineConfig(
                openrouter_api_key=self._key,
                routing_mode=RoutingMode.CUSTOM,
                custom_router=RoleSpecializedRouter(
                    role_pools=DEFAULT_ROLE_POOLS,
                    max_per_vendor=2,
                ),
                observability=False,
            )
        elif router_mode == "Custom-Cost":
            return EngineConfig(
                openrouter_api_key=self._key,
                routing_mode=RoutingMode.CUSTOM,
                custom_router=CostAwareRouter(),
                observability=False,
            )
        else:
            raise ValueError(f"Unknown router mode: {router_mode}")

    async def run(self, query: str, router_mode: str) -> str:
        """Run Crucible deliberation and return final answer.

        Args:
            query: User query to deliberate on
            router_mode: Router configuration to use

        Returns:
            Deliberated final response as string
        """
        engine = self.get_engine(router_mode)
        result = await engine.run(query)
        return result.final_response

    @staticmethod
    def is_available() -> bool:
        """Check if Crucible is available for use.

        Returns:
            True if Crucible module is installed
        """
        return CRUCIBLE_AVAILABLE

    @staticmethod
    def has_api_key() -> bool:
        """Check if OPENROUTER_KEY environment variable is set.

        Returns:
            True if API key is available
        """
        return bool(os.environ.get("OPENROUTER_KEY"))
