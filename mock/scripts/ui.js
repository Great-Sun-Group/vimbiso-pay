import { createNativeForm, formatWhatsAppText } from './handlers.js';

export class ChatUI {
    constructor() {
        this.messageInput = document.getElementById('messageInput');
        this.phoneInput = document.getElementById('phoneNumber');
        this.targetSelect = document.getElementById('target');
        this.sendButton = document.getElementById('sendButton');
        this.chatContainer = document.getElementById('chatContainer');
        this.statusDiv = document.getElementById('status');
        this.currentFormName = null; // Track current form name
    }

    displayMessage(data) {
        const messageDiv = document.createElement('div');
        const messageData = data.response || data;

        if (typeof messageData === 'string') {
            messageDiv.className = 'message bot-message whatsapp-text';
            messageDiv.innerHTML = formatWhatsAppText(messageData);
        } else if (messageData.type === 'interactive') {
            messageDiv.className = 'interactive-message';

            // Display message body if present
            if (messageData.interactive?.body?.text) {
                const bodyDiv = document.createElement('div');
                bodyDiv.className = 'body whatsapp-text';
                bodyDiv.innerHTML = formatWhatsAppText(messageData.interactive.body.text);
                messageDiv.appendChild(bodyDiv);
            }

            // Handle interactive components
            if (messageData.interactive?.action) {
                this.handleInteractiveAction(messageDiv, messageData.interactive);
            }
        } else if (messageData.text?.body) {
            messageDiv.className = 'message bot-message whatsapp-text';
            messageDiv.innerHTML = formatWhatsAppText(messageData.text.body);
        }

        this.chatContainer.appendChild(messageDiv);
        this.chatContainer.scrollTop = this.chatContainer.scrollHeight;
    }

    handleInteractiveAction(messageDiv, interactive) {
        const action = interactive.action;

        // Handle native form messages
        if (interactive.type === 'nfm') {
            // Store form name for use in response
            this.currentFormName = action.name;
            messageDiv.appendChild(createNativeForm(
                action.parameters.fields,
                formData => {
                    // Include form name in submission
                    this.messageInput.value = `form:${this.currentFormName}:${Object.entries(formData).map(([k,v]) => `${k}=${v}`).join(',')}`;
                    this.onSendMessage();
                }
            ));
        }
        // Handle button messages
        else if (interactive.type === 'button' && action.buttons) {
            const buttonsDiv = document.createElement('div');
            buttonsDiv.className = 'buttons';

            action.buttons.forEach(button => {
                const buttonElement = document.createElement('div');
                buttonElement.className = 'button';
                buttonElement.textContent = button.reply.title;
                buttonElement.onclick = () => {
                    this.messageInput.value = button.reply.id;
                    this.onSendMessage();
                };
                buttonsDiv.appendChild(buttonElement);
            });

            messageDiv.appendChild(buttonsDiv);
        }
        // Handle list messages
        else if (interactive.type === 'list') {
            const listDiv = document.createElement('div');
            listDiv.className = 'list-container';

            // Create list button
            if (action.button) {
                const button = document.createElement('div');
                button.className = 'list-button';
                button.textContent = action.button;
                button.onclick = () => {
                    const options = listDiv.querySelector('.list-options');
                    if (options) {
                        options.style.display = options.style.display === 'none' ? 'block' : 'none';
                    }
                };
                listDiv.appendChild(button);
            }

            // Create list options
            if (action.sections) {
                const optionsDiv = document.createElement('div');
                optionsDiv.className = 'list-options';
                optionsDiv.style.display = 'none';

                action.sections.forEach(section => {
                    if (section.title) {
                        const titleDiv = document.createElement('div');
                        titleDiv.className = 'list-section-title';
                        titleDiv.textContent = section.title;
                        optionsDiv.appendChild(titleDiv);
                    }

                    if (section.rows) {
                        section.rows.forEach(row => {
                            const option = document.createElement('div');
                            option.className = 'list-option';
                            option.textContent = row.title;
                            option.onclick = () => {
                                this.messageInput.value = row.id;
                                this.onSendMessage();
                                optionsDiv.style.display = 'none';
                            };
                            optionsDiv.appendChild(option);
                        });
                    }
                });

                listDiv.appendChild(optionsDiv);
            }

            messageDiv.appendChild(listDiv);
        }
    }

    displayUserMessage(text) {
        const userMessageDiv = document.createElement('div');
        userMessageDiv.className = 'message user-message';
        userMessageDiv.textContent = text;
        this.chatContainer.appendChild(userMessageDiv);
        this.chatContainer.scrollTop = this.chatContainer.scrollHeight;
    }

    updateStatus() {
        const text = this.targetSelect.value === 'local' ?
            'Local Server (localhost:8000)' :
            'Staging Server (stage.whatsapp.vimbisopay.africa)';
        this.statusDiv.textContent = `Connected to: ${text}`;
        this.statusDiv.className = `status ${this.targetSelect.value}`;
    }

    disableSendButton(disabled = true) {
        this.sendButton.disabled = disabled;
    }

    clearInput() {
        this.messageInput.value = '';
    }

    setupEventListeners(onSendMessage) {
        this.onSendMessage = onSendMessage;
        this.sendButton.addEventListener('click', onSendMessage);
        this.messageInput.addEventListener('keypress', e => {
            if (e.key === 'Enter' && !this.sendButton.disabled) {
                onSendMessage();
            }
        });
        this.targetSelect.addEventListener('change', () => this.updateStatus());
    }
}
