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

        try {
            const payload = {
                type: 'text',
                message: messageText,
                phone: this.ui.phoneInput.value
            };

            const response = await fetch(`${window.location.origin}/bot/webhook?target=${this.ui.targetSelect.value}`, {
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

            // Show refresh notification
            this.ui.showNotification('Message sent! Click Refresh to update conversation.');
            this.ui.disableSendButton(false);
        } catch (error) {
            console.error('Error:', error);
            this.ui.showNotification(`Error: ${error.message}`);
            this.ui.disableSendButton(false);
        }

        this.ui.clearInput();
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new WhatsAppMock();
});
