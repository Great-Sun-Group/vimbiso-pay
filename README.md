# Vimbiso ChatServer

Facilitates transactions through the [credex-core](https://github.com/Great-Sun-Group/credex-core) API, enabling users to manage their credex accounts and perform financial operations directly in secure WhatsApp and SMS chats:
- Multi-denominational balance display
- Offer secured credex with settlement on demand
- Offer unsecured credex with configurable due date
- Accept/decline/cancel credex offers
- Account ledgers with pagination
- Multiple account management

## Core Architecture

The system is built around a central flow management system (`app/core/flow/headquarters.py`) that coordinates all operations through five core pillars:

```
core/flow/headquarters.py  <-- Central Flow Management
├── state/manager.py      (State Management)
├── components/           (Component System)
├── api/                  (API Integration)
└── messaging/            (Messaging System)
```

See [Core Architecture](docs/architecture.md) for detailed architectural principles and patterns.

### Core Pillars
- **Flow Management** ([Flow Framework](docs/flow-framework.md)) - Coordinates all operations through flow/headquarters.py
- **State Management** ([State Management](docs/state-manager.md)) - Single source of truth for all data
- **Component System** ([Components](docs/components.md)) - Self-contained operational units:
  * Display components for UI/messaging
  * Input components for validation
  * API components for external calls
  * Confirm components for user interaction
- **API Integration** ([Service & API](docs/api-services.md)) - External service communication
- **Messaging System** ([Messaging](docs/messaging.md)) - Channel-agnostic user interaction handling

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

### Flow Management
- Component activation and coordination
- State-based flow control
- Clear operational boundaries
- Standardized error handling
- Comprehensive validation

### Component System
- Self-contained operational units
- Clear responsibilities:
  * Display components for UI/messaging
  * Input components for validation
  * API components for external calls
  * Confirm components for user interaction
- Standard validation patterns
- Consistent error handling

### State Management
- Single source of truth
- Clear data boundaries
- Atomic operations
- Comprehensive validation
- Progress tracking

### API Integration
- State-based integration
- Secure credential management
- Comprehensive validation
- Type-safe handling
- Clear error patterns

### Messaging
- Channel-agnostic design
- Rich formatting
- Interactive elements
- Template system
- State-based flow

## Infrastructure
- [Security](docs/infrastructure/security.md) - Security measures and best practices
- [Docker](docs/infrastructure/docker.md) - Container configuration and services
- [Deployment](docs/infrastructure/deployment.md) - Deployment process and infrastructure
- [Redis](docs/infrastructure/redis-memory-management.md) - Redis configuration and management

## Development Tools

### Mock WhatsApp Interface
Test the WhatsApp chatserver without hitting WhatsApp:

```bash
# Start all services including mock server
make dev
```

### API Testing
Test API endpoints and webhooks using the mock server.

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
