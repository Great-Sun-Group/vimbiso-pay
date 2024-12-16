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
        this.lastMessageId = null; // Track last message ID for context
    }

    displayMessage(data) {
        const messageDiv = document.createElement('div');
        const messageData = data.response || data;

        // Store message ID for context in replies
        if (messageData.messages?.[0]?.id) {
            this.lastMessageId = messageData.messages[0].id;
        }

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
            const buttonsContainer = document.createElement('div');
            buttonsContainer.className = 'buttons';

            action.buttons.forEach(button => {
                const buttonWrapper = document.createElement('div');
                buttonWrapper.style.width = '100%';
                buttonWrapper.style.marginBottom = '8px';

                const buttonElement = document.createElement('button');
                buttonElement.className = 'button';
                buttonElement.textContent = button.reply.title;
                buttonElement.onclick = () => {
                    this.messageInput.value = button.reply.id;
                    this.onSendMessage();
                };

                buttonWrapper.appendChild(buttonElement);
                buttonsContainer.appendChild(buttonWrapper);
            });

            messageDiv.appendChild(buttonsContainer);
        }
        // Handle list messages
        else if (interactive.type === 'list') {
            const listDiv = document.createElement('div');
            listDiv.className = 'list-container';

            // Create list button
            if (action.button) {
                const buttonWrapper = document.createElement('div');
                buttonWrapper.style.width = '100%';
                buttonWrapper.style.marginBottom = '8px';

                const button = document.createElement('button');
                button.className = 'list-button';
                button.textContent = action.button;
                button.onclick = () => {
                    const options = listDiv.querySelector('.list-options');
                    if (options) {
                        options.style.display = options.style.display === 'none' ? 'block' : 'none';
                    }
                };

                buttonWrapper.appendChild(button);
                listDiv.appendChild(buttonWrapper);
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
                            const optionWrapper = document.createElement('div');
                            optionWrapper.style.width = '100%';
                            optionWrapper.style.marginBottom = '8px';

                            const option = document.createElement('button');
                            option.className = 'list-option';
                            option.textContent = row.title;
                            option.onclick = () => {
                                this.messageInput.value = row.id;
                                this.onSendMessage();
                                optionsDiv.style.display = 'none';
                            };

                            optionWrapper.appendChild(option);
                            optionsDiv.appendChild(optionWrapper);
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

    getLastMessageId() {
        return this.lastMessageId;
    }
}
