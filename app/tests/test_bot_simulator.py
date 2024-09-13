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

from test_scripts.simulate_user import BotSimulator, MockCachedUserState
from bot.constants import CachedUser

class TestBotSimulator(unittest.TestCase):
    def setUp(self):
        self.simulator = BotSimulator()

    def test_init(self):
        self.assertEqual(self.simulator.phone_number, "+1234567890")
        self.assertIsInstance(self.simulator.user, CachedUser)
        self.assertIsInstance(self.simulator.user.state, MockCachedUserState)

    @patch('test_scripts.simulate_user.CredexBotService')
    def test_send_message_text(self, mock_credex_bot_service):
        mock_service_instance = MagicMock()
        mock_credex_bot_service.return_value = mock_service_instance
        mock_service_instance.response = {"text": {"body": "Test response"}}

        with patch('builtins.print') as mock_print:
            self.simulator.send_message("Hello", "text")

        mock_credex_bot_service.assert_called_once()
        mock_print.assert_any_call("User: Hello")
        mock_print.assert_any_call("Bot: Test response")

    @patch('test_scripts.simulate_user.CredexBotService')
    def test_send_message_interactive(self, mock_credex_bot_service):
        mock_service_instance = MagicMock()
        mock_credex_bot_service.return_value = mock_service_instance
        mock_service_instance.response = {
            "interactive": {
                "body": {"text": "Interactive message"},
                "action": {
                    "button": "Test Button",
                    "sections": [
                        {
                            "title": "Test Section",
                            "rows": [
                                {"id": "1", "title": "Option 1"},
                                {"id": "2", "title": "Option 2"}
                            ]
                        }
                    ]
                }
            }
        }

        with patch('builtins.print') as mock_print:
            self.simulator.send_message("1", "interactive")

        mock_credex_bot_service.assert_called_once()
        mock_print.assert_any_call("User: 1")
        mock_print.assert_any_call("Bot: Interactive message")
        mock_print.assert_any_call("Options: Test Button")
        mock_print.assert_any_call("Section: Test Section")
        mock_print.assert_any_call("  1: Option 1")
        mock_print.assert_any_call("  2: Option 2")

    @patch('test_scripts.simulate_user.CredexBotService')
    def test_send_message_no_response(self, mock_credex_bot_service):
        mock_service_instance = MagicMock()
        mock_credex_bot_service.return_value = mock_service_instance
        mock_service_instance.response = None

        with patch('builtins.print') as mock_print:
            self.simulator.send_message("Hello")

        mock_credex_bot_service.assert_called_once()
        mock_print.assert_any_call("User: Hello")
        mock_print.assert_any_call("Bot: No response")

    @patch('test_scripts.simulate_user.CredexBotService')
    def test_send_message_exception(self, mock_credex_bot_service):
        mock_credex_bot_service.side_effect = Exception("Test exception")

        with patch('builtins.print') as mock_print:
            self.simulator.send_message("Hello")

        mock_credex_bot_service.assert_called_once()
        mock_print.assert_any_call("User: Hello")
        mock_print.assert_any_call("Error: Test exception")

    @patch('test_scripts.simulate_user.CredexBotService')
    def test_multi_step_conversation(self, mock_credex_bot_service):
        mock_service_instance = MagicMock()
        mock_credex_bot_service.return_value = mock_service_instance

        conversation_flow = [
            ({"text": {"body": "Welcome! What's your name?"}}, "John"),
            ({"text": {"body": "Nice to meet you, John! How old are you?"}}, "25"),
            ({"text": {"body": "Great! What's your favorite color?"}}, "Blue"),
            ({"text": {"body": "Thanks for sharing, John! Your profile is complete."}}, None)
        ]

        with patch('builtins.print') as mock_print:
            for bot_response, user_input in conversation_flow:
                mock_service_instance.response = bot_response
                self.simulator.send_message(user_input if user_input else "")

                if user_input:
                    mock_print.assert_any_call(f"User: {user_input}")
                mock_print.assert_any_call(f"Bot: {bot_response['text']['body']}")

        self.assertEqual(mock_credex_bot_service.call_count, len(conversation_flow))

    @patch('test_scripts.simulate_user.CredexBotService')
    def test_mixed_message_types(self, mock_credex_bot_service):
        mock_service_instance = MagicMock()
        mock_credex_bot_service.return_value = mock_service_instance

        conversation_flow = [
            ({"text": {"body": "Welcome! Choose an option:"}}, "1"),
            ({"interactive": {
                "body": {"text": "You chose option 1. Select a sub-option:"},
                "action": {
                    "button": "Select",
                    "sections": [
                        {
                            "title": "Sub-options",
                            "rows": [
                                {"id": "A", "title": "Sub-option A"},
                                {"id": "B", "title": "Sub-option B"}
                            ]
                        }
                    ]
                }
            }}, "A"),
            ({"text": {"body": "You selected sub-option A. Please confirm (Yes/No):"}}, "Yes"),
            ({"text": {"body": "Thank you for your confirmation."}}, None)
        ]

        with patch('builtins.print') as mock_print:
            for bot_response, user_input in conversation_flow:
                mock_service_instance.response = bot_response
                self.simulator.send_message(user_input if user_input else "")

                if user_input:
                    mock_print.assert_any_call(f"User: {user_input}")
                
                if 'text' in bot_response:
                    mock_print.assert_any_call(f"Bot: {bot_response['text']['body']}")
                elif 'interactive' in bot_response:
                    mock_print.assert_any_call(f"Bot: {bot_response['interactive']['body']['text']}")
                    mock_print.assert_any_call(f"Options: {bot_response['interactive']['action']['button']}")
                    for section in bot_response['interactive']['action']['sections']:
                        mock_print.assert_any_call(f"Section: {section['title']}")
                        for row in section['rows']:
                            mock_print.assert_any_call(f"  {row['id']}: {row['title']}")

        self.assertEqual(mock_credex_bot_service.call_count, len(conversation_flow))

if __name__ == '__main__':
    unittest.main()