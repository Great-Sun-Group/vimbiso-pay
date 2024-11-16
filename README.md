# Vimbiso Pay

A WhatsApp-based client application that interacts with the Credex Core API.

## Local Development Setup

### Prerequisites
- Docker and Docker Compose
- VSCode with Remote Containers extension (for devcontainer usage)
- Access to dev.mycredex.dev API
- WhatsApp API credentials

### Environment Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and fill in the required values:
   ```bash
   cp .env.example .env
   ```

   Required environment variables:
   - `DJANGO_SECRET`: Django secret key
   - `MYCREDEX_APP_URL`: Set to `https://dev.mycredex.dev/` for development
   - `WHATSAPP_BOT_API_KEY`: Must match the value used in credex-core
   - `WHATSAPP_API_URL`: WhatsApp Graph API URL
   - `WHATSAPP_ACCESS_TOKEN`: Your WhatsApp API access token
   - `WHATSAPP_PHONE_NUMBER_ID`: Your WhatsApp phone number ID

### Development with VSCode Devcontainer

1. Open the project in VSCode
2. When prompted, click "Reopen in Container" or run the command palette (F1) and select "Remote-Containers: Reopen in Container"
3. VSCode will build and start the development container with all required extensions and dependencies

### Manual Development Setup

If not using devcontainer:

1. Build and start the services:
   ```bash
   docker compose -f app/compose.yaml up --build
   ```

2. The application will be available at http://localhost:8000

### Verifying Development Setup

The application provides test endpoints to verify all integrations are working correctly:

1. Basic Health Check:
   ```bash
   curl http://localhost:8000/health/
   ```
   Should return "OK"

2. Integration Tests:
   ```bash
   curl http://localhost:8000/api/test-integrations/
   ```
   This endpoint tests:
   - Django setup
   - Redis connection
   - Credex Core API connectivity
   - WhatsApp API configuration

   The response will include the status of each component:
   ```json
   {
     "status": "success",
     "tests": {
       "django": { "status": "success", "message": "..." },
       "redis": { "status": "success", "message": "..." },
       "credex_api": { "status": "success", "message": "..." },
       "whatsapp": { "status": "success", "message": "..." }
     }
   }
   ```

### Development Workflow

- The application runs in development mode with live reload enabled
- Code changes will automatically reload the development server
- Redis is available at localhost:6379
- API requests will be forwarded to dev.mycredex.dev
- WhatsApp messages can be tested using the configured WhatsApp number

### Health Checks

- Application health check: http://localhost:8000/health/
- Redis health is monitored automatically
- Integration status: http://localhost:8000/api/test-integrations/

### Deployment

For deployment instructions, see [README.Docker.md](README.Docker.md)

## GitHub Codespaces Development

### Codespaces Setup

1. Open the repository in GitHub Codespaces
2. The devcontainer configuration will automatically set up your development environment

### Environment Configuration for Codespaces

When working in Codespaces, you need to set up environment variables:

1. Create a `.env` file from template:
   ```bash
   cp .env.example .env
   ```

2. Required Codespaces-specific configuration:
   - `X_GITHUB_TOKEN`: Required for API access from Codespaces
     - Generate a Personal Access Token in GitHub with appropriate scopes
     - This token is needed for authentication when making requests to dev.mycredex.dev
     - Without this token, API requests from Codespaces will be blocked

3. Set Codespaces Secrets:
   - Go to GitHub Repository Settings
   - Navigate to Secrets and Variables > Codespaces
   - Add the following secrets:
     - `X_GITHUB_TOKEN`
     - Other environment variables from `.env.example`

### Testing in Codespaces

When testing API endpoints in Codespaces, ensure:

1. The `X_GITHUB_TOKEN` is properly set in your environment
2. Include the token in API requests:
   ```bash
   # Using curl
   curl -H "X-Github-Token: $X_GITHUB_TOKEN" http://localhost:8000/api/test-integrations/
   
   # Using the test endpoint
   # The test endpoint automatically includes the token if ENV=dev
   ```

### Codespaces Development Workflow

1. Start the application:
   ```bash
   docker compose -f app/compose.yaml up --build
   ```

2. Access the application through the Codespaces forwarded ports
   - Codespaces automatically forwards port 8000
   - Use the Codespaces URL provided in the ports tab

3. For API testing:
   - Always include `X-Github-Token` header in requests
   - Use the test endpoints to verify connectivity
   - Monitor the Django debug toolbar for request details

## Architecture

### Components
- Django application with WhatsApp integration
- Redis for caching and message handling
- Connection to Credex Core API

### Environment Structure
- Development: Local development with dev.mycredex.dev API
- Staging: (configured in terraform)
- Production: (configured in terraform)

## Contributing

1. Create a feature branch
2. Make your changes
3. Submit a pull request

## Troubleshooting

### Common Issues

1. API Connection Issues
   - Verify MYCREDEX_APP_URL is set correctly
   - Check if dev.mycredex.dev is accessible
   - In Codespaces: Verify X_GITHUB_TOKEN is set and valid
   - Use /api/test-integrations/ to verify connectivity

2. WhatsApp Integration
   - Ensure all WhatsApp environment variables are set
   - Verify WHATSAPP_BOT_API_KEY matches credex-core
   - Check WhatsApp configuration via /api/test-integrations/

3. Redis Connection
   - Check if Redis container is running
   - Verify REDIS_URL in environment
   - Use /api/test-integrations/ to test Redis connection

4. Codespaces-Specific Issues
   - Missing X_GITHUB_TOKEN: API requests will fail
   - Port forwarding: Check Ports tab in Codespaces
   - Environment variables: Verify they're set in Codespaces secrets

### Debug Mode

The application runs in debug mode during development, providing:
- Django Debug Toolbar at /__debug__/
- Detailed error pages
- Auto-reload on code changes
