.PHONY: dev-build dev-up dev-down prod-build prod-up prod-down

# Build for development
dev-build:
	DJANGO_ENV=development docker compose -f app/compose.yaml build \
		--build-arg REQUIREMENTS_FILE=requirements/dev.txt \
		--build-arg DJANGO_SETTINGS_MODULE=config.settings \
		--build-arg DJANGO_ENV=development

# Start the server (development)
dev-up:
	DJANGO_ENV=development docker compose -f app/compose.yaml up

# Stop the server (development)
dev-down:
	DJANGO_ENV=development docker compose -f app/compose.yaml down

# Build for production
prod-build:
	DJANGO_ENV=production docker compose -f app/compose.yaml build \
		--build-arg REQUIREMENTS_FILE=requirements/prod.txt \
		--build-arg DJANGO_SETTINGS_MODULE=config.settings \
		--build-arg DJANGO_ENV=production

# Start the server (production)
prod-up:
	DJANGO_ENV=production docker compose -f app/compose.yaml up -d

# Stop the server (production)
prod-down:
	DJANGO_ENV=production docker compose -f app/compose.yaml down
