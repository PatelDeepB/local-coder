"""Server and CLI interfaces package."""

from local_coder.server.api_server import app
from local_coder.server.cli_app import main as cli_main

__all__ = ["app", "cli_main"]
