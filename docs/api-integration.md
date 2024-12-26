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
            'validate_handle': {'path': 'getAccountByHandle'},
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
    """Authentication with minimal complexity"""

    def login(self, channel_identifier: str) -> Tuple[bool, Dict]:
        """Authenticate user"""
        response = self._make_request(
            'auth', 'login',
            payload={"phone": channel_identifier}
        )
        data = response.json()

        if token := self._extract_token(data):
            self._update_token(token)
            return True, data
        return False, {"message": "Login failed"}
```

### 2. Member Service
```python
class CredExMemberService(BaseCredExService):
    """Member operations with minimal state coupling"""

    def get_dashboard(self, phone: str) -> Tuple[bool, Dict]:
        """Get dashboard data"""
        response = self._make_request(
            'member', 'get_dashboard',
            payload={"phone": phone}
        )
        data = response.json()

        if dashboard := data.get("data", {}).get("dashboard"):
            self._update_state({"profile": {"dashboard": dashboard}})
            return True, data
        return False, {"message": "Failed to get dashboard"}
```

### 3. Offers Service
```python
class CredExOffersService(BaseCredExService):
    """Offer operations with helper methods"""

    def _process_offer_data(self, data: Dict) -> Dict:
        """Process offer data for API"""
        offer = data.copy()
        if "denomination" in offer:
            offer["Denomination"] = offer.pop("denomination")
        return offer

    def offer_credex(self, offer_data: Dict) -> Tuple[bool, Dict]:
        """Create new offer"""
        processed_data = self._process_offer_data(offer_data)
        response = self._make_request(
            'credex', 'create',
            payload=processed_data
        )
        data = response.json()

        if self._check_success(data, "CREDEX_CREATED"):
            return True, data
        return False, {"message": "Failed to create offer"}
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

### 2. Error Patterns
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

1. **Service Design**
   - Keep services focused
   - Use helper methods
   - Handle errors consistently
   - Maintain clear boundaries

2. **Token Management**
   - Centralize token updates
   - Use consistent patterns
   - Keep token flow clear
   - Handle errors properly

3. **Error Handling**
   - Use consistent patterns
   - Keep error handling simple
   - Provide clear messages
   - Log appropriately

4. **State Integration**
   - Minimize state coupling
   - Use clear update patterns
   - Follow SINGLE SOURCE OF TRUTH
   - Keep updates minimal

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
