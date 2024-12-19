export function formatWhatsAppText(text) {
    if (!text) return '';

    // Debug log
    console.log('Formatting text:', text);

    // Handle WhatsApp markdown
    const formattedText = text
        .replace(/\*(.*?)\*/g, '<strong>$1</strong>') // Bold
        .replace(/_(.*?)_/g, '<em>$1</em>')          // Italic
        .replace(/~(.*?)~/g, '<del>$1</del>')        // Strikethrough
        .replace(/```(.*?)```/g, '<code>$1</code>')  // Code
        .replace(/\n/g, '<br>');                     // Line breaks

    // Debug log
    console.log('Formatted result:', formattedText);

    return formattedText;
}

export function createNativeForm(fields, onSubmit) {
    const formContainer = document.createElement('div');
    formContainer.className = 'form-container';

    fields.forEach(field => {
        const fieldDiv = document.createElement('div');
        fieldDiv.className = 'form-field';

        const label = document.createElement('label');
        label.textContent = field.label;
        fieldDiv.appendChild(label);

        const input = document.createElement('input');
        input.type = field.type;
        input.name = field.name;
        input.required = field.required;
        input.placeholder = field.label;
        fieldDiv.appendChild(input);

        formContainer.appendChild(fieldDiv);
    });

    const submitButton = document.createElement('button');
    submitButton.className = 'form-submit';
    submitButton.textContent = 'Submit';
    submitButton.onclick = () => {
        const formData = {};
        fields.forEach(field => {
            const input = formContainer.querySelector(`input[name="${field.name}"]`);
            formData[field.name] = input.value;
        });
        onSubmit(formData);
    };
    formContainer.appendChild(submitButton);

    return formContainer;
}

export function createMessagePayload(messageType, messageText, phoneNumber, contextMessageId = null) {
    // Create message object matching WhatsApp format
    const message = {
        from: phoneNumber,
        id: `wamid.${Array(32).fill(0).map(() => Math.floor(Math.random() * 16).toString(16)).join('')}`,
        timestamp: Math.floor(Date.now() / 1000).toString()
    };

    // Add message content based on type
    if (messageType === 'text') {
        message.type = 'text';
        message.text = {
            body: messageText,
            preview_url: false
        };
    } else if (messageType === 'interactive') {
        message.type = 'interactive';
        if (messageText.startsWith('handle_action_')) {
            // Handle menu/button selections
            message.interactive = {
                type: 'button_reply',
                button_reply: {
                    id: messageText,
                    title: messageText
                }
            };
        } else if (typeof messageText === 'object') {
            // Handle form submissions
            message.interactive = {
                type: 'nfm_reply',
                nfm_reply: messageText
            };
        }
    }

    // Create full webhook payload matching staging format
    return {
        object: "whatsapp_business_account",
        entry: [{
            id: "WHATSAPP_BUSINESS_ACCOUNT_ID",
            changes: [{
                value: {
                    messaging_product: "whatsapp",
                    metadata: {
                        display_phone_number: "263787274250",  // Match staging
                        phone_number_id: "390447444143042",    // Match staging
                        timestamp: Math.floor(Date.now() / 1000).toString()
                    },
                    contacts: [{
                        profile: {
                            name: "Test User"
                        },
                        wa_id: phoneNumber
                    }],
                    messages: [message]
                },
                field: "messages"
            }]
        }]
    };
}

export function createFormReply(formData, formName) {
    const timestamp = Math.floor(Date.now() / 1000).toString();

    // Format form reply matching WhatsApp's format
    return {
        submitted_form_data: {
            response_at: timestamp,
            form_data: {
                version: "1",
                screen: "MAIN",
                response_payload: {
                    response_json: JSON.stringify(formData),
                    version: "1"
                },
                response_fields: Object.entries(formData).map(([field_id, value]) => ({
                    field_id: field_id,
                    value: String(value),
                    type: "text",
                    screen: "MAIN",
                    version: "1",
                    selected: true
                }))
            }
        }
    };
}
