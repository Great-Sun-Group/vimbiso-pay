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

                # Extract and validate message data
                message_type = message.get("type")
                interactive_type = message.get("interactive", {}).get("type") if message_type == "interactive" else None

                # Extract message text using shared utility
                text = extract_message_text(message)

                # Enhanced logging for form submissions
                if message_type == "interactive" and interactive_type == "nfm_reply":
                    logger.info("\n=== Form Submission Details ===")
                    logger.info(f"Form Data: {json.dumps(text, indent=2)}")
                    logger.info(f"Interactive Type: {interactive_type}")

                    # Log form structure
                    nfm_reply = message.get("interactive", {}).get("nfm_reply", {})
                    submitted_form = nfm_reply.get("submitted_form_data", {})
                    form_data = submitted_form.get("form_data", {})
                    logger.info(f"Form Name: {form_data.get('name')}")
                    logger.info("Form Fields:")
                    for field in form_data.get("response_fields", []):
                        logger.info(f"  - {field.get('field_id')}: {field.get('value')} (Type: {field.get('type')})")
                else:
                    logger.info(f"\nReceived message: {text}")
                    logger.info(f"Message Type: {message_type}")
                    if interactive_type:
                        logger.info(f"Interactive Type: {interactive_type}")

                logger.info(f"From: {contact['profile']['name']}")
                logger.info(f"Phone: {contact['wa_id']}")
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

                        # Parse and validate the response
                        try:
                            response_data = json.loads(chatbot_response.text)
                            # Validate response structure
                            if not isinstance(response_data, dict):
                                logger.error("Invalid response format - not a dictionary")
                                response_data = {"error": "Invalid response format"}

                            # Ensure response is properly wrapped
                            if 'response' not in response_data:
                                response_data = {"response": response_data}

                            # Send response
                            self.wfile.write(json.dumps(response_data).encode('utf-8'))
                            return

                        except json.JSONDecodeError as e:
                            logger.error(f"Error parsing response JSON: {str(e)}")
                            self.send_error(500, "Internal Server Error", "Invalid JSON response")
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
