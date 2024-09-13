import sys
import os
import django
from decouple import config
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Set environment variables
try:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
    os.environ['CREDEX'] = config('CREDEX', default='https://cautious-space-sniffle-wpxj5grwjq2x5j-5000.app.github.dev')
    os.environ['WHATSAPP_PHONE_NUMBER'] = config('WHATSAPP_PHONE_NUMBER', default='+263778177125')
    os.environ['WHATSAPP_PHONE_NUMBER_ID'] = config('WHATSAPP_PHONE_NUMBER_ID', default='1234567890')
    os.environ['CREDEX_API_CREDENTIALS'] = config('X_GITHUB_TOKEN', default='ghu_tlUxSrr4vOmYdBgdOzzedWBk9Aru060tAdXH')
    os.environ['WHATSAPP_BOT_API_KEY'] = config('AUTHENTICATION', default='Bearer garejhg94_Sdrh456qRhSfAg4286t')
except Exception as e:
    logger.error(f"Error setting environment variables: {str(e)}")
    sys.exit(1)

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up Django
try:
    django.setup()
except Exception as e:
    logger.error(f"Error setting up Django: {str(e)}")
    sys.exit(1)

try:
    from bot.credex_bot_service import CredexBotService
except ImportError as e:
    logger.error(f"Error importing required modules: {str(e)}")
    sys.exit(1)

# Define constants
REGISTER = "You're not registered. Would you like to register? {message}"
INVALID_ACTION = "I'm sorry, I didn't understand that. Can you please try again?"

# Simple in-memory cache for simulation
class SimpleCache:
    def __init__(self):
        self.cache = {}

    def get(self, key, default=None):
        return self.cache.get(key, default)

    def set(self, key, value, timeout=None):
        self.cache[key] = value

# Mock user and state classes
class MockUser:
    def __init__(self, phone_number):
        self.mobile_number = phone_number
        self.state = MockUserState(self)

class MockUserState:
    def __init__(self, user):
        self.user = user
        self.cache = SimpleCache()
        self.direction = self.cache.get(f"{self.user.mobile_number}_direction", "OUT")
        self.stage = self.cache.get(f"{self.user.mobile_number}_stage", "WELCOME")
        self.option = self.cache.get(f"{self.user.mobile_number}_option")

    def get_state(self, user):
        return {"direction": self.direction, "stage": self.stage, "option": self.option}

    def set_state(self, direction=None, stage=None, option=None):
        if direction:
            self.direction = direction
            self.cache.set(f"{self.user.mobile_number}_direction", direction)
        if stage:
            self.stage = stage
            self.cache.set(f"{self.user.mobile_number}_stage", stage)
        if option:
            self.option = option
            self.cache.set(f"{self.user.mobile_number}_option", option)

    def update_state(self, state, stage, update_from, option):
        self.set_state(stage=stage, option=option)

    def reset_state(self):
        self.set_state(direction="OUT", stage="WELCOME", option=None)

def wrap_text(text, extra_rows=None, include_menu=True):
    # For simulation, we'll just return the text as is
    return text

class WhatsAppSimulator:
    def __init__(self):
        self.phone_number = os.environ['WHATSAPP_PHONE_NUMBER']
        self.user = MockUser(self.phone_number)

    def send_message(self, message_body):
        formatted_message = {
            "to": os.environ['WHATSAPP_PHONE_NUMBER'],
            "from": self.phone_number,
            "phone_number_id": os.environ['WHATSAPP_PHONE_NUMBER_ID'],
            "username": f"Test User {self.phone_number}",
            "type": "text",
            "message": message_body,
        }

        try:
            logger.info(f"Sending message: {message_body}")
            service = CredexBotService(payload=formatted_message, user=self.user)
            
            print(f"\nYou: {message_body}")
            
            if hasattr(service, 'response'):
                response = service.response
                if isinstance(response, dict):
                    if 'text' in response:
                        print(f"Bot: {response['text']['body']}")
                    elif 'interactive' in response:
                        print(f"Bot: {response['interactive']['body']['text']}")
                        if 'action' in response['interactive']:
                            if 'button' in response['interactive']['action']:
                                print(f"Options: {response['interactive']['action']['button']}")
                            if 'sections' in response['interactive']['action']:
                                for section in response['interactive']['action']['sections']:
                                    print(f"Section: {section['title']}")
                                    for row in section['rows']:
                                        print(f"  {row['id']}: {row['title']}")
                else:
                    print(f"Bot: {response}")
            else:
                print("Bot: No response")
        except Exception as e:
            print(f"Error: {str(e)}")
            logger.error(f"Error in send_message: {str(e)}", exc_info=True)
        
        print("\n" + "-" * 50)

    def run(self):
        print("WhatsApp Simulator Started. Type 'exit' to quit.")
        print("Enter your messages as if you were chatting on WhatsApp.")
        print("-" * 50)

        while True:
            user_input = input("\nYou: ")
            if user_input.lower() == 'exit':
                print("WhatsApp Simulator Ended")
                break
            
            self.send_message(user_input)

if __name__ == "__main__":
    try:
        simulator = WhatsAppSimulator()
        simulator.run()
    except Exception as e:
        logger.critical(f"Critical error in WhatsAppSimulator: {str(e)}", exc_info=True)
        print(f"A critical error occurred. Please check the logs for details.")
        sys.exit(1)