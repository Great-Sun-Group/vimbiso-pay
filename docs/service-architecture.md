# Service Architecture

## Overview

VimbisoPay uses a simplified service architecture that emphasizes:
- Clear service boundaries
- SINGLE SOURCE OF TRUTH
- Minimal complexity
- Easy maintenance

## Core Services

### 1. Base Service
```python
class BaseCredExService:
    """Base service with core functionality"""

    def _make_request(self, group: str, action: str, payload: Optional[Dict] = None):
        """Make API request using endpoint groups"""
        path = CredExEndpoints.get_path(group, action)
        requires_auth = CredExEndpoints.requires_auth(group, action)

        # Build and execute request with proper auth
        url = self.config.get_url(path)
        headers = self.config.get_headers(self._jwt_token if requires_auth else None)
        return requests.request(method, url, headers=headers, json=payload)
```

Features:
- Simplified request handling
- Clear error patterns
- Consistent token usage
- Logical endpoint grouping

### 2. Auth Service
```python
class CredExAuthService(BaseCredExService):
    """Authentication service with minimal state coupling"""

    def login(self, channel_identifier: str) -> Tuple[bool, Dict]:
        """Authenticate user"""
        response = self._make_request('auth', 'login',
            payload={"phone": channel_identifier})

        if token := self._extract_token(data):
            self._update_token(token)
            return True, data
        return False, {"message": "Login failed"}
```

Features:
- Focused authentication
- Clear token handling
- Simple error handling
- Minimal state coupling

### 3. Member Service
```python
class CredExMemberService(BaseCredExService):
    """Member operations with minimal complexity"""

    def get_dashboard(self, phone: str) -> Tuple[bool, Dict]:
        """Get dashboard data"""
        response = self._make_request('member', 'get_dashboard',
            payload={"phone": phone})

        if dashboard := response.json().get("data", {}).get("dashboard"):
            self._update_state({"profile": {"dashboard": dashboard}})
            return True, response.json()
        return False, {"message": "Failed to get dashboard"}
```

Features:
- Simple state updates
- Clear success patterns
- Focused operations
- Minimal error handling

### 4. Offers Service
```python
class CredExOffersService(BaseCredExService):
    """Offer operations with helper methods"""

    def _process_offer_data(self, data: Dict) -> Dict:
        """Process offer data for API compatibility"""
        offer = data.copy()
        if "denomination" in offer:
            offer["Denomination"] = offer.pop("denomination")
        return offer

    def offer_credex(self, offer_data: Dict) -> Tuple[bool, Dict]:
        """Create new offer"""
        processed_data = self._process_offer_data(offer_data)
        response = self._make_request('credex', 'create',
            payload=processed_data)

        if self._check_success(response.json(), "CREDEX_CREATED"):
            return True, response.json()
        return False, {"message": "Failed to create offer"}
```

Features:
- Helper methods for common tasks
- Clear data processing
- Simple success checks
- Consistent error handling

## Integration Patterns

### 1. State Management
```python
# State as SINGLE SOURCE OF TRUTH
state = {
    "member_id": id,     # Primary identifier
    "channel": {         # Channel information
        "type": type,
        "identifier": id
    },
    "jwt_token": token,  # Authentication
    "flow_data": {}      # Flow state
}
```

### 2. Token Management
```python
def _update_token(self, token: str) -> None:
    """Update token in services and state"""
    # Update service token
    self._jwt_token = token

    # Update state if available
    if self.state_manager:
        self.state_manager.update_state({"jwt_token": token})
```

### 3. Error Handling
```python
try:
    response = self._make_request(group, action, payload)
    data = response.json()

    if self._check_success(data, expected_type):
        return True, data
    return False, {"message": f"Failed to {action}"}

except Exception as e:
    logger.error(f"{action} failed: {str(e)}")
    return False, {"message": str(e)}
```

## Best Practices

1. Service Design
   - Keep services focused
   - Use helper methods
   - Handle errors consistently
   - Maintain clear boundaries

2. State Management
   - Use state as SINGLE SOURCE OF TRUTH
   - Minimize state coupling
   - Keep state updates simple
   - Use clear update patterns

3. Token Handling
   - Centralize token updates
   - Use consistent patterns
   - Keep token flow clear
   - Handle errors properly

4. Error Management
   - Use consistent patterns
   - Keep error handling simple
   - Provide clear messages
   - Log appropriately

For more details on:
- State management: [State Management](state-management.md)
- API integration: [API Integration](api-integration.md)
- Flow framework: [Flow Framework](flow-framework.md)
