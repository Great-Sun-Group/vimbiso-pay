import logging
from datetime import datetime

# Configure the logger
logger = logging.getLogger('audit')
logger.setLevel(logging.INFO)

# Create a file handler
handler = logging.FileHandler('audit.log')
handler.setLevel(logging.INFO)

# Create a logging format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Add the handler to the logger
logger.addHandler(handler)

def log_auth_event(event_type, user, status, details=None):
    """
    Log an authentication event.
    
    :param event_type: Type of the event (e.g., 'login', 'logout', 'password_change')
    :param user: User associated with the event
    :param status: Status of the event (e.g., 'success', 'failure')
    :param details: Additional details about the event
    """
    message = f"Auth event: {event_type} - User: {user} - Status: {status}"
    if details:
        message += f" - Details: {details}"
    logger.info(message)

def log_authorization_event(user, resource, action, status, details=None):
    """
    Log an authorization event.
    
    :param user: User attempting the action
    :param resource: Resource being accessed
    :param action: Action being performed
    :param status: Status of the authorization (e.g., 'granted', 'denied')
    :param details: Additional details about the event
    """
    message = f"Authorization event: User: {user} - Resource: {resource} - Action: {action} - Status: {status}"
    if details:
        message += f" - Details: {details}"
    logger.info(message)

# Example usage:
# log_auth_event('login', 'john_doe', 'success')
# log_authorization_event('john_doe', 'sensitive_data', 'read', 'denied', 'Insufficient permissions')