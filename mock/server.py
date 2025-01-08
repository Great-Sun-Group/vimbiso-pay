"""Mock WhatsApp server implementation."""
import json
import logging
import os
import socketserver
import threading
from http.server import SimpleHTTPRequestHandler

import requests
from whatsapp_utils import create_whatsapp_payload

# Configure logging - just show messages
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

# Silence connection logs
logging.getLogger("urllib3").setLevel(logging.WARNING)

# The actual app endpoint we're testing
APP_ENDPOINT = 'http://app:8000/bot/webhook'


class MockWhatsAppHandler(SimpleHTTPRequestHandler):
    """Handler for serving mock WhatsApp interface and handling webhooks."""

    def __init__(self, *args, directory=None, **kwargs):
        # Set directory before parent initialization
        if directory is None:
            directory = '/app/mock' if os.path.exists('/app/mock') else os.path.dirname(os.path.abspath(__file__))
        super().__init__(*args, directory=directory, **kwargs)

    def _forward_to_app(self, mock_request):
        """Forward message from UI to app."""
        # Format for WhatsApp
        whatsapp_payload = create_whatsapp_payload(
            phone_number=mock_request.get("phone", "263778177125"),
            message_type=mock_request.get("type", "text"),
            message_text=mock_request.get("message", ""),
            phone_number_id="390447444143042"
        )

        # Add context if interactive
        if mock_request.get("type") == "interactive" and mock_request.get("context_id"):
            whatsapp_payload["entry"][0]["changes"][0]["value"]["messages"][0]["context"] = {
                "from": mock_request.get("context_from", "15550783881"),
                "id": mock_request.get("context_id")
            }

        # Forward to app asynchronously
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Mock-Testing": "true",
            "X-Mock-Context": json.dumps({
                "message_type": mock_request.get("type"),
                "has_context": bool(mock_request.get("context_id"))
            })
        }

        def send_request():
            try:
                requests.post(APP_ENDPOINT, json=whatsapp_payload, headers=headers, timeout=10)
            except Exception as e:
                logger.error("Error forwarding to app: %s", e)

        thread = threading.Thread(target=send_request)
        thread.daemon = True  # Thread will exit when main thread exits
        thread.start()

    def _format_ui_message(self, app_message):
        """Format app message for UI."""
        if app_message.get("type") == "text":
            return {
                "type": "text",
                "text": app_message.get("text", {}),
                "timestamp": "",
                "status": "success"
            }
        elif app_message.get("type") == "interactive":
            return {
                "type": "interactive",
                "interactive": app_message.get("interactive", {}),
                "timestamp": "",
                "status": "success"
            }
        return app_message

    def _handle_webhook(self):
        """Handle webhook POST request."""
        try:
            # Read request
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode("utf-8"))

            # Send immediate success response
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()

            # For App->UI messages, include formatted message in response
            if "messaging_product" in request_data and request_data["messaging_product"] == "whatsapp":
                logger.info("App -> UI: %s", request_data)
                response_data = self._format_ui_message(request_data)
                self.wfile.write(json.dumps(response_data).encode('utf-8'))
            else:
                # For UI->App messages, just acknowledge receipt
                logger.info("UI -> App: %s", request_data)
                self.wfile.write(json.dumps({"status": "received"}).encode('utf-8'))
                # Forward to app asynchronously after response
                threading.Thread(
                    target=self._forward_to_app,
                    args=(request_data,),
                    daemon=True
                ).start()

        except Exception as e:
            logger.error("Error in webhook handler: %s", e)
            self.send_error(500, "Internal Server Error")

    def do_POST(self):
        """Handle POST requests."""
        try:
            if self.path.startswith("/bot/webhook"):
                self._handle_webhook()
            else:
                self.send_error(404, "Not Found")
        except Exception as e:
            logger.error("Error: %s", e)
            self.send_error(500, "Internal Server Error")

    def do_GET(self):
        """Handle GET requests."""
        # Serve index.html for root path
        if self.path == "/" or self.path == "":
            self.path = "/index.html"
        return SimpleHTTPRequestHandler.do_GET(self)


def run_server(port=8001):
    """Run the mock server."""
    logger.info("Mock server running on port %d", port)

    server = socketserver.TCPServer(("", port), MockWhatsAppHandler)
    server.allow_reuse_address = True

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
