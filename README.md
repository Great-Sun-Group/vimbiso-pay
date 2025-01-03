# Vimbiso ChatServer

Facilitates transactions through the [credex-core](https://github.com/Great-Sun-Group/credex-core) API, enabling users to manage their credex accounts and perform financial operations directly in secure WhatsApp and SMS chats:
- Multi-denominational balance display
- Offer secured credex with settlement on demand
- Offer unsecured credex with configurable due date
- Accept/decline/cancel credex offers
- Account ledgers with pagination
- Multiple account management

## Core Architecture

The system follows these key principles:

1. **State-Based Design**
- All operations go through state_manager
- Credentials exist ONLY in state
- No direct passing of sensitive data
- State validation through updates
- Progress tracking through state
- Validation tracking through state

2. **Pure Functions**
- Services use stateless functions
- No stored instance variables
- No service-level state
- Clear input/output contracts
- Standard validation patterns
- Standard error handling

3. **Single Source of Truth**
- Member ID ONLY at top level
- Channel info ONLY at top level
- JWT token ONLY in state
- No credential duplication
- No state duplication
- No manual transformation

4. **Flow Framework**
- Common flow configurations
- Clear flow types
- Standard components
- Flow type metadata
- Progress tracking
- Validation tracking

For detailed implementation patterns, see:
- [Service Architecture](docs/service-architecture.md) - Core service patterns and best practices
- [API Integration](docs/api-integration.md) - API interaction patterns and state management
- [State Management](docs/state-management.md) - State validation and flow control

## Documentation
- [Standardization](docs/standardization.md) - Summary of centralized solution for state, flow, and error management.
- [State Management](docs/state-management.md) - Conversation and session management
- [Flow Framework](docs/flow-framework.md) - Progressive interaction framework
- [Components](docs/components.md) - UI components
- [WhatsApp Integration](docs/whatsapp.md) - WhatsApp bot implementation
- [API Integration](docs/api-integration.md) - Integration with credex-core API
- [Error Handling](docs/error-handling.md) - Testing infrastructure and tools
- [Testing Guide](docs/testing.md) - Testing infrastructure and tools
- [Security](docs/security.md) - Security measures and best practices
- [Docker](docs/docker.md) - Docker configuration and services
- [Deployment](docs/deployment.md) - Deployment process and infrastructure
- [Redis Management](docs/redis-memory-management.md) - Redis configuration and management

## Quick Start

### Development Environment
```bash
# Build and start services (combined command)
make dev

# Or use individual commands if needed:
make dev-build
make dev-up
make dev-down

# Access services (from host machine)
Application: http://localhost:8000
Mock WhatsApp: http://localhost:8001

# Note: Within Docker network, services communicate using:
- App service: http://app:8000
- Redis: redis://redis:6379
- Mock WhatsApp: http://mock:8001
```

### Production Environment
```bash
# Build and start services (combined command)
make prod

# Or use individual commands if needed:
make prod-build
make prod-up
make prod-down
```

### Fetching Logs
The `scripts/fetchlogs.sh` script allows you to fetch CloudWatch logs from the staging environment. It supports both real-time log streaming and historical log retrieval.

Requirements:
- AWS CLI installed
- AWS credentials configured with the following environment variables:
  ```bash
  export AWS_ACCESS_KEY_ID='your_access_key'
  export AWS_SECRET_ACCESS_KEY='your_secret_key'
  ```

Usage:
```bash
# Stream logs in real-time
fetchlogs

# Fetch historical logs in seconds
fetchlogs 60
```

## Core Features

### Service Layer
- State-based service architecture
- Pure function implementation
- Single source of truth enforcement
- Consistent error handling
- Clear service boundaries

### WhatsApp Interface
- Interactive menus and buttons
- Form-based data collection
- Rich message formatting
- State-based conversation flow
- Navigation commands
- Custom message templates

### API & Integration
- State-based API integration
- Credential extraction only when needed
- Flow state management
- Consistent error handling
- Direct integration with CredEx core API
- Comprehensive validation and error handling
- Type-safe request/response handling

### Security
- State-based credential management
- No credential duplication
- Flow state validation
- Consistent error handling
- JWT authentication
- Rate limiting
- Input validation
- Secure state management
- Webhook signature validation
- Request payload validation

## Development Tools

### Mock WhatsApp Interface
Test the WhatsApp chatserver without hitting WhastApp:

```bash
# Start all services including mock server
make dev

### API Testing
Test API endpoints and webhooks:

### AI-Assisted Merge Summaries
Generate diffs for AI-assisted summarization in merge requests:

```bash
make diff <source_branch> <target_branch>
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

Public domain.
