# VimbisoPay

A WhatsApp bot service that facilitates financial transactions through the [credex-core](https://github.com/Great-Sun-Group/credex-core) API, enabling users to manage their credex accounts and perform financial operations directly in a secure WhatsApp chat.

## Documentation

### User Guide
- [User Flows](docs/flows/user-flows.md) - Detailed guide to all user interactions and flows

### Technical Documentation
- [Flow Framework](docs/technical/flow-framework.md) - Progressive interaction framework
- [WhatsApp Integration](docs/technical/whatsapp.md) - WhatsApp bot implementation
- [API Integration](docs/technical/api-integration.md) - Integration with credex-core API
- [State Management](docs/technical/state-management.md) - Conversation and session management
- [Testing Guide](docs/technical/testing.md) - Testing infrastructure and tools
- [Security](docs/technical/security.md) - Security measures and best practices
- [Docker](docs/technical/docker.md) - Docker configuration and services
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
./scripts/fetchlogs.sh

# Fetch historical logs in seconds
./scripts/fetchlogs.sh 60

# Show help
./scripts/fetchlogs.sh --help
```

## Core Features

### WhatsApp Interface
- Interactive menus and buttons
- Form-based data collection
- Rich message formatting
- State-based conversation flow
- Time-aware greetings
- Navigation commands
- Custom message templates

### Financial Operations
- Secured credex transactions with immediate settlement
- Unsecured credex with configurable due dates
- Multi-tier account system:
  - Personal accounts with basic features
  - Business accounts with advanced capabilities
  - Member authorization management
- Balance tracking with denomination support
- Transaction history with pagination
- Pending offers management

### API & Integration
- Direct integration with CredEx core API
- Webhook support for real-time updates:
  - Company updates
  - Member updates
  - Offer status changes
- Internal API endpoints for:
  - Company management
  - Member operations
  - Offer handling
- Comprehensive validation and error handling
- Type-safe request/response handling

### Security
- JWT authentication
- Rate limiting
- Input validation
- Secure state management
- Webhook signature validation
- Request payload validation

## Development Tools

### Mock WhatsApp Interface
Test the WhatsApp bot without real WhatsApp credentials:

```bash
# Start all services including mock server
make dev

# CLI testing (from host machine)
./mock/cli.py "Hello, world!"
./mock/cli.py --type button "button_1"
```

### API Testing
Test API endpoints and webhooks:

```bash
# Test webhook endpoint
curl -X POST http://localhost:8000/api/webhooks/ \
  -H "Content-Type: application/json" \
  -d '{
    "metadata": {
      "webhook_id": "test",
      "event_type": "company_update",
      "timestamp": "2024-01-01T00:00:00Z"
    },
    "payload": {
      "company_id": "123",
      "name": "Test Company",
      "status": "active"
    }
  }'

# Test internal API (requires authentication)
curl -X GET http://localhost:8000/api/companies/ \
  -H "Authorization: Bearer your-token"
```

### AI-Assisted Merge Summaries
Generate branch comparison summaries:

```bash
make diff <source_branch> <target_branch>
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

Have at it.
