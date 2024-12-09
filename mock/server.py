import django
import json
import logging
import os
import sys
import time
import traceback
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

# Add the parent directory to sys.path and initialize Django
sys.path.append(str(Path(__file__).resolve().parent.parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    print("\nError: watchdog package is required for hot reload.")
    print("Please install it with: pip install watchdog")
    print(
        "Or install all development requirements with: "
        "pip install -r requirements/dev.txt\n"
    )
    sys.exit(1)

from core.config.constants import CachedUser  # noqa: E402
from core.message_handling.credex_bot_service import CredexBotService  # noqa: E402

logger = logging.getLogger(__name__)

# Global server instance for reloading
httpd = None


class MockWhatsAppService:
    """Mock version of CredexWhatsappService for testing."""
    def __init__(self, payload, phone_number_id=None):
        self.phone_number_id = phone_number_id
        self.payload = payload

    def send_message(self):
        """Simulate sending a WhatsApp message."""
        print(f"\nMock WhatsApp would send: {json.dumps(self.payload, indent=2)}")
        return {
            "messaging_product": "whatsapp",
            "contacts": [{
                "input": self.payload.get("to"),
                "wa_id": self.payload.get("to")
            }],
            "messages": [{"id": "mock_message_id"}]
        }

    def notify(self):
        """Simulate sending a notification."""
        return self.send_message()


class MockWhatsAppHandler(SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/webhook':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            payload = json.loads(post_data.decode('utf-8'))

            # Extract the message from the WhatsApp-style payload
            message_data = payload['entry'][0]['changes'][0]['value']
            message = message_data['messages'][0]
            contact = message_data['contacts'][0]

            # Get the message text based on type
            message_type = message['type']
            if message_type == 'text':
                text = message['text']['body']
            elif message_type == 'button':
                text = message['button']['payload']
            elif message_type == 'interactive':
                text = message['interactive']['button_reply']['id']
            else:
                text = 'Unsupported message type'

            print(f"\nReceived message: {text}")
            print(f"From: {contact['profile']['name']}")
            print(f"Phone: {contact['wa_id']}")
            print(f"Type: {message_type}\n")

            # Format the message for the bot service
            formatted_message = {
                "to": message_data["metadata"]["display_phone_number"],
                "phone_number_id": message_data["metadata"]["phone_number_id"],
                "from": contact["wa_id"],
                "username": contact["profile"]["name"],
                "type": message_type,
                "message": text
            }

            try:
                # Process message through bot service
                user = CachedUser(formatted_message.get("from"))
                service = CredexBotService(payload=formatted_message, user=user)
                bot_response = service.response
                print(f"Bot response: {bot_response}")

                # Send response through mock WhatsApp service
                whatsapp_service = MockWhatsAppService(
                    payload=bot_response,
                    phone_number_id=message_data["metadata"]["phone_number_id"]
                )
                whatsapp_response = whatsapp_service.send_message()
                print(f"Mock WhatsApp response: {whatsapp_response}")

                # Return both responses to the client
                response_data = {
                    "bot_response": bot_response,
                    "whatsapp_response": whatsapp_response
                }

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response_data).encode())
                return

            except Exception as e:
                print(f"Error processing message: {str(e)}")
                print("Traceback:")
                traceback.print_exc()
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }).encode())
                return

        return super().do_POST()

    def do_GET(self):
        # Serve the index.html file
        if self.path == '/':
            self.path = '/index.html'
        return SimpleHTTPRequestHandler.do_GET(self)


class FileChangeHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.src_path.endswith('.py'):
            print(f"\nDetected change in {event.src_path}")
            print("Restarting server...\n")
            if httpd:
                httpd.shutdown()


def run_server(port=8001):
    global httpd

    # Change to the directory containing index.html
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Set up file watching
    event_handler = FileChangeHandler()
    observer = Observer()
    observer.schedule(
        event_handler,
        path=str(Path(__file__).resolve().parent),
        recursive=True
    )
    observer.start()

    try:
        while True:
            print(f'Starting mock WhatsApp server on port {port}...')
            print(f'Open http://localhost:{port} in your browser')
            print('Hot reload is active - server will restart on file changes')

            server_address = ('', port)
            httpd = HTTPServer(server_address, MockWhatsAppHandler)

            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Server error: {e}")
                print("Restarting in 2 seconds...")
                time.sleep(2)
                continue

    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        observer.stop()
        observer.join()
        if httpd:
            httpd.server_close()


if __name__ == '__main__':
    run_server()
