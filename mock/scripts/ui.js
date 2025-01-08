import { createNativeForm, formatWhatsAppText } from './handlers.js';

export class ChatUI {
    constructor() {
        this.messageInput = document.getElementById('messageInput');
        this.phoneInput = document.getElementById('phoneNumber');
        this.targetSelect = document.getElementById('target');
        this.sendButton = document.getElementById('sendButton');
        this.chatContainer = document.getElementById('chatContainer');
        this.statusDiv = document.getElementById('status');
        this.currentFormName = null;
        this.lastMessageId = null;
    }

    displayMessage(messageData) {
        console.log('=== DISPLAY MESSAGE START ===');
        console.log('Raw message data:', messageData);
        console.log('Message type:', messageData?.type);
        console.log('Interactive data:', messageData?.interactive);

        // Skip success acknowledgments
        if (messageData?.success === true) {
            console.log('Skipping success acknowledgment');
            return;
        }

        const messageDiv = document.createElement('div');
        messageDiv.className = 'message bot-message';

        try {
            // Handle direct text content
            if (typeof messageData === 'string') {
                console.log('Handling string message');
                messageDiv.className += ' whatsapp-text';
                messageDiv.innerHTML = formatWhatsAppText(messageData);
                console.log('Formatted string message:', messageDiv.innerHTML);
            }
            // Handle interactive messages
            else if (messageData?.type === 'interactive') {
                console.log('Handling interactive message');
                messageDiv.className = 'interactive-message';

                // Display message body
                if (messageData.interactive?.body?.text) {
                    console.log('Adding body text:', messageData.interactive.body.text);
                    const bodyDiv = document.createElement('div');
                    bodyDiv.className = 'body whatsapp-text';
                    bodyDiv.innerHTML = formatWhatsAppText(messageData.interactive.body.text);
                    messageDiv.appendChild(bodyDiv);
                    console.log('Body HTML:', bodyDiv.outerHTML);
                }

                // Handle interactive components
                if (messageData.interactive?.action) {
                    console.log('Adding interactive action:', messageData.interactive.action);
                    const action = messageData.interactive.action;

                    // Create list container
                    if (messageData.interactive.type === 'list' && action.button) {
                        console.log('Creating list interface');
                        const listContainer = document.createElement('div');
                        listContainer.className = 'list-container';

                        // Add main button
                        const mainButton = document.createElement('button');
                        mainButton.className = 'list-button';
                        mainButton.textContent = action.button;
                        listContainer.appendChild(mainButton);
                        console.log('Added main button:', mainButton.outerHTML);

                        // Create options container
                        const optionsContainer = document.createElement('div');
                        optionsContainer.className = 'list-options';
                        optionsContainer.style.display = 'none';

                        // Add sections
                        if (action.sections) {
                            action.sections.forEach(section => {
                                console.log('Processing section:', section);
                                if (section.title) {
                                    const sectionTitle = document.createElement('div');
                                    sectionTitle.className = 'section-title';
                                    sectionTitle.textContent = section.title;
                                    optionsContainer.appendChild(sectionTitle);
                                    console.log('Added section title:', sectionTitle.outerHTML);
                                }

                                if (section.rows) {
                                    section.rows.forEach(row => {
                                        console.log('Processing row:', row);
                                        const option = document.createElement('button');
                                        option.className = 'list-option';
                                        option.textContent = row.title;
                                        option.onclick = () => {
                                            this.messageInput.value = row.id;
                                            this.sendButton.click();
                                            optionsContainer.style.display = 'none';
                                        };
                                        optionsContainer.appendChild(option);
                                        console.log('Added option:', option.outerHTML);
                                    });
                                }
                            });
                        }

                        // Toggle options on main button click
                        mainButton.onclick = () => {
                            const newDisplay = optionsContainer.style.display === 'none' ? 'block' : 'none';
                            console.log('Toggling options display:', newDisplay);
                            optionsContainer.style.display = newDisplay;
                        };

                        listContainer.appendChild(optionsContainer);
                        messageDiv.appendChild(listContainer);
                        console.log('Final list container:', listContainer.outerHTML);
                    }
                    // Handle button messages
                    else if (messageData.interactive.type === 'button' && action.buttons) {
                        console.log('Creating button interface');
                        const buttonsContainer = document.createElement('div');
                        buttonsContainer.className = 'buttons';

                        action.buttons.forEach(button => {
                            const buttonElement = document.createElement('button');
                            buttonElement.className = 'button';
                            buttonElement.textContent = button.reply.title;
                            buttonElement.onclick = () => {
                                this.messageInput.value = button.reply.id;
                                this.sendButton.click();
                            };
                            buttonsContainer.appendChild(buttonElement);
                            console.log('Added button:', buttonElement.outerHTML);
                        });

                        messageDiv.appendChild(buttonsContainer);
                        console.log('Final buttons container:', buttonsContainer.outerHTML);
                    }
                }
            }
            // Handle text messages
            else if (messageData?.text?.body) {
                console.log('Handling text message');
                messageDiv.className += ' whatsapp-text';
                messageDiv.innerHTML = formatWhatsAppText(messageData.text.body);
                console.log('Formatted text message:', messageDiv.innerHTML);
            }
            // Skip unknown message types
            else {
                console.log('Unknown message type, skipping display');
                return;
            }

            // Log final HTML
            console.log('Final message HTML:', messageDiv.outerHTML);

            // Add message to chat and scroll
            this.chatContainer.appendChild(messageDiv);
            this.chatContainer.scrollTop = this.chatContainer.scrollHeight;

            console.log('=== DISPLAY MESSAGE END ===');

        } catch (error) {
            console.error('Error displaying message:', error);
            // Display error in chat
            messageDiv.className = 'message bot-message error';
            messageDiv.textContent = `Error displaying message: ${error.message}`;
            this.chatContainer.appendChild(messageDiv);
        }
    }

    displayUserMessage(text) {
        console.log('Displaying user message:', text);
        const userMessageDiv = document.createElement('div');
        userMessageDiv.className = 'message user-message';
        userMessageDiv.textContent = text;
        this.chatContainer.appendChild(userMessageDiv);
        this.chatContainer.scrollTop = this.chatContainer.scrollHeight;
        console.log('User message HTML:', userMessageDiv.outerHTML);
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
