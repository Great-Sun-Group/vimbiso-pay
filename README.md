# VimbisoPay

A WhatsApp bot service that facilitates financial transactions through the [credex-core](https://github.com/Great-Sun-Group/credex-core) API, enabling users to manage their credex accounts and perform financial operations directly in a secure WhatsApp chat.

### Quick Start
After cloning and setting up environment variables, or activation of a codespace, start development environment with:
```bash
make up
```

The application will be available at http://localhost:8000

## Core Features

### Financial Operations
- Secured credex transactions with immediate settlement
- Unsecured credex with configurable due dates (up to 5 weeks)
- Multi-tier account system:
  - Personal accounts with basic features
  - Business accounts with advanced capabilities
  - Member authorization management
- Balance tracking with denomination support
- Transaction history with pagination
- Pending offers management:
  - Individual and bulk acceptance
  - Offer cancellation
  - Review of incoming/outgoing offers

### Transaction Commands
- Quick transaction shortcuts:
  - `0.5=>handle` for secured CredEx
  - `0.5->handle` for unsecured CredEx
  - `0.5->handle=2024-02-01` for dated unsecured CredEx
- Menu-based transaction creation
- Bulk transaction handling
- Transaction validation and confirmation

### WhatsApp Interface
- Interactive menus and buttons
- Form-based data collection with validation
- Rich message formatting with emojis
- State-based conversation flow with Redis persistence:
  - 5-minute session timeout
  - Automatic state cleanup
  - Cross-device state sync
- Time-aware greetings and messages
- Navigation commands:
  - `menu` - Return to main menu
  - `x` or `c` - Cancel current operation
  - `home` - Return to account dashboard
- Custom message templates for:
  - Account balances and limits
  - Transaction history
  - Offer confirmations
  - Error messages
  - Status updates
- Notification preferences per account

### Security
- JWT authentication with configurable lifetimes
- Rate limiting (100/day anonymous, 1000/day authenticated)
- XSS protection and HSTS
- CORS configuration
- Input validation and sanitization
- Secure state management

## Development Setup

### Prerequisites
- Docker and Docker Compose
- Python 3.10+
- Access to Credex Core API
- WhatsApp Business API credentials

### Development Features
- Live code reloading
- Django Debug Toolbar
- SQLite database
- Redis for state management
- Console email backend
- Comprehensive logging

### Code Quality
```bash
# Format and lint
black .
isort .
flake8

# Type checking
mypy .

# Run tests
pytest --cov=app
```

## Production Deployment

### Docker Configuration
- Multi-stage builds
- Security-hardened production image
- Non-privileged user
- Gunicorn with gevent workers
- Health monitoring

### Server Configuration
```bash
# Build production image
docker build --target production -t vimbiso-pay:latest .

# Run with production settings
docker run -d \
  --name vimbiso-pay \
  -p 8000:8000 \
  -e DJANGO_ENV=production \
  [additional environment variables]
  vimbiso-pay:latest
```

### Health Monitoring
- Built-in health checks (30s interval)
- Redis connection monitoring
- API integration verification
- Comprehensive logging

## Troubleshooting

### Common Issues
1. API Connection
   - Verify API URL and credentials
   - Check network connectivity
   - Validate JWT token

2. WhatsApp Integration
   - Verify API credentials
   - Test webhook configuration
   - Check message templates

3. State Management
   - Verify Redis connection
   - Check session timeouts (5 minutes)
   - Monitor state transitions

### Debug Mode
- Django Debug Toolbar at /__debug__/
- Detailed error pages
- Auto-reload on code changes
- Console email backend
- Comprehensive logging

## Future Improvements

1. Monitoring
   - JSON logging configuration
   - Error tracking
   - Performance metrics

2. Performance
   - Redis caching strategy
   - Container optimization
   - State management tuning

3. Infrastructure
   - AWS deployment
   - Terraform configurations
   - Production deployment guide
