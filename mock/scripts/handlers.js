export function formatInteractiveMessage(interactive) {
    if (!interactive) return '';

    // Enhanced debug logging
    console.log('Formatting interactive message:', {
        message: interactive,
        type: interactive.type,
        body: interactive.body,
        action: interactive.action,
        structure: JSON.stringify(interactive, null, 2)
    });

    const type = interactive.type;
    let formattedHtml = '';

    // Debug log message type
    console.log('Processing message of type:', type);

    if (type === 'button') {
        const buttons = interactive.action?.buttons || [];
        formattedHtml = `
            <div class="interactive-buttons">
                <div class="interactive-body">${formatWhatsAppText(interactive.body?.text || '')}</div>
                ${buttons.map(button => `
                    <button class="whatsapp-button" data-id="${button.reply.id}">
                        ${button.reply.title}
                    </button>
                `).join('')}
            </div>
        `;
    } else if (type === 'button_reply') {
        formattedHtml = `
            <div class="interactive-buttons">
                <div class="interactive-body">Selected: ${interactive.button_reply?.title || ''}</div>
            </div>
        `;
    } else if (type === 'list_reply') {
        formattedHtml = `
            <div class="interactive-list">
                <div class="interactive-body">Selected: ${interactive.list_reply?.title || ''}</div>
                ${interactive.list_reply?.description ? `<div class="item-description">${interactive.list_reply.description}</div>` : ''}
            </div>
        `;
    } else if (type === 'list') {
        const sections = interactive.action?.sections || [];
        const buttonText = interactive.action?.button || 'Select Option';
        formattedHtml = `
            <div class="interactive-list">
                <div class="interactive-body">${formatWhatsAppText(interactive.body?.text || '')}</div>
                <button class="whatsapp-button list-select-button">${buttonText}</button>
                <div class="list-sections">
                    ${sections.map(section => `
                        <div class="list-section">
                            ${section.title ? `<div class="section-title">${section.title}</div>` : ''}
                            ${section.rows.map(row => `
                                <div class="list-item" data-id="${row.id}">
                                    <div class="item-description">${row.description || row.title}</div>
                                </div>
                            `).join('')}
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }

    // Debug log
    console.log('Formatted interactive result:', formattedHtml);

    // Debug log final HTML
    console.log('Generated HTML:', formattedHtml);

    return formattedHtml;
}

export function formatWhatsAppText(text) {
    if (!text) return '';

    // Debug log
    console.log('Formatting text:', text);

    // Handle WhatsApp markdown
    let formattedText = text
        // First handle double asterisks for italic
        .replace(/\*\*(.*?)\*\*/g, '<em>$1</em>')
        // Then handle single asterisks for bold with our gold color
        .replace(/\*(.*?)\*/g, '<strong>$1</strong>')
        // Other formatting
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
        if (messageText.startsWith('button:')) {
            // Handle button selections
            const buttonId = messageText.split(':')[1];
            message.interactive = {
                type: 'button_reply',
                button_reply: {
                    id: buttonId,
                    title: buttonId
                }
            };
        } else if (messageText.startsWith('list:')) {
            // Handle list selections
            const [_, selection] = messageText.split(':');
            message.interactive = {
                type: 'list_reply',
                list_reply: {
                    id: selection,
                    title: selection
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
