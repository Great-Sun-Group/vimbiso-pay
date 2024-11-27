class CredExCoreException(Exception):
    """Base exception for CredEx Core"""

    pass


class InvalidInputException(CredExCoreException):
    """Exception raised for invalid user input"""

    pass


class APIException(CredExCoreException):
    """Exception raised for API-related errors"""

    pass


class StateException(CredExCoreException):
    """Exception raised for state-related errors"""

    pass


class ActionHandlerException(CredExCoreException):
    """Exception raised for errors in action handlers"""

    pass


class ConfigurationException(CredExCoreException):
    """Exception raised for configuration-related errors"""

    pass
