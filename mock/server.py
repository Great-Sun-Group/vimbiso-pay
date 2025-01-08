"""Mock WhatsApp server implementation."""
import json
import logging
import os
import socketserver
import time
from http.server import SimpleHTTPRequestHandler

import requests

# Configure logging - show all messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Silence connection logs
logging.getLogger("urllib3").setLevel(logging.WARNING)

# The actual app endpoint we're testing
APP_ENDPOINT = 'http://app:8000/bot/webhook'

# Connected SSE clients
sse_clients = set()


class MockWhatsAppHandler(SimpleHTTPRequestHandler):
    """Handler for serving mock WhatsApp interface and handling webhooks."""

    def __init__(self, *args, directory=None, **kwargs):
        # Set directory before parent initialization
        if directory is None:
            directory = '/app/mock' if os.path.exists('/app/mock') else os.path.dirname(os.path.abspath(__file__))
        super().__init__(*args, directory=directory, **kwargs)

    def _send_200(self, content=None):
        """Send 200 OK with optional JSON content"""
        try:
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            if content:
                self.wfile.write(json.dumps(content).encode('utf-8'))
                self.wfile.flush()
        except Exception as e:
            # Ignore all errors - client probably disconnected
            logger.debug("Connection closed: %s", e)

    def _broadcast_to_ui(self, message):
        """Broadcast message to all connected SSE clients."""
        try:
            # Ensure message is JSON serializable
            if isinstance(message, str):
                try:
                    message = json.loads(message)
                except json.JSONDecodeError as e:
                    logger.error("Failed to parse message as JSON: %s", e)
                    return

            logger.info("Broadcasting to %d clients", len(sse_clients))

            # Only broadcast actual messages, not acknowledgments
            if isinstance(message, dict) and message.get("type") == "text" and message.get("text", {}).get("body"):
                # Send to all connected clients
                for client in list(sse_clients):
                    try:
                        logger.info("Sending to client: %s", id(client))
                        client.wfile.write(f"data: {json.dumps(message)}\n\n".encode('utf-8'))
                        client.wfile.flush()
                        logger.info("Successfully sent to client: %s", id(client))
                    except Exception as e:
                        # Remove failed client
                        logger.error("Failed to send to client %s: %s", id(client), e)
                        sse_clients.remove(client)
            else:
                logger.debug("Skipping non-message broadcast: %s", message)

        except Exception as e:
            logger.error("Failed to broadcast message: %s", e)

    def _forward_to_app(self, message):
        """Transform and forward message to app."""
        try:
            # Transform simple message to WhatsApp webhook format
            webhook_message = {
                "object": "whatsapp_business_account",
                "entry": [{
                    "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                    "changes": [{
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "263787274250",
                                "phone_number_id": "390447444143042"
                            },
                            "contacts": [{
                                "profile": {
                                    "name": "Test User"
                                },
                                "wa_id": message.get("phone")
                            }],
                            "messages": [{
                                "from": message.get("phone"),
                                "id": f"wamid.{hex(int.from_bytes(os.urandom(16), 'big'))[2:]}",
                                "timestamp": str(int(time.time())),
                                "type": message.get("type", "text"),
                                "text": {
                                    "body": message.get("message")
                                }
                            }]
                        },
                        "field": "messages"
                    }]
                }]
            }

            # Add mock testing headers
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Mock-Testing": "true"
            }

            # Log what we're forwarding
            logger.info("Forwarding to app: %s", json.dumps(webhook_message))

            # Send request and handle response
            response = requests.post(
                APP_ENDPOINT,
                json=webhook_message,
                headers=headers,
                timeout=10
            )

            # Log response details
            logger.info("App response status: %d", response.status_code)
            if response.status_code != 200:
                logger.error("App error response: %s", response.text)
                return

        except Exception as e:
            # Log but continue
            logger.error("Failed to forward to app: %s", e)

    def _handle_webhook(self):
        """Handle webhook POST request."""
        try:
            # Read and process request
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length > 0:
                body = self.rfile.read(content_length)
                # Log raw payload
                raw_payload = body.decode('utf-8')
                logger.info("Raw webhook payload: %s", raw_payload)
                message = json.loads(raw_payload)

                # Handle UI->Server messages
                if "type" in message and "message" in message and "phone" in message:
                    logger.info("UI -> Server: %s", message)
                    # Acknowledge receipt immediately and close connection
                    self._send_200({"success": True})
                    # Start forwarding to app in a separate thread
                    import threading
                    threading.Thread(target=self._forward_to_app, args=(message,)).start()
                    return

                # Handle App->Server messages
                logger.info("App -> Server: %s", message)
                # Acknowledge receipt to app
                self._send_200({
                    "messaging_product": "whatsapp",
                    "contacts": [{"input": message.get("to"), "wa_id": message.get("to")}],
                    "messages": [{"id": f"wamid.{hex(int.from_bytes(os.urandom(16), 'big'))[2:]}"}]
                })
                # Broadcast to UI via SSE
                self._broadcast_to_ui(message)

        except Exception as e:
            # Just log and continue
            logger.error("Error handling webhook: %s", e)

    def _handle_sse(self):
        """Handle SSE connection."""
        try:
            logger.info("New SSE connection from %s", self.client_address)
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.end_headers()

            # Add client
            sse_clients.add(self)
            logger.info("Added SSE client %s (total: %d)", id(self), len(sse_clients))

            # Keep connection alive with ping events
            while True:
                try:
                    self.wfile.write(b': ping\n\n')
                    self.wfile.flush()
                    logger.debug("Sent ping to client %s", id(self))
                    time.sleep(30)  # Send ping every 30 seconds
                except Exception as e:
                    logger.error("Error sending ping to client %s: %s", id(self), e)
                    break

        except Exception as e:
            logger.error("SSE client %s disconnected: %s", id(self), e)
        finally:
            if self in sse_clients:
                sse_clients.remove(self)
                logger.info("Removed SSE client %s (remaining: %d)", id(self), len(sse_clients))

    def do_GET(self):
        """Handle GET requests."""
        logger.info("GET request to: %s", self.path)
        if self.path == "/events":
            logger.info("Handling SSE connection request")
            return self._handle_sse()
        if self.path == "/" or self.path == "":
            self.path = "/index.html"
        return SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        """Handle POST requests."""
        if self.path.startswith("/bot/webhook"):
            self._handle_webhook()
        else:
            try:
                self.send_response(404)
                self.end_headers()
            except Exception as e:
                logger.debug("Error sending 404: %s", e)


def run_server(port=8001):
    """Run the mock server."""
    logger.info("Mock server running on port %d", port)
    logger.info("Mock WhatsApp interface available at: http://localhost:%d", port)

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
