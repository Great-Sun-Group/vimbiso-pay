import json
import logging
import os
import requests
from http.server import SimpleHTTPRequestHandler
from urllib.parse import parse_qs, urlparse
import socketserver

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

# Target environments - using Docker service names
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
            if base_path == "/webhook":
                # Read the incoming request
                content_length = int(self.headers["Content-Length"])
                post_data = self.rfile.read(content_length)
                payload = json.loads(post_data.decode("utf-8"))

                # Log the incoming request
                message_data = payload["entry"][0]["changes"][0]["value"]
                message = message_data["messages"][0]
                contact = message_data["contacts"][0]
                message_type = message["type"]
                if message_type == "text":
                    text = message["text"]["body"]
                elif message_type == "button":
                    text = message["button"]["payload"]
                elif message_type == "interactive":
                    text = message["interactive"]["button_reply"]["id"]
                else:
                    text = "Unsupported message type"

                print(f"\nReceived message: {text}")
                print(f"From: {contact['profile']['name']}")
                print(f"Phone: {contact['wa_id']}")
                print(f"Type: {message_type}")
                print(f"Target: {target}\n")

                try:
                    # Forward request to selected target
                    print(f"\nForwarding request to {target} server...")
                    print(f"Target URL: {TARGETS[target]}")
                    print(f"Request Headers: {dict(self.headers)}")
                    print(f"Request Payload: {json.dumps(payload, indent=2)}")

                    # Add mock testing header and content type
                    headers = {
                        "Content-Type": "application/json",
                        "X-Mock-Testing": "true",
                        "Accept": "application/json"
                    }

                    target_url = TARGETS.get(target, TARGETS['local'])

                    # Make request with detailed error handling
                    try:
                        print("\nSending request...")
                        chatbot_response = requests.post(
                            target_url,
                            json=payload,
                            headers=headers,
                            timeout=30
                        )
                        print(f"\nResponse Status Code: {chatbot_response.status_code}")
                        print(f"Response Headers: {dict(chatbot_response.headers)}")
                        print(f"Response Content: {chatbot_response.text}")

                        chatbot_response.raise_for_status()

                        # Forward the response
                        self.send_response(chatbot_response.status_code)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(chatbot_response.content)
                        return

                    except requests.exceptions.Timeout:
                        print("\nError: Request timed out")
                        self.send_error(504, "Gateway Timeout")
                        return
                    except requests.exceptions.ConnectionError as e:
                        print(f"\nError: Connection failed - {str(e)}")
                        print("Make sure the Django server is running and accessible")
                        self.send_error(502, "Bad Gateway", f"Connection to {target} server failed")
                        return
                    except requests.exceptions.RequestException as e:
                        print(f"\nError: Request failed - {str(e)}")
                        if hasattr(e, 'response'):
                            print(f"Response status: {e.response.status_code}")
                            print(f"Response content: {e.response.text}")
                        self.send_error(500, "Internal Server Error", str(e))
                        return

                except Exception as e:
                    print(f"\nUnexpected error forwarding request: {str(e)}")
                    self.send_error(500, "Internal Server Error", str(e))
                    return

            return super().do_POST()

        except Exception as e:
            print(f"\nGlobal error handler: {str(e)}")
            self.send_error(500, "Internal Server Error", str(e))
            return

    def do_GET(self):
        # Serve the index.html file
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            with open(os.path.join(os.path.dirname(__file__), "index.html"), "rb") as f:
                self.wfile.write(f.read())
            return
        return super().do_GET()


def run_server(port=8001):
    print(f"\nStarting mock WhatsApp server on port {port}")
    print("\nAvailable targets:")
    for name, url in TARGETS.items():
        print(f"- {name}: {url}")
    print("\nOpen http://localhost:8001 in your browser")

    server_address = ("", port)
    httpd = ReuseAddressHTTPServer(server_address, MockWhatsAppHandler)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    run_server()
