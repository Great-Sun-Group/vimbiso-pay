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

# Directory to store messages
MESSAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "messages")


class MockWhatsAppHandler(SimpleHTTPRequestHandler):
    """Handler for serving mock WhatsApp interface and handling webhooks."""

    def __init__(self, *args, directory=None, **kwargs):
        # Serve from current directory
        directory = os.path.dirname(os.path.abspath(__file__))
        logger.info("Serving files from directory: %s", directory)
        logger.info("Current working directory: %s", os.getcwd())
        logger.info("Directory contents: %s", os.listdir(directory))
        super().__init__(*args, directory=directory, **kwargs)

    def guess_type(self, path):
        """Guess the type of a file based on its path.

        Override to ensure proper MIME types for our files.
        """
        if path.endswith('.js'):
            return 'application/javascript'
        if path.endswith('.css'):
            return 'text/css'
        if path.endswith('.html'):
            return 'text/html'
        return super().guess_type(path)

    def _send_200(self, content=None):
        """Send 200 OK with optional JSON content"""
        try:
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self._send_cors_headers()
            self.end_headers()
            if content:
                self.wfile.write(json.dumps(content).encode('utf-8'))
                self.wfile.flush()
        except Exception as e:
            # Ignore all errors - client probably disconnected
            logger.debug("Connection closed: %s", e)

    def _save_message(self, message):
        """Save message to file for UI/CLI to read."""
        try:
            # Ensure message is JSON serializable
            if isinstance(message, str):
                try:
                    message = json.loads(message)
                except json.JSONDecodeError as e:
                    logger.error("Failed to parse message as JSON: %s", e)
                    return

            # Only save actual messages, not acknowledgments
            if isinstance(message, dict) and message.get("type") == "text" and message.get("text", {}).get("body"):
                # Create timestamp-based filename
                timestamp = int(time.time() * 1000)  # millisecond precision
                filename = f"{timestamp}.json"
                filepath = os.path.join(MESSAGES_DIR, filename)

                # Add filename to message data for timestamp tracking
                message_with_meta = {
                    **message,
                    "_filename": filename  # Add filename to message data
                }

                # Save message to file
                with open(filepath, 'w') as f:
                    json.dump(message_with_meta, f, indent=2)
                logger.info("Saved message to file: %s", filepath)
            else:
                logger.debug("Skipping non-message save: %s", message)

        except Exception as e:
            logger.error("Failed to save message: %s", e)

    def _get_messages(self, since=None):
        """Get messages from file storage, optionally after a timestamp."""
        messages = []
        try:
            # List all message files
            files = sorted(os.listdir(MESSAGES_DIR))
            for filename in files:
                if not filename.endswith('.json'):
                    continue

                # Get timestamp from filename
                timestamp = int(filename[:-5])  # Remove .json
                if since and timestamp <= since:
                    continue

                # Read message
                filepath = os.path.join(MESSAGES_DIR, filename)
                with open(filepath) as f:
                    message = json.load(f)
                    # Ensure filename is included in message data
                    if '_filename' not in message:
                        message['_filename'] = filename
                    messages.append(message)

        except Exception as e:
            logger.error("Error reading messages: %s", e)

        return messages

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
                    # Save outgoing message
                    outgoing_message = {
                        "type": "text",
                        "text": {"body": message["message"]},
                        "to": message["phone"]
                    }
                    self._save_message(outgoing_message)

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
                # Save message to file
                self._save_message(message)

        except Exception as e:
            # Just log and continue
            logger.error("Error handling webhook: %s", e)

    def log_request(self, code='-', size='-'):
        """Log an accepted request."""
        logger.info('"%s" %s %s', self.requestline, str(code), str(size))
        logger.info("Headers: %s", self.headers)

    def log_error(self, format, *args):
        """Log an error."""
        logger.error(format, *args)

    def log_message(self, format, *args):
        """Log a message."""
        logger.info(format, *args)

    def do_GET(self):
        """Handle GET requests."""
        logger.info("GET request to: %s", self.path)
        logger.info("Headers: %s", self.headers)

        if self.path == "/" or self.path == "" or self.path == "/index.html":
            # Get all messages
            messages = self._get_messages()

            # Read the index.html template
            with open(os.path.join(os.path.dirname(__file__), 'index.html'), 'r') as f:
                html_content = f.read()

            # Create message elements
            messages_html = ''
            for msg in messages:
                if msg.get('type') == 'text' and msg.get('text', {}).get('body'):
                    direction = 'incoming' if msg.get('from') else 'outgoing'
                    messages_html += f"""
                    <div class="message {direction}-message whatsapp-text">
                        {msg['text']['body']}
                    </div>
                    """

            # Replace placeholder with messages
            html_content = html_content.replace('{messages_placeholder}', messages_html)

            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(html_content.encode())
            return

        if self.path == "/clear-conversation":
            try:
                # Delete all files in messages directory
                for filename in os.listdir(MESSAGES_DIR):
                    if filename.endswith('.json'):
                        os.remove(os.path.join(MESSAGES_DIR, filename))
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode())
            except Exception as e:
                logger.error("Error clearing conversation: %s", e)
                self.send_response(500)
                self.end_headers()
            return

        if self.path.startswith("/messages"):
            # Get since parameter if provided
            since = None
            if "?" in self.path:
                query = self.path.split("?")[1]
                params = dict(param.split("=") for param in query.split("&"))
                since = int(params.get("since", 0))

            # Get messages
            messages = self._get_messages(since)

            # Send response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(messages).encode())
            return

        # Log file path resolution
        try:
            file_path = self.translate_path(self.path)
            logger.info("Resolved file path: %s", file_path)
            logger.info("File exists: %s", os.path.exists(file_path))
            if os.path.exists(file_path):
                logger.info("File contents: %s", os.listdir(os.path.dirname(file_path)))
                if os.path.isfile(file_path):
                    logger.info("File size: %d", os.path.getsize(file_path))
                    with open(file_path, 'rb') as f:
                        content = f.read()
                        logger.info("First 100 bytes: %s", content[:100])
                    logger.info("Content-Type: %s", self.guess_type(file_path))

                    # Send response with CORS headers
                    self.send_response(200)
                    self.send_header('Content-Type', self.guess_type(file_path))
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(content)
                    return
        except Exception as e:
            logger.error("Error checking file path: %s", e)

        # Fall back to default handler if file not found
        return SimpleHTTPRequestHandler.do_GET(self)

    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS preflight."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Mock-Testing')
        self.end_headers()

    def _send_cors_headers(self):
        """Send CORS headers."""
        # Get the origin from the request headers
        origin = self.headers.get('Origin', '*')
        # If it's a GitHub Codespaces domain, use that specific origin
        if '.app.github.dev' in origin:
            self.send_header('Access-Control-Allow-Origin', origin)
        else:
            self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, X-Mock-Testing')

    def do_POST(self):
        """Handle POST requests."""
        logger.info("POST request to: %s", self.path)
        logger.info("Headers: %s", self.headers)

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
