# Service Architecture

## Overview

VimbisoPay's WhatsApp integration uses a layered service architecture to separate concerns:
- API Communication
- Message Formatting
- Flow Management
- Template System

## Service Layers

### 1. WhatsApp API Layer (WhatsAppMessagingService)

Handles raw API communication with WhatsApp Cloud API:
```python
class WhatsAppMessagingService:
    """WhatsApp-specific implementation of messaging service"""

    def _send_message(self, message: Message):
        """Send message via WhatsApp API"""

    def get_template(self, template_name: str):
        """Get WhatsApp message template"""

    def send_template(self, recipient, template_name, language):
        """Send a template message"""
```

Responsibilities:
- API authentication
- Message delivery
- Template management
- Status tracking
- Error handling

### 2. Message Formatting Layer (WhatsAppMessage)

Handles message creation and formatting:
```python
class WhatsAppMessage:
    """WhatsApp message formatting utilities"""

    @classmethod
    def create_text(cls, to: str, text: str):
        """Create text message"""

    @classmethod
    def create_button(cls, to: str, text: str, buttons: list):
        """Create button message"""

    @classmethod
    def create_list(cls, to: str, text: str, sections: list):
        """Create list message"""
```

Responsibilities:
- Message format validation
- WhatsApp Cloud API compliance
- Character limit enforcement
- Message type handling

### 3. Flow Management Layer (Flow Framework)

Handles conversation flow and state:
```python
class Flow:
    """Base class for all flows"""

    def process_input(self, input_data: Any):
        """Process input and manage state"""

    def complete(self):
        """Complete flow with proper response"""
```

Responsibilities:
- Step progression
- Input validation
- State management
- Error recovery

### 4. Template System

Organized in three layers:

1. String Templates (screens.py):
```python
BALANCE = """*💰 SECURED BALANCES*
{securedNetBalancesByDenom}"""
```
- Basic text templates
- Format strings only

2. Message Builders (templates.py):
```python
class ProgressiveInput:
    def create_prompt(text: str, examples: List[str]):
        """Create formatted prompt"""
```
- Common message patterns
- Reusable components

3. Flow Messages (in flows):
```python
def _create_confirmation(self, state: Dict[str, Any]):
    """Create flow-specific message"""
```
- Flow-specific formatting
- State-aware messages

## Integration Patterns

### 1. Message Flow
```
Flow Framework
    ↓
Message Formatting (WhatsAppMessage)
    ↓
Template System
    ↓
API Communication (WhatsAppMessagingService)
    ↓
WhatsApp Cloud API
```

### 2. State Management
```
Flow Framework (member_id ONLY at top level)
    ↓
Redis State Service (preserves single source of truth)
    ↓
State Validation (enforces member_id at top level)
    ↓
Profile Preservation (maintains member context)
```

### 3. Error Handling
```
API Layer → Service Exceptions
    ↓
Flow Layer → State Recovery
    ↓
Message Layer → User Feedback
```

## Best Practices

1. Service Boundaries
   - Use appropriate layer for each operation
   - Maintain clear responsibilities
   - Follow established patterns
   - Document integration points

2. Message Creation
   - Use WhatsAppMessage for all messages
   - Validate formats before sending
   - Handle all message types
   - Follow Cloud API specs

3. Flow Integration
   - Use Flow framework for conversations
   - Manage state properly
   - Handle errors consistently
   - Document flow patterns

4. Template Usage
   - Use appropriate template layer
   - Keep templates focused
   - Follow formatting standards
   - Document template purpose

## Monitoring and Maintenance

1. API Monitoring
   - Track message delivery
   - Monitor rate limits
   - Log API errors
   - Track template usage

2. Flow Monitoring
   - Track completion rates
   - Monitor state changes
   - Log validation errors
   - Track user progress

3. Performance Metrics
   - Message latency
   - State operations
   - Template rendering
   - Error rates

For more details on:
- Flow framework: [Flow Framework](flow-framework.md)
- WhatsApp integration: [WhatsApp](whatsapp.md)
- State management: [State Management](state-management.md)
