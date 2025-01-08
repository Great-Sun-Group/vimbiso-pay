import { createFormReply } from './handlers.js';
import { ChatUI } from './ui.js';

class WhatsAppMock {
    constructor() {
        this.ui = new ChatUI();
        this.ui.setupEventListeners(() => this.sendMessage());
        this.ui.updateStatus();
        this.setupAppMessageStream();
    }

    setupAppMessageStream() {
        console.log('Setting up SSE connection...');
        // Connect to server events stream for app messages
        const events = new EventSource('./events');

        events.onopen = () => {
            console.log('SSE connection opened');
        };

        events.onmessage = (event) => {
            console.log('Received SSE message:', event.data);
            const message = JSON.parse(event.data);
            console.log('Parsed message:', message);
            this.ui.displayMessage(message);
        };

        events.onerror = (error) => {
            console.error('EventSource error:', error);
            events.close();
            // Retry connection after 1s
            console.log('Retrying SSE connection in 1s...');
            setTimeout(() => this.setupAppMessageStream(), 1000);
        };
    }

    async sendMessage() {
        const messageText = this.ui.messageInput.value.trim();
        if (!messageText) return;

        this.ui.disableSendButton(true);

        let messageType = 'text';
        let displayText = messageText;
        let processedMessage = messageText;

        console.log('=== SEND MESSAGE START ===');
        console.log('Original message:', messageText);

        // Handle special message types
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
            console.log('Processed form data:', processedMessage);
        } else if (messageText.startsWith('handle_action_')) {
            messageType = 'interactive';
            displayText = messageText;
            console.log('Handling action:', messageText);
        }

        // Display user's message in UI
        this.ui.displayUserMessage(displayText);

        try {
            // Create simple message payload
            const payload = {
                type: messageType,
                message: processedMessage,
                phone: this.ui.phoneInput.value
            };

            console.log('Sending payload to server:', payload);

            // Send to mock server
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

            // Ignore empty response from UI->App message
            await response.text();
            this.ui.disableSendButton(false);

        } catch (error) {
            console.error('Error:', error);
            this.ui.displayMessage({
                type: 'text',
                text: { body: `Error: ${error.message}` }
            });
            this.ui.disableSendButton(false);
        }

        this.ui.clearInput();
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new WhatsAppMock();
});
