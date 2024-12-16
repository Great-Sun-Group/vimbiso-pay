import { createFormReply, createMessagePayload } from './handlers.js';
import { ChatUI } from './ui.js';

class WhatsAppMock {
    constructor() {
        this.ui = new ChatUI();
        this.ui.setupEventListeners(() => this.sendMessage());
        this.ui.updateStatus();
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
            // Create payload matching WhatsApp format
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

            const data = await response.json();
            console.log('Raw response from server:', data);

            // Display response after a short delay
            setTimeout(() => {
                // Get the response content
                const responseData = data.response || data;
                console.log('Processed response data:', responseData);

                // Log the type and structure
                console.log('Response type:', typeof responseData);
                console.log('Response keys:', Object.keys(responseData));
                if (responseData.type === 'interactive') {
                    console.log('Interactive type:', responseData.interactive?.type);
                    console.log('Interactive content:', responseData.interactive);
                }

                this.ui.displayMessage(responseData);
                this.ui.disableSendButton(false);

                console.log('=== SEND MESSAGE END ===');
            }, 1000);

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
