from ..utils.utils import CredexWhatsappService, convert_timestamp_to_date
from serializers.company import CompanyDetailsSerializer
from serializers.offers import OfferCredexSerializer
from serializers.members import MemberDetailsSerializer
from ..config.constants import *
import requests, json
from decouple import config
from django.core.cache import cache
from datetime import datetime

class CredexBotService:
    def __init__(self, payload, methods: dict = dict, user: object = None) -> None:
        self.message = payload
        self.user = user
        self.body = self.message['message']

        # Load
        self.user = CachedUser(self.user)
        current_state = user.state.get_state(user)
        if not isinstance(current_state, dict):
            current_state = current_state.state

        self.current_state = current_state
        try:
            self.response = self.handle()
            # print(self.response)
        except Exception as e:
            print("ERROR : ", e)

    # ... (rest of the class implementation)

    def format_synopsis(self, synopsis, style=None):
        formatted_synopsis = ""
        words = synopsis.split()
        line_length = 0

        for word in words:
            # If adding the word exceeds the line length, start a new line
            if line_length + len(word) + 1 > 35:
                formatted_synopsis += "\n"
                line_length = 0
            if style:
                word = f"{style}{word}{style}"
            formatted_synopsis += word + " "
            line_length += len(word) + 1

        return formatted_synopsis.strip()

    def wrap_text(self, message, proceed_option=False, x_is_menu=False, include_back=False, navigate_is="Respond",
                  extra_rows=[], number=None, back_is_cancel=False, use_buttons=False, yes_or_no=False, custom={}, plain=False, include_menu=True):
        """THIS METHOD HANDLES ABSTRACTS CLOUDAPI MESSAGE DETAILS"""
        # ... (rest of the method implementation)

    # ... (rest of the class properties and methods)

    def handle(self):
        # Implement the handle method
        pass  # Replace this with actual implementation

# Add any other necessary functions or classes here
