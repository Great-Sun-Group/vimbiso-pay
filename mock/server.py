"""Mock WhatsApp server implementation."""
import json
import logging
import os
import socketserver
from http.server import SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

import requests

from whatsapp_utils import extract_message_text

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TARGETS = {
    'local': 'http://app:8000/bot/webhook',
    'staging': 'https://stage.whatsapp.vimbisopay.africa/bot/webhook'
}


class MockWhatsAppHandler(SimpleHTTPRequestHandler):
    """Handler for serving mock WhatsApp interface and handling webhooks."""

    def __init__(self, *args, directory=None, **kwargs):
        # Set directory before parent initialization
        if directory is None:
            directory = '/app/mock' if os.path.exists('/app/mock') else os.path.dirname(os.path.abspath(__file__))

        logger.info(f"Setting server directory to: {directory}")
        logger.info(f"Directory contents: {os.listdir(directory)}")

        # Initialize with directory
        super().__init__(*args, directory=directory, **kwargs)

    def _handle_webhook(self):
        """Handle webhook POST request."""
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length)
        payload = json.loads(post_data.decode("utf-8"))

        # Get target from query params
        parsed_url = urlparse(self.path)
        params = parse_qs(parsed_url.query)
        target = params.get('target', ['local'])[0]

        # Extract message details
        message_data = payload["entry"][0]["changes"][0]["value"]
        message = message_data["messages"][0]
        text = extract_message_text(message)

        # Log request details
        logger.info(f"\nReceived message: {text}")
        logger.info(f"Target: {target}\n")

        # Forward to target server
        target_url = TARGETS.get(target, TARGETS['local'])
        headers = {
            "Content-Type": "application/json",
            "X-Mock-Testing": "true",
            "Accept": "application/json"
        }

        try:
            response = requests.post(
                target_url,
                json=payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            response_data = json.loads(response.text)

            # Send response - don't wrap in extra "response" field
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))

        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            logger.error(f"Error: {str(e)}")
            self.send_error(500, "Internal Server Error", str(e))

    def do_POST(self):
        """Handle POST requests."""
        try:
            if self.path.startswith("/bot/webhook"):
                self._handle_webhook()
            else:
                self.send_error(404, "Not Found")
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            self.send_error(500, "Internal Server Error")

    def do_GET(self):
        """Handle GET requests."""
        # Log request details
        logger.info(f"GET request for path: {self.path}")

        # Serve index.html for root path
        if self.path == "/" or self.path == "":
            self.path = "/index.html"

        # Let parent class handle file serving
        return SimpleHTTPRequestHandler.do_GET(self)


def run_server(port=8001):
    """Run the mock server."""
    logger.info(f"\nStarting mock WhatsApp server on port {port}")
    logger.info(f"Available targets: {', '.join(TARGETS.keys())}")
    logger.info("\nOpen http://localhost:8001 in your browser")

    # Log current environment
    logger.info(f"Current working directory: {os.getcwd()}")
    logger.info(f"Directory contents: {os.listdir(os.getcwd())}")
    if os.path.exists('/app/mock'):
        logger.info(f"Docker mount contents: {os.listdir('/app/mock')}")

    server = socketserver.TCPServer(("", port), MockWhatsAppHandler)
    server.allow_reuse_address = True

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
