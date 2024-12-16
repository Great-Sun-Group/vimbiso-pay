"""Mock WhatsApp server implementation."""
import json
import logging
import os
import socketserver
from http.server import SimpleHTTPRequestHandler

import requests

from whatsapp_utils import (
    create_whatsapp_payload,
    extract_message_text,
    format_mock_response
)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# The actual app endpoint we're testing
APP_ENDPOINT = 'http://app:8000/bot/webhook'


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
        mock_request = json.loads(post_data.decode("utf-8"))

        # Create WhatsApp-formatted webhook payload
        whatsapp_payload = create_whatsapp_payload(
            phone_number=mock_request.get("phone", "263778177125"),
            message_type=mock_request.get("type", "text"),
            message_text=mock_request.get("message", ""),
            phone_number_id="390447444143042"  # Match staging phone number ID
        )

        # Extract message details for logging
        message_data = whatsapp_payload["entry"][0]["changes"][0]["value"]
        message = message_data["messages"][0]
        text = extract_message_text(message)

        # Log request details
        logger.info(f"\nReceived message: {text}")
        logger.info(f"WhatsApp webhook payload: {json.dumps(whatsapp_payload, indent=2)}")

        try:
            # Forward to app with WhatsApp webhook format
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Mock-Testing": "true"  # Indicate this is from mock
            }

            response = requests.post(
                APP_ENDPOINT,
                json=whatsapp_payload,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            response_data = response.json()

            # Format response like WhatsApp's API
            mock_response = format_mock_response()

            # Send response
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(mock_response).encode('utf-8'))

            # Log response for debugging
            logger.info(f"\nApp response: {json.dumps(response_data, indent=2)}")
            logger.info(f"Mock response: {json.dumps(mock_response, indent=2)}")

        except Exception as e:
            logger.error(f"Error: {str(e)}")
            if isinstance(e, requests.exceptions.RequestException) and hasattr(e, 'response'):
                logger.error(f"App response: {e.response.text}")
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
    logger.info(f"Forwarding requests to: {APP_ENDPOINT}")
    logger.info("\nOpen http://localhost:8001 in your browser")

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
