"""Generic utility functions"""
import logging
from datetime import datetime

import requests

from .exceptions import ComponentException, SystemException

logger = logging.getLogger(__name__)


def format_synopsis(synopsis: str, style: str = None, max_line_length: int = 35) -> str:
    """Format synopsis text with line breaks and optional styling

    Args:
        synopsis: Text to format
        style: Optional style markers to wrap words with
        max_line_length: Maximum length per line

    Returns:
        Formatted synopsis text

    Raises:
        ComponentException: If synopsis format is invalid
    """
    try:
        if not isinstance(synopsis, str):
            raise ComponentException(
                message="Synopsis must be a string",
                component="text_formatter",
                field="synopsis",
                value=str(synopsis)
            )

        if max_line_length < 1:
            raise ComponentException(
                message="Max line length must be positive",
                component="text_formatter",
                field="max_line_length",
                value=str(max_line_length)
            )

        formatted_synopsis = ""
        words = synopsis.split()
        line_length = 0

        for word in words:
            if line_length + len(word) + 1 > max_line_length:
                formatted_synopsis += "\n"
                line_length = 0
            if style:
                word = f"{style}{word}{style}"
            formatted_synopsis += word + " "
            line_length += len(word) + 1

        return formatted_synopsis.strip()

    except ComponentException:
        raise
    except Exception as e:
        raise ComponentException(
            message=f"Failed to format synopsis: {str(e)}",
            component="text_formatter",
            field="synopsis",
            value=synopsis
        )


def convert_timestamp_to_date(timestamp: int) -> str:
    """Convert millisecond timestamp to formatted date string

    Args:
        timestamp: Unix timestamp in milliseconds

    Returns:
        Formatted date string

    Raises:
        ComponentException: If timestamp is invalid
    """
    try:
        if not isinstance(timestamp, (int, float)):
            raise ComponentException(
                message="Timestamp must be a number",
                component="date_formatter",
                field="timestamp",
                value=str(timestamp)
            )

        if timestamp < 0:
            raise ComponentException(
                message="Timestamp cannot be negative",
                component="date_formatter",
                field="timestamp",
                value=str(timestamp)
            )

        return datetime.fromtimestamp(timestamp / 1000).strftime("%Y-%m-%d %H:%M:%S")

    except ComponentException:
        raise
    except Exception as e:
        raise ComponentException(
            message=f"Failed to convert timestamp: {str(e)}",
            component="date_formatter",
            field="timestamp",
            value=str(timestamp)
        )


def format_denomination(amount: float, denomination: str) -> str:
    """Format currency amount with denomination

    Args:
        amount: Currency amount
        denomination: Currency denomination code

    Returns:
        Formatted currency string

    Raises:
        ComponentException: If amount or denomination is invalid
    """
    try:
        if not isinstance(amount, (int, float)):
            raise ComponentException(
                message="Amount must be a number",
                component="currency_formatter",
                field="amount",
                value=str(amount)
            )

        if not isinstance(denomination, str):
            raise ComponentException(
                message="Denomination must be a string",
                component="currency_formatter",
                field="denomination",
                value=str(denomination)
            )

        if amount < 0:
            raise ComponentException(
                message="Amount cannot be negative",
                component="currency_formatter",
                field="amount",
                value=str(amount)
            )

        if denomination.upper() == "USD":
            return f"${amount:.2f}"
        else:
            return f"{amount:.2f} {denomination}"

    except ComponentException:
        raise
    except Exception as e:
        raise ComponentException(
            message=f"Failed to format denomination: {str(e)}",
            component="currency_formatter",
            field="format",
            value=f"{amount} {denomination}"
        )


def validate_channel_identifier(identifier: str) -> None:
    """Validate channel identifier format

    Args:
        identifier: Channel identifier to validate

    Raises:
        ComponentException: If identifier format is invalid
    """
    # Basic validation for WhatsApp numbers
    # Can be extended for other channel types
    if not identifier.startswith("+"):
        raise ComponentException(
            message="Channel identifier must start with '+'",
            component="channel_validator",
            field="identifier",
            value=identifier
        )

    if len(identifier) < 10:
        raise ComponentException(
            message="Channel identifier must be at least 10 digits",
            component="channel_validator",
            field="identifier",
            value=identifier
        )

    if not identifier[1:].isdigit():
        raise ComponentException(
            message="Channel identifier must contain only digits after '+'",
            component="channel_validator",
            field="identifier",
            value=identifier
        )


def mask_sensitive_info(text: str, mask_char: str = "*") -> str:
    """Mask sensitive information in text

    Args:
        text: Text containing sensitive information
        mask_char: Character to use for masking

    Returns:
        Masked text string

    Raises:
        ComponentException: If text or mask_char is invalid
    """
    try:
        if not isinstance(text, str):
            raise ComponentException(
                message="Text must be a string",
                component="text_masker",
                field="text",
                value=str(text)
            )

        if not isinstance(mask_char, str) or len(mask_char) != 1:
            raise ComponentException(
                message="Mask character must be a single character",
                component="text_masker",
                field="mask_char",
                value=str(mask_char)
            )

        words = text.split()
        masked_words = []
        for word in words:
            if len(word) > 4:
                masked_word = word[:2] + mask_char * (len(word) - 4) + word[-2:]
            else:
                masked_word = mask_char * len(word)
            masked_words.append(masked_word)
        return " ".join(masked_words)

    except ComponentException:
        raise
    except Exception as e:
        raise ComponentException(
            message=f"Failed to mask text: {str(e)}",
            component="text_masker",
            field="text",
            value=text
        )


def handle_api_error(response: requests.Response) -> None:
    """Handle API error responses

    Args:
        response: Response object from requests

    Raises:
        SystemException: If response indicates an error
    """
    if response.status_code >= 400:
        try:
            error_data = response.json()
            error_detail = error_data.get('error', response.text)
        except ValueError:
            error_detail = response.text

        raise SystemException(
            message=f"API Error: {response.status_code} - {error_detail}",
            code="API_ERROR",
            service="api",
            action="request",
            details={
                "status_code": response.status_code,
                "error": error_detail
            }
        )
