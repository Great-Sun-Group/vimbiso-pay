# VimbisoPay

A WhatsApp bot service that facilitates financial transactions through the [credex-core](https://github.com/Great-Sun-Group/credex-core) API, enabling users to manage their credex accounts and perform financial operations directly in a secure WhatsApp chat.

## Documentation

### User Guide
- [User Flows](docs/flows/user-flows.md) - Detailed guide to all user interactions and flows

### Technical Documentation
- [API Integration](docs/technical/api-integration.md) - Integration with credex-core API
- [State Management](docs/technical/state-management.md) - Conversation and session management
- [Testing Guide](docs/technical/testing.md) - Testing infrastructure and tools
- [Security](docs/technical/security.md) - Security measures and best practices
- [Deployment](docs/deployment.md) - Deployment process and infrastructure
- [Redis Management](docs/redis-memory-management.md) - Redis configuration and management

## Quick Start

### Development Environment
```bash
# Build and start services
make dev-build
make dev-up

# Access services (from host machine)
Application: http://localhost:8000
Mock WhatsApp: http://localhost:8001

# Note: Within Docker network, services communicate using:
- App service: http://app:8000
- Redis: redis://redis:6379
- Mock WhatsApp: http://mock:8001

# Stop services
make dev-down
```

### Production Environment
```bash
# Build and start
make prod-build
make prod-up

# Stop services
make prod-down
```

## Core Features

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

### WhatsApp Interface
- Interactive menus and buttons
- Form-based data collection
- Rich message formatting
- State-based conversation flow
- Time-aware greetings
- Navigation commands
- Custom message templates

### Security
- JWT authentication
- Rate limiting
- Input validation
- Secure state management

## Development Tools

### Mock WhatsApp Interface
Test the WhatsApp bot without real WhatsApp credentials:

```bash
# Start all services including mock server
make dev-up

# Or start mock server separately
make mockery

# CLI testing (from host machine)
./mock/cli.py "Hello, world!"
./mock/cli.py --type button "button_1"
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

[License details here]
