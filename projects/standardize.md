# WhatsApp Message Handling Standardization

## Overview
This project standardizes message handling across the codebase to follow consistent patterns and improve maintainability.

## Reference Files
Before starting implementation, review these files to understand current patterns:

1. Message Types and Handling:
   - app/core/messaging/types.py (Message type definitions)
   - app/services/whatsapp/types.py (WhatsAppMessage implementation)
   - app/core/messaging/templates.py (Current template patterns)

2. Flow Implementation:
   - app/core/messaging/flow.py (Flow framework)
   - app/services/whatsapp/handlers/member/flows.py (Example flow usage)
   - app/services/whatsapp/handlers/credex/flows.py (Example flow usage)

3. Template Organization:
   - app/services/whatsapp/screens.py (String templates)
   - app/core/messaging/templates.py (Message builders)

## Implementation Plan

### Phase 1: Service Layer Organization

1. Define Service Boundaries:
   ```python
   # WhatsAppMessagingService: Raw API communication
   class WhatsAppMessagingService:
       def _send_message(self, message: Message)
       def get_template(self, template_name: str)
       def send_template(self, recipient, template_name, language)

   # WhatsAppMessage: Message formatting
   class WhatsAppMessage:
       def create_text(to: str, text: str)
       def create_button(to: str, text: str, buttons: list)
       def create_list(to: str, text: str, sections: list)
   ```

2. Document Service Integration:
   - WhatsAppMessagingService for API calls
   - WhatsAppMessage for message creation
   - Flow framework for interaction logic
   - Template system for content

### Phase 2: Message Format Standardization

1. Update ButtonSelection in templates.py:
   ```python
   @staticmethod
   def create_buttons(params: Dict[str, Any], recipient: str) -> Message:
       """Create button selection message"""
       buttons = [
           Button(id=button["id"], title=button["title"])
           for button in params["buttons"][:3]
       ]

       return Message(
           recipient=MessageRecipient(phone_number=recipient),
           content=InteractiveContent(
               interactive_type=InteractiveType.BUTTON,
               body=params["text"],
               buttons=buttons,
               header=params.get("header"),
               footer=params.get("footer")
           )
       )
   ```

2. Update all template classes to use Message objects consistently

### Phase 2: Template Organization

1. Reorganize template responsibilities:
   - screens.py: String templates only
   - templates.py: Core message builders
   - Flow-specific messages: Move to respective flows

2. Update imports and references:
   - Remove duplicate message creation
   - Use template hierarchy consistently

### Phase 3: Flow Enhancement

1. Update flow message handling:
   - Use WhatsAppMessage consistently
   - Standardize state updates
   - Document patterns

2. Standardize flow completion:
   - Consistent error handling
   - State preservation
   - Response formatting

## Testing Strategy

1. Message Format Tests:
   - Verify WhatsApp Cloud API compliance
   - Check character limits
   - Validate button/list constraints

2. Flow Tests:
   - Test state preservation
   - Verify error handling
   - Check message formatting

3. Integration Tests:
   - Test complete flows
   - Verify state updates
   - Check template rendering

## Documentation Updates

1. Update flow-framework.md:
   - Add architectural patterns section
   - Document state management
   - Clarify message handling
   - Add service integration

2. Update whatsapp.md:
   - Document template hierarchy
   - Clarify message formats
   - Add best practices
   - Document service layer

3. Add service-architecture.md:
   - Document service boundaries
   - Explain integration patterns
   - Define responsibilities
   - Show message flow

## Success Criteria

1. Code Standards:
   - All message creation uses WhatsAppMessage
   - Clear template hierarchy
   - Consistent flow patterns

2. Documentation:
   - Clear architectural guidelines
   - Updated examples
   - Documented patterns

3. Testing:
   - All tests pass
   - Coverage maintained
   - No regressions

## Timeline
- Phase 1: 1 day
- Phase 2: 1 day
- Phase 3: 1 day
- Testing: 1 day
- Documentation: 1 day

Total: 5 days

## Risks and Mitigation

1. Risk: Breaking existing flows
   - Mitigation: Comprehensive testing
   - Fallback: Staged rollout

2. Risk: Performance impact
   - Mitigation: Profile changes
   - Fallback: Optimize critical paths

3. Risk: State corruption
   - Mitigation: Validate state updates
   - Fallback: State recovery
