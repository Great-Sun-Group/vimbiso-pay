# VimbisoPay chatbot

The VimbisoPay chatbot is a Django-based application that integrates with WhatsApp Cloud API and the Credex Core API to provide members of the credex ecosystem access to their accounts.

## Features

- Webhook for handling incoming WhatsApp messages from members
- Support for various message types (text, button, interactive, location, image, document, video, audio, order)
- Welcome message management
- Cache management for user states
- Notification system for sending templated messages
- Integration with WhatsApp Cloud API

## Technologies Used

- Python 3.x
- Django 4.2.13
- Django Rest Framework
- Redis (for caching and session management)
- WhatsApp Cloud API
- Gunicorn (for production deployment)
- Docker and Docker Compose

## Project Structure

The project is organized as follows:

```
credex-bot/
├── .devcontainer/
│   └── devcontainer.json
├── app/
│   ├── bot/
│   │   ├── migrations/
│   │   ├── serializers/
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── constants.py
│   │   ├── models.py
│   │   ├── screens.py
│   │   ├── services.py
│   │   ├── tests.py
│   │   ├── utils.py
│   │   └── views.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── asgi.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── compose.yaml
│   ├── Dockerfile
│   ├── manage.py
│   ├── requirements.txt
│   └── start_app.sh
├── .dockerignore
├── .gitignore
├── generate_summary.py
├── LICENSE
├── nginx.conf
├── project_summary.txt
├── README.Docker.md
├── README.md
└── requirements.txt
```

## Development Setup

This project is configured to work with both GitHub Codespaces and local development using VS Code Dev Containers, providing a consistent development environment across different setups.

### Prerequisites

- [Docker](https://www.docker.com/get-started)
- [Visual Studio Code](https://code.visualstudio.com/)
- [Remote - Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) for VS Code

### Environment Variables

Before starting development, make sure to set up these environment variables:

1. `SECRET_KEY`: Generate a secure random string for Django's secret key.
2. `DEBUG`: Set to `True` for development, `False` for production.
3. `REDIS_URL`: Use `redis://redis:6379/` for both Codespaces and local development.
4. `WHATSAPP_ACCESS_TOKEN`: Obtain from the Meta Developer Portal.
5. `WHATSAPP_PHONE_NUMBER_ID`: Obtain from the Meta Developer Portal.
6. `WHATSAPP_BOT_API_KEY`: Generate this yourself.

To generate secure random strings for `SECRET_KEY` and `WHATSAPP_BOT_API_KEY`, you can use Python:

```python
import secrets
print(secrets.token_urlsafe(50))
```

For `WHATSAPP_ACCESS_TOKEN` and `WHATSAPP_PHONE_NUMBER_ID`, follow these steps:
1. Go to the [Meta Developer Portal](https://developers.facebook.com/).
2. Create a new app or select an existing one.
3. Add the WhatsApp product to your app.
4. Set up a Business Manager account if you haven't already.
5. In the WhatsApp settings:
   - Find your `WHATSAPP_PHONE_NUMBER_ID`
   - Generate a `WHATSAPP_ACCESS_TOKEN` (Permanent Access Token recommended for production)

### Setup Instructions

#### GitHub Codespaces

1. Open the project in GitHub Codespaces.
2. The development environment will be automatically set up based on the `.devcontainer/devcontainer.json` configuration.
3. Once the setup is complete, the development server should start automatically.

#### Local Development with VS Code Dev Containers

1. Clone the repository to your local machine.
2. Open the project folder in VS Code.
3. When prompted, click "Reopen in Container" or use the command palette (F1) and select "Remote-Containers: Reopen in Container".
4. VS Code will build the Docker container and set up the development environment.
5. Once the setup is complete, open a new terminal in VS Code and start the development server:
   ```
   python manage.py runserver 0.0.0.0:8000
   ```

### Accessing the Application

- In GitHub Codespaces: Click on the provided URL or use the "Ports" tab to find and open the running application.
- In local development: Open a web browser and navigate to `http://localhost:8000`.

## Usage

The Credex WhatsApp Bot handles incoming messages through a webhook and can send notifications using templates. To use the bot:

1. Ensure your webhook is properly configured in the Meta Developer Portal.
2. Use the `/bot/notify` endpoint to send templated notifications.
3. Manage welcome messages through the `/bot/welcome/message` endpoint.
4. Use `/bot/wipe` to clear the cache for specific users if needed.

## API Endpoints

- `/bot/webhook`: Handles incoming WhatsApp messages
- `/bot/notify`: Sends templated notifications
- `/bot/welcome/message`: Manages the welcome message
- `/bot/wipe`: Clears the cache for a specific user

## Configuration

The project uses Django's settings module for configuration. Key settings include:

- Database: SQLite (default)
- Caching: Redis
- REST Framework settings
- CORS configuration
- Logging (commented out in the provided settings)

## Contributing

1. Create a branch from the 'dev' branch.
2. Make your changes and commit them with clear, concise commit messages.
3. Push your changes and create a pull request against the 'dev' branch.
4. Follow the [Logging Best Practices](docs/logging_best_practices.md) when adding or modifying code.

## Deployment

1. Contributors branch from `dev` and complete work and testing on an issue, fix, or feature.
2. Contributor requests review from reviewer on merge to `dev` .
3. Reviewer tests and merges.
4. Dev is regularly merged with all recent commits to `stage`, which is auto-deployed to demo deployment.
5. Demo deployment is tested thoroughly in CI/CD pipeline.
6. When tests are passed, stage is merged to `prod`, which is auto-deployed to our production branch.
