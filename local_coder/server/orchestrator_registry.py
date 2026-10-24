"""Registry for the active LocalCoderOrchestrator singleton in the server process."""

from typing import Optional
from local_coder.orchestrator import LocalCoderOrchestrator

_orchestrator_instance: Optional[LocalCoderOrchestrator] = None


def set_orchestrator(orchestrator: Optional[LocalCoderOrchestrator]) -> None:
    """Sets the active orchestrator instance."""
    global _orchestrator_instance
    _orchestrator_instance = orchestrator


def get_orchestrator() -> Optional[LocalCoderOrchestrator]:
    """Retrieves the active orchestrator instance."""
    from local_coder.server import api_server
    if getattr(api_server, "orchestrator_instance", None) is not None:
        return api_server.orchestrator_instance
    return _orchestrator_instance
