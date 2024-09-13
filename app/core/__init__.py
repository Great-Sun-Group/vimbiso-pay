# core/__init__.py

# Only include absolutely necessary imports here
from .config.apps import CoreConfig

# If you need to make any of these classes or functions available at the package level,
# you can use lazy imports or import them in the specific files where they are needed.

# Example of a lazy import (if needed):
# from django.utils.functional import lazy
# CredexBotService = lazy(lambda: __import__('core.message_handling.credex_bot_service').CredexBotService, type(type))

# Add any other necessary configurations here