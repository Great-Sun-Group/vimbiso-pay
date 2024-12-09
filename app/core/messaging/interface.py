from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from .types import (
    AudioContent,
    Button,
    DocumentContent,
    ImageContent,
    Message,
    MessageRecipient,
    VideoContent,
)


class MessagingServiceInterface(ABC):
    """Interface defining messaging service operations"""

    @abstractmethod
    def send_message(self, message: Message) -> Dict[str, Any]:
        """Send a message to a recipient

        Args:
            message: The message to send

        Returns:
            Response data from the messaging provider
        """
        pass

    @abstractmethod
    def send_text(
        self, recipient: MessageRecipient, text: str, preview_url: bool = False
    ) -> Dict[str, Any]:
        """Send a text message

        Args:
            recipient: Message recipient
            text: Message text
            preview_url: Whether to generate URL previews

        Returns:
            Response data from the messaging provider
        """
        pass

    @abstractmethod
    def send_template(
        self,
        recipient: MessageRecipient,
        template_name: str,
        language: Dict[str, str],
        components: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Send a template message

        Args:
            recipient: Message recipient
            template_name: Name of the template to use
            language: Language information
            components: Template components

        Returns:
            Response data from the messaging provider
        """
        pass

    @abstractmethod
    def send_interactive(
        self,
        recipient: MessageRecipient,
        body: str,
        buttons: List[Button],
        header: Optional[str] = None,
        footer: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send an interactive message

        Args:
            recipient: Message recipient
            body: Message body
            buttons: Interactive buttons
            header: Optional header text
            footer: Optional footer text

        Returns:
            Response data from the messaging provider
        """
        pass

    @abstractmethod
    def send_media(
        self,
        recipient: MessageRecipient,
        content: Union[ImageContent, DocumentContent, AudioContent, VideoContent],
    ) -> Dict[str, Any]:
        """Send a media message

        Args:
            recipient: Message recipient
            content: Media content to send

        Returns:
            Response data from the messaging provider
        """
        pass

    @abstractmethod
    def send_location(
        self,
        recipient: MessageRecipient,
        latitude: float,
        longitude: float,
        name: Optional[str] = None,
        address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a location message

        Args:
            recipient: Message recipient
            latitude: Location latitude
            longitude: Location longitude
            name: Optional location name
            address: Optional location address

        Returns:
            Response data from the messaging provider
        """
        pass

    @abstractmethod
    def validate_message(self, message: Message) -> bool:
        """Validate a message before sending

        Args:
            message: Message to validate

        Returns:
            True if message is valid, False otherwise
        """
        pass

    @abstractmethod
    def get_template(self, template_name: str) -> Dict[str, Any]:
        """Get template information

        Args:
            template_name: Name of the template

        Returns:
            Template information
        """
        pass

    @abstractmethod
    def list_templates(self) -> List[Dict[str, Any]]:
        """List all available templates

        Returns:
            List of template information
        """
        pass

    @abstractmethod
    def create_template(
        self, template_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new message template

        Args:
            template_data: Template definition

        Returns:
            Created template information
        """
        pass

    @abstractmethod
    def delete_template(self, template_name: str) -> bool:
        """Delete a message template

        Args:
            template_name: Name of the template to delete

        Returns:
            True if template was deleted, False otherwise
        """
        pass

    @abstractmethod
    def get_message_status(self, message_id: str) -> Dict[str, Any]:
        """Get the status of a sent message

        Args:
            message_id: ID of the message

        Returns:
            Message status information
        """
        pass
