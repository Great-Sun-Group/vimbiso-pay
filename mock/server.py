import json
import logging
import os
import socketserver
from http.server import SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

import requests

from whatsapp_utils import extract_message_text

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Target environments - using app service name for Docker networking
TARGETS = {
    'local': 'http://app:8000/bot/webhook',  # Using Docker service name
    'staging': 'https://stage.whatsapp.vimbisopay.africa/bot/webhook'
}


class ReuseAddressHTTPServer(socketserver.TCPServer):
    allow_reuse_address = True


class MockWhatsAppHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        try:
            # Parse URL to get target from query params
            parsed_url = urlparse(self.path)
            params = parse_qs(parsed_url.query)
            target = params.get('target', ['local'])[0]

            base_path = parsed_url.path
            if base_path == "/bot/webhook":  # Updated to match Django endpoint
                # Read the incoming request
                content_length = int(self.headers["Content-Length"])
                post_data = self.rfile.read(content_length)
                payload = json.loads(post_data.decode("utf-8"))

                # Log the incoming request
                message_data = payload["entry"][0]["changes"][0]["value"]
                message = message_data["messages"][0]
                contact = message_data["contacts"][0]

                # Extract message text using shared utility
                text = extract_message_text(message)

                logger.info(f"\nReceived message: {text}")
                logger.info(f"From: {contact['profile']['name']}")
                logger.info(f"Phone: {contact['wa_id']}")
                logger.info(f"Type: {message['type']}")
                logger.info(f"Target: {target}\n")

                try:
                    # Forward request to selected target
                    logger.info(f"\nForwarding request to {target} server...")
                    logger.info(f"Target URL: {TARGETS[target]}")
                    logger.info(f"Request Headers: {dict(self.headers)}")
                    logger.info(f"Request Payload: {json.dumps(payload, indent=2)}")

                    # Add mock testing header and content type
                    headers = {
                        "Content-Type": "application/json",
                        "X-Mock-Testing": "true",
                        "Accept": "application/json"
                    }

                    target_url = TARGETS.get(target, TARGETS['local'])

                    # Make request with detailed error handling
                    try:
                        logger.info("\nSending request...")
                        # Log exact request being sent
                        logger.info(f"Final request URL: {target_url}")
                        logger.info(f"Final request headers: {headers}")
                        logger.info(f"Final request payload: {json.dumps(payload, indent=2)}")

                        chatbot_response = requests.post(
                            target_url,
                            json=payload,
                            headers=headers,
                            timeout=30
                        )
                        logger.info(f"\nResponse Status Code: {chatbot_response.status_code}")
                        logger.info(f"Response Headers: {dict(chatbot_response.headers)}")
                        logger.info(f"Response Content: {chatbot_response.text}")

                        chatbot_response.raise_for_status()

                        # Forward the response back to the client
                        self.send_response(chatbot_response.status_code)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()

                        # Parse the response and send it back
                        response_data = json.loads(chatbot_response.text)
                        if isinstance(response_data, dict) and 'response' in response_data:
                            # If response is already wrapped, send it as is
                            self.wfile.write(chatbot_response.text.encode('utf-8'))
                        else:
                            # If response is not wrapped, wrap it
                            wrapped_response = {"response": response_data}
                            self.wfile.write(json.dumps(wrapped_response).encode('utf-8'))
                        return

                    except requests.exceptions.Timeout:
                        logger.error("\nError: Request timed out")
                        self.send_error(504, "Gateway Timeout")
                        return
                    except requests.exceptions.ConnectionError as e:
                        logger.error(f"\nError: Connection failed - {str(e)}")
                        logger.error("Make sure the Django server is running and accessible")
                        self.send_error(502, "Bad Gateway", f"Connection to {target} server failed")
                        return
                    except requests.exceptions.RequestException as e:
                        logger.error(f"\nError: Request failed - {str(e)}")
                        if hasattr(e, 'response'):
                            logger.error(f"Response status: {e.response.status_code}")
                            logger.error(f"Response content: {e.response.text}")
                        self.send_error(500, "Internal Server Error", str(e))
                        return

                except Exception as e:
                    logger.error(f"\nUnexpected error forwarding request: {str(e)}")
                    self.send_error(500, "Internal Server Error", str(e))
                    return

            # Serve index.html for root path
            elif self.path == "/" or self.path == "/index.html":
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                with open(os.path.join(os.path.dirname(__file__), "index.html"), "rb") as f:
                    self.wfile.write(f.read())
                return
            else:
                # Handle unknown paths with 404
                self.send_error(404, "Not Found", f"Path {base_path} not found")
                return

        except Exception as e:
            logger.error(f"\nGlobal error handler: {str(e)}")
            self.send_error(500, "Internal Server Error", str(e))
            return

    def do_GET(self):
        # Serve index.html for root path
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            with open(os.path.join(os.path.dirname(__file__), "index.html"), "rb") as f:
                self.wfile.write(f.read())
            return
        else:
            # Handle unknown paths with 404
            self.send_error(404, "Not Found", f"Path {self.path} not found")
            return


def run_server(port=8001):
    logger.info(f"\nStarting mock WhatsApp server on port {port}")
    logger.info("\nAvailable targets:")
    for name, url in TARGETS.items():
        logger.info(f"- {name}: {url}")
    logger.info("\nOpen http://localhost:8001 in your browser")

    server_address = ("", port)
    httpd = ReuseAddressHTTPServer(server_address, MockWhatsAppHandler)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    run_server()
