"""Flow-specific constants and command patterns"""

# Commands that trigger flow resets/greetings
GREETING_COMMANDS = {
    # English greetings
    "hi", "hie", "hy", "hey", "hello",

    # Navigation/menu
    "menu", "home",

    # Shona greetings
    "mhoro", "makadii",

    # Ndebele greetings
    "sawubona",

    # Swahili greetings
    "jambo", "habari",

    # French greetings
    "bonjour", "salut",

    # Spanish greetings
    "hola", "buenos dias"
}

__all__ = [
    'GREETING_COMMANDS'
]
