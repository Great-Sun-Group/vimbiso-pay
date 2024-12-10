// Message type handlers
export const handlerTitles = {
    "handle_action_offer_credex": "Offer Secured Credex",
    "handle_action_pending_offers_in": "Pending Offers",
    "handle_action_pending_offers_out": "Cancel Outgoing",
    "handle_action_transactions": "Review Transactions"
};

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

export function createMessagePayload(messageType, messageText, phoneNumber) {
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
                    messages: [{
                        from: phoneNumber,
                        id: `wamid.${Array(32).fill(0).map(() => Math.floor(Math.random() * 16).toString(16)).join('')}`,
                        timestamp: Math.floor(Date.now() / 1000).toString(),
                        type: messageType,
                        ...(messageType === 'text' ? {
                            text: { body: messageText }
                        } : messageType === 'button' ? {
                            button: { payload: messageText.substring(7) }
                        } : messageType === 'interactive' && typeof messageText === 'object' ? {
                            interactive: {
                                type: "nfm_reply",
                                nfm_reply: messageText
                            }
                        } : {
                            interactive: {
                                type: "button_reply",
                                button_reply: {
                                    id: messageText,
                                    title: handlerTitles[messageText] || messageText,
                                    selected: true
                                }
                            }
                        })
                    }]
                },
                field: "messages"
            }]
        }]
    };
}

export function createFormReply(formData) {
    return {
        submitted_form_data: {
            response_at: Math.floor(Date.now() / 1000).toString(),
            form_data: {
                version: "1",
                screen: "MAIN",
                name: "credex_offer_form",
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
