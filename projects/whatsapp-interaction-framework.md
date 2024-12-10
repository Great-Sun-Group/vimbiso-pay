# WhatsApp Interaction Framework

## Overview
A reusable framework for building smart, progressive interactions in WhatsApp that integrates with existing state management and uses only officially supported message types.

## Core Components

### 1. Flow Management
```typescript
interface Flow {
  id: string;
  steps: Step[];
  state: FlowState;

  // Maps to existing StateService
  currentStage: string;
  previousStage: string;

  // Navigation
  next(): Step;
  back(): Step;

  // State integration
  toStateData(): {
    stage: string;
    option: string;
    data: Record<string, any>;
  };
}

interface Step {
  id: string;
  type: StepType;
  stage: string;  // Maps to StateStage
  message: WhatsAppMessage;
  validation?: (input: any) => boolean;
  transform?: (input: any) => any;
}

enum StepType {
  TEXT_INPUT = 'text_input',      // Free text input
  LIST_SELECT = 'list_select',    // List of options
  BUTTON_SELECT = 'button_select' // Quick reply buttons
}
```

### 2. Message Templates
```typescript
// Replace form with progressive steps
interface ProgressiveInput {
  // Initial prompt with examples
  createPrompt(text: string, examples: string[]): WhatsAppMessage;

  // Validation response
  createValidationError(error: string): WhatsAppMessage;

  // Value confirmation
  createConfirmation(value: any): WhatsAppMessage & {
    buttons: [
      { id: 'confirm', title: 'Confirm' },
      { id: 'retry', title: 'Try Again' }
    ]
  };
}

// List selection with sections
interface ListSelection {
  createList(params: {
    title: string;
    sections: {
      title: string;
      items: Array<{
        id: string;
        title: string;
        description?: string;
      }>;
    }[];
    button?: string;
  }): WhatsAppMessage;
}

// Quick reply buttons
interface ButtonSelection {
  createButtons(params: {
    text: string;
    buttons: Array<{
      id: string;
      title: string;
    }>;
  }): WhatsAppMessage;
}
```

### 3. State Integration
```typescript
class FlowStateManager {
  constructor(private stateService: StateService) {}

  // Load/save flow state
  async loadFlowState(userId: string, flow: Flow): Promise<void>;
  async saveFlowState(userId: string, flow: Flow): Promise<void>;

  // Handle step transitions
  async completeStep(userId: string, flow: Flow, step: Step, input: any): Promise<void>;
  async startStep(userId: string, flow: Flow, step: Step): Promise<void>;
}
```

## Example: Converting Form to Progressive Flow

### Current Form Approach:
```typescript
// Single form message
const formMessage = {
  type: "interactive",
  interactive: {
    type: "nfm",
    body: { text: "Enter amount and recipient:" },
    action: {
      name: "credex_offer_form",
      parameters: {
        fields: [
          { name: "amount", label: "Amount" },
          { name: "recipientAccountHandle", label: "Recipient" }
        ]
      }
    }
  }
};
```

### New Progressive Approach:
```typescript
const credexFlow = new Flow({
  id: 'credex_offer',
  steps: [
    // Step 1: Amount Input
    {
      id: 'amount',
      type: StepType.TEXT_INPUT,
      stage: FlowStages.FLOW_INPUT,
      message: new ProgressiveInput()
        .createPrompt(
          "Enter amount in USD or specify denomination:",
          [
            "100 (USD)",
            "ZWG 100",
            "XAU 1"
          ]
        ),
      validation: validateAmount,
      transform: parseAmount
    },

    // Step 2: Recipient Selection
    {
      id: 'recipient',
      type: StepType.LIST_SELECT,
      stage: FlowStages.FLOW_SELECT,
      message: new ListSelection()
        .createList({
          title: "Select Recipient",
          sections: [
            {
              title: "Recent",
              items: getRecentRecipients()
            },
            {
              title: "Options",
              items: [
                { id: "new", title: "New Recipient" }
              ]
            }
          ]
        })
    },

    // Step 3: New Recipient Input (conditional)
    {
      id: 'new_recipient',
      type: StepType.TEXT_INPUT,
      stage: FlowStages.FLOW_INPUT,
      condition: (state) => state.recipientChoice === 'new',
      message: new ProgressiveInput()
        .createPrompt(
          "Enter recipient's handle:",
          ["@username"]
        ),
      validation: validateHandle
    },

    // Step 4: Confirmation
    {
      id: 'confirm',
      type: StepType.BUTTON_SELECT,
      stage: FlowStages.FLOW_CONFIRM,
      message: new ButtonSelection()
        .createButtons({
          text: "Send {{amount}} to {{recipient}}?",
          buttons: [
            { id: "confirm", title: "Confirm" },
            { id: "cancel", title: "Cancel" }
          ]
        })
    }
  ]
});
```

### Message Handler Integration
```typescript
class WhatsAppFlowHandler {
  constructor(
    private flowStateManager: FlowStateManager,
    private stateService: StateService
  ) {}

  async handleMessage(message: WhatsAppMessage): Promise<void> {
    // Get current flow from state
    const state = await this.stateService.get_state(message.user);
    const flow = this.getFlowForState(state);

    if (!flow) {
      return this.handleNonFlowMessage(message);
    }

    // Load flow state
    await this.flowStateManager.loadFlowState(message.user, flow);

    try {
      const currentStep = flow.getCurrentStep();

      // Process input based on step type
      let input;
      switch (currentStep.type) {
        case StepType.TEXT_INPUT:
          input = await this.handleTextInput(message, currentStep);
          break;
        case StepType.LIST_SELECT:
          input = await this.handleListSelection(message, currentStep);
          break;
        case StepType.BUTTON_SELECT:
          input = await this.handleButtonSelection(message, currentStep);
          break;
      }

      // Validate input
      if (currentStep.validation && !currentStep.validation(input)) {
        return this.sendValidationError(currentStep, message.user);
      }

      // Complete step and get next
      await this.flowStateManager.completeStep(message.user, flow, currentStep, input);
      const nextStep = flow.next();

      if (nextStep) {
        // Start next step
        await this.flowStateManager.startStep(message.user, flow, nextStep);
        await this.sendMessage(nextStep.message);
      } else {
        // Flow complete
        await this.completeFlow(flow, message.user);
      }

    } catch (error) {
      await this.handleFlowError(error, flow, message.user);
    }
  }
}
```

## Implementation Strategy

### Phase 1: Core Flow Engine
1. Flow State Management
   - Integrate with existing StateService
   - Handle step transitions
   - Manage flow data

2. Message Templates
   - Text input with validation
   - List selection
   - Button confirmation

3. Basic Flows
   - Convert registration form
   - Test with simple flows

### Phase 2: Enhanced Features
1. Flow Navigation
   - Back/edit support
   - Skip logic
   - Conditional steps

2. Input Handling
   - Rich validation
   - Format helpers
   - Error recovery

3. State Management
   - Progress tracking
   - Data persistence
   - Error states

### Phase 3: Smart Features
1. Flow Optimization
   - Quick paths
   - Shortcuts
   - Default values

2. Context Awareness
   - User preferences
   - History integration
   - Smart suggestions

## Next Steps

1. Create Basic Templates
   - Text input prompts
   - List selection
   - Button messages

2. Build Flow Engine
   - State integration
   - Step handling
   - Navigation

3. Convert Simple Flow
   - Registration flow
   - Test end-to-end
   - Validate approach
