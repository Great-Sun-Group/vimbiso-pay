export function formatWhatsAppText(text) {
    return text
        .replace(/\*(.*?)\*/g, '<strong>$1</strong>')
        .replace(/_(.*?)_/g, '<em>$1</em>')
        .replace(/\n/g, '<br>');
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
    const message = {
        from: phoneNumber,
        id: `wamid.${Array(32).fill(0).map(() => Math.floor(Math.random() * 16).toString(16)).join('')}`,
        timestamp: Math.floor(Date.now() / 1000).toString()
    };

    // Add context for button responses
    if (contextMessageId) {
        message.context = {
            from: phoneNumber,
            id: contextMessageId
        };
    }

    // Add message content based on type
    if (messageType === 'text') {
        message.type = 'text';
        message.text = { body: messageText };
    } else if (messageType === 'button' || messageType === 'interactive') {
        // All button responses should be type "button" to match WhatsApp format
        message.type = 'button';
        message.button = {
            text: messageText,
            payload: messageText
        };
    } else if (messageType === 'interactive' && typeof messageText === 'object') {
        message.type = 'interactive';
        message.interactive = {
            type: "nfm_reply",
            nfm_reply: messageText
        };
    }

    return {
        object: "whatsapp_business_account",
        entry: [{
            id: "WHATSAPP_BUSINESS_ACCOUNT_ID",
            changes: [{
                value: {
                    messaging_product: "whatsapp",
                    metadata: {
                        display_phone_number: "15550123456",
                        phone_number_id: "123456789",
                        timestamp: Math.floor(Date.now() / 1000).toString()
                    },
                    contacts: [{
                        wa_id: phoneNumber,
                        profile: { name: "" }
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
    return {
        submitted_form_data: {
            response_at: timestamp,
            form_data: {
                version: "1",
                screen: "MAIN",
                name: formName,
                response_payload: {
                    response_json: JSON.stringify(formData),
                    version: "1"
                },
                response_fields: Object.entries(formData).map(([field_id, value]) => ({
                    field_id,
                    value,
                    type: "text",
                    screen: "MAIN",
                    version: "1",
                    selected: true
                }))
            }
        }
    };
}
