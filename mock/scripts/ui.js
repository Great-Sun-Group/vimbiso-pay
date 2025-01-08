import { formatWhatsAppText } from './handlers.js';

export class ChatUI {
    constructor() {
        this.messageInput = document.getElementById('messageInput');
        this.phoneInput = document.getElementById('phoneNumber');
        this.targetSelect = document.getElementById('target');
        this.sendButton = document.getElementById('sendButton');
        this.chatContainer = document.getElementById('chatContainer');
        this.statusDiv = document.getElementById('status');

        // Format any existing messages
        this.formatExistingMessages();
    }

    formatExistingMessages() {
        const messages = document.querySelectorAll('.message.whatsapp-text');
        messages.forEach(message => {
            const rawText = message.getAttribute('data-raw-text');
            if (rawText) {
                message.innerHTML = formatWhatsAppText(rawText);
            }
        });
    }

    showNotification(text) {
        const notificationDiv = document.createElement('div');
        notificationDiv.className = 'message notification';
        notificationDiv.textContent = text;
        this.chatContainer.appendChild(notificationDiv);
        this.chatContainer.scrollTop = this.chatContainer.scrollHeight;

        // Format any new messages that were added
        this.formatExistingMessages();
    }

    updateStatus() {
        const text = this.targetSelect.value === 'local' ?
            'Local Server (localhost:8000)' :
            'Staging Server (stage.whatsapp.vimbisopay.africa)';
        this.statusDiv.innerHTML = `Connected to: ${text}`;
        this.statusDiv.className = `status ${this.targetSelect.value}`;
    }

    disableSendButton(disabled = true) {
        this.sendButton.disabled = disabled;
    }

    clearInput() {
        this.messageInput.value = '';
    }

    setupEventListeners(onSendMessage) {
        // Send message
        this.onSendMessage = onSendMessage;
        this.sendButton.addEventListener('click', onSendMessage);
        this.messageInput.addEventListener('keypress', e => {
            if (e.key === 'Enter' && !this.sendButton.disabled) {
                onSendMessage();
            }
        });

        // Target change
        this.targetSelect.addEventListener('change', () => this.updateStatus());

        // Set up refresh button
        const refreshButton = document.getElementById('refreshButton');
        refreshButton.onclick = () => window.location.reload();

        // Set up clear button
        const clearButton = document.getElementById('clearButton');
        clearButton.onclick = async () => {
            try {
                const response = await fetch(`${window.location.origin}/clear-conversation`);
                if (!response.ok) {
                    throw new Error(`Server responded with ${response.status}`);
                }
                window.location.reload();
            } catch (error) {
                console.error('Error clearing conversation:', error);
                this.showNotification(`Error: ${error.message}`);
            }
        };
    }

    getLastMessageId() {
        return this.lastMessageId;
    }
}
