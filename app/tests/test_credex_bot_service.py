import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import django

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from bot.credex_bot_service import CredexBotService
from bot.constants import CachedUser, CachedUserState

class MockCachedUserState(CachedUserState):
    def __init__(self, user):
        self.user = user
        self.direction = "OUT"
        self.stage = "WELCOME"
        self.option = None

    def get_state(self, user):
        return {"direction": self.direction, "stage": self.stage, "option": self.option}

    def set_state(self, direction=None, stage=None, option=None):
        if direction:
            self.direction = direction
        if stage:
            self.stage = stage
        if option:
            self.option = option

    def update_state(self, state, stage, update_from, option):
        self.stage = stage
        self.option = option

    def reset_state(self):
        self.direction = "OUT"
        self.stage = "WELCOME"
        self.option = None

class TestCredexBotService(unittest.TestCase):
    def setUp(self):
        self.phone_number = "+1234567890"
        self.user = CachedUser(self.phone_number)
        self.user.state = MockCachedUserState(self.user)

    def test_init_with_valid_user(self):
        payload = {
            "message": "Hi",
            "from": self.phone_number,
        }
        service = CredexBotService(payload=payload, user=self.user)
        self.assertIsNotNone(service.response)

    def test_init_with_invalid_user(self):
        payload = {
            "message": "Hi",
            "from": self.phone_number,
        }
        with self.assertRaises(ValueError):
            CredexBotService(payload=payload, user=None)

    @patch('bot.credex_bot_service.ActionHandler')
    def test_handle_greeting(self, mock_action_handler):
        payload = {
            "message": "Hello",
            "from": self.phone_number,
        }
        mock_action_handler_instance = MagicMock()
        mock_action_handler.return_value = mock_action_handler_instance
        mock_action_handler_instance.handle_greeting.return_value = "Welcome message"

        service = CredexBotService(payload=payload, user=self.user)
        self.assertEqual(service.response, "Welcome message")
        mock_action_handler_instance.handle_greeting.assert_called_once()

    @patch('bot.credex_bot_service.OfferCredexHandler')
    def test_handle_offer_credex(self, mock_offer_credex_handler):
        payload = {
            "message": "offer => credex",
            "from": self.phone_number,
        }
        mock_offer_credex_instance = MagicMock()
        mock_offer_credex_handler.return_value = mock_offer_credex_instance
        mock_offer_credex_instance.handle_action_offer_credex.return_value = "Offer Credex response"

        service = CredexBotService(payload=payload, user=self.user)
        self.assertEqual(service.response, "Offer Credex response")
        mock_offer_credex_instance.handle_action_offer_credex.assert_called_once()

    @patch('bot.credex_bot_service.ActionHandler')
    def test_handle_default_action(self, mock_action_handler):
        payload = {
            "message": "Unknown command",
            "from": self.phone_number,
        }
        mock_action_handler_instance = MagicMock()
        mock_action_handler.return_value = mock_action_handler_instance
        mock_action_handler_instance.handle_default_action.return_value = "Default response"

        service = CredexBotService(payload=payload, user=self.user)
        self.assertEqual(service.response, "Default response")
        mock_action_handler_instance.handle_default_action.assert_called_once()

    @patch('bot.credex_bot_service.ActionHandler')
    def test_handle_error(self, mock_action_handler):
        payload = {
            "message": "Trigger error",
            "from": self.phone_number,
        }
        mock_action_handler_instance = MagicMock()
        mock_action_handler.return_value = mock_action_handler_instance
        mock_action_handler_instance.handle_greeting.side_effect = Exception("Test error")

        with self.assertLogs(level='ERROR') as log:
            service = CredexBotService(payload=payload, user=self.user)
            self.assertIn("INVALID_ACTION", service.response)
            self.assertIn("Error in CredexBotService: Test error", log.output[0])

    @patch('bot.credex_bot_service.ActionHandler')
    def test_state_update(self, mock_action_handler):
        payload = {
            "message": "handle_action_test",
            "from": self.phone_number,
        }
        mock_action_handler_instance = MagicMock()
        mock_action_handler.return_value = mock_action_handler_instance
        mock_action_handler_instance.handle_action_test.return_value = "Test action response"

        service = CredexBotService(payload=payload, user=self.user)
        self.assertEqual(service.response, "Test action response")
        self.assertEqual(self.user.state.stage, "handle_action_test")
        self.assertEqual(self.user.state.option, "handle_action_test")

if __name__ == '__main__':
    unittest.main()