# API Integration

## Overview

VimbisoPay integrates with external APIs using a simplified service architecture that emphasizes:
- Clear service boundaries
- Minimal complexity
- Consistent patterns
- Easy maintenance

## Core Services

### Base Configuration
```python
@dataclass
class CredExConfig:
    """Configuration for CredEx service"""
    base_url: str
    client_api_key: str
    default_headers: dict

    @classmethod
    def from_env(cls) -> "CredExConfig":
        """Create from environment"""
        return cls(
            base_url=config("MYCREDEX_APP_URL"),
            client_api_key=config("CLIENT_API_KEY"),
            default_headers={
                "Content-Type": "application/json",
                "x-client-api-key": config("CLIENT_API_KEY")
            }
        )
```

### Endpoint Management
```python
class CredExEndpoints:
    """CredEx API endpoints with logical grouping"""

    ENDPOINTS = {
        'auth': {
            'login': {'path': 'login', 'requires_auth': False},
            'register': {'path': 'onboardMember', 'requires_auth': False}
        },
        'member': {
            'validate_account_handle': {'path': 'getAccountByHandle'},
            'get_dashboard': {'path': 'getDashboard'}
        },
        'credex': {
            'create': {'path': 'createCredex'},
            'accept': {'path': 'acceptCredex'},
            'decline': {'path': 'declineCredex'},
            'get': {'path': 'getCredex'}
        }
    }

    @classmethod
    def get_path(cls, group: str, action: str) -> str:
        """Get endpoint path"""
        if group in cls.ENDPOINTS and action in cls.ENDPOINTS[group]:
            return cls.ENDPOINTS[group][action]['path']
        raise ValueError(f"Invalid endpoint: {group}/{action}")

    @classmethod
    def requires_auth(cls, group: str, action: str) -> bool:
        """Check if endpoint requires authentication"""
        if group in cls.ENDPOINTS and action in cls.ENDPOINTS[group]:
            return cls.ENDPOINTS[group][action].get('requires_auth', True)
        raise ValueError(f"Invalid endpoint: {group}/{action}")
```

### Base Service
```python
class BaseCredExService:
    """Base service with core functionality"""

    def _make_request(
        self,
        group: str,
        action: str,
        payload: Optional[Dict] = None
    ) -> requests.Response:
        """Make API request using endpoint groups"""
        path = CredExEndpoints.get_path(group, action)
        requires_auth = CredExEndpoints.requires_auth(group, action)

        url = self.config.get_url(path)
        headers = self.config.get_headers(
            self._jwt_token if requires_auth else None
        )

        return requests.request("POST", url, headers=headers, json=payload)
```

## Service Implementation

### 1. Authentication Service
```python
class CredExAuthService(BaseCredExService):
    """Authentication through state validation"""

    def login(self, state_manager: Any) -> None:
        """Authenticate user through state update

        Args:
            state_manager: State manager instance

        Raises:
            StateException: If authentication fails
        """
        # Let StateManager validate channel
        channel_id = state_manager.get("channel")["identifier"]  # ONLY at top level

        # Make API request (raises StateException if fails)
        response = self._make_request(
            'auth', 'login',
            payload={"phone": channel_id}
        )

        # Let StateManager validate and store token
        state_manager.update_state({
            "jwt_token": response.json()["token"]  # ONLY in state
        })
```

### 2. Member Service
```python
class CredExMemberService(BaseCredExService):
    """Member operations through state validation"""

    def get_dashboard(self, state_manager: Any) -> None:
        """Get dashboard data through state update

        Args:
            state_manager: State manager instance

        Raises:
            StateException: If dashboard fetch fails
        """
        # Let StateManager validate channel
        channel_id = state_manager.get("channel")["identifier"]  # ONLY at top level

        # Make API request (raises StateException if fails)
        response = self._make_request(
            'member', 'get_dashboard',
            payload={"phone": channel_id}
        )

        # Let StateManager validate and store dashboard
        state_manager.update_state({
            "flow_data": {
                "dashboard": response.json()["data"]["dashboard"]
            }
        })
```

### 3. Offers Service
```python
class CredExOffersService(BaseCredExService):
    """Offer operations through state validation"""

    def offer_credex(self, state_manager: Any) -> None:
        """Create offer through state update

        Args:
            state_manager: State manager instance

        Raises:
            StateException: If offer creation fails
        """
        # Let StateManager validate offer data
        offer_data = state_manager.get("flow_data")["input"]["offer"]

        # Make API request (raises StateException if fails)
        response = self._make_request(
            'credex', 'create',
            payload=offer_data
        )

        # Let StateManager validate and store response
        state_manager.update_state({
            "flow_data": {
                "offer": response.json()["data"]["offer"]
            }
        })
```

## Error Handling

### 1. Response Format
```python
{
    "error": "Error description",
    "details": {
        "field": "Error details"
    }
}
```

### 2. Error Handling
```python
def make_request(self, group: str, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Make API request with state validation

    Args:
        group: Endpoint group
        action: Endpoint action
        payload: Request payload

    Returns:
        API response data

    Raises:
        StateException: If request fails
    """
    # Make request (raises StateException if fails)
    response = self._make_request(group, action, payload)

    # Parse response (raises StateException if invalid)
    data = response.json()
    if not data.get("success"):
        raise StateException(f"API error: {data.get('message')}")

    return data
```

## Best Practices

1. **Service Design**
   - Let StateManager validate
   - NO manual validation
   - NO error recovery
   - NO state transformation

2. **Token Management**
   - JWT token ONLY in state
   - NO token duplication
   - NO manual validation
   - NO error recovery

3. **Error Handling**
   - Let StateManager validate
   - NO manual validation
   - NO error recovery
   - NO state fixing
   - Clear error messages
   - Log errors only

4. **State Integration**
   - Member ID ONLY at top level
   - Channel info ONLY at top level
   - NO state duplication
   - NO state transformation
   - NO state passing
   - NO manual validation

## Environment Setup
```bash
# Core API Configuration
MYCREDEX_APP_URL=https://api.example.com
CLIENT_API_KEY=your-api-key

# Redis Configuration
REDIS_URL=redis://redis-cache:6379/0
REDIS_STATE_URL=redis://redis-state:6379/0
```

For more details on:
- Service architecture: [Service Architecture](service-architecture.md)
- State management: [State Management](state-management.md)
- Flow framework: [Flow Framework](flow-framework.md)
