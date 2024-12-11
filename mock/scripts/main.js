import { createMessagePayload, createFormReply } from './handlers.js';
import { ChatUI } from './ui.js';

class WhatsAppMock {
    constructor() {
        this.ui = new ChatUI();
        this.ui.setupEventListeners(() => this.sendMessage());
        this.ui.updateStatus();
    }

    async sendMessage() {
        const messageText = this.ui.messageInput.value;
        if (!messageText) return;

        this.ui.disableSendButton(true);

        let messageType = 'text';
        let displayText = messageText;
        let processedMessage = messageText;

        if (messageText.startsWith('form:')) {
            messageType = 'interactive';
            const [, formName, formDataStr] = messageText.split(':');
            const formData = Object.fromEntries(
                formDataStr.split(',').map(pair => {
                    const [key, value] = pair.split('=');
                    return [key, value];
                })
            );
            displayText = `Form data: ${formDataStr}`;
            processedMessage = createFormReply(formData, formName);
        } else if (messageText.startsWith('handle')) {
            messageType = 'interactive';
            displayText = messageText;
        } else if (messageText.startsWith('button:')) {
            messageType = 'button';
            displayText = messageText.substring(7);
        }

        this.ui.displayUserMessage(displayText);

        try {
            const payload = createMessagePayload(
                messageType,
                processedMessage,
                this.ui.phoneInput.value
            );

            const response = await fetch(`./bot/webhook?target=${this.ui.targetSelect.value}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json',
                    'X-Mock-Testing': 'true'
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok) {
                throw new Error(`Server responded with ${response.status}: ${await response.text()}`);
            }

            const data = await response.json();

            setTimeout(() => {
                this.ui.displayMessage(data);
                this.ui.disableSendButton(false);
            }, 1000);

        } catch (error) {
            console.error('Error:', error);
            this.ui.displayMessage(`Error: ${error.message}`);
            this.ui.disableSendButton(false);
        }

        this.ui.clearInput();
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new WhatsAppMock();
});
