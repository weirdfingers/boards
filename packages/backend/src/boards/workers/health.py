"""
Minimal HTTP health check server for Cloud Run compatibility.

Cloud Run requires containers to listen on a port and respond to health checks.
This module provides a lightweight HTTP server that runs alongside the dramatiq
worker to satisfy Cloud Run's health check requirements.
"""

import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

from boards.logging import get_logger

logger = get_logger(__name__)


class HealthHandler(BaseHTTPRequestHandler):
    """HTTP request handler that responds to health check probes."""

    def do_GET(self) -> None:
        """Handle GET requests - respond OK to /health or /."""
        if self.path in ("/health", "/"):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        """Suppress default HTTP logging to avoid noise."""
        pass


def start_health_server(port: int | None = None) -> HTTPServer:
    """
    Start the health check HTTP server.

    Args:
        port: Port to listen on. Defaults to PORT env var or 8080.

    Returns:
        The running HTTPServer instance.
    """
    if port is None:
        port = int(os.environ.get("PORT", 8080))

    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info("Health check server started", port=port)
    server.serve_forever()
    return server


def start_health_server_thread(port: int | None = None) -> Thread:
    """
    Start the health check server in a background daemon thread.

    Args:
        port: Port to listen on. Defaults to PORT env var or 8080.

    Returns:
        The daemon thread running the health server.
    """
    if port is None:
        port = int(os.environ.get("PORT", 8080))

    thread = Thread(target=start_health_server, args=(port,), daemon=True)
    thread.start()
    return thread
