import sys
import logging
from pathlib import Path
import os

# Add the necessary directories to sys.path
current_dir = Path(__file__).resolve().parent
core_dir = current_dir.parent.parent
app_dir = core_dir.parent
project_dir = app_dir.parent
sys.path.extend([str(core_dir), str(app_dir), str(project_dir)])

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Explicitly set variables for development
MYCREDEX_APP_URL = 'https://cautious-space-sniffle-wpxj5grwjq2x5j-5000.app.github.dev/'
X_GITHUB_TOKEN = None  # Set to None by default, can be overridden if needed
JWT_AUTH = 'default_jwt_auth'

# Determine the environment
ENV = os.getenv('ENV', 'dev')  # Default to 'dev' if not set

# Set environment variables
os.environ['MYCREDEX_APP_URL'] = MYCREDEX_APP_URL
os.environ['JWT_AUTH'] = JWT_AUTH
if X_GITHUB_TOKEN:
    os.environ['X_GITHUB_TOKEN'] = X_GITHUB_TOKEN

def setup_django():
    logging.debug("Starting Django setup process")
    
    import os
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    
    try:
        import django
        from django.conf import settings
        from django.apps import apps
        
        logging.debug("Imported Django modules successfully")
        
        if not settings.configured:
            logging.debug("Django settings not configured. Configuring now...")
            settings.configure(
                DEBUG=True,
                INSTALLED_APPS=[
                    'django.contrib.auth',
                    'django.contrib.contenttypes',
                    'django.contrib.sessions',
                    'core',
                ],
                DATABASES={
                    'default': {
                        'ENGINE': 'django.db.backends.sqlite3',
                        'NAME': ':memory:',
                    }
                },
                DJANGO_SECRET='dummy-secret-key-for-test',
            )
            logging.debug("Django settings configured successfully")
        
        logging.debug("Setting up Django")
        django.setup()
        logging.debug("Django setup complete")
        
        # Wait for apps to be fully loaded
        apps.populate(settings.INSTALLED_APPS)
        
        # Verify that Django is properly set up
        if not apps.ready:
            logging.error("Django apps are not ready. There might be an issue with the configuration.")
            sys.exit(1)
        logging.debug("Django apps are ready")
        
    except Exception as e:
        logging.error(f"An error occurred during Django setup: {str(e)}")
        logging.exception("Detailed traceback:")
        sys.exit(1)

# Call setup_django before any other imports
setup_django()

# Now we can safely import Django-related modules
from django.core.cache import cache
logging.debug("Successfully imported Django cache module")

# Import necessary components
from core.config.constants import CachedUser
from core.message_handling.credex_bot_service import CredexBotService
from core.utils.utils import wrap_text

class VimbisoPay_Terminal:
    def __init__(self):
        self.user = CachedUser(mobile_number="1234567890")  # Create a user using CachedUser
        self.user_phone_number = "1234567890"  # Simulated user phone number

    def send_message(self, message_text):
        """
        Send a message to the bot and return the response.
        """
        try:
            # Create the payload for CredexBotService
            payload = {
                "message": message_text,
                "from": self.user_phone_number,
                "type": "text"
            }
            
            # Create a new CredexBotService instance for each message
            bot_service = CredexBotService(payload, self.user)
            
            # The response is already stored in bot_service.response
            return bot_service.response
        except Exception as e:
            logging.error(f"Error sending message: {e}")
            return None

    def display_message(self, message):
        """
        Display different types of messages (text, buttons, lists).
        """
        if isinstance(message, str):
            print(f"Bot: {message}")
        elif isinstance(message, dict):
            if message.get('text'):
                print(f"Bot: {message['text']['body']}")
            elif message.get('interactive'):
                interactive = message['interactive']
                if interactive['type'] == 'button':
                    print(f"Bot: {interactive['body']['text']}")
                    for button in interactive['action']['buttons']:
                        print(f"- {button['reply']['title']}")
                elif interactive['type'] == 'list':
                    print(f"Bot: {interactive['body']['text']}")
                    for section in interactive['action']['sections']:
                        print(f"Section: {section['title']}")
                        for row in section['rows']:
                            print(f"- {row['title']}")

    def get_user_input(self, message):
        """
        Get user input based on the message type.
        """
        if isinstance(message, dict) and message.get('interactive'):
            interactive = message['interactive']
            if interactive['type'] == 'button':
                options = [button['reply']['title'] for button in interactive['action']['buttons']]
                return self.display_form_options(options)
            elif interactive['type'] == 'list':
                options = [row['title'] for section in interactive['action']['sections'] for row in section['rows']]
                return self.display_form_options(options)
        return input("You: ")

    def display_form_options(self, options):
        """
        Display form options and get user selection.
        """
        for i, option in enumerate(options, 1):
            print(f"{i}. {option}")
        while True:
            try:
                choice = int(input("Enter your choice (number): "))
                if 1 <= choice <= len(options):
                    return options[choice - 1]
                else:
                    print("Invalid choice. Please try again.")
            except ValueError:
                print("Please enter a valid number.")

    def run(self):
        """
        Run the VimbisoPay Terminal simulator.
        """
        print(f"Welcome to VimbisoPay Terminal Simulator (Environment: {ENV})")
        print("Type 'exit' to quit the simulator")
        
        # Start the conversation with initial messages
        initial_messages = [
            "Hello",
            "I want to use Credex"
        ]
        
        for msg in initial_messages:
            print(f"You: {msg}")
            response = self.send_message(msg)
            if response:
                self.display_message(response)
            else:
                print("No response from the bot. Please try again.")
        
        while True:
            user_input = input("You: ")
            if user_input.lower() == 'exit':
                break
            
            response = self.send_message(user_input)
            if response:
                self.display_message(response)
            else:
                print("No response from the bot. Please try again.")

if __name__ == "__main__":
    simulator = VimbisoPay_Terminal()
    simulator.run()