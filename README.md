# Vimbiso ChatServer

Facilitates transactions through the [credex-core](https://github.com/Great-Sun-Group/credex-core) API, enabling users to manage their credex accounts and perform financial operations directly in secure WhatsApp and SMS chats:
- Login and member onboarding
- Account dashboard with multi-denominational balance display
- Offer secured credex
- Accept/decline/cancel credex offers
- Account ledgers with pagination
- View credex
- Upgrade member tier

## Core Architecture

See [Core Architecture](docs/architecture.md) for detailed architectural principles and patterns. The system is built around a central flow headquarters that coordinates operations as one of five core pillars:

- [Flow Headquarters:](docs/flow-headquarters.md) Coordinates operations
- [State Manager:](docs/state-manager.md) Source of truth for data
- [Components:](docs/components.md) Self-contained operational units for display, input, API, and confirm component types
- [API Services:](docs/api-services.md) Service communication with credex-core API
- [Messaging System:](docs/messaging.md) Channel-agnostic user interaction handling with WhatsApp and SMS (coming) implementations

## Infrastructure
- [Security](docs/infrastructure/security.md) - Security measures and best practices
- [Docker](docs/infrastructure/docker.md) - Container configuration and services
- [Deployment](docs/infrastructure/deployment.md) - Deployment process and infrastructure
- [Redis](docs/infrastructure/redis-memory-management.md) - Redis configuration and management

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
