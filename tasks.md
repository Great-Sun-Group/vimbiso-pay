# Work Plan for Updating Dev Environment

## 1. Review and Update Docker Configuration
- [x] Check existing Dockerfile and compose.yaml
- [x] Update Dockerfile if necessary
- [x] Update compose.yaml if necessary
- [ ] Rebuild container and test

## 2. Set Up Environment Variables
- [ ] Create a .env file for local development
- [ ] Update .gitignore to exclude .env file
- [ ] Add environment variables as mentioned in README
  - [ ] SECRET_KEY
  - [ ] DEBUG
  - [ ] REDIS_URL
  - [ ] WHATSAPP_ACCESS_TOKEN
  - [ ] WHATSAPP_PHONE_NUMBER_ID
  - [ ] WHATSAPP_BOT_API_KEY
- [x] Update Docker configuration to use .env file
- [ ] Rebuild container and test

## 3. Set Up Redis
- [x] Ensure Redis is properly configured in Docker setup
- [ ] Update Django settings to use Redis for caching
- [ ] Rebuild container and test Redis connection

## 4. Update Python Dependencies
- [ ] Review and update requirements.txt
- [ ] Ensure Django 4.2.13 is specified
- [ ] Add any missing dependencies
- [ ] Rebuild container and test

## 5. Configure Django Settings
- [ ] Review and update config/settings.py
- [ ] Ensure database settings are correct (SQLite for dev)
- [ ] Configure Redis caching
- [ ] Set up REST Framework settings
- [ ] Configure CORS settings
- [ ] Set up logging (if not already configured)
- [ ] Rebuild container and test

## 6. Set Up Development Tools
- [ ] Ensure .devcontainer/devcontainer.json is properly configured
- [ ] Add any necessary VS Code extensions to devcontainer.json
- [ ] Rebuild container and test

## 7. Update Project Structure
- [ ] Ensure project structure matches the one in README
- [ ] Create any missing directories or files
- [ ] Rebuild container and test

## 8. Set Up and Test API Endpoints
- [ ] Ensure all mentioned API endpoints are properly set up
  - [ ] /bot/webhook
  - [ ] /bot/notify
  - [ ] /bot/welcome/message
  - [ ] /bot/wipe
- [ ] Create basic tests for each endpoint
- [ ] Run tests and fix any issues

## 9. Documentation
- [ ] Update README.md if any changes to setup process
- [ ] Ensure all setup instructions are clear and accurate
- [ ] Add or update any necessary documentation files

## 10. Final Testing
- [ ] Perform a clean build of the container
- [ ] Go through the entire setup process as a new user
- [ ] Test all features and endpoints
- [ ] Address any remaining issues

## Notes:
- After each step, rebuild the container if necessary and test to catch any bugs early.
- Update this work plan as we progress, marking completed tasks and adding any new tasks that arise.

# Task parking lot (keep these)

1. Update the features section of the readme, and any other relevant sections, with the way that this chatbot interacts with the api endpoints of the credex ecosystem.

# New Tasks

1. Review and update start_app.sh script to ensure it's compatible with the new Docker setup.
2. Check if any changes are needed in the .dockerignore file.
3. Verify that the EXPOSE port in Dockerfile matches the port in compose.yaml.
4. Consider adding a health check for the web service in compose.yaml.
5. Implement a wait-for-it script or similar to ensure the web service waits for Redis to be ready before starting.